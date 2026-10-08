# OA-ASSP — FINAL ADVERSARIAL AUDIT (47-part gate)

Auditor stance: hostile IEEE/ACM reviewer + experimental-algorithms reviewer + reproducibility
auditor + novelty researcher + integrity auditor. Date: 2026-09-30. Authoritative experiment:
`stage20_corrected_20260923_092749`. Evidence produced by this audit (all in
`FINAL_CORRECTED_AUDIT/logs/`): `adversarial_recompute.{log,json}` (independent recomputations,
10 findings), `solver_correctness.json` (10/10 independent-reference checks), re-run of the unit
test suite (79 unique tests / 158 collected cases — the 158 double-counts because `tests/`
contains 16 one-line re-export stubs of `oa_assp/tests/`) and 15 integrity checks (pass).
No paper text is produced here.

**Verdict up front: the corrected record is scientifically valid and reproducible; the work is
publishable ONLY AFTER specific scoping/disclosure fixes; novelty is MODERATE; paper readiness is
MAJOR REVISION.** Details below.

---

## 1. Repository forensics (P1)

| Artifact | Classification | Contamination risk |
|---|---|---|
| `results/stage20_corrected_20260923_092749/` | **AUTHORITATIVE** | none — raw 72,000+36,000 rows, processed, manifest with hashes |
| `FINAL_CORRECTED_AUDIT/` (report, manifest, config, questions, checksums, figures, logs incl. this audit) | **AUTHORITATIVE** | none |
| `README_CORRECTED.md`, `README.md` | AUTHORITATIVE (root docs) | none |
| `results/stage20_scaleup_48g_20260920_215427/` | **HISTORICAL (immutable)** | high if cited as evidence — byte-identity verified again this audit (52 files) |
| `results/stage20_corrected_20260922_234910/` | SUPERSEDED (labeled `SUPERSEDED_README.txt`) | high if cited; its generalization table lacks tier attribution |
| `results/raw/`, `results/processed/`, `results/figures/`, `results/tables/`, `results/preflight_stage20a_*` | DEVELOPMENT ONLY (2026-09-20 era) | **HIGH** — contains the superseded `fig07_total_cost_vs_Q_crossover` figure and old final_* runs; must never be cited; recommend moving to `results/_archive_dev/` before any submission |
| `configs/experiment_scaleup_48g.yaml` (original config) | HISTORICAL | none |
| `configs/experiment_corrected_48g.yaml`, `graph_split_manifest_48g.csv` | AUTHORITATIVE | none |
| `scratch/` | DEVELOPMENT ONLY | none (audit scripts live here by design) |
| `oa_assp/`, `tests/`, `scripts/` | AUTHORITATIVE (source of record, source-hashed in manifest) | none |

Contamination verdict: the paper-grade surface (`results/stage20_corrected_20260923_092749` +
`FINAL_CORRECTED_AUDIT/`) is clean; the dev-era `results/*` and `results/figures/fig07` are the
only traps and are outside the frozen checksum set.

## 2. Reproduction (P2) — independent recomputation

Re-ran: **unit tests pass (79 unique tests / 158 collected cases); 15/15 integrity checks pass;
numeric recomputations match frozen tables within tolerance** (full table in `adversarial_recompute.log`; JSON in
`adversarial_recompute.json`). Key reproduced quantities (reported → recomputed):

| Quantity | Reported | Recomputed | PASS |
|---|---:|---:|---|
| raw shape / graphs / split | 72000; 48; 32/8/8 | 72000; 48; 32/8/8 | PASS |
| SBS train total (Bidi) | 3.670822 s | 3.670822 s | PASS |
| Q=500 SBS / VBS / gap | 1064.200 / 941.677 / 122.523 ms | 1064.2002 / 941.6773 / 122.5229 ms | PASS |
| Q∈{1,10,50,100} SBS/VBS/gap | see report §5 | all match (1e-6) | PASS |
| Adaptive task Q=500 lib / comp | 1556.250 / 1119.706 ms | 1556.2499 / 1119.7232 ms | PASS |
| SelectionOverhead lib Q=500 | 472.044 ms | 472.040 ms | PASS |
| RequiredCapture lib / comp | 3.85 / 0.29 | 3.8527 / 0.2898 | PASS |
| CaptureRate lib; solver-only | −4.02; −0.163 | −4.0160; −0.1633 | PASS |
| crossover cells lib / comp | 0/40; 4/40 (−2.419 ms) | 0/40; 4/40 (−2.4190 ms) | PASS |
| compiled pass dispersion | 9.4% | 9.4016% | PASS |
| bootstrap point / CI | 0.492 [0.383, 0.615] | 0.49205 [0.390, 0.614] | PASS |
| historical cell (s138,Q=500) | −0.0371 ms (original) | **+36.84 ms** corrected record | PASS |

