# README_CORRECTED — OA-ASSP Corrected Stage 20 (authoritative record)

**Read this first.** This file states which experiment is authoritative, why it exists, what was
wrong with the historical record, and how to reproduce and audit the corrected record.

## 1. Which experiment is authoritative?

| Record | Path | Status |
|---|---|---|
| **Corrected (authoritative)** | `results/stage20_corrected_20260923_092749/` | **Use these numbers.** Audit: 15/15 PASS |
| Superseded intermediate corrected run | `results/stage20_corrected_20260922_234910/` | Historical only (see its `SUPERSEDED_README.txt`); completed before per-fold tier attribution existed |
| Original Stage 20 (historical evidence) | `results/stage20_scaleup_48g_20260920_215427/` | Immutable — verified byte-identical against `FINAL_CORRECTED_AUDIT/checksums_original_before.txt` after every corrected run; never modified |

Final audit package: `FINAL_CORRECTED_AUDIT/` — see
`FINAL_CORRECTED_AUDIT/corrected_audit_report.md` for the full report.

## 2. Why a corrected experiment was needed

An implementation/methodology audit found genuine defects in the historical Stage 20 record that
could not be patched in place without breaking the immutability of the historical evidence. The
mandate was: FIX → RERUN → REANALYZE → AUDIT → FREEZE, without changing the research question:

> *When does adaptive exact shortest-path algorithm selection pay for its own feature and
> selection overhead as query workload size Q grows?*

Defects fixed (details in `FINAL_CORRECTED_AUDIT/corrected_audit_report.md` §3):

1. **A\*** — heuristic recomputed at every relaxation → per-(vertex, target) memoization;
   exactness/admissibility/consistency preserved and unit-tested.
2. **SBS leakage** — the single-best-solver policy is now constructed from **training graphs
   only**, with hard disjointness assertions against validation and test.
3. **Hardcoded validity flags** — success/reachable/valid/timeout now derived from actual solver
   execution; fabricated states raise.
4. **Timeout semantics** — a timeout can no longer appear as success/valid; explicit
   `status="timeout"` and consistent exclusion from VBS, labels and aggregates.
5. **Unfair tier comparison** — identical validation-selected hyperparameters (gini, max_depth=6,
   min_samples_leaf=3) across feature tiers 0/1/2.
6. **Validation split** — used only for selector hyperparameter selection; test untouched until
   final evaluation.
7. **Q=1 accounting** — no amortized batch cost at Q=1; graph features charged once, per-query
   costs charged for exactly one query; amortization for Q>1 documented as a deployment
   assumption.
8. **End-to-end adaptive timing** — a real adaptive execution path is timed wall-clock and its
   components reconciled against the total, replacing microbenchmark-only claims.
9. **Timing standardization** — warm-up + 5-repetition median + IQR everywhere; batched
   micro-timing (batch=50) for sub-resolution operations.
10. **Statistical discipline** — oracle-gap noise bound recorded (paired single-shot gap is
    noise-dominated, up to 2795% disagreement); pass-to-pass dispersion over 3 adaptive passes;
    paired graph-level bootstrap CIs (B=1000).
11. **Generalization attribution** — LOCO (24 folds) and LOFO (3 folds) per feature tier, every
    fold tagged with its tier and feature count.

**What was NOT changed:** graphs, query workloads, seeds, the frozen split manifest
(`configs/graph_split_manifest_48g.csv`), the solver set, the Q grid, the research question, and
the original raw data. `FINAL_CORRECTED_AUDIT/corrected_config.yaml` discloses every parameter,
including ones the original configuration hash silently omitted.

## 3. Headline results (authoritative run, 8 test graphs / 4,000 queries)

- **SBS (training-only):** Always-Bidirectional-Dijkstra (training totals: Dijkstra 6.704 s,
  Bidi 3.671 s, A* 7.335 s over 32 graphs / 16,000 instances).
- **Adaptive vs SBS:** 0 of 40 graph × Q cells below SBS under the primary cost accounting
  (analysis-grade, task variant). Smallest loss +0.378 ms.
- **Q=500 aggregate:** SBS 1064.2 ms, VBS 941.7 ms → oracle gap 122.5 ms (11.5% of SBS);
  adaptive task cost 1556.2 ms (library inference) / 1119.7 ms (compiled rules).
