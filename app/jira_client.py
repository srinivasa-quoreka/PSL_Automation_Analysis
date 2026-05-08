"""
Jira client: fetches test cases via JQL, counts steps per test case,
and groups the counts into buckets (0-10, 11-20, ..., 70+).

Credentials never leave this module / the server process.
"""
from __future__ import annotations

import os
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Any

import requests
from requests.auth import HTTPBasicAuth
from cachetools import TTLCache
import urllib3

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

log = logging.getLogger("jira_client")

# ---------------------------------------------------------------------------
# Configuration (read from environment)
# ---------------------------------------------------------------------------
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL", "").rstrip("/")
JIRA_USERNAME = os.getenv("JIRA_USERNAME", "")
JIRA_PASSWORD = os.getenv("JIRA_PASSWORD", "")
JIRA_JQL = os.getenv("JIRA_JQL", 'issuetype = "Test"')
TEST_TOOL = os.getenv("TEST_TOOL", "xray").lower().strip()
STEPS_CUSTOM_FIELD = os.getenv("STEPS_CUSTOM_FIELD", "customfield_10100")
AGILE_TEAM_FIELD = os.getenv("AGILE_TEAM_FIELD", "customfield_12013")
STEP_COUNT_OVERRIDES_RAW = os.getenv("STEP_COUNT_OVERRIDES", "")
CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))
MAX_RESULTS = int(os.getenv("MAX_RESULTS", "2000"))
PHASE2_MAX_RESULTS = int(os.getenv("PHASE2_MAX_RESULTS", "10000"))
SEARCH_TIMEOUT = int(os.getenv("SEARCH_TIMEOUT", "90"))
STEP_TIMEOUT = int(os.getenv("STEP_TIMEOUT", "60"))
TEST_TYPES = ["Sanity", "Smoke", "Regression"]
SANITY_UNDER_THRESHOLDS = [20, 40, 60, 80, 100, 120, 150]
SANITY_STEP_RANGES: List[Tuple[str, int, int | None]] = [
    ("r_0_20", 0, 20),
    ("r_21_40", 21, 40),
    ("r_41_60", 41, 60),
    ("r_61_80", 61, 80),
    ("r_81_100", 81, 100),
    ("r_101_120", 101, 120),
    ("r_121_150", 121, 150),
    ("r_151_plus", 151, None),
]
SANITY_RANGE_LABELS: Dict[str, str] = {
    "r_0_20": "0-20",
    "r_21_40": "21-40",
    "r_41_60": "41-60",
    "r_61_80": "61-80",
    "r_81_100": "81-100",
    "r_101_120": "101-120",
    "r_121_150": "121-150",
    "r_151_plus": "151+",
}

# Bucket boundaries: (label, lo, hi_inclusive). Last bucket is "70+".
BUCKETS: List[Tuple[str, int, int]] = [
    ("0-10",  0, 10),
    ("11-20", 11, 20),
    ("21-30", 21, 30),
    ("31-40", 31, 40),
    ("41-50", 41, 50),
    ("51-60", 51, 60),
    ("61-70", 61, 70),
    ("70+",   71, 10**9),
]

# in-memory cache of the last fetch (cuts down on Jira hits)
_cache: TTLCache = TTLCache(maxsize=20, ttl=max(CACHE_TTL, 1))


def _parse_step_count_overrides(raw: str) -> Dict[str, int]:
    """
    Parse STEP_COUNT_OVERRIDES from env.
    Format: "QAUT-3872=24,QAUT-4001=12"
    """
    overrides: Dict[str, int] = {}
    if not raw:
        return overrides

    for token in raw.split(","):
        part = token.strip()
        if not part or "=" not in part:
            continue
        key, value = part.split("=", 1)
        issue_key = key.strip().upper()
        value_text = value.strip()
        if not issue_key:
            continue
        try:
            count = int(value_text)
            if count >= 0:
                overrides[issue_key] = count
        except ValueError:
            continue
    return overrides


STEP_COUNT_OVERRIDES = _parse_step_count_overrides(STEP_COUNT_OVERRIDES_RAW)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _auth() -> HTTPBasicAuth:
    if not (JIRA_BASE_URL and JIRA_USERNAME and JIRA_PASSWORD):
        raise RuntimeError(
            "Jira credentials missing. Set JIRA_BASE_URL, JIRA_USERNAME, "
            "JIRA_PASSWORD in your .env file."
        )
    return HTTPBasicAuth(JIRA_USERNAME, JIRA_PASSWORD)


def _bucket_for(count: int) -> str:
    for label, lo, hi in BUCKETS:
        if lo <= count <= hi:
            return label
    return "70+"


def _append_test_type_filter(jql: str, test_type: str) -> str:
    # Allow explicit override keys to flow into every section so their bucketed
    # step counts can be reflected across Sanity/Smoke/Regression views.
    override_keys = [k for k in sorted(STEP_COUNT_OVERRIDES.keys()) if re.match(r"^[A-Za-z0-9_-]+$", k)]
    if override_keys:
        keys_clause = ",".join(override_keys)
        return f'({jql}) AND ("Test Type" = "{test_type}" OR key in ({keys_clause}))'
    return f'({jql}) AND "Test Type" = "{test_type}"'


def _section_jql(base_jql: str, test_type: str) -> str:
    """Build the effective JQL used for a section publish/query."""
    return _append_test_type_filter(base_jql, test_type)


def detect_single_test_type(jql: str) -> str | None:
    """Return one explicit test type if query contains: "Test Type" = <value>."""
    m = re.search(
        r'"Test\s*Type"\s*=\s*"?(Sanity|Smoke|Regression)"?',
        jql,
        flags=re.IGNORECASE,
    )
    if not m:
        return None
    value = m.group(1).lower()
    if value == "sanity":
        return "Sanity"
    if value == "smoke":
        return "Smoke"
    if value == "regression":
        return "Regression"
    return None


