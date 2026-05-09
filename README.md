# PSL Automation - Jira Test Step Dashboard

Buckets Jira test cases by their number of test steps and shows the result as
a bar chart + table on a public, no-login dashboard.

## Stack
- **Backend:** Python 3.10+, FastAPI, Uvicorn, requests, python-dotenv, cachetools
- **Frontend:** single `index.html` served by FastAPI, Chart.js (CDN)
- **Database:** none (in-memory cache only — keeps it lite)

## Quick Start (Windows - One Click!)

### Easiest Way: Batch File Setup

1. **Double-click** → `setup-https.bat`
2. Wait for setup to complete (2-3 minutes)
3. Browser opens to dashboard
4. **Done!** ✅

**That's it!** The batch file handles:
- Python installation check
- Dependency installation
- SSL certificate generation
- Environment configuration
- HTTPS server startup
- Auto-remembers on reboot

**See**: [BATCH_FILES_README.md](BATCH_FILES_README.md) for details

---

### Manual Setup (All Platforms)

```bash
# 1. install dependencies
pip install -r requirements.txt

# 2. configure
cp .env.example .env
# Edit .env with your Jira URL, username, password/API token

# 3. run (HTTP)
python -m app.main

# 3b. run (HTTPS - if cert.pem and key.pem exist)
# Use HTTPS_INSTALLATION_GUIDE.md for certificate setup
```

Open `http://localhost:3000` (HTTP) or `https://localhost:3000` (HTTPS)

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

## Deployment (public URL, no login)

Any host that runs a Python web service works. Easiest options:

**Render** — connect the repo, set Start Command to
`uvicorn app.main:app --host 0.0.0.0 --port $PORT`, add the env vars from
`.env.example`. You get an `https://<name>.onrender.com` URL.

**Railway / Fly.io / Heroku** — same idea; the included `Procfile` is
compatible with Heroku-style buildpacks.

---

## Batch File Setup (Windows)

Automated setup for one-click configuration:

### Available Batch Files

| File | Purpose | When to Use |
|------|---------|-----------|
| `setup-https.bat` | One-click full setup + server start | First time, after reboot |
| `start-server-silent.bat` | Silent server startup (no prompts) | Auto-start on reboot |
| `create-shortcuts.bat` | Create desktop shortcuts | For quick access |

### Quick Usage

```batch
REM First time setup (2-3 minutes)
Double-click: setup-https.bat

REM After reboot (15 seconds)
Double-click: setup-https.bat

REM Optional: Auto-start on reboot
Double-click: create-shortcuts.bat
Move "PSL Auto-Start.lnk" to Startup folder
```

### What Batch File Does

✅ Checks Python installation  
✅ Installs dependencies  
✅ Generates SSL certificates  
✅ Configures environment  
✅ Starts HTTPS server  
✅ Opens dashboard in browser  
✅ Remembers setup (no repeat)  

**See**: [BATCH_FILES_README.md](BATCH_FILES_README.md) for full details

---

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
- See [HTTPS_INSTALLATION_GUIDE.md](HTTPS_INSTALLATION_GUIDE.md) for details

---

## Documentation

Complete guides for setup and configuration:

| Guide | Purpose | Read When |
|-------|---------|-----------|
| [BATCH_FILES_README.md](BATCH_FILES_README.md) | Batch file overview & quick reference | Want quick setup |
| [BATCH_SETUP_GUIDE.md](BATCH_SETUP_GUIDE.md) | Detailed batch file usage & troubleshooting | Need detailed help |
| [HTTPS_INSTALLATION_GUIDE.md](HTTPS_INSTALLATION_GUIDE.md) | Complete HTTPS setup guide | Need HTTPS details |
| [HTTPS_SETUP.md](HTTPS_SETUP.md) | Quick HTTPS reference | Quick reference |

### Quick Links

- **Dashboard**: `https://localhost:3000/`
- **Admin Panel**: `https://localhost:3000/?admin=1&key=admin123`
- **GitHub**: https://github.com/srinivasa-quoreka/PSL_Automation_Analysis
- **Jira**: Your Jira instance URL (configured in .env)
