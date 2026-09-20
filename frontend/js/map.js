// ==========================================================================
// ROADLYY GEOSPATIAL NETWORK MAP ENGINE (MONOCHROME B&W EDITION)
// ==========================================================================

let mapInstance = null;
let networkGeoJson = null;
let segmentLayers = {};      // { segId: { layer (glow), topLayer (main), feature, midPoint } }
let nodeMarkers = {};        // { nodeId: circleMarker }
let calloutMarkers = {};     // { segId: marker }
let incidentMarkers = [];    // array of incident/hazard markers
let selectedEndpointMarkers = []; // [sourceMarker, targetMarker]
let activeSegmentId = null;
let currentMetricMode = 'congestion_index';
let showBottlenecksOnly = false;

// Prominent road IDs to show floating callout badges
const PROMINENT_CALLOUTS = ['R0344', 'R0287', 'R0176', 'R0436', 'R0189', 'R0621', 'R0001', 'R0006'];

// Road-class → visual width styling for realistic urban hierarchy
const ROAD_WEIGHT = {
  motorway: 7.0,
  arterial: 5.5,
  collector: 3.5,
  local: 2.5
};
const GLOW_WEIGHT_MULT = 2.4;

function initMap() {
  if (mapInstance) return Promise.resolve();

  // Initialize Leaflet Map centered on Hyderabad metropolitan core
  mapInstance = L.map('leaflet-map', {
    center: [17.418, 78.472],
    zoom: 12,
    zoomControl: true,
    attributionControl: false
  });

  // Esri World Dark Gray Canvas (Watermark-Free, High-Performance Dark Basemap)
  L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
    maxZoom: 19,
    attribution: ''
  }).addTo(mapInstance);

  // Esri World Dark Gray Reference (Clean Street & Neighborhood Labels)
  L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}', {
    maxZoom: 19,
    opacity: 0.85,
    attribution: ''
  }).addTo(mapInstance);

  // Fetch and render the realistic Hyderabad road network
  return fetchNetworkTopology();
}

async function fetchNetworkTopology() {
  try {
    const res = await fetch('/api/network');
    networkGeoJson = await res.json();
    renderNetworkTopology(networkGeoJson);
  } catch (err) {
    console.error('Failed to load network topology:', err);
  }
}

function _getBaseWeight(feature) {
  const rc = (feature.properties.road_class || 'collector').toLowerCase();
  return ROAD_WEIGHT[rc] || 3.5;
}

function renderNetworkTopology(geoData) {
  if (!geoData || !geoData.features) return;

  // Clear existing segment layers
  Object.values(segmentLayers).forEach(s => {
    if (s.layer) mapInstance.removeLayer(s.layer);
    if (s.topLayer) mapInstance.removeLayer(s.topLayer);
  });
  segmentLayers = {};

  // Clear existing node markers
  Object.values(nodeMarkers).forEach(m => mapInstance.removeLayer(m));
  nodeMarkers = {};

  // Clear callout markers
  Object.values(calloutMarkers).forEach(m => mapInstance.removeLayer(m));
  calloutMarkers = {};

  const lineFeatures = [];
  const pointFeatures = [];

  geoData.features.forEach(feat => {
    if (feat.geometry.type === 'LineString') {
      lineFeatures.push(feat);
    } else if (feat.geometry.type === 'Point') {
      pointFeatures.push(feat);
    }
  });

  // 1. Render Realistic Urban Road Segments (436 Links)
  lineFeatures.forEach(feature => {
    const segId = feature.properties.segment_id;
    const coords = feature.geometry.coordinates.map(c => [c[1], c[0]]);
    const isBottleneck = feature.properties.structural_bottleneck;
    const roadClass = (feature.properties.road_class || 'collector').toLowerCase();
    const baseW = _getBaseWeight(feature);
    const baseColor = isBottleneck ? '#ef4444' : '#10b981';

    // Glowing Underlay / Ambient Halo Polyline
    const glowLine = L.polyline(coords, {
      color: baseColor,
      weight: baseW * GLOW_WEIGHT_MULT,
      opacity: isBottleneck ? 0.45 : 0.22,
      lineCap: 'round',
      lineJoin: 'round',
      interactive: false
    }).addTo(mapInstance);

    // Sharp Foreground Road Polyline
    const topLine = L.polyline(coords, {
      color: baseColor,
      weight: baseW,
      opacity: 0.95,
      lineCap: 'round',
      lineJoin: 'round',
      smoothFactor: 1.0
    }).addTo(mapInstance);

    const midIdx = Math.floor(coords.length / 2);
    const midPoint = coords[midIdx] || coords[0];

    _bindSegmentTooltip(topLine, feature);

    topLine.on('click', () => selectSegment(segId));

    topLine.on('mouseover', () => {
      if (segId !== activeSegmentId) {
        topLine.setStyle({ weight: baseW + 2.5, opacity: 1.0, color: '#ffffff' });
        glowLine.setStyle({ opacity: 0.55, weight: (baseW + 2.5) * GLOW_WEIGHT_MULT, color: '#ffffff' });
      }
    });

    topLine.on('mouseout', () => {
      if (segId !== activeSegmentId) {
        let curColor = baseColor;
        if (window.currentSliceData && window.currentSliceData.segments && window.currentSliceData.segments[segId]) {
          curColor = _trafficColor(window.currentSliceData.segments[segId]);
        }
        topLine.setStyle({ weight: baseW, opacity: 0.95, color: curColor });
        glowLine.setStyle({ opacity: isBottleneck ? 0.45 : 0.22, weight: baseW * GLOW_WEIGHT_MULT, color: curColor });
      }
    });

    segmentLayers[segId] = { layer: glowLine, topLayer: topLine, feature, midPoint, coords };
  });

  // 2. Render Incident / Warning Beacons
  renderIncidentBeacons();

  // 3. Render Subtle Key Corridor Badges
  renderProminentCalloutBadges();

  // Fit bounds nicely to entire metropolitan road network
  if (Object.keys(segmentLayers).length > 0) {
    const allLayers = Object.values(segmentLayers).map(s => s.topLayer);
    const group = new L.featureGroup(allLayers);
    mapInstance.fitBounds(group.getBounds(), { padding: [30, 30] });
  }

  // Immediately apply slice traffic colors if slice data is already loaded
  if (window.currentSliceData && window.currentSliceData.segments) {
    updateMapTrafficColors(window.currentSliceData.segments);
  }
}

