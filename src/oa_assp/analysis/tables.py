"""Publication table generation in Markdown, CSV, and LaTeX formats."""

from __future__ import annotations
import csv
from pathlib import Path
from typing import Any, Dict, List, Union
import numpy as np

from oa_assp.analysis.feature_tiers import TierEvaluationSummary
from oa_assp.analysis.workload import WorkloadAnalysisResult
from oa_assp.selector.decision_tree import SelectorEvaluationResult


def _save_table(
    headers: List[str],
    rows: List[List[Any]],
    name: str,
    output_dir: Path,
) -> List[str]:
    """Save a table in CSV, Markdown, and LaTeX formats."""
    output_dir.mkdir(parents=True, exist_ok=True)
    generated: List[str] = []

    # 1. CSV
    csv_file = output_dir / f"{name}.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    generated.append(str(csv_file))

    # 2. Markdown
    md_file = output_dir / f"{name}.md"
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(f"# {name.replace('_', ' ').title()}\n\n")
        f.write("| " + " | ".join(headers) + " |\n")
        f.write("| " + " | ".join(["---"] * len(headers)) + " |\n")
        for r in rows:
            f.write("| " + " | ".join(str(x) for x in r) + " |\n")
    generated.append(str(md_file))

    # 3. LaTeX
    tex_file = output_dir / f"{name}.tex"
    with open(tex_file, "w", encoding="utf-8") as f:
        f.write("\\begin{table}[htbp]\n\\centering\n")
        f.write(f"\\caption{{{name.replace('_', ' ').title()}}}\n")
        cols_align = "l" + "r" * (len(headers) - 1)
        f.write(f"\\begin{{tabular}}{{{cols_align}}}\n\\hline\n")
        f.write(" & ".join(headers).replace("_", "\\_") + " \\\\\n\\hline\n")
        for r in rows:
            f.write(" & ".join(str(x) for x in r).replace("_", "\\_") + " \\\\\n")
        f.write("\\hline\n\\end{tabular}\n\\end{table}\n")
    generated.append(str(tex_file))

    return generated


