"""Master execution script for Stage 20: Full 48-Graph Experiment."""

from __future__ import annotations
import csv
import datetime
import hashlib
import json
import math
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Set, Tuple
import numpy as np

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from oa_assp.analysis.bootstrap import run_graph_level_bootstrap, save_bootstrap_results
from oa_assp.analysis.feature_tiers import (
    evaluate_feature_tiers,
    save_feature_tier_results,
    save_tier_workload_results,
)
from oa_assp.analysis.plots import generate_all_figures
from oa_assp.analysis.tables import generate_all_tables
from oa_assp.analysis.workload import compute_workload_analysis, save_workload_results
from oa_assp.benchmark.oracle import compute_oracles, save_oracle_results
from oa_assp.benchmark.runner import BenchmarkRow, build_graph, run_single_query
from oa_assp.features.schema import (
    FEATURE_REGISTRY,
    get_feature_manifest,
    get_feature_names_for_tier,
)
from oa_assp.graphs.queries import generate_query_workload
from oa_assp.selector.dataset import prepare_selector_dataset
from oa_assp.selector.decision_tree import DecisionTreeSelector
from oa_assp.selector.validation import audit_feature_columns


def run_stage20():
    print("================================================================================")
    print("OA-ASSP — STAGE 20 FULL 48-GRAPH BENCHMARK EXECUTION")
    print("================================================================================")
    start_total_time = time.perf_counter()

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    experiment_id = f"stage20_scaleup_48g_{timestamp}"

    # 1. Load and verify frozen experiment configuration
    config_path = Path("configs/experiment_scaleup_48g.yaml")
    manifest_path = Path("configs/experiment_manifest_48g.json")
    split_csv_path = Path("configs/graph_split_manifest_48g.csv")

    assert config_path.exists(), f"Configuration file not found: {config_path}"
    assert manifest_path.exists(), f"Manifest file not found: {manifest_path}"
    assert split_csv_path.exists(), f"Split manifest not found: {split_csv_path}"

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    expected_hash = "58590b0bb55428b3674107b937c2e261406bfe3d84f34c3f5bfd7b63c20596ec"
    actual_hash = manifest_data["configuration_hash"]
    assert actual_hash == expected_hash, f"Configuration hash mismatch! Expected {expected_hash}, got {actual_hash}"
    print(f"Verified Configuration Hash: {actual_hash}")

    # Load frozen graph manifest
    frozen_graphs = []
    with open(split_csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            frozen_graphs.append({
                "graph_id": r["graph_id"],
                "family": r["family"],
                "V": int(r["V"]),
                "D": float(r["D"]),
                "seed": int(r["seed"]),
                "split": r["split"],
            })

    assert len(frozen_graphs) == 48, f"Expected 48 graphs, got {len(frozen_graphs)}"
    train_ids = [g["graph_id"] for g in frozen_graphs if g["split"] == "train"]
    val_ids = [g["graph_id"] for g in frozen_graphs if g["split"] == "validation"]
    test_ids = [g["graph_id"] for g in frozen_graphs if g["split"] == "test"]

    assert len(train_ids) == 32, f"Expected 32 train graphs, got {len(train_ids)}"
    assert len(val_ids) == 8, f"Expected 8 validation graphs, got {len(val_ids)}"
    assert len(test_ids) == 8, f"Expected 8 test graphs, got {len(test_ids)}"
    assert len(set(train_ids) & set(val_ids)) == 0
    assert len(set(train_ids) & set(test_ids)) == 0
    assert len(set(val_ids) & set(test_ids)) == 0

    print(f"Graph Splits: 32 Train, 8 Validation, 8 Held-out Test (Mutually Exclusive)")

    # 2. Setup isolated output directories
    exp_dir = Path(f"results/{experiment_id}")
    raw_dir = exp_dir / "raw"
    proc_dir = exp_dir / "processed"
    fig_dir = exp_dir / "figures"
    tbl_dir = exp_dir / "tables"

    for d in [raw_dir, proc_dir, fig_dir, tbl_dir]:
        d.mkdir(parents=True, exist_ok=True)
    print(f"Output Directory: {exp_dir}")

    # 3. Graph generation and benchmarking with checkpointing
    print("\n--- [STEP 1: GRAPH & QUERY BENCHMARK EXECUTION] ---")
    raw_csv_file = raw_dir / f"{experiment_id}_benchmark_rows.csv"
    graph_stats_file = proc_dir / f"{experiment_id}_graph_realized_stats.csv"

    graphs = {}
    queries_by_graph = {}
    all_benchmark_rows: List[BenchmarkRow] = []

    correctness_failures = 0
    timeouts = 0
    dijkstra_valid_count = 0
    bidirectional_valid_count = 0
    astar_valid_count = 0
    astar_invalid_count = 0

    realized_stats = []

    # Open CSV writer with streaming flush
    fieldnames = None

    t_bench_start = time.perf_counter()

    with open(raw_csv_file, "w", newline="", encoding="utf-8") as f_out:
        writer = None

        for idx, g_spec in enumerate(frozen_graphs):
            fam = g_spec["family"]
            V = g_spec["V"]
            D = g_spec["D"]
            seed = g_spec["seed"]
            gid = g_spec["graph_id"]
            split = g_spec["split"]

            # Build graph
            g = build_graph(
                family=fam,
                num_vertices=V,
                average_degree=D,
                seed=seed,
                weight_model="geometric" if fam == "geometric" else "positive_random",
                weight_c=1.25,
                weight_eps=0.1,
            )
            graphs[g.graph_id] = g

            # Record realized stats
            actual_d = g.metadata.get("actual_average_degree", g.num_edges / g.num_nodes)
            realized_stats.append({
                "graph_id": g.graph_id,
                "family": fam,
                "V": g.num_nodes,
                "E": g.num_edges,
                "target_average_degree": D,
                "actual_average_degree": actual_d,
                "seed": seed,
                "split": split,
                "weight_model": g.metadata.get("weight_model"),
            })

            # Generate 500 deterministic reachable queries
            q_seed = seed + 2000
            queries = generate_query_workload(g, count=500, global_seed=q_seed)
            queries_by_graph[g.graph_id] = queries

            # Run solvers for each query
            is_geom = (fam == "geometric")
            for q in queries:
                rows = run_single_query(
                    graph=g,
                    query=q,
                    experiment_id=experiment_id,
                    warmup_runs=1,
                    repetitions=3,
                    timeout_seconds=30.0,
                )
                all_benchmark_rows.extend(rows)

                # Initialize CSV writer on first row
                if writer is None and rows:
                    fieldnames = list(rows[0].to_dict().keys())
                    writer = csv.DictWriter(f_out, fieldnames=fieldnames)
                    writer.writeheader()

                # Write rows and update counters
                for r in rows:
                    writer.writerow(r.to_dict())

                row_map = {r.algorithm: r for r in rows}
                d_row = row_map["Dijkstra"]
                b_row = row_map["Bidirectional Dijkstra"]
                a_row = row_map["A*"]

                if not d_row.correct or not b_row.correct or not a_row.correct:
                    correctness_failures += 1
                if not d_row.success or not b_row.success or not a_row.success:
                    timeouts += 1

                # Verify distance agreement within 1e-6
                assert abs(d_row.distance - b_row.distance) < 1e-6, f"Distance mismatch on query {q.query_id}"
                assert abs(d_row.distance - a_row.distance) < 1e-6, f"Distance mismatch on query {q.query_id}"

                dijkstra_valid_count += 1
                bidirectional_valid_count += 1
                if is_geom:
                    astar_valid_count += 1
                else:
                    astar_invalid_count += 1

            # Checkpoint flush after each completed graph
            f_out.flush()
            print(f"  [{idx+1:02d}/48] Completed {gid:<28} | V={g.num_nodes:<3}, E={g.num_edges:<5}, D_act={actual_d:.2f}, Split={split:<10}")

    t_bench_end = time.perf_counter()
    bench_wall_time = t_bench_end - t_bench_start

    # Save realized stats
    with open(graph_stats_file, "w", newline="", encoding="utf-8") as f:
        stat_writer = csv.DictWriter(f, fieldnames=list(realized_stats[0].keys()))
        stat_writer.writeheader()
        stat_writer.writerows(realized_stats)

    print(f"\nBenchmarking Completed:")
    print(f"  Total Wall-Clock Time      : {bench_wall_time:.2f}s ({bench_wall_time/60:.2f} min)")
    print(f"  Correctness Failures       : {correctness_failures}")
    print(f"  Timeouts                   : {timeouts}")
    print(f"  Dijkstra Valid Runs        : {dijkstra_valid_count}")
    print(f"  BiDijkstra Valid Runs      : {bidirectional_valid_count}")
    print(f"  A* Valid Runs (Geometric)  : {astar_valid_count}")
    print(f"  A* Invalid/Skipped (Non-G) : {astar_invalid_count}")
    print(f"  Total Query Instances      : {len(queries_by_graph) * 500}")
    print(f"  Total Benchmark Rows       : {len(all_benchmark_rows)}")

    assert correctness_failures == 0, f"Encountered {correctness_failures} correctness failures!"
    assert timeouts == 0, f"Encountered {timeouts} timeouts!"
    assert len(all_benchmark_rows) == 72000, f"Expected 72,000 rows, got {len(all_benchmark_rows)}"

    # 4. Compute Oracles (SBS and VBS)
    print("\n--- [STEP 2: SBS AND VBS ORACLES] ---")
    oracle_summary = compute_oracles(all_benchmark_rows)
    save_oracle_results(oracle_summary, proc_dir / f"{experiment_id}_oracle_results.csv")
    print(f"  Global SBS Policy: {oracle_summary.sbs_policy}")
    print(f"  Total SBS Cost   : {oracle_summary.sbs_total_cost*1e3:.2f} ms")
    print(f"  Total VBS Cost   : {oracle_summary.vbs_total_cost*1e3:.2f} ms")
    print(f"  VBS Win Counts   : {oracle_summary.vbs_win_counts}")

    # 5. Feature Extraction & Cost Accounting
    print("\n--- [STEP 3: FEATURE EXTRACTION & DATASET SPLIT] ---")
    split_data = prepare_selector_dataset(
        graphs=graphs,
        queries_by_graph=queries_by_graph,
        oracle_summary=oracle_summary,
        tier=1,
        seed=42,
        stratified=True,
        train_graph_ids=train_ids,
        val_graph_ids=val_ids,
        test_graph_ids=test_ids,
    )
    split_data.assert_no_graph_leakage()
    print(f"  Dataset prepared with Tier 0+1 features (21 features).")
    print(f"  Train: {len(split_data.train.graph_ids)} graphs ({len(split_data.train.y)} queries)")
    print(f"  Val  : {len(split_data.val.graph_ids)} graphs ({len(split_data.val.y)} queries)")
    print(f"  Test : {len(split_data.test.graph_ids)} graphs ({len(split_data.test.y)} queries)")

    # Extract graph feature times for cost accounting
    all_metas = split_data.train.metadata + split_data.val.metadata + split_data.test.metadata
    g_feat_times = {m["graph_id"]: m["graph_feature_time"] for m in all_metas}

    # 6. Selector Training and Evaluation
    print("\n--- [STEP 4: SELECTOR TRAINING & TEST EVALUATION] ---")
    selector = DecisionTreeSelector(max_depth=4, min_samples_leaf=3, random_state=42)
    selector.fit(split_data.train)

    selector_eval = selector.evaluate(split_data.test, epsilon=0.05)
    print(f"  Held-out Test Queries : {selector_eval.num_queries}")
    print(f"  Exact Winner Accuracy : {selector_eval.exact_accuracy*100:.2f}%")
    print(f"  Near-Best Accuracy    : {selector_eval.near_best_accuracy*100:.2f}% (epsilon=0.05)")
    print(f"  Mean Selection Time   : {selector_eval.mean_selection_time*1e6:.2f} us")
    print(f"  Mean Feature Time     : {selector_eval.mean_feature_time*1e6:.2f} us")

    # Export Decision Tree
    tree_nodes = selector.export_tree_nodes()
    with open(proc_dir / f"{experiment_id}_decision_tree_nodes.json", "w", encoding="utf-8") as f:
        json.dump(tree_nodes, f, indent=2)
    with open(proc_dir / f"{experiment_id}_decision_tree_structure.txt", "w", encoding="utf-8") as f:
        f.write(selector_eval.tree_text)

    # 7. Query Workload Analysis (Phase 15)
    print("\n--- [STEP 5: QUERY WORKLOAD ANALYSIS (PHASE 15)] ---")
    q_checkpoints = [1, 10, 50, 100, 500]
    workload_res = compute_workload_analysis(
        query_results=selector_eval.query_results,
        oracle_summary=oracle_summary,
        graph_feature_times=g_feat_times,
        q_checkpoints=q_checkpoints,
    )
    save_workload_results(workload_res, proc_dir / f"{experiment_id}_workload_curves.csv")
    print(f"  Aggregate Break-Even Q: {workload_res.aggregate_break_even_Q if workload_res.aggregate_break_even_Q else 'not_observed'}")
    for q, p in sorted(workload_res.aggregate_points.items()):
        gap_str = f"{p['gap_closed']:.4f}" if not np.isnan(p["gap_closed"]) else "N/A"
        print(f"    Q={q:<3}: SBS={p['total_SBS']*1e3:.3f}ms, Adaptive={p['total_Adaptive']*1e3:.3f}ms, VBS={p['total_VBS']*1e3:.3f}ms, GapClosed={gap_str}")

    # 8. Feature-Tier Trade-offs (Phase 16)
    print("\n--- [STEP 6: FEATURE-TIER TRADE-OFFS (PHASE 16)] ---")
    tier_summaries, tier_workloads = evaluate_feature_tiers(
        graphs=graphs,
        queries_by_graph=queries_by_graph,
        oracle_summary=oracle_summary,
        seed=42,
        q_checkpoints=q_checkpoints,
        split_data_tier1=split_data,
        eval_res_tier1=selector_eval,
        train_graph_ids=train_ids,
        val_graph_ids=val_ids,
        test_graph_ids=test_ids,
    )
    save_feature_tier_results(tier_summaries, proc_dir / f"{experiment_id}_feature_tier_tradeoffs.csv")
    save_tier_workload_results(tier_workloads, proc_dir / f"{experiment_id}_tier_workload_results.csv")
    for s in tier_summaries:
        gap_str = f"{s.gap_closed:.4f}" if not np.isnan(s.gap_closed) else "N/A"
        print(f"    {s.tier_name:<25}: Acc={s.exact_accuracy*100:.1f}%, NearAcc={s.near_best_accuracy*100:.1f}%, GapClosed={gap_str}")

    # 9. Graph-Level Bootstrap (Phase 17)
    print("\n--- [STEP 7: GRAPH-LEVEL BOOTSTRAP (PHASE 17)] ---")
    boot_res = run_graph_level_bootstrap(
        query_results=selector_eval.query_results,
        oracle_summary=oracle_summary,
        test_split=split_data.test,
        num_replicates=1000,
        confidence_level=0.95,
        seed=4001,
    )
    save_bootstrap_results(boot_res, proc_dir / f"{experiment_id}_bootstrap_results.csv")
    print(f"  Independent Test Graphs: {len(split_data.test.graph_ids)}")
    print(f"  GapClosed Point Estimate: {boot_res.gap_closed_ci.point_estimate:.4f}")
    print(f"  GapClosed 95% CI        : [{boot_res.gap_closed_ci.ci_lower:.4f}, {boot_res.gap_closed_ci.ci_upper:.4f}]")
    print(f"  Adaptive - SBS Point    : {boot_res.adaptive_minus_sbs_ci.point_estimate*1e3:.3f} ms")
    print(f"  Adaptive - SBS 95% CI   : [{boot_res.adaptive_minus_sbs_ci.ci_lower*1e3:.3f} ms, {boot_res.adaptive_minus_sbs_ci.ci_upper*1e3:.3f} ms]")
    print(f"  Hypothesis H5 Status    : {'SUPPORTED' if boot_res.h5_supported else 'NOT SUPPORTED'} ({boot_res.h5_interpretation})")

    # 10. Publication Figures & Tables (Phase 18)
    print("\n--- [STEP 8: PUBLICATION FIGURES & TABLES (PHASE 18)] ---")
    raw_dict_rows = [r.to_dict() for r in all_benchmark_rows]
    fig_files = generate_all_figures(
        benchmark_rows=raw_dict_rows,
        workload_res=workload_res,
        tier_summaries=tier_summaries,
        selector_eval=selector_eval,
        output_dir=fig_dir,
    )
    tbl_files = generate_all_tables(
        benchmark_rows=raw_dict_rows,
        workload_res=workload_res,
        tier_summaries=tier_summaries,
        selector_eval=selector_eval,
        output_dir=tbl_dir,
    )
    print(f"  Figures Generated: {len(fig_files)} files (PNG & PDF)")
    print(f"  Tables Generated : {len(tbl_files)} files (Markdown, CSV, LaTeX)")

    # 11. Subgroup Analysis (Family, V, D, Q)
    print("\n--- [STEP 9: SUBGROUP ANALYSIS (FAMILY, V, D, Q)] ---")
    subgroup_csv = proc_dir / f"{experiment_id}_subgroup_analysis.csv"
    subgroup_rows = []
    
    # Test query results mapped to graph metadata
    test_graph_map = {g.graph_id: g for g in graphs.values() if g.graph_id in test_ids}
    by_test_graph = {}
    for qr in selector_eval.query_results:
        by_test_graph.setdefault(qr.graph_id, []).append(qr)

    oracle_map = {(inst.graph_id, inst.query_id): inst for inst in oracle_summary.instances}

    for gid, qrs in by_test_graph.items():
        g = test_graph_map[gid]
        fam = g.metadata["graph_family"]
        V = g.num_nodes
        D = g.metadata.get("target_average_degree", 6.0)
        g_feat = g_feat_times.get(gid, 0.0)

        for Q in q_checkpoints:
            sub_q = qrs[:min(Q, len(qrs))]
            c_qfeat = sum(qr.query_feature_time for qr in sub_q)
            c_sel = sum(qr.selection_time for qr in sub_q)
            c_solv = sum(qr.selected_solver_runtime for qr in sub_q)
            c_adapt = g_feat + c_qfeat + c_sel + c_solv

            c_sbs = sum(oracle_map[(gid, qr.query_id)].always_bidi_cost for qr in sub_q)
            c_vbs = sum(oracle_map[(gid, qr.query_id)].vbs_cost for qr in sub_q)

            gap = c_sbs - c_vbs
            gap_cl = (c_sbs - c_adapt) / gap if abs(gap) > 1e-12 else math.nan
            diff = c_adapt - c_sbs
            ratio = c_adapt / c_sbs if c_sbs > 0 else 1.0

            subgroup_rows.append({
                "graph_id": gid,
                "family": fam,
                "V": V,
                "target_D": D,
                "Q": Q,
                "C_graph_feature": g_feat,
                "C_query_feature": c_qfeat,
                "C_selection": c_sel,
                "C_solver": c_solv,
                "C_adaptive": c_adapt,
                "C_SBS": c_sbs,
                "C_VBS": c_vbs,
                "Adaptive_minus_SBS": diff,
                "Adaptive_ratio_SBS": ratio,
                "GapClosed": gap_cl,
                "BreakEven": "yes" if c_adapt < c_sbs else "not_observed",
            })

    with open(subgroup_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(subgroup_rows[0].keys()))
        w.writeheader()
        w.writerows(subgroup_rows)
    print(f"  Subgroup Analysis saved to: {subgroup_csv}")

    # 12. Final Numerical Integrity Audit
    print("\n--- [STEP 10: CROSS-ARTIFACT NUMERICAL INTEGRITY AUDIT] ---")
    # Verify:
    # 1. Main Workload C_adaptive == C_graph + C_query + C_sel + C_solver exactly
    audit_passed = True
    for Q, pt in workload_res.aggregate_points.items():
        c_g = pt["total_graph_feature"]
        c_q = pt["total_query_feature"]
        c_sel = pt["total_selection"]
        c_solv = pt["total_solver"]
        c_ad = pt["total_Adaptive"]
        c_sum = c_g + c_q + c_sel + c_solv
        diff = abs(c_ad - c_sum)
        if diff > 1e-12:
            print(f"  FAIL: Discrepancy at Q={Q}: c_ad={c_ad:.9f} vs sum={c_sum:.9f} (diff={diff:.2e})")
            audit_passed = False
        else:
            print(f"  PASS Q={Q:<3}: C_adaptive ({c_ad*1e3:.4f}ms) == C_g({c_g*1e3:.4f}ms) + C_q({c_q*1e3:.4f}ms) + C_sel({c_sel*1e3:.4f}ms) + C_solv({c_solv*1e3:.4f}ms)")

    # 2. Reconcile Main Workload with Tier 0+1 Workload
    tier1_wk = [w for w in tier_workloads if w.tier == 1]
    for w in tier1_wk:
        main_pt = workload_res.aggregate_points[w.Q]
        diff_ad = abs(w.total_adaptive_cost - main_pt["total_Adaptive"])
        diff_sbs = abs(w.total_sbs_cost - main_pt["total_SBS"])
        diff_vbs = abs(w.total_vbs_cost - main_pt["total_VBS"])
        if diff_ad > 1e-12 or diff_sbs > 1e-12 or diff_vbs > 1e-12:
            print(f"  FAIL: Tier 1 vs Main mismatch at Q={w.Q}: diff_ad={diff_ad:.2e}")
            audit_passed = False
        else:
            print(f"  PASS Tier 0+1 cross-artifact match at Q={w.Q}: diff=0.000ms")

    assert audit_passed, "Numerical integrity audit failed!"

    # 13. Save Stage 20 Reproducibility Manifest
    total_wall_clock = time.perf_counter() - start_total_time
    manifest_out = {
        "experiment_id": experiment_id,
        "configuration_hash": actual_hash,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_wall_clock_seconds": total_wall_clock,
        "benchmark_wall_clock_seconds": bench_wall_time,
        "num_graphs": 48,
        "num_queries_per_graph": 500,
        "total_queries": 24000,
        "total_solver_runs": 72000,
        "train_graph_ids": train_ids,
        "validation_graph_ids": val_ids,
        "test_graph_ids": test_ids,
        "sbs_policy": oracle_summary.sbs_policy,
        "test_metrics_summary": {
            "exact_accuracy": selector_eval.exact_accuracy,
            "near_best_accuracy": selector_eval.near_best_accuracy,
            "mean_selection_time_us": selector_eval.mean_selection_time * 1e6,
            "mean_feature_time_us": selector_eval.mean_feature_time * 1e6,
            "aggregate_break_even_Q": workload_res.aggregate_break_even_Q,
            "gap_closed_ci": {
                "point": boot_res.gap_closed_ci.point_estimate,
                "ci_lower": boot_res.gap_closed_ci.ci_lower,
                "ci_upper": boot_res.gap_closed_ci.ci_upper,
            },
            "adaptive_minus_sbs_ci": {
                "point": boot_res.adaptive_minus_sbs_ci.point_estimate,
                "ci_lower": boot_res.adaptive_minus_sbs_ci.ci_lower,
                "ci_upper": boot_res.adaptive_minus_sbs_ci.ci_upper,
            },
        },
        "artifacts": {
            "raw_benchmark_csv": str(raw_csv_file.as_posix()),
            "graph_stats_csv": str(graph_stats_file.as_posix()),
            "oracle_results_csv": str((proc_dir / f"{experiment_id}_oracle_results.csv").as_posix()),
            "workload_curves_csv": str((proc_dir / f"{experiment_id}_workload_curves.csv").as_posix()),
            "subgroup_analysis_csv": str(subgroup_csv.as_posix()),
            "bootstrap_results_csv": str((proc_dir / f"{experiment_id}_bootstrap_results.csv").as_posix()),
            "feature_tier_tradeoffs_csv": str((proc_dir / f"{experiment_id}_feature_tier_tradeoffs.csv").as_posix()),
        },
    }

    manifest_file = proc_dir / f"{experiment_id}_stage20_manifest.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest_out, f, indent=2)

    print("\n================================================================================")
    print(f"STAGE 20 FULL EXPERIMENT COMPLETED IN {total_wall_clock:.2f}s ({total_wall_clock/60:.2f} min)")
    print(f"EXPERIMENT ID: {experiment_id}")
    print(f"MANIFEST     : {manifest_file}")
    print("================================================================================")
    return 0

if __name__ == "__main__":
    sys.exit(run_stage20())
