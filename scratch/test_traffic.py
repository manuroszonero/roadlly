import pickle
import os

cache_path = 'data_preprocessed/traffic_full_cache.pkl'
if os.path.exists(cache_path):
    with open(cache_path, 'rb') as f:
        cache = pickle.load(f)
    print("Timestamps count:", len(cache['timestamps']))
    ts_list = cache['timestamps']
    for idx in [0, 20, 50, 80, 100, 140, 180]:
        if idx < len(ts_list):
            ts = ts_list[idx]
            tdata = cache['traffic'].get(ts, {})
            speeds = [v['speed_kmh'] for v in tdata.values() if 'speed_kmh' in v]
            congs = [v['congestion_index'] for v in tdata.values() if 'congestion_index' in v]
            flows = [v['flow_vph'] for v in tdata.values() if 'flow_vph' in v]
            print(f"{ts} -> {len(tdata)} segs | Avg spd: {sum(speeds)/len(speeds):.1f} | Avg cong: {sum(congs)/len(congs):.5f} | Max cong: {max(congs):.5f} | Cong > 0.005: {sum(1 for c in congs if c > 0.005)} | Cong > 0.01: {sum(1 for c in congs if c > 0.01)}")
