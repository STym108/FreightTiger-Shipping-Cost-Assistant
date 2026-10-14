"""
Metrics Calculation Module for FreightTiger Shipping Cost Assistant.

Implements contract-grade cost per tonne-km tracking, Monday-to-Sunday weekly grouping,
trailing 8-week unweighted rolling history baselines (strictly prior weeks, no lookahead),
and peer route-type baselines (excluding the route itself).
"""

from typing import Optional, Tuple
import pandas as pd
import numpy as np


def compute_weekly_metrics(shipment_csv_path: str) -> pd.DataFrame:
    """
    Loads shipment records and aggregates weekly metrics by route and route_type.
    
    Formula:
        Cost per tonne per km = total freight cost / (quantity carried in tonnes x distance travelled in km)
        
    Week definition:
        Monday to Sunday. week_of is the week's Monday date (YYYY-MM-DD).
    """
    df = pd.read_csv(shipment_csv_path)
    
    # Ensure datetime parsing
    df['shipment_date'] = pd.to_datetime(df['shipment_date'])
    
    # Map each shipment date to Monday of that week
    # weekday(): Monday is 0, Sunday is 6
    df['week_of'] = df['shipment_date'].apply(
        lambda d: (d - pd.Timedelta(days=d.weekday())).strftime('%Y-%m-%d')
    )
    
    # Canonical route name: Origin-Destination
    df['route'] = df['origin'] + '-' + df['destination']
    
    # Group by route, route_type, and week_of
    weekly = df.groupby(['route', 'route_type', 'week_of']).apply(
        lambda g: pd.Series({
            'total_freight_cost': g['freight_cost_inr'].sum(),
            'total_tonne_km': (g['quantity_tonnes'] * g['distance_km']).sum(),
            'cost_per_tonne_km': g['freight_cost_inr'].sum() / (g['quantity_tonnes'] * g['distance_km']).sum(),
            'shipment_count': len(g)
        })
    ).reset_index()
    
    # Sort chronologically by route and week
    weekly = weekly.sort_values(['route', 'week_of']).reset_index(drop=True)
    
    # -------------------------------------------------------------
    # 1. Baseline: vs. Own History
    # Trailing 8-week unweighted rolling average of cost per tonne-km,
    # strictly before current week. If fewer than 8 prior weeks exist,
    # use all prior weeks available. No look-ahead, no extrapolation.
    # -------------------------------------------------------------
    weekly['hist_8wk_avg'] = np.nan
    weekly['prior_weeks_count'] = 0
    
    for route, group in weekly.groupby('route'):
        indices = group.index
        for idx in indices:
            current_week = weekly.loc[idx, 'week_of']
            prior = group[group['week_of'] < current_week].tail(8)
            prior_count = len(prior)
            weekly.loc[idx, 'prior_weeks_count'] = prior_count
            if prior_count > 0:
                weekly.loc[idx, 'hist_8wk_avg'] = prior['cost_per_tonne_km'].mean()

    # -------------------------------------------------------------
    # 2. Baseline: vs. Similar Routes (Peer routes)
    # Average cost per tonne-km in that same week across all other routes
    # sharing the same route_type (Short / Medium / Long), excluding itself.
    # -------------------------------------------------------------
    weekly['peer_same_week_avg'] = np.nan
    weekly['peer_routes_count'] = 0
    
    for idx, row in weekly.iterrows():
        peers = weekly[
            (weekly['week_of'] == row['week_of']) &
            (weekly['route_type'] == row['route_type']) &
            (weekly['route'] != row['route'])
        ]
        weekly.loc[idx, 'peer_routes_count'] = len(peers)
        if len(peers) > 0:
            weekly.loc[idx, 'peer_same_week_avg'] = peers['cost_per_tonne_km'].mean()

    # Percentage differences
    weekly['pct_vs_own_history'] = (
        (weekly['cost_per_tonne_km'] - weekly['hist_8wk_avg']) / weekly['hist_8wk_avg'] * 100
    )
    weekly['pct_vs_similar_routes'] = (
        (weekly['cost_per_tonne_km'] - weekly['peer_same_week_avg']) / weekly['peer_same_week_avg'] * 100
    )
    
    # Format strings matching sample_output_format_v2.csv exactly
    weekly['vs_own_history_formatted'] = weekly['pct_vs_own_history'].apply(format_history_comparison)
    weekly['vs_similar_routes_formatted'] = weekly['pct_vs_similar_routes'].apply(format_peer_comparison)
    
    return weekly


def format_history_comparison(pct: Optional[float]) -> str:
    """Format: '+35.5% vs this route\'s past average'"""
    if pd.isna(pct):
        return "N/A (first week, no past history)"
    return f"{pct:+.1f}% vs this route's past average"


def format_peer_comparison(pct: Optional[float]) -> str:
    """Format: '+21.0% vs similar-length routes this week'"""
    if pd.isna(pct):
        return "N/A (no peer routes available)"
    return f"{pct:+.1f}% vs similar-length routes this week"
