import pickle
import numpy as np

with open('data_preprocessed/traffic_full_cache.pkl', 'rb') as f:
    cache = pickle.load(f)

# Look at 2026-01-01 02:00:00 (Night), 08:30:00 (Morning Peak), 13:00:00 (Midday), 18:00:00 (Evening Peak)
test_times = ['2026-01-01 02:00:00', '2026-01-01 08:30:00', '2026-01-01 13:00:00', '2026-01-01 18:00:00']

for ts in test_times:
    if ts not in cache['traffic']:
        # Find nearest
        ts = [t for t in cache['timestamps'] if t.startswith(ts[:13])][0]
    tdata = cache['traffic'][ts]
    congs = [v.get('congestion_index', 0.0) for v in tdata.values()]
    speeds = [v.get('speed_kmh', 0.0) for v in tdata.values()]
    flows = [v.get('flow_vph', 0.0) for v in tdata.values()]
    
    # Let's see how many would be Green, Yellow, Orange, Red under different thresholds
    print(f"\n--- Timestamp: {ts} ---")
    print(f"Congestion Min: {min(congs):.5f}, 25%: {np.percentile(congs, 25):.5f}, Med: {np.median(congs):.5f}, 75%: {np.percentile(congs, 75):.5f}, 90%: {np.percentile(congs, 90):.5f}, Max: {max(congs):.5f}")
    
    # Current thresholds: <0.003, <0.025, <0.090, >=0.090
    g = sum(1 for c in congs if c < 0.003)
    y = sum(1 for c in congs if 0.003 <= c < 0.025)
    o = sum(1 for c in congs if 0.025 <= c < 0.090)
    r = sum(1 for c in congs if c >= 0.090)
    print(f"Current bins -> Green: {g}, Yellow: {y}, Orange: {o}, Red: {r}")
