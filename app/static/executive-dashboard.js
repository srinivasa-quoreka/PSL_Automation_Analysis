const ExecutiveState = {
  targets: {
    sanity: 250,
    smoke: 600,
    regression: 3000,
  },
  jql: {
    backlog: 'project in (QA-Automation) AND issuetype = Test',
    bugs: 'issueFunction in linkedIssuesOf("project = QA-Automation AND issuetype = Test") AND issuetype = Bug',
  },
  chart: null,
};

function executiveTargetsStorageKey() {
  return 'pslExecutiveTargets:v1';
}

function loadExecutiveTargets() {
  try {
    const raw = localStorage.getItem(executiveTargetsStorageKey());
    if (!raw) return;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return;
    for (const key of ['sanity', 'smoke', 'regression']) {
      const n = Number(parsed[key]);
      if (Number.isFinite(n) && n >= 0) {
        ExecutiveState.targets[key] = Math.round(n);
      }
    }
    if (typeof parsed.backlogJql === 'string' && parsed.backlogJql.trim()) {
      ExecutiveState.jql.backlog = parsed.backlogJql.trim();
    }
    if (typeof parsed.bugJql === 'string' && parsed.bugJql.trim()) {
      ExecutiveState.jql.bugs = parsed.bugJql.trim();
    }
  } catch (_e) {
    // Ignore malformed local storage values.
  }
}

function writeTargetsToInputs() {
  const sanity = document.getElementById('targetSanity');
  const smoke = document.getElementById('targetSmoke');
  const regression = document.getElementById('targetRegression');
  const backlogJql = document.getElementById('execBacklogJql');
  const bugJql = document.getElementById('execBugJql');
  if (sanity) sanity.value = String(ExecutiveState.targets.sanity);
  if (smoke) smoke.value = String(ExecutiveState.targets.smoke);
  if (regression) regression.value = String(ExecutiveState.targets.regression);
  if (backlogJql) backlogJql.value = ExecutiveState.jql.backlog;
  if (bugJql) bugJql.value = ExecutiveState.jql.bugs;
}

function readTargetsFromInputs() {
  const sanity = Number(document.getElementById('targetSanity')?.value || 0);
  const smoke = Number(document.getElementById('targetSmoke')?.value || 0);
  const regression = Number(document.getElementById('targetRegression')?.value || 0);
  const backlogJql = (document.getElementById('execBacklogJql')?.value || '').trim();
  const bugJql = (document.getElementById('execBugJql')?.value || '').trim();

  ExecutiveState.targets.sanity = Number.isFinite(sanity) && sanity >= 0 ? Math.round(sanity) : 0;
  ExecutiveState.targets.smoke = Number.isFinite(smoke) && smoke >= 0 ? Math.round(smoke) : 0;
  ExecutiveState.targets.regression = Number.isFinite(regression) && regression >= 0 ? Math.round(regression) : 0;
  if (backlogJql) {
    ExecutiveState.jql.backlog = backlogJql;
  }
  if (bugJql) {
    ExecutiveState.jql.bugs = bugJql;
  }
}

function saveExecutiveTargets() {
  const status = document.getElementById('execStatus');
  readTargetsFromInputs();
  localStorage.setItem(executiveTargetsStorageKey(), JSON.stringify({
    ...ExecutiveState.targets,
    backlogJql: ExecutiveState.jql.backlog,
    bugJql: ExecutiveState.jql.bugs,
  }));
  if (status) {
    status.style.display = 'block';
    status.style.background = '#0f5132';
    status.style.color = '#d1fae5';
    status.textContent = 'Executive report config saved.';
    setTimeout(() => { status.style.display = 'none'; }, 2500);
  }
  loadExecutiveCoverageReport();
}

