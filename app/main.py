"""
FastAPI entry point.

  GET /                -> dashboard HTML (no login)
  GET /api/health      -> liveness probe
  GET /api/test-cases  -> JSON: buckets + rows
"""
from __future__ import annotations

import json
import os
import csv
from io import StringIO
from pathlib import Path
from threading import Lock

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Load .env BEFORE importing modules that read os.environ at import time
load_dotenv()

from app import jira_client, queries  # noqa: E402

app = FastAPI(
    title="PSL Automation - Jira Test Step Dashboard",
    version="1.0.0",
    description="Buckets Jira test cases by their number of steps.",
)

# Public dashboard, so allow any origin to GET data
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"
DATA_DIR = Path(__file__).parent / "data"
PUBLISHED_STATE_FILE = DATA_DIR / "published_state.json"
ADMIN_ACCESS_KEY = os.getenv("ADMIN_ACCESS_KEY", "admin123").strip()
_state_lock = Lock()

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class PublishRequest(BaseModel):
    jql: str
    refresh: bool = False


class PublishSectionRequest(BaseModel):
    jql: str
    test_type: str  # "Sanity", "Smoke", "Regression"
    refresh: bool = False


def _require_admin(x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")) -> None:
    if x_admin_key != ADMIN_ACCESS_KEY:
        raise HTTPException(status_code=403, detail="Admin access denied.")


def _load_published_state() -> dict:
    with _state_lock:
        if not PUBLISHED_STATE_FILE.exists():
            return {"published": False}
        try:
            return json.loads(PUBLISHED_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {"published": False}


def _save_published_state(data: dict) -> None:
    with _state_lock:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        PUBLISHED_STATE_FILE.write_text(json.dumps(data, ensure_ascii=True, indent=2), encoding="utf-8")


def _update_published_section(section_key: str, section_data: dict) -> None:
    """Atomically update one section (sanity/smoke/regression) in the published state."""
    with _state_lock:
        if PUBLISHED_STATE_FILE.exists():
            try:
                state = json.loads(PUBLISHED_STATE_FILE.read_text(encoding="utf-8"))
            except Exception:
                state = {"published": False}
        else:
            state = {"published": False}
        state["published"] = True
        state[section_key] = section_data
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        PUBLISHED_STATE_FILE.write_text(json.dumps(state, ensure_ascii=True, indent=2), encoding="utf-8")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/dashboards")
def list_dashboards() -> JSONResponse:
    """List all available dashboards."""
    return JSONResponse({"dashboards": queries.list_dashboards()})


@app.get("/api/test-cases")
def test_cases(
    dashboard: str | None = Query(default=None, description="Dashboard ID (see /api/dashboards)"),
    jql: str | None = Query(default=None, description="Override JQL query"),
    refresh: bool = Query(default=False, description="Bypass cache"),
    _: None = Depends(_require_admin),
) -> JSONResponse:
    try:
        # Priority: explicit jql > dashboard > default
        if jql:
            query_jql = jql
        elif dashboard:
            query_config = queries.get_query(dashboard)
            query_jql = query_config["jql"]
        else:
            query_jql = None
        
        data = jira_client.build_dashboard_data(jql=query_jql, force_refresh=refresh)
        return JSONResponse(data)
    except RuntimeError as e:
        # Missing config
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=502, detail=f"Jira fetch failed: {e}")


@app.get("/api/test-type-counts")
def test_type_counts(
    jql: str = Query(..., description="Base JQL query"),
    refresh: bool = Query(default=False, description="Bypass cache"),
    _: None = Depends(_require_admin),
) -> JSONResponse:
    try:
        data = jira_client.get_test_type_counts(base_jql=jql, force_refresh=refresh)
        return JSONResponse(data)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=502, detail=f"Jira fetch failed: {e}")


        return JSONResponse(data)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=502, detail=f"Jira fetch failed: {e}")


@app.get("/api/sanity-agileteam-thresholds")
def sanity_agileteam_thresholds(
    jql: str = Query(..., description="Base JQL query"),
    refresh: bool = Query(default=False, description="Bypass cache"),
    _: None = Depends(_require_admin),
) -> JSONResponse:
    try:
        data = jira_client.get_sanity_agileteam_threshold_summary(
            base_jql=jql,
            force_refresh=refresh,
        )
        return JSONResponse(data)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=502, detail=f"Jira fetch failed: {e}")