function renderProminentCalloutBadges() {
  PROMINENT_CALLOUTS.forEach(segId => {
    if (segId === activeSegmentId) return;
    const s = segmentLayers[segId];
    if (!s) return;

    const isBot = s.feature.properties.structural_bottleneck;
    const badgeClass = isBot ? 'bw-bot-badge' : 'bw-badge';

    const icon = L.divIcon({
      className: '',
      html: `<div class="road-callout-pill ${badgeClass}">${segId}</div>`,
      iconSize: [50, 20],
      iconAnchor: [25, 10]
    });

    const marker = L.marker(s.midPoint, { icon, interactive: true }).addTo(mapInstance);
    marker.on('click', () => selectSegment(segId));
    calloutMarkers[segId] = marker;
  });
}

function renderIncidentBeacons() {
  incidentMarkers.forEach(m => mapInstance.removeLayer(m));
  incidentMarkers = [];

  const beaconSpecs = [
    { segId: 'R0344', type: 'incident', iconHtml: '<div class="incident-pulse-marker">!</div>' },
    { segId: 'R0621', type: 'warning', iconHtml: '<div class="warning-triangle-marker">!</div>' },
    { segId: 'R0176', type: 'event', iconHtml: '<div class="purple-event-marker">+</div>' }
  ];

  beaconSpecs.forEach(b => {
    const seg = segmentLayers[b.segId];
    if (!seg) return;

    const icon = L.divIcon({
      className: '',
      html: b.iconHtml,
      iconSize: [24, 24],
      iconAnchor: [12, 12]
    });

    const marker = L.marker(seg.midPoint, { icon, interactive: true, zIndexOffset: 1000 }).addTo(mapInstance);
    marker.bindTooltip(`
      <div class="roadlyy-tooltip">
        <div style="color:#ffffff; font-weight:800; font-size:12px;">Active Event / Incident</div>
        <div style="color:#d4d4d8;">Segment: <b>${b.segId}</b></div>
      </div>
    `, { className: 'roadlyy-tooltip' });
    marker.on('click', () => selectSegment(b.segId));
    incidentMarkers.push(marker);
  });
}

