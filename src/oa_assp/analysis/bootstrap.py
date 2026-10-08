"""Graph-level bootstrap statistical analysis and hypothesis testing."""

from __future__ import annotations
import csv
from dataclasses import dataclass, asdict
import math
import numpy as np
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from oa_assp.benchmark.oracle import OracleSummary
from oa_assp.selector.dataset import DatasetSplit
from oa_assp.selector.decision_tree import QuerySelectionResult


@dataclass
class BootstrapMetricCI:
    """Point estimate and confidence interval for a bootstrap metric."""

    metric_name: str
    point_estimate: float
    ci_lower: float
    ci_upper: float
    confidence_level: float
    std_error: float
    num_replicates: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BootstrapAnalysisResult:
    """Complete summary of graph-level bootstrap evaluation."""

    gap_closed_ci: BootstrapMetricCI
    adaptive_minus_sbs_ci: BootstrapMetricCI
    adaptive_ratio_sbs_ci: BootstrapMetricCI
    h5_supported: bool  # True if GapClosed CI lower bound > 0
    h5_interpretation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gap_closed": self.gap_closed_ci.to_dict(),
            "adaptive_minus_sbs": self.adaptive_minus_sbs_ci.to_dict(),
            "adaptive_ratio_sbs": self.adaptive_ratio_sbs_ci.to_dict(),
            "h5_supported": self.h5_supported,
            "h5_interpretation": self.h5_interpretation,
        }


