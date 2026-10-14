"""
Lightweight Evaluation Harness & Guardrail Benchmark Suite.

Tests and scores the Shipping Cost Assistant against known ground-truth cases
and deliberate distractor trap notes to guarantee zero-hallucination.
"""

from typing import List, Dict, Any
import pandas as pd
from freight_guard.core.pipeline import ShippingCostPipeline
from freight_guard.rag.guardrails import FreightGuardrailEngine, GuardrailResult


class EvaluationHarness:
    """
    Automated benchmark scoring guardrail fidelity, contract compliance,
    and anti-hallucination defense.
    """

    def __init__(self, pipeline: ShippingCostPipeline):
        self.pipeline = pipeline
        self.guardrails = pipeline.guardrails
        self.store = pipeline.store

    def run_guardrail_stress_tests(self) -> Dict[str, Any]:
        """
        Runs 10 adversarial probe tests against all known notes (valid + distractors).
        """
        test_probes = [
            {
                "probe_id": "PROBE_01_VALID_FLOOD",
                "route": "Chennai-Bangalore",
                "week_of": "2025-02-24",
                "pct_vs_hist": 31.5,
                "pct_vs_peer": 38.7,
                "query": "flooding detour highway cost surge",
                "expected_valid": True,
                "expected_note_id": "N001",
                "description": "N001: Heavy flooding detour on Chennai-Bangalore"
            },
            {
                "probe_id": "PROBE_02_VALID_FESTIVAL",
                "route": "Ahmedabad-Mumbai",
                "week_of": "2025-01-20",
                "pct_vs_hist": 29.5,
                "pct_vs_peer": 22.5,
                "query": "festival surcharge limited truck availability",
                "expected_valid": True,
                "expected_note_id": "N002",
                "description": "N002: Regional festival surcharge on Ahmedabad-Mumbai"
            },
            {
                "probe_id": "PROBE_03_VALID_DIESEL",
                "route": "Mumbai-Delhi",
                "week_of": "2025-05-12",
                "pct_vs_hist": 11.6,
                "pct_vs_peer": 6.7,
                "query": "diesel prices nationwide increase fuel",
                "expected_valid": True,
                "expected_note_id": "N003",
                "description": "N003: Nationwide diesel price hike (+5-7%)"
            },
            {
                "probe_id": "PROBE_04_TRAP_TOLL",
                "route": "Delhi-Jaipur",
                "week_of": "2024-03-11",
                "pct_vs_hist": 15.0,
                "pct_vs_peer": 10.0,
                "query": "new toll plaza commissioned highway",
                "expected_valid": False,
                "expected_note_id": None,
                "description": "N004 TRAP: Toll plaza on routes not part of dataset"
            },
            {
                "probe_id": "PROBE_05_TRAP_MAINTENANCE",
                "route": "Mumbai-Delhi",
                "week_of": "2024-07-29",
                "pct_vs_hist": 12.0,
                "pct_vs_peer": 8.0,
                "query": "highway maintenance work minor delays",
                "expected_valid": False,
                "expected_note_id": None,
                "description": "N005 TRAP: Costs explicitly not significantly affected"
            },
            {
                "probe_id": "PROBE_06_TRAP_STABLE_DEMAND",
                "route": "Mumbai-Pune",
                "week_of": "2025-09-15",
                "pct_vs_hist": 9.2,
                "pct_vs_peer": 23.6,
                "query": "logistics demand freight capacity stable",
                "expected_valid": False,
                "expected_note_id": None,
                "description": "N006 TRAP: Stable demand with no disruptions"
            },
            {
                "probe_id": "PROBE_07_TRAP_RESURFACING",
                "route": "Delhi-Jaipur",
                "week_of": "2024-05-20",
                "pct_vs_hist": 10.0,
                "pct_vs_peer": 5.0,
                "query": "improved road conditions resurfacing work",
                "expected_valid": False,
                "expected_note_id": None,
                "description": "N007 TRAP: Road resurfaced (infrastructure improvement)"
            },
            {
                "probe_id": "PROBE_08_TRAP_NORMAL_CORRIDOR",
                "route": "Kolkata-Bhubaneswar",
                "week_of": "2025-06-09",
                "pct_vs_hist": 10.0,
                "pct_vs_peer": 5.0,
                "query": "no disruptions reported normal movement",
                "expected_valid": False,
                "expected_note_id": None,
                "description": "N008 TRAP: Freight movement normal, no disruptions"
            },
            {
                "probe_id": "PROBE_09_TRAP_NORMALIZATION",
                "route": "Chennai-Bangalore",
                "week_of": "2025-03-17",
                "pct_vs_hist": 13.7,
                "pct_vs_peer": 33.5,
                "query": "returned to normal conditions repairs complete",
                "expected_valid": False,
                "expected_note_id": None,
                "description": "N009 TRAP: Returned to normal conditions post-flooding"
            },
            {
                "probe_id": "PROBE_10_TRAP_TRACKING_MANDATE",
                "route": "Delhi-Chennai",
                "week_of": "2025-10-27",
                "pct_vs_hist": 10.0,
                "pct_vs_peer": 5.0,
                "query": "vehicle tracking mandate compliance costs",
                "expected_valid": False,
                "expected_note_id": None,
                "description": "N010 TRAP: Costs absorbed by transporters without rate change"
            }
        ]

        passed = 0
        total = len(test_probes)
        probe_results = []

        for p in test_probes:
            candidates = self.store.retrieve_candidates(p["query"], p["route"], p["week_of"], top_k=5)
            g_res = self.guardrails.evaluate_candidate(
                route=p["route"],
                week_of=p["week_of"],
                pct_vs_hist=p["pct_vs_hist"],
                pct_vs_peer=p["pct_vs_peer"],
                candidate_notes=candidates
            )

            is_correct_valid = (g_res.is_valid == p["expected_valid"])
            is_correct_note = (g_res.note_id == p["expected_note_id"])
            test_ok = is_correct_valid and is_correct_note

            if test_ok:
                passed += 1

            probe_results.append({
                "probe_id": p["probe_id"],
                "description": p["description"],
                "expected_valid": p["expected_valid"],
                "actual_valid": g_res.is_valid,
                "expected_note_id": p["expected_note_id"],
                "actual_note_id": g_res.note_id,
                "passed": test_ok,
                "rejection_reason": g_res.rejection_reason or g_res.closest_distractor_reason
            })

        score_pct = (passed / total) * 100.0

        return {
            "total_probes": total,
            "passed_probes": passed,
            "score_pct": score_pct,
            "hallucination_rate_pct": 0.0 if score_pct == 100.0 else (100.0 - score_pct),
            "probe_details": probe_results
        }

    def verify_sample_format_contract(self, sample_csv_path: str) -> Dict[str, Any]:
        """
        Validates output against the provided sample_output_format_v2.csv.
        """
        # Read sample file safely handling line 4 where FreightTiger omitted quotes around reason
        sample_rows = []
        with open(sample_csv_path, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
        
        headers = lines[0].split(',')
        for line in lines[1:]:
            parts = line.split(',')
            # route, week_of, cost, vs_hist, vs_peer, flagged, matched_note_id, remainder...
            route = parts[0]
            week_of = parts[1]
            cost = parts[2]
            vs_hist = parts[3]
            vs_peer = parts[4]
            flagged = parts[5]
            matched_note = parts[6]
            reason = ','.join(parts[7:]).strip('"')
            sample_rows.append({
                "route": route,
                "week_of": week_of,
                "cost_per_tonne_km": cost,
                "vs_own_history": vs_hist,
                "vs_similar_routes": vs_peer,
                "flagged": flagged,
                "matched_note_id": matched_note,
                "reason": reason
            })
        sample_df = pd.DataFrame(sample_rows)
        output_df = self.pipeline.run(include_all_weeks=False)

        checks = []
        for _, s_row in sample_df.iterrows():
            r = s_row['route']
            w = s_row['week_of']

            match = output_df[(output_df['route'] == r) & (output_df['week_of'] == w)]
            if len(match) == 0:
                checks.append({"route": r, "week_of": w, "status": "MISSING_ROW"})
                continue

            m_row = match.iloc[0]
            cost_match = round(float(m_row['cost_per_tonne_km']), 2) == round(float(s_row['cost_per_tonne_km']), 2)
            hist_match = str(m_row['vs_own_history']).strip() == str(s_row['vs_own_history']).strip()
            peer_match = str(m_row['vs_similar_routes']).strip() == str(s_row['vs_similar_routes']).strip()
            flag_match = str(m_row['flagged']).strip() == str(s_row['flagged']).strip()
            
            # Handle empty vs nan matched_note_id
            s_note = "" if pd.isna(s_row['matched_note_id']) else str(s_row['matched_note_id']).strip()
            m_note = "" if pd.isna(m_row['matched_note_id']) else str(m_row['matched_note_id']).strip()
            note_match = (s_note == m_note)

            all_ok = cost_match and hist_match and peer_match and flag_match and note_match
            checks.append({
                "route": r,
                "week_of": w,
                "cost_match": cost_match,
                "hist_match": hist_match,
                "peer_match": peer_match,
                "flag_match": flag_match,
                "note_match": note_match,
                "status": "PASS" if all_ok else "FAIL"
            })

        all_sample_passed = all(c.get("status") == "PASS" for c in checks)
        return {
            "all_sample_passed": all_sample_passed,
            "sample_checks": checks
        }
