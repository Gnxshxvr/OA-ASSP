# OA-ASSP: Overhead-Aware Adaptive Algorithm Selection for Exact Shortest Paths

## 0. READ THIS FIRST — which record is authoritative

| Record | Path | Status |
|---|---|---|
| **Corrected Stage 20 (AUTHORITATIVE)** | `results/stage20_corrected_20260923_092749/` | **Use these numbers.** 15/15 integrity checks pass. |
| **Authoritative audit package** | `FINAL_CORRECTED_AUDIT/` | Full report, manifests, provenance, checksums. |
| Superseded intermediate corrected run | `results/stage20_corrected_20260922_234910/` | Historical only (see its `SUPERSEDED_README.txt`). |
| Original Stage 20 (HISTORICAL, immutable) | `results/stage20_scaleup_48g_20260920_215427/` | Historical evidence, never modified. **NOT the current result.** |
| Development-era artifacts (NON-AUTHORITATIVE) | `results/_archive_dev/` | Archived and labeled; see its `README_NON_AUTHORITATIVE.md`. |

**Start here:** [`README_CORRECTED.md`](README_CORRECTED.md) for the authoritative record, and
[`FINAL_CORRECTED_AUDIT/corrected_audit_report.md`](FINAL_CORRECTED_AUDIT/corrected_audit_report.md)
for the full corrected audit report.

**Do not write, cite, or plot from the original Stage 20 run or from `results/_archive_dev/`.**
Section 5 below preserves the original record's findings for historical context only.

---

## 1. Research Question

> *When does adaptive exact shortest-path algorithm selection pay for its own feature and
> selection overhead as query workload size Q grows?*

Shortest-path algorithm selection has traditionally been evaluated on classifier accuracy or
theoretical solver speedups in isolation, omitting the wall-clock cost of feature extraction and
model inference. OA-ASSP introduces explicit wall-clock cost accounting over the end-to-end path:

$$C_{\text{adaptive}}(Q) = C_{\text{graph\_feature}} + \sum_{q=1}^Q \left( C_{\text{query\_feature}, q} + C_{\text{selection}, q} + C_{\text{solver}, q} \right)$$

Graph-level features are computed once per graph ($C_{\text{graph\_feature}}$) and amortized across
$Q$ incoming queries; query-level features and decision-tree inference are incurred per query.

---

## 2. Authoritative Result (corrected Stage 20)

**Experiment ID:** `stage20_corrected_20260923_092749`
**Config hash:** `91cef3a3dbfa46115869c72f596d9c2b7f266e4c711d0d89dac14ad498fbea62`
**Verdict: CASE B, scoped** — within the evaluated undirected synthetic families and graph sizes up
to V=320, **no genuine crossover was observed** under the primary cost accounting.

Headline numbers (analysis-grade, 8 test graphs / 4,000 queries, Q=500):

| Quantity | Value |
|---|---|
| SBS (training-only, Always-Bidirectional-Dijkstra) | 1064.200 ms |
| VBS | 941.677 ms |
| Oracle gap | 122.523 ms (11.5% of SBS) |
| Adaptive (library inference) | 1556.250 ms |
| Adaptive (compiled rules) | 1119.723 ms |
| Selection overhead (library / compiled) | 472.040 ms / 35.513 ms |
| RequiredCapture (library / compiled) | 3.8527 / 0.2898 |
| Solver-only capture | −0.1633 |
| Genuine crossover cells | **0 / 40** |

Two separable causes: (1) **selector efficacy** — solver-only capture ≈ −0.16, so the selector adds
nothing overhead-free; (2) **per-query selection overhead** — library inference prices the decision
at ~3.9× the entire available headroom. Generalization fails: LOCO/LOFO median lift ≈ 0 pp.

This is not a claim of universal non-viability. Scope: 3 synthetic undirected families, V ≤ 320,
8 held-out test graphs, one frozen split, Python timing, 3-solver portfolio. See
[`FINAL_CORRECTED_AUDIT/corrected_audit_report.md`](FINAL_CORRECTED_AUDIT/corrected_audit_report.md) §9.

