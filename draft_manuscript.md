> **SUPERSEDED — do not cite or reuse.** This markdown draft predates the final overhead-aware revision. The
> submission manuscript is `paper/main.tex` (compiled: `paper/main.pdf`). Several figures and phrasings in this
> file are stale (e.g., "one per parameter cell" for the test split, an unqualified "heuristic quality
> indicators" feature label, and rounded overhead values such as 472.044 / 1119.706 that the frozen artifacts
> put at 472.040 / 1119.723). The corrected values live in `paper/main.tex`, and every number in that file is
> re-verified by `scratch/verify_paper_numbers.py` against the frozen experiment artifacts.

# OA-ASSP: Overhead-Aware Adaptive Algorithm Selection for Exact Shortest-Path Computation Using Graph Characteristics

**Abstract**—Algorithm selection models typically evaluate candidate solvers under the assumption that instance feature extraction and model inference incur negligible computational cost relative to execution runtime. While defensible in compute-heavy combinatorial optimization (e.g., SAT or integer programming), this premise breaks down in single-pair exact shortest-path queries on small-to-moderate networks, where solver executions finish in hundreds of microseconds. This paper presents an empirical, overhead-priced investigation of adaptive shortest-path algorithm selection across repeated-query workloads. Evaluating an active portfolio consisting of Dijkstra, Bidirectional Dijkstra, and $A^*$ across 48 synthetic graphs (Erdős–Rényi random, random geometric, and Barabási–Albert scale-free graphs with vertex count $V \in \{40, 80, 160, 320\}$ and average degree $D \in \{6, 12\}$) under 500 deterministic queries per graph, we isolate available solver-performance headroom via Single Best Solver (SBS) and Virtual Best Solver (VBS) oracles. We formalize an interpretable break-even criterion, $\mathrm{RequiredCapture}(Q)$, which quantifies the fraction of the SBS–VBS oracle gap a selector must capture to amortize feature and inference overhead over a query workload of size $Q \in \{1, 10, 50, 100, 500\}$. Our measurements uncover a persistent dual bottleneck: (1) under standard machine learning library inference, selection overhead exceeds available oracle headroom across all workloads ($\mathrm{RequiredCapture} = 3.8527 > 1.0$ at $Q=500$), rendering selection strictly overhead-bound; (2) compiling the selector into native conditional branches reduces per-query selection latency from $87.9\,\mu\mathrm{s}$ to $0.8\,\mu\mathrm{s}$, bringing selection overhead within theoretical affordability ($\mathrm{RequiredCapture} = 0.2898 < 1.0$ at $Q=500$), yet the selector captures zero solver-level savings ($\mathrm{SolverOnlyCapture} = -0.1633$, 95% CI $[-0.4735, +0.0856]$), rendering compiled selection efficacy-bound. After qualifying nominal performance deltas against empirical pass-to-pass dispersion (16.32% library, 9.40% compiled), adaptive selection yields exactly 0 out of 40 genuine crossover cells. Although instance-level solver complementarity exists—particularly in geometric networks where $A^*$ achieves per-query runtime minimums on 6%–20% of instances—the unweighted $0/1$ classification loss fails to exploit this structure. These findings delineate the boundary conditions under which machine learning algorithm selection can amortize its own overhead in high-throughput graph processing.

**Index Terms**—Algorithm selection, shortest-path algorithms, performance profiling, empirical algorithmics, overhead accounting, machine learning systems.

---

## 1. Introduction

Exact shortest-path computation is an algorithmic cornerstone of transportation planning, computer networking, robotics, and social network analysis [10], [14]. Across different topological configurations and query geometries, canonical solvers—including Dijkstra's algorithm [10], Bidirectional Dijkstra [12], and the $A^*$ search heuristic [11]—exhibit varied performance profiles. Dijkstra provides uniform frontier expansion; Bidirectional Dijkstra reduces the search space by expanding simultaneous balls from source and target; and $A^*$ directs search toward the target when an admissible, consistent coordinate-based heuristic is accessible.

The principle of per-instance algorithm selection, established by Rice [1], seeks to exploit this algorithmic complementarity by mapping measurable features of a problem instance to the solver minimizing execution latency. In heavy combinatorial optimization tasks—such as propositional satisfiability (SAT) [2], answer set programming (ASP) [5], and mixed integer programming—algorithm selection has yielded substantial performance dividends. In those settings, individual solver runtimes span seconds, minutes, or hours, easily absorbing the milliseconds required for instance feature extraction and model inference.

In high-throughput graph query workloads, however, this cost-benefit symmetry collapses. Exact shortest-path queries on sub-thousand-vertex topologies execute in hundreds of microseconds. When solver runtimes are microsecond-scale, extracting topological graph metrics, computing query-specific features (such as source-target distance or degree interactions), and executing classifier inference impose wall-clock delays that can rival or surpass the cost of computing the shortest path directly. While one-time topological feature extraction can be amortized across a persistent query workload of size $Q$ on a resident graph, per-query feature extraction and selector inference must be paid repeatedly for every query.

Prior studies have characterized performance variations of shortest-path algorithms across graph landscape regions [9] or analyzed feature computation budgets in black-box optimization [8]. However, the literature lacks an empirical, overhead-priced evaluation that measures whether per-instance shortest-path selection can capture enough solver headroom to pay for its own computational cost under physical wall-clock execution.

This paper addresses this gap by formulating and answering the following central research question:

> *Under what graph and query-workload conditions can adaptive exact shortest-path algorithm selection capture enough solver-performance headroom to justify its selection overhead?*

To investigate this question, we present OA-ASSP (Overhead-Aware Adaptive Algorithm Selection for Shortest Paths). Rather than proposing a new shortest-path algorithm or novel neural architecture, this work provides a disciplined experimental study that measures the complete execution pipeline:
$$\text{Graph/query features} \longrightarrow \text{Selector inference} \longrightarrow \text{Selected solver execution}$$
Every microsecond spent characterizing the instance or evaluating the decision tree is explicitly accounted for and debited from the performance headroom separating the Single Best Solver (SBS) from the theoretical Virtual Best Solver (VBS).

### Contributions
1. **Unified Overhead-Priced Cost Model:** We formalize $\mathrm{RequiredCapture}(Q)$ as an interpretable break-even accounting criterion that defines the exact fraction of the empirical SBS–VBS oracle gap a selector must secure to amortize feature extraction and selection latency over workload size $Q$.
2. **Workload Amortization Analysis:** We track the computational economics of algorithm selection across five workload scales ($Q \in \{1, 10, 50, 100, 500\}$) on 48 synthetic graphs spanning three topological families, isolating the amortization curve of one-time graph metrics against recurring per-query feature and inference latencies.
3. **Dual-Bottleneck Empirical Discovery:** We evaluate two distinct inference deployment regimes—general-purpose library inference (`scikit-learn`) and compiled conditional branch execution—revealing a fundamental trade-off: library selection is strictly *overhead-bound* ($\mathrm{RequiredCapture} = 3.8527 > 1.0$), while compiled selection removes the latency bottleneck ($\mathrm{RequiredCapture} = 0.2898 < 1.0$) but exposes the selector as strictly *efficacy-bound* ($\mathrm{SolverOnlyCapture} = -0.1633$).
4. **Noise-Qualified Crossover Protocol:** Applying an empirical measurement-noise floor derived from repeated benchmark dispersion (16.32% library, 9.40% compiled), we evaluate 40 test cells (8 held-out graphs $\times$ 5 workload scales), establishing that adaptive selection yields exactly $0/40$ genuine performance crossovers against SBS.
5. **Generalization Forensics:** Through leave-one-cell-out (LOCO) and leave-one-family-out (LOFO) cross-validation, we show that standard decision trees under $0/1$ classification loss experience constant-policy collapse, failing to convert underlying topological complementarity into runtime savings.

