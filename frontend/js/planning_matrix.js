// ==========================================================================
// ROADLYY 90-CANDIDATE PLANNING & ROI MATRIX
// ==========================================================================

let allRankedCandidates = [];

async function initPlanningMatrix() {
  await fetchPlanningRankings();

  // Search & Filter listeners
  const typeFilter = document.getElementById('planning-type-filter');
  const feasFilter = document.getElementById('planning-feasibility-filter');
  const bneckFilter = document.getElementById('planning-bottleneck-only');
  const searchInput = document.getElementById('planning-search');

  if (typeFilter) typeFilter.addEventListener('change', applyPlanningFilters);
  if (feasFilter) feasFilter.addEventListener('change', applyPlanningFilters);
  if (bneckFilter) bneckFilter.addEventListener('change', applyPlanningFilters);
  if (searchInput) searchInput.addEventListener('input', applyPlanningFilters);

  // Portfolio budget optimizer
  const budgetInput = document.getElementById('portfolio-budget-input');
  const optBtn = document.getElementById('run-portfolio-btn');
  if (optBtn && budgetInput) {
    optBtn.addEventListener('click', () => {
      runPortfolioOptimizer(parseInt(budgetInput.value) || 50);
    });
  }
}

async function fetchPlanningRankings() {
  try {
    const res = await fetch('/api/planning/rankings');
    allRankedCandidates = await res.json();
    renderPlanningTable(allRankedCandidates);
  } catch (err) {
    console.error('Failed to load planning rankings:', err);
  }
}

function applyPlanningFilters() {
  const typeVal = document.getElementById('planning-type-filter')?.value || 'all';
  const feasVal = document.getElementById('planning-feasibility-filter')?.value || 'all';
  const bneckVal = document.getElementById('planning-bottleneck-only')?.checked || false;
  const query = document.getElementById('planning-search')?.value.trim().toUpperCase() || '';

  let filtered = allRankedCandidates.filter(c => {
    if (typeVal !== 'all' && c.intervention_type !== typeVal) return false;
    if (feasVal !== 'all' && c.feasibility_band !== feasVal) return false;
    if (bneckVal && !c.is_structural_bottleneck) return false;
    if (query && !c.candidate_id.includes(query) && !c.target_segment.includes(query)) return false;
    return true;
  });

  renderPlanningTable(filtered);
}

function renderPlanningTable(candidates) {
  const tbody = document.getElementById('planning-table-body');
  if (!tbody) return;

  if (candidates.length === 0) {
    tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; color:#94a3b8; padding:20px;">No matching planning candidates found.</td></tr>';
    return;
  }

  tbody.innerHTML = candidates.map(c => `
    <tr>
      <td style="font-family:'JetBrains Mono'; font-weight:700; color:#ffffff;">#${c.rank}</td>
      <td style="font-family:'JetBrains Mono'; font-weight:600;">${c.candidate_id}</td>
      <td>
        <strong>${c.target_segment}</strong>
        ${c.is_structural_bottleneck ? '<span class="badge-tag badge-bottleneck" style="margin-left:6px;">Bottleneck</span>' : ''}
      </td>
      <td><span style="text-transform:capitalize;">${c.intervention_type.replace('_', ' ')}</span></td>
      <td style="font-family:'JetBrains Mono'; color:#ffffff; font-weight:600;">+${c.capacity_delta_vph} vph</td>
      <td style="font-family:'JetBrains Mono';">${c.cost_index}</td>
      <td>
        <span class="badge-tag ${c.feasibility_band === 'high' ? 'badge-high' : c.feasibility_band === 'medium' ? 'badge-medium' : 'badge-low'}">
          ${c.feasibility_band}
        </span>
      </td>
      <td style="font-family:'JetBrains Mono'; color:#ffffff; font-weight:700;">${c.estimated_weekly_delay_savings_hrs} hrs/wk</td>
      <td>
        <button class="control-btn" style="padding:4px 8px; font-size:11px;" onclick="simulateCandidateInSandbox('${c.candidate_id}', '${c.target_segment}')">
          Simulate
        </button>
      </td>
    </tr>
  `).join('');
}

function simulateCandidateInSandbox(candId, segId) {
  // Switch to scenario tab
  const scenarioTab = document.querySelector('.nav-tab-btn[data-tab="tab-scenarios"]');
  if (scenarioTab) scenarioTab.click();

  // Populate sandbox
  const segInput = document.getElementById('sim-target-segment');
  if (segInput) {
    segInput.value = segId;
    loadSegmentPlanningOptions(segId).then(() => {
      const candSelect = document.getElementById('sim-intervention-select');
      if (candSelect) candSelect.value = candId;
      runScenarioSimulation();
    });
  }
}

async function runPortfolioOptimizer(budget) {
  try {
    const res = await fetch(`/api/planning/portfolio?budget=${budget}`);
    const data = await res.json();
    
    // Highlight selected candidates
    const selectedIds = new Set(data.selected_interventions.map(i => i.candidate_id));
    
    const banner = document.getElementById('portfolio-results-banner');
    if (banner) {
      banner.style.display = 'block';
      banner.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <div>
            <strong>Optimized Portfolio:</strong> ${data.selected_count} Interventions selected | 
            Cost Spent: <strong>${data.budget_spent} / ${data.budget_limit}</strong>
          </div>
          <div style="font-size:16px; color:#10b981; font-weight:700;">
            +${data.total_weekly_delay_savings_hrs} veh-hrs saved weekly
          </div>
        </div>
      `;
    }

    renderPlanningTable(data.selected_interventions);
  } catch (err) {
    console.error('Portfolio optimization failed:', err);
  }
}
