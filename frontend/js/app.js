// ==========================================================================
// ROADLYY MAIN APPLICATION CONTROLLER
// ==========================================================================

let availableTimestamps = [];
let currentTimestampIndex = 0;
let isPlaying = false;
let playbackInterval = null;
let playbackSpeed = 1000; // ms per step
const sliceCache = new Map();
let isFetchingSlice = false;

document.addEventListener('DOMContentLoaded', async () => {
  console.log('[Roadlyy] Initializing frontend application...');
  
  initTabs();
  await initMap();
  initForecastChart();
  initScenarioSandbox();
  initPlanningMatrix();

  await loadTimestamps();
  initTimelineControls();
});

function initTabs() {
  const tabs = document.querySelectorAll('.nav-tab-btn');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));

      tab.classList.add('active');
      const targetPane = document.getElementById(tab.dataset.tab);
      if (targetPane) {
        targetPane.classList.add('active');
        if (tab.dataset.tab === 'tab-dashboard' && mapInstance) {
          setTimeout(() => mapInstance.invalidateSize(), 200);
        }
      }
    });
  });
}

let fullTimelinePool = [];

async function loadTimestamps(split = 'val') {
  try {
    const res = await fetch(`/api/traffic/timestamps?split=all`);
    const data = await res.json();
    fullTimelinePool = data.timestamps || [];

    filterAndApplyTimestamps(split);

    if (availableTimestamps.length > 0) {
      const initialTs = availableTimestamps[0];
      await loadTrafficSlice(initialTs);
      if (!activeSegmentId) {
        selectSegment('R0001');
      }
    }
  } catch (err) {
    console.error('Failed to load timestamps:', err);
  }
}

function filterAndApplyTimestamps(filterVal) {
  if (filterVal === 'val') {
    availableTimestamps = fullTimelinePool.filter(ts => 
      ts.startsWith('2026-01-16') || ts.startsWith('2026-01-17') || ts.startsWith('2026-01-18') || ts.startsWith('2026-01-19')
    );
  } else if (filterVal === 'train') {
    availableTimestamps = fullTimelinePool.filter(ts => 
      !ts.startsWith('2026-01-16') && !ts.startsWith('2026-01-17') && !ts.startsWith('2026-01-18') && !ts.startsWith('2026-01-19')
    );
  } else if (filterVal === 'all') {
    availableTimestamps = fullTimelinePool;
  } else {
    // Specific single date filter (e.g., '2026-01-01')
    availableTimestamps = fullTimelinePool.filter(ts => ts.startsWith(filterVal));
  }

  const slider = document.getElementById('timeline-slider');
  if (slider) {
    slider.min = 0;
    slider.max = Math.max(0, availableTimestamps.length - 1);
    slider.value = 0;
    currentTimestampIndex = 0;
  }
}

function onDayFilterChange(filterVal) {
  const picker = document.getElementById('custom-range-picker');
  if (filterVal === 'custom') {
    // Show the range picker, don't load yet
    if (picker) picker.style.display = 'flex';
    return;
  }
  // Hide range picker for preset options
  if (picker) picker.style.display = 'none';
  changeDayFilter(filterVal);
}

function applyCustomRange() {
  const startEl = document.getElementById('range-start-input');
  const endEl   = document.getElementById('range-end-input');
  const label   = document.getElementById('range-count-label');
  if (!startEl || !endEl) return;

  const startVal = startEl.value;
  const endVal   = endEl.value;

  if (!startVal || !endVal) {
    if (label) label.textContent = 'Select start and end dates';
    return;
  }

  // Convert datetime-local value (2026-01-07T13:00) -> timestamp format (2026-01-07 13:00:00)
  const startStr = startVal.replace('T', ' ');
  const endStr   = endVal.replace('T', ' ');

  if (startStr >= endStr) {
    if (label) label.textContent = 'Start must precede End';
    return;
  }

  if (isPlaying) togglePlayback();

  // 1. Try matching with precomputed historical cache
  let matched = fullTimelinePool.filter(ts => ts >= startStr && ts <= endStr + ':59');
  
  // 2. If no data exists in static pool or range extends outside, dynamically synthesize 5-min intervals
  if (matched.length === 0) {
    matched = generateTimestampsBetween(startStr, endStr);
  }

  availableTimestamps = matched;
  
  const slider = document.getElementById('timeline-slider');
  if (slider) {
    slider.min = 0;
    slider.max = Math.max(0, availableTimestamps.length - 1);
    slider.value = 0;
  }
  currentTimestampIndex = 0;

  if (label) label.textContent = `${availableTimestamps.length} steps`;

  if (availableTimestamps.length > 0) {
    loadTrafficSlice(availableTimestamps[0]);
  } else {
    if (label) label.textContent = '0 steps';
  }
}

