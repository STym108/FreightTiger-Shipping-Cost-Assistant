# FreightTiger Shipping Cost Assistant: 3-Run Reproducibility Report

## Executive Summary
- **Evaluation Status**: ✅ PASSED (100% Deterministic)
- **Runs Executed**: 3 untouched sequential runs on identical input `shipment_records.csv`
- **Total Rows Evaluated per Run**: 22 anomaly candidate records
- **Deterministic Checksum (SHA-256)**:
  - Run 1: `0739ae6376e0629c6cab9e45af669a4629429c4363b8b16c3755c9305a6417f1`
  - Run 2: `0739ae6376e0629c6cab9e45af669a4629429c4363b8b16c3755c9305a6417f1`
  - Run 3: `0739ae6376e0629c6cab9e45af669a4629429c4363b8b16c3755c9305a6417f1`

## Pairwise Comparison Matrix
| Comparison | Float Numbers Exact | Flags & Verdicts Exact | Cited Notes Exact | Explanation Prose Grounded | Diff Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Run 1 vs Run 2** | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% | **0 Differences** |
| **Run 2 vs Run 3** | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% | **0 Differences** |
| **Run 1 vs Run 3** | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% | **0 Differences** |

## Determinism Design Rationale
1. **Mathematical Baselines**: The 8-week trailing history and same-week peer calculations are computed using exact floating-point aggregations with explicit Monday-Sunday calendar bucketing, eliminating random ordering issues.
2. **Deterministic RAG Retrieval**: Embedding queries with ChromaDB use fixed vector distance rankings.
3. **Zero-Hallucination Guardrails**: Semantic impact and temporal-route boundaries are gated by deterministic policy functions, ensuring verdicts and note IDs never flip across executions.
