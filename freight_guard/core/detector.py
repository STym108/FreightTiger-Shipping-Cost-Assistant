"""
Anomaly Detection Module for FreightTiger Shipping Cost Assistant.

Identifies route-week periods where cost per tonne-km is rising out of the ordinary
relative to its trailing 8-week history or peer routes of the same length type.
"""

from typing import Dict, Any, List
import pandas as pd


class AnomalyDetector:
    """
    Detects shipping cost anomalies based on deviations from own historical baseline
    and peer route baselines.
    """

    def __init__(
        self,
        hist_threshold_pct: float = 8.0,
        peer_threshold_pct: float = 20.0,
    ):
        """
        Args:
            hist_threshold_pct: Minimum percentage rise vs own history to trigger candidate flag.
                                (Default: 8.0% captures Mumbai-Pune at +9.2%, Ahmedabad-Mumbai at +29.5%,
                                 Delhi-Jaipur at +35.5%)
            peer_threshold_pct: Minimum percentage rise vs peer routes to trigger candidate flag.
                                (Default: 20.0% captures peer corridor divergences)
        """
        self.hist_threshold_pct = hist_threshold_pct
        self.peer_threshold_pct = peer_threshold_pct

    def is_candidate_anomaly(self, row: pd.Series) -> bool:
        """
        Determines whether a route-week row warrants investigation as a cost rise anomaly.
        """
        pct_hist = row.get('pct_vs_own_history')
        pct_peer = row.get('pct_vs_similar_routes')

        hist_breach = pd.notna(pct_hist) and pct_hist >= self.hist_threshold_pct
        peer_breach = pd.notna(pct_peer) and pct_peer >= self.peer_threshold_pct

        return bool(hist_breach or peer_breach)

    def classify_anomaly_trigger(self, row: pd.Series) -> str:
        """
        Returns a descriptive trigger reason for logging and UI explainability.
        """
        pct_hist = row.get('pct_vs_own_history')
        pct_peer = row.get('pct_vs_similar_routes')

        hist_breach = pd.notna(pct_hist) and pct_hist >= self.hist_threshold_pct
        peer_breach = pd.notna(pct_peer) and pct_peer >= self.peer_threshold_pct

        if hist_breach and peer_breach:
            return f"Dual breach: +{pct_hist:.1f}% vs history, +{pct_peer:.1f}% vs peers"
        elif hist_breach:
            return f"History breach: +{pct_hist:.1f}% vs history"
        elif peer_breach:
            return f"Peer breach: +{pct_peer:.1f}% vs peers"
        return "Normal operating range"

    def filter_candidate_anomalies(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filters a weekly dataframe down to candidate anomalous rows.
        """
        df_copy = df.copy()
        mask = df_copy.apply(self.is_candidate_anomaly, axis=1)
        candidates = df_copy[mask].copy()
        candidates['anomaly_trigger'] = candidates.apply(self.classify_anomaly_trigger, axis=1)
        return candidates
