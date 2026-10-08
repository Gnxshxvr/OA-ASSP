"""Figures for the corrected OA-ASSP experiment."""

from __future__ import annotations
import math
from pathlib import Path
from typing import Any, Dict, List, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from oa_assp.analysis.capture import CaptureAnalysisResult  # noqa: E402


def _save(fig, out_dir: Path, name: str) -> List[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    png = out_dir / f"{name}.png"
    pdf = out_dir / f"{name}.pdf"
    fig.savefig(png, dpi=160, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")
    plt.close(fig)
    return [str(png), str(pdf)]


def _q_axis(capture: CaptureAnalysisResult) -> List[int]:
    return sorted(capture.aggregate_points)


def fig_cost_vs_q(capture: CaptureAnalysisResult, out_dir: Path) -> List[str]:
    qs = _q_axis(capture)
    sbs = [capture.aggregate_points[q]["total_SBS"] * 1e3 for q in qs]
    vbs = [capture.aggregate_points[q]["total_VBS"] * 1e3 for q in qs]
    ad = [capture.aggregate_points[q]["total_Adaptive_task"] * 1e3 for q in qs]

    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.plot(qs, sbs, "o-", label="SBS (training-derived fixed policy)")
    ax.plot(qs, vbs, "s-", label="VBS (per-instance oracle)")
    ax.plot(qs, ad, "^-", label="Adaptive (measured end to end)")
    ax.set_xscale("log")
    ax.set_xlabel("workload size Q (queries per graph)")
    ax.set_ylabel("cumulative cost over test graphs (ms)")
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(fontsize=8)
    fig.tight_layout()
    return _save(fig, out_dir, "fig_c1_cost_vs_Q")


def fig_capture_vs_required(capture: CaptureAnalysisResult, out_dir: Path) -> List[str]:
    qs = _q_axis(capture)
    cap = [capture.aggregate_points[q]["CaptureRate_task"] for q in qs]
    req = [capture.aggregate_points[q]["RequiredCapture_task"] for q in qs]

    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.axhline(1.0, color="grey", linestyle=":", linewidth=1)
    ax.plot(qs, cap, "o-", label="measured capture rate")
    ax.plot(qs, req, "s-", label="required capture rate (overhead / oracle gap)")
    ax.set_xscale("log")
    ax.set_yscale("symlog", linthresh=1.0)
    ax.set_xlabel("workload size Q (queries per graph)")
    ax.set_ylabel("fraction of oracle gap")
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(fontsize=8)
    ax.set_title("Adaptive selection pays for itself where capture >= required", fontsize=9)
    fig.tight_layout()
    return _save(fig, out_dir, "fig_c2_capture_vs_required")


def fig_overhead_decomposition(capture: CaptureAnalysisResult, out_dir: Path) -> List[str]:
    qs = _q_axis(capture)
    gf = [capture.aggregate_points[q]["total_graph_feature"] * 1e3 for q in qs]
    qf = [capture.aggregate_points[q]["total_query_feature"] * 1e3 for q in qs]
    sl = [capture.aggregate_points[q]["total_selection"] * 1e3 for q in qs]

    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    x = np.arange(len(qs))
    ax.bar(x, gf, label="graph features (once per graph)")
    ax.bar(x, qf, bottom=gf, label="query features (per query)")
    ax.bar(x, sl, bottom=np.array(gf) + np.array(qf), label="selector inference (per query)")
    ax.set_xticks(x)
    ax.set_xticklabels([str(q) for q in qs])
    ax.set_xlabel("workload size Q")
    ax.set_ylabel("selection overhead (ms)")
    ax.legend(fontsize=8)
    ax.grid(True, axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()
    return _save(fig, out_dir, "fig_c3_overhead_decomposition")


def fig_tier_economics(tier_rows: Sequence[Dict[str, Any]], out_dir: Path) -> List[str]:
    labels = [f"Tier {r['tier']}\n({r['feature_count']} feats)" for r in tier_rows]
    req = [r.get("analysis_grade_required_capture_Q500", r["RequiredCapture_Q500"]) for r in tier_rows]
    cap = [r.get("analysis_grade_solver_capture_Q500", r["CaptureRate_Q500"]) for r in tier_rows]
    req_compiled = [r.get("compiled_analysis_grade_required_capture_Q500", float("nan")) for r in tier_rows]

    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    x = np.arange(len(labels))
    ax.bar(x - 0.27, req, width=0.27, label="required capture (library inference)")
    ax.bar(x, req_compiled, width=0.27, label="required capture (compiled rules)")
    ax.bar(x + 0.27, cap, width=0.27, label="achievable solver capture")
    ax.axhline(0.0, color="black", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("fraction of oracle gap")
    ax.legend(fontsize=8)
    ax.grid(True, axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()
    return _save(fig, out_dir, "fig_c4_tier_economics")


def fig_selector_vs_baselines(
    generality_rows: Sequence[Dict[str, Any]], baseline_rows: Sequence[Dict[str, Any]], out_dir: Path
) -> List[str]:
    protocols = ["standard_held_out", "leave_one_cell_out", "leave_one_family_out"]
    accs, majs, names = [], [], []
    for proto in protocols:
        sub = [r for r in generality_rows if r["protocol"] == proto]
        if not sub:
            continue
        accs.append(float(np.median([r["exact_accuracy"] for r in sub])) * 100)
        majs.append(float(np.median([r["majority_exact_accuracy"] for r in sub])) * 100)
        names.append(proto.replace("_", " "))

    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    x = np.arange(len(names))
    ax.bar(x - 0.2, accs, width=0.4, label="decision tree")
    ax.bar(x + 0.2, majs, width=0.4, label="majority label (train-derived)")
    ax.set_xticks(x)
    ax.set_xticklabels(names, fontsize=8)
    ax.set_ylabel("exact-winner accuracy (%)")
    ax.legend(fontsize=8)
    ax.grid(True, axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()
    return _save(fig, out_dir, "fig_c5_selector_vs_majority")


def fig_per_graph_delta(capture: CaptureAnalysisResult, out_dir: Path) -> List[str]:
    points = [p for p in capture.graph_points if p.Q == 500]
    points.sort(key=lambda p: p.AdaptiveMinusSBS)
    labels = [p.graph_id for p in points]
    deltas = [p.AdaptiveMinusSBS * 1e3 for p in points]

    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    colors = ["tab:green" if d < 0 else "tab:red" for d in deltas]
    ax.barh(np.arange(len(labels)), deltas, color=colors)
    ax.set_yticks(np.arange(len(labels)))
    ax.set_yticklabels(labels, fontsize=7)
    ax.axvline(0.0, color="black", linewidth=0.8)
    ax.set_xlabel("Adaptive − SBS at Q=500 (ms)")
    ax.grid(True, axis="x", linestyle="--", alpha=0.4)
    fig.tight_layout()
    return _save(fig, out_dir, "fig_c6_per_graph_delta")


def fig_tuning(tuning_rows: Sequence[Dict[str, Any]], out_dir: Path) -> List[str]:
    depth = [int(r["max_depth"]) for r in tuning_rows]
    leaf = [int(r["min_samples_leaf"]) for r in tuning_rows]
    obj = [float(r["val_objective"]) * 1e3 for r in tuning_rows]
    sel = [bool(r["is_selected"]) for r in tuning_rows]

    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    sc = ax.scatter(depth, obj, c=leaf, cmap="viridis", s=40)
    for x, y, s in zip(depth, obj, sel):
        if s:
            ax.scatter([x], [y], facecolors="none", edgecolors="red", s=180, linewidths=2)
    ax.set_xlabel("max_depth")
    ax.set_ylabel("validation objective (ms)")
    cb = fig.colorbar(sc, ax=ax)
    cb.set_label("min_samples_leaf", fontsize=8)
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.set_title("validation-only selector selection (red = selected)", fontsize=9)
    fig.tight_layout()
    return _save(fig, out_dir, "fig_c7_selector_tuning")


def fig_reconciliation(pass_totals: Sequence[Dict[str, Any]], out_dir: Path) -> List[str]:
    wall = [float(t["adaptive_wall_clock"]) * 1e3 for t in pass_totals]
    comp = [float(t["component_sum"]) * 1e3 for t in pass_totals]
    diff = [w - c for w, c in zip(wall, comp)]

    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.scatter(comp, diff, s=14, alpha=0.6)
    ax.axhline(0.0, color="black", linewidth=0.8)
    ax.set_xlabel("component sum (ms) per workload pass")
    ax.set_ylabel("end-to-end wall clock − component sum (ms)")
    ax.set_title("measurement reconciliation per adaptive workload pass", fontsize=9)
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.tight_layout()
    return _save(fig, out_dir, "fig_c8_reconciliation")


def fig_analysis_grade(
    capture_hybrid: CaptureAnalysisResult,
    capture_compiled: CaptureAnalysisResult,
    out_dir: Path,
) -> List[str]:
    """Analysis-grade economics: measured overhead, benchmark-median solver costs.

    Two inference modalities are overlaid because the per-query selection charge is the
    single largest difference between them, and the whole question is whether that charge
    is worth paying.
    """
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.0))

    ax = axes[0]
    for cap, label, style in ((capture_hybrid, "library inference", "o-"),
                              (capture_compiled, "compiled rules", "s--")):
        qs = _q_axis(cap)
        ax.plot(qs, [cap.aggregate_points[q]["total_Adaptive"] * 1e3 for q in qs], style,
                label=f"Adaptive ({label})")
        ax.plot(qs, [cap.aggregate_points[q]["total_SBS"] * 1e3 for q in qs], ":", alpha=0.7,
                label=f"SBS ({label} run)")
        ax.plot(qs, [cap.aggregate_points[q]["total_VBS"] * 1e3 for q in qs], "-.", alpha=0.7,
                label=f"VBS ({label} run)")
    ax.set_xscale("log")
    ax.set_xlabel("workload size Q")
    ax.set_ylabel("cumulative cost (ms)")
    ax.set_title("analysis-grade variant", fontsize=9)
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(fontsize=6)

    ax = axes[1]
    for cap, label, style in ((capture_hybrid, "library inference", "o-"),
                              (capture_compiled, "compiled rules", "s--")):
        qs = _q_axis(cap)
        ax.plot(qs, [cap.aggregate_points[q]["RequiredCapture_e2e"] for q in qs], style,
                label=f"required ({label})")
        ax.plot(qs, [cap.aggregate_points[q]["SolverOnlyCapture"] for q in qs], ":", alpha=0.7,
                label=f"achievable ({label})")
    ax.set_xscale("log")
    ax.set_yscale("symlog", linthresh=0.01)
    ax.set_xlabel("workload size Q")
    ax.set_ylabel("fraction of oracle gap")
    ax.set_title("required vs achievable capture", fontsize=9)
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(fontsize=6)
    fig.tight_layout()
    return _save(fig, out_dir, "fig_c9_analysis_grade")


def generate_corrected_figures(
    output_dir: Path,
    capture: CaptureAnalysisResult,
    tier_rows: Sequence[Dict[str, Any]],
    tuning_rows: Sequence[Dict[str, Any]],
    generality_rows: Sequence[Dict[str, Any]],
    baseline_rows: Sequence[Dict[str, Any]],
    pass_totals: Sequence[Dict[str, Any]],
    primary_tier: int = 1,
    capture_hybrid: Any = None,
    capture_compiled_hybrid: Any = None,
) -> List[str]:
    """Generate every corrected-experiment figure."""
    out = Path(output_dir)
    files: List[str] = []
    files += fig_cost_vs_q(capture, out)
    files += fig_capture_vs_required(capture, out)
    files += fig_overhead_decomposition(capture, out)
    files += fig_tier_economics(tier_rows, out)
    files += fig_selector_vs_baselines(generality_rows, baseline_rows, out)
    files += fig_per_graph_delta(capture, out)
    files += fig_tuning(tuning_rows, out)
    pt = [t for t in pass_totals if int(t["tier"]) == int(primary_tier) and str(t.get("mode", "library")) == "library"]
    if pt:
        files += fig_reconciliation(pt, out)
    if capture_hybrid is not None and capture_compiled_hybrid is not None:
        files += fig_analysis_grade(capture_hybrid, capture_compiled_hybrid, out)
    return files