## 3. Original vs corrected (P3)

| Property | Original | Corrected | Why changed |
|---|---|---|---|
| A* | heuristic recomputed per relaxation | memoized per (v,target); values bit-identical | audit item #2; no semantic change (verified: same distances, same counters) |
| SBS | totals printed without row-set discipline | train-only + disjointness assertions; totals recomputable from raw | audit #3 |
| Timing | single-shot, no warm-up discipline | warm-up + 5-rep median + IQR everywhere; batched micro-timing | audit #10 |
| Q=1 | amortized batch cost charged | graph features once + one query's costs | audit #8 |
| Selection timing | microbenchmark only | in-loop measured, end-to-end wall clock | audit #9 |
| End-to-end | absent | real adaptive path timed; residual 5.7% median / 8.2% max | audit #9 |
| Tier hyperparameters | historical frozen (depth 4) | validation-selected (gini, depth 6, msl 3), identical across tiers | audit #6/7 |
| Validation | weakly used | HP selection only; test untouched until final | audit #7 |
| Capture analysis | single blended number | task/e2e/analysis-grade + solver-only + compiled variant | audit (new) |
| Crossover | 1 cell at −0.037 ms (Q=500) | 0/40; compiled 4/40 nominal inside 9.4% dispersion | original cell was noise-floor artifact (its magnitude = 0.0066% of SBS; corrected per-row IQR up to 14.4%) |

Pre-specification: all changes were mandated by the audit charter before the rerun; none were
chosen after seeing results. Bias risk: the direction-favoring change (timing honesty) actually
**worsens** adaptive results (×1.024 → ×1.46), i.e., the corrections bias *against* the
attractive outcome — no pro-positive bias detected. The original understated solver costs because
it timed each solver once without warm-up/median discipline (corrected C_SBS ≈ 1.9× original),
which is exactly why its adaptive−SBS gap (13.4 ms) collapsed toward a fake crossover.

## 4–5. Solver correctness & A* fairness (P4, P5)

Independent fresh-written reference (label-correcting loop), 3 families × V∈{40,80} × D∈{6,12} ×
2 seeds × ~12 (s,t) pairs, plus 120-pair bidirectional stress: **10/10 checks pass** — distances
match reference exactly; paths valid and weight-consistent; counters sane; bidirectional meeting
logic exact; euclidean heuristic admissible AND consistent on geometric graphs under the
experiment's weight model (c=1.25, ε=0.1); memoization changes no distance and no expansion
count; zero-heuristic A* ≡ Dijkstra semantics.

Fairness findings (one material disclosure item): A* is excluded from oracle eligibility on
random/scale-free graphs **by metadata flag** (`weight model sets heuristic_admissible=False`),
not by measured inadmissibility — my sampling shows euclidean h(s,t) ≤ d*(s,t) in 30/30 sampled
random pairs (uniform 1–100 weights make it admissible by accident). Impact is nil for the
*results* (A* is never the per-instance winner on random/scale-free — label audit: those cells
contain only Bidi/Dijkstra winners — so VBS, labels and SBS are unchanged by the rule), but the
*stated reason* in any manuscript must be "conservative admissibility policy", not "the heuristic
is inadmissible there". All 16,000 excluded A* rows returned correct distances.

## 6–8. Timing, noise floor, cost model (P6–P8)

Protocol verified in code: warm-up + 5 reps + median + IQR; batch=50 for query features;
`perf_counter`; solver order fixed; adaptive path timed end-to-end with components measured in
the same loop; reconciliation residual (unaccounted/wall) 5.7% median, 8.2% max (library) —
within the documented tolerance; regimes are distinguished (task / e2e / analysis-grade /
microbenchmark) **but see F3 below**. Cost model C_adaptive(Q)=C_graph+ΣC_query+ΣC_sel+ΣC_solver
verified from raw rows; Q=1 physically meaningful (audit check 9). **Empirical noise floor:**
per-row solver-median IQR median 14.4% (p90 57%, max 434%); aggregate pass dispersion 16.3%
(library) / 9.4% (compiled). **Any effect below ~10% of the same aggregate is unclaimable.** The
rejected compiled "wins" (max 0.23% of SBS) sit ~40× below the floor — the rejection is sound.