function generateTimestampsBetween(startStr, endStr) {
  const list = [];
  let cur = new Date(startStr.replace(' ', 'T'));
  const end = new Date(endStr.replace(' ', 'T'));
  if (isNaN(cur.getTime()) || isNaN(end.getTime())) return list;

  let count = 0;
  // Step by 5 minutes (max 2016 steps for safe playback, ~7 continuous days)
  while (cur <= end && count < 2016) {
    const yyyy = cur.getFullYear();
    const mm = String(cur.getMonth() + 1).padStart(2, '0');
    const dd = String(cur.getDate()).padStart(2, '0');
    const hh = String(cur.getHours()).padStart(2, '0');
    const min = String(cur.getMinutes()).padStart(2, '0');
    list.push(`${yyyy}-${mm}-${dd} ${hh}:${min}:00`);
    cur = new Date(cur.getTime() + 5 * 60 * 1000);
    count++;
  }
  return list;
}

function changeDayFilter(filterVal) {
  if (isPlaying) {
    togglePlayback();
  }
  filterAndApplyTimestamps(filterVal);
  if (availableTimestamps.length > 0) {
    updateSliderAndLoad();
  }
}

function jumpToJuryHotspot(hotspotValue) {
  if (!hotspotValue) return;
  const [targetTs, targetSeg] = hotspotValue.split('|');
  
  // Set day filter to all so it contains the target timestamp
  const daySelect = document.getElementById('dataset-day-select');
  if (daySelect) daySelect.value = 'all';
  filterAndApplyTimestamps('all');

  const foundIndex = availableTimestamps.findIndex(ts => ts === targetTs);
  if (foundIndex !== -1) {
    currentTimestampIndex = foundIndex;
    const slider = document.getElementById('timeline-slider');
    if (slider) slider.value = foundIndex;
    loadTrafficSlice(targetTs);
  }

  if (targetSeg) {
    selectSegment(targetSeg);
  }
}

function initTimelineControls() {
  const slider = document.getElementById('timeline-slider');
  const playBtn = document.getElementById('play-btn');
  const prevBtn = document.getElementById('prev-btn');
  const nextBtn = document.getElementById('next-btn');

  if (slider) {
    slider.addEventListener('input', (e) => {
      currentTimestampIndex = parseInt(e.target.value);
      loadTrafficSlice(availableTimestamps[currentTimestampIndex]);
    });
  }

  if (playBtn) {
    playBtn.addEventListener('click', () => {
      togglePlayback();
    });
  }

  if (prevBtn) {
    prevBtn.addEventListener('click', () => {
      if (currentTimestampIndex > 0) {
        currentTimestampIndex--;
        updateSliderAndLoad();
      }
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener('click', () => {
      if (currentTimestampIndex < availableTimestamps.length - 1) {
        currentTimestampIndex++;
        updateSliderAndLoad();
      }
    });
  }

  // Speed toggles
  document.querySelectorAll('.speed-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.speed-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const speed = parseFloat(btn.dataset.speed);
      playbackSpeed = 1000 / speed;
      if (isPlaying) {
        clearInterval(playbackInterval);
        playbackInterval = setInterval(stepPlayback, playbackSpeed);
      }
    });
  });
}

function togglePlayback() {
  isPlaying = !isPlaying;
  const playBtn = document.getElementById('play-btn');
  if (playBtn) {
    playBtn.textContent = isPlaying ? 'Pause' : 'Play';
    playBtn.classList.toggle('active', isPlaying);
  }

  if (isPlaying) {
    playbackInterval = setInterval(stepPlayback, playbackSpeed);
  } else {
    clearInterval(playbackInterval);
  }
}

function stepPlayback() {
  if (currentTimestampIndex < availableTimestamps.length - 1) {
    currentTimestampIndex++;
    updateSliderAndLoad();
  } else {
    togglePlayback(); // Stop at end
  }
}

function updateSliderAndLoad() {
  const slider = document.getElementById('timeline-slider');
  if (slider) slider.value = currentTimestampIndex;
  loadTrafficSlice(availableTimestamps[currentTimestampIndex]);
}