def _target_test_types(base_jql: str) -> List[str]:
    single = detect_single_test_type(base_jql)
    if single:
        return [single]
    return list(TEST_TYPES)


def _read_agile_team(issue: Dict[str, Any]) -> str:
    fields = issue.get("fields", {}) or {}
    team = fields.get(AGILE_TEAM_FIELD)
    if isinstance(team, dict):
        return str(team.get("value") or team.get("name") or "Unknown")
    if isinstance(team, list):
        names = []
        for item in team:
            if isinstance(item, dict):
                names.append(str(item.get("value") or item.get("name") or ""))
            else:
                names.append(str(item))
        names = [x for x in names if x]
        return ", ".join(names) if names else "Unknown"
    if team is None:
        return "Unknown"
    value = str(team).strip()
    return value if value else "Unknown"


def _extract_bug_of_test_links(issue: Dict[str, Any]) -> List[str]:
    """Return unique linked QAUT test issue keys attached via a Bug of issue link."""
    fields = issue.get("fields", {}) or {}
    issue_links = fields.get("issuelinks") or []
    linked_keys: set[str] = set()

    for link in issue_links:
        if not isinstance(link, dict):
            continue

        link_type = link.get("type") or {}
        inward_label = str(link_type.get("inward") or "").strip().lower()
        outward_label = str(link_type.get("outward") or "").strip().lower()

        linked_issue = None
        relation_label = ""
        if isinstance(link.get("inwardIssue"), dict):
            linked_issue = link.get("inwardIssue")
            relation_label = inward_label
        elif isinstance(link.get("outwardIssue"), dict):
            linked_issue = link.get("outwardIssue")
            relation_label = outward_label

        if not isinstance(linked_issue, dict):
            continue
        if relation_label != "bug of":
            continue

        linked_key = str(linked_issue.get("key") or "").strip()
        if not linked_key.upper().startswith("QAUT"):
            continue

        linked_fields = linked_issue.get("fields") or {}
        linked_issue_type = linked_fields.get("issuetype") or {}
        issue_type_name = str(linked_issue_type.get("name") or "").strip().lower()
        if issue_type_name and issue_type_name != "test":
            continue

        if linked_key:
            linked_keys.add(linked_key)

    return sorted(linked_keys)


def _normalize_test_type(value: Any) -> str | None:
    allowed = {"sanity": "Sanity", "smoke": "Smoke", "regression": "Regression"}
    if value is None:
        return None
    if isinstance(value, dict):
        return _normalize_test_type(value.get("value") or value.get("name"))
    if isinstance(value, list):
        for item in value:
            normalized = _normalize_test_type(item)
            if normalized:
                return normalized
        return None

    text = str(value).strip()
    if not text:
        return None
    lowered = text.lower()
    if lowered in allowed:
        return allowed[lowered]

    # Handle compound forms like "Sanity, Smoke".
    for token in re.split(r"[,/|]", lowered):
        token = token.strip()
        if token in allowed:
            return allowed[token]
    return None


def _get_test_type_field_id() -> str | None:
    cache_key = "meta::test-type-field-id"
    if cache_key in _cache:
        cached = _cache[cache_key]
        return str(cached) if cached else None

    try:
        url = f"{JIRA_BASE_URL}/rest/api/2/field"
        r = requests.get(url, auth=_auth(), timeout=SEARCH_TIMEOUT, verify=False)
        r.raise_for_status()
        fields = r.json() or []
        for field in fields:
            if not isinstance(field, dict):
                continue
            name = str(field.get("name") or "").strip().lower()
            if name == "test type":
                field_id = str(field.get("id") or "").strip()
                _cache[cache_key] = field_id
                return field_id or None
    except Exception as exc:  # pragma: no cover
        log.warning("Failed to resolve Test Type field id: %s", exc)

    _cache[cache_key] = ""
    return None


def _fetch_test_type_by_issue_keys(issue_keys: List[str]) -> Dict[str, str]:
    if not issue_keys:
        return {}

    field_id = _get_test_type_field_id()
    if not field_id:
        return {}

    result: Dict[str, str] = {}
    batch_size = 100
    for start in range(0, len(issue_keys), batch_size):
        batch = issue_keys[start:start + batch_size]
        keys_clause = ",".join(batch)
        jql = f"key in ({keys_clause})"
        url = f"{JIRA_BASE_URL}/rest/api/2/search"
        params = {
            "jql": jql,
            "startAt": 0,
            "maxResults": len(batch),
            "fields": f"issuetype,{field_id}",
        }
        r = requests.get(url, params=params, auth=_auth(), timeout=SEARCH_TIMEOUT, verify=False)
        r.raise_for_status()
        payload = r.json() or {}
        for issue in payload.get("issues", []) or []:
            key = str(issue.get("key") or "").strip()
            if not key:
                continue
            fields = issue.get("fields", {}) or {}
            issue_type = str(((fields.get("issuetype") or {}).get("name")) or "").strip().lower()
            if issue_type and issue_type != "test":
                continue
            normalized = _normalize_test_type(fields.get(field_id))
            if normalized:
                result[key] = normalized

    return result


def _fetch_agile_team_by_issue_keys(issue_keys: List[str]) -> Dict[str, str]:
    if not issue_keys:
        return {}

    result: Dict[str, str] = {}
    batch_size = 100
    for start in range(0, len(issue_keys), batch_size):
        batch = issue_keys[start:start + batch_size]
        keys_clause = ",".join(batch)
        jql = f"key in ({keys_clause})"
        url = f"{JIRA_BASE_URL}/rest/api/2/search"
        params = {
            "jql": jql,
            "startAt": 0,
            "maxResults": len(batch),
            "fields": f"issuetype,{AGILE_TEAM_FIELD}",
        }
        r = requests.get(url, params=params, auth=_auth(), timeout=SEARCH_TIMEOUT, verify=False)
        r.raise_for_status()
        payload = r.json() or {}
        for issue in payload.get("issues", []) or []:
            key = str(issue.get("key") or "").strip()
            if not key:
                continue
            team = _read_agile_team(issue)
            if team and team != "Unknown":
                result[key] = team

    return result