function _bindSegmentTooltip(layer, feature) {
  const props = feature.properties;
  const segId = props.segment_id;
  const isBottleneck = props.structural_bottleneck;
  const roadClass = (props.road_class || 'collector').toUpperCase();

  const tipHtml = `
    <div class="roadlyy-tooltip" style="font-size:12px; line-height:1.6; min-width:190px;">
      <div style="font-weight:800; font-size:13px; color:#ffffff; border-bottom:1px solid rgba(255,255,255,0.2); padding-bottom:3px; margin-bottom:5px; display:flex; justify-content:space-between; align-items:center;">
        <span>${segId}</span>
        <span style="font-size:10.5px; font-weight:700; color:#ffffff; background:rgba(255,255,255,0.15); padding:1px 6px; border-radius:4px;">${roadClass}</span>
      </div>
      <div style="color:#d4d4d8;">Route: <b>${props.source_node} &rarr; ${props.target_node}</b></div>
      <div style="color:#d4d4d8;">Free-flow Speed: <b>${props.free_flow_speed_kmh} km/h</b></div>
      <div style="color:#d4d4d8;">Capacity: <b>${props.capacity_vph} vph</b> (${props.lanes} lanes)</div>
      <div style="color:#d4d4d8;">Length: <b>${props.length_km} km</b></div>
      ${isBottleneck ? '<div style="color:#ffffff; font-weight:800; margin-top:4px;">Structural Bottleneck Corridor</div>' : ''}
      <div style="color:#a1a1aa; font-size:11px; margin-top:6px; border-top:1px dashed rgba(255,255,255,0.15); padding-top:4px;">Click to inspect deep-dive &amp; forecast</div>
    </div>
  `;

  layer.bindTooltip(tipHtml, { sticky: true, className: 'roadlyy-tooltip', opacity: 0.98 });
}

function _trafficColor(metrics) {
  if (!metrics) return '#10b981';

  if (currentMetricMode === 'congestion_index') {
    const cong = parseFloat(metrics.congestion_index) || 0;
    if (cong < 0.003) return '#10b981';   // Free-flow / Calm (Emerald Green)
    if (cong < 0.015) return '#84cc16';   // Light / Normal Flow (Lime Green)
    if (cong < 0.045) return '#f59e0b';   // Moderate / Building Surge (Amber Yellow)
    if (cong < 0.085) return '#f97316';   // Heavy Rush (Vivid Orange)
    return '#ef4444';                     // Severe Congestion / Gridlock (Crimson Red)
  } else if (currentMetricMode === 'speed_kmh') {
    const spd = parseFloat(metrics.speed_kmh) || 0;
    const ff = parseFloat(metrics.free_flow_speed_kmh) || 50;
    const r = spd / Math.max(1, ff);
    if (r >= 0.92) return '#10b981';      // Fast / Free-flow (Green)
    if (r >= 0.80) return '#84cc16';      // Normal (Lime)
    if (r >= 0.65) return '#f59e0b';      // Moderate (Amber)
    if (r >= 0.50) return '#f97316';      // Heavy (Orange)
    return '#ef4444';                     // Severe Delay (Red)
  } else if (currentMetricMode === 'flow_vph') {
    const flw = parseFloat(metrics.flow_vph) || 0;
    const cap = parseFloat(metrics.capacity_vph) || 2000;
    const r = flw / Math.max(1, cap);
    if (r > 0.80) return '#ef4444';      // Near Capacity (Red)
    if (r > 0.60) return '#f97316';      // Heavy Flow (Orange)
    if (r > 0.40) return '#f59e0b';      // Moderate Flow (Amber)
    if (r > 0.20) return '#84cc16';      // Light Flow (Lime)
    return '#10b981';                     // Free / Low Flow (Green)
  }
  return '#10b981';
}

function updateMapTrafficColors(segmentsData) {
  if (!segmentsData) return;

  Object.entries(segmentsData).forEach(([segId, metrics]) => {
    const item = segmentLayers[segId];
    if (!item) return;

    const baseW = _getBaseWeight(item.feature);
    const isBottleneck = item.feature.properties.structural_bottleneck;
    const isActive = (segId === activeSegmentId);
    const color = isActive ? '#00f2fe' : _trafficColor(metrics);
    const topW = isActive ? baseW + 4.5 : baseW;

    if (showBottlenecksOnly) {
      item.topLayer.setStyle({
        color: isBottleneck ? '#ef4444' : '#27272a',
        weight: isBottleneck ? baseW + 3.0 : baseW,
        opacity: isBottleneck ? 1.0 : 0.05
      });
      item.layer.setStyle({
        color: isBottleneck ? '#ef4444' : '#27272a',
        weight: (isBottleneck ? baseW + 3.0 : baseW) * GLOW_WEIGHT_MULT,
        opacity: isBottleneck ? 0.70 : 0.01
      });
    } else {
      item.topLayer.setStyle({
        color: color,
        weight: topW,
        opacity: isActive ? 1.0 : 0.95
      });

      item.layer.setStyle({
        color: color,
        weight: topW * GLOW_WEIGHT_MULT,
        opacity: isActive ? 0.80 : (color === '#10b981' ? 0.18 : (color === '#84cc16' ? 0.25 : 0.45))
      });
    }
  });
}

