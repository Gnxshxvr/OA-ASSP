# OA-ASSP — Corrected Stage 20 Audit Report (authoritative)

Experiment ID: **`stage20_corrected_20260923_092749`** (authoritative).
Superseded intermediate run: `stage20_corrected_20260922_234910` (labeled by `SUPERSEDED_README.txt`; log kept at `FINAL_CORRECTED_AUDIT/logs/corrected_run_superseded_draft_234910.log`).
Historical evidence, never modified: `results/stage20_scaleup_48g_20260920_215427`.

Status: **FROZEN.** All 15 integrity checks passed (log: `FINAL_CORRECTED_AUDIT/logs/verify_092749.log`).
Worked log of the authoritative run: `FINAL_CORRECTED_AUDIT/logs/corrected_run.log`.

---

## 1. Executive summary

The corrected experiment answers the mandated research question — *when does adaptive exact
shortest-path algorithm selection pay for its own feature and selection overhead as query
workload size Q grows?* — under a measurement protocol in which every reported cost is a
warm-up + repetition median and the adaptive path is timed end-to-end. The verdict is:

> **CASE B, refined to an overhead-priced decision problem.** Within the evaluated undirected
> synthetic graph families and graph sizes up to V=320, **no genuine crossover was observed under
> the primary cost accounting**: 0 of 40 graph × Q cells. At Q=500 the oracle gap is
> 122.5 ms (11.5% of SBS), while the selection overhead is 472.0 ms (library inference) or
> 35.5 ms (compiled rules). Required capture exceeds 1 by 3.9× (library) at every measured Q
> with Q ≥ 10, so even a perfect selector could not pay under library inference. With compiled
> rules required capture is 0.29 < 1 — the overhead is no longer the binding constraint, but the
> achieved solver-only capture is −0.163 ≈ 0, so the selector has nothing to capture and the
> compiled variant does not pay either. The historical "37 µs crossover at Q=500" is **not
> reproduced** and no new crossover is claimed: 4 compiled-rule cells sit a fraction of a
> percent below SBS, an order of magnitude inside the 9.4% pass-to-pass dispersion of the same
> aggregate quantity. This conclusion is scoped to the evaluated benchmark (3 synthetic
> undirected families, V ≤ 320, 8 test graphs, Python timing, the stated workload model) and is
> not a claim of universal non-viability.

Three quantified, separable causes (no single-cause story):

1. **Selector efficacy (solver side).** Solver-only capture at Q=500 is **−0.163** of the oracle
   gap: the selector's expected solver cost equals the SBS policy's (chosen-solver total
   1084.2 ms vs SBS 1064.2 ms). Whenever inference is cheap (compiled rules, required capture
   0.29), this is the binding constraint: the selector does not beat Always-Bidirectional-Dijkstra
   even overhead-free.
2. **Per-query selection overhead (library mode).** Library single-row inference
   (87.9 µs median) prices the decision at ~3.9× the entire available headroom at Q=500. This is
   the binding constraint for the library deployment mode.
3. **Small oracle gap.** The headroom selection could capture is only 11.5% of SBS cost
   (122.5 ms of 1064.2 ms at Q=500 over the 8 test graphs), because Always-Bidirectional-Dijkstra
   is already the per-instance winner on most instances.

## 2. Configuration identity

| Field | Value |
|---|---|
| Configuration hash (SHA-256) | `91cef3a3dbfa46115869c72f596d9c2b7f266e4c711d0d89dac14ad498fbea62` |
| Source hash (72 files, SHA-256) | `c668df6b5e2a2034892a9d6089683f2ca50a05c77fc70ed35d01e49db8252721` |
| Python | 3.13.7 (MSC v.1944 64 bit, AMD64) |
| Platform | Windows-11-10.0.26200, Intel 12th-gen, 12 CPUs |
| numpy / scipy / sklearn / matplotlib | 2.2.6 / 1.16.2 / 1.8.0 / 3.10.6 |
| Run timestamp (UTC) | 2026-09-23T04:02:53Z; analysis + audit regenerated 2026-09-30 |
| Total run wall clock | 303.4 s |
| Seeds | master 42, base 100, query seed = graph seed + 2000, selector 42, bootstrap 4001 |
| Split | frozen `configs/graph_split_manifest_48g.csv` (32/8/8 train/val/test) |
| Full parameter disclosure | `corrected_config.yaml` |

