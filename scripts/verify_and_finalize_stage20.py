"""Verify and finalize Stage 20 results, perform full numerical audit, and save manifest."""

from __future__ import annotations
import csv
import datetime
import json
import math
from pathlib import Path
import sys
import numpy as np

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def verify_and_finalize():
    exp_dir = Path("results/stage20_scaleup_48g_20260920_215427")
    raw_dir = exp_dir / "raw"
    proc_dir = exp_dir / "processed"
    fig_dir = exp_dir / "figures"
    tbl_dir = exp_dir / "tables"

    exp_id = "stage20_scaleup_48g_20260920_215427"
    raw_csv = raw_dir / f"{exp_id}_benchmark_rows.csv"
    stats_csv = proc_dir / f"{exp_id}_graph_realized_stats.csv"
    oracle_csv = proc_dir / f"{exp_id}_oracle_results.csv"
    workload_csv = proc_dir / f"{exp_id}_workload_curves.csv"
    tier_wk_csv = proc_dir / f"{exp_id}_tier_workload_results.csv"
    tier_tradeoff_csv = proc_dir / f"{exp_id}_feature_tier_tradeoffs.csv"
    subgroup_csv = proc_dir / f"{exp_id}_subgroup_analysis.csv"
    bootstrap_csv = proc_dir / f"{exp_id}_bootstrap_results.csv"

    print("================================================================================")
    print("STAGE 20 FINAL VERIFICATION & NUMERICAL INTEGRITY AUDIT")
    print("================================================================================")

    # 1. Row count verification
    with open(raw_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        raw_rows = list(reader)

    print(f"\n1. Raw Benchmark Records:")
    print(f"   Total rows: {len(raw_rows)}")
    assert len(raw_rows) == 72000, f"Expected 72000, got {len(raw_rows)}"

    unique_queries = set((r["graph_id"], r["query_id"]) for r in raw_rows)
    print(f"   Unique queries: {len(unique_queries)}")
    assert len(unique_queries) == 24000, f"Expected 24000, got {len(unique_queries)}"

    dijk_rows = [r for r in raw_rows if r["algorithm"] == "Dijkstra"]
    bidi_rows = [r for r in raw_rows if r["algorithm"] == "Bidirectional Dijkstra"]
    astar_rows = [r for r in raw_rows if r["algorithm"] == "A*"]

    print(f"   Dijkstra executions           : {len(dijk_rows)}")
    print(f"   Bidirectional Dijkstra execs   : {len(bidi_rows)}")
    print(f"   A* executions                 : {len(astar_rows)}")

    # Check validity
    geom_astar = [r for r in astar_rows if r["graph_family"] == "geometric"]
    non_geom_astar = [r for r in astar_rows if r["graph_family"] != "geometric"]

    print(f"   A* valid executions (geom)     : {len(geom_astar)}")
    print(f"   A* skipped/invalid (non-geom) : {len(non_geom_astar)}")

    assert len(dijk_rows) == 24000
    assert len(bidi_rows) == 24000
    assert len(geom_astar) == 8000
    assert len(non_geom_astar) == 16000

    # 2. Check correctness & timeouts
    correctness_failures = sum(1 for r in raw_rows if r["correct"] != "True")
    timeouts = sum(1 for r in raw_rows if r["success"] != "True")
    print(f"   Correctness failures          : {correctness_failures}")
    print(f"   Timeouts                      : {timeouts}")
    assert correctness_failures == 0
    assert timeouts == 0

    # 3. Workload Curves Verification
    with open(workload_csv, "r", encoding="utf-8") as f:
        workload_pts = list(csv.DictReader(f))

    print(f"\n2. Workload Points Audit ({len(workload_pts)} per-graph records):")
    # Group by Q across all 8 test graphs
    q_vals = [1, 10, 50, 100, 500]
    agg_workload = {}
    for q in q_vals:
        pts_q = [r for r in workload_pts if int(r["Q"]) == q]
        tot_sbs = sum(float(r["C_SBS"]) for r in pts_q)
        tot_adapt = sum(float(r["C_Adaptive"]) for r in pts_q)
        tot_vbs = sum(float(r["C_VBS"]) for r in pts_q)
        tot_gfeat = sum(float(r["C_graph_feature"]) for r in pts_q)
        tot_qfeat = sum(float(r["C_query_feature"]) for r in pts_q)
        tot_sel = sum(float(r["C_selection"]) for r in pts_q)
        tot_solv = sum(float(r["C_solver"]) for r in pts_q)

        # Check identity
        sum_components = tot_gfeat + tot_qfeat + tot_sel + tot_solv
        diff_ad = abs(tot_adapt - sum_components)
        assert diff_ad < 1e-12, f"Discrepancy at Q={q}: {tot_adapt} vs {sum_components} (diff={diff_ad})"

        gap = tot_sbs - tot_vbs
        gap_closed = (tot_sbs - tot_adapt) / gap if abs(gap) > 1e-12 else math.nan

        agg_workload[q] = {
            "Q": q,
            "SBS": tot_sbs,
            "Adaptive": tot_adapt,
            "VBS": tot_vbs,
            "C_graph_feature": tot_gfeat,
            "C_query_feature": tot_qfeat,
            "C_selection": tot_sel,
            "C_solver": tot_solv,
            "Adaptive_minus_SBS": tot_adapt - tot_sbs,
            "Adaptive_ratio_SBS": tot_adapt / tot_sbs if tot_sbs > 0 else 1.0,
            "GapClosed": gap_closed,
        }

        print(f"   PASS Q={q:<3}: SBS={tot_sbs*1e3:8.3f}ms | Adaptive={tot_adapt*1e3:8.3f}ms | VBS={tot_vbs*1e3:8.3f}ms | GapClosed={gap_closed:.4f}")
        print(f"          Components: G_feat={tot_gfeat*1e3:6.3f}ms + Q_feat={tot_qfeat*1e3:6.3f}ms + Sel={tot_sel*1e3:6.3f}ms + Solv={tot_solv*1e3:6.3f}ms = {sum_components*1e3:8.3f}ms")

    # 4. Cross-Artifact Reconciliation: Tier 0+1 Workload vs Main Workload
    with open(tier_wk_csv, "r", encoding="utf-8") as f:
        tier_wk_rows = list(csv.DictReader(f))

    print(f"\n3. Cross-Artifact Reconciliation: Tier 0+1 vs Main Workload:")
    tier1_wk = [r for r in tier_wk_rows if int(r["tier"]) == 1]
    for r in tier1_wk:
        q = int(r["Q"])
        main_pt = agg_workload[q]
        t_ad = float(r["total_adaptive_cost"])
        t_sbs = float(r["total_sbs_cost"])
        t_vbs = float(r["total_vbs_cost"])
        t_feat = float(r["feature_cost"])
        t_sel = float(r["selection_cost"])
        t_solv = float(r["solver_cost"])

        diff_ad = abs(t_ad - main_pt["Adaptive"])
        diff_sbs = abs(t_sbs - main_pt["SBS"])
        diff_vbs = abs(t_vbs - main_pt["VBS"])

        assert diff_ad < 1e-12, f"Tier 1 mismatch on Adaptive at Q={q}: {t_ad} vs {main_pt['Adaptive']}"
        assert diff_sbs < 1e-12, f"Tier 1 mismatch on SBS at Q={q}: {t_sbs} vs {main_pt['SBS']}"
        assert diff_vbs < 1e-12, f"Tier 1 mismatch on VBS at Q={q}: {t_vbs} vs {main_pt['VBS']}"
        print(f"   PASS Q={q:<3}: Tier 0+1 Adaptive={t_ad*1e3:.4f}ms == Main Adaptive={main_pt['Adaptive']*1e3:.4f}ms (diff=0.000ms)")

    # 5. Bootstrap verification
    with open(bootstrap_csv, "r", encoding="utf-8") as f:
        boot_rows = list(csv.DictReader(f))
    print(f"\n4. Bootstrap Results:")
    for r in boot_rows:
        print(f"   {r['metric_name']:<22}: Point={float(r['point_estimate']):.4f}, 95% CI=[{float(r['ci_lower']):.4f}, {float(r['ci_upper']):.4f}]")

    # 6. Save final stage 20 manifest
    with open(stats_csv, "r", encoding="utf-8") as f:
        stat_rows = list(csv.DictReader(f))
    train_ids = sorted([r["graph_id"] for r in stat_rows if r["split"] == "train"])
    val_ids = sorted([r["graph_id"] for r in stat_rows if r["split"] == "validation"])
    test_ids = sorted([r["graph_id"] for r in stat_rows if r["split"] == "test"])

    manifest_out = {
        "experiment_id": exp_id,
        "configuration_hash": "58590b0bb55428b3674107b937c2e261406bfe3d84f34c3f5bfd7b63c20596ec",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_wall_clock_seconds": 95.37,
        "num_graphs": 48,
        "num_queries_per_graph": 500,
        "total_queries": 24000,
        "total_solver_runs": 72000,
        "train_graph_ids": train_ids,
        "validation_graph_ids": val_ids,
        "test_graph_ids": test_ids,
        "sbs_policy": "Always-Bidirectional-Dijkstra",
        "main_workload_results": agg_workload,
        "audit_status": "PASS",
    }

    manifest_file = proc_dir / f"{exp_id}_stage20_manifest.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest_out, f, indent=2)

    print(f"\nManifest saved to: {manifest_file}")
    print("\n================================================================================")
    print("STAGE 20 FINAL NUMERICAL INTEGRITY AUDIT: ALL CHECKS PASSED (100% RECONCILED)")
    print("================================================================================")
    return 0

if __name__ == "__main__":
    sys.exit(verify_and_finalize())
