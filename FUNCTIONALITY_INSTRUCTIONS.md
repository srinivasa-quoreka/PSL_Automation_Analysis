# PSL Automation - Functionality Instructions

This document captures all working features implemented so far in the dashboard.

## 1. How to Run

1. Open PowerShell in the project root.
2. Run:

```powershell
.\start.ps1
```

3. Open in browser:

- User mode: http://localhost:3000/
- Admin mode: http://localhost:3000/?admin=1&key=admin123

Notes:
- Admin mode is required for Run/Publish and CSV export actions.
- Admin key is read from environment variable `ADMIN_ACCESS_KEY` (default `admin123`).

## 2. Tabs and Sections

The UI contains these tabs:

- Published Data
- Admin Runner (visible in admin mode)
- Bug Analysis

The Test Step Distribution functionality has 3 independent sections:

- Sanity
- Smoke
- Regression

Each section has:
- JQL input
- Run & Publish button
- Save Query button
- Step-range table by AgileTeam
- Export Range dropdown
- Export All CSV button
- Team-level CSV button in each row

## 3. Test Step Distribution Flow

### 3.1 Run and Publish

For each test type section (Sanity/Smoke/Regression):

1. Enter JQL.
2. Click Run & Publish.
3. Backend computes AgileTeam-wise step-range counts.
4. Backend stores snapshot data for that section.
5. Table updates in UI with latest counts.

Data is published per section to persisted snapshot state.

### 3.2 Save Query

Each section supports Save Query.

Behavior:
- Saves query in browser local storage.
- Saved automatically after successful publish.
- Restored on page reload.

Storage keys:
- `pslSavedJql:sanity`
- `pslSavedJql:smoke`
- `pslSavedJql:regression`

### 3.3 CSV Export

CSV export is available for each section:

- Export all rows
- Export by selected step range
- Export by individual AgileTeam row

Important behavior:
- Export uses cached issue-level rows from published snapshot when available (fast).
- If cache is missing, export can fetch live data using provided JQL.

## 4. Bug Analysis Flow

### 4.1 Query

Default bug analysis query:

```
issueFunction in linkedIssuesOf("project = QA-Automation AND issuetype = Test") AND issuetype = Bug
```

Bug Analysis supports:
- Bug JQL input
- Run Query button
- Save Query button
- Reload Data button
- Filters (Team, Status, Severity)
- Export CSV button

Storage key:
- `pslSavedJql:bug-analysis`

### 4.2 Linked Test Counting Rules

For each bug row:

1. Read issue links from bug.
2. Keep only links with relation label `Bug of`.
3. Keep linked issue keys starting with `QAUT`.
4. Keep linked issue type `Test` when type info is available.
5. Remove duplicates by issue key.

Outputs per bug:
- `Linked Tests` (total deduplicated linked tests)
- `Sanity` count
- `Smoke` count
- `Regression` count

Per-type counts are derived from linked test case `Test Type` values.

### 4.3 Linked Test Popup

In Bug Analysis table:

- `Linked Tests` count is clickable when value > 0.
- Clicking opens a popup with exact linked QAUT IDs for that bug.
- Popup can be closed by:
  - Close button
  - Clicking backdrop
  - Escape key

## 5. Metrics in Bug Analysis

Top cards include:

- Total Bugs
- Open
- Critical
- High Priority
- Linked Tests (sum of linked test counts in current filtered view)

## 6. CSV from Bug Analysis

CSV export includes:

- ID
- Title
- AgileTeam
- Status
- Severity
- Linked Test Count
- Linked Sanity Count
- Linked Smoke Count
- Linked Regression Count
- Linked Test Keys
- Created
- Reporter

Export uses currently filtered rows.

## 7. Backend APIs in Use

### Core

- `GET /api/published-state`

### Test Step Distribution

- `POST /api/admin/publish-section`
- `GET /api/admin/export-csv`

### Bug Analysis

- `GET /api/admin/bug-analysis`

All admin APIs require `X-Admin-Key` header (or supported fallback where implemented).

## 8. File Structure for Current Logic

### Frontend

- `app/static/index.html`
  - Layout, tabs, section markup, popup markup, shared styles
- `app/static/app-shell.js`
  - Shared bootstrap, admin detection, fetch helpers, view-only restrictions
- `app/static/published-data.js`
  - Published Data rendering, refresh, and CSV export
- `app/static/admin-runner.js`
  - Admin Runner tab behavior, saved queries, and publish actions
- `app/static/bug-analysis.js`
  - Bug analysis behavior, filters, popup, CSV export

### Backend

- `app/main.py`
  - API routes and published state management
- `app/jira_client.py`
  - Jira fetch, issue processing, step counting, bug analysis, linked test categorization

### Run Script

- `start.ps1`
  - Loads environment from `.env`, starts app on port 3000

## 9. Snapshot Persistence

Published section snapshots are stored in:

- `app/data/published_state.json`

Each published section stores:
- JQL
- Published timestamp
- Execution time
- Agile summary data
- Issue-level rows for export

## 10. Operational Notes

- Restart application after backend code changes.
- Hard refresh browser if frontend JS changes are not reflected.
- Bug Analysis and section query saves are browser-local (per browser profile).
- API performance is improved by in-memory caching and precomputed rows.