## 3. What was wrong → what was fixed → what was not changed

Fix sites are `oa_assp/` modules and `scripts/run_stage20_corrected.py`. The original experiment
was never modified; the superseded 234910 run is retained as historical evidence only.

| # | Area | What was wrong | Fix (site) | Tests / audit evidence |
|---|---|---|---|---|
| 1 | A* heuristic | Euclidean heuristic recomputed at every relaxation | Per-(vertex, target) memoization; admissibility, consistency, exactness and path correctness preserved (`oa_assp/algorithms/astar.py`) | `test_astar_cached.py`: cached distances == reference distances, paths verified |
| 2 | SBS construction | Risk of validation/test leakage into policy selection | SBS = argmin of fixed-policy totals over **training graphs only**; hard assertions train ∩ val = ∅, train ∩ test = ∅ (`oa_assp/benchmark/oracle.py`) | `test_sbs_training_only.py`; audit `sbs_training_only`, `sbs_replayable_from_raw` |
| 3 | Validity flags | Hardcoded benchmark fields could fabricate results | success/reachable/valid/distance/path/timeout all derived from actual execution; fabricated states raise (`oa_assp/benchmark/runner.py`) | `test_timeout_and_validity.py`; audit `validity_derived` |
| 4 | Timeout semantics | A timeout could masquerade as success/valid | Explicit `status="timeout"`, `success=False`, `valid=False`; timed-out runs excluded from VBS, selector labels and aggregates (0 timeouts occurred in this run) (`oa_assp/benchmark/runner.py`) | `test_timeout_and_validity.py`; audit `timeout_semantics` |
| 5 | Tier fairness | Different effective hyperparameters across feature tiers | Validation-selected configuration (gini, max_depth=6, min_samples_leaf=3) frozen and identical across tiers 0/1/2 (`oa_assp/selector/decision_tree.py`, `tuning.py`) | `test_selector.py`; audit `tier_hyperparameters_identical` |
| 6 | Validation split | Weakly used | Validation used **only** for selector hyperparameter selection (grid: gini; max_depth 2–6; min_samples_leaf {1,2,3,5,10}); tune on train, select on val, freeze, evaluate once on test | `test_sbs_training_only.py`, `test_selector.py` |
| 7 | Q=1 accounting | Amortized batch cost charged at Q=1 | Q=1 charges graph features once + query features/selection/solver for exactly one query; for Q>1 graph-level cost amortized under a documented deployment assumption (graph stays resident) (`oa_assp/benchmark/adaptive.py`) | audit `q1_accounting` |
| 8 | End-to-end timing | Overhead claims rested on separately measured microbenchmarks | Real adaptive path timed wall-clock: graph features → query features → selector inference → selected solver; components measured separately and reconciled against end-to-end (`oa_assp/benchmark/adaptive.py`) | audit `q1_accounting`, `cost_traceability`; figure `fig_c8_reconciliation` |
| 9 | Timing standardization | Single-shot microsecond measurements treated as precise | warm-up + 5-repetition median + IQR everywhere; batched micro-timing (batch=50) for sub-resolution operations (`oa_assp/benchmark/timing.py`) | `test_benchmark.py` |
| 10 | Cost accounting | Implicit feature/selection cost model | Explicit C_graph_feature / C_query_feature / C_selection / C_solver; C_Adaptive(Q) = C_graph_feature + Σ recurring terms | audit `q1_accounting`, `cost_traceability` |
| 11 | Capture analysis | One blended capture number | Task / end-to-end / analysis-grade variants; solver-only (overhead-free) capture; RequiredCapture; per-graph and aggregate; compiled-rule variant measured over the same passes (`oa_assp/analysis/capture.py`) | `test_capture.py` |
| 12 | Generalization | No held-out-configuration attribution | LOCO (24 folds) and LOFO (3 folds) per feature tier; every fold records its tier and feature count (`oa_assp/selector/generalization.py`) | audit `generalization_attribution`, `reported_values_match_frozen_tables` |
| 13 | Statistical reporting | Point estimates without dispersion | Paired graph-level bootstrap (B=1000, seed 4001); pass-to-pass dispersion (3 passes) for every adaptive aggregate (`oa_assp/analysis/bootstrap.py`) | section 6 dispersion; audit `oracle_gap_crosscheck_recorded` |
| 14 | Oracle-gap noise | Noise in the central quantity uncontrolled | Repeated-median gap is primary; paired single-shot gap recorded as a noise bound (disagrees by up to 2795%) (`oa_assp/benchmark/oracle.py`) | audit `oracle_gap_crosscheck_recorded` |

