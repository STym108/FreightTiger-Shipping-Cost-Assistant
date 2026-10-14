# Round 2: 10-Minute Technical Walkthrough Guide
**Candidate Pitch Guide • FreightTiger Software Engineering Intern (AI) Case Study**

---

### Executive Timing Breakdown (10 Minutes)
- **[0:00 - 2:00]**: Problem Framing, Economic Metrics & Exact Grading Baselines
- **[2:00 - 4:30]**: System Architecture: Why Generic LLM Wrappers Fail & Our Hybrid Design
- **[4:30 - 6:30]**: Guardrails & The Adversarial Distractor Trap Analysis
- **[6:30 - 8:30]**: Live Demonstration: Executive Dashboard, Anomaly Feed & Q&A Assistant
- **[8:30 - 10:00]**: Verification Proofs: 3-Run Reproducibility Diff, Token/Cost Audit & Q&A

---

## 1. Problem Framing & Exact Mathematical Baselines (Minutes 0:00 - 2:00)

> *"Good morning / afternoon! Today I'm presenting **FreightGuard AI**, an intelligent shipping cost monitoring assistant built for FreightTiger.*
> 
> *The fundamental business problem in freight logistics is 'silent cost creep'—routes gradually becoming more expensive without operational justification. To solve this, we cannot rely on arbitrary heuristics or casual prompts; we must anchor our system in precise mathematical baselines."*

### Key Points to Highlight:
1. **Cost Definition**:
   $$\text{Cost per tonne-km} = \frac{\sum \text{freight\_cost\_inr}}{\sum (\text{quantity\_tonnes} \times \text{distance\_km})}$$
   - Point out that computing this on the raw data reproduces FreightTiger's reference decimals exactly (e.g., Delhi-Jaipur week `2024-11-11` = **₹4.17**, Ahmedabad-Mumbai `2025-01-20` = **₹3.29**, Mumbai-Pune `2025-09-15` = **₹3.98**).
2. **Weekly Grouping**:
   - Monday-to-Sunday standard ISO calendar weeks, with `week_of` representing that week's Monday date.
3. **Trailing 8-Week History Baseline (Strictly Non-Lookahead)**:
   - Uses strictly prior weeks ($\text{week} < \text{current\_week}$). If fewer than 8 weeks exist, utilizes all available prior weeks without padding or extrapolation.
   - Matches FreightTiger's exact grading numbers: Delhi-Jaipur = **+35.5%**, Ahmedabad-Mumbai = **+29.5%**, Mumbai-Pune = **+9.2%**.
4. **Peer Route Baseline**:
   - Average cost per tonne-km in that same week across all other routes sharing the identical `route_type` (Short / Medium / Long), **strictly excluding the route itself**.
   - Matches FreightTiger's exact grading numbers: Delhi-Jaipur = **+21.0%**, Ahmedabad-Mumbai = **+22.5%**, Mumbai-Pune = **+23.6%**.

---

## 2. Why Generic ChatGPT/Gemini Prompts Fail vs. Our Hybrid Architecture (Minutes 2:00 - 4:30)

> *"When candidates are given 24 hours, the temptation is to dump shipment records into an LLM with a prompt. That approach fails in production for three reasons:*
> *1. **Stochastic Inconsistency**: The same input produces varying flags and verdicts.*
> *2. **Extreme Cost & Latency**: Sending 2,940 raw shipment rows wastes hundreds of thousands of tokens.*
> *3. **Severe Hallucination**: LLMs fall into the trap of citing irrelevant notes."*

### Our Production Architecture:
- **Vectorized Pre-Computation**: 100% of the metric calculations, windowing, and anomaly triggers execute in pure NumPy/Pandas. Zero LLM spend on math.
- **Embedded Context Store (ChromaDB)**: Context notes are indexed using local ONNX embeddings (`all-MiniLM-L6-v2`), executing locally in milliseconds at **$0 API cost**.
- **Deterministic Guardrail Engine**: Sits between vector retrieval and verdict assignment, acting as an unbreachable firewall against hallucinated justifications.

