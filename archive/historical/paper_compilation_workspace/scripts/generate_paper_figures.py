"""Generate publication-quality IEEE-style figures for the OA-ASSP conference paper."""

import os
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

# IEEE style configuration
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif", "Times"],
    "font.size": 7.5,
    "axes.labelsize": 7.5,
    "axes.titlesize": 8.0,
    "xtick.labelsize": 7.0,
    "ytick.labelsize": 7.0,
    "legend.fontsize": 6.5,
    "figure.titlesize": 8.5,
    "lines.linewidth": 1.1,
    "lines.markersize": 4.0,
    "grid.alpha": 0.35,
    "grid.linestyle": "--",
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})

OUT_DIR = Path("paper/figures")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def save_fig(fig, name):
    pdf_path = OUT_DIR / f"{name}.pdf"
    png_path = OUT_DIR / f"{name}.png"
    fig.savefig(pdf_path, bbox_inches="tight", dpi=300)
    fig.savefig(png_path, bbox_inches="tight", dpi=300)
    plt.close(fig)
    print(f"Saved {pdf_path} and {png_path}")

# ==============================================================================
# FIGURE 1: OA-ASSP Selection Pipeline
# ==============================================================================
def make_fig1_pipeline():
    fig, ax = plt.subplots(figsize=(3.4, 1.8))
    ax.axis("off")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)

    # Styles
    box_blue = dict(boxstyle="square,pad=0.25", fc="#E8F0FE", ec="#1A73E8", lw=0.9)
    box_green = dict(boxstyle="square,pad=0.25", fc="#E6F4EA", ec="#137333", lw=0.9)
    box_yellow = dict(boxstyle="square,pad=0.25", fc="#FEF7E0", ec="#EA8600", lw=0.9)
    box_purple = dict(boxstyle="square,pad=0.25", fc="#F3E8FD", ec="#8430CE", lw=0.9)
    arrow = dict(arrowstyle="->", lw=0.8, color="#333333")

    # 1. Resident Graph
    ax.text(28, 93, "Resident Graph $G=(V, E, w)$\nOne-Time: $C_{\\mathrm{feat}}^{\\mathrm{graph}}$ (Amortized / $Q$)",
            ha="center", va="center", bbox=box_blue, fontsize=6.0)

    # 2. Query
    ax.text(78, 93, "Incoming Query\n$q_i = (s_i, t_i)$, $i \\in [1, Q]$",
            ha="center", va="center", bbox=box_yellow, fontsize=6.0)

    # 3. Query Feature Extraction
    ax.text(50, 75, "Per-Query Features ($C_{\\mathrm{feat}}^{\\mathrm{query}}$): Degree, Distance",
            ha="center", va="center", bbox=box_yellow, fontsize=6.2)

    # Arrows to Feature Extraction
    ax.annotate("", xy=(38, 78), xytext=(28, 87), arrowprops=arrow)
    ax.annotate("", xy=(62, 78), xytext=(78, 87), arrowprops=arrow)

    # 4. Selector Inference Box
    ax.text(50, 56, "Decision Tree Selector ($C_{\\mathrm{sel}}$)\n"
                    "• Library Mode: $\\approx 87.9\\,\\mu\\mathrm{s}$ | • Compiled Mode: $\\approx 0.8\\,\\mu\\mathrm{s}$",
            ha="center", va="center", bbox=box_purple, fontsize=6.0)
    ax.annotate("", xy=(50, 61), xytext=(50, 70), arrowprops=arrow)

    # 5. Selected Solver Execution
    ax.text(50, 37, "Selected Solver $t(A^*; G, q_i)$ (Dijkstra | Bidi | $A^*$)",
            ha="center", va="center", bbox=box_green, fontsize=6.2)
    ax.annotate("", xy=(50, 42), xytext=(50, 50), arrowprops=arrow)

    # 6. Overhead Accounting & Headroom Debit
    ax.text(50, 18, "Overhead Accounting vs Headroom:\n"
                    "$C_{\\mathrm{query}} = C_{\\mathrm{feat}}^{\\mathrm{query}} + C_{\\mathrm{sel}} + t(A^*) + C_{\\mathrm{feat}}^{\\mathrm{graph}}/Q$",
            ha="center", va="center", bbox=box_blue, fontsize=6.0)
    ax.annotate("", xy=(50, 24), xytext=(50, 31), arrowprops=arrow)

    # Net Viability Condition
    ax.text(50, 4, "Break-Even: $\\mathrm{SolverOnlyCapture}(Q) > \\mathrm{RequiredCapture}(Q)$",
            ha="center", va="center", fontsize=6.2, fontweight="bold", color="#B06000")

    fig.tight_layout()
    save_fig(fig, "fig1_pipeline")

