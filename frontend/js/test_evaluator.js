// ==========================================================================
// ROADLYY JURY TEST CASE EVALUATION & LIVE ML INFERENCE ENGINE
// ==========================================================================

let benchmarkScenariosList = [];

document.addEventListener('DOMContentLoaded', () => {
  loadBenchmarkScenarios();
});

async function loadBenchmarkScenarios() {
  try {
    const res = await fetch('/api/testcase/scenarios');
    benchmarkScenariosList = await res.json();
    populateScenarioPresetDropdown(benchmarkScenariosList);
  } catch (err) {
    console.error('Failed to load benchmark scenarios:', err);
  }
}

function populateScenarioPresetDropdown(scenarios) {
  const select = document.getElementById('testcase-preset-select');
  if (!select) return;

  select.innerHTML = '<option value="">-- Choose a Preset Challenge Scenario or Enter Custom --</option>';
  scenarios.forEach((sc, idx) => {
    const opt = document.createElement('option');
    opt.value = idx;
    opt.textContent = `${sc.scenario_id}: ${sc.target_segment} (${sc.incident_type.replace('_', ' ')}, Sev ${sc.severity}) - ${sc.start_time}`;
    select.appendChild(opt);
  });
}

function onScenarioPresetChange(indexStr) {
  if (indexStr === '') return;
  const sc = benchmarkScenariosList[parseInt(indexStr)];
  if (!sc) return;

  document.getElementById('tc-scenario-id').value = sc.scenario_id;
  document.getElementById('tc-segment-id').value = sc.target_segment;
  document.getElementById('tc-timestamp').value = sc.start_time;
  document.getElementById('tc-incident-type').value = sc.incident_type;
  document.getElementById('tc-severity').value = sc.severity;
  document.getElementById('tc-lanes-blocked').value = Math.min(2, sc.severity);
  document.getElementById('tc-rain').value = (sc.target_segment === 'R0161') ? '6.5' : '0.0';
  document.getElementById('tc-speed').value = '';
  document.getElementById('tc-flow').value = '';
}

function normalizeSegmentId(val) {
  if (!val) return 'R0067';
  const s = String(val).trim().toUpperCase();
  if (typeof segmentLayers === 'object' && segmentLayers[s]) return s;
  const digits = s.replace(/\D/g, '');
  if (digits) {
    const padded = 'R' + digits.padStart(4, '0');
    return padded;
  }
  return s;
}

function getCoordsForSegment(segId) {
  const normId = normalizeSegmentId(segId);
  if (typeof segmentLayers === 'object' && segmentLayers[normId] && segmentLayers[normId].coords) {
    return segmentLayers[normId].coords;
  }
  if (typeof segmentLayers === 'object' && segmentLayers[segId] && segmentLayers[segId].coords) {
    return segmentLayers[segId].coords;
  }
  if (networkGeoJson && networkGeoJson.features) {
    const feat = networkGeoJson.features.find(f => {
      const sid = f.properties && f.properties.segment_id;
      return sid === normId || sid === segId;
    });
    if (feat && feat.geometry && feat.geometry.coordinates) {
      return feat.geometry.coordinates.map(c => [c[1], c[0]]);
    }
  }
  return null;
}

function openTestCaseModal() {
  const modal = document.getElementById('testcase-modal');
  if (modal) {
    modal.style.display = 'flex';
    setTimeout(() => {
      if (tcMapInstance) {
        tcMapInstance.invalidateSize();
      }
    }, 100);
  }
}

function closeTestCaseModal() {
  const modal = document.getElementById('testcase-modal');
  if (modal) {
    modal.style.display = 'none';
  }
}

