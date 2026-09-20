from backend.test_evaluator_service import test_evaluator_service

test_input = {
    'scenario_id': 'JURY_UNSEEN_TEST_01',
    'segment_id': 'R0067',
    'timestamp': '2026-01-25 09:15:00',
    'rain_intensity': 6.5,
    'temperature_c': 21.0,
    'incident_type': 'lane_blockage',
    'severity': 3,
    'lanes_blocked': 2,
    'current_speed_kmh': 18.5,
    'current_flow_vph': 1950.0
}

res = test_evaluator_service.evaluate_test_case(test_input)
print("=== TEST CASE RESULT ===")
print("Model Engine:", res['model_engine'])
print("Current State:", res['current_state'])
print("Forecasts (4 Horizons):")
for f in res['forecasts']:
    print(f"  +{f['horizon']}: Speed={f['predicted_speed_kmh']} km/h, Flow={f['predicted_flow_vph']} vph, Congestion={f['predicted_congestion_index']}")
print("Upstream Shockwave Feeders:", len(res['propagation_shockwave']))
print("Detour route:", res['detour_recommendation'].get('route_summary'))
print("Top Candidate Intervention:", res['candidate_interventions'][0] if res['candidate_interventions'] else 'None')