- **CaptureRate at Q=500:** −4.02 (library) / −0.45 (compiled). RequiredCapture: 3.85 (library)
  / 0.29 (compiled). Solver-only (overhead-free) capture: −0.163 ≈ 0.
- **Crossover:** the historical 37 µs cell is not reproduced and no new crossover is claimed.
  4 compiled-mode cells sit nominally below SBS (largest −2.419 ms = 0.23% of SBS), inside the
  9.4% pass-to-pass dispersion of the same aggregate → reported as noise.
- **Generalization:** LOCO median lift +0.00 pp (constant solver predicted in 9/24 primary-tier
  folds); LOFO median lift +0.00 pp → the selector does not generalize to unseen configurations
  or families.
- **Verdict: CASE B, scoped** — within the evaluated undirected synthetic families and graph
  sizes up to V=320, no genuine crossover was observed under the primary cost accounting; the
  binding constraint is **per-query selection overhead** in library mode (required capture 3.85
  > 1) and **selector efficacy** in compiled mode (required capture 0.29 < 1 but solver-only
  capture ≈ 0). The evidence supports the **overhead-priced decision problem** framing. This is
  not a claim of universal non-viability.

Full per-Q tables, bootstrap CIs, dispersion, Q1–Q10 answers: `FINAL_CORRECTED_AUDIT/`.

## 4. Reproduce

```bash
python -u scripts/run_stage20_corrected.py      # benchmark + adaptive passes + tuning + generalization (~5 min)
python -u scripts/analyze_corrected_stage20.py  # regenerates FINAL_CORRECTED_AUDIT artifacts (newest run by default)
python -u scripts/verify_corrected_stage20.py   # 15-check falsifiable integrity audit
python -m pytest tests/ oa_assp/tests/          # unit tests
```

Analysis/audit accept an explicit experiment ID (`argv[1]`) to pin a run. The audit re-derives
SBS, Q=1 accounting, per-graph costs, fold attribution and the reported Q8/Q9 values from frozen
raw data and tables, and fails loudly on any inconsistency.

Environment of record: Python 3.13.7, numpy 2.2.6, scipy 1.16.2, sklearn 1.8.0, matplotlib
3.10.6, Windows 11, 12-core x64 (full identity in `FINAL_CORRECTED_AUDIT/corrected_audit_report.md` §2).

## 5. Artifact map

```
FINAL_CORRECTED_AUDIT/
├── corrected_audit_report.md          full report (fixes, results, audit, conclusion)
├── corrected_results_manifest.json    machine-readable authoritative results
├── corrected_config.yaml              full parameter disclosure
├── corrected_questions.json           frozen Q1–Q10 answers with evidence
├── original_vs_corrected.csv          per-Q original vs corrected comparison
├── bootstrap_analysis_grade.csv       graph-level bootstrap CIs (Q=500)
├── checksums.txt                      SHA-256 manifest: 167 hashes (40 experiment + 75 source/config
│                                      + 52 historical). Predates the closure pass; superseded as the
│                                      authoritative manifest by LOCK_CHECKSUMS.txt (see below).
├── LOCK_CHECKSUMS.txt                 AUTHORITATIVE lock manifest for FINAL_CORRECTED_AUDIT/**
│                                      (relative path + SHA-256 + size per file)
├── SOURCE_PROVENANCE_MANIFEST.json    historical vs current source identity + per-file hashes
├── checksums_original_before.txt      pre-experiment baseline of the original (52 files)
├── figures/                           fig_c1..fig_c9 (PNG+PDF)
└── logs/                              corrected run, analysis, and audit logs
```

Raw data: `results/stage20_corrected_20260923_092749/raw/` (72,000 benchmark rows),
`processed/` (manifest, capture tables, generalization folds, oracle crosscheck, dispersion),
`figures/`.

Note: `results/stage20_corrected_20260923_092749/tables/` is created by
`scripts/run_stage20_corrected.py` but is intentionally empty — the corrected run's table writer
was never populated; the corrected tables live in this audit directory and in the experiment's
`processed/` CSVs. The empty directory was removed during the closure pass so that the frozen tree
contains no unexplained empty authoritative directories.

## 6. Status

**FROZEN (2026-09-30).** All 15 integrity checks pass for
`stage20_corrected_20260923_092749`. The corrected empirical record is the only basis for any
subsequent manuscript. Do not write the paper from the superseded or original records.
