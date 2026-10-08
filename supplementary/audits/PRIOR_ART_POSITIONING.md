# P0-4 — 2026 Prior-Art Positioning (mandatory citations and claim boundaries)

## 1. van der Blom & Vermetten (2026) — arXiv:2605.04954

**What they study.** "On the Influence of the Feature Computation Budget on Per-Instance
Algorithm Selection for Black-Box Optimization": in per-instance algorithm selection (PIAS) for
black-box optimization (BBO), instance features consume part of the *optimization budget*; the
paper measures how the fraction of budget spent on feature computation affects whether selection
outperforms the single best algorithm, across portfolios, benchmark suites, and dimensionalities,
and identifies payoff curves and the budget fraction that maximizes performance.

**What OA-ASSP shares.** The core economic question — feature computation is not free, and
selection must pay for its own characterization cost out of solver-performance gains — is the
same question. We do **not** claim novelty for feature-cost-aware algorithm selection; that
question is asked explicitly and in depth for BBO by the cited work and the line it belongs to.

**What differs.**
- *Domain and cost model:* they charge features against a **budget inside the optimization
  run** (sampling-based ELA features); we charge **wall-clock time** for graph-level and
  query-level feature extraction plus per-query selection inference, measured end-to-end.
- *Amortization axis:* their setting has no repeated-query workload on a persistent structure;
  OA-ASSP's central independent variable is **workload size Q**, which amortizes the one-time
  graph-level cost across 1…500 queries — an axis their design cannot express.
- *Accounting device:* we decompose viability into headroom (SBS−VBS oracle gap), captured
  fraction (CaptureRate), and a break-even ratio (RequiredCapture = overhead/headroom),
  reported per workload size and per inference mode.
- *Outcome type:* they find selection generally pays given sufficient budget; our exact-SP
  setting yields a disciplined negative result (overhead-bound or efficacy-bound depending on
  inference mode), i.e. the two papers bracket the phenomenon rather than replicate it.

**Why shortest-path workload amortization is a distinct experimental setting.** Exact
shortest-path solvers are *query-repeatable*: the graph is resident and many (s,t) queries hit
the same structure, so a one-time graph-characterization cost has a natural, measurable
amortization curve — a structurally different economics from one-shot black-box optimization
runs, and precisely the regime our RequiredCapture-vs-Q analysis targets.

## 2. Gholami Shiri, Krminac, Djukanović, Džeroski, Tuba, Eftimov (IEEE CEC 2026) — arXiv:2606.18267

**What they study.** "Graph Instance Landscapes: When Structural Similarity Does (Not) Reflect
Shortest-Path Performance": an instance-landscape view of shortest-path benchmarking — graphs are
embedded in a low-cost structural feature space, clustered into landscape regions, and runtime
distributions of four solvers (Dijkstra, bidirectional Dijkstra, A*, DEQ) are compared across
regions over weighted Erdős–Rényi graphs, random geometric graphs, and real road networks.

**What OA-ASSP shares.** The same four-adjacent solver space (our portfolio is a subset: Dijkstra,
bidirectional Dijkstra, A*), the same family of low-cost structural features, the same three
synthetic-family design (Erdős–Rényi/random, geometric), and the same underlying observation that
structure relates to solver performance.

**How OA-ASSP differs — specifically the workload-cost/accounting axis.** Their work is
*benchmarking and landscape analysis*: it asks whether structural similarity predicts performance
similarity, and finds that it often does not. It performs **no algorithm selection, charges no
feature/selection cost, has no workload dimension, and no VBS/headroom accounting**. OA-ASSP
takes the next step they explicitly motivate: given that structure exists, does a selector that
exploits it *pay for the exploiting*? We measure the price of the decision (graph features +
query features + selection, in two inference modes) against the available headroom
(SBS−VBS), per workload size — and find the selector does not capture enough of the existing
complementarity to justify itself at V≤320.

**Claim boundary (binding for the manuscript).** We must **not** claim:
- "first overhead-aware algorithm selection" — no;
- "first feature-cost-aware algorithm selection" — no (see van der Blom & Vermetten 2026 and the
  feature-cost line they represent);
- "first structural analysis of shortest-path algorithms" — no (see Gholami Shiri et al. 2026 and
  the classical SP-engineering literature);
- "first ML selection among Dijkstra / A* / bidirectional Dijkstra" — not defensible; their work
  and prior SP-ML benchmarking already connect structure to these solvers' performance.

## Defensible contribution statement (single sentence)

> An overhead-priced empirical framework for evaluating whether per-instance exact
> shortest-path solver selection can capture enough of the available fixed-policy-to-oracle
> performance headroom to justify graph-level feature extraction, query-level feature
> extraction, and selection overhead across repeated query workloads.

RequiredCapture is described as **an interpretable break-even accounting criterion**, not a
theoretical result. The contribution is the empirical characterization the accounting enables:
available headroom → captured fraction → selection overhead → workload amortization → net
viability, with the negative result (library: overhead-bound; compiled: efficacy-bound) as the
finding.

## Related-work checklist for the manuscript (minimum set)

Rice (1976); SATzilla (Xu et al., JAIR 2012); ASlib (Bischl et al., AIJ 2016); LLAMA
(Kotthoff); claspfolio 2 (Hoos et al. 2014); AutoFolio (Lindauer et al. 2015); Kerschke et al.
survey (ECJ 2019); Hutter et al. runtime prediction (2014); **van der Blom & Vermetten
(arXiv:2605.04954, 2026)**; **Gholami Shiri et al. (IEEE CEC 2026, arXiv:2606.18267)**; Dijkstra
(1959); Hart–Nilsson–Raphael (1968); Nicholson / Pohl (bidirectional search); Goldberg–Harrelson
and Bast et al. (routing algorithms); Efron (bootstrap); one or more recent SP-ML benchmarking
works surfaced in the literature search.
