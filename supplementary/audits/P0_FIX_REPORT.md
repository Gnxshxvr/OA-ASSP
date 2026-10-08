# P0 FIX REPORT — OA-ASSP (post-adversarial-audit correction pass)

Scope: four P0 fixes only. **No frozen data touched** (`stage20_corrected_20260923_092749` raw
bytes unchanged — verified by the integrity audit's `original_stage20_immutable` check pattern
and by the fact that every number below was recomputed *from* the frozen raw files).

## F1 — Common-query-set SBS comparison (P0-1) — PASS

Artifacts: `COMMON_QUERY_SBS.md`, `common_query_sbs.csv` (comparison A = all 16,000 valid
training queries with all three solvers; B = 5,000 geometric-eligible queries; C = frozen
eligibility-aware diagnostic, retained and labeled NOT comparable across rows).

Result: SBS identity **unchanged — Bidirectional Dijkstra** — on every fair partition:
all-training 3.6708 s (vs Dijkstra 6.7038, A* 7.6452); geometric-eligible 1.6092 s (vs 1.9206 /
2.5516). **Consequence for downstream analysis: none** (no headline number changes). The
misleading-as-printed manifest table is superseded by comparison A for any manuscript use; the
original eligibility semantics remain untouched and govern VBS/labels.

## F2 — Cost-regime separation (P0-2) — PASS

Artifacts: `COST_REGIME_DEFINITION.md`, `p0_regime_reconciliation.csv`.

- `e2e_measured` (End-to-End Measured): in-loop wall clock incl. single-shot solver.
- `analysis_grade` (Analysis-Grade Normalized): measured overhead + benchmark-median solver
  cost; **not** a physical time; exists to isolate overhead from single-shot solver noise.
- Reconciliation at Q=500: e2e 1191.0 ms (solver 699.9 + overhead 491.2) vs analysis-grade
  1556.2 ms (solver 1084.2 + overhead 472.0) vs C_SBS 1064.2 ms. Overhead components agree
  across regimes (~4%); solver components differ ~1.55× **by construction** (stated).
- The authoritative report §5 now carries an explicit regime banner; every regime-sensitive
  statement is labeled.

## F3 — Primary crossover definition (P0-3) — PASS

Artifacts: `CROSSOVER_DEFINITION.md`, `p0_crossover_unified.csv`, `p0_noise_floor.csv`.

- PRIMARY = task-variant cost, **identical accounting for library and compiled**; GENUINE
  crossover = primary condition AND advantage ≥ noise floor (16.3% primary; 9.4% compiled
  dispersion for the compiled aggregate).
- **Primary result: 0/40 genuine crossover cells** (library 0/40 nominal; compiled 3/40 nominal
  under primary accounting, largest −1.486 ms = 0.14% of SBS).
- Secondary conservative compiled sensitivity analysis: 4/40 nominal, largest −2.419 ms =
  0.227% of SBS — reported, not suppressed, not inflated; ~41× below the 9.4% floor (computed:
  9.40/0.227 ≈ 41.4).
- The unlabeled task/non-task inconsistency flagged by the adversarial audit is eliminated: one
  primary definition, one labeled secondary sensitivity variant.

## F4 — 2026 prior-art positioning (P0-4) — PASS

Artifact: `PRIOR_ART_POSITIONING.md`. Positions OA-ASSP against van der Blom & Vermetten
(arXiv:2605.04954; feature-budget vs payoff in BBO) and Gholami Shiri et al. (IEEE CEC 2026,
arXiv:2606.18267; graph-instance landscapes for Dijkstra/Bidi/A*) with explicit
shared/different/why-distinct sections, the binding forbidden-claims list (no "first
overhead-aware / feature-cost-aware / structural / ML-selection" claims), the single-sentence
defensible contribution, and RequiredCapture framed as *an interpretable break-even accounting
criterion*.

## Claims & scope hardening

Artifact: `FINAL_CLAIM_AUDIT.md` (term scan + dispositions). Universal wordings replaced with
scope-qualified statements in `corrected_audit_report.md` (executive summary, §7, Q5, Q6) and
`README_CORRECTED.md` (results, verdict). Complementarity handled per the mandate: measurable
instance-level complementarity exists (geometric cells: A* wins ~6–20%, Dijkstra 23–50%), but the
evaluated pipeline does not capture enough of it to offset overhead.

## Regression verification (all run after the fixes)

| Check | Result |
|---|---|
| Unit tests (`pytest tests/ oa_assp/tests/`) | PASS — 79 unique tests / 158 collected cases (the 158 double-counts via 16 re-export stubs in `tests/`) |
| Integrity audit (`verify_corrected_stage20.py`) | 15/15 PASS |
| Adversarial recomputation (`scratch/adversarial_recompute.py`) | PASS + 10 triaged findings (unchanged; F6 is a resolved false positive — see below) |

### F6 — FALSE POSITIVE (resolved 2026-10-04)

The adversarial audit's finding 10 claimed `corrected_audit_report.md` §5 misreports the Q=1 row
as "VBS 1.362 ms and gap 0.012 ms". The checker read the **SBS** column. The report prints
**VBS 1.350** and **gap 0.012**, which are correct roundings of the frozen manifest values
1.35010 ms and 0.01190 ms. **The report is correct; the finding was the error.** No Q=1 result was
changed. The finding is retained in the audit record, explicitly marked as a resolved false
positive, so the record is internally consistent.
| P0 core verification (`scratch/p0_core.py`) | 10/10 PASS |
| Original Stage 20 byte-identical | PASS (integrity check 1) |
| Corrected benchmark untouched | PASS (all headline numbers re-verified from raw: gap 122.5229 ms; RequiredCapture 3.8527 / 0.2898; solver-only −0.1633; e2e Q=500 1191.0 ms) |
| Historical crossover reintroduced? | NO (cell now +36.84 ms; 0 genuine crossovers anywhere) |
| Headline conclusions changed? | NO (only labeling/scoping) |
| New benchmark run? | NO |

## Files created/modified in this pass

Created: `COMMON_QUERY_SBS.md`, `COST_REGIME_DEFINITION.md`, `CROSSOVER_DEFINITION.md`,
`PRIOR_ART_POSITIONING.md`, `FINAL_CLAIM_AUDIT.md`, `P0_FIX_REPORT.md` (this file),
`common_query_sbs.csv`, `p0_regime_reconciliation.csv`, `p0_crossover_unified.csv`,
`p0_noise_floor.csv`, `scratch/p0_core.py`.
Modified (text/scoping only): `corrected_audit_report.md` (regime banner, crossover paragraph,
noise-floor note, scoped claims), `README_CORRECTED.md` (scoped claims), `PRIOR_ART_POSITIONING.md`
(one attribution softening). No code, config, or data files modified.