async function runLiveTestCaseInference() {
  const runBtn = document.getElementById('tc-run-btn');
  const resultsContainer = document.getElementById('tc-results-content');
  const emptyState = document.getElementById('tc-results-empty');

  const rawSeg = document.getElementById('tc-segment-id').value || 'R0067';
  const normSeg = normalizeSegmentId(rawSeg);
  document.getElementById('tc-segment-id').value = normSeg;

  const payload = {
    scenario_id: document.getElementById('tc-scenario-id').value || 'CUSTOM_TEST_CASE',
    segment_id: normSeg,
    timestamp: document.getElementById('tc-timestamp').value || '2026-01-20 08:30:00',
    incident_type: document.getElementById('tc-incident-type').value || 'none',
    severity: parseInt(document.getElementById('tc-severity').value) || 1,
    lanes_blocked: parseInt(document.getElementById('tc-lanes-blocked').value) || 0,
    rain_intensity: parseFloat(document.getElementById('tc-rain').value) || 0.0,
    temperature_c: parseFloat(document.getElementById('tc-temp').value) || 25.0,
    current_speed_kmh: parseFloat(document.getElementById('tc-speed').value) || 0.0,
    current_flow_vph: parseFloat(document.getElementById('tc-flow').value) || 0.0
  };

  if (runBtn) {
    runBtn.disabled = true;
    runBtn.textContent = 'Running AI Inference...';
  }

  try {
    const res = await fetch('/api/testcase/evaluate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}));
      throw new Error(errJson.detail || `Server returned HTTP ${res.status}`);
    }

    const data = await res.json();
    if (!data || !data.current_state) {
      throw new Error('Invalid response structure from backend model engine.');
    }

    if (emptyState) emptyState.style.display = 'none';
    if (resultsContainer) resultsContainer.style.display = 'block';

    renderTestCaseResults(data);

    // Also highlight segment on main map in background
    if (typeof selectSegment === 'function') {
      selectSegment(normSeg);
    }
  } catch (err) {
    console.error('Error running test case evaluation:', err);
    alert('Failed to evaluate test case: ' + err.message);
  } finally {
    if (runBtn) {
      runBtn.disabled = false;
      runBtn.textContent = '▶ Run Live AI Inference';
    }
  }
}

function renderTestCaseResults(data) {
  if (!data || !data.current_state) return;

  // Current State
  const cs = data.current_state;
  const statusEl = document.getElementById('tc-res-status');
  if (statusEl) statusEl.textContent = cs.status || 'Active';
  
  const speedEl = document.getElementById('tc-res-speed');
  if (speedEl) speedEl.textContent = `${cs.speed_kmh} km/h`;
  
  const flowEl = document.getElementById('tc-res-flow');
  if (flowEl) flowEl.textContent = `${(cs.flow_vph || 0).toLocaleString()} vph`;
  
  const vcEl = document.getElementById('tc-res-vc');
  if (vcEl) vcEl.textContent = `${cs.vc_ratio}`;
  
  const congEl = document.getElementById('tc-res-cong');
  if (congEl) congEl.textContent = `${cs.congestion_index}`;
  
  const delayEl = document.getElementById('tc-res-delay');
  if (delayEl) delayEl.textContent = `${cs.delay_min} min`;
  
  const queueEl = document.getElementById('tc-res-queue');
  if (queueEl) queueEl.textContent = `${cs.queue_length_veh} veh`;

  // 4-Horizon Forecasts Grid
  const forecastGrid = document.getElementById('tc-forecast-cards');
  if (forecastGrid && data.forecasts) {
    forecastGrid.innerHTML = '';
    data.forecasts.forEach(f => {
      const card = document.createElement('div');
      card.className = 'tc-fcard';

      card.innerHTML = `
        <div class="tc-fcard-header" style="margin-bottom:2px;">
          <span style="font-weight:800; font-size:11.5px; color:#ffffff;">+${f.horizon}</span>
          <span style="font-size:10px; font-weight:600; color:#d4d4d8; background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.15); padding:1px 5px; border-radius:3px;">${(f.predicted_congestion_index * 100).toFixed(1)}% Cong</span>
        </div>
        <div style="margin-top:2px;">
          <div style="font-size:13.5px; font-weight:800; color:#ffffff;">${f.predicted_speed_kmh} <span style="font-size:10px; font-weight:600; color:#a1a1aa;">km/h</span></div>
          <div style="font-size:9.5px; color:#a1a1aa;">Range: ${f.speed_lower}-${f.speed_upper}</div>
        </div>
        <div style="margin-top:3px; border-top:1px dashed rgba(255,255,255,0.1); padding-top:2px;">
          <div style="font-size:10.5px; color:#d4d4d8;">Flow: <b>${f.predicted_flow_vph}</b> &bull; Delay: <b>${f.predicted_delay_min}m</b></div>
        </div>
      `;
      forecastGrid.appendChild(card);
    });
  }

  // Render Geospatial Incident, Shockwave & Detour Map
  renderTestCaseMap(data);
}

let tcMapInstance = null;
let tcMapLayersGroup = null;