---

## 3. Reproduce

```bash
python -u scripts/run_stage20_corrected.py        # benchmark + adaptive passes + tuning + generalization
python -u scripts/analyze_corrected_stage20.py    # post-hoc analysis -> audit_runs/<timestamp>/
python -u scripts/verify_corrected_stage20.py     # 15-check falsifiable integrity audit (read-only)
python -m pytest tests/ oa_assp/tests/            # unit tests (79 unique / 158 collected cases)
```

The authoritative audit package `FINAL_CORRECTED_AUDIT/` is **READ-ONLY**. Analysis and audit
scripts write to run-scoped `audit_runs/<run_id>/` directories by default; writing into the frozen
package requires an explicit `--output-dir FINAL_CORRECTED_AUDIT --force`. Full reproduction and
verification sequence: [`REPRODUCTION.md`](REPRODUCTION.md).

Environment of record: Python 3.13.7, numpy 2.2.6, scipy 1.16.2, sklearn 1.8.0, matplotlib 3.10.6,
Windows 11, 12-core x64.

---

## 4. Repository Layout

```text
DAA_PROJ/
├── README.md                          # this file
├── README_CORRECTED.md                # authoritative record pointer
├── REPRODUCTION.md                    # full reproduce + verify sequence
├── FINAL_LOCK_MANIFEST.json           # final machine-readable lock manifest
├── configs/                           # frozen configuration & split manifests
├── oa_assp/                           # core Python package (algorithms, benchmark, features, selector)
├── scripts/                           # experiment, analysis and audit scripts
├── tests/                             # unit test suite (re-export stubs)
├── audit_runs/                        # run-scoped analysis/audit outputs (git-ignored)
├── FINAL_CORRECTED_AUDIT/             # AUTHORITATIVE audit package (READ-ONLY)
└── results/
    ├── stage20_corrected_20260923_092749/   # AUTHORITATIVE corrected experiment
    ├── stage20_corrected_20260922_234910/   # SUPERSEDED intermediate run
    ├── stage20_scaleup_48g_20260920_215427/ # HISTORICAL original run (immutable)
    └── _archive_dev/                        # NON-AUTHORITATIVE development artifacts
```

---

## 5. HISTORICAL — Original Stage 20 Record (SUPERSEDED, NOT CURRENT)

> **WARNING.** Everything in this section describes the **original, superseded** Stage 20 run
> (`stage20_scaleup_48g_20260920_215427`) and is retained for historical context only. Its timing
> protocol lacked warm-up/median discipline, which compressed solver timings. **Do not cite these
> numbers as current results.** The corrected record in §2 supersedes them entirely.

**Retracted crossover claim.** The original record reported a marginal adaptive win at
`scalefree_V80_D6_s138`, Q=500: Δ = −0.037 ms, GapClosed = +0.79%. **This crossover is retracted.**
The corrected protocol does not reproduce it: that same cell now measures **+36.84 ms** (a loss),
and the corrected record contains 0 genuine crossover cells in 40. The original cell's magnitude was
0.0066% of that cell's SBS cost — far inside the empirical noise floor (9.4–16.3%).

Other original findings, for historical context only: Always-Bidirectional-Dijkstra dominated the
fixed-policy comparison (75.17% of instances); oracle headroom at Q=500 was reported as 8.99%; the
adaptive deficit at Q=500 was reported as +13.385 ms (+2.37%); hypothesis H5 (net positive adaptive
advantage) was not supported. Corrected counterparts: see §2.

The original run remains byte-identical to its pre-experiment baseline (52 files verified against
`FINAL_CORRECTED_AUDIT/checksums_original_before.txt`).

---

## 6. Development-Era Artifacts

`results/_archive_dev/` holds development-era figures, tables, processed outputs, raw smoke-test
records, and preflight runs from 2026-09-20. These are **NON-AUTHORITATIVE**, were moved out of the
live `results/` surface during the closure pass, and are retained as historical evidence only. See
[`results/_archive_dev/README_NON_AUTHORITATIVE.md`](results/_archive_dev/README_NON_AUTHORITATIVE.md).