## 9. Library vs compiled (P9)

LIBRARY measures: real Python/sklearn single-row inference (~88 µs) + feature extraction + solver
dispatch + solver — a *naive deployment* scenario. COMPILED compiles **only the selector** to
nested conditionals (~0.8 µs); features and solvers are identical. They answer the *same*
scientific question (does selection pay for its decision cost?) under **two different price
regimes**, and the answer flips the bottleneck: library → overhead-bound (3.85 > 1), compiled →
efficacy-bound (0.29 < 1 but nothing to capture). They must **never** be merged into one headline
number; the paper must present both columns and name the deployment mode each answer applies to.
Compiled mode is a legitimate deployment abstraction (decision-tree inference is genuinely
compiled in practice), not merely an optimization experiment — but per-query compiled traces are
missing from raw (F2).

## 10–14. SBS / VBS / selector / objective / validation (P10–P14)

- **SBS (P10):** recomputed from training rows only; Bidi is argmin on every fair query set
  (eligible-only, geometric-only 1.609 s vs A* 2.552 s, all-rows 3.671 s vs 7.645 s). **F1:** the
  manifest's printed fixed-policy totals are NOT same-query-set comparable (A* 2.552 s over 5,000
  eligible rows vs Bidi 3.671 s over 16,000). No result depends on it, but the table as printed
  is misleading and must be re-expressed on a common query set.
- **VBS (P11):** recomputed per Q from benchmark medians over eligible solvers; matches exactly.
  Because A* is excluded on 2 families and never wins there, VBS is unaffected (verified).
- **Selector (P12):** test exact accuracy 72.50–73.30% across tiers vs majority 72.60% —
  **statistically indistinguishable from the constant policy**; solver-only capture −0.163
  confirms zero solver-side value. The selector does not beat a trivial policy. Say so.
- **Objective (P13):** classifying the VBS argmin under 0/1 loss is misaligned with minimizing
  runtime — the loss matrix should be cost-sensitive (expected-runtime), as in SATzilla-style
  approaches. This is the **single most defensible methodological upgrade**; it may lift solver
  capture on the genuinely mixed geometric cells (F5), but no new model class is required.
- **Validation (P14):** genuinely used (grid over gini/depth/leaf, selected on validation,
  identical across tiers); no test tuning found (checks + code inspection).

## 15. Features (P15)

Tier 0 (6 O(1)) / Tier 1 (+15, 21 total) / Tier 2 (+2, 23): all measured with the standardized
protocol; identical hyperparameters across tiers; no leakage path found (features derive from
graph structure and (s,t) coordinates only; query distance category is not a feature). Costs:
graph features ~1.0–1.1 µs? — measured 1.05 ms→1051 µs for tier 1 (charged once); query features
~11 µs; selection 88 µs (library) / 0.8 µs (compiled). Tier expansion does not pay (tier 2
compiled required capture 0.42 vs tier 0 0.11) — a legitimate negative finding.

## 16–17. LOCO / LOFO (P16, P17)

Independently verified: cell = (family, V, D) with 2 graphs; 24 folds; held-out cell's graphs
excluded entirely from fold training; hyperparameters frozen (not retuned) per the
identical-HP rule; folds tier-attributed; reported 9/24 constant-prediction folds and 0.00 pp
median lift reproduce from the frozen fold table. **Adversarial finding F5:** the cells are NOT
uniform — random/scale-free cells are 67–97% Bidi (nothing to learn), but geometric cells are
genuinely mixed (majority share 38–67% with 6–20% A* wins). The tree's constant-Bidi collapse in
LOCO is therefore partly a **failure to exploit available structure**, not merely absence of
structure. LOFO over exactly 3 families cannot support any transfer claim; it can only fail to
find one (it does).

## 18–21. Capture framework, conclusion, crossover, statistics (P18–P21)

