"""Publication-quality figure generation for OA-ASSP benchmark and selector."""

from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np

from oa_assp.analysis.bootstrap import BootstrapAnalysisResult
from oa_assp.analysis.feature_tiers import TierEvaluationSummary
from oa_assp.analysis.workload import WorkloadAnalysisResult
from oa_assp.benchmark.runner import BenchmarkRow
from oa_assp.selector.decision_tree import SelectorEvaluationResult


# Publication plotting styling
plt.rcParams.update({
    "font.size": 11,
    "font.family": "serif",
    "axes.labelsize": 12,
    "axes.titlesize": 13,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 10,
    "figure.titlesize": 14,
    "figure.dpi": 300,
    "savefig.dpi": 300,
})


def generate_all_figures(
    benchmark_rows: List[Dict[str, Any]],
    workload_res: WorkloadAnalysisResult,
    tier_summaries: List[TierEvaluationSummary],
    selector_eval: SelectorEvaluationResult,
    output_dir: Union[str, Path] = "results/figures",
) -> List[str]:
    """Generate and save all 10 required publication-quality figures."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    generated_files: List[str] = []

    def _save_fig(fig: plt.Figure, name: str) -> None:
        png_file = out_path / f"{name}.png"
        pdf_file = out_path / f"{name}.pdf"
        fig.tight_layout()
        fig.savefig(png_file)
        fig.savefig(pdf_file)
        plt.close(fig)
        generated_files.extend([str(png_file), str(pdf_file)])

    # --- Figure 1: Algorithm runtime vs graph size V ---
    fig, ax = plt.subplots(figsize=(6, 4))
    v_vals = sorted(list({int(r["V"]) for r in benchmark_rows if r.get("success")}))
    for algo in ["Dijkstra", "Bidirectional Dijkstra", "A*"]:
        runtimes = []
        for v in v_vals:
            times = [
                float(r["runtime_median"]) * 1e3
                for r in benchmark_rows
                if r["algorithm"] == algo and int(r["V"]) == v and r.get("success")
            ]
            runtimes.append(float(np.mean(times)) if times else 0.0)
        ax.plot(v_vals, runtimes, marker="o", label=algo)
    ax.set_xlabel("Number of Vertices (V)")
    ax.set_ylabel("Median Runtime (ms)")
    ax.set_title("Figure 1: Algorithm Runtime vs Graph Size")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.5)
    _save_fig(fig, "fig01_runtime_vs_size")

    # --- Figure 2: Runtime vs average degree ---
    fig, ax = plt.subplots(figsize=(6, 4))
    d_vals = sorted(list({round(float(r["actual_average_degree"])) for r in benchmark_rows if r.get("success")}))
    for algo in ["Dijkstra", "Bidirectional Dijkstra", "A*"]:
        runtimes = []
        for d in d_vals:
            times = [
                float(r["runtime_median"]) * 1e3
                for r in benchmark_rows
                if r["algorithm"] == algo and round(float(r["actual_average_degree"])) == d and r.get("success")
            ]
            runtimes.append(float(np.mean(times)) if times else 0.0)
        ax.plot(d_vals, runtimes, marker="s", label=algo)
    ax.set_xlabel("Average Degree (d)")
    ax.set_ylabel("Median Runtime (ms)")
    ax.set_title("Figure 2: Runtime vs Average Degree")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.5)
    _save_fig(fig, "fig02_runtime_vs_degree")

    # --- Figure 3: A* performance vs heuristic-quality proxy ---
    fig, ax = plt.subplots(figsize=(6, 4))
    geom_rows = [r for r in benchmark_rows if r.get("weight_model") == "geometric" and r["algorithm"] == "A*"]
    if geom_rows:
        hq_vals = [float(r.get("query_distance_value", 0.0)) for r in geom_rows]
        exp_nodes = [int(r.get("nodes_expanded", 0)) for r in geom_rows]
        ax.scatter(hq_vals, exp_nodes, color="teal", alpha=0.7, edgecolors="none")
        ax.set_xlabel("Source-Target Distance")
        ax.set_ylabel("Nodes Expanded")
    else:
        ax.text(0.5, 0.5, "No geometric instances with heuristic", ha="center", va="center")
    ax.set_title("Figure 3: A* Performance vs Heuristic Quality")
    ax.grid(True, linestyle="--", alpha=0.5)
    _save_fig(fig, "fig03_astar_vs_heuristic_quality")

    # --- Figure 4: Feature extraction cost vs feature tier ---
    fig, ax = plt.subplots(figsize=(6, 4))
    tier_names = [s.tier_name for s in tier_summaries]
    g_costs = [s.mean_graph_feature_time * 1e6 for s in tier_summaries]
    q_costs = [s.mean_query_feature_time * 1e6 for s in tier_summaries]
    x = np.arange(len(tier_names))
    width = 0.35
    ax.bar(x - width/2, g_costs, width, label="Graph Feature Time (μs)")
    ax.bar(x + width/2, q_costs, width, label="Query Feature Time (μs)")
    ax.set_xticks(x)
    ax.set_xticklabels(tier_names, rotation=15)
    ax.set_ylabel("Mean Overhead (μs)")
    ax.set_title("Figure 4: Feature Extraction Overhead by Tier")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.5)
    _save_fig(fig, "fig04_feature_cost_vs_tier")

    # --- Figure 5: Selection accuracy vs feature tier ---
    fig, ax = plt.subplots(figsize=(6, 4))
    exact_accs = [s.exact_accuracy * 100 for s in tier_summaries]
    near_accs = [s.near_best_accuracy * 100 for s in tier_summaries]
    ax.plot(tier_names, exact_accs, marker="o", label="Exact Accuracy (%)", color="navy")
    ax.plot(tier_names, near_accs, marker="^", label="Near-Best Accuracy (ε=0.05) (%)", color="crimson")
    ax.set_ylabel("Accuracy (%)")
    ax.set_ylim(0, 105)
    ax.set_title("Figure 5: Selection Accuracy vs Feature Tier")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.5)
    _save_fig(fig, "fig05_accuracy_vs_tier")

    # --- Figure 6: GapClosed vs feature tier ---
    fig, ax = plt.subplots(figsize=(6, 4))
    gaps = [s.gap_closed if not np.isnan(s.gap_closed) else 0.0 for s in tier_summaries]
    colors = ["green" if g >= 0 else "red" for g in gaps]
    ax.bar(tier_names, gaps, color=colors, width=0.4)
    ax.axhline(0.0, color="black", linestyle="-", linewidth=0.8)
    ax.set_ylabel("GapClosed Ratio")
    ax.set_title("Figure 6: GapClosed vs Feature Tier")
    ax.grid(True, linestyle="--", alpha=0.5)
    _save_fig(fig, "fig06_gap_closed_vs_tier")

    # --- Figure 7: Total adaptive cost vs Q (crossover analysis) ---
    fig, ax = plt.subplots(figsize=(6, 4))
    q_keys = sorted(list(workload_res.aggregate_points.keys()))
    sbs_costs = [workload_res.aggregate_points[q]["total_SBS"] * 1e3 for q in q_keys]
    adapt_costs = [workload_res.aggregate_points[q]["total_Adaptive"] * 1e3 for q in q_keys]
    vbs_costs = [workload_res.aggregate_points[q]["total_VBS"] * 1e3 for q in q_keys]
    ax.plot(q_keys, sbs_costs, label="SBS (Fixed Policy)", color="black", linestyle="--")
    ax.plot(q_keys, adapt_costs, label="OA-ASSP (Adaptive)", color="blue", marker="o")
    ax.plot(q_keys, vbs_costs, label="VBS (Oracle)", color="green", linestyle=":")
    if workload_res.aggregate_break_even_Q is not None:
        ax.axvline(workload_res.aggregate_break_even_Q, color="purple", linestyle="-.", label=f"Crossover (Q={workload_res.aggregate_break_even_Q})")
    ax.set_xlabel("Query Workload Size (Q)")
    ax.set_ylabel("Cumulative Workload Cost (ms)")
    ax.set_title("Figure 7: Cumulative Cost vs Workload Size Q")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.5)
    _save_fig(fig, "fig07_total_cost_vs_Q_crossover")

    # --- Figure 8: SBS vs Adaptive vs VBS ---
    fig, ax = plt.subplots(figsize=(6, 4))
    max_q = max(q_keys) if q_keys else 1
    final_pts = workload_res.aggregate_points.get(max_q, {})
    labels = ["SBS (Fixed)", "OA-ASSP (Adaptive)", "VBS (Oracle)"]
    totals = [
        final_pts.get("total_SBS", 0.0) * 1e3,
        final_pts.get("total_Adaptive", 0.0) * 1e3,
        final_pts.get("total_VBS", 0.0) * 1e3,
    ]
    ax.bar(labels, totals, color=["gray", "royalblue", "forestgreen"], width=0.4)
    ax.set_ylabel(f"Total Cost at Q={max_q} (ms)")
    ax.set_title("Figure 8: Aggregate Workload Cost Comparison")
    ax.grid(True, linestyle="--", alpha=0.5)
    _save_fig(fig, "fig08_sbs_vs_adaptive_vs_vbs")

    # --- Figure 9: Operation counts ---
    fig, ax = plt.subplots(figsize=(6, 4))
    op_algos = ["Dijkstra", "Bidirectional Dijkstra", "A*"]
    mean_relax = []
    mean_expanded = []
    for algo in op_algos:
        r_list = [int(r["relaxations"]) for r in benchmark_rows if r["algorithm"] == algo and r.get("success")]
        e_list = [int(r["nodes_expanded"]) for r in benchmark_rows if r["algorithm"] == algo and r.get("success")]
        mean_relax.append(float(np.mean(r_list)) if r_list else 0.0)
        mean_expanded.append(float(np.mean(e_list)) if e_list else 0.0)
    x = np.arange(len(op_algos))
    ax.bar(x - 0.2, mean_relax, 0.4, label="Mean Relaxations", color="darkorange")
    ax.bar(x + 0.2, mean_expanded, 0.4, label="Mean Nodes Expanded", color="steelblue")
    ax.set_xticks(x)
    ax.set_xticklabels(op_algos, rotation=10)
    ax.set_ylabel("Operation Count")
    ax.set_title("Figure 9: Operation Counts by Algorithm")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.5)
    _save_fig(fig, "fig09_operation_counts")

    # --- Figure 10: Selector confusion matrix ---
    fig, ax = plt.subplots(figsize=(6, 5))
    classes = ["Dijkstra", "Bidirectional Dijkstra", "A*"]
    matrix = np.zeros((len(classes), len(classes)), dtype=int)
    for qr in selector_eval.query_results:
        if qr.actual_vbs_algorithm in classes and qr.selected_algorithm in classes:
            i = classes.index(qr.actual_vbs_algorithm)
            j = classes.index(qr.selected_algorithm)
            matrix[i, j] += 1
    cax = ax.matshow(matrix, cmap="Blues")
    fig.colorbar(cax)
    ax.set_xticks(range(len(classes)))
    ax.set_yticks(range(len(classes)))
    ax.set_xticklabels(classes, rotation=20)
    ax.set_yticklabels(classes)
    ax.set_xlabel("Predicted Algorithm")
    ax.set_ylabel("Actual VBS Algorithm")
    ax.set_title("Figure 10: Selector Confusion Matrix", pad=20)
    for i in range(len(classes)):
        for j in range(len(classes)):
            ax.text(j, i, str(matrix[i, j]), ha="center", va="center", color="black")
    _save_fig(fig, "fig10_selector_confusion_matrix")

    return generated_files
