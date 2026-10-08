# Benchmark Data & Graph Generators

## Graph Corpus Structure

The evaluation corpus consists of 48 synthetic undirected graphs with positive edge weights, generated deterministically across three representative topological families:

1. **Erdős–Rényi (ER) Random Graphs (`random`):**
   - Edge probability $p = D / (V - 1)$
   - Uniform random edge weights: $w(u, v) \sim U[1, 100]$
2. **Random Geometric Graphs (`geometric`):**
   - 2D Euclidean coordinates: $(x, y) \sim U[0, 1]^2$
   - $k$-Nearest Neighbors connectivity targeting average degree $D$
   - Metric edge weights: $w(u, v) = 1.25 \cdot \|u - v\|_2 + 0.1$
3. **Barabási–Albert Scale-Free Graphs (`scalefree`):**
   - Preferential attachment parameter $m = D / 2$
   - Uniform random edge weights: $w(u, v) \sim U[1, 100]$

## Parameter Dimensions

- **Vertex Counts ($V$):** $\{40, 80, 160, 320\}$
- **Target Average Degree ($D$):** $\{6, 12\}$
- **Seeds per Parameter Cell:** 2 independent seeds per cell
- **Total Parameter Combinations:** $3 \text{ families} \times 4\,V \times 2\,D = 24 \text{ cells}$
- **Total Graphs:** $24 \times 2 = 48 \text{ graphs}$

## Data Partitioning & Splits

- **Training Split:** 32 graphs (16,000 queries total)
- **Validation Split:** 8 graphs (4,000 queries total)
- **Held-Out Test Split:** 8 graphs (4,000 queries total at $Q=500$), covering 8 distinct parameter cells (3 geometric, 3 random, 2 scale-free).
- **Split Manifest:** Frozen in `configs/graph_split_manifest_48g.csv`.

## Query Workloads

- 500 deterministic $(s, t)$ shortest-path query pairs per graph (24,000 total queries across all 48 graphs).
- Queries are generated with deterministic per-graph seeds and evaluated at checkpoints $Q \in \{1, 10, 50, 100, 500\}$.
- Raw benchmark execution logs containing 72,000 solver runs (24,000 queries $\times$ 3 candidate algorithms) are stored in `results/stage20_corrected_20260923_092749/raw/`.