Formulas verified from raw data with exact denominators (OracleGap = C_SBS − C_VBS on eligible
solvers; CaptureRate = (SBS−Adaptive)/Gap; RequiredCapture = SelectionOverhead/Gap);
RequiredCapture > 1 ⇒ no overhead model can pay (library, all Q≥10); RequiredCapture < 1 is
necessary-but-not-sufficient (compiled) — the framework's two-regime reading is the correct
central device. **P19:** the strongest supported claim is NOT "at V≤320 adaptive selection never
pays" but the scoped statement in §42. **P20:** 0/40 library cells verified; compiled 4/40 uses
the conservative non-task variant while the library search uses the task variant — an unlabeled
inconsistency (F4; under the task variant compiled is 3/40; both are inside the 9.4% dispersion
so no conclusion changes, but one variant must be chosen and labeled). The historical −0.037 ms
cell is absent (that cell is now +36.84 ms). **P21:** graph-level paired bootstrap B=1000 with
seed is sound but n=8 resampling units makes CIs wide and population-scoped; test graphs are
purposive (one per cell) — CIs must be described as covering *graph-sampling* variability within
this generator, not universal generalization.

## 22–25. Prior art, matrix, novelty (P22–P25)

Verified prior art (all real; checked via arXiv/publisher pages):

| Paper | Year | Venue | AlgSel | FeatCost | SelCost | SBS/VBS | Workload Q | Graph feats | RepeatedQ | Break-even | SP | Main difference |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Rice, "The algorithm selection problem" | 1976 | Adv. Computers | yes | – | – | – | – | – | – | – | – | founding formulation; no cost accounting |
| Xu et al., SATzilla | 2008/2012 | JAIR | yes | presolve | partial | – | – | – | – | implicit | – | cost-sensitive DFs; features assumed cheap |
| Bischl et al., ASlib | 2016 | AIJ | yes | – | – | – | – | – | – | – | – | benchmark library; no feature-cost axis |
| Kerschke et al., survey | 2019 | ECJ | yes | noted | – | – | – | – | – | – | – | flags feature cost as open; no SP domain |
| Hoos et al., claspfolio 2 / AutoFolio | 2014/15 | AAAI/arXiv | yes | presolve | partial | – | – | – | – | implicit | – | portfolios for ASP/SAT |
| **van der Blom & Vermetten** (arXiv:2605.04954) | 2026 | arXiv | yes | **yes (budget)** | budget | – | – | – | – | **empirical payoff curve** | – | feature-budget vs payoff in BBO — closest to the *question*; different domain, no Q-amortization axis, no RequiredCapture |
| **Gholami Shiri et al.** (arXiv:2606.18267, IEEE CEC 2026) | 2026 | CEC | partial | low-cost feats | – | landscape regions | – | **yes** | – | – | **yes** | structure-vs-performance landscapes for 4 SP solvers incl. Bidi/A*; *benchmarking*, not selection; no selection overhead, no Q axis, no capture framework |
| This work (OA-ASSP) | 2026 | — | yes | **measured** | **measured in-loop** | **yes** | **yes** | **yes** | **yes** | **RequiredCapture** | **yes** | — |

Novelty components: **N1** overhead-aware selection — pursued in BBO 2026 (MODERATE overlap);
**N2/N3** measured graph/query feature cost in SP selection — no prior art found (STRONG within
domain); **N4** repeated-query amortization axis Q — not in any found prior work (STRONG);
**N5** RequiredCapture criterion — algebraically simple but not present in the literature
(INCREMENTAL-but-useful; verified phrase unclaimed); **N6** break-even formulation — implicit
elsewhere, explicit here (INCREMENTAL); **N7** LOCO/LOFO for graph-config generalization —
standard method, new application (WEAK); **N8** negative/conditional characterization with noise
floor — valuable, rarely published (MODERATE); **N9** SP-specific instantiation — overlaps CEC
2026 landscape work (MODERATE, must cite); **N10** tiered feature-cost analysis — not found
elsewhere (MODERATE). **Verdict: MODERATE.** The *conjunction* (overhead-priced selection +
workload-Q amortization + RequiredCapture + honest negative result, on exact SP) is not in the
literature; each ingredient alone has close neighbors; capture-rate is useful bookkeeping, not a
breakthrough. Reviewer vulnerability: "this is Rice (1976) with a timer on the features."

