import os
import pickle
import pandas as pd
import numpy as np

DATA_DIR = r"c:\projects\roadlyy\data_preprocessed"

print("[Cache Builder] Loading all 19-day traffic observations...")
df_tr = pd.read_csv(os.path.join(DATA_DIR, "traffic_train.csv"))
df_val = pd.read_csv(os.path.join(DATA_DIR, "traffic_validation.csv"))
df_all = pd.concat([df_tr, df_val], ignore_index=True)

print("[Cache Builder] Loading forecast targets...")
ft_tr = pd.read_csv(os.path.join(DATA_DIR, "forecast_targets_train.csv"))
ft_val = pd.read_csv(os.path.join(DATA_DIR, "forecast_targets_validation.csv"))
ft_all = pd.concat([ft_tr, ft_val], ignore_index=True)

print("[Cache Builder] Grouping traffic by timestamp...")
traffic_cache = {}
for ts, group in df_all.groupby('timestamp'):
    traffic_cache[ts] = group.set_index('segment_id').to_dict(orient='index')

print("[Cache Builder] Grouping forecast targets by timestamp...")
forecast_cache = {}
for ts, group in ft_all.groupby('timestamp'):
    forecast_cache[ts] = group.set_index('segment_id').to_dict(orient='index')

cache_path = os.path.join(DATA_DIR, "traffic_full_cache.pkl")
with open(cache_path, "wb") as f:
    pickle.dump({
        "traffic": traffic_cache,
        "forecast": forecast_cache,
        "timestamps": sorted(list(traffic_cache.keys()))
    }, f, protocol=pickle.HIGHEST_PROTOCOL)

print(f"[Cache Builder] Successfully saved fast cache to {cache_path} ({len(traffic_cache)} timestamps)")
