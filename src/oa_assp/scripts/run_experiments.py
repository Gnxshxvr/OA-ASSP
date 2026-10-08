"""Master experiment orchestration script executing Phases 14.5 through 18."""

from __future__ import annotations
import argparse
import csv
import datetime
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

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


def run_experiments(profile: str = "full") -> int:
    print(f"OA-ASSP MASTER EXPERIMENT (PROFILE: {profile.upper()})")
    print("==================================================")
    start_all = time.perf_counter()

    results_dir = Path("results")
    raw_dir = results_dir / "raw"
    proc_dir = results_dir / "processed"
    fig_dir = results_dir / "figures"
    tbl_dir = results_dir / "tables"

    for d in [raw_dir, proc_dir, fig_dir, tbl_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # 1. Determine configuration based on profile
    if profile == "smoke":
        sizes = [40]
        degrees = [6.0]
        families = ["random", "geometric", "scale_free"]
        seeds_per_cfg = 1
        q_count = 5
        q_checkpoints = [1, 2, 5]
        boot_reps = 100
    elif profile == "development":
        sizes = [40, 80]
        degrees = [6.0, 12.0]
        families = ["random", "geometric", "scale_free"]
        seeds_per_cfg = 2
        q_count = 10
        q_checkpoints = [1, 5, 10]
        boot_reps = 500
    else:  # full
        sizes = [40, 80]
        degrees = [6.0, 12.0]
        families = ["random", "geometric", "scale_free"]
        seeds_per_cfg = 2
        q_count = 500
        q_checkpoints = [1, 10, 50, 100, 500]
        boot_reps = 500

    experiment_id = f"final_q1_q10_q50_q100_q500_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # -------------------------------------------------------------
    # STEP 1: Graph and Query Generation
    # -------------------------------------------------------------
    print("\n[Step 1] Generating graphs and deterministic query workloads...")
    graphs = {}
    queries_by_graph = {}
    all_benchmark_rows = []
    base_seed = 100

    cfg_idx = 0
    for fam in families:
        for V in sizes:
            for D in degrees:
                for s_i in range(seeds_per_cfg):
                    cfg_idx += 1
                    seed = base_seed + cfg_idx
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

                    queries = generate_query_workload(g, count=q_count, global_seed=seed + 2000)
                    queries_by_graph[g.graph_id] = queries

                    # Run solvers
                    for q in queries:
                        rows = run_single_query(
                            graph=g,
                            query=q,
                            experiment_id=experiment_id,
                            warmup_runs=1,
                            repetitions=3,
                            timeout_seconds=5.0,
                        )
                        all_benchmark_rows.extend(rows)

    print(f"  Graphs generated       : {len(graphs)}")
    print(f"  Queries generated      : {sum(len(q) for q in queries_by_graph.values())}")
    print(f"  Benchmark rows produced: {len(all_benchmark_rows)}")

    # Save raw benchmark rows for immutability
    raw_csv = raw_dir / f"{experiment_id}_benchmark_rows.csv"
    if all_benchmark_rows:
        fieldnames = list(all_benchmark_rows[0].to_dict().keys())
        with open(raw_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in all_benchmark_rows:
                writer.writerow(r.to_dict())
    print(f"  Raw benchmark data saved: {raw_csv}")

    # -------------------------------------------------------------
    # STEP 2: Oracles (SBS & VBS)
    # -------------------------------------------------------------
    print("\n[Step 2] Computing SBS and VBS Oracles...")
    oracle_summary = compute_oracles(all_benchmark_rows)
    save_oracle_results(oracle_summary, proc_dir / f"{experiment_id}_oracle_results.csv")
    print(f"  Global SBS policy: {oracle_summary.sbs_policy}")
    print(f"  Total SBS cost   : {oracle_summary.sbs_total_cost:.6f}s")
    print(f"  Total VBS cost   : {oracle_summary.vbs_total_cost:.6f}s")
    print(f"  VBS win counts   : {oracle_summary.vbs_win_counts}")

    # -------------------------------------------------------------
    # STEP 3: Phase 14.5 Methodology & Leakage Audits
    # -------------------------------------------------------------
    print("\n[Step 3] Executing Phase 14.5 Methodology Audits...")
    # Audit 1: Feature manifest consistency
    t0_names = get_feature_names_for_tier(0)
    t1_names = get_feature_names_for_tier(1)
    t2_names = get_feature_names_for_tier(2)
    manifest_pass = (len(t0_names) == 6 and len(t1_names) == 21 and len(t2_names) == 23)
    print(f"  1. Feature Count Consistency: {'PASS' if manifest_pass else 'FAIL'} (T0={len(t0_names)}, T0+1={len(t1_names)}, T0+1+2={len(t2_names)})")

    # Audit 2: A* admissibility & validity
    geom_graphs = [g for g in graphs.values() if g.metadata.get("weight_model") == "geometric"]
    astar_valid_pass = all(g.metadata.get("heuristic_valid") is True for g in geom_graphs)
    print(f"  2. A* Admissibility & Validity: {'PASS' if astar_valid_pass else 'FAIL'}")

    # Audit 3: Leakage audit
    leak_audit = audit_feature_columns(t1_names)
    print(f"  3. Data Leakage Audit         : {'PASS' if leak_audit.passed else 'FAIL'}")
    if not leak_audit.passed:
        print(f"     Violations: {leak_audit.violations}")

    # Audit 4: Stratified graph-level split
    split_data = prepare_selector_dataset(
        graphs=graphs,
        queries_by_graph=queries_by_graph,
        oracle_summary=oracle_summary,
        tier=1,
        train_ratio=0.70,
        val_ratio=0.15,
        test_ratio=0.15,
        seed=42,
        stratified=True,
    )
    # Check disjointness
    tr_set = set(split_data.train.graph_ids)
    va_set = set(split_data.val.graph_ids) if split_data.val else set()
    te_set = set(split_data.test.graph_ids)
    disjoint_pass = (len(tr_set & te_set) == 0 and len(tr_set & va_set) == 0 and len(va_set & te_set) == 0)
    print(f"  4. Graph-Level Disjointness   : {'PASS' if disjoint_pass else 'FAIL'}")
    print(f"     Train graphs: {len(tr_set)}, Val graphs: {len(va_set)}, Test graphs: {len(te_set)}")

    # Audit 5: Feature cost accounting
    all_metas = split_data.train.metadata + (split_data.val.metadata if split_data.val else []) + split_data.test.metadata
    g_feat_times = {m["graph_id"]: m["graph_feature_time"] for m in all_metas}
    cost_acct_pass = all(t >= 0.0 for t in g_feat_times.values())
    print(f"  5. Feature Cost Accounting   : {'PASS' if cost_acct_pass else 'FAIL'}")

    all_audits_pass = manifest_pass and astar_valid_pass and leak_audit.passed and disjoint_pass and cost_acct_pass
    print(f"  >>> Overall Phase 14.5 Audit : {'PASS' if all_audits_pass else 'FAIL'}")

    # -------------------------------------------------------------
    # STEP 4: Selector Training and Evaluation
    # -------------------------------------------------------------
    print("\n[Step 4] Training Decision Tree Selector...")
    selector = DecisionTreeSelector(max_depth=4, min_samples_leaf=3, random_state=42)
    selector.fit(split_data.train)

    selector_eval = selector.evaluate(split_data.test, epsilon=0.05)
    print(f"  Test queries evaluated : {selector_eval.num_queries}")
    print(f"  Exact winner accuracy  : {selector_eval.exact_accuracy * 100:.2f}%")
    print(f"  Near-best accuracy     : {selector_eval.near_best_accuracy * 100:.2f}% (eps=0.05)")
    print(f"  Mean selection time    : {selector_eval.mean_selection_time * 1e6:.2f} us")
    print(f"  Mean feature time      : {selector_eval.mean_feature_time * 1e6:.2f} us")

    # Export Decision Tree nodes and text representation
    tree_nodes = selector.export_tree_nodes()
    with open(proc_dir / f"{experiment_id}_decision_tree_nodes.json", "w", encoding="utf-8") as f:
        json.dump(tree_nodes, f, indent=2)
    with open(proc_dir / f"{experiment_id}_decision_tree_structure.txt", "w", encoding="utf-8") as f:
        f.write(selector_eval.tree_text)

    # -------------------------------------------------------------
    # STEP 5: Phase 15 Query Workload Analysis
    # -------------------------------------------------------------
    print("\n[Step 5] Computing Query Workload Analysis (Phase 15)...")
    workload_res = compute_workload_analysis(
        query_results=selector_eval.query_results,
        oracle_summary=oracle_summary,
        graph_feature_times=g_feat_times,
        q_checkpoints=q_checkpoints,
    )
    save_workload_results(workload_res, proc_dir / f"{experiment_id}_workload_curves.csv")
    print(f"  Aggregate break-even Q: {workload_res.aggregate_break_even_Q if workload_res.aggregate_break_even_Q else 'not_observed'}")
    for q, p in sorted(workload_res.aggregate_points.items()):
        gap_str = f"{p['gap_closed']:.4f}" if not np.isnan(p["gap_closed"]) else "N/A"
        print(f"    Q={q:<3}: SBS={p['total_SBS']*1e3:.2f}ms, Adaptive={p['total_Adaptive']*1e3:.2f}ms, VBS={p['total_VBS']*1e3:.2f}ms, GapClosed={gap_str}")

    # -------------------------------------------------------------
    # STEP 6: Phase 16 Feature-Tier Trade-offs
    # -------------------------------------------------------------
    print("\n[Step 6] Evaluating Feature-Tier Trade-offs (Phase 16)...")
    tier_summaries, tier_workloads = evaluate_feature_tiers(
        graphs=graphs,
        queries_by_graph=queries_by_graph,
        oracle_summary=oracle_summary,
        train_ratio=0.70,
        val_ratio=0.15,
        test_ratio=0.15,
        seed=42,
        q_checkpoints=q_checkpoints,
        split_data_tier1=split_data,
        eval_res_tier1=selector_eval,
    )
    save_feature_tier_results(tier_summaries, proc_dir / f"{experiment_id}_feature_tier_tradeoffs.csv")
    save_tier_workload_results(tier_workloads, proc_dir / f"{experiment_id}_tier_workload_results.csv")
    for s in tier_summaries:
        gap_str = f"{s.gap_closed:.4f}" if not np.isnan(s.gap_closed) else "N/A"
        print(f"    {s.tier_name:<25}: Acc={s.exact_accuracy*100:.1f}%, NearAcc={s.near_best_accuracy*100:.1f}%, GapClosed={gap_str}")

    # -------------------------------------------------------------
    # STEP 7: Phase 17 Graph-Level Bootstrap
    # -------------------------------------------------------------
    print("\n[Step 7] Running Graph-Level Bootstrap (Phase 17)...")
    boot_res = run_graph_level_bootstrap(
        query_results=selector_eval.query_results,
        oracle_summary=oracle_summary,
        test_split=split_data.test,
        num_replicates=boot_reps,
        confidence_level=0.95,
        seed=4001,
    )
    save_bootstrap_results(boot_res, proc_dir / f"{experiment_id}_bootstrap_results.csv")
    print(f"  GapClosed 95% CI: [{boot_res.gap_closed_ci.ci_lower:.4f}, {boot_res.gap_closed_ci.ci_upper:.4f}] (Point: {boot_res.gap_closed_ci.point_estimate:.4f})")
    print(f"  Adaptive - SBS  : [{boot_res.adaptive_minus_sbs_ci.ci_lower*1e3:.3f}ms, {boot_res.adaptive_minus_sbs_ci.ci_upper*1e3:.3f}ms] (Point: {boot_res.adaptive_minus_sbs_ci.point_estimate*1e3:.3f}ms)")
    print(f"  Hypothesis H5   : {'SUPPORTED' if boot_res.h5_supported else 'NOT SUPPORTED'} ({boot_res.h5_interpretation})")

    # -------------------------------------------------------------
    # STEP 8: Phase 18 Publication Figures & Tables
    # -------------------------------------------------------------
    print("\n[Step 8] Generating Publication Figures & Tables (Phase 18)...")
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
    print(f"  Figures generated: {len(fig_files)} files (10 figures in PNG & PDF)")
    print(f"  Tables generated : {len(tbl_files)} files (7 tables in MD, CSV, LaTeX)")

    # Save reproducibility manifest
    manifest = {
        "experiment_id": experiment_id,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "profile": profile,
        "configuration_hash": hashlib.sha256(str(sorted(graphs.keys())).encode()).hexdigest(),
        "random_seed": 42,
        "graph_seeds": [base_seed + i for i in range(1, cfg_idx + 1)],
        "query_seeds": [base_seed + i + 2000 for i in range(1, cfg_idx + 1)],
        "train_graph_ids": sorted(split_data.train.graph_ids),
        "validation_graph_ids": sorted(split_data.val.graph_ids) if split_data.val else [],
        "test_graph_ids": sorted(split_data.test.graph_ids),
        "feature_tiers": ["Tier 0: O(1)", "Tier 0+1: O(V+E)", "Tier 0+1+2: Structural"],
        "tree_parameters": {
            "max_depth": 4,
            "min_samples_leaf": 3,
            "random_state": 42,
            "criterion": "gini",
        },
        "timing_repetitions": 3,
        "epsilon": 0.05,
        "bootstrap_seed": 4001,
        "bootstrap_samples": boot_reps,
        "confidence_level": 0.95,
        "Q_values": q_checkpoints,
    }
    with open(proc_dir / f"{experiment_id}_reproducibility_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    elapsed_all = time.perf_counter() - start_all
    print(f"\n==================================================")
    print(f"EXPERIMENT COMPLETED in {elapsed_all:.2f}s")
    print(f"STATUS: {'PASS' if all_audits_pass else 'FAIL'}")
    return 0 if all_audits_pass else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run OA-ASSP experiments.")
    parser.add_argument(
        "--profile",
        choices=["smoke", "development", "full"],
        default="full",
        help="Experiment profile to run.",
    )
    args = parser.parse_args()
    return run_experiments(profile=args.profile)



if __name__ == "__main__":
    sys.exit(main())