**Not changed (deliberately).** Graph families and parameters, query workloads, all seeds, the
frozen split manifest (loaded from the original experiment), the solver set
{Dijkstra, Bidirectional Dijkstra, A*}, the Q grid {1,10,50,100,500}, 500 queries/graph, the
research question, and the original raw data. `corrected_config.yaml` documents every parameter
that the original configuration hash silently omitted (weight multiplier/noise/range, geometric
mechanism, directedness, timing repetitions, micro-timing protocol, bootstrap seed).

## 4. Original Stage 20 vs corrected Stage 20

Aggregate over the 8 test graphs (per-graph sums; full table in `original_vs_corrected.csv`):

| Q | Original C_SBS / C_Adaptive (ms) | Original Δ (ms, ×SBS) | Corrected C_SBS / C_Adaptive (ms) | Corrected Δ (ms, ×SBS) |
|---|---|---|---|---|
| 1 | 0.64 / 5.71 | +5.07 (×8.99) | 1.36 / 11.45 | +10.09 (×8.39) |
| 10 | 9.46 / 14.75 | +5.29 (×1.56) | 22.77 / 42.18 | +19.41 (×1.84) |
| 50 | 52.58 / 58.58 | +6.00 (×1.11) | 108.45 / 161.21 | +52.76 (×1.48) |
| 100 | 106.35 / 113.37 | +7.01 (×1.07) | 223.78 / 328.12 | +104.34 (×1.47) |
| 500 | 564.11 / 577.50 | +13.38 (×1.024) | 1064.20 / 1556.25 | +492.05 (×1.46) |

Reading of the comparison:

- The original protocol (no warm-up/median discipline) compressed solver timings: corrected
  C_SBS at Q=500 is ~1.9× the original. The original's adaptive−SBS gap of 13.4 ms at Q=500
  understated the honest gap (492.0 ms) by ~37×.
