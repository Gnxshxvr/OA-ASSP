# Final Claims Audit (pre-freeze)

**Method.** All generated text surfaces (`FINAL_CORRECTED_AUDIT/corrected_audit_report.md`,
`README_CORRECTED.md`, `COMMON_QUERY_SBS.md`, `COST_REGIME_DEFINITION.md`,
`CROSSOVER_DEFINITION.md`, `PRIOR_ART_POSITIONING.md`) were scanned for the mandated term list
(first, novel, state-of-the-art, best, superior, proves/prove, always, never, general, universal,
practical, real-world, plus guarantee, outperform). Every hit was manually triaged into
LEGITIMATE, EDITED, or FLAGGED.

## Dispositions

| File | Line context | Term | Disposition |
|---|---|---|---|
| corrected_audit_report.md | "Historical evidence, never modified" | never | LEGITIMATE (factual: immutability) |
| corrected_audit_report.md | exec summary "Adaptive selection **never beats SBS anywhere**" | never | **EDITED** → "Within the evaluated … no genuine crossover was observed under the primary cost accounting", scope sentence appended |
| corrected_audit_report.md | "Always-Bidirectional-Dijkstra" (5 hits) | always | LEGITIMATE (proper name of the fixed policy) |
| corrected_audit_report.md | §7 "strictly worse than SBS end-to-end" + "negative at every Q" | — | **EDITED** → "worse under this accounting", "negative at every measured Q in this benchmark"; complementarity sentence added |
| corrected_audit_report.md | Q5 "never positive at aggregate level" | never | **EDITED** → "negative at every measured Q in this benchmark" |
| corrected_audit_report.md | Q6 "never crosses 1 in library mode" | never | **EDITED** → "does not cross 1 at any measured Q in library mode" |
| corrected_audit_report.md | §10 "at no measured Q does the value exceed the price" | — | LEGITIMATE (explicitly scoped by "measured") |
| README_CORRECTED.md | "Read this first." | first | LEGITIMATE (idiom) |
| README_CORRECTED.md | "Adaptive never beats SBS" | never | **EDITED** → "0 of 40 … under the primary cost accounting" |
| README_CORRECTED.md | "Verdict: CASE B (adaptive never pays)" | never | **EDITED** → "CASE B, scoped … no genuine crossover … not a claim of universal non-viability" |
| README_CORRECTED.md | "single-best-solver policy" | best | LEGITIMATE (technical term SBS) |
| COMMON_QUERY_SBS.md | "never merged" | never | LEGITIMATE (methodological instruction) |
| COMMON_QUERY_SBS.md | "Always-Bidirectional-Dijkstra" | always | LEGITIMATE (proper name) |
| COST_REGIME_DEFINITION.md | "must simply never be mixed" | never | LEGITIMATE (methodological instruction) |
| CROSSOVER_DEFINITION.md | "best loss / best advantage" | best | LEGITIMATE (extremal statistic over cells) |
| PRIOR_ART_POSITIONING.md | "single best algorithm" (describing their paper) | best | LEGITIMATE (quoting their setting) |
| PRIOR_ART_POSITIONING.md | "asks it first and in depth for BBO" | first | **EDITED** → softened to "is asked explicitly and in depth for BBO by that work" (attribution stays with them; no primacy claim by us) |
| PRIOR_ART_POSITIONING.md | forbidden-claims list ("first overhead-aware…", 4 hits) | first | LEGITIMATE (the list exists to *prohibit* these claims) |

## Binding scope-qualified formulations for the manuscript

- Instead of "adaptive selection never pays": **"Within the evaluated undirected synthetic graph
  families and graph sizes up to V=320, no genuine crossover was observed under the primary cost
  accounting."** (Data-supported: 0/40 cells, all nominal advantages ≥ an order of magnitude
  below the 16.3%/9.4% empirical floors.)
- Instead of "no useful solver complementarity": **"The benchmark contains measurable
  instance-level solver complementarity, particularly within geometric graphs (A* is the
  per-instance winner on ~6–20% of queries in those cells), but the evaluated feature/selector
  pipeline does not capture enough of that complementarity to offset its computational
  overhead."** (Percentages verified from raw winner shares: geometric cells 38–67% Bidi
  majority, 6–20% A*, 23–50% Dijkstra.)
- Instead of "the 40× ratio" as a loose claim: the computed statement **"largest nominal compiled
  advantage 0.227% of SBS vs a 9.4% pass-dispersion floor (ratio ≈ 1/41)"**.
- RequiredCapture is **"an interpretable break-even accounting criterion"**, not a theoretical
  result.
- Any generalization sentence is limited to: graph-level bootstrap covers graph-sampling
  variability within these generators; LOFO over 3 families can only fail to find transfer (it
  does), not establish absence in general.

## Scope-limitations checklist (must appear in the manuscript)

3 synthetic undirected families · V ≤ 320 · 8 held-out test graphs · one frozen split · current
workload design (independent random (s,t) queries, Q ∈ {1,10,50,100,500}) · Python 3.13
implementation and its timing characteristics · 3-solver portfolio · A* eligibility policy
(metadata-driven conservative admissibility, disclosed) · no claim of universal non-viability.
