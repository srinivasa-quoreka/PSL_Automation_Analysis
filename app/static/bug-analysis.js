/**
 * Bug Analysis - Analyzes and visualizes bug metrics and trends
 * Supports bug filtering by AgileTeam, status, severity, and date range
 */

const BugAnalysisState = {
  bugsCache: [],
  filteredBugs: [],
  reopenedRows: [],
  currentFilter: {
    team: '',
    status: '',
    severity: '',
    dateFrom: '',
    dateTo: ''
  },
  defaultJql: 'issueFunction in linkedIssuesOf("project = QA-Automation AND issuetype = Test") AND issuetype = Bug',
  defaultReopenedJql: 'project in (QA-Automation) AND issuetype = Test AND status changed to Re-opened'
};

function isBugAnalysisAdminMode() {
  const urlParams = new URLSearchParams(window.location.search);
  const adminMode = urlParams.get('admin') === '1';
  const adminKey = sessionStorage.getItem('adminKey') || urlParams.get('key') || '';
  return adminMode && !!adminKey;
}

function bugQueryStorageKey() {
  return 'pslSavedJql:bug-analysis';
}

function getBugQuery() {
  const input = document.getElementById('bugJql');
  return (input?.value || BugAnalysisState.defaultJql || '').trim();
}

function saveBugQuery(showBanner = true) {
  const status = document.getElementById('bugLoadStatus');
  const jql = getBugQuery();
  if (!jql) {
    if (status) {
      status.style.display = 'block';
      status.style.background = '#7f1d1d';
      status.style.color = '#fee2e2';
      status.textContent = 'Query is empty. Enter JQL before saving.';
    }
    return false;
  }
  localStorage.setItem(bugQueryStorageKey(), jql);
  BugAnalysisState.defaultJql = jql;
  if (showBanner && status) {
    status.style.display = 'block';
    status.style.background = '#0f5132';
    status.style.color = '#d1fae5';
    status.textContent = 'Query saved locally.';
    setTimeout(() => { status.style.display = 'none'; }, 2500);
  }
  return true;
}

function loadBugQuery() {
  const input = document.getElementById('bugJql');
  const saved = localStorage.getItem(bugQueryStorageKey()) || BugAnalysisState.defaultJql;
  if (input) {
    input.value = saved;
  }
  BugAnalysisState.defaultJql = saved;
}

function reopenedQueryStorageKey() {
  return 'pslSavedJql:reopened-test-analysis';
}

function loadReopenedQuery() {
  const input = document.getElementById('reopenedJql');
  const saved = localStorage.getItem(reopenedQueryStorageKey()) || BugAnalysisState.defaultReopenedJql;
  if (input) {
    input.value = saved;
  }
  BugAnalysisState.defaultReopenedJql = saved;
}

function saveReopenedQuery(showBanner = true) {
  const status = document.getElementById('reopenedStatus');
  const jql = getReopenedQuery();
  if (!jql) {
    if (status) {
      status.style.display = 'block';
      status.style.background = '#7f1d1d';
      status.style.color = '#fee2e2';
      status.textContent = 'Query is empty. Enter JQL before saving.';
    }
    return false;
  }
  localStorage.setItem(reopenedQueryStorageKey(), jql);
  BugAnalysisState.defaultReopenedJql = jql;
  if (showBanner && status) {
    status.style.display = 'block';
    status.style.background = '#0f5132';
    status.style.color = '#d1fae5';
    status.textContent = 'Re-opened query saved locally.';
    setTimeout(() => { status.style.display = 'none'; }, 2500);
  }
  return true;
}

function getReopenedQuery() {
  const input = document.getElementById('reopenedJql');
  return (input?.value || BugAnalysisState.defaultReopenedJql || '').trim();
}