def _extract_linked_issue_keys(issue: Dict[str, Any]) -> List[str]:
    fields = issue.get("fields", {}) or {}
    issue_links = fields.get("issuelinks") or []
    keys: set[str] = set()
    for link in issue_links:
        if not isinstance(link, dict):
            continue
        inward = link.get("inwardIssue")
        outward = link.get("outwardIssue")
        if isinstance(inward, dict):
            key = str(inward.get("key") or "").strip()
            if key:
                keys.add(key)
        if isinstance(outward, dict):
            key = str(outward.get("key") or "").strip()
            if key:
                keys.add(key)
    return sorted(keys)


def _search_total(jql: str) -> int:
    """Fast count-only Jira search (no issue payload)."""
    url = f"{JIRA_BASE_URL}/rest/api/2/search"
    params = {
        "jql": jql,
        "startAt": 0,
        "maxResults": 0,
        "fields": "none",
    }
    r = requests.get(url, params=params, auth=_auth(), timeout=SEARCH_TIMEOUT, verify=False)
    r.raise_for_status()
    payload = r.json() or {}
    return int(payload.get("total", 0))


# ---------------------------------------------------------------------------
# Step-count strategies
# ---------------------------------------------------------------------------
def _steps_xray(key: str) -> int:
    """Xray Server: GET /rest/raven/1.0/api/test/{key}/steps -> list."""
    url = f"{JIRA_BASE_URL}/rest/raven/1.0/api/test/{key}/steps"
    r = requests.get(url, auth=_auth(), timeout=STEP_TIMEOUT, verify=False)
    if r.status_code == 404:
        return 0
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list):
        return 0

    total_steps = 0
    for item in data:
        if not isinstance(item, dict):
            continue

        # In some projects one Xray step can contain numbered sub-steps
        # (e.g. 1.1, 1.2). When present, count those instead of raw rows.
        substep_count = 0
        for fld in ("step", "action", "data", "result"):
            val = item.get(fld)
            if isinstance(val, str) and val.strip():
                substep_count = max(substep_count, _count_numbered_substeps(val))

        total_steps += substep_count if substep_count > 0 else 1

    return total_steps


def _steps_zephyr_scale(key: str) -> int:
    """Zephyr Scale: GET /rest/atm/1.0/testcase/{key} -> testScript.steps[]."""
    url = f"{JIRA_BASE_URL}/rest/atm/1.0/testcase/{key}"
    r = requests.get(url, auth=_auth(), timeout=STEP_TIMEOUT, verify=False)
    if r.status_code == 404:
        return 0
    r.raise_for_status()
    data = r.json() or {}
    script = data.get("testScript") or {}
    steps = script.get("steps") or []
    return len(steps) if isinstance(steps, list) else 0


def _count_numbered_substeps(text: str) -> int:
    """Count numbered steps and keyword-based steps from mixed Jira text formats.

    For each line:
    - If it has numbered patterns (1.1, 2.3, etc.), count those numbers.
    - Else if it has "Create" or "Refer" keywords with NO numbers, count it as one step.
    
    Supports:
    - nested steps: 1.1, 2.3, 3.15
    - flat steps: 1.Click, 6. In ..., 10) Do ...
    - keyword steps: "Create a Collection" (only if no number prefix)
    """
    if not text:
        return 0

    total_steps = 0
    lines = text.splitlines()
    
    for line in lines:
        if not line.strip():
            continue
        
        line_lower = line.lower()
        
        # Skip section header lines: "1.Create..." or "1.Refer..." pattern
        # These are marked as headers and shouldn't be counted as steps
        if re.match(r"^\s*\d+[.)\-]\s*(create|refer)\b", line_lower):
            continue
        
        # Check for nested numbering (1.1 / 2.3 / 3.15), including inline formats
        nested_pattern = re.compile(
            r"(?<!\d)\d+\.\d+(?:\.\d+)?(?=\s*(?:[\.:)\-]\s*)?[A-Za-z(])"
        )
        nested_matches = nested_pattern.findall(line)
        
        # Check for flat numbering (1.Click / 6. In ... / 10) Do ...).
        # Count only if next word is NOT "create" or "refer" (those are section headers).
        flat_pattern = re.compile(r"(?<!\d)\d+[.)](?!\d)\s*([A-Za-z][A-Za-z0-9_-]*)")
        flat_matches = []
        for m in flat_pattern.finditer(line):
            next_word = (m.group(1) or "").lower()
            if next_word not in ("create", "refer"):
                flat_matches.append(m)
        
        # If line has numbered patterns, count them and skip keyword check
        if nested_matches or flat_matches:
            total_steps += max(len(nested_matches), len(flat_matches))
            continue
        
        # If line has NO numbered patterns at all, check for keyword patterns
        line_lower = line.lower()
        # Count whole-word "create" or "refer" only (avoid matching words like "created").
        if re.search(r"\b(create|refer)\b", line_lower):
            total_steps += 1

    return total_steps