function getAutomatedCount(snapshot, key) {
  const section = snapshot?.[key];
  if (section?.agile?.total_test_cases != null) {
    return Number(section.agile.total_test_cases) || 0;
  }
  if (section?.agile?.total_row?.total_test_cases != null) {
    return Number(section.agile.total_row.total_test_cases) || 0;
  }

  const legacyKey = key + '_agile';
  const legacy = snapshot?.[legacyKey];
  if (legacy?.total_test_cases != null) {
    return Number(legacy.total_test_cases) || 0;
  }
  if (legacy?.total_row?.total_test_cases != null) {
    return Number(legacy.total_row.total_test_cases) || 0;
  }

  const rows = section?.agile?.rows || legacy?.rows || [];
  if (!Array.isArray(rows)) return 0;
  return rows.reduce((sum, row) => sum + (Number(row?.total_test_cases) || 0), 0);
}

function percent(numerator, denominator) {
  if (!denominator) return 0;
  return Math.round((numerator / denominator) * 1000) / 10;
}

function renderExecutiveKpis(report) {
  const wrap = document.getElementById('execKpis');
  if (!wrap) return;

  wrap.innerHTML = `
    <div class="stat">
      <div class="v">${report.totalBacklog}</div>
      <div class="l">Total Backlog</div>
    </div>
    <div class="stat">
      <div class="v">${report.totalAutomated}</div>
      <div class="l">Automated</div>
    </div>
    <div class="stat">
      <div class="v">${report.totalRemaining}</div>
      <div class="l">Remaining</div>
    </div>
    <div class="stat">
      <div class="v">${report.totalCoverage.toFixed(1)}%</div>
      <div class="l">Coverage</div>
    </div>
    <div class="stat">
      <div class="v">${report.totalLinkedBugs}</div>
      <div class="l">Linked Bugs</div>
    </div>
  `;
}

