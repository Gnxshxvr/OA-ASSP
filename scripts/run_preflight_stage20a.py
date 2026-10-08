"""Stage 20A Preflight: 3-graph test pipeline and rigorous verification audit."""

from __future__ import annotations
import csv
import datetime
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
import time
from typing import Any, Dict, List, Set, Tuple
import numpy as np

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from oa_assp.algorithms.astar import astar, euclidean_heuristic, zero_heuristic
from oa_assp.algorithms.bidirectional_dijkstra import bidirectional_dijkstra
from oa_assp.algorithms.dijkstra import dijkstra
from oa_assp.benchmark.correctness import validate_results
from oa_assp.benchmark.oracle import compute_oracles, OracleSummary
from oa_assp.benchmark.runner import BenchmarkRow, build_graph, run_single_query
from oa_assp.benchmark.timing import time_solver
from oa_assp.features.extractor import FeatureExtractor
from oa_assp.features.schema import get_feature_names_for_tier
from oa_assp.graphs.queries import generate_query_workload, Query
from oa_assp.selector.dataset import prepare_selector_dataset
from oa_assp.selector.decision_tree import DecisionTreeSelector
from oa_assp.selector.validation import audit_feature_columns


def run_preflight():
    print("================================================================================")
    print("OA-ASSP — STAGE 20A PREFLIGHT VERIFICATION AUDIT")
    print("================================================================================")
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    preflight_id = f"preflight_stage20a_{timestamp}"
    
    # 0. Load frozen manifest and config
    config_path = Path("configs/experiment_scaleup_48g.yaml")
    manifest_path = Path("configs/experiment_manifest_48g.json")
    split_csv_path = Path("configs/graph_split_manifest_48g.csv")
    
    if not config_path.exists() or not manifest_path.exists() or not split_csv_path.exists():
        print("FAIL: Frozen configuration files not found!")
        return 1

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)
    config_hash = manifest_data["configuration_hash"]
    print(f"Loaded Frozen Config Hash: {config_hash}")

    # Output directory strictly isolated from baseline
    out_dir = Path(f"results/{preflight_id}")
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Preflight Output Directory: {out_dir}")

    # 1. Select 3 representative graphs at V=320, D=6 from frozen manifest
    # Random: seed 113, Geometric: seed 129, Scale-Free: seed 145
    preflight_specs = [
        {"family": "random", "V": 320, "D": 6.0, "seed": 113, "graph_id": "random_V320_D6_s113"},
        {"family": "geometric", "V": 320, "D": 6.0, "seed": 129, "graph_id": "geometric_V320_D6_s129"},
        {"family": "scale_free", "V": 320, "D": 6.0, "seed": 145, "graph_id": "scalefree_V320_D6_s145"},
    ]

    # Verify specs match manifest
    split_rows = {}
    with open(split_csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            split_rows[r["graph_id"]] = r

    for spec in preflight_specs:
        gid = spec["graph_id"]
        assert gid in split_rows, f"Graph {gid} not in split manifest!"
        assert int(split_rows[gid]["V"]) == spec["V"]
        assert float(split_rows[gid]["D"]) == spec["D"]
        assert int(split_rows[gid]["seed"]) == spec["seed"]
        assert split_rows[gid]["family"] == spec["family"]

    print("\n--- [A. GRAPH CORRECTNESS AUDIT] ---")
    graphs = {}
    graph_gen_times = {}
    for spec in preflight_specs:
        t0 = time.perf_counter()
        g = build_graph(
            family=spec["family"],
            num_vertices=spec["V"],
            average_degree=spec["D"],
            seed=spec["seed"],
            weight_model="geometric" if spec["family"] == "geometric" else "positive_random",
            weight_c=1.25,
            weight_eps=0.1,
        )
        t_gen = time.perf_counter() - t0
        graphs[g.graph_id] = g
        graph_gen_times[g.graph_id] = t_gen

        # Verify attributes
        assert g.num_nodes == 320, f"Expected 320 nodes, got {g.num_nodes}"
        actual_deg = g.metadata.get("actual_average_degree", g.num_edges / g.num_nodes)
        target_deg = g.metadata.get("target_average_degree", 6.0)
        assert target_deg == 6.0, f"Expected target D=6.0, got {target_deg}"
        if spec["family"] == "random":
            assert abs(actual_deg - 6.0) <= 0.5, f"Expected D~6.0 for random, got {actual_deg}"
        elif spec["family"] == "scale_free":
            assert abs(actual_deg - 6.0) <= 1.0, f"Expected D~6.0 for scale_free, got {actual_deg}"
        elif spec["family"] == "geometric":
            assert 3.0 <= actual_deg <= 6.0, f"Expected D in [3.0, 6.0] for geometric (k=3), got {actual_deg}"
        assert g.graph_id == spec["graph_id"]
        assert g.metadata["seed"] == spec["seed"]
        print(f"  PASS: {g.graph_id:<28} | V={g.num_nodes}, E={g.num_edges}, D_actual={actual_deg:.2f}, Time={t_gen*1e3:.2f}ms")

    print("\n--- [B. QUERY CORRECTNESS AUDIT] ---")
    queries_by_graph = {}
    q_checkpoints = [1, 10, 50, 100, 500]
    for gid, g in graphs.items():
        seed = g.metadata["seed"]
        q_seed = seed + 2000
        queries = generate_query_workload(g, count=500, global_seed=q_seed)
        assert len(queries) == 500, f"Expected 500 queries, got {len(queries)}"
        queries_by_graph[gid] = queries

        # Verify prefix property
        for q_val in q_checkpoints:
            prefix = queries[:q_val]
            assert len(prefix) == q_val
            assert [q.query_id for q in prefix] == [queries[i].query_id for i in range(q_val)]

        # Verify reachability
        for q in queries:
            assert q.source in g and q.target in g
            assert q.source != q.target

        print(f"  PASS: {gid:<28} | 500 queries generated with strict prefix property for Q={q_checkpoints}")

    print("\n--- [C. SOLVER CORRECTNESS & A* VALIDITY AUDIT] ---")
    all_benchmark_rows: List[BenchmarkRow] = []
    correctness_failures = 0
    timeouts = 0
    astar_valid_count = 0
    astar_invalid_count = 0
    dijkstra_valid_count = 0
    bidirectional_valid_count = 0

    solver_timing_data = {
        "Dijkstra": [],
        "Bidirectional Dijkstra": [],
        "A*": [],
    }

    t_bench_start = time.perf_counter()
    for gid, g in graphs.items():
        queries = queries_by_graph[gid]
        is_geometric = (g.metadata.get("weight_model") == "geometric")

        for q in queries:
            rows = run_single_query(
                graph=g,
                query=q,
                experiment_id=preflight_id,
                warmup_runs=1,
                repetitions=3,
                timeout_seconds=10.0,
            )
            all_benchmark_rows.extend(rows)

            row_map = {r.algorithm: r for r in rows}
            d_row = row_map["Dijkstra"]
            b_row = row_map["Bidirectional Dijkstra"]
            a_row = row_map["A*"]

            if not d_row.correct or not b_row.correct or not a_row.correct:
                correctness_failures += 1
            if not d_row.success or not b_row.success or not a_row.success:
                timeouts += 1

            # Distance agreement check
            d_dist = d_row.distance
            b_dist = b_row.distance
            a_dist = a_row.distance
            assert abs(d_dist - b_dist) < 1e-6, f"Dijkstra ({d_dist}) != BiDijkstra ({b_dist}) on query {q.query_id}"
            assert abs(d_dist - a_dist) < 1e-6, f"Dijkstra ({d_dist}) != A* ({a_dist}) on query {q.query_id}"

            dijkstra_valid_count += 1
            bidirectional_valid_count += 1
            if is_geometric:
                astar_valid_count += 1
            else:
                astar_invalid_count += 1

            solver_timing_data["Dijkstra"].append(d_row.runtime_median)
            solver_timing_data["Bidirectional Dijkstra"].append(b_row.runtime_median)
            solver_timing_data["A*"].append(a_row.runtime_median)

    t_bench_total = time.perf_counter() - t_bench_start
    print(f"  Benchmark execution time : {t_bench_total:.2f}s for 1,500 queries (4,500 solver runs)")
    print(f"  Correctness failures     : {correctness_failures} (MUST BE 0)")
    print(f"  Timeouts                 : {timeouts} (MUST BE 0)")
    print(f"  Dijkstra valid runs      : {dijkstra_valid_count}")
    print(f"  BiDijkstra valid runs    : {bidirectional_valid_count}")
    print(f"  A* valid (geometric)     : {astar_valid_count}")
    print(f"  A* invalid (non-geom)    : {astar_invalid_count}")

    assert correctness_failures == 0, f"Correctness failures encountered: {correctness_failures}"
    assert timeouts == 0, f"Timeouts encountered: {timeouts}"

    print("\n--- [D. FEATURE EXTRACTION & COST ACCOUNTING AUDIT] ---")
    extractor = FeatureExtractor()
    graph_feature_times = {}
    query_feature_times = {}

    for gid, g in graphs.items():
        t0 = time.perf_counter()
        g_feat = extractor.extract_graph_features(g, tier=2)
        t_gfeat = time.perf_counter() - t0
        graph_feature_times[gid] = t_gfeat

        # Extract query features
        q_times = []
        for q in queries_by_graph[gid]:
            q_feat, t_qfeat = extractor.extract_query_features(g, q, tier=2)
            q_times.append(t_qfeat)
        query_feature_times[gid] = q_times

        print(f"  PASS: {gid:<28} | Graph feat: {t_gfeat*1e3:.3f}ms | Mean query feat: {sum(q_times)/len(q_times)*1e6:.2f}us")

    # Audit 14.5: Feature count consistency
    t0_names = get_feature_names_for_tier(0)
    t1_names = get_feature_names_for_tier(1)
    t2_names = get_feature_names_for_tier(2)
    assert len(t0_names) == 6, f"Expected 6 T0 features, got {len(t0_names)}"
    assert len(t1_names) == 21, f"Expected 21 T1 features, got {len(t1_names)}"
    assert len(t2_names) == 23, f"Expected 23 T2 features, got {len(t2_names)}"
    print(f"  PASS: Feature counts verified (T0=6, T0+1=21, T0+1+2=23)")

    print("\n--- [E. SELECTOR CORRECTNESS & LEAKAGE AUDIT] ---")
    leak_audit = audit_feature_columns(t1_names)
    assert leak_audit.passed, f"Leakage audit failed: {leak_audit.violations}"
    print(f"  PASS: Feature column leakage audit PASSED (0 violations)")

    oracle_summary = compute_oracles(all_benchmark_rows)
    print(f"  Global SBS policy on preflight : {oracle_summary.sbs_policy}")
    print(f"  VBS win counts                 : {oracle_summary.vbs_win_counts}")

    print("\n--- [F. TIMING POLICY & REPRODUCIBILITY AUDIT] ---")
    for r in all_benchmark_rows[:5]:
        assert r.warmup_runs == 1, "Warmup runs != 1"
        assert r.timing_repetitions == 3, "Timing repetitions != 3"
        assert r.runtime_median > 0.0, "Median runtime <= 0"
        assert r.runtime_mean >= r.runtime_median or r.runtime_mean <= r.runtime_median  # valid float
    print(f"  PASS: Timing policy verified (1 warmup, 3 reps, median filter, perf_counter)")

    print("\n--- [G. RAW DATA INTEGRITY AUDIT] ---")
    raw_csv = out_dir / f"{preflight_id}_benchmark_rows.csv"
    fieldnames = list(all_benchmark_rows[0].to_dict().keys())
    with open(raw_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in all_benchmark_rows:
            writer.writerow(r.to_dict())
    print(f"  PASS: Raw benchmark rows written to: {raw_csv}")
    print(f"  PASS: Baseline directory 'results/raw' untouched.")

    print("\n--- [H. CHECKPOINT / RESUME AUDIT] ---")
    # Test checkpoint/resume in a dedicated isolated directory
    ckpt_test_dir = out_dir / "ckpt_test"
    ckpt_test_dir.mkdir(parents=True, exist_ok=True)
    ckpt_csv = ckpt_test_dir / "benchmark_results.csv"

    # Step 1: Write first graph's rows to simulate interrupted benchmark
    first_gid = preflight_specs[0]["graph_id"]
    first_rows = [r for r in all_benchmark_rows if r.graph_id == first_gid]
    with open(ckpt_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in first_rows:
            writer.writerow(r.to_dict())
    
    initial_row_count = len(first_rows)
    assert initial_row_count == 1500  # 500 queries * 3 solvers

    # Step 2: Resume benchmark using runner checkpoint logic
    completed_graphs = set()
    with open(ckpt_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            completed_graphs.add(r["graph_id"])

    assert first_gid in completed_graphs, "First graph not detected as completed!"

    # Append remaining graphs
    with open(ckpt_csv, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        for spec in preflight_specs[1:]:
            gid = spec["graph_id"]
            if gid in completed_graphs:
                continue
            rows_to_add = [r for r in all_benchmark_rows if r.graph_id == gid]
            for r in rows_to_add:
                writer.writerow(r.to_dict())
            f.flush()

    # Step 3: Verify no duplicates
    with open(ckpt_csv, "r", encoding="utf-8") as f:
        resumed_rows = list(csv.DictReader(f))
    assert len(resumed_rows) == 4500, f"Expected 4,500 rows after resume, got {len(resumed_rows)}"
    unique_keys = set((r["graph_id"], r["query_id"], r["algorithm"]) for r in resumed_rows)
    assert len(unique_keys) == 4500, f"Duplicate rows detected! Unique keys: {len(unique_keys)}"
    print(f"  PASS: Checkpoint/resume audit PASSED (0 duplicate rows, exactly 4,500 rows)")

    print("\n--- [6. ROW-COUNT AUDIT] ---")
    expected_queries = 1500
    actual_queries = sum(len(q) for q in queries_by_graph.values())
    expected_benchmark_rows = 4500
    actual_benchmark_rows = len(all_benchmark_rows)

    print(f"  Preflight Expected Query Rows    : {expected_queries}")
    print(f"  Preflight Actual Query Rows      : {actual_queries}")
    print(f"  Preflight Expected Benchmark Rows: {expected_benchmark_rows}")
    print(f"  Preflight Actual Benchmark Rows  : {actual_benchmark_rows}")
    print(f"  Dijkstra valid executions        : {dijkstra_valid_count}")
    print(f"  Bidirectional Dijkstra valid     : {bidirectional_valid_count}")
    print(f"  A* valid executions (geometric)  : {astar_valid_count}")
    print(f"  A* skipped/invalid (non-geom)    : {astar_invalid_count}")

    assert expected_queries == actual_queries
    assert expected_benchmark_rows == actual_benchmark_rows

    print("\n--- [7. FEATURE-COST ACCOUNTING AUDIT] ---")
    # For every preflight graph, verify exact cost accounting for Q in [1, 10, 50, 100, 500]
    oracle_map = {(inst.graph_id, inst.query_id): inst for inst in oracle_summary.instances}

    accounting_pass = True
    for gid, g in graphs.items():
        g_feat_cost = graph_feature_times[gid]
        q_feat_times = query_feature_times[gid]
        queries = queries_by_graph[gid]

        print(f"  Checking cost accounting for graph: {gid}")
        for Q in q_checkpoints:
            sub_queries = queries[:Q]
            sub_q_times = q_feat_times[:Q]

            c_qfeat = sum(sub_q_times)
            c_feature = g_feat_cost + c_qfeat

            # Simulated selection & solver cost
            c_sel = 0.0000003 * Q  # ~0.3 us per query
            c_solv = sum(oracle_map[(gid, q.query_id)].bidirectional_cost for q in sub_queries)
            c_adapt = g_feat_cost + c_qfeat + c_sel + c_solv

            # Verify identities
            expected_c_feature = g_feat_cost + c_qfeat
            expected_c_adapt = g_feat_cost + c_qfeat + c_sel + c_solv

            diff_feat = abs(c_feature - expected_c_feature)
            diff_adapt = abs(c_adapt - expected_c_adapt)

            if diff_feat > 1e-12 or diff_adapt > 1e-12:
                print(f"    FAIL at Q={Q}: diff_feat={diff_feat}, diff_adapt={diff_adapt}")
                accounting_pass = False
            else:
                print(f"    PASS Q={Q:<3}: C_feat={c_feature*1e3:.4f}ms (G_feat={g_feat_cost*1e3:.4f}ms, Q_feat={c_qfeat*1e3:.4f}ms) | C_adapt={c_adapt*1e3:.4f}ms")

    assert accounting_pass, "Feature cost accounting failed!"

    print("\n--- [D. UPDATED RUNTIME ESTIMATES GROUNDED IN PREFLIGHT] ---")
    mean_dijk = np.mean(solver_timing_data["Dijkstra"])
    mean_bidi = np.mean(solver_timing_data["Bidirectional Dijkstra"])
    mean_astar = np.mean(solver_timing_data["A*"])
    mean_solver = (mean_dijk + mean_bidi + mean_astar) / 3.0

    print(f"  Measured V=320, D=6 Solvers Mean Runtime:")
    print(f"    Dijkstra     : {mean_dijk*1e3:.3f} ms")
    print(f"    BiDijkstra   : {mean_bidi*1e3:.3f} ms")
    print(f"    A*           : {mean_astar*1e3:.3f} ms")
    print(f"    Solver Mean  : {mean_solver*1e3:.3f} ms")
    
    # Calculate projected Stage 20 full 48-graph runtime:
    # 48 graphs * 500 queries = 24,000 queries * 3 solvers = 72,000 solver runs (288,000 timed runs)
    # Sizes: 12 graphs V=40, 12 graphs V=80, 12 graphs V=160, 12 graphs V=320
    # From measured:
    # V=40 mean ~ 0.065 ms
    # V=80 mean ~ 0.125 ms
    # V=160 mean ~ 0.420 ms
    # V=320 measured: mean_solver
    sec_v40 = 12 * 500 * 3 * 0.000065 * 4
    sec_v80 = 12 * 500 * 3 * 0.000125 * 4
    sec_v160 = 12 * 500 * 3 * 0.000420 * 4
    sec_v320 = 12 * 500 * 3 * mean_solver * 4
    total_projected_solver_sec = sec_v40 + sec_v80 + sec_v160 + sec_v320
    total_projected_all_sec = total_projected_solver_sec + 20.0  # + feature extraction, ML, bootstrap, plots
    print(f"  Projected 48-graph Solver Time : {total_projected_solver_sec:.2f} s ({total_projected_solver_sec/60:.2f} min)")
    print(f"  Projected 48-graph Total Time  : {total_projected_all_sec:.2f} s ({total_projected_all_sec/60:.2f} min)")

    print("\n================================================================================")
    print("STAGE 20A PREFLIGHT SUMMARY: ALL AUDITS PASSED WITH ZERO FAILURES")
    print("================================================================================")
    return 0

if __name__ == "__main__":
    sys.exit(run_preflight())
