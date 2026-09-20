// ==========================================================================
// ROADLYY MULTI-HORIZON FORECAST VISUALIZER (B&W EDITION)
// ==========================================================================

let forecastChartInstance = null;
let currentForecastMetric = 'speed'; // 'speed', 'flow', 'congestion'
let currentSegmentForecastData = null;

function initForecastChart() {
  const ctx = document.getElementById('forecast-chart-canvas');
  if (!ctx) return;

  forecastChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: ['Now (T)', '+15m', '+30m', '+45m', '+60m'],
      datasets: [
        {
          label: 'Forecast Prediction',
          data: [],
          borderColor: '#ffffff',
          backgroundColor: 'rgba(255, 255, 255, 0.15)',
          borderWidth: 2.5,
          fill: false,
          tension: 0.35,
          pointBackgroundColor: '#ffffff',
          pointRadius: 4.5
        },
        {
          label: 'Upper Confidence (90%)',
          data: [],
          borderColor: 'transparent',
          backgroundColor: 'rgba(255, 255, 255, 0.10)',
          fill: '+1',
          pointRadius: 0
        },
        {
          label: 'Lower Confidence (90%)',
          data: [],
          borderColor: 'transparent',
          backgroundColor: 'transparent',
          fill: false,
          pointRadius: 0
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: {
            color: '#a1a1aa',
            font: { family: 'Outfit', size: 11 }
          }
        },
        tooltip: {
          backgroundColor: '#121215',
          titleColor: '#ffffff',
          bodyColor: '#a1a1aa',
          borderColor: 'rgba(255, 255, 255, 0.2)',
          borderWidth: 1,
          padding: 10
        }
      },
      scales: {
        x: {
          grid: { color: 'rgba(255, 255, 255, 0.06)' },
          ticks: { color: '#a1a1aa', font: { family: 'JetBrains Mono' } }
        },
        y: {
          grid: { color: 'rgba(255, 255, 255, 0.06)' },
          ticks: { color: '#a1a1aa', font: { family: 'JetBrains Mono' } }
        }
      }
    }
  });
}

function updateForecastDisplay(forecastData) {
  currentSegmentForecastData = forecastData;
  if (!forecastData || !forecastChartInstance) return;

  const current = forecastData.current || {};
  const horizons = forecastData.horizons || {};

  let nowVal = 0;
  let pts = [];
  let uppers = [];
  let lowers = [];

  if (currentForecastMetric === 'speed') {
    nowVal = current.speed_kmh || 50;
    ['15m', '30m', '45m', '60m'].forEach(h => {
      const sp = horizons[h] ? horizons[h].predicted_speed_kmh : nowVal;
      pts.push(sp);
      uppers.push(Math.round(sp + 4.5));
      lowers.push(Math.max(0, Math.round(sp - 4.5)));
    });
  } else if (currentForecastMetric === 'flow') {
    nowVal = current.flow_vph || 1500;
    ['15m', '30m', '45m', '60m'].forEach(h => {
      const fl = horizons[h] ? horizons[h].predicted_flow_vph : nowVal;
      pts.push(fl);
      uppers.push(Math.round(fl * 1.08));
      lowers.push(Math.round(fl * 0.92));
    });
  } else if (currentForecastMetric === 'congestion') {
    nowVal = current.congestion_index || 0.1;
    ['15m', '30m', '45m', '60m'].forEach(h => {
      const cg = horizons[h] ? horizons[h].predicted_congestion : nowVal;
      pts.push(cg);
      uppers.push(Math.min(1.0, +(cg + 0.05).toFixed(3)));
      lowers.push(Math.max(0.0, +(cg - 0.05).toFixed(3)));
    });
  }

  forecastChartInstance.data.datasets[0].data = [nowVal, ...pts];
  forecastChartInstance.data.datasets[1].data = [nowVal, ...uppers];
  forecastChartInstance.data.datasets[2].data = [nowVal, ...lowers];
  forecastChartInstance.update();

  // Render Feature Drivers in Monochrome
  renderFeatureAttribution(forecastData.feature_attributions || []);
}

function renderFeatureAttribution(drivers) {
  const container = document.getElementById('feature-drivers-list');
  if (!container) return;

  if (!drivers || drivers.length === 0) {
    container.innerHTML = '<div style="color:#71717a; font-size:12px;">No feature attribution available.</div>';
    return;
  }

  container.innerHTML = drivers.map(d => {
    const pct = Math.min(100, Math.round(d.weight * 100));
    return `
      <div style="display:flex; flex-direction:column; gap:4px; margin-bottom:8px;">
        <div style="display:flex; justify-content:space-between; font-size:11.5px;">
          <span style="color:#d4d4d8; font-weight:600;">${d.feature}</span>
          <span style="color:#ffffff; font-family:'JetBrains Mono'; font-weight:700;">${pct}%</span>
        </div>
        <div style="width:100%; height:4px; background:rgba(255,255,255,0.1); border-radius:2px; overflow:hidden;">
          <div style="width:${pct}%; height:100%; background:#ffffff;"></div>
        </div>
      </div>
    `;
  }).join('');
}

function setForecastMetric(metric) {
  currentForecastMetric = metric;
  document.querySelectorAll('.forecast-metric-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.metric === metric);
  });
  if (currentSegmentForecastData) {
    updateForecastDisplay(currentSegmentForecastData);
  }
}
