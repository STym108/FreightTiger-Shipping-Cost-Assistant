# FreightTiger Shipping Cost Assistant: Token & Execution Cost Audit Log

## Executive Summary
For one full execution run over the entire `shipment_records.csv` dataset:
- **Total Shipments Ingested**: 2,940 records
- **Weekly Tracking Intervals**: 728 route-weeks across 7 corridors
- **Anomaly Events Screened**: 22 candidate spikes
- **Total Input Tokens**: 6,340
- **Total Output Tokens**: 1,430
- **Total Token Volume**: 7,770
- **Model Call Volume**: 32 calls

## Cost Breakdown by Model / Provider
| Model / Inference Engine | Deployment Mode | Input Rate / 1M | Output Rate / 1M | Total Execution Cost (USD) |
| :--- | :--- | :---: | :---: | :---: |
| **Local ONNX all-MiniLM-L6-v2 (Default)** | Free / Local Open-Source | $0.00 | $0.00 | **$0.000000 (Free)** |
| **Google Gemini 1.5 Flash** | Free Tier / Ultra Low Cost | $0.075 | $0.30 | **$0.000905 (< $0.001)** |
| **OpenAI GPT-4o-mini** | Commercial Cloud API | $0.15 | $0.60 | **$0.001809 (< $0.002)** |

## Responsible AI & Cost-Optimization Architecture
1. **Mathematical Pre-Filtering**: Sending all 2,940 raw shipment rows to an LLM would consume >150,000 tokens and cost significantly more. We run all grouping, calendar windowing, and 8-week trailing rolling averages in pure vectorized NumPy/Pandas.
2. **Selective RAG Invocations**: Only the anomalous candidate weeks invoke vector retrieval and grounded synthesis.
3. **Local Embedding Zero-Cost Default**: ChromaDB embeds the 10 context notes locally using ONNX `all-MiniLM-L6-v2`, resulting in $0 API spend and zero external network latency.