async function loadTrafficSlice(timestamp) {
  if (!timestamp) return;

  try {
    let data = sliceCache.get(timestamp);
    if (!data) {
      const res = await fetch(`/api/traffic/slice?timestamp=${encodeURIComponent(timestamp)}`);
      data = await res.json();
      sliceCache.set(timestamp, data);
    }
    
    window.currentSliceData = data;

    // Update time displays
    const timeDisplay = document.getElementById('current-time-display');
    if (timeDisplay) timeDisplay.textContent = timestamp;

    // Update metric strip
    const ns = data.network_summary;
    if (ns) {
      const spdEl = document.getElementById('stat-avg-speed');
      const flwEl = document.getElementById('stat-total-flow');
      const dlyEl = document.getElementById('stat-total-delay');
      const congEl = document.getElementById('stat-congested');
      const incEl = document.getElementById('stat-incidents');
      
      if (spdEl) spdEl.textContent = `${ns.avg_network_speed}`;
      if (flwEl) flwEl.textContent = `${ns.total_network_flow ? ns.total_network_flow.toLocaleString() : 0}`;
      if (dlyEl) dlyEl.textContent = `${ns.total_delay_min}`;
      if (congEl) congEl.textContent = `${ns.congested_segments}`;
      if (incEl) incEl.textContent = `${ns.active_incidents_count}`;
    }

    // Update context strip
    const ctx = data.context || {};
    const tempEl = document.getElementById('ctx-temp');
    const rainEl = document.getElementById('ctx-rain');
    const evtEl = document.getElementById('ctx-event');
    if (tempEl) tempEl.textContent = `${ctx.temperature_c || 25.0}°C`;
    if (rainEl) rainEl.textContent = `${ctx.rain_intensity || 0.0} mm/h`;
    if (evtEl) evtEl.textContent = ctx.event_level > 0 ? `Level ${ctx.event_level}` : 'None';

    // Update map colors dynamically
    if (data.segments) {
      updateMapTrafficColors(data.segments);
    }

    // If a segment is active, refresh its details
    if (activeSegmentId) {
      loadSegmentDetails(activeSegmentId, timestamp);
    }

    // Background prefetch next 5 timestamps for butter-smooth timelapse
    prefetchUpcomingSlices(currentTimestampIndex);
  } catch (err) {
    console.error('Failed to load traffic slice:', err);
  }
}

function prefetchUpcomingSlices(startIndex) {
  const count = 6;
  for (let i = 1; i <= count; i++) {
    const nextIdx = startIndex + i;
    if (nextIdx < availableTimestamps.length) {
      const nextTs = availableTimestamps[nextIdx];
      if (!sliceCache.has(nextTs)) {
        fetch(`/api/traffic/slice?timestamp=${encodeURIComponent(nextTs)}`)
          .then(r => r.json())
          .then(d => sliceCache.set(nextTs, d))
          .catch(() => {});
      }
    }
  }
}

// Callback when user clicks on a road segment on the map
window.onSegmentSelected = function(segId) {
  const ts = availableTimestamps[currentTimestampIndex] || '2026-01-16 00:00:00';
  loadSegmentDetails(segId, ts);
};

async function loadSegmentDetails(segId, timestamp) {
  try {
    const res = await fetch(`/api/forecast/segment?segment_id=${segId}&timestamp=${encodeURIComponent(timestamp)}`);
    if (!res.ok) return;
    const data = await res.json();

    // Populate Inspector Card
    document.getElementById('inspector-seg-id').textContent = `Segment ${segId}`;
    document.getElementById('inspector-road-class').textContent = data.meta.road_class;
    document.getElementById('inspector-lanes').textContent = `${data.meta.lanes} Lanes`;
    document.getElementById('inspector-free-speed').textContent = `${data.meta.free_flow_speed_kmh} km/h`;
    document.getElementById('inspector-capacity').textContent = `${data.meta.capacity_vph} vph`;
    document.getElementById('inspector-bottleneck').textContent = data.meta.structural_bottleneck ? 'YES (Structural)' : 'No';

    const cur = data.current_state;
    document.getElementById('inspector-cur-speed').textContent = `${cur.speed_kmh.toFixed(1)} km/h`;
    document.getElementById('inspector-cur-flow').textContent = `${Math.round(cur.flow_vph)} vph`;
    document.getElementById('inspector-cur-cong').textContent = cur.congestion_index.toFixed(4);

    if (document.getElementById('inspector-vc-ratio')) {
      const cap = data.meta.capacity_vph || 2000;
      const vc = (cur.flow_vph / Math.max(1, cap)).toFixed(2);
      document.getElementById('inspector-vc-ratio').textContent = `${vc}`;
    }

    // Update Chart
    if (typeof updateForecastDisplay === 'function') {
      updateForecastDisplay(data);
    }
  } catch (err) {
    console.error('Failed to load segment details:', err);
  }
}