async function fetchBugData() {
  const err = document.getElementById('err');
  try {
    err.style.display = 'none';
    const status = document.getElementById('bugLoadStatus');
    if (status) {
      status.style.display = 'block';
      status.style.background = 'rgba(56,189,248,0.1)';
      status.style.color = '#93c5fd';
      status.textContent = '⏳ Loading bug data…';
    }

    const isAdmin = isBugAnalysisAdminMode();
    const activeJql = getBugQuery();
    let res;
    if (isAdmin) {
      if (!activeJql) {
        throw new Error('JQL is required for Bug Analysis.');
      }
      const query = new URLSearchParams({ jql: activeJql });
      res = await fetch('/api/admin/bug-analysis?' + query.toString(), {
        headers: { 'X-Admin-Key': sessionStorage.getItem('adminKey') || '' }
      });
    } else {
      res = await fetch('/api/bug-analysis');
    }
    if (!res.ok) {
      throw new Error('HTTP ' + res.status + ' - ' + await res.text());
    }
    const data = await res.json();
    if (isAdmin) {
      BugAnalysisState.defaultJql = activeJql;
      localStorage.setItem(bugQueryStorageKey(), activeJql);
    }
    BugAnalysisState.bugsCache = Array.isArray(data.rows) ? data.rows : [];

    // Populate AgileTeam dropdown with distinct teams from loaded bugs
    populateBugTeamDropdown();

    // Always apply current UI filters so default status filter is respected on initial load.
    applyBugFilter();

    if (status) {
      status.style.background = '#0f5132';
      status.style.color = '#d1fae5';
      status.textContent = '✓ Bug data loaded! (' + BugAnalysisState.bugsCache.length + ' bugs)';
      setTimeout(() => { status.style.display = 'none'; }, 4000);
    }
  } catch (e) {
    if (err) {
      err.style.display = 'block';
      err.style.background = '#7f1d1d';
      err.style.color = '#fee2e2';
      err.textContent = 'Failed to load bug data: ' + (e.message || e);
    }
  }
}

function renderBugAnalysisDashboard(bugs) {
  const metricsContainer = document.getElementById('bugMetrics');
  const tableContainer = document.getElementById('bugTableBody');

  if (!metricsContainer || !tableContainer) return;

  // Calculate metrics
  const totalBugs = bugs.length;
  const openBugs = bugs.filter(b => b.status === 'Open').length;
  const criticalBugs = bugs.filter(b => b.severity === 'Critical').length;
  const highBugs = bugs.filter(b => b.severity === 'High').length;
  const linkedTests = bugs.reduce((sum, bug) => sum + Number(bug.linkedTestCount || 0), 0);

  // Render metrics cards
  metricsContainer.innerHTML = `
    <div class="stat">
      <div class="v">${totalBugs}</div>
      <div class="l">Total Bugs</div>
    </div>
    <div class="stat">
      <div class="v" style="color: #ff6b6b;">${openBugs}</div>
      <div class="l">Open</div>
    </div>
    <div class="stat">
      <div class="v" style="color: #ff0000;">${criticalBugs}</div>
      <div class="l">Critical</div>
    </div>
    <div class="stat">
      <div class="v" style="color: #ff9800;">${highBugs}</div>
      <div class="l">High Priority</div>
    </div>
    <div class="stat">
      <div class="v" style="color: #38bdf8;">${linkedTests}</div>
      <div class="l">Linked Tests</div>
    </div>
  `;

  // Render bug table
  tableContainer.innerHTML = '';
  for (const bug of bugs) {
    const severityColor = {
      'Critical': '#ff0000',
      'High': '#ff9800',
      'Medium': '#ffeb3b',
      'Low': '#4caf50'
    }[bug.severity] || '#94a3b8';

    const statusColor = {
      'Open': '#ff6b6b',
      'In Progress': '#93c5fd',
      'Closed': '#4caf50'
    }[bug.status] || '#94a3b8';

    const row = document.createElement('tr');
    const linkedTitle = Array.isArray(bug.linkedTestKeys) && bug.linkedTestKeys.length
      ? bug.linkedTestKeys.join(', ')
      : 'No linked QAUT tests';
    const linkedCount = Number(bug.linkedTestCount || 0);
    const linkedAttr = encodeURIComponent(JSON.stringify(Array.isArray(bug.linkedTestKeys) ? bug.linkedTestKeys : []));
    row.innerHTML = `
      <td class="k">${bug.id}</td>
      <td>${bug.title}</td>
      <td>${bug.agileTeam}</td>
      <td><span style="background:${statusColor}; color:#0f172a; padding:3px 8px; border-radius:4px; font-size:11px; font-weight:600;">${bug.status}</span></td>
      <td><span style="background:${severityColor}; color:#0f172a; padding:3px 8px; border-radius:4px; font-size:11px; font-weight:600;">${bug.severity}</span></td>
      <td class="n" title="${linkedTitle}">
        <button
          type="button"
          class="link-count-btn"
          data-bug-id="${bug.id}"
          data-linked-tests="${linkedAttr}"
          ${linkedCount ? '' : 'disabled'}
        >${linkedCount}</button>
      </td>
      <td class="n">${Number(bug.linkedSanityCount || 0)}</td>
      <td class="n">${Number(bug.linkedSmokeCount || 0)}</td>
      <td class="n">${Number(bug.linkedRegressionCount || 0)}</td>
      <td style="font-size:12px;">${bug.createdAt}</td>
    `;
    tableContainer.appendChild(row);
  }
}