# ==============================================================================
# FIGURE 2: SBS / VBS / Adaptive cost across Q
# ==============================================================================
def make_fig2_cost_vs_q():
    fig, ax = plt.subplots(figsize=(3.4, 1.35))
    
    Q = np.array([1, 10, 50, 100, 500])
    sbs = np.array([1.362, 22.775, 108.448, 223.777, 1064.200])
    vbs = np.array([1.350, 20.016, 94.738, 198.342, 941.677])
    adaptive_lib = np.array([11.452, 42.184, 161.211, 328.120, 1556.250])
    adaptive_comp = np.array([10.048, 32.512, 121.425, 241.847, 1119.723])

    ax.plot(Q, adaptive_lib, "o-", color="#D93025", label="Adaptive (Library)")
    ax.plot(Q, adaptive_comp, "s-", color="#E37400", label="Adaptive (Compiled)")
    ax.plot(Q, sbs, "^--", color="#1A73E8", label="SBS (Fixed Baseline)")
    ax.plot(Q, vbs, "v:", color="#188038", label="VBS (Oracle Lower Bound)")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xticks(Q)
    ax.set_xticklabels(["1", "10", "50", "100", "500"])
    ax.set_xlabel("Workload Size $Q$")
    ax.set_ylabel("Runtime (ms)")
    ax.grid(True, which="both", linestyle="--", alpha=0.35)
    ax.legend(fontsize=5.8, loc="upper left", framealpha=0.85)
    
    fig.tight_layout()
    save_fig(fig, "fig2_cost_vs_q")

# ==============================================================================
# FIGURE 3: RequiredCapture versus workload Q
# ==============================================================================
def make_fig3_required_capture():
    fig, ax = plt.subplots(figsize=(3.4, 1.35))
    
    Q = np.array([1, 10, 50, 100, 500])
    req_lib = np.array([847.89, 6.85, 3.73, 3.94, 3.85])
    req_comp = np.array([729.90, 3.34, 0.83, 0.55, 0.29])

    ax.plot(Q, req_lib, "o-", color="#D93025", label="Library ReqCap")
    ax.plot(Q, req_comp, "s-", color="#137333", label="Compiled ReqCap")
    ax.axhline(1.0, color="#5F6368", linestyle=":", linewidth=1.1, label="Break-Even ($=1.0$)")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xticks(Q)
    ax.set_xticklabels(["1", "10", "50", "100", "500"])
    ax.set_xlabel("Workload Size $Q$")
    ax.set_ylabel("RequiredCapture Ratio")
    ax.grid(True, which="both", linestyle="--", alpha=0.35)
    
    ax.axhspan(0.1, 1.0, facecolor="#E6F4EA", alpha=0.45, zorder=0)
    ax.text(25, 0.35, "Viable Zone (< 1.0)", fontsize=6.0, color="#137333", ha="center")
    
    ax.legend(fontsize=5.8, loc="upper right", framealpha=0.85)
    fig.tight_layout()
    save_fig(fig, "fig3_required_capture")

# ==============================================================================
# FIGURE 4: Library versus compiled overhead economics (Q=500)
# ==============================================================================
def make_fig4_overhead_economics():
    fig, ax = plt.subplots(figsize=(3.4, 1.4))
    
    categories = ["Oracle\nGap", "Library\nOverhead", "Compiled\nOverhead", "Solver\nLoss"]
    values = [122.52, 472.04, 35.51, 20.01]
    colors = ["#1A73E8", "#D93025", "#188038", "#EA8600"]
    
    bars = ax.bar(categories, values, color=colors, width=0.52, edgecolor="#333333", lw=0.5)
    
    ax.text(0, 122.52 + 8, "122.5 ms\n(100%)", ha="center", va="bottom", fontsize=6.0)
    ax.text(1, 472.04 + 8, "472.0 ms\n(385%)", ha="center", va="bottom", fontsize=6.0, color="#D93025")
    ax.text(2, 35.51 + 8, "35.5 ms\n(29%)", ha="center", va="bottom", fontsize=6.0, color="#188038")
    ax.text(3, 20.01 + 8, "+20.0 ms\n(Regret)", ha="center", va="bottom", fontsize=6.0, color="#EA8600")

    ax.set_ylabel("Runtime at $Q=500$ (ms)")
    ax.set_ylim(0, 560)
    ax.grid(True, axis="y", linestyle="--", alpha=0.35)

    fig.tight_layout()
    save_fig(fig, "fig4_overhead_economics")

