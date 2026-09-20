import os
import json
import pandas as pd
import numpy as np
from datetime import datetime

DATA_DIR = r"c:\projects\roadlyy\NEURAX_SMART_CITIES_TRAINING_V2"
OUT_DIR = r"c:\projects\roadlyy\data_preprocessed"
os.makedirs(OUT_DIR, exist_ok=True)

print("=" * 80)
print("ROADLYY INDUSTRIAL DATA PREPROCESSING & CLEANING PIPELINE")
print("=" * 80)

# Load network topology for physical road boundary validation
network_df = pd.read_csv(os.path.join(DATA_DIR, "network.csv"))
net_meta = network_df.set_index('segment_id').to_dict(orient='index')

clean_audit = {
    "traffic_train": {},
    "traffic_validation": {},
    "forecast_targets_train": {},
    "forecast_targets_validation": {},
    "context_train": {},
    "context_validation": {}
}

def clean_traffic_dataset(filename: str, audit_key: str):
    print(f"\n[1/4] Processing {filename}...")
    fpath = os.path.join(DATA_DIR, filename)
    df = pd.read_csv(fpath)
    initial_rows = len(df)
    
    # 1. Deduplication
    dups_exact = int(df.duplicated().sum())
    dups_key = int(df.duplicated(subset=['timestamp', 'segment_id']).sum())
    df = df.drop_duplicates(subset=['timestamp', 'segment_id'], keep='first')
    
    # 2. Chronological sorting (Fix row shuffle)
    df['ts_dt'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values(by=['segment_id', 'ts_dt']).reset_index(drop=True)
    
    # 3. Impossible negative readings & physics-based boundaries
    neg_speed = int((df['speed_kmh'] < 0).sum())
    neg_flow = int((df['flow_vph'] < 0).sum())
    neg_occ = int((df['occupancy_pct'] < 0).sum())
    neg_delay = int((df['delay_min'] < 0).sum())
    neg_cong = int((df['congestion_index'] < 0).sum())
    
    df['speed_kmh'] = df['speed_kmh'].clip(lower=0.0)
    df['flow_vph'] = df['flow_vph'].clip(lower=0.0)
    df['occupancy_pct'] = df['occupancy_pct'].clip(lower=0.0, upper=100.0)
    df['delay_min'] = df['delay_min'].clip(lower=0.0)
    df['congestion_index'] = df['congestion_index'].clip(lower=0.0, upper=1.0)
    
    # Clip to road capacity & max physical design speeds
    for seg_id, group in df.groupby('segment_id'):
        limit = net_meta.get(seg_id, {}).get('free_flow_speed_kmh', 60.0) * 1.3
        cap = net_meta.get(seg_id, {}).get('capacity_vph', 2700.0) * 1.5
        idx = group.index
        df.loc[idx, 'speed_kmh'] = df.loc[idx, 'speed_kmh'].clip(upper=limit)
        df.loc[idx, 'flow_vph'] = df.loc[idx, 'flow_vph'].clip(upper=cap)
        
    # 4. Spike & Outlier Filtering (Hampel rolling median filter per segment)
    spikes_smoothed = 0
    stuck_sensors_detected = 0
    
    cleaned_groups = []
    for seg_id, group in df.groupby('segment_id'):
        group = group.copy()
        
        # Stuck sensor check: if speed is identical for >12 consecutive 5-min intervals
        diff_speed = group['speed_kmh'].diff().abs()
        stuck_mask = (diff_speed == 0).rolling(window=12).sum() >= 12
        stuck_count = int(stuck_mask.sum())
        if stuck_count > 0:
            stuck_sensors_detected += 1
            
        # Spike filter: rolling median
        rolling_med = group['speed_kmh'].rolling(window=5, center=True, min_periods=1).median()
        rolling_std = group['speed_kmh'].rolling(window=5, center=True, min_periods=1).std().fillna(1.0)
        outlier_mask = (group['speed_kmh'] - rolling_med).abs() > (3.5 * rolling_std)
        spikes_smoothed += int(outlier_mask.sum())
        group.loc[outlier_mask, 'speed_kmh'] = rolling_med[outlier_mask]
        
        cleaned_groups.append(group)
        
    df_cleaned = pd.concat(cleaned_groups, ignore_index=True)
    df_cleaned = df_cleaned.sort_values(by=['ts_dt', 'segment_id']).reset_index(drop=True)
    df_cleaned = df_cleaned.drop(columns=['ts_dt'])
    
    # Save cleaned
    out_path = os.path.join(OUT_DIR, filename)
    df_cleaned.to_csv(out_path, index=False)
    
    clean_audit[audit_key] = {
        "initial_rows": initial_rows,
        "final_rows": len(df_cleaned),
        "exact_duplicates_removed": dups_exact,
        "key_duplicates_removed": dups_key,
        "negative_speed_corrected": neg_speed,
        "negative_flow_corrected": neg_flow,
        "negative_occupancy_corrected": neg_occ,
        "negative_delay_corrected": neg_delay,
        "negative_congestion_corrected": neg_cong,
        "spikes_smoothed": spikes_smoothed,
        "stuck_sensor_events": stuck_sensors_detected,
        "row_order_restored": True
    }
    print(f"-> Saved cleaned dataset to: {out_path} ({len(df_cleaned)} rows)")

def clean_forecast_dataset(filename: str, audit_key: str):
    print(f"\n[2/4] Processing {filename}...")
    fpath = os.path.join(DATA_DIR, filename)
    df = pd.read_csv(fpath)
    initial_rows = len(df)
    
    # 1. Deduplication
    dups = int(df.duplicated(subset=['timestamp', 'segment_id']).sum())
    df = df.drop_duplicates(subset=['timestamp', 'segment_id'], keep='first')
    
    # 2. Chronological sorting
    df['ts_dt'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values(by=['ts_dt', 'segment_id']).reset_index(drop=True)
    
    # 3. Clip negative values on all target columns
    neg_count = 0
    target_cols = [c for c in df.columns if c.startswith('target_')]
    for col in target_cols:
        neg_count += int((df[col] < 0).sum())
        if 'speed' in col or 'flow' in col:
            df[col] = df[col].clip(lower=0.0)
        elif 'congestion' in col:
            df[col] = df[col].clip(lower=0.0, upper=1.0)
            
    df = df.drop(columns=['ts_dt'])
    out_path = os.path.join(OUT_DIR, filename)
    df.to_csv(out_path, index=False)
    
    clean_audit[audit_key] = {
        "initial_rows": initial_rows,
        "final_rows": len(df),
        "duplicates_removed": dups,
        "negative_targets_corrected": neg_count,
        "row_order_restored": True
    }
    print(f"-> Saved cleaned targets to: {out_path} ({len(df)} rows)")

def clean_context_dataset(filename: str, audit_key: str):
    print(f"\n[3/4] Processing {filename}...")
    fpath = os.path.join(DATA_DIR, filename)
    df = pd.read_csv(fpath)
    initial_rows = len(df)
    
    # Fill missing event_id with 'NO_EVENT'
    null_events = int(df['event_id'].isnull().sum())
    df['event_id'] = df['event_id'].fillna('NONE')
    
    # Clip temperature and rain intensity
    df['temperature_c'] = df['temperature_c'].clip(lower=5.0, upper=50.0)
    df['rain_intensity'] = df['rain_intensity'].clip(lower=0.0)
    
    # Sort by timestamp
    df['ts_dt'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values(by='ts_dt').reset_index(drop=True)
    df = df.drop(columns=['ts_dt'])
    
    out_path = os.path.join(OUT_DIR, filename)
    df.to_csv(out_path, index=False)
    
    clean_audit[audit_key] = {
        "initial_rows": initial_rows,
        "final_rows": len(df),
        "null_event_ids_standardized": null_events,
        "row_order_restored": True
    }
    print(f"-> Saved cleaned context to: {out_path} ({len(df)} rows)")

# Copy static topology files
def copy_static_tables():
    print("\n[4/4] Copying and validating static network & scenario files...")
    static_files = [
        "network.csv", "nodes.csv", "signal_plans.csv", "turn_restrictions.csv",
        "planning_candidates.csv", "od_demand_profiles.csv", "scenario_examples.csv",
        "incidents_train.csv", "incidents_validation.csv",
        "roadworks_train.csv", "roadworks_validation.csv",
        "DATASET_MANIFEST.json", "README.md"
    ]
    for sf in static_files:
        src = os.path.join(DATA_DIR, sf)
        dst = os.path.join(OUT_DIR, sf)
        if os.path.exists(src):
            if sf.endswith('.csv'):
                df = pd.read_csv(src)
                df = df.drop_duplicates()
                df.to_csv(dst, index=False)
            else:
                with open(src, 'r') as f_in, open(dst, 'w') as f_out:
                    f_out.write(f_in.read())
            print(f"  - Validated: {sf}")

# Run pipeline
clean_traffic_dataset("traffic_train.csv", "traffic_train")
clean_traffic_dataset("traffic_validation.csv", "traffic_validation")
clean_forecast_dataset("forecast_targets_train.csv", "forecast_targets_train")
clean_forecast_dataset("forecast_targets_validation.csv", "forecast_targets_validation")
clean_context_dataset("context_train.csv", "context_train")
clean_context_dataset("context_validation.csv", "context_validation")
copy_static_tables()

# Save audit report
audit_report_path = os.path.join(OUT_DIR, "DATA_CLEANING_AUDIT_REPORT.json")
with open(audit_report_path, "w") as f:
    json.dump(clean_audit, f, indent=2)

print("\n" + "=" * 80)
print(f"DATA PREPROCESSING COMPLETE! Cleaned dataset saved to: {OUT_DIR}")
print(f"Audit report saved to: {audit_report_path}")
print("=" * 80)