---

## 2. Related Work

### A. Algorithm Selection and Empirical Algorithmics
The foundational framework for algorithm selection was introduced by Rice [1], defining mapping functions from instance feature spaces to algorithm performance metrics. In hard combinatorial domains, systems such as SATzilla [2], [16] demonstrated that machine learning classifiers and runtime predictors can construct effective solver portfolios for SAT. Bischl et al. [3] standardized evaluation protocols through the Algorithm Selection Benchmark Library (ASlib), formalizing definitions of the Single Best Solver (SBS) and Virtual Best Solver (VBS). Subsequent systems, including LLAMA [4], claspfolio 2 [5], and AutoFolio [6], expanded automated algorithm configuration and selection across diverse constraint-satisfaction paradigms. Comprehensive surveys by Kerschke et al. [7] synthesize these methodologies, noting that accounting for feature computation costs remains a vital yet frequently marginalized concern.

### B. Feature-Cost and Budget-Aware Selection
The computational cost of feature computation was addressed directly by van der Blom and Vermetten [8] in the context of per-instance algorithm selection for black-box optimization (BBO). Their work charged exploratory landscape analysis (ELA) features against a fixed total function-evaluation budget, identifying payoff curves and optimal feature budget fractions. OA-ASSP shares this economic foundation—that feature computation is not free and must pay for itself through solver-performance gains. 

However, OA-ASSP differs in three fundamental respects:
1. *Cost Dimension:* Rather than consuming optimization function evaluations inside a solver loop, OA-ASSP accounts for physical wall-clock runtime across feature extraction and model inference.
2. *Workload Structure:* BBO tasks represent single-instance executions without structural persistence. In contrast, shortest-path processing features a resident graph topology serving repeated $(s, t)$ queries, introducing a workload-size parameter $Q$ that amortizes fixed graph-characterization costs over time.
3. *Outcome Characterization:* While BBO selection demonstrates viable payoff curves under sufficient budgets, exact shortest-path selection on moderate graphs yields a dual bottleneck, delineating precise boundary conditions where overhead-priced selection fails.

### C. Shortest-Path Algorithm Engineering and Solver Landscapes
The single-pair shortest-path problem has seen decades of algorithm refinement. Beyond Dijkstra's classic algorithm [10], bidirectional search was established by Nicholson [12] and Pohl [12] to halve search-space radius. Hart, Nilsson, and Raphael [11] formalized $A^*$, directing search via goal-directed heuristics, later expanded to landmark-based ALT algorithms by Goldberg and Harrelson [13] and hierarchical highway/contraction techniques by Bast et al. [14].

Closest to our topological scope is the recent work of Gholami Shiri et al. [9], which mapped graph instance landscapes across weighted Erdős–Rényi, random geometric, and road networks, examining performance distributions of Dijkstra, Bidirectional Dijkstra, $A^*$, and DEQ. While Gholami Shiri et al. establish that structural graph metrics correlate with solver runtime distributions, their contribution is benchmarking and landscape visualization: they do not implement an adaptive algorithm selector, charge no feature extraction or inference overhead, evaluate no workload amortization axis, and conduct no VBS headroom or crossover accounting. OA-ASSP directly investigates the operational viability of the step they motivate: determining whether exploiting observed structural differences via an adaptive selector can physically pay for the cost of selection.

---

## 3. Problem Formulation and Cost Model

### 3.1 Shortest-Path Solver Selection
Let $G = (V, E, w)$ be a weighted undirected graph with vertex set $V$, edge set $E$, and non-negative edge weight function $w: E \to \mathbb{R}^+$. A query $q = (s, t)$ requests an exact minimum-weight path between source $s \in V$ and target $t \in V$. We consider a finite portfolio of exact shortest-path solvers $\mathcal{A} = \{A_1, A_2, \dots, A_m\}$. For each query $q$, solver $A \in \mathcal{A}$ requires physical execution time $t(A; G, q)$ to return the optimal path distance $d^*(s, t)$.

An adaptive algorithm selector $S: \Phi(G, q) \to \mathcal{A}$ evaluates a feature vector $\Phi(G, q)$ and selects solver $A \in \mathcal{A}$.

### 3.2 Single Best Solver (SBS) and Virtual Best Solver (VBS)
To isolate solver-performance headroom independently of selection mechanics, we rely on standard empirical algorithmic baselines [3]:

- **Single Best Solver (SBS):** The fixed solver $A_{\mathrm{SBS}} \in \mathcal{A}$ that minimizes cumulative execution latency over the training distribution $\mathcal{D}_{\mathrm{train}}$:
  $$A_{\mathrm{SBS}} = \arg\min_{A \in \mathcal{A}} \sum_{(G, q) \in \mathcal{D}_{\mathrm{train}}} t(A; G, q)$$
- **Virtual Best Solver (VBS):** A theoretical, zero-overhead per-query oracle that executes the fastest eligible solver for every specific instance:
  $$t(\mathrm{VBS}; G, q) = \min_{A \in \mathcal{A}_{\mathrm{elig}}(G, q)} t(A; G, q)$$
  where $\mathcal{A}_{\mathrm{elig}}(G, q) \subseteq \mathcal{A}$ represents the set of candidate solvers eligible for instance $(G, q)$. VBS represents an unachievable physical lower bound on solver execution time.

### 3.3 Oracle Gap
For a workload of $Q$ queries evaluated on graph $G$, the available performance headroom between the fixed baseline policy and the theoretical oracle is defined as:
$$\mathrm{OracleGap}(Q) = C_{\mathrm{SBS}}(Q) - C_{\mathrm{VBS}}(Q)$$
where $C_{\mathrm{SBS}}(Q) = \sum_{i=1}^Q t(A_{\mathrm{SBS}}; G, q_i)$ and $C_{\mathrm{VBS}}(Q) = \sum_{i=1}^Q t(\mathrm{VBS}; G, q_i)$. The oracle gap represents the theoretical maximum runtime savings any algorithm selector could extract.

### 3.4 Capture Rate
Let $C_{\mathrm{Adaptive}}(Q)$ denote the total execution cost of the adaptive selection pipeline over $Q$ queries. The net savings achieved relative to SBS is:
$$\mathrm{AdaptiveSavings}(Q) = C_{\mathrm{SBS}}(Q) - C_{\mathrm{Adaptive}}(Q)$$
The normalized efficiency of the adaptive selector is given by its **Capture Rate**:
$$\mathrm{CaptureRate}(Q) = \frac{\mathrm{AdaptiveSavings}(Q)}{\mathrm{OracleGap}(Q)} = \frac{C_{\mathrm{SBS}}(Q) - C_{\mathrm{Adaptive}}(Q)}{C_{\mathrm{SBS}}(Q) - C_{\mathrm{VBS}}(Q)}$$
When $\mathrm{CaptureRate} = 1.0$, the selector matches the performance of the theoretical VBS oracle. When $\mathrm{CaptureRate} = 0.0$, the selector achieves parity with the fixed SBS policy. Negative values indicate that adaptive selection performs worse than maintaining the fixed SBS solver.

