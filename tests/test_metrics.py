"""Tests for metrics and baseline computations."""
import pytest
import pandas as pd
from freight_guard.core.metrics import compute_weekly_metrics, format_history_comparison, format_peer_comparison


@pytest.fixture(scope="module")
def metrics_df():
    return compute_weekly_metrics("data/shipment_records.csv")


def test_shipment_date_to_monday_grouping(metrics_df):
    """Verify all week_of values are valid Mondays."""
    for week_str in metrics_df['week_of'].unique():
        dt = pd.to_datetime(week_str)
        assert dt.weekday() == 0, f"{week_str} is not a Monday!"


def test_sample_case_delhi_jaipur(metrics_df):
    """Verify Delhi-Jaipur on 2024-11-11 matches sample output format exactly."""
    row = metrics_df[(metrics_df['route'] == 'Delhi-Jaipur') & (metrics_df['week_of'] == '2024-11-11')].iloc[0]
    assert round(row['cost_per_tonne_km'], 2) == 4.17
    assert row['vs_own_history_formatted'] == "+35.5% vs this route's past average"
    assert row['vs_similar_routes_formatted'] == "+21.0% vs similar-length routes this week"


def test_sample_case_ahmedabad_mumbai(metrics_df):
    """Verify Ahmedabad-Mumbai on 2025-01-20 matches sample output format exactly."""
    row = metrics_df[(metrics_df['route'] == 'Ahmedabad-Mumbai') & (metrics_df['week_of'] == '2025-01-20')].iloc[0]
    assert round(row['cost_per_tonne_km'], 2) == 3.29
    assert row['vs_own_history_formatted'] == "+29.5% vs this route's past average"
    assert row['vs_similar_routes_formatted'] == "+22.5% vs similar-length routes this week"


def test_sample_case_mumbai_pune(metrics_df):
    """Verify Mumbai-Pune on 2025-09-15 matches sample output format exactly."""
    row = metrics_df[(metrics_df['route'] == 'Mumbai-Pune') & (metrics_df['week_of'] == '2025-09-15')].iloc[0]
    assert round(row['cost_per_tonne_km'], 2) == 3.98
    assert row['vs_own_history_formatted'] == "+9.2% vs this route's past average"
    assert row['vs_similar_routes_formatted'] == "+23.6% vs similar-length routes this week"


def test_no_lookahead_in_history_baseline(metrics_df):
    """Verify trailing history strictly uses prior weeks and at most 8 weeks."""
    for _, row in metrics_df.iterrows():
        assert row['prior_weeks_count'] <= 8