@app.get("/api/admin/sanity-agileteam-export-csv")
def sanity_agileteam_export_csv(
    jql: str = Query(..., description="Base JQL query"),
    team: str | None = Query(default=None, description="Filter by AgileTeam"),
    range_key: str | None = Query(default=None, description="Filter by step range key"),
    admin_key: str | None = Query(default=None, description="Admin key (optional alternative to X-Admin-Key header)"),
    refresh: bool = Query(default=False, description="Bypass cache"),
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
) -> Response:
    try:
        if (x_admin_key or "") != ADMIN_ACCESS_KEY and (admin_key or "") != ADMIN_ACCESS_KEY:
            raise HTTPException(status_code=403, detail="Admin access denied.")

        range_labels = {
            "r_0_20": "0-20",
            "r_21_40": "21-40",
            "r_41_60": "41-60",
            "r_61_80": "61-80",
            "r_81_100": "81-100",
            "r_101_120": "101-120",
            "r_121_150": "121-150",
            "r_151_plus": "151+",
        }
        allowed_range_keys = set(range_labels.keys())
        normalized_range = (range_key or "").strip()
        if normalized_range and normalized_range not in allowed_range_keys:
            raise HTTPException(status_code=400, detail="Invalid range_key.")

        # Use pre-computed rows from published state if available (avoids live Jira fetch).
        published = _load_published_state()
        if published.get("published") and published.get("sanity_issue_rows") is not None:
            rows = published["sanity_issue_rows"]
        else:
            data = jira_client.get_sanity_issue_step_rows(base_jql=jql, force_refresh=refresh)
            rows = data.get("rows", [])

        if team:
            rows = [r for r in rows if str(r.get("agile_team") or "") == team]
        if normalized_range:
            rows = [r for r in rows if str(r.get("range_key") or "") == normalized_range]

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Issue Key",
            "Summary",
            "AgileTeam",
            "Step Count",
            "Range",
            "Range Key",
        ])
        for row in rows:
            writer.writerow([
                row.get("issue_key", ""),
                row.get("summary", ""),
                row.get("agile_team", ""),
                row.get("steps", 0),
                row.get("range_label", ""),
                row.get("range_key", ""),
            ])

        safe_team = (team or "all-teams").replace(" ", "-").replace("/", "-")
        safe_range = range_labels.get(normalized_range, "all-ranges") if normalized_range else "all-ranges"
        filename = f"sanity-ids-{safe_team}-{safe_range}.csv"

        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=502, detail=f"CSV export failed: {e}")


@app.get("/api/published-state")
def published_state() -> JSONResponse:
    return JSONResponse(_load_published_state())


@app.get("/api/bug-analysis")
def bug_analysis_public() -> JSONResponse:
    """Return last published bug analysis for view-only users."""
    published = _load_published_state()
    data = published.get("bug_analysis")
    if not data:
        raise HTTPException(status_code=404, detail="No published bug analysis found.")
    return JSONResponse(data)


@app.get("/api/reopened-test-analysis")
def reopened_test_analysis_public() -> JSONResponse:
    """Return last published re-opened test analysis for view-only users."""
    published = _load_published_state()
    data = published.get("reopened_test_analysis")
    if not data:
        raise HTTPException(status_code=404, detail="No published re-opened test analysis found.")
    return JSONResponse(data)


@app.get("/api/admin/bug-analysis")
def bug_analysis(
    jql: str = Query(..., description="Bug analysis JQL query"),
    refresh: bool = Query(default=False, description="Bypass cache"),
    _: None = Depends(_require_admin),
) -> JSONResponse:
    try:
        query_jql = jql.strip()
        if not query_jql:
            raise HTTPException(status_code=400, detail="JQL is required.")
        data = jira_client.get_bug_analysis(base_jql=query_jql, force_refresh=refresh)

        published = _load_published_state()
        published["bug_analysis"] = data
        published["bug_analysis_jql"] = query_jql
        _save_published_state(published)

        return JSONResponse(data)
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Bug analysis failed: {e}")


@app.get("/api/admin/reopened-test-analysis")
def reopened_test_analysis(
    jql: str = Query(..., description="Re-opened test case analysis JQL query"),
    refresh: bool = Query(default=False, description="Bypass cache"),
    _: None = Depends(_require_admin),
) -> JSONResponse:
    try:
        query_jql = jql.strip()
        if not query_jql:
            raise HTTPException(status_code=400, detail="JQL is required.")
        data = jira_client.get_reopened_test_case_analysis(base_jql=query_jql, force_refresh=refresh)

        published = _load_published_state()
        published["reopened_test_analysis"] = data
        published["reopened_test_analysis_jql"] = query_jql
        _save_published_state(published)

        return JSONResponse(data)
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Re-opened test analysis failed: {e}")


