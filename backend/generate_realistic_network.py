import json
import os
import math
import numpy as np
import pandas as pd
import networkx as nx

def generate_hyderabad_realistic_network():
    data_dir = r"c:\projects\roadlyy\NEURAX_SMART_CITIES_TRAINING_V2"
    out_dir = r"c:\projects\roadlyy\data_preprocessed"
    os.makedirs(out_dir, exist_ok=True)
    
    nodes_df = pd.read_csv(os.path.join(data_dir, "nodes.csv"))
    net_df = pd.read_csv(os.path.join(data_dir, "network.csv"))
    signals_df = pd.read_csv(os.path.join(data_dir, "signal_plans.csv")) if os.path.exists(os.path.join(data_dir, "signal_plans.csv")) else pd.DataFrame()
    
    signals_by_node = {}
    if not signals_df.empty and 'node_id' in signals_df.columns:
        signals_by_node = signals_df.set_index('node_id').to_dict(orient='index')

    print(f"[Hyderabad Network Engine] Processing {len(nodes_df)} nodes and {len(net_df)} links...")

    # 1. Build Network Graph
    G = nx.Graph()
    for _, r in nodes_df.iterrows():
        G.add_node(r['node_id'])
        
    for _, r in net_df.iterrows():
        u = r['source_node']
        v = r['target_node']
        length = float(r['length_km'])
        is_art = (r['road_class'] == 'arterial')
        w = length * (0.6 if is_art else 1.0)
        G.add_edge(u, v, weight=w, length=length, road_class=r['road_class'])

    # 2. Realistic Hyderabad Geographic Anchors & Corridors
    # Anchor Hubs in Latitude, Longitude:
    # Hyderabad Center (Hussain Sagar / Tank Bund): 17.423, 78.474
    # HITEC City / Madhapur: 17.445, 78.380
    # Gachibowli / Financial District: 17.430, 78.348
    # Jubilee Hills / Banjara Hills: 17.428, 78.420
    # Panjagutta / Somajiguda: 17.426, 78.452
    # Begumpet / Secunderabad: 17.448, 78.490
    # Mehdipatnam / Masab Tank: 17.395, 78.440
    # Charminar / Old City / Koti: 17.365, 78.478
    # Uppal / Dilsukhnagar: 17.385, 78.535

    # We map the 120 graph nodes to an organic multi-ring urban layout centered around Hyderabad:
    # Core downtown (Hussain Sagar promenade & central business district)
    # Inner ring boulevard
    # Arterial radial corridors branching west (HITEC/Gachibowli), north (Secunderabad/Begumpet),
    # east (Uppal/Dilsukhnagar), south (Charminar/Mehdipatnam), and outer ring expressway arcs.

    np.random.seed(42)

    # Calculate graph-distance from central hub N055 / N066
    central_node = 'N055' if 'N055' in G else list(G.nodes)[0]
    shortest_paths = nx.single_source_shortest_path_length(G, central_node)

    # Assign initial organic urban coordinates with natural radial-concentric hierarchy
    init_positions = {}
    
    # Analyze graph structure
    for nid in G.nodes():
        idx = int(nid.replace('N', '')) - 1  # 0..119
        row = idx // 12  # 0..9
        col = idx % 12   # 0..11

        # Transform (col, row) grid coordinates into organic radial-concentric urban corridors
        # Normalized coordinates relative to city center (5.5, 4.5)
        cx = (col - 5.5) / 5.5
        cy = (row - 4.5) / 4.5

        # Radius and base angle
        r = math.hypot(cx, cy)
        theta = math.atan2(cy, cx)

        # Organic radial curvature & corridor stretching
        # Stretch along major Hyderabad East-West tech/heritage corridor (x-axis) and North-South axis
        corridor_stretch_x = 1.35 if abs(math.cos(theta)) > 0.4 else 1.0
        corridor_stretch_y = 1.10 if abs(math.sin(theta)) > 0.4 else 1.0

        # Natural serpentine curve (modeling the Musi river valley and Hussain Sagar contour)
        lake_contour = 0.22 * math.sin(2.2 * theta + 0.5) + 0.14 * math.cos(3.8 * theta)
        
        # Ring expressway curvature
        ring_r = math.pow(r, 0.85) * (1.0 + 0.25 * lake_contour)
        
        # Radial angle twisting (creates realistic spiral-radial urban avenues)
        angle_twist = 0.28 * math.sin(ring_r * 2.5) + 0.15 * math.cos(theta * 3.0)
        final_theta = theta + angle_twist

        # Deterministic organic offset per junction
        h = sum(ord(c) * (i + 7) for i, c in enumerate(nid))
        jitter_r = ((h % 23) - 11) * 0.018
        jitter_t = (((h * 13) % 19) - 9) * 0.025

        eff_r = max(0.25, ring_r + jitter_r)
        eff_theta = final_theta + jitter_t

        px = eff_r * math.cos(eff_theta) * corridor_stretch_x
        py = eff_r * math.sin(eff_theta) * corridor_stretch_y

        init_positions[nid] = np.array([px, py])

    # Physics-based spring relaxation with topological edge constraints
    # This untangles any tight overlaps while forming clean arterial avenues
    pos_relaxed = nx.spring_layout(
        G,
        pos=init_positions,
        iterations=260,
        k=0.95,
        weight='weight',
        seed=42
    )

    # Geo-reference to Hyderabad city coordinates
    # Center at Hussain Sagar / Tank Bund: Lat 17.418, Lon 78.472
    center_lat, center_lon = 17.418, 78.472
    scale_lat = 0.0145  # ~16km North-South coverage
    scale_lon = 0.0195  # ~22km East-West coverage (covering HITEC City to Uppal)

    # Normalize pos_relaxed
    xs = [p[0] for p in pos_relaxed.values()]
    ys = [p[1] for p in pos_relaxed.values()]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    range_x = max(1e-5, max_x - min_x)
    range_y = max(1e-5, max_y - min_y)

    node_coords = {}
    for nid, p in pos_relaxed.items():
        norm_x = 2.0 * (p[0] - min_x) / range_x - 1.0  # [-1, 1]
        norm_y = 2.0 * (p[1] - min_y) / range_y - 1.0  # [-1, 1]

        # Apply realistic urban sector shaping (Western Tech corridor expands further west)
        if norm_x < 0:
            norm_x *= 1.15  # Expand west toward HITEC / Gachibowli / Financial District
        
        # Add realistic Musi river valley dip in the south-central sector
        river_dip = -0.04 * math.exp(-((norm_x - 0.1)**2 + (norm_y + 0.3)**2) / 0.3)
        norm_y += river_dip

        lon = center_lon + norm_x * scale_lon * 5.8
        lat = center_lat + norm_y * scale_lat * 5.2
        node_coords[nid] = (round(lon, 7), round(lat, 7))

    # 3. Generate Realistic Multi-Segment Curved Road Polylines (436 Links)
    # Every road segment is generated with 10 to 14 high-precision intermediate coordinates
    # following realistic road curvature, boulevard bends, lane separation, and highway arcs.
    features = []

    def get_road_hash(s_id):
        return sum(ord(c) * (i + 1) * 41 for i, c in enumerate(s_id))

    for _, r in net_df.iterrows():
        seg_id = str(r['segment_id'])
        u, v = str(r['source_node']), str(r['target_node'])
        u_lon, u_lat = node_coords[u]
        v_lon, v_lat = node_coords[v]

        dx = v_lon - u_lon
        dy = v_lat - u_lat
        dist = math.hypot(dx, dy)
        if dist < 1e-7:
            dist = 1e-7

        # Unit normal perpendicular vector for lane separation & curvature
        norm_x = -dy / dist
        norm_y = dx / dist

        # Lateral lane separation (Dual-carriageway standard):
        # Eastbound/Northbound and Westbound/Southbound run on parallel lane tracks
        is_art = (r['road_class'] == 'arterial')
        is_bottleneck = bool(r['structural_bottleneck'] == 1)
        lanes = int(r['lanes'])
        
        lane_offset = 0.00032 if is_art else 0.00022
        u_start_lon = u_lon + norm_x * lane_offset
        u_start_lat = u_lat + norm_y * lane_offset
        v_end_lon = v_lon + norm_x * lane_offset
        v_end_lat = v_lat + norm_y * lane_offset

        # Compute natural road curvature (modeling urban street bends, highway flyovers, and lake contours)
        mid_lon = (u_lon + v_lon) / 2.0
        mid_lat = (u_lat + v_lat) / 2.0
        dist_to_center = math.hypot(mid_lon - center_lon, mid_lat - center_lat)
        angle_to_center = math.atan2(mid_lat - center_lat, mid_lon - center_lon)
        road_heading = math.atan2(dy, dx)

        # Detect if this is an arterial ring road or a radial spoke
        is_tangential_ring = abs(math.sin(road_heading - angle_to_center)) < 0.60
        
        rh = get_road_hash(seg_id)
        curve_sign = 1.0 if (rh % 2 == 0) else -1.0
        wobble_strength = ((rh % 100) / 100.0) * 0.0006 + 0.0004

        if is_tangential_ring:
            # Ring roads curve in sweeping arcs away from city center
            arc_direction = 1.0 if (dx * (mid_lat - center_lat) - dy * (mid_lon - center_lon)) > 0 else -1.0
            c_factor = (0.0012 + 0.0004 * math.sin(dist_to_center * 10)) * arc_direction
        else:
            # Radial arterial roads have gentle S-curves matching urban terrain
            c_factor = wobble_strength * curve_sign

        # Multi-point cubic spline control points for realistic highway geometry
        ctrl1_lon = u_start_lon + 0.30 * dx + norm_x * c_factor * 1.3
        ctrl1_lat = u_start_lat + 0.30 * dy + norm_y * c_factor * 1.3
        ctrl2_lon = u_start_lon + 0.70 * dx + norm_x * c_factor * 0.8
        ctrl2_lat = u_start_lat + 0.70 * dy + norm_y * c_factor * 0.8

        # Generate 12-segment smooth road polyline
        num_pts = 12
        coords = []
        for i in range(num_pts + 1):
            t = i / float(num_pts)
            # Smooth cubic Bézier interpolation
            bx = (1-t)**3 * u_start_lon + 3*(1-t)**2*t * ctrl1_lon + 3*(1-t)*t**2 * ctrl2_lon + t**3 * v_end_lon
            by = (1-t)**3 * u_start_lat + 3*(1-t)**2*t * ctrl1_lat + 3*(1-t)*t**2 * ctrl2_lat + t**3 * v_end_lat
            
            # Subtle natural micro-jitter to prevent artificial computerized straightness
            if 0 < i < num_pts:
                micro_j = 0.00008 * math.sin(t * math.pi * 3 + rh)
                bx += norm_x * micro_j
                by += norm_y * micro_j

            coords.append([round(bx, 7), round(by, 7)])

        feat = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": coords
            },
            "properties": {
                "segment_id": seg_id,
                "source_node": u,
                "target_node": v,
                "road_class": str(r['road_class']),
                "lanes": lanes,
                "free_flow_speed_kmh": float(r['free_flow_speed_kmh']),
                "capacity_vph": float(r['capacity_vph']),
                "length_km": float(r['length_km']),
                "grade_pct": float(r['grade_pct']) if 'grade_pct' in r and pd.notnull(r['grade_pct']) else 0.0,
                "structural_bottleneck": is_bottleneck,
                "importance": float(r['importance']) if pd.notnull(r['importance']) else 1.0,
                "signal_id": str(r['signal_id']) if pd.notnull(r['signal_id']) and str(r['signal_id']) != 'nan' else None
            }
        }
        features.append(feat)

    # 4. Generate Node Junction Features (120 Nodes)
    # We include node metadata for topology/signals, but rendering can keep them subtle
    for nid, (n_lon, n_lat) in node_coords.items():
        deg = G.degree(nid)
        sig_info = signals_by_node.get(nid, None)
        sig_id = sig_info.get('signal_id', None) if sig_info else None
        
        feat = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [round(n_lon, 7), round(n_lat, 7)]
            },
            "properties": {
                "node_id": nid,
                "degree": deg,
                "signal_id": sig_id,
                "cycle_s": float(sig_info['cycle_s']) if sig_info and 'cycle_s' in sig_info else None,
                "green_ratio": float(sig_info['green_ratio']) if sig_info and 'green_ratio' in sig_info else None,
                "is_signalized": sig_id is not None,
                "type": "intersection"
            }
        }
        features.append(feat)

    # 5. Output Final Enhanced GeoJSON
    geojson_data = {
        "type": "FeatureCollection",
        "metadata": {
            "title": "Hyderabad Metropolitan Road Network Digital Twin",
            "subtitle": "120 Intersections · 436 Directed Arterial & Collector Corridors",
            "nodes_count": len(nodes_df),
            "segments_count": len(net_df),
            "bottlenecks_count": int((net_df['structural_bottleneck'] == 1).sum()),
            "center": [center_lat, center_lon],
            "bounds": {
                "min_lon": min(c[0] for c in node_coords.values()),
                "max_lon": max(c[0] for c in node_coords.values()),
                "min_lat": min(c[1] for c in node_coords.values()),
                "max_lat": max(c[1] for c in node_coords.values())
            }
        },
        "features": features
    }

    out_file = os.path.join(out_dir, "network_enhanced.geojson")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(geojson_data, f, indent=2)

    print(f"[Hyderabad Network Engine] Done! Generated {len(features)} GeoJSON features to {out_file}.")
    print(f"Network Center: {center_lat}, {center_lon}")

if __name__ == "__main__":
    generate_hyderabad_realistic_network()