## 26–28. Plagiarism / attribution (P26–P28)

No manuscript text exists yet; audited README/reports/docstrings: no lifted passages found;
terminology is either standard (SBS/VBS usage should cite benchmarking norms) or original
("overhead-priced decision problem" — 0 search hits; "RequiredCapture" — unclaimed in AS
literature). Attribution requirements for the paper: Rice 1976 (problem), SATzilla/ASlib/LLAMA/
claspfolio/Kerschke (AS frameworks + cost-sensitive selection), Hutter runtime prediction,
BBO feature-budget 2026 paper (the closest question), Gholami Shiri et al. 2026 (SP landscapes —
**mandatory**), Goldberg/Harrelson & Bast et al. (SP algorithms/routing), Dijkstra 1959,
Pohl 1970 (A*), bidirectional search (Nicholson 1966 / Pohl 1971), Efron (bootstrap),
Bischl (split discipline). Risk: LOW, manual Turnitin check still required before submission.

## 29–36. IEEE audit, five reviewers, venues (P29–P36)

**Title (P29):** current title overclaims ("Using Graph Characteristics" implies features that
work). Recommended: *"When Does Adaptive Algorithm Selection Pay for Its Own Overhead? An
Overhead-Priced Study of Exact Shortest-Path Solver Selection"* — accurate, includes the negative
result. **Abstract must contain:** the question, the RequiredCapture criterion, both inference
modes, 0/40 + no-reproduced-crossover, the bottleneck switch, LOCO/LOFO ≈ 0, and the explicit
scope. **Related Work needs:** AS & portfolios; feature-cost/budget; SP algorithms & SP-ML
benchmarking; negative-results methodology.

- **Reviewer #1 (algorithms):** strengths — exactness verified, fairness checks, honest oracle
  construction. Major concerns — portfolio of 3 textbook solvers is thin; undirected only;
  V≤320 small; capture-rate is algebra. Decision: major revision / reject at a top venue.
- **Reviewer #2 (experimental algorithms):** strengths — 15-check audit, recomputable tables,
  noise floor disclosed. Concerns — 8 test graphs; one split; no real networks. Decision: major
  revision; salvageable at a venue valuing benchmarking rigor.
- **Reviewer #3 (ML):** "the selector does not learn; why include ML?" — the honest answer (the
  paper studies *whether* ML selection can pay, and finds the answer no at this scale) must be
  foregrounded; cost-sensitive objective demanded. Decision: weak accept only if framing is
  negative-result-first.
- **Reviewer #4 (systems):** Python timing; 1.5× solver regime gap; compiled per-query traces
  missing; OneDrive/desktop environment. All fixable by disclosure; e2e variant must be shown.
- **Reviewer #5 (novelty):** "Why isn't this known?" — answer: nobody measures the decision's
  price against the available headroom per workload size in exact SP, and the 2026 neighbors
  (feature-budget BBO; SP landscapes) each miss the other half. Convincing only with both cited.

**Venue fit (P35–36):** best scope — **ACM JEA / ACM TOMS (reproducibility track)** or
**SEA/ALNEX-style experimental algorithms** (no invented deadlines; check CFPs); the CEC-2026
precedent shows SP-benchmarking is in scope at IEEE CEC; ambitious option — ACM TOMS regular;
safer — IEEE Access / Applied Sciences-class venues (lower bar, lower prestige). Not in scope:
NeurIPS/ICML (no ML contribution).

## 37. Scorecard (P37)

Problem significance 6/10 (selection overhead is real but SP-specific instantiation is narrow);
Novelty 5/10 (moderate: new conjunction, simple algebra); Technical contribution 5/10 (framework
+ audit harness, no algorithmic contribution); Experimental rigor 7/10 (protocols, checks,
dispersion — genuinely above typical); Statistical rigor 5.5/10 (bootstrap sound but n=8;
multiple regime definitions); Reproducibility 9/10 (hashes, replayable SBS, falsifiable audit);
Practical relevance 4/10 (negative at studied scale, small graphs, synthetic); Clarity 6/10
(good artifacts; report has one transcription error); Literature positioning 3.5/10 (nothing
cited yet — must be built); Overall scientific maturity 6/10. **Do not average: the profile is
"rigorous negative study with thin external positioning" — that profile is publishable at the
right venue only after positioning exists.**