def _steps_zephyr_zapi(issue: Dict[str, Any]) -> int:
    """Legacy Zephyr: GET /rest/zapi/latest/teststep/{issueId} -> stepBeanCollection[]."""
    issue_id = issue.get("id")
    if not issue_id:
        return 0

    url = f"{JIRA_BASE_URL}/rest/zapi/latest/teststep/{issue_id}"
    r = requests.get(url, auth=_auth(), timeout=STEP_TIMEOUT, verify=False)
    if r.status_code == 404:
        return 0
    r.raise_for_status()

    data = r.json() or {}
    step_beans = data.get("stepBeanCollection") or []
    numbered_substeps = 0

    for step_bean in step_beans:
        step_text = "\n".join(
            str(step_bean.get(field) or "")
            for field in ("step", "action", "data")
        )
        numbered_substeps += _count_numbered_substeps(step_text)

    top_level_count = len(step_beans) if isinstance(step_beans, list) else 0
    return max(numbered_substeps, top_level_count)


def _steps_custom_field(issue: Dict[str, Any]) -> int:
    """Read step count from a custom field already present on the issue."""
    fields = issue.get("fields", {}) or {}
    val = fields.get(STEPS_CUSTOM_FIELD)
    if val is None:
        return 0
    if isinstance(val, list):
        return len(val)
    if isinstance(val, str):
        substeps = _count_numbered_substeps(val)
        if substeps:
            return substeps
        # fallback: count non-empty lines
        return len([ln for ln in val.splitlines() if ln.strip()])
    if isinstance(val, dict):
        # Xray Cloud sometimes returns {"steps":[...]}
        steps = val.get("steps")
        if isinstance(steps, list):
            return len(steps)
    return 0


def _count_steps(issue: Dict[str, Any]) -> int:
    key = issue.get("key", "")
    override_count = STEP_COUNT_OVERRIDES.get(str(key).upper())
    if override_count is not None:
        return int(override_count)
    try:
        if TEST_TOOL == "xray":
            xray_steps = _steps_xray(key)
            zapi_steps = _steps_zephyr_zapi(issue)
            if xray_steps or zapi_steps:
                return max(int(xray_steps), int(zapi_steps))
            return _steps_custom_field(issue)
        if TEST_TOOL == "zephyr_scale":
            scale_steps = _steps_zephyr_scale(key)
            zapi_steps = _steps_zephyr_zapi(issue)
            if scale_steps or zapi_steps:
                return max(int(scale_steps), int(zapi_steps))
            return _steps_custom_field(issue)
        if TEST_TOOL == "zephyr_zapi":
            zapi_steps = _steps_zephyr_zapi(issue)
            if zapi_steps:
                return zapi_steps
            return _steps_custom_field(issue)
        if TEST_TOOL == "custom_field":
            return _steps_custom_field(issue)
        # default fallback
        zapi_steps = _steps_zephyr_zapi(issue)
        if zapi_steps:
            return zapi_steps
        return _steps_custom_field(issue)
    except Exception as exc:  # pragma: no cover
        log.warning("Step count failed for %s: %s", key, exc)
        return 0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def fetch_test_cases(jql: str | None = None,
                     max_results: int | None = None,
                     extra_fields: List[str] | None = None,
                     expand: str | None = None) -> List[Dict[str, Any]]:
    """Page through Jira's /search endpoint and return raw issues."""
    jql = jql or JIRA_JQL
    effective_max = max_results if max_results is not None else MAX_RESULTS
    issues: List[Dict[str, Any]] = []
    start_at = 0
    page_size = 100
    fields = ["summary", "status", "issuetype", STEPS_CUSTOM_FIELD]
    if extra_fields:
        for fld in extra_fields:
            if fld and fld not in fields:
                fields.append(fld)

    while len(issues) < effective_max:
        url = f"{JIRA_BASE_URL}/rest/api/2/search"
        params = {
            "jql": jql,
            "startAt": start_at,
            "maxResults": page_size,
            "fields": ",".join(fields),
        }
        if expand:
            params["expand"] = expand
        r = requests.get(url, params=params, auth=_auth(), timeout=SEARCH_TIMEOUT, verify=False)
        r.raise_for_status()
        payload = r.json()
        batch = payload.get("issues", [])
        issues.extend(batch)
        if len(batch) < page_size:
            break
        start_at += page_size
        if start_at >= payload.get("total", 0):
            break
    return issues[:effective_max]


def build_dashboard_data(jql: str | None = None,
                         force_refresh: bool = False,
                         max_results: int | None = None) -> Dict[str, Any]:
    """
    Returns:
        {
            "total": <int>,
            "buckets": [{"label": "0-10", "count": <int>}, ...],
            "test_cases": [{"key","summary","status","steps","bucket"}, ...],
    
            "fetched_at": <iso>,
            "jql": "<jql used>",
        }
    """
    cache_key = jql or JIRA_JQL
    if not force_refresh and cache_key in _cache:
        return _cache[cache_key]

    import datetime as _dt
    
    issues = fetch_test_cases(jql, max_results=max_results)

    # Performance optimization: increase worker pool for single-type queries (better parallelization)
    single_type = detect_single_test_type(jql or JIRA_JQL)
    MAX_WORKERS = 20 if single_type else 10

    def _process_issue(issue: Dict[str, Any]) -> Dict[str, Any]:
        key = issue.get("key", "")
        f = issue.get("fields", {}) or {}
        summary = f.get("summary", "")
        status = (f.get("status") or {}).get("name", "")
        steps = _count_steps(issue)
        bucket = _bucket_for(steps)
        return {"key": key, "summary": summary, "status": status,
                "steps": steps, "bucket": bucket}

    rows: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(_process_issue, issue): i
                   for i, issue in enumerate(issues)}
        # Preserve original order
        ordered: Dict[int, Dict[str, Any]] = {}
        for fut in as_completed(futures):
            idx = futures[fut]
            try:
                ordered[idx] = fut.result()
            except Exception as exc:
                log.warning("Failed processing issue at index %s: %s", idx, exc)
        rows = [ordered[i] for i in sorted(ordered)]

    bucket_counts: Dict[str, int] = {label: 0 for label, _, _ in BUCKETS}
    for row in rows:
        bucket_counts[row["bucket"]] += 1

    result = {
        "total": len(rows),
        "buckets": [{"label": lbl, "count": bucket_counts[lbl]}
                    for lbl, _, _ in BUCKETS],
        "test_cases": rows,
        "fetched_at": _dt.datetime.utcnow().isoformat() + "Z",
        "jql": cache_key,
    }
    _cache[cache_key] = result
    return result


