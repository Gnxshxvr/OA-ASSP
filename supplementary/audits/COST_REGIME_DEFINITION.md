# P0-2 — Cost Regime Definitions and Reconciliation

**Rule: no two regimes may share a table, axis, or "runtime" label without an explicit regime
tag.** Every result surface must carry one of:

- **`e2e_measured` — End-to-End Measured Cost.** The actual adaptive execution path, timed as
  one wall-clock loop per pass: graph-level features (once) + per-query (query features +
  vector assembly + selector inference + bookkeeping + the selected solver's **single-shot**
  in-loop runtime). This is what physically happens when the pipeline runs. Solver components
  inherit single-shot timing variability; the paired adaptive−SBS comparison in this regime is
  the only true like-for-like physical comparison.

- **`analysis_grade` — Analysis-Grade Normalized Cost.** A constructed cost: measured adaptive
  feature/selection overhead (same in-loop measurements, bookkeeping excluded from the task
  variant) **plus** the selected solver's **warm-up+5-repetition benchmark-median** cost, and
  correspondingly benchmark-median C_SBS/C_VBS. **It is not a physical execution time.** It
  exists because single-shot solver timings are noise-dominated (see
  `p0_noise_floor.csv`: per-row median IQR 14.4%, max 434%), so pairing noisy single-shot
  solver times against each other cannot resolve the oracle gap at all — the paired single-shot
  gap disagrees with the repeated-median gap by up to 2795%. Analysis-grade **isolates the
  selection/feature overhead from single-shot solver timing variability and provides a stable
  workload-cost comparison.** Any claim built on it is a claim about normalized costs, not
  wall-clock execution.

## Reconciliation table (tier 1 primary, 8 test graphs, frozen raw data)

Machine-readable: `p0_regime_reconciliation.csv`. Both columns decompose into the same two
conceptual components; the solver component differs *by construction* (single-shot in-loop vs
benchmark median).

| Q | e2e_measured Adaptive (ms) | = solver (in-loop, ms) | + overhead (ms) | analysis_grade Adaptive (ms) | = solver (benchmark median, ms) | + overhead (ms) | C_SBS benchmark-median (ms) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 11.719 | 1.488 | 10.231 | 11.452 | 1.362 | 10.090 | 1.362 |
| 10 | 34.395 | 15.392 | 19.003 | 42.184 | 23.293 | 18.890 | 22.775 |
| 50 | 119.188 | 67.113 | 52.075 | 161.211 | 110.102 | 51.109 | 108.448 |
| 100 | 242.218 | 139.238 | 102.981 | 328.120 | 227.895 | 100.226 | 223.777 |
| 500 | 1191.045 | 699.874 | 491.171 | 1556.250 | 1084.210 | 472.040 | 1064.200 |

Reconciliation notes:

- The overhead components agree closely across regimes (Q=500: 491.17 e2e vs 472.04 task; the
  e2e figure additionally carries the bookkeeping component, excluded from the task variant by
  frozen definition). This is the expected relationship and reconciles within the measured
  per-graph residual (median 5.7%, max 8.2%, `fig_c8_reconciliation`).
- The solver components differ by ~1.55× at Q=500 (699.9 vs 1084.2 ms) **by construction**:
  benchmark medians sit above typical single-shot times because the median is taken over
  repetitions after warm-up on a shared machine. Neither is "wrong"; they measure different
  things.
- The frozen record's `total_Adaptive_e2e` (1191.0 ms at Q=500) equals the e2e column to within
  rounding — verified programmatically this pass.

## Which regime answers which question

| Question | Regime |
|---|---|
| Does the pipeline physically beat SBS end-to-end? | e2e_measured (both adaptive and SBS single-shot, paired) |
| How large is the selection/feature overhead relative to the available headroom (RequiredCapture)? | analysis_grade overhead (measured in-loop) against benchmark-median headroom |
| Are tiny nominal advantages real? | Neither — apply the noise floor (`p0_noise_floor.csv`) |

Both regimes support the same scientific conclusions (overhead-bound library mode; efficacy-bound
compiled mode); they must simply never be mixed in one number or one unlabeled column.