@app.post("/api/admin/publish-section")
def admin_publish_section(payload: PublishSectionRequest, _: None = Depends(_require_admin)) -> JSONResponse:
    valid_types = {"Sanity", "Smoke", "Regression"}
    if payload.test_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"test_type must be one of {sorted(valid_types)}")
    base_jql = payload.jql.strip()
    if not base_jql:
        raise HTTPException(status_code=400, detail="JQL is required.")
    try:
        import time
        import datetime as _dt
        start = time.time()

        agile = jira_client.get_agileteam_step_summary(
            base_jql=base_jql,
            test_type=payload.test_type,
            force_refresh=payload.refresh,
        )
        issue_rows = jira_client.get_issue_step_rows_for_type(
            base_jql=base_jql,
            test_type=payload.test_type,
            force_refresh=payload.refresh,
        ).get("rows", [])

        section_data = {
            "jql": base_jql,
            "published_at": _dt.datetime.utcnow().isoformat() + "Z",
            "execution_time_sec": round(time.time() - start, 2),
            "agile": agile,
            "issue_rows": issue_rows,
        }
        _update_published_section(payload.test_type.lower(), section_data)
        return JSONResponse(section_data)
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Publish failed: {e}")


@app.get("/api/export-csv")
def export_csv_public(
    test_type: str = Query(..., description="Sanity, Smoke, or Regression"),
    team: str | None = Query(default=None),
    range_key: str | None = Query(default=None),
) -> Response:
    """Public CSV export from already-published snapshot data."""
    try:
        valid_types = {"Sanity", "Smoke", "Regression"}
        if test_type not in valid_types:
            raise HTTPException(status_code=400, detail=f"Invalid test_type. Must be one of {sorted(valid_types)}")

        range_labels = {
            "r_0_20": "0-20", "r_21_40": "21-40", "r_41_60": "41-60",
            "r_61_80": "61-80", "r_81_100": "81-100", "r_101_120": "101-120",
            "r_121_150": "121-150", "r_151_plus": "151+",
        }
        normalized_range = (range_key or "").strip()
        if normalized_range and normalized_range not in range_labels:
            raise HTTPException(status_code=400, detail="Invalid range_key.")

        published = _load_published_state()
        section = published.get(test_type.lower(), {})
        rows = section.get("issue_rows", [])

        # Backward compat: Sanity from old-format snapshot
        if not rows and test_type == "Sanity" and published.get("sanity_issue_rows"):
            rows = published["sanity_issue_rows"]

        if not rows:
            raise HTTPException(status_code=404, detail="No published data found for export.")

        if team:
            rows = [r for r in rows if str(r.get("agile_team") or "") == team]
        if normalized_range:
            rows = [r for r in rows if str(r.get("range_key") or "") == normalized_range]

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["Issue Key", "Summary", "AgileTeam", "Step Count", "Range", "Range Key"])
        for row in rows:
            writer.writerow([
                row.get("issue_key", ""), row.get("summary", ""),
                row.get("agile_team", ""), row.get("steps", 0),
                row.get("range_label", ""), row.get("range_key", ""),
            ])

        safe_type = test_type.lower()
        safe_team = (team or "all-teams").replace(" ", "-").replace("/", "-")
        safe_range = range_labels.get(normalized_range, "all-ranges") if normalized_range else "all-ranges"
        filename = f"{safe_type}-ids-{safe_team}-{safe_range}.csv"

        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSV export failed: {e}")


@app.get("/api/admin/export-csv")
def export_csv_generic(
    test_type: str = Query(..., description="Sanity, Smoke, or Regression"),
    team: str | None = Query(default=None),
    range_key: str | None = Query(default=None),
    admin_key: str | None = Query(default=None),
    refresh: bool = Query(default=False),
    jql: str | None = Query(default=None),
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
) -> Response:
    try:
        if (x_admin_key or "") != ADMIN_ACCESS_KEY and (admin_key or "") != ADMIN_ACCESS_KEY:
            raise HTTPException(status_code=403, detail="Admin access denied.")

        valid_types = {"Sanity", "Smoke", "Regression"}
        if test_type not in valid_types:
            raise HTTPException(status_code=400, detail=f"Invalid test_type. Must be one of {sorted(valid_types)}")

        range_labels = {
            "r_0_20": "0-20", "r_21_40": "21-40", "r_41_60": "41-60",
            "r_61_80": "61-80", "r_81_100": "81-100", "r_101_120": "101-120",
            "r_121_150": "121-150", "r_151_plus": "151+",
        }
        normalized_range = (range_key or "").strip()
        if normalized_range and normalized_range not in range_labels:
            raise HTTPException(status_code=400, detail="Invalid range_key.")

        published = _load_published_state()
        section = published.get(test_type.lower(), {})
        rows = section.get("issue_rows", [])

        # Backward compat: Sanity from old-format snapshot
        if not rows and test_type == "Sanity" and published.get("sanity_issue_rows"):
            rows = published["sanity_issue_rows"]

        # Fallback: live fetch if nothing cached
        if not rows and jql:
            data = jira_client.get_issue_step_rows_for_type(
                base_jql=jql, test_type=test_type, force_refresh=refresh,
            )
            rows = data.get("rows", [])

        if team:
            rows = [r for r in rows if str(r.get("agile_team") or "") == team]
        if normalized_range:
            rows = [r for r in rows if str(r.get("range_key") or "") == normalized_range]

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["Issue Key", "Summary", "AgileTeam", "Step Count", "Range", "Range Key"])
        for row in rows:
            writer.writerow([
                row.get("issue_key", ""), row.get("summary", ""),
                row.get("agile_team", ""), row.get("steps", 0),
                row.get("range_label", ""), row.get("range_key", ""),
            ])

        safe_type = test_type.lower()
        safe_team = (team or "all-teams").replace(" ", "-").replace("/", "-")
        safe_range = range_labels.get(normalized_range, "all-ranges") if normalized_range else "all-ranges"
        filename = f"{safe_type}-ids-{safe_team}-{safe_range}.csv"

        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CSV export failed: {e}")

