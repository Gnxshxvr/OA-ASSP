# P0-1 — Common-Query-Set Fixed-Policy Solver Comparison

**Status: PASS — SBS identity unchanged (Bidirectional Dijkstra on every fair query set).**

## Why this artifact exists

The frozen manifest's fixed-policy training totals are computed under the pipeline's
oracle-eligibility rule, under which A* rows are eligible only where the euclidean heuristic is
admissible (the geometric subset). The printed totals therefore sum A* over 5,000 rows and
Dijkstra / Bidirectional Dijkstra over 16,000 rows. That is a **diagnostic** quantity, not an
apples-to-apples policy comparison. This artifact provides the fair comparison without altering
any frozen eligibility semantics.

## Definitions (two distinct purposes, never merged)

| Name | Purpose | Query set | Rows per solver |
|---|---|---:|---:|
| **A. Common-query fixed-policy comparison** (this artifact) | fair comparison of solver policies | all valid training (graph, query) pairs where all three solvers returned valid, correct, non-timeout results | 16,000 each |
| **B. Oracle/VBS eligibility** (frozen, unchanged) | VBS construction, selector labels, oracle gap | A* eligible only where `heuristic_admissible=True` (geometric subset); Dijkstra/Bidi eligible everywhere valid | A* 5,000; others 16,000 |

VBS eligibility is **not** modified. The common-query set is a *comparison artifact* only; no
downstream analysis, label, or table changes because of it.

## Results

All values from frozen raw benchmark medians (`stage20_corrected_20260923_092749`),
training graphs only (32 graphs / 16,000 queries). Machine-readable:
`FINAL_CORRECTED_AUDIT/common_query_sbs.csv`.

### A. Common query set — all 16,000 valid training queries (each solver on the same 16,000 queries)

| Solver | Common Query Set | Total Cost (s) | Mean per query (µs) | Median per query (µs) | Eligible Queries |
|---|---:|---:|---:|---:|---:|
| Dijkstra | all training, valid | 6.7038 | 418.99 | — | 16,000 |
| **Bidirectional Dijkstra** | all training, valid | **3.6708** | 229.43 | — | 16,000 |
| A* | all training, valid | 7.6452 | 477.83 | — | 16,000 |

**Argmin: Bidirectional Dijkstra (3.6708 s).**

### B. Geometric-eligible subset — 5,000 queries where A* is admissible under the experiment's policy

| Solver | Common Query Set | Total Cost (s) | Mean per query (µs) | Eligible Queries |
|---|---:|---:|---:|---:|
| Dijkstra | geometric training | 1.9206 | 384.11 | 5,000 |
| **Bidirectional Dijkstra** | geometric training | **1.6092** | 321.84 | 5,000 |
| A* | geometric training | 2.5516 | 510.32 | 5,000 |

**Argmin: Bidirectional Dijkstra (1.6092 s) — even where A* is admissible.**

### C. Diagnostic — eligibility-aware totals exactly as frozen in the manifest (NOT comparable across rows)

| Solver | Rows summed | Total Cost (s) | Note |
|---|---:|---:|---|
| Dijkstra | 16,000 | 6.7038 | comparable to Bidi |
| Bidirectional Dijkstra | 16,000 | 3.6708 | comparable to Dijkstra |
| A* | 5,000 | 2.5516 | **NOT comparable** to the rows above (different query set); argmin over these printed totals would misleadingly pick A* |

## Verification

- Common-query SBS identity: **Bidirectional Dijkstra** (3.6708 s vs 6.7038 / 7.6452 s).
- Geometric-subset SBS identity: **Bidirectional Dijkstra** (1.6092 s vs 1.9206 / 2.5516 s).
- On identical query sets, Bidi is argmin in every partition tried (all rows, geometric rows).
- **Consequence for downstream analysis: none.** The frozen SBS policy
  (Always-Bidirectional-Dijkstra), and therefore SBS/VBS/oracle gap, capture rates,
  RequiredCapture, crossover search, and bootstrap, are unchanged. No number in the frozen
  record changes.
