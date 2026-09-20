// ==========================================================================
// ROADLYY SCENARIO & COUNTERFACTUAL SIMULATION SANDBOX (B&W EDITION)
// ==========================================================================

let sandboxChartInstance = null;
let benchmarkScenarios = [];

async function initScenarioSandbox() {
  const ctx = document.getElementById('sandbox-chart-canvas');
  if (ctx && !sandboxChartInstance) {
    sandboxChartInstance = new Chart(ctx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [
          {
            label: 'Baseline Disrupted Delay (veh-min)',
            data: [],
            borderColor: '#71717a',
            backgroundColor: 'rgba(255, 255, 255, 0.05)',
            borderWidth: 2,
            borderDash: [5, 5],
            tension: 0.3
          },
          {
            label: 'Mitigated Counterfactual Delay (veh-min)',
            data: [],
            borderColor: '#ffffff',
            backgroundColor: 'rgba(255, 255, 255, 0.12)',
            borderWidth: 2.5,
            tension: 0.3
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: '#a1a1aa', font: { family: 'Outfit', size: 12 } } },
          tooltip: {
            backgroundColor: '#121215',
            titleColor: '#ffffff',
            bodyColor: '#a1a1aa',
            borderColor: 'rgba(255, 255, 255, 0.2)',
            borderWidth: 1
          }
        },
        scales: {
          x: { grid: { color: 'rgba(255, 255, 255, 0.06)' }, ticks: { color: '#a1a1aa', font: { family: 'JetBrains Mono' } } },
          y: { grid: { color: 'rgba(255, 255, 255, 0.06)' }, ticks: { color: '#a1a1aa', font: { family: 'JetBrains Mono' } } }
        }
      }
    });
  }

  await loadBenchmarkScenarios();
  await loadPlanningOptionsForSandbox();
}

async function loadBenchmarkScenarios() {
  try {
    const res = await fetch('/api/scenarios/benchmarks');
    benchmarkScenarios = await res.json();
    
    const select = document.getElementById('benchmark-scenario-select');
    if (select) {
      select.innerHTML = '<option value="">-- Choose Benchmark Scenario (30 Available) --</option>' +
        benchmarkScenarios.map(sc => `
          <option value="${sc.scenario_id}">
            [${sc.scenario_id}] ${sc.target_segment} - ${sc.incident_type} (Sev ${sc.severity})
          </option>
        `).join('');

      select.addEventListener('change', (e) => {
        const selected = benchmarkScenarios.find(s => s.scenario_id === e.target.value);
        if (selected) {
          document.getElementById('sim-target-segment').value = selected.target_segment;
          document.getElementById('sim-incident-type').value = selected.incident_type;
          document.getElementById('sim-severity').value = selected.severity;
          loadSegmentPlanningOptions(selected.target_segment);
          runScenarioSimulation();
        }
      });
    }
  } catch (err) {
    console.error('Failed to load benchmark scenarios:', err);
  }
}

async function loadPlanningOptionsForSandbox() {
  const segInput = document.getElementById('sim-target-segment');
  if (segInput) {
    segInput.addEventListener('change', () => {
      loadSegmentPlanningOptions(segInput.value.trim().toUpperCase());
    });
  }
}

async function loadSegmentPlanningOptions(segId) {
  const candSelect = document.getElementById('sim-intervention-select');
  if (!candSelect) return;

  try {
    const res = await fetch(`/api/segments/${segId}`);
    if (res.ok) {
      const data = await res.json();
      if (data.candidates && data.candidates.length > 0) {
        candSelect.innerHTML = '<option value="">-- Select Candidate Intervention --</option>' +
          data.candidates.map(c => `
            <option value="${c.candidate_id}">
              [${c.candidate_id}] ${c.intervention_type} (+${c.capacity_delta_vph} vph, Cost: ${c.cost_index})
            </option>
          `).join('');
      } else {
        candSelect.innerHTML = '<option value="">No pre-registered candidates (Custom params will apply)</option>';
      }
    }
  } catch (err) {
    console.error('Failed to load segment candidates:', err);
  }
}

async function runScenarioSimulation() {
  const targetSeg = document.getElementById('sim-target-segment').value.trim().toUpperCase() || 'R0067';
  const incType = document.getElementById('sim-incident-type').value || 'stalled_vehicle';
  const severity = parseInt(document.getElementById('sim-severity').value || '2');
  const lanesBlocked = parseInt(document.getElementById('sim-lanes-blocked').value || '1');
  const interventionId = document.getElementById('sim-intervention-select').value || null;
  const customCap = parseFloat(document.getElementById('sim-custom-capacity').value || '0');

  const payload = {
    target_segment: targetSeg,
    incident_type: incType,
    severity: severity,
    lanes_blocked: lanesBlocked,
    intervention_id: interventionId,
    custom_capacity_delta: customCap
  };

  try {
    const res = await fetch('/api/scenarios/simulate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    
    if (res.ok) {
      const simData = await res.json();
      renderSimulationResults(simData);
    }
  } catch (err) {
    console.error('Simulation failed:', err);
  }
}

function renderSimulationResults(simData) {
  if (!simData || !sandboxChartInstance) return;

  const m = simData.summary_metrics;
  const ts = simData.time_series;

  // Update metrics readout
  document.getElementById('sim-baseline-delay').textContent = `${m.total_delay_baseline_veh_hrs} veh-hrs`;
  document.getElementById('sim-mitigated-delay').textContent = `${m.total_delay_mitigated_veh_hrs} veh-hrs`;
  document.getElementById('sim-delay-savings').textContent = `${m.delay_savings_veh_hrs} veh-hrs`;
  document.getElementById('sim-improvement-pct').textContent = `+${m.delay_reduction_pct}%`;
  document.getElementById('sim-recovery-time').textContent = `${m.bottleneck_recovery_time_min} mins`;

  // Update chart
  sandboxChartInstance.data.labels = ts.intervals;
  sandboxChartInstance.data.datasets[0].data = ts.baseline_delay_min;
  sandboxChartInstance.data.datasets[1].data = ts.mitigated_delay_min;
  sandboxChartInstance.update();

  // Render upstream spillback propagation
  const spillList = document.getElementById('spillback-nodes-list');
  if (spillList && simData.spillback_propagation) {
    spillList.innerHTML = simData.spillback_propagation.map(sp => `
      <div style="display:flex; justify-content:space-between; align-items:center; padding:8px 12px; background:rgba(255,255,255,0.03); border-radius:6px; font-size:12px; border:1px solid rgba(255,255,255,0.08);">
        <div>
          <strong>Segment ${sp.segment_id}</strong>
          <span style="color:#a1a1aa; margin-left:6px;">(${sp.hop}-Hop Upstream Feeder)</span>
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
          <span class="badge-tag ${sp.queue_risk === 'HIGH' ? 'badge-bottleneck' : sp.queue_risk === 'MEDIUM' ? 'badge-medium' : 'badge-high'}">
            Risk: ${sp.queue_risk}
          </span>
          <span style="font-family:'JetBrains Mono'; color:#ffffff; font-weight:600;">-${sp.speed_drop_pct}% Speed</span>
        </div>
      </div>
    `).join('');
  }
}