# ---------------------------------------------------------------------------
# Generic AgileTeam summary (works for Sanity, Smoke, Regression)
# ---------------------------------------------------------------------------

def get_agileteam_step_summary(base_jql: str,
                                test_type: str,
                                force_refresh: bool = False) -> Dict[str, Any]:
    """AgileTeam × non-overlapping step-range counts for any test type."""
    cache_key = f"agile-summary::{test_type}::{base_jql}"
    if not force_refresh and cache_key in _cache:
        return _cache[cache_key]

    filtered_jql = _section_jql(base_jql, test_type)
    source_total = _search_total(filtered_jql)
    max_issues = min(source_total, PHASE2_MAX_RESULTS)

    issues = fetch_test_cases(
        jql=filtered_jql,
        max_results=max_issues,
        extra_fields=[AGILE_TEAM_FIELD],
    )

    def _process(issue: Dict[str, Any]) -> Tuple[str, int]:
        return _read_agile_team(issue), _count_steps(issue)

    by_team_steps: Dict[str, List[int]] = {}
    with ThreadPoolExecutor(max_workers=10) as pool:
        futs = [pool.submit(_process, iss) for iss in issues]
        for fut in as_completed(futs):
            try:
                team, steps = fut.result()
                by_team_steps.setdefault(team, []).append(int(steps))
            except Exception as exc:
                log.warning("%s AgileTeam processing failed: %s", test_type, exc)

    def _range_counts(step_counts: List[int]) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for key, lo, hi in SANITY_STEP_RANGES:
            if hi is None:
                out[key] = sum(1 for c in step_counts if c >= lo)
            else:
                out[key] = sum(1 for c in step_counts if lo <= c <= hi)
        return out

    rows: List[Dict[str, Any]] = []
    for team in sorted(by_team_steps.keys()):
        counts = by_team_steps[team]
        row: Dict[str, Any] = {"agile_team": team, "total_test_cases": len(counts)}
        row.update(_range_counts(counts))
        rows.append(row)

    total_row: Dict[str, Any] = {
        "agile_team": "TOTAL",
        "total_test_cases": sum(r["total_test_cases"] for r in rows),
    }
    for key, _, _ in SANITY_STEP_RANGES:
        total_row[key] = sum(int(r.get(key, 0)) for r in rows)

    total_steps = sum(sum(v) for v in by_team_steps.values())
    total_count = sum(len(v) for v in by_team_steps.values())

    result = {
        "base_jql": base_jql,
        "test_type": test_type,
        "agile_team_field": AGILE_TEAM_FIELD,
        "thresholds": SANITY_UNDER_THRESHOLDS,
        "rows": rows,
        "total_row": total_row,
        "step_ranges": [{"key": k, "min": lo, "max": hi} for k, lo, hi in SANITY_STEP_RANGES],
        "total_test_cases": total_count,
        "source_total": source_total,
        "is_capped": source_total > max_issues,
        "phase2_max_results": PHASE2_MAX_RESULTS,
        "total_steps": total_steps,
        "avg_steps": round(total_steps / total_count, 2) if total_count else 0,
    }
    _cache[cache_key] = result
    return result


def get_issue_step_rows_for_type(base_jql: str,
                                  test_type: str,
                                  force_refresh: bool = False) -> Dict[str, Any]:
    """Issue-level rows (key, summary, team, steps, range) for any test type."""
    cache_key = f"issue-rows::{test_type}::{base_jql}"
    if not force_refresh and cache_key in _cache:
        return _cache[cache_key]

    filtered_jql = _section_jql(base_jql, test_type)
    source_total = _search_total(filtered_jql)
    max_issues = min(source_total, PHASE2_MAX_RESULTS)

    issues = fetch_test_cases(
        jql=filtered_jql,
        max_results=max_issues,
        extra_fields=[AGILE_TEAM_FIELD],
    )

    def _process(issue: Dict[str, Any]) -> Dict[str, Any]:
        k = str(issue.get("key") or "")
        fields = issue.get("fields", {}) or {}
        summary = str(fields.get("summary") or "")
        team = _read_agile_team(issue)
        steps = int(_count_steps(issue))
        rk = _step_range_key(steps)
        return {
            "issue_key": k,
            "summary": summary,
            "agile_team": team,
            "steps": steps,
            "range_key": rk,
            "range_label": SANITY_RANGE_LABELS.get(rk, "151+"),
        }

    rows: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        futs = [pool.submit(_process, iss) for iss in issues]
        for fut in as_completed(futs):
            try:
                rows.append(fut.result())
            except Exception as exc:
                log.warning("%s issue-level processing failed: %s", test_type, exc)

    rows.sort(key=lambda r: (r.get("agile_team", ""), r.get("steps", 0), r.get("issue_key", "")))

    result = {
        "base_jql": base_jql,
        "test_type": test_type,
        "rows": rows,
        "total_test_cases": len(rows),
        "source_total": source_total,
        "is_capped": source_total > max_issues,
        "phase2_max_results": PHASE2_MAX_RESULTS,
        "range_labels": SANITY_RANGE_LABELS,
    }
    _cache[cache_key] = result
    return result