function renderExecutiveTable(report) {
  const body = document.getElementById('execCoverageRows');
  if (!body) return;

  body.innerHTML = '';
  for (const row of report.rows) {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${row.label}</td>
      <td class="n">${row.backlog}</td>
      <td class="n">${row.automated}</td>
      <td class="n">${row.remaining}</td>
      <td class="n">${row.coverage.toFixed(1)}%</td>
    `;
    body.appendChild(tr);
  }

  const totalTr = document.createElement('tr');
  totalTr.style.fontWeight = '700';
  totalTr.innerHTML = `
    <td>TOTAL</td>
    <td class="n">${report.totalBacklog}</td>
    <td class="n">${report.totalAutomated}</td>
    <td class="n">${report.totalRemaining}</td>
    <td class="n">${report.totalCoverage.toFixed(1)}%</td>
  `;
  body.appendChild(totalTr);
}

function renderExecutiveChart(report) {
  const canvas = document.getElementById('execCoverageChart');
  if (!canvas || typeof Chart === 'undefined') return;

  const labels = report.rows.map(r => r.label);
  const automated = report.rows.map(r => r.automated);
  const remaining = report.rows.map(r => r.remaining);

  if (ExecutiveState.chart) {
    ExecutiveState.chart.destroy();
  }

  ExecutiveState.chart = new Chart(canvas, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: 'Automated',
          data: automated,
          backgroundColor: '#4a90e2',
        },
        {
          label: 'Remaining',
          data: remaining,
          backgroundColor: '#2a4c70',
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: { color: '#ffffff' },
        },
      },
      scales: {
        x: {
          ticks: { color: '#a8bcc9' },
          grid: { color: '#1f3a52' },
        },
        y: {
          ticks: { color: '#a8bcc9' },
          grid: { color: '#1f3a52' },
          beginAtZero: true,
        },
      },
    },
  });
}

async function loadExecutiveCoverageReport() {
  const status = document.getElementById('execStatus');
  try {
    if (status) {
      status.style.display = 'block';
      status.style.background = 'rgba(56,189,248,0.1)';
      status.style.color = '#93c5fd';
      status.textContent = 'Loading program coverage report...';
    }

    readTargetsFromInputs();

    const snapshotRes = await fetchWithTimeout('/api/published-state', 180000);
    if (!snapshotRes.ok) {
      throw new Error('HTTP ' + snapshotRes.status);
    }
    const snapshot = await snapshotRes.json();

    // Source backlog counts from Jira with the provided "all tests" JQL.
    const backlogJql = ExecutiveState.jql.backlog;
    let backlogByType = {
      sanity: ExecutiveState.targets.sanity,
      smoke: ExecutiveState.targets.smoke,
      regression: ExecutiveState.targets.regression,
    };

    if (PSLDashboardState?.adminMode && backlogJql) {
      const typeQuery = new URLSearchParams({ jql: backlogJql, refresh: 'false' });
      const typeRes = await fetch('/api/test-type-counts?' + typeQuery.toString(), {
        headers: { 'X-Admin-Key': sessionStorage.getItem('adminKey') || PSLDashboardState.adminKey || '' }
      });
      if (typeRes.ok) {
        const typeData = await typeRes.json();
        const types = Array.isArray(typeData.types) ? typeData.types : [];
        const getCount = (name) => {
          const hit = types.find(t => String(t.test_type || '').toLowerCase() === name);
          return Number(hit?.count || 0);
        };
        backlogByType = {
          sanity: getCount('sanity'),
          smoke: getCount('smoke'),
          regression: getCount('regression'),
        };
      }
    }

    const sanityAutomated = getAutomatedCount(snapshot, 'sanity');
    const smokeAutomated = getAutomatedCount(snapshot, 'smoke');
    const regressionAutomated = getAutomatedCount(snapshot, 'regression');

    const rows = [
      {
        key: 'sanity',
        label: 'Sanity',
        backlog: backlogByType.sanity,
        automated: sanityAutomated,
      },
      {
        key: 'smoke',
        label: 'Smoke',
        backlog: backlogByType.smoke,
        automated: smokeAutomated,
      },
      {
        key: 'regression',
        label: 'Regression',
        backlog: backlogByType.regression,
        automated: regressionAutomated,
      },
    ].map(r => {
      const remaining = Math.max(r.backlog - r.automated, 0);
      return {
        ...r,
        remaining,
        coverage: percent(r.automated, r.backlog),
      };
    });

    const totalBacklog = rows.reduce((s, r) => s + r.backlog, 0);
    const totalAutomated = rows.reduce((s, r) => s + r.automated, 0);
    const totalRemaining = rows.reduce((s, r) => s + r.remaining, 0);
    const totalCoverage = percent(totalAutomated, totalBacklog);

    // Source linked bug total from Jira using provided bug query.
    let totalLinkedBugs = 0;
    const bugJql = ExecutiveState.jql.bugs;
    if (PSLDashboardState?.adminMode && bugJql) {
      const bugQuery = new URLSearchParams({ jql: bugJql, refresh: 'false' });
      const bugRes = await fetch('/api/admin/bug-analysis?' + bugQuery.toString(), {
        headers: { 'X-Admin-Key': sessionStorage.getItem('adminKey') || PSLDashboardState.adminKey || '' }
      });
      if (bugRes.ok) {
        const bugData = await bugRes.json();
        totalLinkedBugs = Number(bugData.total_bugs || (Array.isArray(bugData.rows) ? bugData.rows.length : 0) || 0);
      }
    }

    const report = {
      rows,
      totalBacklog,
      totalAutomated,
      totalRemaining,
      totalCoverage,
      totalLinkedBugs,
    };

    renderExecutiveKpis(report);
    renderExecutiveTable(report);
    renderExecutiveChart(report);

    if (status) {
      status.style.background = '#0f5132';
      status.style.color = '#d1fae5';
      status.textContent = 'Executive coverage report loaded.';
      setTimeout(() => { status.style.display = 'none'; }, 3000);
    }
  } catch (e) {
    if (status) {
      status.style.display = 'block';
      status.style.background = '#7f1d1d';
      status.style.color = '#fee2e2';
      status.textContent = 'Failed to load report: ' + String(e.message || e);
    }
  }
}

function initExecutiveDashboard() {
  loadExecutiveTargets();
  writeTargetsToInputs();
  document.getElementById('saveCoverageTargetsBtn')?.addEventListener('click', saveExecutiveTargets);
  document.getElementById('reloadExecutiveBtn')?.addEventListener('click', loadExecutiveCoverageReport);
}

window.loadExecutiveCoverageReport = loadExecutiveCoverageReport;
window.initExecutiveDashboard = initExecutiveDashboard;
