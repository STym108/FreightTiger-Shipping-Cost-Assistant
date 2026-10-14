"""Tests for anti-hallucination guardrails and distractor rejection."""
import pytest
from freight_guard.core.pipeline import ShippingCostPipeline
from freight_guard.eval.harness import EvaluationHarness


@pytest.fixture(scope="module")
def harness():
    pipeline = ShippingCostPipeline("data/shipment_records.csv", "data/context_notes.csv")
    return EvaluationHarness(pipeline)


def test_guardrail_benchmark_probes(harness):
    """Assert 100% pass rate on adversarial probes including all distractor notes."""
    results = harness.run_guardrail_stress_tests()
    assert results["score_pct"] == 100.0, f"Probes failed: {results['passed_probes']}/{results['total_probes']}"
    assert results["hallucination_rate_pct"] == 0.0


def test_distractor_n005_rejection(harness):
    """Specifically verify N005 (maintenance with no cost impact) is rejected."""
    candidates = harness.store.retrieve_candidates("maintenance minor delays", "Mumbai-Delhi", "2024-07-29")
    g_res = harness.guardrails.evaluate_candidate(
        route="Mumbai-Delhi",
        week_of="2024-07-29",
        pct_vs_hist=10.0,
        pct_vs_peer=5.0,
        candidate_notes=candidates
    )
    assert not g_res.is_valid
    assert g_res.note_id is None


def test_distractor_n004_rejection(harness):
    """Specifically verify N004 (toll plaza not in dataset) is rejected."""
    candidates = harness.store.retrieve_candidates("new toll plaza", "Delhi-Jaipur", "2024-03-11")
    g_res = harness.guardrails.evaluate_candidate(
        route="Delhi-Jaipur",
        week_of="2024-03-11",
        pct_vs_hist=10.0,
        pct_vs_peer=5.0,
        candidate_notes=candidates
    )
    assert not g_res.is_valid
    assert g_res.note_id is None
