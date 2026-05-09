window.PSLDashboardState = window.PSLDashboardState || {
  sectionTypes: ['Sanity', 'Smoke', 'Regression'],
  lastSectionJql: { sanity: '', smoke: '', regression: '' },
  urlParams: new URLSearchParams(window.location.search),
  adminMode: false,
  adminKey: '',
};

PSLDashboardState.adminMode = PSLDashboardState.urlParams.get('admin') === '1';
PSLDashboardState.adminKey = PSLDashboardState.urlParams.get('key') || sessionStorage.getItem('adminKey') || '';
if (PSLDashboardState.adminMode && PSLDashboardState.adminKey) {
  sessionStorage.setItem('adminKey', PSLDashboardState.adminKey);
}

function isAdminUser() {
  return PSLDashboardState.adminMode;
}

async function fetchWithTimeout(url, ms = 300000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ms);
  try {
    return await fetch(url, { signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

async function postJson(url, payload, ms = 900000, headers = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ms);
  try {
    return await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...headers },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timer);
  }
}

function restrictAdminControls() {
  if (isAdminUser()) {
    return;
  }

  const controlsToHide = [
    'tabAdmin',
    'runSanityBtn', 'saveSanityBtn',
    'runSmokeBtn', 'saveSmokeBtn',
    'runRegressionBtn', 'saveRegressionBtn',
    'bugJql', 'bugRunBtn', 'bugSaveBtn',
    'reopenedJql', 'runReopenedBtn', 'saveReopenedBtn',
  ];

  controlsToHide.forEach(id => {
    const elem = document.getElementById(id);
    if (elem) {
      elem.style.display = 'none';
    }
  });

  const bugExport = document.getElementById('bugExportBtn');
  if (bugExport) {
    bugExport.style.display = 'inline-block';
  }

  const tabBar = document.getElementById('tabBar');
  if (tabBar && !document.getElementById('viewOnlyNote')) {
    const note = document.createElement('div');
    note.id = 'viewOnlyNote';
    note.style.cssText = 'color: #94a3b8; font-size: 12px; margin: -8px 0 16px; padding: 8px; background: rgba(15, 23, 42, 0.5); border-radius: 6px; border-left: 3px solid #64748b;';
    note.textContent = 'View-only mode. Published data only.';
    tabBar.insertAdjacentElement('afterend', note);
  }
}

document.addEventListener('DOMContentLoaded', function () {
  restrictAdminControls();
  initPublishedData();
  initAdminRunner();
  initBugAnalysis();
  if (typeof initExecutiveDashboard === 'function') {
    initExecutiveDashboard();
  }
});

window.isAdminUser = isAdminUser;
window.fetchWithTimeout = fetchWithTimeout;
window.postJson = postJson;
window.restrictAdminControls = restrictAdminControls;
