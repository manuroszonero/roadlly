import os
import time
import pickle
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, ExtraTreesRegressor
from sklearn.metrics import mean_absolute_error, r2_score

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_preprocessed")
if not os.path.exists(DATA_DIR):
    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "NEURAX_SMART_CITIES_TRAINING_V2")

MODEL_SAVE_PATH = os.path.join(DATA_DIR, "trained_forecasting_models.pkl")

def train_and_save_models():
    print("[ML Engine] Starting training data preparation...")
    t0 = time.time()
    
    # 1. Load data
    network_df = pd.read_csv(os.path.join(DATA_DIR, "network.csv"))
    nodes_df = pd.read_csv(os.path.join(DATA_DIR, "nodes.csv"))
    
    # Fast segment metadata map
    seg_meta = {}
    for _, r in network_df.iterrows():
        seg_meta[r['segment_id']] = {
            'lanes': int(r['lanes']),
            'free_flow_speed_kmh': float(r['free_flow_speed_kmh']),
            'capacity_vph': float(r['capacity_vph']),
            'length_km': float(r['length_km']),
            'structural_bottleneck': int(r['structural_bottleneck']),
            'importance': float(r['importance'])
        }
        
    print(f"[ML Engine] Loaded metadata for {len(seg_meta)} road segments.")
    
    # Load traffic and forecast target data
    # We can load traffic_train + forecast_targets_train
    traffic_tr = pd.read_csv(os.path.join(DATA_DIR, "traffic_train.csv"))
    targets_tr = pd.read_csv(os.path.join(DATA_DIR, "forecast_targets_train.csv"))
    context_tr = pd.read_csv(os.path.join(DATA_DIR, "context_train.csv")).set_index('timestamp')
    incidents_tr = pd.read_csv(os.path.join(DATA_DIR, "incidents_train.csv"))
    incidents_tr['start_dt'] = pd.to_datetime(incidents_tr['start_time'])
    incidents_tr['end_dt'] = pd.to_datetime(incidents_tr['end_time'])
    
    print(f"[ML Engine] Training rows: traffic={len(traffic_tr)}, targets={len(targets_tr)}")
    
    # Merge traffic with targets on ['timestamp', 'segment_id']
    df = pd.merge(traffic_tr, targets_tr, on=['timestamp', 'segment_id'])
    
    # Add context features
    df['dt'] = pd.to_datetime(df['timestamp'])
    df['hour'] = df['dt'].dt.hour
    df['day_of_week'] = df['dt'].dt.dayofweek
    df['minute'] = df['dt'].dt.minute
    df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
    
    # Context map
    ctx_dict = context_tr.to_dict(orient='index')
    df['rain_intensity'] = df['timestamp'].map(lambda ts: ctx_dict.get(ts, {}).get('rain_intensity', 0.0) if ts in ctx_dict else 0.0).fillna(0.0)
    df['temperature_c'] = df['timestamp'].map(lambda ts: ctx_dict.get(ts, {}).get('temperature_c', 25.0) if ts in ctx_dict else 25.0).fillna(25.0)
    df['event_level'] = df['timestamp'].map(lambda ts: ctx_dict.get(ts, {}).get('event_level', 0) if ts in ctx_dict else 0).fillna(0)
    
    # Segment metadata features
    df['lanes'] = df['segment_id'].map(lambda s: seg_meta.get(s, {}).get('lanes', 2))
    df['free_flow_speed_kmh'] = df['segment_id'].map(lambda s: seg_meta.get(s, {}).get('free_flow_speed_kmh', 50.0))
    df['capacity_vph'] = df['segment_id'].map(lambda s: seg_meta.get(s, {}).get('capacity_vph', 2000.0))
    df['length_km'] = df['segment_id'].map(lambda s: seg_meta.get(s, {}).get('length_km', 1.0))
    df['structural_bottleneck'] = df['segment_id'].map(lambda s: seg_meta.get(s, {}).get('structural_bottleneck', 0))
    df['importance'] = df['segment_id'].map(lambda s: seg_meta.get(s, {}).get('importance', 0.5))
    
    # Traffic physics features
    df['speed_ratio'] = df['speed_kmh'] / np.maximum(1.0, df['free_flow_speed_kmh'])
    df['vc_ratio'] = df['flow_vph'] / np.maximum(1.0, df['capacity_vph'])
    df['speed_drop'] = np.maximum(0.0, 1.0 - df['speed_ratio'])
    
    feature_cols = [
        'hour', 'day_of_week', 'minute', 'is_weekend',
        'speed_kmh', 'flow_vph', 'occupancy_pct', 'delay_min', 'queue_length_veh', 'congestion_index',
        'speed_ratio', 'vc_ratio', 'speed_drop',
        'lanes', 'free_flow_speed_kmh', 'capacity_vph', 'length_km', 'structural_bottleneck', 'importance',
        'rain_intensity', 'temperature_c', 'event_level'
    ]
    
    X_train = df[feature_cols].fillna(0)
    
    # Target columns for all 4 horizons
    horizons = ['15m', '30m', '45m', '60m']
    target_types = ['speed', 'flow', 'congestion']
    
    models = {}
    validation_scores = {}
    
    print(f"[ML Engine] Training fast Gradient Boosting models for 12 forecasting targets...")
    
    for t_type in target_types:
        for h in horizons:
            target_col = f'target_{t_type}_{h}'
            if target_col not in df.columns:
                continue
                
            y_train = df[target_col].fillna(0)
            
            # Use HistGradientBoostingRegressor (fastest, state-of-the-art tabular regressor in sklearn)
            model = HistGradientBoostingRegressor(
                max_iter=120,
                max_depth=10,
                learning_rate=0.08,
                random_state=42
            )
            model.fit(X_train, y_train)
            
            # Training metrics
            preds = model.predict(X_train)
            mae = mean_absolute_error(y_train, preds)
            r2 = r2_score(y_train, preds)
            
            models[target_col] = model
            validation_scores[target_col] = {
                'mae': round(float(mae), 4),
                'r2': round(float(r2), 4)
            }
            print(f"  -> Model {target_col:22s} | MAE: {mae:8.4f} | R2: {r2:6.4f}")
            
    # Save the trained models bundle
    save_bundle = {
        'models': models,
        'feature_cols': feature_cols,
        'seg_meta': seg_meta,
        'validation_scores': validation_scores,
        'trained_at': pd.Timestamp.now().isoformat()
    }
    
    with open(MODEL_SAVE_PATH, "wb") as f:
        pickle.dump(save_bundle, f)
        
    print(f"[ML Engine] Models trained and saved successfully to {MODEL_SAVE_PATH} in {time.time() - t0:.2f}s")

if __name__ == "__main__":
    train_and_save_models()