@app.post("/api/admin/publish")
def admin_publish(payload: PublishRequest, _: None = Depends(_require_admin)) -> JSONResponse:
    try:
        import time
        start_time = time.time()
        
        base_jql = payload.jql.strip()
        if not base_jql:
            raise HTTPException(status_code=400, detail="JQL is required.")

        single_type = jira_client.detect_single_test_type(base_jql)

        if single_type == "Sanity":
            # Fast path: compute once and reuse for all summary cards.
            sanity_agile = jira_client.get_sanity_agileteam_threshold_summary(
                base_jql=base_jql,
                force_refresh=payload.refresh,
            )
            sanity_issue_rows = jira_client.get_sanity_issue_step_rows(
                base_jql=base_jql,
                force_refresh=payload.refresh,
            ).get("rows", [])
            sanity_count = int(sanity_agile.get("total_test_cases", 0))
            sanity_total_steps = int(sanity_agile.get("total_steps", 0))
            sanity_avg_steps = float(sanity_agile.get("avg_steps", 0))
            type_counts = {
                "base_jql": base_jql,
                "types": [{"test_type": "Sanity", "count": sanity_count}],
                "total": sanity_count,
            }
            type_steps = {
                "base_jql": base_jql,
                "types": [{
                    "test_type": "Sanity",
                    "test_case_count": sanity_count,
                    "total_steps": sanity_total_steps,
                    "avg_steps": sanity_avg_steps,
                    "source_total": int(sanity_agile.get("source_total", sanity_count)),
                    "is_capped": bool(sanity_agile.get("is_capped", False)),
                }],
                "total_test_cases": sanity_count,
                "total_steps": sanity_total_steps,
                "is_capped": bool(sanity_agile.get("is_capped", False)),
                "phase2_max_results": int(sanity_agile.get("phase2_max_results", 0)),
            }
        else:
            type_counts = jira_client.get_test_type_counts(base_jql=base_jql, force_refresh=payload.refresh)
            type_steps = jira_client.get_test_type_step_counts(base_jql=base_jql, force_refresh=payload.refresh)
            # Only compute Sanity AgileTeam table when base query includes Sanity or no explicit type.
            if single_type is None:
                sanity_agile = jira_client.get_sanity_agileteam_threshold_summary(
                    base_jql=base_jql,
                    force_refresh=payload.refresh,
                )
                sanity_issue_rows = jira_client.get_sanity_issue_step_rows(
                    base_jql=base_jql,
                    force_refresh=payload.refresh,
                ).get("rows", [])
            else:
                sanity_agile = {
                    "base_jql": base_jql,
                    "test_type": "Sanity",
                    "agile_team_field": os.getenv("AGILE_TEAM_FIELD", "customfield_12013"),
                    "thresholds": [20, 40, 60, 80, 100, 120, 150],
                    "rows": [],
                    "total_test_cases": 0,
                    "source_total": 0,
                    "is_capped": False,
                    "phase2_max_results": int(os.getenv("PHASE2_MAX_RESULTS", "10000")),
                    "total_steps": 0,
                    "avg_steps": 0,
                }
                sanity_issue_rows = []

        import datetime as _dt
        execution_time = round(time.time() - start_time, 2)
        snapshot = {
            "published": True,
            "published_at": _dt.datetime.utcnow().isoformat() + "Z",
            "execution_time_sec": execution_time,
            "base_jql": base_jql,
            "type_counts": type_counts,
            "type_steps": type_steps,
            "sanity_agile": sanity_agile,
            "sanity_issue_rows": sanity_issue_rows,
        }
        _save_published_state(snapshot)
        return JSONResponse(snapshot)
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=502, detail=f"Publish failed: {e}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