def get_bug_analysis(base_jql: str,
                     force_refresh: bool = False) -> Dict[str, Any]:
    """Return bug rows and summary metrics for a Jira bug-analysis query."""
    cache_key = f"bug-analysis::{base_jql}"
    if not force_refresh and cache_key in _cache:
        return _cache[cache_key]

    source_total = _search_total(base_jql)
    max_issues = min(source_total, PHASE2_MAX_RESULTS)

    issues = fetch_test_cases(
        jql=base_jql,
        max_results=max_issues,
        extra_fields=[AGILE_TEAM_FIELD, "priority", "created", "reporter", "issuelinks"],
    )

    rows: List[Dict[str, Any]] = []
    by_status: Dict[str, int] = {}
    by_severity: Dict[str, int] = {}
    by_team: Dict[str, int] = {}
    all_linked_test_keys: set[str] = set()

    for issue in issues:
        fields = issue.get("fields", {}) or {}
        status_value = str(((fields.get("status") or {}).get("name")) or "Unknown")
        severity_value = str(((fields.get("priority") or {}).get("name")) or "Unknown")
        agile_team = _read_agile_team(issue)
        reporter = fields.get("reporter") or {}
        reporter_value = ""
        if isinstance(reporter, dict):
            reporter_value = str(
                reporter.get("displayName")
                or reporter.get("name")
                or reporter.get("emailAddress")
                or ""
            )
        else:
            reporter_value = str(reporter or "")

        linked_test_keys = _extract_bug_of_test_links(issue)
        all_linked_test_keys.update(linked_test_keys)

        row = {
            "id": str(issue.get("key") or ""),
            "title": str(fields.get("summary") or ""),
            "agileTeam": agile_team,
            "status": status_value,
            "severity": severity_value,
            "createdAt": str(fields.get("created") or "")[:10],
            "reporter": reporter_value,
            "linkedTestCount": len(linked_test_keys),
            "linkedTestKeys": linked_test_keys,
            "linkedSanityCount": 0,
            "linkedSmokeCount": 0,
            "linkedRegressionCount": 0,
        }
        rows.append(row)
        by_status[status_value] = by_status.get(status_value, 0) + 1
        by_severity[severity_value] = by_severity.get(severity_value, 0) + 1
        by_team[agile_team] = by_team.get(agile_team, 0) + 1

    test_type_by_key = _fetch_test_type_by_issue_keys(sorted(all_linked_test_keys))
    for row in rows:
        sanity = 0
        smoke = 0
        regression = 0
        for linked_key in row.get("linkedTestKeys", []) or []:
            tt = test_type_by_key.get(str(linked_key), "")
            if tt == "Sanity":
                sanity += 1
            elif tt == "Smoke":
                smoke += 1
            elif tt == "Regression":
                regression += 1
        row["linkedSanityCount"] = sanity
        row["linkedSmokeCount"] = smoke
        row["linkedRegressionCount"] = regression

    rows.sort(key=lambda row: (row.get("status", ""), row.get("severity", ""), row.get("id", "")))

    result = {
        "jql": base_jql,
        "rows": rows,
        "total_bugs": len(rows),
        "source_total": source_total,
        "is_capped": source_total > max_issues,
        "phase2_max_results": PHASE2_MAX_RESULTS,
        "by_status": by_status,
        "by_severity": by_severity,
        "by_team": by_team,
    }
    _cache[cache_key] = result
    return result


def _is_reopened_status(status_text: Any) -> bool:
    value = str(status_text or "").strip().lower().replace(" ", "").replace("-", "")
    return value == "reopened"