### 3.5 Required Capture
Total adaptive execution cost decomposes into feature extraction, model inference, and selected solver execution:
$$C_{\mathrm{Adaptive}}(Q) = C_{\mathrm{feat}}^{\mathrm{graph}}(G) + \sum_{i=1}^Q \left[ C_{\mathrm{feat}}^{\mathrm{query}}(G, q_i) + C_{\mathrm{sel}}(q_i) + t(S(\Phi); G, q_i) \right]$$
where $C_{\mathrm{feat}}^{\mathrm{graph}}$ is the one-time cost of extracting topological graph metrics, $C_{\mathrm{feat}}^{\mathrm{query}}$ is per-query feature extraction latency, and $C_{\mathrm{sel}}$ is selector inference latency.

We define total selection overhead as:
$$\mathrm{SelectionOverhead}(Q) = C_{\mathrm{feat}}^{\mathrm{graph}}(G) + \sum_{i=1}^Q \left[ C_{\mathrm{feat}}^{\mathrm{query}}(G, q_i) + C_{\mathrm{sel}}(q_i) \right]$$
To determine whether selection can amortize this overhead, we define **Required Capture**:
$$\mathrm{RequiredCapture}(Q) = \frac{\mathrm{SelectionOverhead}(Q)}{\mathrm{OracleGap}(Q)}$$
$\mathrm{RequiredCapture}(Q)$ is an interpretable break-even accounting criterion:
- If $\mathrm{RequiredCapture}(Q) > 1.0$, selection overhead exceeds the entire available oracle headroom. In this regime, even an omniscient selector with zero solver-level error cannot break even against SBS.
- If $\mathrm{RequiredCapture}(Q) < 1.0$, selection overhead is sufficiently low that an adaptive selector capturing at least this fraction of headroom will achieve a net physical speedup over SBS.

To isolate decision quality from overhead latency, we define **Solver-Only Capture**:
$$\mathrm{SolverOnlyCapture}(Q) = \frac{C_{\mathrm{SBS}}(Q) - C_{\mathrm{chosen\_solver}}(Q)}{\mathrm{OracleGap}(Q)}$$
where $C_{\mathrm{chosen\_solver}}(Q) = \sum_{i=1}^Q t(S(\Phi); G, q_i)$. This metric reflects the hypothetical capture rate achieved by a zero-cost selector.

### 3.6 Cost Regimes
To prevent conflation between physical hardware execution and variance-reduced statistical evaluation, we formally distinguish two cost accounting regimes:

1. **End-to-End Measured Cost (`e2e_measured`):** The physical wall-clock runtime of the adaptive execution path measured in a single uninterrupted execution loop per pass:
   $$C_{\mathrm{Adaptive}}^{\mathrm{e2e}} = \Delta t_{\mathrm{wall}} \left( \text{graph features} + \sum_{i=1}^Q [\text{query features} + \text{inference} + \text{solver} + \text{bookkeeping}] \right)$$
   This reflects physical wall-clock deployment time, where solver execution inherits single-shot execution variability.
2. **Analysis-Grade Normalized Cost (`analysis_grade`):** A standardized, variance-reduced benchmark metric:
   $$C_{\mathrm{Adaptive}}^{\mathrm{analysis}} = \mathrm{SelectionOverhead}_{\mathrm{task}}(Q) + \sum_{i=1}^Q \mathrm{median}_{k=1}^5 \left[ t^{(k)}(S(\Phi); G, q_i) \right]$$
   Here, $\mathrm{SelectionOverhead}_{\mathrm{task}}$ utilizes in-loop measured feature extraction and inference latency (excluding bookkeeping instrumentation), paired with solver execution times standardized across 1 warm-up and 5 repeated benchmark executions. Correspondingly, $C_{\mathrm{SBS}}$ and $C_{\mathrm{VBS}}$ utilize identical benchmark-median solver timings. 

`analysis_grade` is not a physical execution time; it isolates feature and selection overhead from single-shot solver timing noise (where per-row relative IQR reaches 434.5%), providing a stable foundation for headroom accounting. Physical wall-clock validation is strictly evaluated under `e2e_measured`.

```
+-----------------------------------------------------------------------------------+
| FIGURE 1: OA-ASSP Overhead-Priced Shortest-Path Selection Pipeline                |
| Cost Regime: In-loop timing decomposition (analysis_grade and e2e_measured)       |
+-----------------------------------------------------------------------------------+

Resident Graph Topology G = (V, E, w)
  │
  ├─► [ One-Time Graph Feature Extraction: C_graph_feat ] ──► (Amortized over Q)
  │
  ▼
Incoming Query q_i = (s_i, t_i), i ∈ {1, ..., Q}
  │
  ├─► [ Per-Query Feature Extraction: C_query_feat ]
  │         │
  │         ▼
  ├─► [ Vector Assembly & Pre-processing: C_assembly ]
  │         │
  │         ▼
  ├─► [ Selector Inference: C_sel ] ──────────────┐
  │         │                                     │
  │         ▼ (Selected Algorithm A*)             ▼ (Deployment Modes)
  │   ┌───────────────┬────────────────────────┐  │  ├─ Library Mode:
  │   │   Dijkstra    │ Bidirectional Dijkstra │  │  │  scikit-learn (~87.9 µs)
  │   └───────────────┴────────────────────────┘  │  └─ Compiled Mode:
  │                                               │     Native C-tree (~0.8 µs)
  ▼                                               │
Exact Shortest-Path Computation: t(A*; G, q_i)    │
  │                                               │
  ▼                                               │
Total Incurred Cost per Query:                     ▼
  C_query_total = C_query_feat + C_sel + t(A*; G, q_i) + (C_graph_feat / Q)
  Debited against available Headroom: OracleGap(Q) = C_SBS(Q) - C_VBS(Q)
```

---

## 4. Experimental Methodology

### 4.1 Graph Families
We generate 48 synthetic undirected graphs across three topological families:
1. **Erdős–Rényi Random Graphs (`random`):** Edge existence between vertex pairs follows independent probability $p = D / (V - 1)$. Edge weights are drawn uniformly from $[1.0, 100.0]$.
2. **Random Geometric Graphs (`geometric`):** Vertices are assigned coordinates $(x, y) \in [0, 1]^2$ uniformly at random. Edges are constructed using $k$-nearest neighbors to target average degree $D$. Edge weights are defined as $w(u, v) = c \cdot \|u - v\|_2 + \epsilon$, with scaling multiplier $c = 1.25$ and noise offset $\epsilon = 0.1$, guaranteeing metric consistency and positive weights.
3. **Barabási–Albert Scale-Free Graphs (`scale_free`):** Generated via preferential attachment with parameter $m = D / 2$, yielding power-law degree distributions. Edge weights are assigned uniformly from $[1.0, 100.0]$.

For each family, graphs are generated across four vertex scales $V \in \{40, 80, 160, 320\}$ and two average degrees $D \in \{6.0, 12.0\}$, with two distinct random seeds per configuration ($3 \times 4 \times 2 \times 2 = 48$ graphs).

