function queryStorageKey(testType) {
  return 'pslSavedJql:' + String(testType || '').toLowerCase();
}

function saveSectionQuery(testType, showBanner = true) {
  const key = String(testType || '').toLowerCase();
  const input = document.getElementById(key + 'Jql');
  const status = document.getElementById(key + 'RunStatus');
  const jql = (input?.value || '').trim();
  if (!jql) {
    if (status) {
      status.style.display = 'block';
      status.style.background = '#7f1d1d';
      status.style.color = '#fee2e2';
      status.textContent = 'Query is empty. Enter JQL before saving.';
    }
    return false;
  }
  localStorage.setItem(queryStorageKey(testType), jql);
  if (showBanner && status) {
    status.style.display = 'block';
    status.style.background = '#0f5132';
    status.style.color = '#d1fae5';
    status.textContent = 'Query saved locally.';
    setTimeout(() => { status.style.display = 'none'; }, 2500);
  }
  return true;
}

function loadSavedQueries() {
  for (const type of PSLDashboardState.sectionTypes) {
    const key = type.toLowerCase();
    const input = document.getElementById(key + 'Jql');
    const saved = localStorage.getItem(queryStorageKey(type)) || '';
    if (input && saved && !input.value.trim()) {
      input.value = saved;
    }
  }
}

let currentActiveTab = 'published';

function activateTab(name) {
  currentActiveTab = name;
  const published = document.getElementById('tabPublished');
  const admin = document.getElementById('tabAdmin');
  const bug = document.getElementById('tabBugAnalysis');
  const isAdminTab = name === 'admin';
  const isBugTab = name === 'bug';

  if (published) {
    published.style.background = (isAdminTab || isBugTab) ? '#475569' : '#0ea5e9';
    published.style.color = (isAdminTab || isBugTab) ? '#e2e8f0' : '#0f172a';
  }
  if (admin && PSLDashboardState.adminMode) {
    admin.style.background = isAdminTab ? '#0ea5e9' : '#475569';
    admin.style.color = isAdminTab ? '#0f172a' : '#e2e8f0';
  }
  if (bug) {
    bug.style.background = isBugTab ? '#0ea5e9' : '#475569';
    bug.style.color = isBugTab ? '#0f172a' : '#e2e8f0';
  }

  for (const type of PSLDashboardState.sectionTypes) {
    const panel = document.getElementById(type.toLowerCase() + 'AdminPanel');
    if (panel) {
      panel.style.display = (isAdminTab && PSLDashboardState.adminMode) ? 'block' : 'none';
    }
  }

  const testStepSection = document.getElementById('testStepSection');
  if (testStepSection) {
    testStepSection.style.display = isBugTab ? 'none' : 'block';
  }

  const bugAnalysisSection = document.getElementById('bugAnalysisSection');
  if (bugAnalysisSection) {
    bugAnalysisSection.style.display = isBugTab ? 'block' : 'none';
  }
}

const universalRefresh = function() {
  if (currentActiveTab === 'published' && typeof loadPublishedState === 'function') {
    loadPublishedState();
  } else if (currentActiveTab === 'admin' && PSLDashboardState.adminMode) {
    loadSavedQueries();
  } else if (currentActiveTab === 'bug') {
    if (typeof fetchBugData === 'function') {
      fetchBugData();
    }
    if (typeof fetchReopenedTestData === 'function') {
      fetchReopenedTestData();
    }
  }
};

async function publishSection(testType) {
  const key = testType.toLowerCase();
  const btn = document.getElementById('run' + testType + 'Btn');
  const status = document.getElementById(key + 'RunStatus');
  const jql = (document.getElementById(key + 'Jql')?.value || '').trim();
  const err = document.getElementById('err');
  err.style.display = 'none';

  if (!jql) {
    alert('Please enter a JQL query for ' + testType + '.');
    return;
  }
  if (!PSLDashboardState.adminMode) {
    err.style.display = 'block';
    err.textContent = 'Admin mode required.';
    return;
  }
  if (!PSLDashboardState.adminKey) {
    PSLDashboardState.adminKey = prompt('Enter admin access key:') || '';
    if (!PSLDashboardState.adminKey) {
      return;
    }
    sessionStorage.setItem('adminKey', PSLDashboardState.adminKey);
  }

  btn.disabled = true;
  status.style.display = 'block';
  status.style.background = 'rgba(56,189,248,0.1)';
  status.style.color = '#93c5fd';
  status.textContent = 'Running ' + testType + ' query...';

  try {
    const response = await postJson('/api/admin/publish-section',
      { jql, test_type: testType, refresh: true },
      900000,
      { 'X-Admin-Key': PSLDashboardState.adminKey });
    if (!response.ok) {
      throw new Error('HTTP ' + response.status + ' - ' + await response.text());
    }
    const data = await response.json();
    PSLDashboardState.lastSectionJql[key] = jql;
    saveSectionQuery(testType, false);
    renderSectionTable(testType, data.agile);
    const sub = document.getElementById(key + 'Sub');
    if (sub) {
      sub.textContent = 'Published: ' + data.published_at + ' - ' + (data.agile?.total_test_cases ?? 0) + ' test cases - ' + data.execution_time_sec + 's';
    }
    status.style.background = '#0f5132';
    status.style.color = '#d1fae5';
    status.textContent = 'Published ' + (data.agile?.total_test_cases ?? 0) + ' test cases (' + data.execution_time_sec + 's)';
    setTimeout(() => { status.style.display = 'none'; }, 5000);
  } catch (e) {
    status.style.background = '#7f1d1d';
    status.style.color = '#fee2e2';
    status.textContent = String(e.message || e);
  } finally {
    btn.disabled = false;
  }
}

function initAdminRunner() {
  document.getElementById('runSanityBtn')?.addEventListener('click', () => publishSection('Sanity'));
  document.getElementById('runSmokeBtn')?.addEventListener('click', () => publishSection('Smoke'));
  document.getElementById('runRegressionBtn')?.addEventListener('click', () => publishSection('Regression'));
  document.getElementById('saveSanityBtn')?.addEventListener('click', () => saveSectionQuery('Sanity'));
  document.getElementById('saveSmokeBtn')?.addEventListener('click', () => saveSectionQuery('Smoke'));
  document.getElementById('saveRegressionBtn')?.addEventListener('click', () => saveSectionQuery('Regression'));
  document.getElementById('tabPublished')?.addEventListener('click', () => activateTab('published'));
  document.getElementById('tabAdmin')?.addEventListener('click', () => activateTab('admin'));
  document.getElementById('tabBugAnalysis')?.addEventListener('click', () => activateTab('bug'));
  
  // Wire refresh button to universal refresh function
  document.getElementById('refresh')?.addEventListener('click', universalRefresh);

  ['sanity', 'smoke', 'regression'].forEach(key => {
    const input = document.getElementById(key + 'Jql');
    const type = key.charAt(0).toUpperCase() + key.slice(1);
    if (input) {
      input.addEventListener('keypress', event => {
        if (event.key === 'Enter') {
          publishSection(type);
        }
      });
    }
  });

  if (PSLDashboardState.adminMode) {
    const adminTab = document.getElementById('tabAdmin');
    if (adminTab) {
      adminTab.style.display = 'inline-block';
    }
  }

  activateTab('published');
  loadSavedQueries();
}

window.activateTab = activateTab;
window.universalRefresh = universalRefresh;
window.publishSection = publishSection;
window.initAdminRunner = initAdminRunner;