function renderTestCaseMap(data) {
  const mapContainer = document.getElementById('tc-map-container');
  if (!mapContainer) return;

  if (!tcMapInstance) {
    tcMapInstance = L.map('tc-map-container', {
      center: [17.418, 78.472],
      zoom: 13,
      zoomControl: true,
      attributionControl: false
    });

    // Dark Basemap
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
      maxZoom: 19,
      attribution: ''
    }).addTo(tcMapInstance);

    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}', {
      maxZoom: 19,
      opacity: 0.85,
      attribution: ''
    }).addTo(tcMapInstance);

    tcMapLayersGroup = L.featureGroup().addTo(tcMapInstance);
  }

  // Clear previous layers
  tcMapLayersGroup.clearLayers();

  const highlightBoundsLayers = [];

  // 1. Draw subtle background road network if available
  if (typeof segmentLayers === 'object') {
    Object.entries(segmentLayers).forEach(([sid, s]) => {
      if (s.coords && s.coords.length >= 2) {
        L.polyline(s.coords, {
          color: '#27272a',
          weight: 2.0,
          opacity: 0.35,
          interactive: false
        }).addTo(tcMapLayersGroup);
      }
    });
  }

  const targetSegId = normalizeSegmentId(data.segment_id);
  const feeders = data.propagation_shockwave || [];
  const detourSegs = (data.detour_recommendation && data.detour_recommendation.detour_segments) || [];

  // 2. Draw Detour Route Polylines in High-Contrast White Dashed Flow
  detourSegs.forEach(dsId => {
    const coords = getCoordsForSegment(dsId);
    if (coords && coords.length >= 2) {
      const line = L.polyline(coords, {
        color: '#ffffff',
        weight: 5.0,
        opacity: 0.95,
        dashArray: '6, 6',
        lineCap: 'round',
        lineJoin: 'round'
      }).addTo(tcMapLayersGroup);
      line.bindTooltip(`<div class="roadlyy-tooltip"><b>Detour Link: ${dsId}</b></div>`, { className: 'roadlyy-tooltip' });
      highlightBoundsLayers.push(line);
    }
  });

  // 3. Draw Upstream Feeder Links in Subtle Muted Silver/Gray
  feeders.forEach(fd => {
    const fsId = fd.feeder_segment;
    const coords = getCoordsForSegment(fsId);
    if (coords && coords.length >= 2) {
      const line = L.polyline(coords, {
        color: '#71717a',
        weight: 4.5,
        opacity: 0.90,
        lineCap: 'round'
      }).addTo(tcMapLayersGroup);
      line.bindTooltip(`<div class="roadlyy-tooltip"><b>Feeder ${fsId}</b>: Drops to ${fd.estimated_spillover_speed} km/h (+${fd.added_delay_min}m delay)</div>`, { className: 'roadlyy-tooltip' });
      highlightBoundsLayers.push(line);
    }
  });

  // 4. Draw Target Incident Segment in High-Intensity Solid White
  const targetCoords = getCoordsForSegment(targetSegId);
  if (targetCoords && targetCoords.length >= 2) {
    // Ambient white glow
    L.polyline(targetCoords, {
      color: '#ffffff',
      weight: 14.0,
      opacity: 0.35,
      interactive: false
    }).addTo(tcMapLayersGroup);

    // Sharp main line
    const targetLine = L.polyline(targetCoords, {
      color: '#ffffff',
      weight: 6.5,
      opacity: 1.0,
      lineCap: 'round'
    }).addTo(tcMapLayersGroup);

    targetLine.bindTooltip(`
      <div class="roadlyy-tooltip">
        <b style="color:#ffffff;">INCIDENT LINK: ${targetSegId}</b><br/>
        Speed: <b>${data.current_state.speed_kmh} km/h</b><br/>
        Queue: <b>${data.current_state.queue_length_veh} veh</b>
      </div>
    `, { className: 'roadlyy-tooltip', permanent: true });
    
    highlightBoundsLayers.push(targetLine);

    // Incident Beacon Marker at midpoint (B&W)
    const midIdx = Math.floor(targetCoords.length / 2);
    const midPt = targetCoords[midIdx] || targetCoords[0];
    const icon = L.divIcon({
      className: '',
      html: '<div class="incident-pulse-marker" style="transform:scale(1.2);">!</div>',
      iconSize: [28, 28],
      iconAnchor: [14, 14]
    });
    L.marker(midPt, { icon, zIndexOffset: 3000 }).addTo(tcMapLayersGroup);
  }

  // 5. Invalidate Size & Fit bounds to all highlighted scenario features
  setTimeout(() => {
    if (tcMapInstance) {
      tcMapInstance.invalidateSize();
      if (highlightBoundsLayers.length > 0) {
        const group = L.featureGroup(highlightBoundsLayers);
        tcMapInstance.fitBounds(group.getBounds(), { padding: [35, 35], maxZoom: 16 });
      } else if (targetCoords && targetCoords.length > 0) {
        tcMapInstance.setView(targetCoords[0], 14);
      }
    }
  }, 100);

  setTimeout(() => {
    if (tcMapInstance) {
      tcMapInstance.invalidateSize();
    }
  }, 300);
}
