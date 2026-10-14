"""
End-to-End Pipeline for Shipping Cost Analysis and Contract CSV Generation.
"""

import os
from typing import Optional, List, Dict, Any, Tuple
import pandas as pd

from freight_guard.core.metrics import compute_weekly_metrics
from freight_guard.core.detector import AnomalyDetector
from freight_guard.rag.vector_store import ContextNoteStore
from freight_guard.rag.guardrails import FreightGuardrailEngine
from freight_guard.rag.explainer import ExplanationGenerator


class ShippingCostPipeline:
    """
    Orchestrates ingestion, baseline computation, anomaly detection, RAG retrieval,
    guardrail verification, and contract-compliant output generation.
    """

    def __init__(
        self,
        shipment_csv_path: str,
        context_notes_csv_path: str,
        hist_threshold_pct: float = 8.0,
        peer_threshold_pct: float = 20.0,
        persist_dir: Optional[str] = None
    ):
        self.shipment_csv_path = shipment_csv_path
        self.context_notes_csv_path = context_notes_csv_path
        self.detector = AnomalyDetector(
            hist_threshold_pct=hist_threshold_pct,
            peer_threshold_pct=peer_threshold_pct
        )
        self.store = ContextNoteStore(context_notes_csv_path, persist_dir=persist_dir)
        self.guardrails = FreightGuardrailEngine()
        self.explainer = ExplanationGenerator()

        # Cache notes dictionary for quick lookup
        notes_df = pd.read_csv(context_notes_csv_path)
        self.notes_dict = {str(row['note_id']).strip(): row.to_dict() for _, row in notes_df.iterrows()}

    def run(self, include_all_weeks: bool = False) -> pd.DataFrame:
        """
        Executes the full pipeline.
        
        Args:
            include_all_weeks: If False (default), returns candidate anomaly rows evaluated
                              against context notes (matching sample_output_format_v2.csv contract).
                              If True, returns all route-week rows.
        """
        metrics_df = compute_weekly_metrics(self.shipment_csv_path)

        output_rows = []

        # If include_all_weeks is False, filter to candidate anomalies
        target_df = metrics_df if include_all_weeks else self.detector.filter_candidate_anomalies(metrics_df)

        for _, row in target_df.iterrows():
            route = row['route']
            week_of = row['week_of']
            cost = round(float(row['cost_per_tonne_km']), 2)
            vs_hist_formatted = row['vs_own_history_formatted']
            vs_peer_formatted = row['vs_similar_routes_formatted']

            # Check if this row is an anomaly
            is_anomaly = self.detector.is_candidate_anomaly(row)

            if not is_anomaly:
                flagged = "No"
                matched_note_id = ""
                reason = "Operating within normal historical and peer corridor cost parameters."
            else:
                # Query RAG store for relevant notes across the context set
                query = f"{route} {week_of} shipping cost increase freight spike delay surcharge"
                candidates = self.store.retrieve_candidates(query, route, week_of, top_k=10)

                # Evaluate guardrails
                g_res = self.guardrails.evaluate_candidate(
                    route=route,
                    week_of=week_of,
                    pct_vs_hist=row['pct_vs_own_history'],
                    pct_vs_peer=row['pct_vs_similar_routes'],
                    candidate_notes=candidates
                )

                # Generate grounded explanation
                flagged, matched_note_id, reason = self.explainer.generate_explanation(
                    route=route,
                    week_of=week_of,
                    cost_per_tonne_km=cost,
                    pct_vs_hist=row['pct_vs_own_history'],
                    pct_vs_peer=row['pct_vs_similar_routes'],
                    guardrail_result=g_res,
                    context_notes_dict=self.notes_dict
                )

            output_rows.append({
                "route": route,
                "week_of": week_of,
                "cost_per_tonne_km": cost,
                "vs_own_history": vs_hist_formatted,
                "vs_similar_routes": vs_peer_formatted,
                "flagged": flagged,
                "matched_note_id": matched_note_id,
                "reason": reason
            })

        result_df = pd.DataFrame(output_rows)
        # Contract column order
        contract_cols = [
            "route",
            "week_of",
            "cost_per_tonne_km",
            "vs_own_history",
            "vs_similar_routes",
            "flagged",
            "matched_note_id",
            "reason"
        ]
        return result_df[contract_cols]

    def export_submission_csv(self, output_path: str, include_all_weeks: bool = False) -> pd.DataFrame:
        """Runs pipeline and exports exactly formatted CSV."""
        result_df = self.run(include_all_weeks=include_all_weeks)
        result_df.to_csv(output_path, index=False)
        return result_df