### 4.2 Dataset Split
The 48 graphs are partitioned into strictly disjoint subsets following a frozen manifest:
- **Training Set (32 graphs, 16,000 queries):** Used exclusively for SBS determination, selector training, and feature baseline extraction. Hard assertions enforce $\mathcal{D}_{\mathrm{train}} \cap \mathcal{D}_{\mathrm{val}} = \emptyset$ and $\mathcal{D}_{\mathrm{train}} \cap \mathcal{D}_{\mathrm{test}} = \emptyset$.
- **Validation Set (8 graphs, 4,000 queries):** Reserved solely for hyperparameter tuning.
- **Held-Out Test Set (8 graphs, 4,000 queries):** Evaluated strictly once for final reporting.

### 4.3 Query Workloads
For each graph, 500 deterministic $(s, t)$ query pairs are generated using query seeds derived systematically as $\mathrm{seed}_{\mathrm{query}} = \mathrm{seed}_{\mathrm{graph}} + 2000$. Workloads are evaluated at checkpoints $Q \in \{1, 10, 50, 100, 500\}$.

### 4.4 Solver Portfolio
The active candidate portfolio contains three canonical exact shortest-path algorithms:
1. **Dijkstra's Algorithm:** Standard priority-queue implementation using a min-heap.
2. **Bidirectional Dijkstra:** Balanced simultaneous search from $s$ and $t$, terminating when search frontiers collide and the shortest cross-edge bound is certified.
3. **$A^*$ Search:** Directed search using Euclidean coordinate distance $h(u, t) = \|u - t\|_2$. To guarantee that $A^*$ is timed fairly, heuristic distances are memoized per $(u, t)$ pair, preventing redundant Euclidean norm calculations during edge relaxations.

*Robustness Baseline:* Bellman-Ford was implemented and verified as a correctness baseline; having verified non-negative edge weights across all graphs, it is excluded from the online portfolio.

*$A^*$ Eligibility Disclosure:* On `random` and `scale_free` graphs, coordinate embeddings do not correspond to edge weights. Under a conservative, metadata-driven admissibility policy, $A^*$ is designated ineligible on non-geometric graphs. While post-hoc empirical sampling revealed that random weight assignments frequently satisfied $h(u, t) \le d^*(u, t)$ by numerical coincidence, $A^*$ was restricted to `geometric` graphs to strictly prevent heuristic overestimation. Label auditing confirms that $A^*$ is never the physical runtime winner on random or scale-free instances; hence, this conservative eligibility policy does not distort the VBS oracle.

### 4.5 Feature Tiers
To quantify the trade-off between characterization depth and extraction cost, features are organized into three cumulative tiers:
- **Tier 0 (6 features, $O(1)$ complexity):** Graph-level metrics ($|V|$, $|E|$, average degree $D$, heuristic availability flag) and query-level degrees ($d(s)$, $d(t)$).
- **Tier 1 (21 features, $O(V + E)$ complexity):** Adds graph degree statistics (mean, variance, min, max), edge weight statistics (mean, variance, min, max), negative edge fraction, heuristic quality metrics, and query interaction metrics (source-target Euclidean distance, normalized degree product, degree difference).
- **Tier 2 (23 features, structural complexity):** Adds global clustering coefficient and approximate graph diameter.

### 4.6 Selector Training and Deployment Variants
The selector is instantiated as a `DecisionTreeClassifier` trained under $0/1$ classification loss against per-instance VBS labels. Hyperparameters were tuned on the validation set via grid search across splitting criteria (`gini`), maximum tree depth ($\{2, 3, 4, 5, 6\}$), and minimum leaf samples ($\{1, 2, 3, 5, 10\}$). The selected optimal architecture—frozen across all feature tiers—utilizes the Gini criterion, $\mathrm{max\_depth} = 6$, and $\mathrm{min\_samples\_leaf} = 3$ (resulting in 61 terminal leaves).

We evaluate two operational deployment modes:
1. **Library Mode:** Standard `scikit-learn` single-row inference (`predict`), representing an out-of-the-box ML deployment.
2. **Compiled Mode:** Decision tree branches compiled directly into nested native conditional code (`if-else` blocks), eliminating Python object wrapping and array instantiation overhead.

### 4.7 Timing Protocol and Benchmarking Rigor
Execution timing adheres to strict standardization:
- Hardware: Intel 12th-Gen Core processor (12 execution cores), 64-bit Windows 11 platform, Python 3.13.7 native AMD64 environment.
- Repetitions: 1 initial warm-up execution followed by 5 timed repetitions per query. Runtimes are captured via `time.perf_counter` and summarized using the median and interquartile range (IQR).
- Sub-microsecond Operations: Per-query feature extraction and compiled selection latencies are timed using batched executions ($B = 50$) to ensure resolution above operating system timer granularity.
- End-to-End Tracking: Adaptive execution is timed physically end-to-end over 3 independent passes, logging intermediate durations for component reconciliation.

### 4.8 Statistical and Noise Analysis
To guard against declaring artificial speedups:
- **Bootstrap Dispersion:** Graph-level paired bootstrap resampling ($B = 1000$ replicates, seed 4001) computes 95% confidence intervals over the 8 held-out test graphs.
- **Pass-to-Pass Dispersion:** Adaptive execution is repeated over 3 full passes; aggregate wall-clock dispersion measures 16.32% for library inference and 9.40% for compiled execution.
- **Primary Genuine Crossover Criterion:** A graph $\times$ workload cell $(G, Q)$ is designated a **genuine crossover** if and only if:
  1. $C_{\mathrm{Adaptive}}(Q) < C_{\mathrm{SBS}}(Q)$ under the standardized task accounting; and
  2. The net absolute advantage $|C_{\mathrm{Adaptive}}(Q) - C_{\mathrm{SBS}}(Q)|$ exceeds the empirical noise floor of the evaluated aggregate (16.32% for primary evaluation).
Cells exhibiting nominal speedups smaller than this noise threshold are classified as nominal artifacts.

---

```
TABLE 1: Authoritative Experimental Configuration and Benchmark Envelope
-----------------------------------------------------------------------------------------
Parameter                     Specification / Configuration Value
-----------------------------------------------------------------------------------------
Authoritative Experiment ID   stage20_corrected_20260923_092749
Graph Families (3)            Erdős–Rényi random, random geometric (2D k-NN), Barabási–Albert
Vertex Counts (V)             V ∈ {40, 80, 160, 320}
Average Degree Targets (D)    D ∈ {6.0, 12.0}
Graph Instances Total         48 graphs (3 families × 4 V × 2 D × 2 random seeds)
Dataset Split                 32 training (66.7%), 8 validation (16.7%), 8 test (16.7%)
Query Workload per Graph      500 deterministic (s, t) queries (24,000 queries total)
Evaluated Workloads (Q)       Q ∈ {1, 10, 50, 100, 500}
Active Solver Portfolio       Dijkstra, Bidirectional Dijkstra, A* (heuristic memoized)
Robustness Baseline           Bellman-Ford (offline correctness/exactness verification)
Feature Tiers                 Tier 0 (6 feats, O(1)), Tier 1 (21 feats), Tier 2 (23 feats)
Selector Model                DecisionTreeClassifier (Gini, max_depth=6, min_samples_leaf=3)
Benchmarking Protocol         1 warm-up + 5 repetitions median; batched micro-timing (B=50)
Noise Floors                  16.32% (library pass dispersion), 9.40% (compiled dispersion)
Bootstrap Replicates          B = 1,000 paired graph-level resamples (95% CI)
Platform & Runtime            Intel 12th-Gen (12 cores), Windows 11, Python 3.13.7 x64
-----------------------------------------------------------------------------------------
```

---

## 5. Results