- The original crossover cell (−0.037 ms at `scalefree_V80_D6_s138`, Q=500, i.e. 0.0066% of that
  cell's SBS cost) sat far below the corrected protocol's noise floor. The corrected record
  contains **0 of 40** cells below SBS and the historical cell is absent; the nominal compiled
  variant cells are inside pass dispersion and are not reported as a crossover.
- Both records agree qualitatively at small Q (adaptive loses heavily at Q=1); they disagree on
  the asymptote: the original record approached break-even (×1.024) while the corrected record
  plateaus at ×1.46 (library). The plateau has an overhead-independent component: solver-only
  capture ≈ 0.

Corrected-only analyses with no original counterpart: compiled-rule inference variant,
solver-only capture, oracle-gap noise bound, per-fold tier attribution of LOCO/LOFO,
pass-to-pass dispersion, graph-level bootstrap CIs, full parameter disclosure.

## 5. Corrected benchmark results (authoritative numbers)

Unless a table states otherwise, all costs in sections 5–7 are **`analysis_grade` (Analysis-Grade
Normalized Cost)**: measured adaptive overhead + benchmark-median solver costs. They are not
physical execution times; the **`e2e_measured`** (End-to-End Measured) counterparts are given in
`COST_REGIME_DEFINITION.md` (Q=500: e2e 1191.0 ms vs analysis-grade 1556.2 ms; the difference is
the single-shot-vs-benchmark-median solver regime, by construction). Regime definitions and the
full reconciliation table: `COST_REGIME_DEFINITION.md`.

Primary (analysis-grade) aggregate over 8 test graphs / 4,000 queries, per workload size Q:

| Q | SBS (ms) | VBS (ms) | Adaptive task (ms) | Sel. overhead (ms) | OracleGap (ms) | CaptureRate | RequiredCapture | Solver-only capture |
|---|---|---|---|---|---|---|---|---|
| 1 | 1.362 | 1.350 | 11.452 | 10.090 | 0.012 | −847.89 | 847.89 | 0.000 |
| 10 | 22.775 | 20.016 | 42.184 | 18.905 | 2.759 | −7.04 | 6.85 | −0.188 |
| 50 | 108.448 | 94.738 | 161.211 | 51.058 | 13.710 | −3.85 | 3.73 | −0.121 |
| 100 | 223.777 | 198.342 | 328.120 | 100.196 | 25.435 | −4.10 | 3.94 | −0.162 |
| 500 | 1064.200 | 941.677 | 1556.250 | 472.044 | 122.523 | −4.02 | 3.85 | −0.163 |

Compiled-rule inference variant (same passes, same trees compiled to nested conditionals):

| Q | SBS (ms) | Adaptive task (ms) | Sel. overhead (ms) | CaptureRate | RequiredCapture |
|---|---|---|---|---|---|
| 1 | 1.362 | 10.017 | 8.655 | −729.90 | 729.90 |
| 10 | 22.775 | 32.536 | 9.182 | −3.53 | 3.34 |
| 50 | 108.448 | 121.371 | 11.266 | −0.95 | 0.83 |
| 100 | 223.777 | 241.809 | 14.013 | −0.71 | 0.55 |
| 500 | 1064.200 | 1119.706 | 35.530 | −0.45 | 0.29 |

SBS identity (training-only): **Always-Bidirectional-Dijkstra** (training totals, 32 graphs /
16,000 instances: Dijkstra 6.704 s, Bidirectional Dijkstra 3.671 s, A* 7.335 s). Validation and
test totals are in the manifest (`sbs.reference_policy_totals_s` covers training; per-split
figures in `sbs_audit.csv`). The selected policy is unchanged from the original experiment.

Selector configuration (validation-selected, identical across tiers): gini, max_depth=6,
min_samples_leaf=3 (61 leaves; historical frozen setting was max_depth=4). Test exact accuracy:
tier 0 = 72.78%, tier 1 = 72.50%, tier 2 = 73.30% — statistically indistinguishable; richer
features cost more than they return (tier-2 compiled required capture 0.42 > tier-0 0.11).

Crossover search (primary criterion = task-variant cost, identical for both modes; definitions in
`CROSSOVER_DEFINITION.md`): 40 cells (8 test graphs × 5 Q) — **0 genuine crossover cells**;
library 0/40 nominal (smallest loss +0.378 ms), compiled 3/40 nominal under the primary
accounting (largest −1.486 ms = 0.14% of SBS) and 4/40 under the *secondary conservative compiled
sensitivity analysis* (largest −2.419 ms = 0.227% of SBS) — all an order of magnitude below the
empirical noise floor (9.4–16.3%) → **no crossover claimed under any labeled variant**.

## 6. Measurement quality

- **Pass-to-pass dispersion (3 passes).** The sign of adaptive − SBS is stable in all 9 tier × Q
  cells. At the primary tier: Q=1 median Δ +11.742 ms (range 11.709–12.553), Q=10 median
  +25.504 ms (35.360–39.306 for C_adaptive), Q=500 median +792.058 ms (C_adaptive 1256.6–1491.5).
  The compiled aggregate's 9.4% dispersion bounds any nominal compiled crossover. The
  measurement-noise floor (per-row median IQR 14.4%; pass dispersions 16.3% library / 9.4%
  compiled) is tabulated in `p0_noise_floor.csv`; no effect below ~10% of the same aggregate is
  interpretable.
- **Oracle-gap noise bound.** The paired single-shot gap disagrees with the repeated-median gap by
  up to 2795% (Q=500: 122.523 ms vs −4.547 ms) → the single-shot gap is noise-dominated; the
  benchmark-median gap is primary (`oracle_gap_crosscheck.csv`).
- **Graph-level paired bootstrap (B=1000, 8 test graphs, Q=500, analysis-grade).**
  adaptive − SBS = 0.492 s, 95% CI [0.383, 0.615]; adaptive/SBS ratio 1.462 [1.324, 1.734];
  CaptureRate −4.016 [−11.928, −2.485]; RequiredCapture 3.853 [2.288, 12.003]; solver-only
  capture −0.163 [−0.473, +0.086]; oracle gap 0.1225 s [0.036, 0.239].
- **Component reconciliation.** Component sums reconcile with the end-to-end adaptive wall clock
  within measurement noise (figure `fig_c8_reconciliation.png`).

## 7. CaptureRate and generalization analysis

**CaptureRate (primary tier, analysis-grade, library):** negative at every measured Q in this
benchmark — the adaptive pipeline is strictly worse than SBS under this accounting. RequiredCapture falls from 847.9 (Q=1, graph
features charged once) to 3.85 (Q=500): the fixed graph-feature cost amortizes, but per-query
selection (~472 ms over 500 queries) keeps required capture ~3.9× above 1. Solver-only capture
(what a zero-overhead selector would capture) is ≈ 0 at Q=1 and slightly negative thereafter:
**the selector's solver choices are no better than Always-Bidirectional-Dijkstra.** With compiled
rules, RequiredCapture at Q=500 drops to 0.29 — below 1 — so the barrier in compiled mode is
purely selector efficacy, not overhead. This is the "overhead-priced decision problem" framing:
the price of the decision (library ≈ 3.9× headroom; compiled ≈ 0.29× headroom) and the value of
the decision (≈ 0 captured) are measured separately, and neither is favorable at this scale.
Note on complementarity: the benchmark **does** contain measurable instance-level solver
complementarity, particularly within geometric graphs (A* is the per-instance winner on ~6–20%
of queries in those cells), but the evaluated feature/selector pipeline does not capture enough
of that complementarity to offset its computational overhead.

**Generalization (identical hyperparameters per fold; tier-attributed).**

| Protocol | Tier | Folds | Median exact | Majority | Median lift | Constant-prediction folds |
|---|---|---|---|---|---|---|
| standard held-out | 1 | 1 | 72.50% | 72.60% | −0.10 pp | 0/1 |
| leave-one-cell-out | 0 | 24 | 79.10% | 77.95% | +0.00 pp | 15/24 |
| leave-one-cell-out | 1 | 24 | 80.80% | 77.95% | +0.00 pp | 9/24 |
| leave-one-family-out | 0 | 3 | 83.76% | 83.45% | +0.06 pp | 1/3 |
| leave-one-family-out | 1 | 3 | 79.09% | 83.45% | +0.00 pp | 1/3 |

Median lift over the majority-label baseline is ≈ 0 everywhere, and the tree collapses to a
constant solver in most held-out-cell folds (15/24 and 9/24) and in LOFO folds. **The selector
does not generalize to unseen configurations or families: Q8 = No, Q9 = No.** This is consistent
with solver-only capture ≈ 0: there is little per-instance structure for the selector to exploit
at these graph sizes (V ≤ 320), where a single solver dominates almost everywhere.

## 8. Final integrity audit (15/15 PASS)

Run: `python -u scripts/verify_corrected_stage20.py` (defaults to the newest
`stage20_corrected_*`); log `logs/verify_092749.log`, 2026-09-30.

1. PASS original_stage20_immutable — 52 historical files byte-identical to the pre-experiment baseline
2. PASS raw_shape — 72,000 rows = 24,000 queries × 3 algorithms on 48 graphs
3. PASS timeout_semantics — 0 timeouts; none reported as success/valid
4. PASS validity_derived — 0 invalid rows, all with a failure reason
5. PASS runtime_positivity — 72,000 rows with positive median runtime
6. PASS sbs_training_only — SBS reference disjoint from validation and test
7. PASS sbs_replayable_from_raw — argmin over 16,000 training queries reproduces Always-Bidirectional-Dijkstra; all fixed-policy totals match the manifest to 1e-6
8. PASS tier_hyperparameters_identical — all tiers use max_depth=6, min_samples_leaf=3 (validation-selected)
9. PASS q1_accounting — at Q=1 graph features charged once (1051.10 µs), query features, vector assembly and selection charged once each for exactly one query
10. PASS cost_traceability — every per-graph C_SBS / C_VBS at Q=500 recomputes exactly from raw benchmark medians
11. PASS oracle_gap_crosscheck_recorded — Q=500 gap: benchmark medians 122.523 ms vs paired single-shot −4.547 ms
12. PASS generalization_attribution — every fold records its tier; tiers 0 and 1 each contribute 24 cell folds + 3 family folds
13. PASS reported_values_match_frozen_tables — Q8/Q9 numbers in the artifacts recompute from the frozen fold table for the primary tier
14. PASS artifact_completeness — 9 corrected figures, all named `fig_c*`; no historical figure names
15. PASS no_unreproduced_crossover_claimed — 0 of 40 cells show a gain; the historical 37 µs cell is absent

Original Stage 20 was additionally verified byte-identical after both corrected runs
(52 files vs `checksums_original_before.txt`).

## 9. Limitations

1. **Scale.** V ∈ {40, 80, 160, 320}; solver differences (and hence the oracle gap, ~11.5%) may
   grow with graph size; the crossover question at much larger V remains open.
2. **Solver diversity.** Three exact solvers; a wider portfolio could widen the oracle gap, but
   solver diversity is demonstrably not the current bottleneck (solver-only capture ≈ 0 with the
   existing portfolio).
3. **Workload model.** Independent random (s,t) queries per graph; no locality/adversarial query
   distributions, which could change per-instance solver dominance.
4. **Inference modes.** The library-vs-compiled distinction is itself part of the finding: the
   deployment mode determines which constraint binds. Neither mode pays at this scale.
5. **Timing environment.** Windows desktop, OneDrive-synced directory, 12-core consumer CPU;
   absolute numbers are machine-specific (all comparisons are paired on the same machine/run).
6. **3 benchmark repetitions** per solver per (graph, query) cell plus 3 adaptive passes —
   adequate for the reported medians and dispersion, but the compiled-variant margin question
   (cells ≪ 1% apart) would need far more repetitions to resolve; we explicitly do not resolve it.
7. **Single split.** One frozen 32/8/8 split (LOCO/LOFO mitigate but do not eliminate
   split-specific variance).

## 10. Scientific conclusion

The corrected, audited record supports the **overhead-priced decision problem** framing:
adaptive exact shortest-path algorithm selection at these graph scales is a decision whose price
(measured end-to-end: 472 ms per 500 queries with library inference, 35.5 ms with compiled rules)
exceeds the value of the decision (oracle headroom 122.5 ms per 500 queries, of which the selector
captures ≈ 0). At Q=1 the price is dominated by one-time graph characterization; by Q=10 it is
dominated by per-query selection; at no measured Q does the value exceed the price, and in
compiled mode the price is already negligible while the value remains ≈ 0. **CASE B** — with the
refinement that the binding constraint switches from selection overhead (library mode) to selector
efficacy (compiled mode) as inference cost falls.

## 11. Reproducibility

```bash
# 1. Corrected benchmark (authoritative run; ~5 min on the recorded machine)
python -u scripts/run_stage20_corrected.py

# 2. Post-hoc analysis -> FINAL_CORRECTED_AUDIT artifacts
python -u scripts/analyze_corrected_stage20.py        # defaults to newest stage20_corrected_*

# 3. Integrity audit (15 checks)
python -u scripts/verify_corrected_stage20.py         # defaults to newest stage20_corrected_*

# 4. Unit tests
python -m pytest tests/ oa_assp/tests/
```

Both analysis and audit accept an explicit experiment ID as `argv[1]` to pin a run. The audit
re-derives SBS, Q=1 accounting, per-graph costs, fold attribution and all reported Q8/Q9 values
from the frozen raw data and tables — it fails loudly on any inconsistency.

## 12. Authoritative artifact paths

- Raw / processed / tables / figures: `results/stage20_corrected_20260923_092749/`
  (manifest: `processed/stage20_corrected_20260923_092749_manifest.json`)
- This directory `FINAL_CORRECTED_AUDIT/`: `corrected_results_manifest.json`,
  `corrected_config.yaml`, `corrected_questions.json`, `original_vs_corrected.csv`,
  `bootstrap_analysis_grade.csv`, `checksums.txt` (167 hashes: 40 corrected-experiment
  artifacts + 75 source/config files + 52 historical files), `LOCK_CHECKSUMS.txt` (authoritative
  manifest for this directory), `SOURCE_PROVENANCE_MANIFEST.json`,
  `checksums_original_before.txt` (original baseline), `figures/` (18 files),
  `logs/` (corrected run, analysis, audit)
- Historical: `results/stage20_scaleup_48g_20260920_215427/` (immutable)
- Superseded: `results/stage20_corrected_20260922_234910/` (see its `SUPERSEDED_README.txt`)

## 13. Answers to the ten standing questions (frozen in `corrected_questions.json`)

- **Q1 — Does adaptive beat SBS anywhere?** No. 0 of 40 cells (primary); 4 of 40 nominal cells
  in compiled mode are inside pass dispersion and are not a crossover.
- **Q2 — Why not?** Two separable reasons: solver-only capture ≈ −0.16 (selector adds nothing
  overhead-free) and per-query selection overhead (library: 3.9× the headroom; compiled: 0.29×).
- **Q3 — How much headroom?** Small but real: 122.5 ms = 11.5% of SBS at Q=500.
- **Q4 — Does capture pay?** No: CaptureRate −4.02 at Q=500 (library), −0.45 (compiled).
- **Q5 — Capture vs Q?** Roughly Q-independent and negative at every measured Q in this
  benchmark (−848, −7.0, −3.8, −4.1, −4.0 for Q = 1, 10, 50, 100, 500).
- **Q6 — Required capture vs Q?** Falls with Q (847.9 → 3.85 library; → 0.29 compiled) as the
  one-time graph cost amortizes, but does not cross 1 at any measured Q in library mode.
- **Q7 — Do richer feature tiers pay?** No: tier 2 costs more (required capture 0.42 compiled vs
  tier 0's 0.11) for statistically indistinguishable accuracy.
- **Q8 — Generalizes to unseen configurations?** No (LOCO median lift +0.00 pp; constant
  prediction in 9/24 primary-tier folds).
- **Q9 — Generalizes across families?** No (LOFO median lift +0.00 pp; 1/3 constant folds).
- **Q10 — Bottleneck?** Selector efficacy whenever inference is cheap (compiled); per-query
  selection overhead when inference goes through a model library. Solver diversity is not the
  constraint; graph scale and workload size only modulate the amortization.
