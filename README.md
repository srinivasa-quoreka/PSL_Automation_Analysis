# PSL Automation - Jira Test Step Dashboard

Buckets Jira test cases by their number of test steps and shows the result as
a bar chart + table on a public, no-login dashboard.

## Stack
- **Backend:** Python 3.10+, FastAPI, Uvicorn, requests, python-dotenv, cachetools
- **Frontend:** single `index.html` served by FastAPI, Chart.js (CDN)
- **Database:** none (in-memory cache only — keeps it lite)

## Quick start

```bash
# 1. install
pip install -r requirements.txt

# 2. configure
cp .env.example .env
#   then edit .env with your Jira URL, username, password/API token, JQL

# 3. run
python -m app.main
# or:  uvicorn app.main:app --reload
```

Open <http://localhost:3000>. If SSL certificates exist, the server runs on **HTTPS** (see [HTTPS_SETUP.md](HTTPS_SETUP.md)).

## Endpoints
- `GET /` — dashboard
- `GET /api/test-cases` — JSON `{ total, buckets, test_cases, fetched_at, jql }`
- `GET /api/test-cases?refresh=true` — bypass cache
- `GET /api/test-cases?jql=...` — override default JQL
- `GET /api/health` — liveness probe

## Test step source

Set `TEST_TOOL` in `.env`:
| Value          | Where steps come from                                      |
|----------------|------------------------------------------------------------|
| `xray`         | Xray Server: `/rest/raven/1.0/api/test/{key}/steps`        |
| `zephyr_scale` | Zephyr Scale: `/rest/atm/1.0/testcase/{key}` -> `testScript.steps` |
| `custom_field` | A list/text custom field on the issue (`STEPS_CUSTOM_FIELD`) |

## Buckets
`0-10`, `11-20`, `21-30`, `31-40`, `41-50`, `51-60`, `61-70`, `70+`.

## Deploy (public URL, no login)

Any host that runs a Python web service works. Easiest options:

**Render** — connect the repo, set Start Command to
`uvicorn app.main:app --host 0.0.0.0 --port $PORT`, add the env vars from
`.env.example`. You get an `https://<name>.onrender.com` URL.

**Railway / Fly.io / Heroku** — same idea; the included `Procfile` is
compatible with Heroku-style buildpacks.

## Security
Jira credentials are read only on the server from environment variables and
are never sent to the browser. The frontend talks to the backend; the backend
talks to Jira.

### Admin Access
Access to admin functions (section publishing, custom JQL filters) is protected by an admin key parameter: `?key=admin123` (see `.env` for configuration). Non-admin users see the dashboard in read-only mode.

### HTTPS/TLS
The server supports **HTTPS encryption**. Self-signed SSL certificates are auto-detected:
- If `cert.pem` and `key.pem` exist, the server runs on HTTPS
- Generate certificates or use CA-signed certs in production
- See [HTTPS_SETUP.md](HTTPS_SETUP.md) for details