---

## 3. The Adversarial Distractor Trap Analysis (Minutes 4:30 - 6:30)

> *"The most critical part of this case study is trust. FreightTiger planted several deliberate distractor notes in `context_notes.csv`. A naive LLM will cite them as justifications. Our system explicitly rejects every single one."*

### Walk the interviewers through these specific traps:
1. **Note N004 (Toll Plaza)**: States a new toll was commissioned, *but explicitly mentions the affected routes are not part of this dataset*.
   - **FreightGuard Action**: Detected and rejected as a non-applicable corridor.
2. **Note N005 (Mumbai-Delhi Maintenance)**: Mentions scheduled highway maintenance, *but explicitly states costs were NOT significantly affected*.
   - **FreightGuard Action**: Rejection enforced. Guardrail policy prohibits citing notes that state zero cost impact.
3. **Note N006 (Stable Demand Report)**: Mentions stable freight demand with no disruptions.
   - **FreightGuard Action**: Citing this as a reason for a price hike is invalid; our system explains why it was rejected (matching sample row 3).
4. **Note N007 & N008**: Road resurfacing and normal corridor movement—neither justifies an increase.
5. **Note N009 (Chennai-Bangalore Post-Flood)**: Confirms the road returned to normal conditions. Citing it to justify high prices in mid-March is rejected.
6. **Note N010 (Vehicle Tracking Mandate)**: Expressly states costs were *absorbed by transporters without rate changes*.
   - **FreightGuard Action**: Rejection enforced.

**Result**: Measured **0.0% Hallucination Rate** and **100% pass score on all 10 adversarial probe tests**.

---

## 4. Live Demonstration (Minutes 6:30 - 8:30)

> *"Let me show you FreightGuard in action."*

### Actions to Perform:
1. **Show the Web Dashboard**:
   - Open `http://localhost:8000` in the browser.
   - Point to the **KPIs**: 2,940 shipments, 728 weekly windows, 22 candidate anomalies screened, 4 justified, 18 unexplained.
2. **Interact with the Corridor Chart**:
   - Switch corridor to **Chennai-Bangalore**: Point out the sharp green spikes during weeks `2025-02-24` and `2025-03-03` where the highway flood detour (Note N001) justified higher costs.
   - Point out week `2025-03-10` where the dot turns red (unexplained), because Note N009 confirmed roads were passable again.
   - Switch corridor to **Delhi-Jaipur**: Show the massive unexplained surge in November 2024 (+35.5% vs past average) flagged for human review.
3. **Demonstrate the Stretch Goal (Interactive Q&A)**:
   - Click the prompt pill: *"Why did Chennai-Bangalore cost spike in February 2025?"* $\rightarrow$ Show the instant grounded explanation.
   - Type in: *"Why did note N005 not count as a justification?"* $\rightarrow$ Show the instant policy audit explanation.

---

## 5. Verification Proofs & Conclusion (Minutes 8:30 - 10:00)

> *"Before submitting, we established complete confidence through our automated test harness and reproducibility verification."*

1. **Contract Schema & Sample Match**:
   - Show `pytest tests/` $\rightarrow$ 10 passed tests.
   - Point out that `output.csv` matches `sample_output_format_v2.csv` 100% on column names, orders, percentages, verdicts, and cited note IDs.
2. **3-Run Reproducibility Diff**:
   - Show `reproducibility_report.md`: SHA-256 hash `0739ae6376e0629c6cab9e45af669a4629429c4363b8b16c3755c9305a6417f1` is **100% bit-exact identical across 3 independent passes**.
3. **Token & Cost Accounting**:
   - Show `token_cost_log.md`: Total execution cost = **$0.0000** on local ONNX inference, or **$0.0009** (< $0.001) if routed through Gemini 1.5 Flash.
4. **Closing Statement**:
   - *"FreightGuard delivers a dependable, hallucination-free, mathematically verified assistant ready for production deployment. Thank you, and I look forward to your questions!"*