def get_reopened_test_case_analysis(base_jql: str,
                                    force_refresh: bool = False) -> Dict[str, Any]:
    """Return reopened test cases sorted by labels, excluding Automation_TCs label."""
    cache_key = f"reopened-tests::{base_jql}"
    if not force_refresh and cache_key in _cache:
        return _cache[cache_key]

    source_total = _search_total(base_jql)
    max_issues = min(source_total, PHASE2_MAX_RESULTS)

    issues = fetch_test_cases(
        jql=base_jql,
        max_results=max_issues,
        extra_fields=["summary", "labels", "status", AGILE_TEAM_FIELD, "issuelinks"],
        expand="changelog",
    )

    rows: List[Dict[str, Any]] = []
    total_reopen_events = 0
    fallback_linked_keys: set[str] = set()

    for issue in issues:
        fields = issue.get("fields", {}) or {}
        key = str(issue.get("key") or "")
        summary = str(fields.get("summary") or "")
        status_name = str(((fields.get("status") or {}).get("name")) or "")
        agile_team = _read_agile_team(issue)
        linked_issue_keys = _extract_linked_issue_keys(issue)

        raw_labels = fields.get("labels") or []
        filtered_labels: List[str] = []
        seen_labels: set[str] = set()
        for label in raw_labels:
            label_text = str(label or "").strip()
            if not label_text:
                continue
            if label_text.lower() == "automation_tcs":
                continue
            if label_text in seen_labels:
                continue
            seen_labels.add(label_text)
            filtered_labels.append(label_text)
        filtered_labels.sort(key=lambda x: x.lower())

        changelog = issue.get("changelog") or {}
        histories = changelog.get("histories") or []
        reopen_count = 0
        for history in histories:
            items = (history or {}).get("items") or []
            for item in items:
                if str((item or {}).get("field") or "").strip().lower() != "status":
                    continue
                if _is_reopened_status((item or {}).get("toString")):
                    reopen_count += 1
        total_reopen_events += reopen_count

        if agile_team == "Unknown":
            fallback_linked_keys.update(linked_issue_keys)

        rows.append({
            "issue_key": key,
            "summary": summary,
            "status": status_name,
            "agile_team": agile_team,
            "linked_issue_keys": linked_issue_keys,
            "labels": filtered_labels,
            "label_count": len(filtered_labels),
            "reopen_count": reopen_count,
            "labels_sort_key": "|".join(filtered_labels).lower() if filtered_labels else "~",
        })

    linked_team_map = _fetch_agile_team_by_issue_keys(sorted(fallback_linked_keys))
    for row in rows:
        if row.get("agile_team") != "Unknown":
            continue
        for linked_key in row.get("linked_issue_keys", []) or []:
            mapped = linked_team_map.get(str(linked_key) or "")
            if mapped and mapped != "Unknown":
                row["agile_team"] = mapped
                break

    rows.sort(key=lambda r: (str(r.get("labels_sort_key") or "~"), str(r.get("issue_key") or "")))

    label_case_count: Dict[str, int] = {}
    label_team_case_count: Dict[str, Dict[str, int]] = {}
    reopen_sum_by_label: Dict[str, int] = {}

    for row in rows:
        team = str(row.get("agile_team") or "Unknown")
        reopen_value = int(row.get("reopen_count", 0))
        for label in row.get("labels", []) or []:
            label_case_count[label] = label_case_count.get(label, 0) + 1
            team_map = label_team_case_count.setdefault(label, {})
            team_map[team] = team_map.get(team, 0) + 1
            reopen_sum_by_label[label] = reopen_sum_by_label.get(label, 0) + reopen_value

    label_rows = [
        {"label": label, "test_case_count": count}
        for label, count in sorted(label_case_count.items(), key=lambda x: (-x[1], x[0].lower()))
    ]

    team_names = sorted({str(r.get("agile_team") or "Unknown") for r in rows})
    matrix_rows: List[Dict[str, Any]] = []
    team_totals: Dict[str, int] = {team: 0 for team in team_names}

    for label in sorted(label_team_case_count.keys(), key=lambda x: x.lower()):
        per_team = {team: int(label_team_case_count.get(label, {}).get(team, 0)) for team in team_names}
        total_unique = sum(per_team.values())
        for team in team_names:
            team_totals[team] = team_totals.get(team, 0) + per_team.get(team, 0)
        matrix_rows.append({
            "label": label,
            "per_team": per_team,
            "total_unique_issues": total_unique,
            "reopen_count": int(reopen_sum_by_label.get(label, 0)),
        })

    total_row = {
        "label": "Total Unique Issues",
        "per_team": team_totals,
        "total_unique_issues": sum(team_totals.values()),
        "reopen_count": total_reopen_events,
    }

    result = {
        "base_jql": base_jql,
        "rows": rows,
        "total_test_cases": len(rows),
        "total_reopen_events": total_reopen_events,
        "source_total": source_total,
        "is_capped": source_total > max_issues,
        "phase2_max_results": PHASE2_MAX_RESULTS,
        "ignored_label": "Automation_TCs",
        "label_rows": label_rows,
        "team_names": team_names,
        "matrix_rows": matrix_rows,
        "matrix_total_row": total_row,
    }
    _cache[cache_key] = result
    return result


def get_sanity_agileteam_threshold_summary(base_jql: str,
                                           force_refresh: bool = False) -> Dict[str, Any]:
    """
    Returns AgileTeam-wise cumulative counts for Sanity tests under thresholds.
    """
    cache_key = f"sanity-agile::{base_jql}"
    if not force_refresh and cache_key in _cache:
        return _cache[cache_key]

    single_type = detect_single_test_type(base_jql)
    sanity_jql = base_jql if single_type == "Sanity" else _append_test_type_filter(base_jql, "Sanity")
    sanity_total = _search_total(sanity_jql)
    max_for_sanity = min(sanity_total, PHASE2_MAX_RESULTS)

    issues = fetch_test_cases(
        jql=sanity_jql,
        max_results=max_for_sanity,
        extra_fields=[AGILE_TEAM_FIELD],
    )

    def _process_issue(issue: Dict[str, Any]) -> Tuple[str, int]:
        team = _read_agile_team(issue)
        steps = _count_steps(issue)
        return team, steps

    by_team_steps: Dict[str, List[int]] = {}
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = [pool.submit(_process_issue, issue) for issue in issues]
        for fut in as_completed(futures):
            try:
                team, steps = fut.result()
                by_team_steps.setdefault(team, []).append(int(steps))
            except Exception as exc:
                log.warning("Sanity AgileTeam processing failed: %s", exc)

    def _range_counts(step_counts: List[int]) -> Dict[str, int]:
        values: Dict[str, int] = {}
        for key, lo, hi in SANITY_STEP_RANGES:
            if hi is None:
                values[key] = sum(1 for c in step_counts if c >= lo)
            else:
                values[key] = sum(1 for c in step_counts if lo <= c <= hi)
        return values

    rows: List[Dict[str, Any]] = []
    for team in sorted(by_team_steps.keys()):
        counts = by_team_steps[team]
        range_values = _range_counts(counts)
        row: Dict[str, Any] = {
            "agile_team": team,
            "total_test_cases": len(counts),
        }
        row.update(range_values)
        rows.append(row)

    total_row = {
        "agile_team": "TOTAL",
        "total_test_cases": sum(r["total_test_cases"] for r in rows),
    }
    for key, _, _ in SANITY_STEP_RANGES:
        total_row[key] = sum(int(r.get(key, 0)) for r in rows)

    result = {
        "base_jql": base_jql,
        "test_type": "Sanity",
        "agile_team_field": AGILE_TEAM_FIELD,
        "thresholds": SANITY_UNDER_THRESHOLDS,
        "rows": rows,
        "total_row": total_row,
        "step_ranges": [
            {"key": k, "min": lo, "max": hi}
            for k, lo, hi in SANITY_STEP_RANGES
        ],
        "total_test_cases": sum(r["total_test_cases"] for r in rows),
        "source_total": sanity_total,
        "is_capped": sanity_total > max_for_sanity,
        "phase2_max_results": PHASE2_MAX_RESULTS,
        "total_steps": sum(sum(v) for v in by_team_steps.values()),
        "avg_steps": round(
            (sum(sum(v) for v in by_team_steps.values()) / sum(len(v) for v in by_team_steps.values())),
            2,
        ) if by_team_steps else 0,
    }
    _cache[cache_key] = result
    return result


