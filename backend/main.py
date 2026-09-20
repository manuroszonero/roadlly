import os
import uvicorn
from fastapi import FastAPI, Query, Body, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Optional, Dict, Any

from backend.data_service import data_service
from backend.forecasting_service import forecasting_service
from backend.scenario_service import scenario_service
from backend.planning_service import planning_service

app = FastAPI(
    title="Roadlyy Traffic Intelligence API",
    description="Backend API for urban traffic forecasting, incident propagation modeling, and counterfactual planning.",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

# 1. Network Topology
@app.get("/api/network")
def get_network():
    return data_service.get_network_geojson()

# 2. Timestamps List
@app.get("/api/traffic/timestamps")
def get_timestamps(split: str = Query("val", description="Dataset split: 'val', 'train', or 'all'")):
    if split == "train":
        ts_list = data_service.train_timestamps
    elif split == "all":
        ts_list = data_service.all_timestamps
    else:
        ts_list = data_service.val_timestamps
        
    return {
        "split": split,
        "timestamps": ts_list,
        "count": len(ts_list),
        "start": ts_list[0] if ts_list else None,
        "end": ts_list[-1] if ts_list else None
    }

# 3. Dynamic Traffic Slice
@app.get("/api/traffic/slice")
def get_traffic_slice(timestamp: str = Query(..., description="Timestamp in YYYY-MM-DD HH:MM:SS format")):
    return data_service.get_traffic_slice(timestamp)

# 4. Segment Deep Dive
@app.get("/api/segments/{segment_id}")
def get_segment_history(segment_id: str):
    res = data_service.get_segment_history(segment_id)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res

# 5. Multi-Horizon Forecast
@app.get("/api/forecast/segment")
def get_segment_forecast(
    segment_id: str = Query(..., description="Segment ID (e.g. R0001)"),
    timestamp: str = Query(..., description="Timestamp in YYYY-MM-DD HH:MM:SS format")
):
    res = forecasting_service.get_segment_forecast(segment_id, timestamp)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res

@app.get("/api/forecast/benchmarks")
def get_forecast_benchmarks():
    return forecasting_service.metrics_summary

# 6. Incidents & Scenarios
@app.get("/api/incidents")
def get_incidents():
    return {
        "train_incidents": data_service.incidents_train.to_dict(orient="records"),
        "validation_incidents": data_service.incidents_val.to_dict(orient="records"),
        "roadworks": data_service.roadworks_all.to_dict(orient="records")
    }

@app.get("/api/scenarios/benchmarks")
def get_benchmark_scenarios():
    return scenario_service.get_benchmark_scenarios()

# 7. Counterfactual Simulation
@app.post("/api/scenarios/simulate")
def simulate_scenario(payload: Dict[str, Any] = Body(...)):
    target_segment = payload.get("target_segment", "R0067")
    incident_type = payload.get("incident_type", "stalled_vehicle")
    severity = int(payload.get("severity", 2))
    lanes_blocked = int(payload.get("lanes_blocked", 1))
    intervention_id = payload.get("intervention_id")
    custom_capacity_delta = float(payload.get("custom_capacity_delta", 0.0))
    custom_signal_green_delta = float(payload.get("custom_signal_green_delta", 0.0))
    
    return scenario_service.simulate_counterfactual(
        target_segment=target_segment,
        incident_type=incident_type,
        severity=severity,
        lanes_blocked=lanes_blocked,
        intervention_id=intervention_id,
        custom_capacity_delta=custom_capacity_delta,
        custom_signal_green_delta=custom_signal_green_delta
    )

from backend.test_evaluator_service import test_evaluator_service

# 9. Jury Test Case Live Evaluation Engine
@app.post("/api/testcase/evaluate")
def evaluate_test_case(payload: Dict[str, Any] = Body(...)):
    """Live inference for any arbitrary / unseen test case using trained ML model & Graph AI."""
    return test_evaluator_service.evaluate_test_case(payload)

@app.get("/api/testcase/scenarios")
def get_testcase_scenarios():
    """Returns official benchmark scenario examples."""
    return data_service.scenarios_df.to_dict(orient="records")

@app.post("/api/testcase/batch")
def evaluate_batch_testcases(payload: Dict[str, Any] = Body(...)):
    test_cases = payload.get("test_cases", [])
    results = [test_evaluator_service.evaluate_test_case(tc) for tc in test_cases]
    return {
        "count": len(results),
        "results": results
    }

# Static Files & SPA Route
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/")
def serve_index():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Roadlyy API is running. Frontend build in progress."}

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