### 5.1 Fixed-Policy Single Best Solver (SBS)
Evaluating cumulative solver runtimes over all 16,000 valid queries in the training set establishes the baseline policy:
- **Bidirectional Dijkstra:** 3.6708 s total runtime ($229.43\,\mu\mathrm{s}/\mathrm{query}$)
- **Dijkstra:** 6.7038 s total runtime ($418.99\,\mu\mathrm{s}/\mathrm{query}$)
- **$A^*$:** 7.6452 s total runtime ($477.83\,\mu\mathrm{s}/\mathrm{query}$)

Bidirectional Dijkstra strictly minimizes training runtime, establishing **Always-Bidirectional-Dijkstra** as the unequivocal Single Best Solver ($A_{\mathrm{SBS}}$). 

To ensure complete fairness regarding $A^*$ eligibility, we also evaluated runtimes restricted to the 5,000 geometric training queries where $A^*$ was fully eligible:
- **Bidirectional Dijkstra:** 1.6092 s total runtime ($321.84\,\mu\mathrm{s}/\mathrm{query}$)
- **Dijkstra:** 1.9206 s total runtime ($384.11\,\mu\mathrm{s}/\mathrm{query}$)
- **$A^*$:** 2.5516 s total runtime ($510.32\,\mu\mathrm{s}/\mathrm{query}$)

Even when evaluated strictly on instances with admissible Euclidean heuristics, Bidirectional Dijkstra outperforms $A^*$ in cumulative training runtime, confirming its identity as SBS across every valid partitioning.

### 5.2 Workload-Amortization Results
Table 2 reports cumulative benchmark runtimes across the 8 held-out test graphs (4,000 total queries) under the primary `analysis_grade` regime.

```
TABLE 2: Primary Workload-Amortization Results across Query Workloads Q
Cost Regime: analysis_grade (Benchmark-median solver runtimes + in-loop measured task overhead)
Aggregate over 8 held-out test graphs (4,000 total queries evaluated)
-------------------------------------------------------------------------------------------------------
Workload   SBS Cost   VBS Cost  OracleGap  Adaptive Cost  Overhead   CaptureRate  RequiredCap  Solver-Only
  (Q)        (ms)       (ms)      (ms)         (ms)         (ms)        (task)       (task)      Capture
-------------------------------------------------------------------------------------------------------
Q = 1        1.362      1.350      0.012       11.452      10.090     -847.89       847.89       0.000
Q = 10      22.775     20.016      2.759       42.184      18.905       -7.04         6.85      -0.188
Q = 50     108.448     94.738     13.710      161.211      51.058       -3.85         3.73      -0.121
Q = 100    223.777    198.342     25.435      328.120     100.196       -4.10         3.94      -0.162
Q = 500   1064.200    941.677    122.523     1556.250     472.044       -4.02         3.85      -0.163
-------------------------------------------------------------------------------------------------------
Note: At Q=500, paired bootstrap 95% CIs are: OracleGap [0.036 s, 0.239 s]; CaptureRate [-11.928, -2.485];
RequiredCapture [2.288, 12.003]; SolverOnlyCapture [-0.4735, +0.0856]; Adaptive/SBS Ratio 1.462 [1.324, 1.734].
```

At $Q = 1$, one-time graph feature extraction ($1051.1\,\mu\mathrm{s}$ for Tier 1) is absorbed entirely by a single query, resulting in an extreme $\mathrm{RequiredCapture}$ of 847.89. As $Q$ increases, graph feature costs amortize over queries. By $Q = 50$, per-query overhead terms ($C_{\mathrm{feat}}^{\mathrm{query}} \approx 11.2\,\mu\mathrm{s}$ and library $C_{\mathrm{sel}} \approx 87.9\,\mu\mathrm{s}$) dominate total overhead, causing $\mathrm{RequiredCapture}$ to stabilize between 3.73 and 3.94. Across all tested workloads in library mode, $\mathrm{CaptureRate}$ remains deeply negative ($-4.02$ at $Q = 500$), indicating that adaptive selection increases total execution cost by 46.2% over SBS.

```
+-----------------------------------------------------------------------------------+
| FIGURE 2: Total Execution Cost vs. Query Workload Q                               |
| Cost Regime: analysis_grade (Log-Log Scale, Aggregate over 8 Test Graphs)         |
+-----------------------------------------------------------------------------------+
 Runtime (ms)
  10^4 +
       |                                                    [Adaptive Library]
  10^3 +                                                   * / 1556.3 ms
       |                                              *  /
       |                                         *   /      [Adaptive Compiled]
  10^2 +                                    *   /  #        # 1119.7 ms
       |                               *   /  #  o          o [SBS] 1064.2 ms
       |                          *   /  #  o               + [VBS] 941.7 ms
  10^1 +                     *   /  #  o  +
       |                *   /  #  o  +
       |           *   /  #  o  +
  10^0 +      *   /  #  o  +
       |  *  /  #  o  +
       +--+-----+-----+-----+-----+------------------------------------------------
         Q=1   Q=10  Q=50 Q=100 Q=500                               Workload Size Q
```

### 5.3 Overhead vs. Oracle Headroom
At the maximum evaluated workload ($Q = 500$), the available headroom between SBS ($1064.200\,\mathrm{ms}$) and the theoretical VBS oracle ($941.677\,\mathrm{ms}$) is:
$$\mathrm{OracleGap}(500) = 122.523\,\mathrm{ms} \quad (11.51\% \text{ of SBS})$$
Against this headroom, library selection incurs $472.044\,\mathrm{ms}$ of overhead ($1.05\,\mathrm{ms}$ graph features $+ 470.99\,\mathrm{ms}$ cumulative query features and inference). Consequently:
$$\mathrm{RequiredCapture}(500) = \frac{472.044}{122.523} = 3.8527 > 1.0$$
Because selection overhead exceeds the entire oracle gap by nearly four-fold, library-based selection is mathematically incapable of achieving break-even, irrespective of selector classification accuracy.

```
+-----------------------------------------------------------------------------------+
| FIGURE 3: CaptureRate vs. RequiredCapture Trajectory                              |
| Cost Regime: analysis_grade across Workload Checkpoints Q ∈ {1, 10, 50, 100, 500} |
+-----------------------------------------------------------------------------------+
  Capture Ratio
   +2.0 +
        |                       THEORETICAL BREAK-EVEN LINE (RequiredCapture = 1.0)
   +1.0 +==========================================================================
        |                                                 [Compiled Mode: ReqCap=0.29]
    0.0 +-------------------------------------------------------x------------------
        |                                                       | (Solver-Only = -0.16)
   -1.0 +                                                       v [Compiled Cap = -0.45]
        |
   -4.0 +-----------------------------------------------------------* [Lib Cap = -4.02]
        |                                                           |
        |                                                           | [Lib ReqCap = 3.85]
 -850.0 +---* [Q=1: Lib Cap = -847.89, ReqCap = 847.89]             v
        +---+-------------------------------------------------------+--------------
           Q=1                                                    Q=500 Workload Q
```

### 5.4 Compiled vs. Library Selection Economics
Table 3 compares the computational economics of library inference against compiled conditional branch execution.

