"""End-to-end smoke test script for OA-ASSP benchmark infrastructure."""

from __future__ import annotations
import csv
from dataclasses import fields
import datetime
from pathlib import Path
import sys
import time

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from oa_assp.algorithms.bellman_ford import bellman_ford
from oa_assp.benchmark.runner import (
    BenchmarkRow,
    build_graph,
    run_single_query,
)
from oa_assp.graphs.base import Graph
from oa_assp.graphs.queries import generate_query_workload
from oa_assp.graphs.weights import assign_negative_weights


def main() -> int:
    print("OA-ASSP SMOKE TEST")
    print("==================")

    output_dir = Path("results/raw")
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_file = output_dir / "smoke_benchmark_results.csv"

    experiment_id = f"smoke_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # 1. Generate graphs
    graph_configs = [
        ("random", 50, 6.0, 101),
        ("geometric", 50, 6.0, 102),
        ("scale_free", 50, 6.0, 103),
    ]

    graphs_status = {}
    graphs = []

    for family, V, D, seed in graph_configs:
        try:
            g = build_graph(
                family=family,
                num_vertices=V,
                average_degree=D,
                seed=seed,
                weight_model="geometric" if family == "geometric" else "positive_random",
                weight_c=1.25,
                weight_eps=0.1,
            )
            graphs.append(g)
            graphs_status[family] = "PASS"
        except Exception as e:
            graphs_status[family] = f"FAIL ({e})"

    print("\nGraphs:")
    for family, status in graphs_status.items():
        print(f"  {family:<12}: {status}")

    # 2. Generate queries
    total_queries_generated = 0
    total_queries_reachable = 0
    all_queries = []

    for g in graphs:
        queries = generate_query_workload(g, count=5, global_seed=2026)
        total_queries_generated += len(queries)
        total_queries_reachable += len(queries)
        all_queries.append((g, queries))

    print(f"\nQueries:")
    print(f"  generated: {total_queries_generated}")
    print(f"  reachable: {total_queries_reachable}")

    # 3. Execute queries and record rows
    all_rows: list[BenchmarkRow] = []
    algo_status = {
        "Dijkstra": "PASS",
        "A*": "PASS",
        "Bidirectional Dijkstra": "PASS",
    }
    correctness_passed = 0
    correctness_failed = 0

    for g, queries in all_queries:
        for q in queries:
            rows = run_single_query(
                graph=g,
                query=q,
                experiment_id=experiment_id,
                warmup_runs=1,
                repetitions=5,
                timeout_seconds=10.0,
                include_bellman_ford=False,
            )
            all_rows.extend(rows)

            # Check query correctness across algorithms
            query_correct = all(r.correct for r in rows if r.success)
            if query_correct and len(rows) > 0:
                correctness_passed += 1
            else:
                correctness_failed += 1

            for r in rows:
                if not r.success or not r.correct:
                    algo_status[r.algorithm] = "FAIL"

    # Tiny Bellman-Ford negative weight validation
    g_neg = Graph()
    g_neg.add_edge(0, 1, 3.0)
    g_neg.add_edge(0, 2, 4.0)
    g_neg.add_edge(2, 1, -2.0)
    res_bf = bellman_ford(g_neg, 0, 1)
    if res_bf.distance == 2.0 and res_bf.reachable:
        bellman_status = "PASS"
    else:
        bellman_status = "FAIL"

    print("\nAlgorithms:")
    for algo, status in algo_status.items():
        print(f"  {algo:<24}: {status}")
    print(f"  Bellman-Ford (robustness): {bellman_status}")

    print("\nCorrectness:")
    print(f"  passed: {correctness_passed}")
    print(f"  failed: {correctness_failed}")

    # 4. Save results to CSV
    field_names = [f.name for f in fields(BenchmarkRow)]
    with open(csv_file, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=field_names)
        writer.writeheader()
        for r in all_rows:
            writer.writerow(r.to_dict())

    print(f"\nBenchmark rows:")
    print(f"  generated: {len(all_rows)}")

    print(f"\nResults:")
    print(f"  {csv_file.as_posix()}")

    overall_pass = (
        all(s == "PASS" for s in graphs_status.values())
        and all(s == "PASS" for s in algo_status.values())
        and bellman_status == "PASS"
        and correctness_failed == 0
    )

    print(f"\nSTATUS: {'PASS' if overall_pass else 'FAIL'}")
    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