## 38. Top reviewer attacks (P38)

| # | Attack | Severity | Valid? | Fix | Cost |
|---|---|---|---|---|---|
| 1 | "Standard AS with a timer" | high | partly | lead with Q-amortization axis + RequiredCapture; cite BBO-2026 | low |
| 2 | "Capture rate is trivial algebra" | high | partly | present as accounting identity, sell the *measurement discipline* | low |
| 3 | "3 textbook solvers" | high | yes | scope claims; optional 4th solver (DEQ as in CEC'26) | med |
| 4 | "V≤320 too small" | high | yes | scope + optional V=1000 pilot | med |
| 5 | "Synthetic graphs only" | high | yes | add one real road network (P1) | med |
| 6 | "8 test graphs" | med | yes | report per-graph CIs; more seeds optional | low |
| 7 | "Selector ≈ constant policy" | med | yes | that IS the finding — cost-sensitive run to test the ceiling | med |
| 8 | "LOCO/LOFO negative" | med | yes | frame as generalization failure evidence | low |
| 9 | "Python timing" | med | partly | show e2e variant + batched protocol; state floor | low |
| 10 | "Compiled mode artificial" | med | partly | per-query compiled traces; justify as deployment | med |
| 11 | "A* eligibility asymmetry" | med | yes (disclosure) | restate totals on common query set (F1) | low |
| 12 | "Regime mixing" | med | yes (disclosure) | one variant labeled everywhere (F3) | low |
| 13 | "Crossover variant inconsistency 4 vs 3" | low | yes (disclosure) | pick task variant, restate (F4) | low |
| 14 | "No theory" | med | yes | derive RequiredCapture>1 ⇒ no-pay proposition formally (trivial but citable) | low |
| 15 | "Negative result, not novel" | high | partly | negative-results venues/framing + noise-floor discipline | low |
| 16 | "No directed graphs" | med | yes | scope (or directed pilot) | med |
| 17 | "One split" | low | partly | LOCO/LOFO mitigate; state it | low |
| 18 | "Q grid coarse" | low | partly | fine near 1–50 in revision | low |
| 19 | "Feature tiers toy" | low | partly | report tier-cost table (exists) | low |
| 20 | "Report typo Q=1 VBS" | low | **NO — FALSE POSITIVE (resolved)** | F6 was caused by reading the SBS column of the report's Q=1 row. The report prints VBS **1.350** and gap **0.012**, correct roundings of the frozen manifest (1.35010 ms / 0.01190 ms). **No correction was ever needed; no Q=1 result changed.** Retained as an explicitly resolved false positive. | trivial |

## 39–40. Required fixes & experiments (P39–P40)

**P0 (mandatory, no rerun):** F1 same-query-set SBS table; F3 single labeled cost regime;
F4 one crossover variant labeled; full prior-art positioning (both 2026
papers); scoped claims (§42); real-machine spec disclosure. **P1 (strongly recommended):** one
real road network; cost-sensitive selector run (existing framework supports it) to test the
geometric-cell ceiling; per-query compiled traces; archive dev-era results. **P2 (optional):**
directed pilot; V=1000 pilot; extra Q points; DEQ 4th solver. **DO NOT:** add deep models;
retune anything on test; rerun the frozen benchmark; chase a crossover.

More experiments required? Larger graphs: RECOMMENDED (pilot). Real road networks:
RECOMMENDED (P1). Directed: OPTIONAL. ALT/landmarks: OPTIONAL (portfolio widening). Bidirectional
A*: UNNECESSARY. More families: UNNECESSARY (3 suffice for the negative). More test graphs:
OPTIONAL. More Q values: OPTIONAL. More selector models: UNNECESSARY (contradicts scope).
Cost-sensitive learning: RECOMMENDED (P1, tests the objective critique). Ablation:
UNNECESSARY. Additional seeds: OPTIONAL.

## 41–45. Contribution, claims, title, question, structure (P41–P45)

**Strongest defensible contribution:** "A measured, audited characterization of when
overhead-aware per-instance selection of exact shortest-path solvers can and cannot pay,
introducing a workload-Q amortization axis and a RequiredCapture break-even criterion, and
showing — under a noise-floor-disciplined protocol — that with this portfolio the decision is
overhead-bound under library inference and efficacy-bound under compiled inference, with no
reproducible crossover at V≤320 and no generalization to unseen configurations." **Weakest
interpretation:** "a decision tree failed to beat always-bidirectional-Dijkstra on tiny synthetic
graphs" — the paper must be written so this reading cannot stand.

**Claims (P42).** Can definitely make: all §2/§5 numbers; 0/40 primary cells; RequiredCapture
3.85/0.29; solver-only −0.163; LOCO/LOFO ≈ 0; noise floor; historical crossover not reproduced.
With qualification: "never pays" (must be scoped to portfolio, V≤320, undirected, synthetic,
these workload models); "compiled mode is deployment-realistic"; bootstrap CI statements
(graph-sampling scope). Must not make: universal negative for SP selection; "A* heuristic
inadmissible on random graphs" (it is excluded by conservative policy); any sub-percent effect;
any generalization claim from LOFO.

**Title (P43):** see P29; five candidates evaluated; recommended above. **Research question
(P44):** keep Version C ("how much solver-performance headroom must adaptive selection capture
to justify its computational overhead, as a function of workload size?") — it matches the
evidence actually produced and forces the two-regime answer into the open. **Structure (P45):**
as proposed by the charter (Intro → Related → Problem → Overhead-priced framework → Methodology
→ Results → Generalization → Cost/break-even → Discussion → Limitations → Conclusion) with one
change: merge Generalization into Results and add a dedicated "Threats to validity" section.

## 46. GO/NO-GO

```text
OA-ASSP FINAL AUDIT

SCIENTIFIC VALIDITY:            PASS WITH CONDITIONS
IMPLEMENTATION:                 STRONG
REPRODUCIBILITY:                STRONG
STATISTICAL RIGOR:              ACCEPTABLE
NOVELTY:                        MODERATE
PRIOR-ART OVERLAP:              MODERATE
PLAGIARISM/TEXTUAL RISK:        LOW (manual Turnitin check still required)
IEEE FIT:                       MODERATE
PAPER READINESS:                MAJOR REVISION

MAIN CONTRIBUTION:              <see §41 — overhead-priced selection study with Q-amortization
                                 axis, RequiredCapture criterion, and an audited negative result>
MAIN THREAT TO VALIDITY:        <scope: 3 undirected synthetic families, V≤320, 8 test graphs,
                                 Python timing, one split — every quantitative "never pays"
                                 claim dies outside this envelope unless re-scoped>
SINGLE MOST IMPORTANT CHANGE:   <rebuild SBS totals on a common query set and label ONE cost
                                 regime everywhere (F1+F3) — the two disclosure gaps a hostile
                                 reviewer can actually break the story on>
MORE BENCHMARKING REQUIRED:     NO (for submission after P0/P1; pilots optional)
PAPER WRITING MAY BEGIN:        YES, ONLY AFTER P0 FIXES ARE APPLIED TO THE ARTIFACTS
```

## 47. Final independent verdict (P47)

**"If this arrived on my desk today, what would make me reject it?"** Three things, in order:
(1) no related-work section worthy of the name — the two 2026 nearest-neighbors (feature-budget
PIAS in black-box optimization; graph-instance landscapes for exactly Dijkstra/Bidi/A*) are
concurrent, mandatory citations, and a submission that misses them signals cherry-picked
positioning; (2) the printed SBS table comparing sums over different query sets and the unlabeled
mixing of measurement regimes between the library and compiled columns — both are exactly the
kind of accounting inconsistency the paper's whole thesis (honest overhead accounting) claims to
fix, and a hostile reviewer will use that self-contradiction; (3) the negative result delivered
without the noise-floor argument — without it, "0/40" reads as "the ML didn't work" rather than
"nothing above the measurement floor exists to find".

**Smallest scientifically defensible change addressing the strongest rejection reason:** apply
the P0 disclosure set — re-express the three fixed-policy training totals on a single common
query set, print one chosen cost-regime variant in every table (with the others in an appendix),
state the compiled-crossover search under one labeled variant, and cite and differentiate the two
2026 papers in one paragraph ("they establish landscapes / budgets; we measure the price of the
decision against the headroom per workload size"). This requires no new experiments, no rerun of
the frozen benchmark, and directly removes all three rejection grounds above. With that done, the
work is a defensible, honest, moderately novel negative-result methodology paper for an
experimental-algorithms or reproducibility-track venue.