```
TABLE 3: Library vs. Compiled Decision-Tree Selection Economics
Cost Regime: analysis_grade (Except e2e_measured row); Evaluated at Q = 500 across 8 test graphs
---------------------------------------------------------------------------------------------------
Metric / Quantity                  Library Deployment Mode       Compiled Native Deployment Mode
---------------------------------------------------------------------------------------------------
Inference Latency per Query        87.9 µs (median)              0.8 µs (median)
Feature Extraction Overhead        10.1 ms (cumulative)          10.1 ms (cumulative)
Selection Inference Overhead       461.9 ms (cumulative)         25.4 ms (cumulative)
Total Selection Overhead           472.044 ms                    35.530 ms
Adaptive Total Runtime             1556.250 ms                   1119.706 ms
SBS Baseline Runtime               1064.200 ms                   1064.200 ms
Net Difference vs. SBS             +492.050 ms (loss)            +55.506 ms (loss)
RequiredCapture Ratio              3.8527 (overhead-bound)       0.2898 (viable headroom)
Realized CaptureRate               -4.0160                       -0.4530
Solver-Only Capture (zero-cost)    -0.1633                       -0.1633
Physical e2e_measured Runtime      1191.045 ms                   — (analysis-grade model)
Genuine Crossover Cells            0 / 40                        0 / 40
---------------------------------------------------------------------------------------------------
```

Compiling decision tree rules into native conditional logic compresses per-query inference latency by two orders of magnitude (from $87.9\,\mu\mathrm{s}$ to $0.8\,\mu\mathrm{s}$), slashing total selection overhead from $472.044\,\mathrm{ms}$ to $35.530\,\mathrm{ms}$. This drops $\mathrm{RequiredCapture}$ to $0.2898 < 1.0$.

Under compiled inference, selection overhead is no longer the binding constraint: the selector needs to capture only 28.98% of the oracle gap to break even. However, because $\mathrm{SolverOnlyCapture} = -0.1633$, the selector fails to secure positive solver-side savings. The cumulative runtime of the solvers chosen by the selector ($1084.210\,\mathrm{ms}$) exceeds the fixed SBS runtime ($1064.200\,\mathrm{ms}$). Thus, while compiled selection resolves the overhead bottleneck, it directly exposes the selector efficacy bottleneck.

```
+-----------------------------------------------------------------------------------+
| FIGURE 4: The Dual-Bottleneck Empirical Dilemma                                   |
| Cost Regime: analysis_grade Budget Allocation at Q = 500                          |
+-----------------------------------------------------------------------------------+

A. LIBRARY MODE: OVERHEAD-BOUND
┌─────────────────────────┐
│ Oracle Headroom: 122.5ms│
└─────────────────────────┘
┌──────────────────────────────────────────────────────────────────────────┐
│ Incurred Selection Overhead: 472.0 ms (RequiredCapture = 3.85 > 1.0)     │
└──────────────────────────────────────────────────────────────────────────┘
Result: Overhead exceeds entire available headroom. Viability impossible.

B. COMPILED MODE: EFFICACY-BOUND
┌─────────────────────────┐
│ Oracle Headroom: 122.5ms│
└─────────────────────────┘
┌───────────────┐
│ Overhead: 35.5│ (RequiredCapture = 0.29 < 1.0 -> Headroom is accessible)
└───────────────┘
┌───────────────────────────────┐
│ Solver-Only Capture: -16.3 ms │ (Chosen solvers are slower than fixed SBS!)
└───────────────────────────────┘
Result: Overhead is affordable, but selector makes net-negative solver choices.
```

### 5.5 Crossover Analysis and Noise-Floor Disqualification
Across the 40 test cells (8 test graphs $\times$ 5 workload scales), we evaluated whether adaptive selection achieves a net physical runtime advantage ($C_{\mathrm{Adaptive}} < C_{\mathrm{SBS}}$):

```
TABLE 5: Comprehensive Crossover Audit and Noise-Floor Qualification
Cost Regime: analysis_grade (Task-variant accounting, identical across library and compiled)
Evaluated across 40 cells (8 test graphs × 5 Q checkpoints)
-------------------------------------------------------------------------------------------------------
Evaluation Category / Mode      Total Cells   Nominal Cells   Genuine Cells   Extremal Cell Advantage
-------------------------------------------------------------------------------------------------------
Library (Primary Task Variant)      40              0               0         Smallest loss: +0.378 ms
Compiled (Primary Task Variant)     40              3               0         Max adv: -1.486 ms (0.14% SBS)
Compiled (Secondary Conservative)   40              4               0         Max adv: -2.419 ms (0.23% SBS)
-------------------------------------------------------------------------------------------------------
Empirical Noise Floors:
  - Per-row benchmark-median relative IQR (median): 14.39% (p90: 57.47%, max: 434.53%)
  - Library aggregate pass-to-pass dispersion (3 passes): 16.32%
  - Compiled aggregate pass-to-pass dispersion (3 passes): 9.40%
  - Primary applied noise threshold: 16.32%
-------------------------------------------------------------------------------------------------------
```

Under primary task-variant accounting, library selection yields zero cells where adaptive cost is below SBS. Compiled selection yields exactly 3 nominal cells with negative signs:
1. `geometric_V160_D6_s126` at $Q = 500$: $\Delta = -0.353\,\mathrm{ms}$
2. `random_V80_D12_s108` at $Q = 500$: $\Delta = -1.486\,\mathrm{ms}$
3. `scalefree_V160_D12_s144` at $Q = 50$: $\Delta = -0.464\,\mathrm{ms}$

Under a secondary conservative compiled variant (which excludes vector assembly latency), a fourth nominal cell appears (`random_V40_D6_s102` at $Q = 100$, $\Delta = -2.419\,\mathrm{ms}$).

However, evaluating these nominal differences against the empirical noise floor demonstrates their invalidity as scientific wins. The maximum observed nominal advantage across all variants is $-2.419\,\mathrm{ms}$, representing $0.227\%$ of the corresponding SBS cost ($1064.200\,\mathrm{ms}$). This nominal margin is approximately $41\times$ smaller than the measured $9.40\%$ pass-to-pass dispersion of compiled execution, and $72\times$ smaller than the primary $16.32\%$ noise floor. Because all nominal improvements sit an order of magnitude below the physical measurement resolution of the benchmark environment, exactly **0 out of 40** cells represent genuine crossovers.


```
+-----------------------------------------------------------------------------------+
| FIGURE 6: Per-Graph Runtime Delta (Adaptive Task − SBS) at Q = 500                |
| Cost Regime: analysis_grade (Task-Variant, All 8 Held-Out Test Graphs)            |
+-----------------------------------------------------------------------------------+
 Delta (ms) [Positive = Adaptive is Slower than SBS; Negative = Adaptive Wins]
  +120 +
       |        +104.0 ms (geom_V320)
  +100 +           |
       |           |    +69.3 ms  +68.6 ms  +64.2 ms  +63.6 ms
   +60 +           |    (geom160) (scale160)(geom40)  (rand320) +47.9 ms
       |           |       |         |         |         |      (rand80)  +37.7 ms  +36.8 ms
   +20 +           |       |         |         |         |         |      (rand40)  (scale80)
       |           |       |         |         |         |         |         |         |
    0 -+-----------+-------+---------+---------+---------+---------+---------+---------+---
       |                                                            -1.5 ms (rand80 compiled)
       +-------------------------------------------------------------------------------
         Test Graph Instances (Ordered by Overhead Magnitude)
         * All library deltas are positive (adaptive loses on every test graph).
         * Compiled nominal negative deltas (-1.5 ms) sit far below the 9.4% noise floor.
```