function openLinkedTestsModal(bugId, linkedTestKeys) {
  const modal = document.getElementById('linkedTestsModal');
  const subtitle = document.getElementById('linkedTestsSubtitle');
  const empty = document.getElementById('linkedTestsEmpty');
  const list = document.getElementById('linkedTestsList');
  if (!modal || !subtitle || !empty || !list) {
    return;
  }

  const items = Array.isArray(linkedTestKeys) ? linkedTestKeys : [];
  subtitle.textContent = `${bugId} · ${items.length} linked QAUT test case${items.length === 1 ? '' : 's'}`;
  list.innerHTML = '';

  if (!items.length) {
    empty.style.display = 'block';
    list.style.display = 'none';
  } else {
    empty.style.display = 'none';
    list.style.display = 'grid';
    for (const key of items) {
      const item = document.createElement('div');
      item.className = 'linked-test-item';
      item.innerHTML = `
        <span class="linked-test-key">${key}</span>
        <span class="modal-sub">Linked via Bug of</span>
      `;
      list.appendChild(item);
    }
  }

  modal.style.display = 'flex';
}

function closeLinkedTestsModal() {
  const modal = document.getElementById('linkedTestsModal');
  if (modal) {
    modal.style.display = 'none';
  }
}

function renderReopenedTestTable(rows, summaryData = {}) {
  const head = document.getElementById('reopenedTableHead');
  const body = document.getElementById('reopenedTableBody');
  const wrap = document.getElementById('reopenedTableWrap');
  const empty = document.getElementById('reopenedTableEmpty');
  const summary = document.getElementById('reopenedSummary');
  if (!head || !body || !wrap || !empty || !summary) {
    return;
  }

  const totalCases = Number(summaryData.total_test_cases || 0);
  const totalReopens = Number(summaryData.total_reopen_events || 0);
  const ignoredLabel = String(summaryData.ignored_label || 'Automation_TCs');
  summary.textContent = `Total re-opened test cases: ${totalCases} · Total re-open events: ${totalReopens} · Ignored label: ${ignoredLabel}`;

  const teams = Array.isArray(summaryData.team_names) ? summaryData.team_names : [];
  const matrixRows = Array.isArray(summaryData.matrix_rows) ? summaryData.matrix_rows : [];
  const totalRow = summaryData.matrix_total_row || null;

  const teamHeaders = teams.map(team => `<th style="text-align:center;">${team}</th>`).join('');
  head.innerHTML = `
    <tr>
      <th style="text-align:left; min-width:220px;">Labels</th>
      ${teamHeaders}
      <th style="text-align:center; min-width:130px;">Total count</th>
    </tr>
  `;

  if (!matrixRows.length) {
    body.innerHTML = '';
    wrap.style.display = 'none';
    empty.style.display = 'block';
    return;
  }

  body.innerHTML = '';
  for (const row of matrixRows) {
    const perTeam = row.per_team || {};
    const teamCells = teams.map(team => `<td class="n">${Number(perTeam[team] || 0)}</td>`).join('');
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${row.label || ''}</td>
      ${teamCells}
      <td class="n">${Number(row.total_unique_issues || 0)}</td>
    `;
    body.appendChild(tr);
  }

  if (totalRow && typeof totalRow === 'object') {
    const totalPerTeam = totalRow.per_team || {};
    const teamTotalCells = teams.map(team => `<td class="n">${Number(totalPerTeam[team] || 0)}</td>`).join('');
    const totalTr = document.createElement('tr');
    totalTr.style.fontWeight = '700';
    totalTr.innerHTML = `
      <td>${totalRow.label || 'Total count'}</td>
      ${teamTotalCells}
      <td class="n">${Number(totalRow.total_unique_issues || 0)}</td>
    `;
    body.appendChild(totalTr);
  }

  empty.style.display = 'none';
  wrap.style.display = 'block';
}

async function fetchReopenedTestData() {
  const err = document.getElementById('err');
  const status = document.getElementById('reopenedStatus');
  try {
    if (err) {
      err.style.display = 'none';
    }
    if (status) {
      status.style.display = 'block';
      status.style.background = 'rgba(56,189,248,0.1)';
      status.style.color = '#93c5fd';
      status.textContent = '⏳ Running re-opened test case analysis…';
    }

    const isAdmin = isBugAnalysisAdminMode();
    const jql = getReopenedQuery();
    let res;
    if (isAdmin) {
      if (!jql) {
        throw new Error('JQL is required for Re-opened Test Case Analysis.');
      }
      localStorage.setItem(reopenedQueryStorageKey(), jql);
      BugAnalysisState.defaultReopenedJql = jql;
      const params = new URLSearchParams({ jql });
      res = await fetch('/api/admin/reopened-test-analysis?' + params.toString(), {
        headers: { 'X-Admin-Key': sessionStorage.getItem('adminKey') || '' }
      });
    } else {
      res = await fetch('/api/reopened-test-analysis');
    }
    if (!res.ok) {
      throw new Error('HTTP ' + res.status + ' - ' + await res.text());
    }

    const data = await res.json();
    BugAnalysisState.reopenedRows = Array.isArray(data.rows) ? data.rows : [];
    renderReopenedTestTable(BugAnalysisState.reopenedRows, data);

    if (status) {
      status.style.background = '#0f5132';
      status.style.color = '#d1fae5';
      status.textContent = `✓ Re-opened analysis loaded (${BugAnalysisState.reopenedRows.length} test cases).`;
      setTimeout(() => { status.style.display = 'none'; }, 4500);
    }
  } catch (e) {
    if (status) {
      status.style.background = '#7f1d1d';
      status.style.color = '#fee2e2';
      status.textContent = '✗ ' + String(e.message || e);
    }
    if (err) {
      err.style.display = 'block';
      err.style.background = '#7f1d1d';
      err.style.color = '#fee2e2';
      err.textContent = String(e.message || e);
    }
  }
}

function applyBugFilter() {
  const teamFilter = (document.getElementById('bugTeamFilter')?.value || '').trim();
  const testTypeFilter = (document.getElementById('bugTestTypeFilter')?.value || '').trim();
  const statusFilter = (document.getElementById('bugStatusFilter')?.value || '').trim().toLowerCase();
  const severityFilter = (document.getElementById('bugSeverityFilter')?.value || '').trim().toLowerCase();

  let filtered = BugAnalysisState.bugsCache.slice();

  // Filter by AgileTeam (exact match from dropdown)
  if (teamFilter) {
    filtered = filtered.filter(b => b.agileTeam === teamFilter);
  }

  // Filter by Test Type
  if (testTypeFilter) {
    filtered = filtered.filter(b => {
      if (testTypeFilter === 'Sanity') {
        return Number(b.linkedSanityCount || 0) > 0;
      } else if (testTypeFilter === 'Smoke') {
        return Number(b.linkedSmokeCount || 0) > 0;
      } else if (testTypeFilter === 'Regression') {
        return Number(b.linkedRegressionCount || 0) > 0;
      }
      return true;
    });
  }

  if (statusFilter) {
    filtered = filtered.filter(b => b.status.toLowerCase() === statusFilter);
  }
  if (severityFilter) {
    filtered = filtered.filter(b => b.severity.toLowerCase().includes(severityFilter));
  }

  BugAnalysisState.filteredBugs = filtered;
  renderBugAnalysisDashboard(filtered);
}

function populateBugTeamDropdown() {
  const dropdown = document.getElementById('bugTeamFilter');
  if (!dropdown) return;

  // Extract distinct teams from bugsCache
  const teams = new Set(BugAnalysisState.bugsCache.map(b => b.agileTeam).filter(t => t));
  const sortedTeams = Array.from(teams).sort();

  // Preserve current selection
  const currentValue = dropdown.value;

  // Clear and rebuild options
  dropdown.innerHTML = '<option value="">All Teams</option>';
  for (const team of sortedTeams) {
    const option = document.createElement('option');
    option.value = team;
    option.textContent = team;
    dropdown.appendChild(option);
  }

  // Restore selection if still valid
  if (currentValue && sortedTeams.includes(currentValue)) {
    dropdown.value = currentValue;
  }
}

function downloadBugsCsv() {
  const err = document.getElementById('err');
  try {
    err.style.display = 'none';
    if (!BugAnalysisState.filteredBugs || !BugAnalysisState.filteredBugs.length) {
      throw new Error('No bug data to export.');
    }

    const csv = ['ID,Title,AgileTeam,Status,Severity,Linked Test Count,Linked Sanity Count,Linked Smoke Count,Linked Regression Count,Linked Test Keys,Created,Reporter'];
    for (const bug of BugAnalysisState.filteredBugs) {
      const title = (bug.title || '').replace(/"/g, '""');
      const linkedKeys = Array.isArray(bug.linkedTestKeys) ? bug.linkedTestKeys.join(', ') : '';
      csv.push(`"${bug.id}","${title}","${bug.agileTeam}","${bug.status}","${bug.severity}","${bug.linkedTestCount || 0}","${bug.linkedSanityCount || 0}","${bug.linkedSmokeCount || 0}","${bug.linkedRegressionCount || 0}","${linkedKeys}","${bug.createdAt}","${bug.reporter}"`);
    }

    const blob = new Blob([csv.join('\n')], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'bugs-export-' + new Date().toISOString().split('T')[0] + '.csv';
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 30000);

    err.style.display = 'block';
    err.style.background = '#0f5132';
    err.style.color = '#d1fae5';
    err.textContent = 'Bug export started (' + BugAnalysisState.filteredBugs.length + ' bugs).';
  } catch (e) {
    err.style.display = 'block';
    err.style.background = '#7f1d1d';
    err.style.color = '#fee2e2';
    err.textContent = String(e.message || e);
  }
}

function initBugAnalysis() {
  loadBugQuery();
  loadReopenedQuery();

  const statusFilter = document.getElementById('bugStatusFilter');
  if (statusFilter && !statusFilter.value) {
    statusFilter.value = 'Open';
  }

  // Wire filter buttons
  const filterBtn = document.getElementById('bugFilterBtn');
  if (filterBtn) {
    filterBtn.addEventListener('click', applyBugFilter);
  }

  const loadBtn = document.getElementById('bugLoadBtn');
  if (loadBtn) {
    loadBtn.addEventListener('click', fetchBugData);
  }

  const runBtn = document.getElementById('bugRunBtn');
  if (runBtn) {
    runBtn.addEventListener('click', fetchBugData);
  }

  const runReopenedBtn = document.getElementById('runReopenedBtn');
  if (runReopenedBtn) {
    runReopenedBtn.addEventListener('click', fetchReopenedTestData);
  }

  const saveReopenedBtn = document.getElementById('saveReopenedBtn');
  if (saveReopenedBtn) {
    saveReopenedBtn.addEventListener('click', () => saveReopenedQuery(true));
  }

  const saveBtn = document.getElementById('bugSaveBtn');
  if (saveBtn) {
    saveBtn.addEventListener('click', () => saveBugQuery(true));
  }

  const exportBtn = document.getElementById('bugExportBtn');
  if (exportBtn) {
    exportBtn.addEventListener('click', downloadBugsCsv);
  }

  const tableBody = document.getElementById('bugTableBody');
  if (tableBody) {
    tableBody.addEventListener('click', event => {
      const button = event.target.closest('.link-count-btn');
      if (!button || button.disabled) {
        return;
      }
      const bugId = button.getAttribute('data-bug-id') || '';
      const raw = button.getAttribute('data-linked-tests') || '';
      let linkedTests = [];
      try {
        linkedTests = JSON.parse(decodeURIComponent(raw));
      } catch (_error) {
        linkedTests = [];
      }
      openLinkedTestsModal(bugId, linkedTests);
    });
  }

  const closeBtn = document.getElementById('linkedTestsCloseBtn');
  if (closeBtn) {
    closeBtn.addEventListener('click', closeLinkedTestsModal);
  }

  const modal = document.getElementById('linkedTestsModal');
  if (modal) {
    modal.addEventListener('click', event => {
      if (event.target === modal) {
        closeLinkedTestsModal();
      }
    });
  }

  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
      closeLinkedTestsModal();
    }
  });

  const jqlInput = document.getElementById('bugJql');
  if (jqlInput) {
    jqlInput.addEventListener('keypress', e => {
      if (e.key === 'Enter') {
        fetchBugData();
      }
    });
  }

  const reopenedInput = document.getElementById('reopenedJql');
  if (reopenedInput) {
    reopenedInput.addEventListener('keypress', e => {
      if (e.key === 'Enter') {
        fetchReopenedTestData();
      }
    });
  }

  // Load bug data on init
  fetchBugData();
  fetchReopenedTestData();
}
