# 🚦 Roadlyy — Urban Traffic Intelligence & Multi-Horizon Spatial-Temporal ML Engine

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Scikit-Learn](https://img.shields.io/badge/scikit--learn-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)](https://scikit-learn.org)
[![NetworkX](https://img.shields.io/badge/NetworkX-Graph%20Theory-blue?style=for-the-badge)](https://networkx.org)
[![Leaflet](https://img.shields.io/badge/Leaflet-199900?style=for-the-badge&logo=Leaflet&logoColor=white)](https://leafletjs.com)

**Roadlyy** is an end-to-end urban traffic intelligence platform combining machine learning forecasting, graph-based shockwave propagation, dynamic detour optimization, and capital planning simulation. Designed for high-density metropolitan networks, Roadlyy provides real-time situational awareness and forward predictive intelligence across hundreds of road corridors.

---

## 🌟 Key Features

### 1. 🔮 Multi-Horizon Traffic Forecasting (+15m, +30m, +45m, +60m)
* Trained ensemble models (**HistGradientBoostingRegressor**) trained across **1.88M+ time-series observations**.
* Simultaneously predicts **Speed (km/h)**, **Flow (vph)**, and **Congestion Index** with 90%+ baseline $R^2$ accuracy.
* Computes dynamic uncertainty confidence intervals (`speed_lower`, `speed_upper`) per horizon.

### 2. ⚡ Graph-Aware Shockwave & Upstream Propagation
* Directed graph representation of the road network using **NetworkX** (436 road segments, 120 intersection nodes).
* Models spatio-temporal spillover bottlenecks and queue accumulation on upstream feeder links when disruptions occur.

### 3. 🔄 Dynamic Detour & Rerouting Engine
* Automatically computes optimal detour corridors bypassing congested/blocked segments using network shortest-path graphs.
* Calculates added detour travel time penalties and length differentials.

### 4. 🧪 Live Jury Test Case Evaluator & What-If Sandbox
* Real-time interactive scenario builder to inject arbitrary lane blockages, crashes, road closures, rainstorms, and temperature shocks.
* Instant auto-normalization for arbitrary link inputs (e.g. `4`, `r4`, `R004`, `R0004`).
* Infinite custom date/time range playback with dynamic real-time traffic physics synthesis.

### 5. 🏗️ 90-Candidate Capital Planning & ROI Matrix
* Quantitative decision-support matrix evaluating infrastructure interventions (Lane Additions, Capacity Upgrades, Turn Lanes, Signal Retiming, Connectors).
* Ranked by **Weekly Delay Hours Saved per Unit Cost Index**.

### 6. 🖤 High-Performance Monochrome Geospatial Interface
* Responsive dark monochrome theme with high-contrast glowing link overlays and animated pulse beacon markers.
* Hardware-accelerated Leaflet map with ArcGIS Dark Canvas basemaps.

---

## 🏗️ Architecture & Project Structure

```
roadlyy/
├── backend/
│   ├── main.py                       # FastAPI application & REST routing
│   ├── data_service.py               # In-memory graph network & dynamic slice engine
│   ├── forecasting_service.py        # Multi-horizon forecasting service
│   ├── test_evaluator_service.py     # Live AI inference, shockwave & detour engine
│   ├── scenario_service.py           # Counterfactual scenario simulation
│   ├── planning_service.py           # 90-candidate capital planning matrix
│   ├── train_ml_engine.py            # Model training & serialization script
│   └── build_fast_cache.py           # Fast binary caching utility
├── frontend/
│   ├── index.html                    # Single-page dashboard application
│   ├── css/
│   │   └── style.css                 # Monochrome design system & animations
│   └── js/
│       ├── app.js                    # Core state controller & timeline loop
│       ├── map.js                    # Leaflet geospatial network visualization
│       ├── test_evaluator.js         # Evaluator modal controller & embedded map
│       ├── forecast_chart.js         # Multi-horizon forecast visualizer
│       ├── scenario_sandbox.js       # What-if scenario sandbox
│       └── planning_matrix.js        # Infrastructure ROI matrix
├── data_preprocessed/                # Network topology, nodes & validation data
├── requirements.txt                  # Python dependencies
├── run.py                            # 1-click startup launcher
└── README.md                         # Documentation
```

---

## 🚀 Quickstart & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/manuroszonero/roadlly.git
cd roadlly
```

### 2. Set Up Virtual Environment (Recommended)
```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application
```bash
python run.py
```
*Or via Uvicorn directly:*
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Access the Web Dashboard
Open your browser and navigate to:
👉 **[http://localhost:8000](http://localhost:8000)**

---

## 📡 REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/network` | Returns the road network GeoJSON topology with coordinates and road hierarchy. |
| `GET` | `/api/traffic/timestamps` | Returns available validation and historical timestamps. |
| `GET` | `/api/traffic/slice` | Retrieves citywide traffic telemetry slice for any timestamp (or synthesized on-the-fly). |
| `GET` | `/api/forecast/segment` | Multi-horizon forecasts (+15m, +30m, +45m, +60m) for a specific segment. |
| `POST` | `/api/testcase/evaluate` | Evaluates arbitrary unseen test cases with live ML predictions, shockwaves, and detours. |
| `GET` | `/api/testcase/scenarios` | Preloaded preset benchmark test scenarios. |
| `POST` | `/api/scenarios/simulate` | Simulates counterfactual interventions against active disruptions. |
| `GET` | `/api/planning/candidates` | Returns ranked capital planning candidates with ROI and feasibility scoring. |

---

## 🔬 Technology Stack

* **Core Language**: Python 3.10+
* **Backend Framework**: FastAPI, Starlette, Uvicorn
* **Data Processing & Modeling**: Pandas, NumPy, Scikit-Learn (`HistGradientBoostingRegressor`)
* **Graph & Network Theory**: NetworkX (Directed Graphs, Shortest Path Routing)
* **Frontend Technologies**: Vanilla JavaScript (ES6+), HTML5, CSS3 Custom Properties
* **Mapping Engine**: Leaflet.js with Esri World Dark Gray Canvas

---

## 📄 License
This project is open-source under the MIT License.