def _step_range_key(steps: int) -> str:
    for key, lo, hi in SANITY_STEP_RANGES:
        if hi is None and steps >= lo:
            return key
        if hi is not None and lo <= steps <= hi:
            return key
    return "r_151_plus"


def get_sanity_issue_step_rows(base_jql: str,
                               force_refresh: bool = False) -> Dict[str, Any]:
    """
    Returns issue-level rows for Sanity tests with AgileTeam, step count and range bucket.
    Useful for CSV exports and manual validation.
    """
    cache_key = f"sanity-rows::{base_jql}"
    if not force_refresh and cache_key in _cache:
        return _cache[cache_key]

    single_type = detect_single_test_type(base_jql)
    sanity_jql = base_jql if single_type == "Sanity" else _append_test_type_filter(base_jql, "Sanity")
    sanity_total = _search_total(sanity_jql)
    max_for_sanity = min(sanity_total, PHASE2_MAX_RESULTS)

    issues = fetch_test_cases(
        jql=sanity_jql,
        max_results=max_for_sanity,
        extra_fields=[AGILE_TEAM_FIELD],
    )

    def _process_issue(issue: Dict[str, Any]) -> Dict[str, Any]:
        key = str(issue.get("key") or "")
        fields = issue.get("fields", {}) or {}
        summary = str(fields.get("summary") or "")
        team = _read_agile_team(issue)
        steps = int(_count_steps(issue))
        range_key = _step_range_key(steps)
        return {
            "issue_key": key,
            "summary": summary,
            "agile_team": team,
            "steps": steps,
            "range_key": range_key,
            "range_label": SANITY_RANGE_LABELS.get(range_key, "151+"),
        }

    rows: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = [pool.submit(_process_issue, issue) for issue in issues]
        for fut in as_completed(futures):
            try:
                rows.append(fut.result())
            except Exception as exc:
                log.warning("Sanity issue-level processing failed: %s", exc)

    rows.sort(key=lambda r: (r.get("agile_team", ""), r.get("steps", 0), r.get("issue_key", "")))

    result = {
        "base_jql": base_jql,
        "rows": rows,
        "total_test_cases": len(rows),
        "source_total": sanity_total,
        "is_capped": sanity_total > max_for_sanity,
        "phase2_max_results": PHASE2_MAX_RESULTS,
        "range_labels": SANITY_RANGE_LABELS,
    }
    _cache[cache_key] = result
    return result


def get_test_type_counts(base_jql: str,
                         force_refresh: bool = False) -> Dict[str, Any]:
    """
    Fast phase-1 summary by test type using Jira total counts only.
    """
    cache_key = f"type-counts::{base_jql}"
    if not force_refresh and cache_key in _cache:
        return _cache[cache_key]

    target_types = _target_test_types(base_jql)
    rows: Dict[str, int] = {t: 0 for t in target_types}
    with ThreadPoolExecutor(max_workers=min(3, len(target_types))) as pool:
        futures = {
            pool.submit(_search_total, _append_test_type_filter(base_jql, t)): t
            for t in target_types
        }
        for fut in as_completed(futures):
            test_type = futures[fut]
            try:
                rows[test_type] = fut.result()
            except Exception as exc:
                log.warning("Type count failed for %s: %s", test_type, exc)
                rows[test_type] = 0

    result = {
        "base_jql": base_jql,
        "types": [{"test_type": t, "count": rows[t]} for t in target_types],
        "total": sum(rows.values()),
    }
    _cache[cache_key] = result
    return result


def get_test_type_step_counts(base_jql: str,
                              force_refresh: bool = False) -> Dict[str, Any]:
    """
    Phase-2 summary by test type with aggregated step counts.
    """
    cache_key = f"type-steps::{base_jql}"
    if not force_refresh and cache_key in _cache:
        return _cache[cache_key]

    target_types = _target_test_types(base_jql)

    def _for_type(test_type: str) -> Dict[str, Any]:
        jql = _append_test_type_filter(base_jql, test_type)
        type_total = _search_total(jql)
        max_for_type = min(type_total, PHASE2_MAX_RESULTS)
        data = build_dashboard_data(
            jql=jql,
            force_refresh=force_refresh,
            max_results=max_for_type,
        )
        test_count = int(data.get("total", 0))
        total_steps = sum(int(x.get("steps", 0)) for x in data.get("test_cases", []))
        avg_steps = round((total_steps / test_count), 2) if test_count else 0
        return {
            "test_type": test_type,
            "test_case_count": test_count,
            "total_steps": total_steps,
            "avg_steps": avg_steps,
            "source_total": type_total,
            "is_capped": type_total > max_for_type,
        }

    rows_by_type: Dict[str, Dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=min(3, len(target_types))) as pool:
        futures = {pool.submit(_for_type, t): t for t in target_types}
        for fut in as_completed(futures):
            test_type = futures[fut]
            try:
                rows_by_type[test_type] = fut.result()
            except Exception as exc:
                log.warning("Step summary failed for %s: %s", test_type, exc)
                rows_by_type[test_type] = {
                    "test_type": test_type,
                    "test_case_count": 0,
                    "total_steps": 0,
                    "avg_steps": 0,
                }

    rows = [rows_by_type[t] for t in target_types]
    result = {
        "base_jql": base_jql,
        "types": rows,
        "total_test_cases": sum(r["test_case_count"] for r in rows),
        "total_steps": sum(r["total_steps"] for r in rows),
        "is_capped": any(r.get("is_capped") for r in rows),
        "phase2_max_results": PHASE2_MAX_RESULTS,
    }
    _cache[cache_key] = result
    return result
