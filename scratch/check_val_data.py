import pickle
import pandas as pd
import numpy as np

with open('data_preprocessed/traffic_full_cache.pkl', 'rb') as f:
    cache = pickle.load(f)

val_ts = [t for t in cache['timestamps'] if t.startswith('2026-01-16')]
print(f"Jan 16 timestamps count: {len(val_ts)}")

for idx in [0, 20, 60, 100, 150, 200, 250]:
    if idx < len(val_ts):
        ts = val_ts[idx]
        tdata = cache['traffic'].get(ts, {})
        congs = [v.get('congestion_index', 0.0) for v in tdata.values()]
        speeds = [v.get('speed_kmh', 0.0) for v in tdata.values()]
        print(f"TS: {ts} | Segs: {len(tdata)} | Spd min/avg/max: {min(speeds):.1f}/{np.mean(speeds):.1f}/{max(speeds):.1f} | Cong min/avg/max: {min(congs):.5f}/{np.mean(congs):.5f}/{max(congs):.5f}")