def generate_all_tables(
    benchmark_rows: List[Dict[str, Any]],
    workload_res: WorkloadAnalysisResult,
    tier_summaries: List[TierEvaluationSummary],
    selector_eval: SelectorEvaluationResult,
    output_dir: Union[str, Path] = "results/tables",
) -> List[str]:
    """Generate and save all 7 required publication tables."""
    out_path = Path(output_dir)
    generated_files: List[str] = []

    # --- Table 1: Graph configuration summary ---
    t1_headers = ["Graph ID", "Family", "Vertices (V)", "Edges (E)", "Target Degree", "Actual Degree", "Weight Model"]
    t1_seen = set()
    t1_rows = []
    for r in benchmark_rows:
        gid = r["graph_id"]
        if gid not in t1_seen:
            t1_seen.add(gid)
            t1_rows.append([
                gid,
                r.get("graph_family", "unknown"),
                r["V"],
                r["E"],
                f"{float(r['target_average_degree']):.1f}",
                f"{float(r['actual_average_degree']):.2f}",
                r.get("weight_model", "unknown"),
            ])
    generated_files.extend(_save_table(t1_headers, t1_rows, "table01_graph_configurations", out_path))

    # --- Table 2: Algorithm runtime summary ---
    t2_headers = ["Algorithm", "Median Runtime (ms)", "Mean Runtime (ms)", "Min Runtime (ms)", "Max Runtime (ms)", "Std Dev (ms)"]
    t2_rows = []
    for algo in ["Dijkstra", "Bidirectional Dijkstra", "A*"]:
        times = [float(r["runtime_median"]) * 1e3 for r in benchmark_rows if r["algorithm"] == algo and r.get("success")]
        if times:
            t2_rows.append([
                algo,
                f"{np.median(times):.3f}",
                f"{np.mean(times):.3f}",
                f"{np.min(times):.3f}",
                f"{np.max(times):.3f}",
                f"{np.std(times):.3f}",
            ])
    generated_files.extend(_save_table(t2_headers, t2_rows, "table02_algorithm_runtime", out_path))

    # --- Table 3: Operation counts ---
    t3_headers = ["Algorithm", "Mean Edges Examined", "Mean Relaxations", "Mean Heap Pushes", "Mean Heap Pops", "Mean Nodes Expanded"]
    t3_rows = []
    for algo in ["Dijkstra", "Bidirectional Dijkstra", "A*"]:
        rows_a = [r for r in benchmark_rows if r["algorithm"] == algo and r.get("success")]
        if rows_a:
            t3_rows.append([
                algo,
                f"{np.mean([int(r['edges_examined']) for r in rows_a]):.1f}",
                f"{np.mean([int(r['relaxations']) for r in rows_a]):.1f}",
                f"{np.mean([int(r['heap_pushes']) for r in rows_a]):.1f}",
                f"{np.mean([int(r['heap_pops']) for r in rows_a]):.1f}",
                f"{np.mean([int(r['nodes_expanded']) for r in rows_a]):.1f}",
            ])
    generated_files.extend(_save_table(t3_headers, t3_rows, "table03_operation_counts", out_path))

    # --- Table 4: Feature tier cost/performance ---
    t4_headers = ["Tier", "Features", "Graph Feature Time (μs)", "Query Feature Time (μs)", "Selection Time (μs)", "Exact Acc (%)", "Near-Best Acc (%)", "GapClosed"]
    t4_rows = []
    for s in tier_summaries:
        gap_str = f"{s.gap_closed:.4f}" if not np.isnan(s.gap_closed) else "N/A"
        t4_rows.append([
            s.tier_name,
            s.feature_count,
            f"{s.mean_graph_feature_time * 1e6:.1f}",
            f"{s.mean_query_feature_time * 1e6:.1f}",
            f"{s.mean_selection_time * 1e6:.1f}",
            f"{s.exact_accuracy * 100:.1f}",
            f"{s.near_best_accuracy * 100:.1f}",
            gap_str,
        ])
    generated_files.extend(_save_table(t4_headers, t4_rows, "table04_feature_tier_tradeoff", out_path))

    # --- Table 5: SBS vs Adaptive vs VBS ---
    t5_headers = ["Policy", "Type", "Total Solver Cost (ms)", "Total Overhead (ms)", "Total Workload Cost (ms)"]
    t5_rows = []
    max_q = max(workload_res.aggregate_points.keys()) if workload_res.aggregate_points else 1
    p_info = workload_res.aggregate_points.get(max_q, {})
    t5_rows.append(["SBS", "Fixed Policy", f"{p_info.get('total_SBS', 0.0)*1e3:.3f}", "0.000", f"{p_info.get('total_SBS', 0.0)*1e3:.3f}"])
    ovhd = (p_info.get("total_graph_feature", 0.0) + p_info.get("total_query_feature", 0.0) + p_info.get("total_selection", 0.0)) * 1e3
    solv = p_info.get("total_solver", 0.0) * 1e3
    tot_ad = p_info.get("total_Adaptive", 0.0) * 1e3
    t5_rows.append(["OA-ASSP", "Adaptive Policy", f"{solv:.3f}", f"{ovhd:.3f}", f"{tot_ad:.3f}"])
    t5_rows.append(["VBS", "Offline Oracle", f"{p_info.get('total_VBS', 0.0)*1e3:.3f}", "0.000", f"{p_info.get('total_VBS', 0.0)*1e3:.3f}"])
    generated_files.extend(_save_table(t5_headers, t5_rows, "table05_sbs_vs_adaptive_vs_vbs", out_path))

    # --- Table 6: Q crossover / workload analysis ---
    t6_headers = ["Q", "SBS", "Adaptive", "VBS", "Adaptive-SBS", "Adaptive/SBS", "GapClosed", "BreakEven"]
    t6_rows = []
    for q, p in sorted(workload_res.aggregate_points.items()):
        gap_str = f"{p['gap_closed']:.4f}" if not np.isnan(p["gap_closed"]) else "N/A"
        brk_str = "Yes" if p["total_Adaptive"] < p["total_SBS"] else "not_observed"
        t6_rows.append([
            f"Q={q}",
            f"{p['total_SBS']*1e3:.3f}",
            f"{p['total_Adaptive']*1e3:.3f}",
            f"{p['total_VBS']*1e3:.3f}",
            f"{p['adaptive_minus_SBS']*1e3:.3f}",
            f"{p['adaptive_ratio_to_SBS']:.3f}",
            gap_str,
            brk_str,
        ])
    generated_files.extend(_save_table(t6_headers, t6_rows, "table06_workload_crossover", out_path))

    # --- Table 7: Selector accuracy and near-best accuracy ---
    t7_headers = ["Metric", "Value"]
    t7_rows = [
        ["Total Test Queries", str(selector_eval.num_queries)],
        ["Exact Selection Accuracy", f"{selector_eval.exact_accuracy * 100:.2f}%"],
        [f"Near-Best Accuracy (ε={selector_eval.epsilon})", f"{selector_eval.near_best_accuracy * 100:.2f}%"],
        ["Mean Selection Time", f"{selector_eval.mean_selection_time * 1e6:.2f} μs"],
        ["Mean Feature Time", f"{selector_eval.mean_feature_time * 1e6:.2f} μs"],
    ]
    generated_files.extend(_save_table(t7_headers, t7_rows, "table07_selector_accuracy", out_path))

    return generated_files
