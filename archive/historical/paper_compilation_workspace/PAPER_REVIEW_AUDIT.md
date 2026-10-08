# Simulated IEEE Review — Final Manuscript (paper/main.tex)

Scope: reviewer-proofing pass over the final submission manuscript, executed against the frozen
experiment `stage20_corrected_20260923_092749`. Every number printed in the manuscript is
re-verified by `scratch/verify_paper_numbers.py` (39/39 checks pass).

## Simulated reviewer concerns and where the manuscript resolves them

| # | Reviewer question | Resolution in the manuscript |
|---|---|---|
| 1 | What is genuinely novel? | The contribution is positioned as the *explicit pricing of selection overhead against SBS–VBS headroom* on repeated-query, microsecond-scale shortest-path workloads, together with the library-versus-compiled deployment comparison (Section I contributions; Section II-B positioning). No "first" claim is made; van der Blom & Vermetten (feature budgets in BBO) and Gholami Shiri et al. (shortest-path landscapes) are cited as the closest work and the difference is stated concretely. |
| 2 | Is the selector failure an artifact of a weak classifier? | The paper does not claim a ceiling for all selectors. It reports that the *evaluated* tree is at parity with the constant policy (72.50% vs 72.60% held-out; +0.00 pp median lift), that the loss is unweighted 0/1, and that no cost-sensitive variant was trained (Section V-F, Section VI-C, Limitation 5). The capacity question is addressed: Tier 2 features move accuracy by 0.52 pp, so the failure is attributed to the objective, not to model capacity. |
| 3 | Feature leakage? | Section IV-D defines the exact feature set and states that every feature is computable before solver dispatch, derived from graph metadata/structure, edge weights, coordinates, and query endpoints. The two graph-level "geometry-to-weight" features are edge-wise ratios, not path quantities; no feature uses ground-truth distances, solver runtimes, expansion counts, or post-solver output. Verified against `oa_assp/features/{cheap,linear_scan,structural}.py`. |
| 4 | Are 8 test graphs enough? | The limitation is stated explicitly and the claims are scoped to it (Section IV-A, Section IV-B, Limitation 8). The test graphs cover 8 of 24 parameter cells and the manuscript says so. Bootstrap intervals are described as graph-sampling variability within the generators, not population generalization. |
| 5 | Are the 40 cells treated as independent samples? | No. Section IV-B states that the graph is the independent unit and the 40 graph–workload cells are evaluation conditions, with uncertainty from a paired graph-level bootstrap over the 8 test graphs. |
| 6 | Why do analysis-grade and end-to-end numbers differ? | Section V-G plus Table VI reconcile the two regimes: different solver-timing modalities by construction (single-shot in-loop vs warm-up + five-repetition medians), decision components agree to ~4%, primary comparative claims restricted to the analysis-grade regime, end-to-end reported as supplementary. |
| 7 | Is the parameter-cell description internally consistent? | The manuscript states 24 (family, V, D) cells and 8 held-out test graphs spanning a subset (3 geometric, 3 random, 2 scale-free). The earlier "one per parameter cell" wording is removed. |
| 8 | Are any claims broader than the evidence? | Claim discipline was applied throughout: "within the evaluated envelope", "no statistically qualified genuine crossover was observed", "reported as nominal rather than wins", "hypotheses motivated by the results rather than validated interventions". The negative result is explicit and not hidden. |
| 9 | Can another researcher reproduce it? | Section VIII names the experiment ID, the deterministic generation and frozen split, the 72,000 solver executions, the 15-check verifier, the SHA-256 manifests (75 source files; 44 audit-evidence files with aggregate digest; 52 historical hashes; one documented pre-closure divergence), and the 79-test suite, plus the reproduction commands. |
| 10 | Is there a meaningful contribution without an end-to-end speedup? | Yes: the overhead-priced accounting framework, the RequiredCapture break-even criterion with the SolverOnlyCapture equivalence, the measured 110× inference reduction moving selection from an unaffordable to an affordable regime, the evidence of solver complementarity, the noise-qualified crossover protocol, and the diagnosis that the residual bottleneck is the training objective. |

## Residual risks (not resolvable within this dataset)

1. Synthetic undirected families only; no road/transit network.
2. V ≤ 320; headroom on large graphs is expected (not shown) to be wider.
3. Three textbook solvers; no preprocessing-based competitors.
4. The cost-sensitive / runtime-regret remedy is argued, not tested.
5. Absolute overhead values are environment-specific (CPython, Windows).
6. Manuscript length is 10 pages including references (9 pages of body + references); if the target venue has a
   hard page limit below that, compression is required before submission.

## Checklist status (final acceptance checklist)

Title accuracy ✓ · abstract content ✓ (288 words) · explicit research gap ✓ · overhead-economics framing ✓ ·
RequiredCapture motivation ✓ · SBS/VBS definitions ✓ · feature-leakage statement ✓ · A* eligibility justified
and scoped ✓ · parameter-cell inconsistency fixed ✓ · 8-test-graph limitation stated ✓ · 40 cells not treated as
independent samples ✓ · bootstrap methodology described ✓ · library vs compiled regimes distinguished ✓ ·
87.9 μs → 0.8 μs and ≈110× stated ✓ · RequiredCapture 3.8527 ✓ · RequiredCapture 0.2898 ✓ · SolverOnlyCapture
−0.1633 ✓ · crossover claim correctly scoped ✓ · regime difference explained, not fabricated ✓ · limitations
honest ✓ · figures regenerated with corrected break-even condition ✓ · tables renumbered and cited in order ✓ ·
conclusion matches evidence ✓ · reproducibility preserved and corrected against the lock manifest ✓.
