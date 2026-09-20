import os
import json
import pickle
import pandas as pd
import numpy as np
import networkx as nx
from datetime import datetime
from typing import Dict, List, Any, Optional

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_preprocessed")
if not os.path.exists(DATA_DIR):
    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "NEURAX_SMART_CITIES_TRAINING_V2")

class DataService:
    def __init__(self):
        print("[DataService] Initializing Roadlyy Data Service...")
        self.nodes_df = pd.read_csv(os.path.join(DATA_DIR, "nodes.csv"))
        self.network_df = pd.read_csv(os.path.join(DATA_DIR, "network.csv"))
        self.signals_df = pd.read_csv(os.path.join(DATA_DIR, "signal_plans.csv"))
        self.turns_df = pd.read_csv(os.path.join(DATA_DIR, "turn_restrictions.csv"))
        self.planning_df = pd.read_csv(os.path.join(DATA_DIR, "planning_candidates.csv"))
        self.od_df = pd.read_csv(os.path.join(DATA_DIR, "od_demand_profiles.csv"))
        self.scenarios_df = pd.read_csv(os.path.join(DATA_DIR, "scenario_examples.csv"))
        
        # Incidents & Roadworks
        self.incidents_train = pd.read_csv(os.path.join(DATA_DIR, "incidents_train.csv"))
        self.incidents_val = pd.read_csv(os.path.join(DATA_DIR, "incidents_validation.csv"))
        self.incidents_all = pd.concat([self.incidents_train, self.incidents_val], ignore_index=True)
        self.incidents_all['start_dt'] = pd.to_datetime(self.incidents_all['start_time'])
        self.incidents_all['end_dt'] = pd.to_datetime(self.incidents_all['end_time'])
        
        self.roadworks_train = pd.read_csv(os.path.join(DATA_DIR, "roadworks_train.csv"))
        self.roadworks_val = pd.read_csv(os.path.join(DATA_DIR, "roadworks_validation.csv"))
        self.roadworks_all = pd.concat([self.roadworks_train, self.roadworks_val], ignore_index=True)
        self.roadworks_all['start_dt'] = pd.to_datetime(self.roadworks_all['start_time'])
        self.roadworks_all['end_dt'] = pd.to_datetime(self.roadworks_all['end_time'])
        
        # Context
        self.context_train = pd.read_csv(os.path.join(DATA_DIR, "context_train.csv"))
        self.context_val = pd.read_csv(os.path.join(DATA_DIR, "context_validation.csv"))
        self.context_all = pd.concat([self.context_train, self.context_val], ignore_index=True)
        self.context_all = self.context_all.astype(object).where(pd.notnull(self.context_all), None)
        self.context_dict = self.context_all.set_index('timestamp').to_dict(orient='index')
        
        # Precompute Graph Topology
        self.graph = nx.DiGraph()
        self._build_graph()
        
        # Network metadata dictionary
        self.nodes_dict = {
            row['node_id']: {
                'id': row['node_id'],
                'x': float(row['x']),
                'y': float(row['y']),
                'lat': float(row['lat']),
                'lon': float(row['lon'])
            }
            for _, row in self.nodes_df.iterrows()
        }
        
        self.signals_dict = self.signals_df.set_index('signal_id').to_dict(orient='index')
        
        self.segments_dict = {}
        for _, row in self.network_df.iterrows():
            seg_id = row['segment_id']
            sig_id = row['signal_id'] if pd.notnull(row['signal_id']) else None
            sig_info = self.signals_dict.get(sig_id) if sig_id else None
            
            src_node = self.nodes_dict[row['source_node']]
            tgt_node = self.nodes_dict[row['target_node']]
            
            self.segments_dict[seg_id] = {
                'segment_id': seg_id,
                'source_node': row['source_node'],
                'target_node': row['target_node'],
                'source_coord': [src_node['lat'], src_node['lon']],
                'target_coord': [tgt_node['lat'], tgt_node['lon']],
                'road_class': row['road_class'],
                'lanes': int(row['lanes']),
                'free_flow_speed_kmh': float(row['free_flow_speed_kmh']),
                'capacity_vph': float(row['capacity_vph']),
                'length_km': float(row['length_km']),
                'grade_pct': float(row['grade_pct']),
                'signal_id': sig_id,
                'signal_info': sig_info,
                'structural_bottleneck': bool(row['structural_bottleneck'] == 1),
                'importance': float(row['importance']),
                'peak_capacity_factor': float(row['peak_capacity_factor'])
            }
            
        # Fast binary cache loading for instant sub-second startup across all 19 days
        cache_path = os.path.join(DATA_DIR, "traffic_full_cache.pkl")
        if os.path.exists(cache_path):
            print(f"[DataService] Loading precomputed 19-day cache from {cache_path}...")
            with open(cache_path, "rb") as f:
                cache_obj = pickle.load(f)
                self.traffic_by_timestamp = cache_obj["traffic"]
                self.forecast_by_timestamp = cache_obj["forecast"]
                self.all_timestamps = cache_obj["timestamps"]
            fval_path = os.path.join(DATA_DIR, "forecast_targets_validation.csv")
            if os.path.exists(fval_path):
                self.forecast_val_df = pd.read_csv(fval_path)
            else:
                self.forecast_val_df = pd.DataFrame()
        else:
            print("[DataService] Cache not found, loading CSVs...")
            self.traffic_val_df = pd.read_csv(os.path.join(DATA_DIR, "traffic_validation.csv"))
            self.forecast_val_df = pd.read_csv(os.path.join(DATA_DIR, "forecast_targets_validation.csv"))
            self.traffic_by_timestamp = {}
            for ts, group in self.traffic_val_df.groupby('timestamp'):
                self.traffic_by_timestamp[ts] = group.set_index('segment_id').to_dict(orient='index')
            self.forecast_by_timestamp = {}
            for ts, group in self.forecast_val_df.groupby('timestamp'):
                self.forecast_by_timestamp[ts] = group.set_index('segment_id').to_dict(orient='index')
            self.all_timestamps = sorted(list(self.traffic_by_timestamp.keys()))

        self.val_timestamps = [ts for ts in self.all_timestamps if ts.startswith("2026-01-16") or ts.startswith("2026-01-17") or ts.startswith("2026-01-18") or ts.startswith("2026-01-19")]
        self.train_timestamps = [ts for ts in self.all_timestamps if ts not in self.val_timestamps]
            
        # Planning candidates indexed
        self.planning_candidates = self.planning_df.to_dict(orient='records')
        self.planning_by_segment = {}
        for cand in self.planning_candidates:
            seg = cand['target_segment']
            if seg not in self.planning_by_segment:
                self.planning_by_segment[seg] = []
            self.planning_by_segment[seg].append(cand)
            
        print(f"[DataService] Initialized successfully. Segments: {len(self.segments_dict)}, Nodes: {len(self.nodes_dict)}, Val Timestamps: {len(self.val_timestamps)}")

    def _build_graph(self):
        for _, row in self.nodes_df.iterrows():
            self.graph.add_node(row['node_id'], lat=row['lat'], lon=row['lon'], x=row['x'], y=row['y'])
            
        for _, row in self.network_df.iterrows():
            self.graph.add_edge(
                row['source_node'],
                row['target_node'],
                segment_id=row['segment_id'],
                length_km=row['length_km'],
                speed_kmh=row['free_flow_speed_kmh'],
                capacity=row['capacity_vph'],
                road_class=row['road_class'],
                lanes=row['lanes'],
                bottleneck=row['structural_bottleneck']
            )

    def get_network_geojson(self) -> Dict[str, Any]:
        """Returns full network topology as GeoJSON — uses enhanced real-road geometry if available."""
        
        # Prefer pre-built enhanced GeoJSON (OSM-snapped or bezier-curved roads)
        enhanced_path = os.path.join(DATA_DIR, "network_enhanced.geojson")
        if os.path.exists(enhanced_path):
            with open(enhanced_path, "r") as f:
                geojson = json.load(f)
            # Ensure all segment properties are present (add any missing from segments_dict)
            for feat in geojson.get("features", []):
                if feat.get("geometry", {}).get("type") == "LineString":
                    seg_id = feat.get("properties", {}).get("segment_id")
                    if seg_id and seg_id in self.segments_dict:
                        seg = self.segments_dict[seg_id]
                        props = feat["properties"]
                        # Fill in any missing fields
                        props.setdefault("structural_bottleneck", seg["structural_bottleneck"])
                        props.setdefault("importance", seg["importance"])
            geojson["metadata"]["bottlenecks_count"] = sum(
                1 for s in self.segments_dict.values() if s["structural_bottleneck"]
            )
            return geojson
        
        # Fallback: generate 2-point straight lines from grid nodes
        features = []
        
        for seg_id, seg in self.segments_dict.items():
            src = seg['source_coord']
            tgt = seg['target_coord']
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [src[1], src[0]],
                        [tgt[1], tgt[0]]
                    ]
                },
                "properties": {
                    "segment_id": seg_id,
                    "source_node": seg['source_node'],
                    "target_node": seg['target_node'],
                    "road_class": seg['road_class'],
                    "lanes": seg['lanes'],
                    "free_flow_speed_kmh": seg['free_flow_speed_kmh'],
                    "capacity_vph": seg['capacity_vph'],
                    "length_km": seg['length_km'],
                    "structural_bottleneck": seg['structural_bottleneck'],
                    "importance": seg['importance'],
                    "signal_id": seg['signal_id']
                }
            })
            
        for node_id, node in self.nodes_dict.items():
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [node['lon'], node['lat']]
                },
                "properties": {
                    "node_id": node_id,
                    "x": node['x'],
                    "y": node['y'],
                    "type": "intersection"
                }
            })
            
        return {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "nodes_count": len(self.nodes_dict),
                "segments_count": len(self.segments_dict),
                "bottlenecks_count": sum(1 for s in self.segments_dict.values() if s['structural_bottleneck']),
                "center": [17.381, 78.449]
            }
        }


    def _generate_synthetic_slice(self, timestamp: str) -> Dict[str, Any]:
        """Dynamically synthesizes realistic citywide traffic state for any custom/unseen timestamp."""
        try:
            ts_dt = pd.to_datetime(timestamp)
            hour = ts_dt.hour
            dow = ts_dt.dayofweek
            minute = ts_dt.minute
        except Exception:
            ts_dt = pd.to_datetime("2026-01-20 08:30:00")
            hour, dow, minute = 8, 1, 30

        is_weekend = (dow >= 5)
        # Diurnal rush-hour curves
        if is_weekend:
            # Weekend peak between 12:00 and 19:00
            time_factor = 0.85 if 12 <= hour <= 19 else 0.40
        else:
            # Weekday morning peak (7:30-10:00) and evening peak (16:30-20:00)
            if (7 <= hour <= 10) or (16 <= hour <= 20):
                time_factor = 0.88 + 0.08 * np.sin((minute / 60.0) * np.pi)
            elif (11 <= hour <= 15):
                time_factor = 0.65
            else:
                time_factor = 0.25 + 0.10 * (hour / 24.0)

        # Context (synthetic weather)
        temp_c = round(22.0 + 8.0 * np.sin((hour - 6) / 24.0 * 2 * np.pi), 1)
        rain_mm = 0.0
        ctx = {
            'temperature_c': temp_c,
            'rain_intensity': rain_mm,
            'event_level': 0,
            'is_weekend': 1 if is_weekend else 0
        }

        # Check incidents in database
        active_incidents = []
        for _, inc in self.incidents_all.iterrows():
            if inc['start_dt'] <= ts_dt <= inc['end_dt']:
                active_incidents.append({
                    'incident_id': inc['incident_id'],
                    'segment_id': inc['segment_id'],
                    'incident_type': inc['incident_type'],
                    'severity': int(inc['severity']),
                    'lanes_blocked': int(inc['lanes_blocked']),
                    'start_time': str(inc['start_time']),
                    'end_time': str(inc['end_time'])
                })

        active_roadworks = []
        for _, rw in self.roadworks_all.iterrows():
            if rw['start_dt'] <= ts_dt <= rw['end_dt']:
                active_roadworks.append({
                    'work_id': rw['work_id'],
                    'segment_id': rw['segment_id'],
                    'work_type': rw['work_type'],
                    'closure_fraction': float(rw['closure_fraction']),
                    'start_time': str(rw['start_time']),
                    'end_time': str(rw['end_time'])
                })

        incident_segs = {inc['segment_id']: inc for inc in active_incidents}

        segments_data = {}
        total_delay = 0.0
        total_queue = 0.0
        congested_count = 0

        for seg_id, seg_meta in self.segments_dict.items():
            free_spd = float(seg_meta['free_flow_speed_kmh'])
            cap = float(seg_meta['capacity_vph'])
            is_bn = bool(seg_meta['structural_bottleneck'])

            # Seed pseudo-random per segment and hour for consistent playback
            seg_num = int(''.join(c for c in seg_id if c.isdigit()) or 1)
            seg_hash = (seg_num * 37 + hour * 13 + minute) % 100 / 100.0
            noise = (seg_hash - 0.5) * 0.08
            
            bn_factor = 1.25 if is_bn else 1.0
            flow = max(40.0, min(cap * 1.2, cap * (time_factor * bn_factor + noise)))
            vc = flow / max(1.0, cap)
            
            # Speed from BPR-like congestion curve
            speed = max(8.0, free_spd / (1.0 + 0.45 * (vc ** 3.5)))
            
            # Incident impact if on this link
            if seg_id in incident_segs:
                inc = incident_segs[seg_id]
                sev = inc.get('severity', 2)
                speed = max(5.0, speed * (0.45 / sev))
                flow = flow * 0.65

            delay = max(0.0, (seg_meta['length_km'] / max(1.0, speed) - seg_meta['length_km'] / max(1.0, free_spd)) * 60.0)
            congestion = max(0.0, min(1.0, (1.0 - (speed / max(1.0, free_spd))) * 0.75 + (vc * 0.25)))
            queue = max(0.0, (flow * delay / 60.0) * (0.8 if is_bn else 0.4))
            occupancy = min(100.0, vc * 70.0 + congestion * 30.0)

            total_delay += delay
            total_queue += queue
            if congestion > 0.05:
                congested_count += 1

            # Multi-horizon forecast
            f15_spd = max(6.0, round(speed * (0.95 if vc > 0.8 else 1.02), 2))
            f30_spd = max(6.0, round(speed * (0.92 if vc > 0.8 else 1.04), 2))
            f45_spd = max(6.0, round(speed * (0.90 if vc > 0.8 else 1.05), 2))
            f60_spd = max(6.0, round(speed * (0.88 if vc > 0.8 else 1.05), 2))

            segments_data[seg_id] = {
                'speed_kmh': round(speed, 2),
                'flow_vph': round(flow, 1),
                'occupancy_pct': round(occupancy, 2),
                'delay_min': round(delay, 2),
                'queue_length_veh': round(queue, 1),
                'congestion_index': round(congestion, 4),
                'free_flow_speed_kmh': free_spd,
                'capacity_vph': cap,
                'forecast': {
                    'speed_15m': f15_spd,
                    'flow_15m': round(flow * 1.03, 1),
                    'congestion_15m': round(max(0.0, 1.0 - f15_spd / free_spd), 4),
                    'speed_30m': f30_spd,
                    'flow_30m': round(flow * 1.05, 1),
                    'congestion_30m': round(max(0.0, 1.0 - f30_spd / free_spd), 4),
                    'speed_45m': f45_spd,
                    'flow_45m': round(flow * 1.07, 1),
                    'congestion_45m': round(max(0.0, 1.0 - f45_spd / free_spd), 4),
                    'speed_60m': f60_spd,
                    'flow_60m': round(flow * 1.08, 1),
                    'congestion_60m': round(max(0.0, 1.0 - f60_spd / free_spd), 4),
                }
            }

        return {
            'timestamp': timestamp,
            'context': ctx,
            'network_summary': {
                'avg_network_speed': round(np.mean([s['speed_kmh'] for s in segments_data.values()]), 2),
                'total_network_flow': round(sum([s['flow_vph'] for s in segments_data.values()]), 1),
                'total_delay_min': round(total_delay, 1),
                'total_queue_veh': round(total_queue, 1),
                'congested_segments': congested_count,
                'active_incidents_count': len(active_incidents),
                'active_roadworks_count': len(active_roadworks)
            },
            'active_incidents': active_incidents,
            'active_roadworks': active_roadworks,
            'segments': segments_data
        }

    def get_traffic_slice(self, timestamp: str) -> Dict[str, Any]:
        """Returns traffic metrics and active disruptions for all segments at given timestamp."""
        if timestamp not in self.traffic_by_timestamp:
            return self._generate_synthetic_slice(timestamp)
            
        traffic_map = self.traffic_by_timestamp.get(timestamp, {})
        forecast_map = self.forecast_by_timestamp.get(timestamp, {})
        ctx = self.context_dict.get(timestamp, {})
        
        ts_dt = pd.to_datetime(timestamp)
        
        # Check active incidents
        active_incidents = []
        for _, inc in self.incidents_all.iterrows():
            if inc['start_dt'] <= ts_dt <= inc['end_dt']:
                active_incidents.append({
                    'incident_id': inc['incident_id'],
                    'segment_id': inc['segment_id'],
                    'incident_type': inc['incident_type'],
                    'severity': int(inc['severity']),
                    'lanes_blocked': int(inc['lanes_blocked']),
                    'start_time': str(inc['start_time']),
                    'end_time': str(inc['end_time'])
                })
                
        # Check active roadworks
        active_roadworks = []
        for _, rw in self.roadworks_all.iterrows():
            if rw['start_dt'] <= ts_dt <= rw['end_dt']:
                active_roadworks.append({
                    'work_id': rw['work_id'],
                    'segment_id': rw['segment_id'],
                    'work_type': rw['work_type'],
                    'closure_fraction': float(rw['closure_fraction']),
                    'start_time': str(rw['start_time']),
                    'end_time': str(rw['end_time'])
                })
                
        segments_data = {}
        total_delay = 0.0
        total_queue = 0.0
        congested_count = 0
        
        for seg_id, seg_meta in self.segments_dict.items():
            t_data = traffic_map.get(seg_id, {})
            f_data = forecast_map.get(seg_id, {})
            
            speed = float(t_data.get('speed_kmh', seg_meta['free_flow_speed_kmh']))
            flow = float(t_data.get('flow_vph', 0.0))
            occupancy = float(t_data.get('occupancy_pct', 10.0))
            delay = float(t_data.get('delay_min', 0.0))
            queue = float(t_data.get('queue_length_veh', 0.0))
            congestion = float(t_data.get('congestion_index', 0.0))
            
            total_delay += delay
            total_queue += queue
            if congestion > 0.05:
                congested_count += 1
                
            segments_data[seg_id] = {
                'speed_kmh': speed,
                'flow_vph': flow,
                'occupancy_pct': occupancy,
                'delay_min': delay,
                'queue_length_veh': queue,
                'congestion_index': congestion,
                'free_flow_speed_kmh': seg_meta['free_flow_speed_kmh'],
                'capacity_vph': seg_meta['capacity_vph'],
                'forecast': {
                    'speed_15m': f_data.get('target_speed_15m'),
                    'flow_15m': f_data.get('target_flow_15m'),
                    'congestion_15m': f_data.get('target_congestion_15m'),
                    'speed_30m': f_data.get('target_speed_30m'),
                    'flow_30m': f_data.get('target_flow_30m'),
                    'congestion_30m': f_data.get('target_congestion_30m'),
                    'speed_45m': f_data.get('target_speed_45m'),
                    'flow_45m': f_data.get('target_flow_45m'),
                    'congestion_45m': f_data.get('target_congestion_45m'),
                    'speed_60m': f_data.get('target_speed_60m'),
                    'flow_60m': f_data.get('target_flow_60m'),
                    'congestion_60m': f_data.get('target_congestion_60m'),
                }
            }
            
        return {
            'timestamp': timestamp,
            'context': ctx,
            'network_summary': {
                'avg_network_speed': round(np.mean([s['speed_kmh'] for s in segments_data.values()]), 2),
                'total_network_flow': round(sum([s['flow_vph'] for s in segments_data.values()]), 1),
                'total_delay_min': round(total_delay, 1),
                'total_queue_veh': round(total_queue, 1),
                'congested_segments': congested_count,
                'active_incidents_count': len(active_incidents),
                'active_roadworks_count': len(active_roadworks)
            },
            'active_incidents': active_incidents,
            'active_roadworks': active_roadworks,
            'segments': segments_data
        }

    def get_segment_history(self, segment_id: str) -> Dict[str, Any]:
        """Returns time-series history across validation split for a specific segment."""
        if segment_id not in self.segments_dict:
            return {'error': 'Invalid segment_id'}
            
        seg_meta = self.segments_dict[segment_id]
        timestamps = []
        speeds = []
        flows = []
        delays = []
        congestions = []
        
        for ts in self.val_timestamps:
            t_data = self.traffic_by_timestamp.get(ts, {}).get(segment_id, {})
            if t_data:
                timestamps.append(ts)
                speeds.append(float(t_data.get('speed_kmh', 0)))
                flows.append(float(t_data.get('flow_vph', 0)))
                delays.append(float(t_data.get('delay_min', 0)))
                congestions.append(float(t_data.get('congestion_index', 0)))
                
        # Candidate interventions for this segment
        candidates = self.planning_by_segment.get(segment_id, [])
        
        return {
            'segment_id': segment_id,
            'meta': seg_meta,
            'candidates': candidates,
            'timestamps': timestamps,
            'speed_kmh': speeds,
            'flow_vph': flows,
            'delay_min': delays,
            'congestion_index': congestions
        }

data_service = DataService()