### 5.6 Selector Generalization and Topological Complementarity
Table 4 presents cross-validation performance under Leave-One-Cell-Out (LOCO) and Leave-One-Family-Out (LOFO) protocols across feature tiers.

```
TABLE 4: Generalization and Cross-Validation Performance across Topologies
Model: DecisionTreeClassifier (Gini, max_depth=6, min_samples_leaf=3; validation-tuned)
-------------------------------------------------------------------------------------------------------
Evaluation Protocol          Tier   Folds   Median Exact Acc.  Majority Baseline  Median Lift  Constant Folds
-------------------------------------------------------------------------------------------------------
Standard Held-Out Test Split   1       1         72.50%             72.60%         -0.10 pp         0 / 1
Leave-One-Cell-Out (LOCO)      0      24         79.10%             77.95%         +0.00 pp        15 / 24
Leave-One-Cell-Out (LOCO)      1      24         80.80%             77.95%         +0.00 pp         9 / 24
Leave-One-Family-Out (LOFO)    0       3         83.76%             83.45%         +0.06 pp         1 / 3
Leave-One-Family-Out (LOFO)    1       3         79.09%             83.45%         +0.00 pp         1 / 3
-------------------------------------------------------------------------------------------------------
Feature Tier Economics (Q = 500, Analysis-Grade):
  - Tier 0 (6 features):  Test Exact Acc = 72.78%; RequiredCapture = 2.828 (library) / 0.114 (compiled)
  - Tier 1 (21 features): Test Exact Acc = 72.50%; RequiredCapture = 3.853 (library) / 0.290 (compiled)
  - Tier 2 (23 features): Test Exact Acc = 73.30%; RequiredCapture = 4.015 (library) / 0.420 (compiled)
-------------------------------------------------------------------------------------------------------
```

Across all cross-validation folds, median classification accuracy lift over the trivial majority-class baseline is $+0.00$ percentage points. In LOCO evaluations, the decision tree collapses to a constant solver prediction in 15 of 24 folds for Tier 0 and 9 of 24 folds for Tier 1. Under LOFO, accuracy fails to exceed majority voting, demonstrating that structural decision trees trained under $0/1$ loss fail to generalize across graph generators.

Furthermore, expanding feature dimensionality from Tier 0 (6 features) to Tier 2 (23 features) increases classification accuracy by only $0.52\,\mathrm{pp}$ ($72.78\%$ to $73.30\%$), while increasing compiled $\mathrm{RequiredCapture}$ from $0.114$ to $0.420$. Richer structural features incur higher computational costs without delivering actionable predictive power.

```
+-----------------------------------------------------------------------------------+
| FIGURE 5: Selector Accuracy vs. Majority Baseline across Evaluation Protocols     |
| Metric: Exact Classification Accuracy (%) across Held-Out Folds                   |
+-----------------------------------------------------------------------------------+
 Accuracy (%)
  100 +
      |
   80 +---  72.5%   72.6%      80.8%   78.0%      79.1%   83.5%
      |    [     ] [     ]    [     ] [     ]    [     ] [     ]
   60 +    [ Sel ] [ Maj ]    [ Sel ] [ Maj ]    [ Sel ] [ Maj ]
      |    [     ] [     ]    [     ] [     ]    [     ] [     ]
   40 +    [     ] [     ]    [     ] [     ]    [     ] [     ]
      +----+-------+-----+----+-------+-----+----+-------+-----+-------------------
             Standard Test          LOCO Folds          LOFO Folds
          (Lift: -0.10 pp)     (Median Lift: 0.00pp)(Median Lift: 0.00pp)
```

---

## 6. Discussion

### 6.1 Why Selection Is Overhead-Bound Under Library Inference
In library deployment mode, per-query feature extraction and scikit-learn decision-tree inference require approximately $99.1\,\mu\mathrm{s}$ per query ($11.2\,\mu\mathrm{s}$ query features $+ 87.9\,\mu\mathrm{s}$ inference). Over 500 queries, this accumulates to $49.5\,\mathrm{ms}$ of recurring overhead per graph, in addition to one-time graph feature extraction. Concurrently, because Bidirectional Dijkstra dominates the benchmark envelope, the average per-query oracle headroom is only:
$$\frac{\mathrm{OracleGap}(500)}{500 \times 8} = \frac{122.523\,\mathrm{ms}}{4000} \approx 30.6\,\mu\mathrm{s}/\mathrm{query}$$
Because selecting the solver costs $99.1\,\mu\mathrm{s}$ while the maximum attainable performance dividend is $30.6\,\mu\mathrm{s}$, library selection incurs an immediate per-query deficit of $68.5\,\mu\mathrm{s}$. The decision process itself is more expensive than the physical performance variation among solvers.

### 6.2 Why Compiled Selection Becomes Efficacy-Bound
Compiling decision tree branches to native conditionals reduces inference latency to $0.8\,\mu\mathrm{s}$, bringing recurring selection overhead down to $12.0\,\mu\mathrm{s}$ per query ($11.2\,\mu\mathrm{s}$ features $+ 0.8\,\mu\mathrm{s}$ inference). This represents only 39.2% of the $30.6\,\mu\mathrm{s}$ per-query headroom, making selection theoretically viable ($\mathrm{RequiredCapture} = 0.2898$).

However, selection fails in practice because $\mathrm{SolverOnlyCapture} = -0.1633$. Standard decision trees optimize Gini impurity (unweighted $0/1$ classification error), treating all misclassifications identically. In shortest-path selection, misclassifying an instance where Bidirectional Dijkstra and Dijkstra differ by $5\,\mu\mathrm{s}$ is inconsequential, whereas misclassifying an instance where Dijkstra diverges into dense search (incurring a $2000\,\mu\mathrm{s}$ penalty) destroys aggregate savings. By failing to minimize runtime regret, the classifier makes mispredictions whose aggregate runtime penalties exceed the gains of its correct selections.

### 6.3 Solver Complementarity vs. Selector Failure
Crucially, the failure of adaptive selection does not imply that shortest-path solvers lack instance-level complementarity. On random and scale-free graphs, Bidirectional Dijkstra wins 67%–97% of queries, offering minimal exploitable headroom. However, in **random geometric graphs**, genuine solver diversity exists:
- **Bidirectional Dijkstra:** per-query winner on 38%–67% of instances
- **Dijkstra:** per-query winner on 23%–50% of instances
- **$A^*$:** per-query winner on 6%–20% of instances

The selector's collapse to an Always-Bidirectional-Dijkstra policy represents an **exploitation failure of the model and training objective**, not an absence of underlying topological structure.

### 6.4 Implications for Algorithm Selection Systems
These findings highlight two practical imperatives for algorithm selection in high-throughput systems:
1. *Inference Compilation is Mandatory:* In sub-millisecond execution domains, standard machine learning runtimes (e.g., Python, scikit-learn, ONNX) impose prohibitive dispatch overheads. Selection models must be compiled into native, branch-optimized code.
2. *Cost-Sensitive Objectives are Essential:* Classifying the VBS solver under $0/1$ loss is structurally misaligned with runtime minimization. Future shortest-path selectors must employ cost-sensitive loss functions that scale penalties by physical runtime regret.

---

## 7. Threats to Validity and Limitations

