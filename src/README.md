# OA-ASSP Source Package (`oa_assp`)

The `oa_assp` Python library implements the core shortest-path algorithm portfolio, feature extractors, decision tree training, compiled rule generator, and timing harnesses.

## Submodules

- **`oa_assp.algorithms`**:
  - `dijkstra.py`: Binary-heap priority queue Dijkstra implementation.
  - `bidirectional.py`: Balanced meeting-certificate bidirectional Dijkstra.
  - `astar.py`: Memoized Euclidean heuristic $A^*$ search.
  - `bellman_ford.py`: Bellman-Ford reference solver (offline exactness baseline).
- **`oa_assp.features`**:
  - `structural.py`: Graph-level topological metrics (degrees, weights, geometry ratios, clustering).
  - `linear_scan.py` & `cheap.py`: Fast pre-solver query features ($O(1)$ and $O(\operatorname{deg})$).
- **`oa_assp.selector`**:
  - `tree.py`: Scikit-learn `DecisionTreeClassifier` wrapper with cross-validation.
  - `compiler.py`: Code generator compiling decision tree rules into native nested conditional branches.
- **`oa_assp.benchmark`**:
  - Multi-repetition execution harness (1 warm-up + 5 timed repetitions median) with `time.perf_counter`.
- **`oa_assp.analysis`**:
  - Overhead accounting, break-even metric calculation (`RequiredCapture`, `SolverOnlyCapture`), and noise-qualified crossover detection.
- **`oa_assp.graphs`**:
  - Synthetic graph generators and file loaders.
- **`oa_assp.tests`**:
  - Unit tests covering all algorithms, correctness certificates, features, and accounting logic.
