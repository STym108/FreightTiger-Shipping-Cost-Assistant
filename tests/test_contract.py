"""Tests for sample output schema and contract compliance."""
import pytest
from freight_guard.core.pipeline import ShippingCostPipeline
from freight_guard.eval.harness import EvaluationHarness


@pytest.fixture(scope="module")
def pipeline():
    return ShippingCostPipeline("data/shipment_records.csv", "data/context_notes.csv")


def test_schema_contract_compliance(pipeline):
    """Verify output columns match sample_output_format_v2.csv exactly in name and order."""
    expected_cols = [
        "route",
        "week_of",
        "cost_per_tonne_km",
        "vs_own_history",
        "vs_similar_routes",
        "flagged",
        "matched_note_id",
        "reason"
    ]
    df = pipeline.run(include_all_weeks=False)
    assert list(df.columns) == expected_cols


def test_sample_rows_pass(pipeline):
    """Verify all rows in sample_output_format_v2.csv match output perfectly."""
    harness = EvaluationHarness(pipeline)
    res = harness.verify_sample_format_contract("data/sample_output_format_v2.csv")
    assert res["all_sample_passed"]
