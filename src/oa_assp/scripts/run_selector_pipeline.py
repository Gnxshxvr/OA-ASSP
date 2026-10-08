"""Complete end-to-end smoke pipeline demonstrating Phases 12–14."""

from __future__ import annotations
from pathlib import Path
import sys

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from oa_assp.benchmark.oracle import compute_oracles, save_oracle_results
from oa_assp.benchmark.runner import build_graph, run_single_query
from oa_assp.graphs.queries import generate_query_workload
from oa_assp.selector.dataset import prepare_selector_dataset
from oa_assp.selector.decision_tree import DecisionTreeSelector
from oa_assp.selector.validation import audit_feature_columns


def run_pipeline() -> None:
    print("OA-ASSP SELECTION PIPELINE (PHASES 12–14)")
    print("=========================================")

    # 1. Generate a small set of diverse graphs (6 graphs)
    configs = [
        ("random", 40, 6.0, 101),
        ("random", 40, 8.0, 102),
        ("geometric", 40, 6.0, 103),
        ("geometric", 40, 8.0, 104),
        ("scale_free", 40, 6.0, 105),
        ("scale_free", 40, 8.0, 106),
    ]

    graphs = {}
    queries_by_graph = {}
    all_benchmark_rows = []

    print("\n1. Generating graphs and reachable queries...")
    for family, V, D, seed in configs:
        g = build_graph(
            family=family,
            num_vertices=V,
            average_degree=D,
            seed=seed,
            weight_model="geometric" if family == "geometric" else "positive_random",
            weight_c=1.25,
            weight_eps=0.1,
        )
        graphs[g.graph_id] = g

        queries = generate_query_workload(g, count=5, global_seed=seed + 1000)
        queries_by_graph[g.graph_id] = queries

        for q in queries:
            rows = run_single_query(
                graph=g,
                query=q,
                experiment_id="pipeline_smoke",
                warmup_runs=1,
                repetitions=3,
                timeout_seconds=5.0,
            )
            all_benchmark_rows.extend(rows)

    print(f"  Graphs generated: {len(graphs)}")
    print(f"  Queries generated: {sum(len(q) for q in queries_by_graph.values())}")
    print(f"  Benchmark rows generated: {len(all_benchmark_rows)}")

    # 2. Compute Oracles (SBS & VBS)
    print("\n2. Computing offline oracles (SBS / VBS)...")
    oracle_summary = compute_oracles(all_benchmark_rows)
    print(f"  Global SBS policy: {oracle_summary.sbs_policy}")
    print(f"  Total SBS cost   : {oracle_summary.sbs_total_cost:.6f}s")
    print(f"  Total VBS cost   : {oracle_summary.vbs_total_cost:.6f}s")
    print(f"  VBS win counts   : {oracle_summary.vbs_win_counts}")

    out_oracle_path = Path("results/processed/oracle_results.csv")
    save_oracle_results(oracle_summary, out_oracle_path)
    print(f"  Saved oracle results to: {out_oracle_path.as_posix()}")

    # 3. Extract Features & Audit for Leakage
    print("\n3. Extracting features and auditing for leakage...")
    split_data = prepare_selector_dataset(
        graphs=graphs,
        queries_by_graph=queries_by_graph,
        oracle_summary=oracle_summary,
        tier=1,
        train_ratio=0.67,  # 4 graphs train, 2 graphs test
        val_ratio=0.0,
        test_ratio=0.33,
        seed=42,
    )

    audit = audit_feature_columns(split_data.all_feature_names)
    print(f"  Leakage audit status: {'PASS' if audit.passed else 'FAIL'}")
    if not audit.passed:
        print(f"  Violations: {audit.violations}")
        sys.exit(1)

    print(f"  Features used ({len(split_data.all_feature_names)}): {split_data.all_feature_names}")
    print(f"  Train graph IDs ({len(split_data.train.graph_ids)}): {split_data.train.graph_ids}")
    print(f"  Test graph IDs  ({len(split_data.test.graph_ids)}): {split_data.test.graph_ids}")

    # 4. Train Decision Tree Selector
    print("\n4. Training Decision Tree Selector on training graphs...")
    selector = DecisionTreeSelector(max_depth=3, min_samples_leaf=2, random_state=42)
    selector.fit(split_data.train)
    print("  Decision tree successfully trained.")

    # 5. Evaluate on Unseen Test Graphs
    print("\n5. Evaluating on completely unseen test graphs...")
    eval_res = selector.evaluate(split_data.test, epsilon=0.05)

    print(f"  Test queries evaluated : {eval_res.num_queries}")
    print(f"  Exact accuracy         : {eval_res.exact_accuracy * 100:.1f}%")
    print(f"  Near-best accuracy     : {eval_res.near_best_accuracy * 100:.1f}% (epsilon=0.05)")
    print(f"  True class distribution: {eval_res.class_distribution}")
    print(f"  Predicted distribution : {eval_res.predicted_distribution}")
    print(f"  Mean selection time    : {eval_res.mean_selection_time * 1e6:.2f} microseconds")
    print(f"  Mean feature time      : {eval_res.mean_feature_time * 1e6:.2f} microseconds")

    print("\nFeature Importances:")
    for fname, imp in sorted(eval_res.feature_importances.items(), key=lambda x: x[1], reverse=True):
        if imp > 0:
            print(f"  {fname:<35}: {imp:.4f}")

    print("\nDecision Tree Structure:")
    print(eval_res.tree_text)
    print("STATUS: PASS (PIPELINE COMPLETE)")


if __name__ == "__main__":
    run_pipeline()