To maintain scientific integrity, we explicitly articulate the bounds of this empirical study:
1. **Synthetic Undirected Graph Families:** Benchmark topologies are generated using synthetic models (Erdős–Rényi, random geometric, Barabási–Albert). Runtimes do not capture power-grid dynamics, complex multimodal transportation networks, or real-world road network topologies.
2. **Graph Scale ($V \le 320$):** Evaluations are restricted to vertex counts $V \in \{40, 80, 160, 320\}$. At these scales, the oracle gap is 11.51% of SBS. On massive graphs ($V \ge 10^5$), Dijkstra search spaces expand non-linearly, potentially widening the oracle gap and altering the break-even balance.
3. **Three-Solver Portfolio:** The active portfolio is restricted to textbook Dijkstra, Bidirectional Dijkstra, and $A^*$. Advanced preprocessing techniques (Contraction Hierarchies, Hub Labeling, Transit Node Routing) were not evaluated.
4. **Admissibility Policy:** $A^*$ was excluded from non-geometric graphs by a conservative metadata flag rather than empirical inadmissibility measurements, reflecting standard operational safety.
5. **Loss Formulation:** The selector was trained using unweighted classification loss rather than cost-sensitive runtime regret optimization.
6. **Execution Environment:** Timings reflect Python 3.13 / x64 execution on consumer desktop hardware. While absolute ratios depend on language and runtime, the structural disparity between microsecond execution and model dispatch persists across environments.
7. **Workload Model:** Queries were sampled independently and uniformly at random, excluding query locality, burst traffic, or adversarial routing distributions.
8. **Test Set Scale:** Final evaluation rests on 8 held-out test graphs (one per cell). Paired bootstrap intervals capture graph-sampling variability within this generative envelope, not universal generalization.

---

## 8. Reproducibility

The OA-ASSP experimental repository is completely deterministic, version-controlled, and audited:
- **Authoritative Experiment:** `stage20_corrected_20260923_092749`
- **Data & Code Hashes:** Complete SHA-256 manifests verify that all 72 source files and 52 historical baseline files remain bit-identical (`FINAL_LOCK_MANIFEST.json`).
- **Audit Verification:** The suite passed 15 automated integrity and correctness checks (`verify_corrected_stage20.py`), verifying row shapes (72,000 benchmark executions), runtime positivity, zero timeouts, derived validity flags, and disjoint split enforcement.
- **Execution:** The full experimental pipeline can be reproduced by executing:
  ```bash
  python -u scripts/run_stage20_corrected.py
  python -u scripts/analyze_corrected_stage20.py
  python -u scripts/verify_corrected_stage20.py
  ```

---

## 9. Conclusion

This paper investigated whether adaptive exact shortest-path algorithm selection can amortize its own feature extraction and inference overhead across repeated query workloads. Evaluating 48 graphs, 24,000 queries, and two deployment regimes through an overhead-priced cost model, our findings confirm that within the evaluated experimental envelope ($V \le 320$, synthetic undirected families, 3-solver portfolio), adaptive selection failed to produce genuine task-level speedups over the Single Best Solver (Always-Bidirectional-Dijkstra).

Specifically, our analysis uncovers a dual bottleneck: standard library inference is strictly **overhead-bound**, incurring selection costs that exceed the entire available oracle headroom ($\mathrm{RequiredCapture} = 3.8527 > 1.0$ at $Q = 500$). Compiling decision trees into native conditional branches resolves this latency penalty ($\mathrm{RequiredCapture} = 0.2898 < 1.0$), but the resulting selector is strictly **efficacy-bound**, achieving negative solver-level capture ($\mathrm{SolverOnlyCapture} = -0.1633$) due to unweighted classification loss. After accounting for physical measurement noise, adaptive selection yielded exactly 0 out of 40 genuine crossover cells. 

Because genuine solver complementarity exists in geometric topologies, future research should explore cost-sensitive runtime-regret loss functions and evaluate whether wider oracle headroom on massive, real-world road networks can enable compiled adaptive selection to achieve net physical speedups.

---

## References

[1] J. R. Rice, "The algorithm selection problem," *Advances in Computers*, vol. 15, pp. 65–118, 1976.

[2] L. Xu, F. Hutter, H. H. Hoos, and K. Leyton-Brown, "SATzilla: Portfolio-based algorithm selection for SAT," *Journal of Artificial Intelligence Research*, vol. 32, pp. 565–606, 2008.

[3] B. Bischl, P. Kerschke, L. Kotthoff, M. Lindauer, C. Malitsky, A. Fréchette, H. Hoos, F. Hutter, K. Leyton-Brown, K. Tierney, and J. Vanschoren, "ASlib: A benchmark library for algorithm selection," *Artificial Intelligence*, vol. 237, pp. 41–58, 2016.

[4] L. Kotthoff, "LLAMA: Leveraging learning to automatically manage algorithms," *AI Communications*, vol. 27, no. 2, pp. 175–182, 2014.

[5] M. Gebser, R. Kaminski, B. Kaufmann, T. Schaub, M. Schneider, and S. Ziller, "claspfolio 2: Portfolio-based algorithm selection for answer set programming," *Theory and Practice of Logic Programming*, vol. 14, no. 4-5, pp. 589–603, 2014.

[6] M. Lindauer, H. H. Hoos, F. Hutter, and T. Schaub, "AutoFolio: An automatically configured algorithm selector," *Journal of Artificial Intelligence Research*, vol. 53, pp. 745–778, 2015.

[7] P. Kerschke, H. H. Hoos, F. Neumann, and H. Trautmann, "Automated algorithm selection: Survey and perspectives," *Evolutionary Computation*, vol. 27, no. 1, pp. 3–45, 2019.

[8] K. van der Blom and D. Vermetten, "On the influence of the feature computation budget on per-instance algorithm selection for black-box optimization," *arXiv preprint arXiv:2605.04954*, 2026.

[9] N. Gholami Shiri, V. Krminac, B. Djukanović, S. Džeroski, M. Tuba, and T. Eftimov, "Graph instance landscapes: When structural similarity does (not) reflect shortest-path performance," in *Proc. IEEE Congress on Evolutionary Computation (CEC)*, 2026, arXiv:2606.18267.

[10] E. W. Dijkstra, "A note on two problems in connexion with graphs," *Numerische Mathematik*, vol. 1, no. 1, pp. 269–271, 1959.

[11] P. E. Hart, N. J. Nilsson, and B. Raphael, "A formal basis for the heuristic determination of minimum cost paths," *IEEE Transactions on Systems Science and Cybernetics*, vol. 4, no. 2, pp. 100–107, 1968.

[12] T. A. J. Nicholson, "Finding the shortest route between two points in a network," *The Computer Journal*, vol. 9, no. 3, pp. 275–280, 1966.

[13] A. V. Goldberg and C. Harrelson, "Computing the shortest path: A* search meets graph theory," in *Proc. 16th ACM-SIAM Symposium on Discrete Algorithms (SODA)*, 2005, pp. 156–165.

[14] H. Bast, D. Delling, A. Goldberg, M. Müller-Hannemann, T. Pajor, P. Sanders, D. Wagner, and R. F. Werneck, "Route planning in transportation networks," in *Algorithm Engineering*, ser. LNCS, vol. 9220. Springer, 2016, pp. 19–80.

[15] B. Efron and R. J. Tibshirani, *An Introduction to the Bootstrap*. CRC Press, 1994.

[16] F. Hutter, L. Xu, H. H. Hoos, and K. Leyton-Brown, "Algorithm runtime prediction: Methods & evaluation," *Artificial Intelligence*, vol. 206, pp. 79–111, 2014.