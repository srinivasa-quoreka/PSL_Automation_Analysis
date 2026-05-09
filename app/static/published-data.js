function renderSectionTable(testType, agileData) {
  const key = testType.toLowerCase();
  const body = document.getElementById(key + 'TableBody');
  const wrap = document.getElementById(key + 'TableWrap');
  const empty = document.getElementById(key + 'TableEmpty');
  const controls = document.getElementById(key + 'ExportControls');

  if (!body || !wrap || !empty || !controls) {
    return;
  }

  if (!agileData || !agileData.rows || !agileData.rows.length) {
    wrap.style.display = 'none';
    empty.style.display = 'block';
    controls.style.display = 'none';
    return;
  }

  controls.style.display = 'flex';
  body.innerHTML = '';

  function makeRow(row, isBold) {
    const enc = encodeURIComponent(row.agile_team || '');
    const csvBtn = `<button style="padding:4px 8px;font-size:12px;" onclick="downloadSectionCsv('${testType}','${enc}')">CSV</button>`;
    const tr = document.createElement('tr');
    if (isBold) {
      tr.style.fontWeight = '700';
    }
    tr.innerHTML = `
      <td>${row.agile_team}</td>
      <td class="n">${row.total_test_cases || 0}</td>
      <td class="n">${row.r_0_20 || 0}</td><td class="n">${row.r_21_40 || 0}</td>
      <td class="n">${row.r_41_60 || 0}</td><td class="n">${row.r_61_80 || 0}</td>
      <td class="n">${row.r_81_100 || 0}</td><td class="n">${row.r_101_120 || 0}</td>
      <td class="n">${row.r_121_150 || 0}</td><td class="n">${row.r_151_plus || 0}</td>
      <td>${csvBtn}</td>`;
    return tr;
  }

  for (const row of agileData.rows) {
    body.appendChild(makeRow(row, false));
  }
  if (agileData.total_row) {
    body.appendChild(makeRow(agileData.total_row, true));
  }

  if (agileData.is_capped) {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td colspan="11" style="color:var(--muted);font-size:12px;">Note: capped at ${agileData.phase2_max_results} test cases.</td>`;
    body.appendChild(tr);
  }

  empty.style.display = 'none';
  wrap.style.display = 'block';
}

async function downloadSectionCsv(testType, encodedTeam) {
  const key = testType.toLowerCase();
  const err = document.getElementById('err');
  try {
    err.style.display = 'none';
    err.textContent = '';

    const jql = PSLDashboardState.lastSectionJql[key] || '';
    if (!jql && PSLDashboardState.adminMode) {
      throw new Error('No published data for ' + testType + '. Run & Publish first.');
    }

    const rangeKey = (document.getElementById(key + 'ExportRange')?.value || '').trim();
    const team = decodeURIComponent(encodedTeam || '');
    const params = new URLSearchParams({ test_type: testType });
    if (PSLDashboardState.adminMode && jql) {
      params.set('jql', jql);
    }
    if (team) {
      params.set('team', team);
    }
    if (rangeKey) {
      params.set('range_key', rangeKey);
    }

    const selectedTeam = team || 'all-teams';
    const selectedRange = rangeKey || 'all-ranges';
    err.style.display = 'block';
    err.style.background = '#1e3a5f';
    err.style.color = '#93c5fd';
    err.textContent = 'Preparing CSV for ' + testType + ' - ' + selectedTeam + ' (' + selectedRange + ')...';

    let response;
    if (PSLDashboardState.adminMode) {
      if (!PSLDashboardState.adminKey) {
        PSLDashboardState.adminKey = prompt('Enter admin access key:') || '';
        if (!PSLDashboardState.adminKey) {
          throw new Error('Admin key required.');
        }
        sessionStorage.setItem('adminKey', PSLDashboardState.adminKey);
      }
      response = await fetch('/api/admin/export-csv?' + params.toString(), {
        headers: { 'X-Admin-Key': PSLDashboardState.adminKey.trim() }
      });
    } else {
      response = await fetch('/api/export-csv?' + params.toString());
    }

    if (!response.ok) {
      throw new Error('CSV export failed (' + response.status + ')');
    }

    const blob = await response.blob();
    const blobUrl = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = blobUrl;
    link.download = key + '-ids-' + selectedTeam + '-' + selectedRange + '.csv';
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(blobUrl), 30000);

    err.style.background = '#0f5132';
    err.style.color = '#d1fae5';
    err.textContent = 'CSV download started for ' + testType + ' - ' + selectedTeam + ' (' + selectedRange + ').';
  } catch (e) {
    err.style.display = 'block';
    err.style.background = '#7f1d1d';
    err.style.color = '#fee2e2';
    err.textContent = String(e.message || e);
  }
}

async function loadPublishedState() {
  const sub = document.getElementById('sub');
  const err = document.getElementById('err');
  try {
    const res = await fetchWithTimeout('/api/published-state', 180000);
    if (!res.ok) {
      throw new Error('HTTP ' + res.status);
    }
    const snap = await res.json();
    if (!snap.published) {
      if (sub) {
        sub.textContent = PSLDashboardState.adminMode
          ? 'No data published yet. Enter JQL in each section and click Run & Publish.'
          : 'No published data yet. Contact admin to publish data.';
      }
      return;
    }
    }

    let latestAt = '';
    for (const type of PSLDashboardState.sectionTypes) {
      const key = type.toLowerCase();
      const section = snap[key];
      if (section?.agile) {
        renderSectionTable(type, section.agile);
        PSLDashboardState.lastSectionJql[key] = section.jql || '';
        const input = document.getElementById(key + 'Jql');
        if (input && section.jql) {
          input.value = section.jql;
        }
        const subEl = document.getElementById(key + 'Sub');
        if (subEl && section.published_at) {
          subEl.textContent = 'Published: ' + section.published_at + ' - ' + (section.agile?.total_test_cases ?? 0) + ' test cases';
        }
        if (!latestAt || section.published_at > latestAt) {
          latestAt = section.published_at;
        }
      }
    }

    if (!snap.sanity && snap.sanity_agile?.rows?.length) {
      renderSectionTable('Sanity', snap.sanity_agile);
      PSLDashboardState.lastSectionJql.sanity = snap.base_jql || '';
      const sanityInput = document.getElementById('sanityJql');
      if (sanityInput && snap.base_jql) {
        sanityInput.value = snap.base_jql;
      }
    }

    if (sub) {
      sub.textContent = latestAt ? 'Last published: ' + latestAt : 'Published snapshot loaded.';
    }
    if (err) {
      err.style.display = 'none';
    }
  } catch (e) {
    if (err) {
      err.style.display = 'block';
      err.textContent = String(e.message || e);
    }
    if (sub) {
      sub.textContent = 'Failed to load published data.';
    }
  }
}

function initPublishedData() {
  loadPublishedState();
}

window.renderSectionTable = renderSectionTable;
window.downloadSectionCsv = downloadSectionCsv;
window.loadPublishedState = loadPublishedState;
window.initPublishedData = initPublishedData;