function selectSegment(segId) {
  selectedEndpointMarkers.forEach(m => mapInstance.removeLayer(m));
  selectedEndpointMarkers = [];

  if (activeSegmentId && segmentLayers[activeSegmentId]) {
    const prev = segmentLayers[activeSegmentId];
    const prevW = _getBaseWeight(prev.feature);
    
    let baseColor = prev.feature.properties.structural_bottleneck ? '#ef4444' : '#10b981';
    if (window.currentSliceData && window.currentSliceData.segments && window.currentSliceData.segments[activeSegmentId]) {
      baseColor = _trafficColor(window.currentSliceData.segments[activeSegmentId]);
    }
    prev.topLayer.setStyle({ color: baseColor, weight: prevW, opacity: 0.92 });
    prev.layer.setStyle({ color: baseColor, weight: prevW * GLOW_WEIGHT_MULT, opacity: 0.25 });
  }

  activeSegmentId = segId;

  if (segmentLayers[segId]) {
    const cur = segmentLayers[segId];
    const curW = _getBaseWeight(cur.feature);

    cur.topLayer.setStyle({ color: '#00f2fe', weight: curW + 4.5, opacity: 1.0 });
    cur.layer.setStyle({ color: '#00f2fe', weight: (curW + 4.5) * GLOW_WEIGHT_MULT, opacity: 0.80 });
    cur.topLayer.bringToFront();

    if (cur.coords && cur.coords.length >= 2) {
      const startPt = cur.coords[0];
      const endPt = cur.coords[cur.coords.length - 1];

      [startPt, endPt].forEach(pt => {
        const ring = L.circleMarker(pt, {
          radius: 7.5,
          color: '#00f2fe',
          weight: 2.5,
          fillColor: '#000000',
          fillOpacity: 1.0,
          interactive: false
        }).addTo(mapInstance);
        selectedEndpointMarkers.push(ring);
      });
    }

    if (calloutMarkers['active_callout']) {
      mapInstance.removeLayer(calloutMarkers['active_callout']);
    }
    const icon = L.divIcon({
      className: '',
      html: `<div class="road-callout-pill bw-sel-badge">${segId}</div>`,
      iconSize: [58, 24],
      iconAnchor: [29, 12]
    });
    const actMarker = L.marker(cur.midPoint, { icon, zIndexOffset: 2000 }).addTo(mapInstance);
    calloutMarkers['active_callout'] = actMarker;
  }

  if (window.onSegmentSelected) {
    window.onSegmentSelected(segId);
  }
}

function toggleBottleneckHighlights() {
  showBottlenecksOnly = !showBottlenecksOnly;
  const btn = document.getElementById('toggle-bottlenecks-btn');
  if (btn) {
    btn.classList.toggle('active', showBottlenecksOnly);
    btn.textContent = showBottlenecksOnly ? 'Show All Roads' : 'Bottleneck';
  }

  Object.entries(segmentLayers).forEach(([segId, item]) => {
    const isB = item.feature.properties.structural_bottleneck;
    const baseW = _getBaseWeight(item.feature);
    if (showBottlenecksOnly) {
      item.topLayer.setStyle({
        opacity: isB ? 1.0 : 0.05,
        weight: isB ? baseW + 3.0 : baseW,
        color: isB ? '#ef4444' : '#27272a'
      });
      item.layer.setStyle({
        opacity: isB ? 0.70 : 0.01,
        color: isB ? '#ef4444' : '#27272a'
      });
      if (isB) item.topLayer.bringToFront();
    } else {
      let color = '#10b981';
      if (window.currentSliceData && window.currentSliceData.segments && window.currentSliceData.segments[segId]) {
        color = _trafficColor(window.currentSliceData.segments[segId]);
      }
      item.topLayer.setStyle({ opacity: 0.92, weight: baseW, color: color });
      item.layer.setStyle({ opacity: isB ? 0.45 : 0.25, weight: baseW * GLOW_WEIGHT_MULT, color: color });
    }
  });
}

function setMetricColorMode(mode) {
  currentMetricMode = mode;
  if (window.currentSliceData && window.currentSliceData.segments) {
    updateMapTrafficColors(window.currentSliceData.segments);
  }
}