# ==============================================================================
# FIGURE 5: Selector accuracy versus majority baseline
# ==============================================================================
def make_fig5_selector_accuracy():
    fig, ax = plt.subplots(figsize=(3.4, 1.35))
    
    protocols = ["Held-Out", "LOCO (24)", "LOFO (3)"]
    selector_acc = [72.50, 80.80, 79.09]
    majority_acc = [72.60, 77.95, 83.45]
    
    x = np.arange(len(protocols))
    width = 0.32
    
    ax.bar(x - width/2, selector_acc, width, label="Decision Tree", color="#1A73E8", edgecolor="#333333", lw=0.5)
    ax.bar(x + width/2, majority_acc, width, label="Majority Policy", color="#9AA0A6", edgecolor="#333333", lw=0.5)
    
    ax.set_ylabel("Exact Accuracy (%)")
    ax.set_xticks(x)
    ax.set_xticklabels(protocols, fontsize=7.0)
    ax.set_ylim(60, 95)
    ax.grid(True, axis="y", linestyle="--", alpha=0.35)
    ax.legend(fontsize=5.8, loc="upper left", framealpha=0.85)
    
    lifts = ["-0.10 pp", "+0.00 pp", "+0.00 pp"]
    for i, lift in enumerate(lifts):
        y_pos = max(selector_acc[i], majority_acc[i]) + 1.5
        ax.text(x[i], y_pos, lift, ha="center", va="bottom", fontsize=6.0, fontweight="bold", color="#333333")

    fig.tight_layout()
    save_fig(fig, "fig5_selector_accuracy")

# ==============================================================================
# FIGURE 6: Per-graph Adaptive - SBS at Q=500
# ==============================================================================
def make_fig6_per_graph_delta():
    fig, ax = plt.subplots(figsize=(3.4, 1.5))
    
    graphs = [
        "geom_V320_D12",
        "geom_V160_D6",
        "scale_V160_D12",
        "geom_V40_D12",
        "rand_V320_D6",
        "rand_V80_D12",
        "rand_V40_D6",
        "scale_V80_D6"
    ]
    lib_deltas = np.array([103.97, 69.25, 68.65, 64.21, 63.57, 47.90, 37.67, 36.84])
    comp_deltas = np.array([27.64, -0.35, 17.64, 4.96, 3.23, -1.49, 3.87, 5.58])
    
    y = np.arange(len(graphs))
    height = 0.36
    
    ax.barh(y + height/2, lib_deltas, height, label="Library Mode", color="#D93025", alpha=0.85, edgecolor="#333333", lw=0.4)
    ax.barh(y - height/2, comp_deltas, height, label="Compiled Mode", color="#188038", alpha=0.85, edgecolor="#333333", lw=0.4)
    
    ax.axvline(0, color="black", linewidth=0.8)
    ax.axvspan(-2.5, 0, color="#F1F3F4", alpha=0.8, zorder=0)
    
    ax.set_yticks(y)
    ax.set_yticklabels(graphs, fontsize=6.2)
    ax.set_xlabel("$\\Delta = C_{\\mathrm{Adaptive}}^{\\mathrm{task}} - C_{\\mathrm{SBS}}$ (ms)")
    ax.set_xlim(-10, 115)
    ax.grid(True, axis="x", linestyle="--", alpha=0.35)
    ax.legend(fontsize=5.8, loc="upper right", framealpha=0.85)
    
    fig.tight_layout()
    save_fig(fig, "fig6_per_graph_delta")

if __name__ == "__main__":
    print("Generating conference paper figures (compact)...")
    make_fig1_pipeline()
    make_fig2_cost_vs_q()
    make_fig3_required_capture()
    make_fig4_overhead_economics()
    make_fig5_selector_accuracy()
    make_fig6_per_graph_delta()
    print("Done.")