def run_graph_level_bootstrap(
    query_results: List[QuerySelectionResult],
    oracle_summary: OracleSummary,
    test_split: DatasetSplit,
    num_replicates: int = 1000,
    confidence_level: float = 0.95,
    seed: int = 4001,
) -> BootstrapAnalysisResult:
    """Perform graph-level bootstrap resampling to compute 95% CIs.

    Resamples whole graphs with replacement, keeping all queries of each graph intact.
    """
    rng = np.random.default_rng(seed)

    # Group results and oracle instances by graph_id
    by_graph_results: Dict[str, List[QuerySelectionResult]] = {}
    for qr in query_results:
        by_graph_results.setdefault(qr.graph_id, []).append(qr)

    by_graph_meta: Dict[str, List[Dict[str, Any]]] = {}
    for m in test_split.metadata:
        by_graph_meta.setdefault(m["graph_id"], []).append(m)

    unique_graphs = sorted(list(by_graph_results.keys()))
    n_graphs = len(unique_graphs)
    if n_graphs == 0:
        raise ValueError("Cannot run bootstrap on empty test split.")

    # 1. Compute original point estimates
    def _compute_metrics(sampled_gids: List[str]) -> Tuple[float, float, float]:
        tot_adaptive = 0.0
        tot_sbs = 0.0
        tot_vbs = 0.0

        for gid in sampled_gids:
            q_res_list = by_graph_results.get(gid, [])
            meta_list = by_graph_meta.get(gid, [])
            if meta_list:
                tot_adaptive += meta_list[0].get("graph_feature_time", 0.0)

            for qr, meta in zip(q_res_list, meta_list):
                inst = meta["oracle_instance"]
                # Adaptive cost = feature + selection + solver
                c_adapt = qr.feature_time + qr.selection_time + qr.selected_solver_runtime
                tot_adaptive += c_adapt

                # SBS cost
                if oracle_summary.sbs_policy == "Always-Dijkstra":
                    c_sbs = inst.always_dijkstra_cost
                elif oracle_summary.sbs_policy == "Always-Bidirectional-Dijkstra":
                    c_sbs = inst.always_bidi_cost
                else:
                    c_sbs = inst.always_astar_cost
                tot_sbs += c_sbs

                # VBS cost
                tot_vbs += inst.vbs_cost

        diff = tot_adaptive - tot_sbs
        ratio = (tot_adaptive / tot_sbs) if tot_sbs > 0 else 1.0

        gap = tot_sbs - tot_vbs
        if abs(gap) < 1e-12:
            gap_closed = math.nan
        else:
            gap_closed = (tot_sbs - tot_adaptive) / gap

        return gap_closed, diff, ratio

    orig_gap, orig_diff, orig_ratio = _compute_metrics(unique_graphs)

    # 2. Resample graphs with replacement
    boot_gaps = []
    boot_diffs = []
    boot_ratios = []

    for _ in range(num_replicates):
        sampled_gids = list(rng.choice(unique_graphs, size=n_graphs, replace=True))
        g_val, d_val, r_val = _compute_metrics(sampled_gids)
        if not math.isnan(g_val):
            boot_gaps.append(g_val)
        boot_diffs.append(d_val)
        boot_ratios.append(r_val)

    alpha = 1.0 - confidence_level
    low_pct = (alpha / 2.0) * 100.0
    high_pct = (1.0 - alpha / 2.0) * 100.0

    # GapClosed CI
    if boot_gaps:
        gap_arr = np.array(boot_gaps, dtype=float)
        gap_ci = BootstrapMetricCI(
            metric_name="GapClosed",
            point_estimate=orig_gap,
            ci_lower=float(np.percentile(gap_arr, low_pct)),
            ci_upper=float(np.percentile(gap_arr, high_pct)),
            confidence_level=confidence_level,
            std_error=float(np.std(gap_arr)),
            num_replicates=len(boot_gaps),
        )
    else:
        gap_ci = BootstrapMetricCI("GapClosed", math.nan, math.nan, math.nan, confidence_level, 0.0, 0)

    # Adaptive - SBS CI
    diff_arr = np.array(boot_diffs, dtype=float)
    diff_ci = BootstrapMetricCI(
        metric_name="Adaptive - SBS",
        point_estimate=orig_diff,
        ci_lower=float(np.percentile(diff_arr, low_pct)),
        ci_upper=float(np.percentile(diff_arr, high_pct)),
        confidence_level=confidence_level,
        std_error=float(np.std(diff_arr)),
        num_replicates=len(boot_diffs),
    )

    # Adaptive / SBS CI
    ratio_arr = np.array(boot_ratios, dtype=float)
    ratio_ci = BootstrapMetricCI(
        metric_name="Adaptive / SBS",
        point_estimate=orig_ratio,
        ci_lower=float(np.percentile(ratio_arr, low_pct)),
        ci_upper=float(np.percentile(ratio_arr, high_pct)),
        confidence_level=confidence_level,
        std_error=float(np.std(ratio_arr)),
        num_replicates=len(boot_ratios),
    )

    # Hypothesis H5 test: GapClosed > 0 with CI strictly positive
    h5_supported = bool((not math.isnan(gap_ci.ci_lower)) and (gap_ci.ci_lower > 0.0))
    if h5_supported:
        h5_msg = "Hypothesis H5 is SUPPORTED: 95% CI for GapClosed is strictly positive."
    elif (not math.isnan(gap_ci.point_estimate)) and gap_ci.point_estimate > 0:
        h5_msg = "Hypothesis H5 is NOT CONCLUSIVE: point estimate is positive but CI includes zero/negative."
    else:
        h5_msg = "Hypothesis H5 is NOT SUPPORTED: point estimate is negative or zero."

    return BootstrapAnalysisResult(
        gap_closed_ci=gap_ci,
        adaptive_minus_sbs_ci=diff_ci,
        adaptive_ratio_sbs_ci=ratio_ci,
        h5_supported=h5_supported,
        h5_interpretation=h5_msg,
    )


def save_bootstrap_results(result: BootstrapAnalysisResult, output_csv: Union[str, Path]) -> str:
    """Save bootstrap metrics and confidence intervals to CSV."""
    path = Path(output_csv)
    path.parent.mkdir(parents=True, exist_ok=True)

    metrics = [
        result.gap_closed_ci.to_dict(),
        result.adaptive_minus_sbs_ci.to_dict(),
        result.adaptive_ratio_sbs_ci.to_dict(),
    ]

    field_names = list(metrics[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=field_names)
        writer.writeheader()
        for m in metrics:
            writer.writerow(m)

    return str(path)
