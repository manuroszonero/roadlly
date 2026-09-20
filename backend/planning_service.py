import numpy as np
import pandas as pd
from typing import Dict, List, Any
from backend.data_service import data_service

class PlanningService:
    def __init__(self):
        print("[PlanningService] Initializing 90-Candidate Planning & ROI Matrix...")
        self.ranked_candidates = self._evaluate_all_candidates()
        
    def _evaluate_all_candidates(self) -> List[Dict[str, Any]]:
        """Ranks all 90 planning candidates by efficiency: (Capacity Delta * Segment Importance) / Cost Index."""
        results = []
        for cand in data_service.planning_candidates:
            c_id = cand['candidate_id']
            seg_id = cand['target_segment']
            seg_meta = data_service.segments_dict.get(seg_id, {})
            
            cap_delta = float(cand['capacity_delta_vph'])
            cost = max(1, int(cand['cost_index']))
            feasibility = cand['feasibility_band']
            i_type = cand['intervention_type']
            importance = seg_meta.get('importance', 0.5)
            is_bottleneck = seg_meta.get('structural_bottleneck', False)
            
            # Bottleneck multiplier
            bottleneck_bonus = 1.4 if is_bottleneck else 1.0
            
            # Estimated network vehicle-hours delay reduced per week
            est_weekly_delay_savings = round((cap_delta * 0.12 * importance * bottleneck_bonus * 7.0), 1)
            
            # ROI score
            roi_score = round((est_weekly_delay_savings / cost) * (1.2 if feasibility == 'high' else 1.0 if feasibility == 'medium' else 0.8), 2)
            
            results.append({
                'candidate_id': c_id,
                'target_segment': seg_id,
                'road_class': seg_meta.get('road_class', 'unknown'),
                'is_structural_bottleneck': is_bottleneck,
                'importance': round(importance, 3),
                'intervention_type': i_type,
                'capacity_delta_vph': int(cap_delta),
                'cost_index': cost,
                'feasibility_band': feasibility,
                'estimated_weekly_delay_savings_hrs': est_weekly_delay_savings,
                'roi_score': roi_score
            })
            
        results.sort(key=lambda x: x['roi_score'], reverse=True)
        for idx, item in enumerate(results):
            item['rank'] = idx + 1
        return results

    def get_ranked_candidates(
        self,
        intervention_type: str = None,
        feasibility_band: str = None,
        only_bottlenecks: bool = False
    ) -> List[Dict[str, Any]]:
        """Filters ranked planning candidates based on user criteria."""
        filtered = self.ranked_candidates
        if intervention_type and intervention_type != 'all':
            filtered = [c for c in filtered if c['intervention_type'] == intervention_type]
        if feasibility_band and feasibility_band != 'all':
            filtered = [c for c in filtered if c['feasibility_band'] == feasibility_band]
        if only_bottlenecks:
            filtered = [c for c in filtered if c['is_structural_bottleneck']]
        return filtered

    def get_portfolio_optimization(self, budget_limit: int = 50) -> Dict[str, Any]:
        """Knapsack-style greedy portfolio optimization under a given cost budget."""
        selected = []
        spent = 0
        total_delay_saved = 0.0
        
        for cand in self.ranked_candidates:
            if spent + cand['cost_index'] <= budget_limit:
                selected.append(cand)
                spent += cand['cost_index']
                total_delay_saved += cand['estimated_weekly_delay_savings_hrs']
                
        return {
            'budget_limit': budget_limit,
            'budget_spent': spent,
            'selected_count': len(selected),
            'total_weekly_delay_savings_hrs': round(total_delay_saved, 1),
            'selected_interventions': selected
        }

planning_service = PlanningService()
