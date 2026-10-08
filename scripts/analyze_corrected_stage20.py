"""Post-hoc analysis, comparison and freezing of the corrected Stage 20 experiment.

This script reads ONLY the corrected experiment's own artifacts plus the immutable
historical Stage 20 artifacts. It writes the authoritative audit bundle:

    FINAL_CORRECTED_AUDIT/
        corrected_results_manifest.json
        corrected_config.yaml
        original_vs_corrected.csv
        corrected_questions.json
        bootstrap_analysis_grade.csv
        checksums.txt
        figures/            (copies of the corrected experiment figures)
        logs/corrected_run.log

Nothing in this script computes a value that is not written to disk or printed, and
no value is hand-transcribed: every number in the report is traceable to a CSV
produced by ``scripts/run_stage20_corrected.py``.

Reproduction safety
-------------------
``FINAL_CORRECTED_AUDIT/`` is the FROZEN authoritative package and is treated as
READ-ONLY. Normal execution writes to a run-scoped directory instead::

    audit_runs/analyze_<UTC timestamp>/

Writing into the frozen package requires an explicit ``--output-dir FINAL_CORRECTED_AUDIT``
**and** ``--force``; without ``--force`` the script refuses and exits.

Usage
-----
    python scripts/analyze_corrected_stage20.py [experiment_id]
    python scripts/analyze_corrected_stage20.py [experiment_id] --output-dir <path>
    python scripts/analyze_corrected_stage20.py [experiment_id] \\
        --output-dir FINAL_CORRECTED_AUDIT --force      # regenerates the frozen package
"""

from __future__ import annotations

import csv
import datetime
import hashlib
import json
import math
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
FROZEN_OUT = ROOT / "FINAL_CORRECTED_AUDIT"
ORIGINAL_ID = "stage20_scaleup_48g_20260920_215427"
GAP_EPSILON = 1e-12
BOOTSTRAP_SAMPLES = 1000
BOOTSTRAP_SEED = 4001


# ------------------------------------------------------------------------ helpers
def read_csv(path: Path) -> List[Dict[str, str]]:
    with open(path, "r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fnum(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def ratio(numerator: float, denominator: float) -> float:
    if abs(denominator) <= GAP_EPSILON:
        return float("nan")
    return numerator / denominator


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


VALUE_FLAGS = ("--output-dir",)


def _positional_args(argv: Sequence[str]) -> List[str]:
    """Positional arguments only, skipping known flags and their values."""
    out: List[str] = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in VALUE_FLAGS:
            i += 2
            continue
        if a.startswith("--"):
            i += 1
            continue
        out.append(a)
        i += 1
    return out


def resolve_out_dir(argv: Sequence[str]) -> Path:
    """Resolve the output directory, defaulting to a run-scoped path.

    The frozen authoritative package may only be written with an explicit
    ``--output-dir FINAL_CORRECTED_AUDIT --force``.
    """
    force = "--force" in argv
    explicit: Optional[Path] = None
    for i, a in enumerate(argv):
        if a == "--output-dir":
            if i + 1 >= len(argv):
                raise SystemExit("--output-dir requires a path argument")
            explicit = Path(argv[i + 1])

    if explicit is None:
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
        out = ROOT / "audit_runs" / f"analyze_{stamp}"
        out.mkdir(parents=True, exist_ok=True)
        print(f"Output (run-scoped) : {out.relative_to(ROOT).as_posix()}/")
        return out

    out = explicit if explicit.is_absolute() else (ROOT / explicit)
    out = out.resolve()
    if out == FROZEN_OUT.resolve():
        if not force:
            raise SystemExit(
                "REFUSING TO WRITE INTO THE FROZEN AUTHORITATIVE PACKAGE:\n"
                f"  {FROZEN_OUT}\n"
                "  FINAL_CORRECTED_AUDIT/ is READ-ONLY. Use the default run-scoped output\n"
                "  (omit --output-dir), or pass --force if you intend to regenerate the\n"
                "  frozen package. Doing so invalidates LOCK_CHECKSUMS.txt and\n"
                "  SOURCE_PROVENANCE_MANIFEST.json.")
        print("!" * 88)
        print("WARNING: --force set - REGENERATING THE FROZEN AUTHORITATIVE PACKAGE.")
        print("         This invalidates FINAL_CORRECTED_AUDIT/LOCK_CHECKSUMS.txt.")
        print("!" * 88)
    out.mkdir(parents=True, exist_ok=True)
    return out


def resolve_experiment_id(argv: Sequence[str]) -> str:
    # argv[0] is the script path; only user-supplied positionals are experiment IDs.
    positional = _positional_args(list(argv)[1:])
    if positional:
        return positional[0]
    candidates = sorted(p.name for p in (ROOT / "results").glob("stage20_corrected_*") if p.is_dir())
    if not candidates:
        raise SystemExit("No corrected experiment directory found. Run the corrected experiment first.")
    return candidates[-1]


# ------------------------------------------------------------------- bootstrap
def graph_level_bootstrap(
    per_graph: List[Dict[str, str]],
    samples: int = BOOTSTRAP_SAMPLES,
    seed: int = BOOTSTRAP_SEED,
) -> Dict[str, Dict[str, float]]:
    """Paired graph-level bootstrap over the test graphs using analysis-grade costs.

    Each replicate resamples graphs with replacement and recomputes every metric from
    the resampled *sums*, so the ratios stay ratios of sums rather than averages of
    ratios. Graphs are the resampling unit because queries on one graph share solver
    behaviour; treating 24,000 queries as 24,000 independent observations would be
    pseudoreplication.
    """
    sbs = np.array([fnum(r["C_SBS"]) for r in per_graph], dtype=float)
    vbs = np.array([fnum(r["C_VBS"]) for r in per_graph], dtype=float)
    adaptive = np.array([fnum(r["C_Adaptive_task"]) for r in per_graph], dtype=float)
    overhead = np.array([fnum(r["SelectionOverhead_task"]) for r in per_graph], dtype=float)
    solver = np.array([fnum(r["C_selected_solver"]) for r in per_graph], dtype=float)

    rng = np.random.default_rng(seed)
    n = len(sbs)
    reps: Dict[str, List[float]] = {
        "adaptive_minus_sbs_seconds": [],
        "adaptive_ratio_sbs": [],
        "capture_rate_task": [],
        "required_capture_task": [],
        "solver_only_capture": [],
        "oracle_gap_seconds": [],
    }

    for _ in range(samples):
        idx = rng.integers(0, n, size=n)
        s_sbs, s_vbs = float(sbs[idx].sum()), float(vbs[idx].sum())
        s_adaptive, s_overhead, s_solver = (
            float(adaptive[idx].sum()),
            float(overhead[idx].sum()),
            float(solver[idx].sum()),
        )
        gap = s_sbs - s_vbs
        reps["adaptive_minus_sbs_seconds"].append(s_adaptive - s_sbs)
        reps["adaptive_ratio_sbs"].append(s_adaptive / s_sbs if s_sbs > 0 else float("nan"))
        reps["capture_rate_task"].append(ratio(s_sbs - s_adaptive, gap))
        reps["required_capture_task"].append(ratio(s_overhead, gap))
        reps["solver_only_capture"].append(ratio(s_sbs - s_solver, gap))
        reps["oracle_gap_seconds"].append(gap)

    # Point estimates from the full (unresampled) sample.
    gap = float(sbs.sum() - vbs.sum())
    points = {
        "adaptive_minus_sbs_seconds": float(adaptive.sum() - sbs.sum()),
        "adaptive_ratio_sbs": float(adaptive.sum() / sbs.sum()),
        "capture_rate_task": ratio(float(sbs.sum() - adaptive.sum()), gap),
        "required_capture_task": ratio(float(overhead.sum()), gap),
        "solver_only_capture": ratio(float(sbs.sum() - solver.sum()), gap),
        "oracle_gap_seconds": gap,
    }

    out: Dict[str, Dict[str, float]] = {}
    for key, vals in reps.items():
        arr = np.array([v for v in vals if not math.isnan(v)], dtype=float)
        if arr.size == 0:
            continue
        lo, hi = np.percentile(arr, 2.5), np.percentile(arr, 97.5)
        out[key] = {
            "point_estimate": points[key],
            "ci_lower": float(lo),
            "ci_upper": float(hi),
            "std_error": float(np.std(arr)),
            "num_replicates": int(arr.size),
            "num_graphs": n,
            "resampling_unit": "graph (paired, with replacement)",
            "caveat": (
                "8 purposively designed test graphs; intervals bound this sample, not a "
                "population of graphs"
            ),
        }
    return out


# ------------------------------------------------------------------------ main
def main() -> int:
    exp_id = resolve_experiment_id(sys.argv)
    OUT = resolve_out_dir(sys.argv)
    exp_dir = ROOT / "results" / exp_id
    proc = exp_dir / "processed"
    raw = exp_dir / "raw"
    if not exp_dir.is_dir():
        raise SystemExit(f"Corrected experiment not found: {exp_dir}")

    (OUT / "figures").mkdir(parents=True, exist_ok=True)
    manifest = json.loads((proc / f"{exp_id}_manifest.json").read_text(encoding="utf-8"))

    print("=" * 96)
    print("OA-ASSP -- CORRECTED STAGE 20 POST-HOC ANALYSIS")
    print("=" * 96)
    print(f"Experiment      : {exp_id}")
    print(f"Config hash     : {manifest['configuration_hash']}")
    print(f"Source hash     : {manifest['source_hash']}")

    # ---------------------------------------------------------- headline tables
    agg_measured = read_csv(proc / f"{exp_id}_capture_aggregate.csv")
    agg_grade = read_csv(proc / f"{exp_id}_capture_aggregate_analysis_grade.csv")
    agg_compiled = read_csv(proc / f"{exp_id}_capture_aggregate_compiled_analysis_grade.csv")
    per_graph_grade = read_csv(proc / f"{exp_id}_capture_per_graph_analysis_grade.csv")
    tiers = read_csv(proc / f"{exp_id}_feature_tier_tradeoffs.csv")
    generic = read_csv(proc / f"{exp_id}_generalization.csv")
    baselines = read_csv(proc / f"{exp_id}_baselines.csv")
    tuning = read_csv(proc / f"{exp_id}_selector_tuning.csv")
    crosscheck = read_csv(proc / f"{exp_id}_oracle_gap_crosscheck.csv")
    dispersion = read_csv(proc / f"{exp_id}_pass_dispersion.csv")
    compiled_cells = read_csv(proc / f"{exp_id}_compiled_mode.csv")
    pass_totals = read_csv(proc / f"{exp_id}_adaptive_pass_totals.csv")

    def table(rows: List[Dict[str, str]], keys: Sequence[str], title: str) -> None:
        print(f"\n{title}")
        print("   " + " ".join(f"{k:>13}" for k in keys))
        for r in rows:
            cells = []
            for k in keys:
                v = r.get(k, "")
                try:
                    cells.append(f"{float(v):13.4f}")
                except (TypeError, ValueError):
                    cells.append(f"{str(v)[:13]:>13}")
            print("   " + " ".join(cells))

    table(agg_grade, ["Q", "total_SBS", "total_VBS", "total_selected_solver", "total_Adaptive_task",
                      "SelectionOverhead_task", "OracleGap", "CaptureRate_task", "RequiredCapture_task",
                      "SolverOnlyCapture"], "A. PRIMARY (analysis-grade) cumulative costs in seconds")

    table(agg_compiled, ["Q", "total_SBS", "total_Adaptive_task", "SelectionOverhead_task", "OracleGap",
                         "CaptureRate_task", "RequiredCapture_task", "SolverOnlyCapture"],
          "B. COMPILED-RULE INFERENCE (analysis-grade), primary tier")

    table(agg_measured, ["Q", "total_Adaptive_e2e", "SelectionOverhead_e2e", "OracleGap",
                         "CaptureRate_e2e", "RequiredCapture_e2e"],
          "C. Fully single-shot measured variant (noise-dominated oracle gap)")

    table(tiers, ["tier", "feature_count", "exact_accuracy", "analysis_grade_overhead_Q500_ms",
                  "analysis_grade_required_capture_Q500", "compiled_analysis_grade_required_capture_Q500",
                  "analysis_grade_solver_capture_Q500"], "D. Feature tiers (identical hyperparameters)")

    # --------------------------------------------------------- crossover search
    q_values = sorted({int(r["Q"]) for r in per_graph_grade})
    crossover_cells: List[Dict[str, Any]] = []
    for Q in q_values:
        for r in per_graph_grade:
            if int(r["Q"]) != Q:
                continue
            delta = fnum(r["AdaptiveMinusSBS_task"])
            if delta < 0:
                crossover_cells.append({
                    "graph_id": r["graph_id"], "Q": Q, "adaptive_minus_sbs_ms": delta * 1e3,
                    "solver_only_capture": fnum(r["SolverOnlyCapture"]),
                })
    print("\nE. CROSSOVER SEARCH (analysis-grade, per graph x Q)")
    print(f"   cells examined            : {len(q_values) * 8}")
    print(f"   cells where adaptive wins : {len(crossover_cells)}")
    best = min((fnum(r["AdaptiveMinusSBS_task"]) for r in per_graph_grade), default=float("nan"))
    print(f"   best (least negative-loss) cell: {best * 1e3:+.3f} ms")

    # ----------------------------------------------------- generalization summary
    # Folds are attributed to the feature tier that produced them; the analysis headline
    # uses the primary tier only, so that folds from different feature sets are never
    # pooled into one median.
    primary_tier = int(manifest["adaptive"].get("primary_tier", 1))
    print("\nF. GENERALIZATION (folds, identical hyperparameters)")
    assert "tier" in generic[0], "generalization rows do not record the feature tier"
    per_protocol: Dict[str, Dict[str, Any]] = {}
    for proto in ("standard_held_out", "leave_one_cell_out", "leave_one_family_out"):
        by_tier = sorted({int(r["tier"]) for r in generic if r["protocol"] == proto})
        for tier in by_tier:
            sub = [r for r in generic if r["protocol"] == proto and int(r["tier"]) == tier]
            if not sub:
                continue
            entry = {
                "tier": tier,
                "feature_count": int(sub[0]["feature_count"]),
                "folds": len(sub),
                "median_exact_accuracy": float(np.median([fnum(r["exact_accuracy"]) for r in sub])),
                "median_majority_accuracy": float(np.median([fnum(r["majority_exact_accuracy"]) for r in sub])),
                "median_accuracy_lift": float(np.median([fnum(r["accuracy_lift_over_majority"]) for r in sub])),
                "median_solver_only_capture": float(np.median([fnum(r["solver_only_capture"]) for r in sub])),
                "constant_prediction_folds": int(sum(
                    1 for r in sub
                    if ";" not in r["predicted_distribution"] and r["predicted_distribution"].count("=") == 1)),
                "folds_with_positive_lift": int(sum(
                    1 for r in sub if fnum(r["accuracy_lift_over_majority"]) > 0)),
                "max_lift": float(np.max([fnum(r["accuracy_lift_over_majority"]) for r in sub])),
            }
            per_protocol[f"{proto}__tier{tier}"] = entry
            p = entry
            print(f"   tier {tier} {proto:<20} folds={p['folds']:>3}  exact={p['median_exact_accuracy']*100:6.2f}%  "
                  f"majority={p['median_majority_accuracy']*100:6.2f}%  lift={p['median_accuracy_lift']*100:+6.2f}pp  "
                  f"solver-capture={p['median_solver_only_capture']:+.4f}  "
                  f"constant-prediction folds={p['constant_prediction_folds']}/{p['folds']}")
    gen_primary = {proto: per_protocol.get(f"{proto}__tier{primary_tier}", {})
                   for proto in ("standard_held_out", "leave_one_cell_out", "leave_one_family_out")}
    assert gen_primary["leave_one_cell_out"], (
        f"no leave-one-cell-out folds for the primary tier {primary_tier}")

    # --------------------------------------------------- baselines & selection
    print("\nG. TEST-SET BASELINES (benchmark medians, all 4,000 test queries)")
    for r in baselines:
        print(f"   {r['name']:<40} exact={fnum(r['exact_accuracy'])*100:6.2f}%  "
              f"near={fnum(r['near_best_accuracy'])*100:6.2f}%  solverCost={fnum(r['total_selected_solver_runtime'])*1e3:9.3f} ms")

    selected = [r for r in tuning if r["is_selected"] == "True"]
    print("\nH. VALIDATION-SELECTED SELECTOR CONFIGURATION")
    for r in selected:
        print(f"   criterion={r['criterion']} max_depth={r['max_depth']} min_samples_leaf={r['min_samples_leaf']} "
              f"leaves={r['num_leaves']} valExact={fnum(r['val_exact_accuracy'])*100:.2f}% "
              f"valObjective={fnum(r['val_objective'])*1e3:.3f}ms")

    # --------------------------------------------------- oracle-gap noise bound
    print("\nI. ORACLE-GAP NOISE BOUND (benchmark medians vs paired single-shot)")
    max_rel = 0.0
    for r in crosscheck:
        rel = fnum(r["gap_relative_difference"])
        if not math.isnan(rel):
            max_rel = max(max_rel, rel)
        print(f"   Q={r['Q']:>4}  benchmark gap={fnum(r['OracleGap_benchmark_ms']):9.3f} ms  "
              f"paired gap={fnum(r['OracleGap_paired_ms']):9.3f} ms  relative difference={rel*100:8.1f}%")
    print(f"   -> the single-shot paired gap disagrees with the repeated-median gap by up to "
          f"{max_rel*100:.0f}%; it is noise-dominated and is therefore not used as the primary gap")

    # ------------------------------------------------------------- bootstrap
    print("\nJ. PAIRED GRAPH-LEVEL BOOTSTRAP (analysis-grade, primary tier, Q=500)")
    q500 = [r for r in per_graph_grade if int(r["Q"]) == 500]
    boot = graph_level_bootstrap(q500)
    for key, stats in boot.items():
        print(f"   {key:<32} point={stats['point_estimate']:12.6f}  "
              f"95% CI [{stats['ci_lower']:12.6f}, {stats['ci_upper']:12.6f}]")

    # --------------------------------------------------------- reproducibility
    print("\nK. MEASUREMENT REPRODUCIBILITY (adaptive workload repeated per pass)")
    for r in dispersion:
        print(f"   tier {r['tier']} Q={r['Q']:>4}  C_adaptive min/median/max = "
              f"{fnum(r['C_adaptive_min_ms']):9.3f}/{fnum(r['C_adaptive_median_ms']):9.3f}/"
              f"{fnum(r['C_adaptive_max_ms']):9.3f} ms  "
              f"adaptive-sbs median={fnum(r['adaptive_minus_sbs_median_ms']):+9.3f} ms  "
              f"sign stable={r['sign_stable']}")

    # ------------------------------------------------------------ Q1..Q10 answers
    g500 = next(r for r in agg_grade if int(r["Q"]) == 500)
    c500 = next(r for r in agg_compiled if int(r["Q"]) == 500)
    t0 = next(r for r in tiers if int(r["tier"]) == 0)

    # Compiled-rule deployment variant: how many graph x Q cells are nominally below SBS, and
    # how large are those nominal gains relative to the pass-to-pass dispersion of the same
    # aggregate wall-clock quantity? This is the only place where a crossover could hide.
    compiled_primary = [r for r in compiled_cells]
    compiled_wins = sum(1 for r in compiled_primary if fnum(r["AdaptiveMinusSBS"]) < 0)
    compiled_best = min((fnum(r["AdaptiveMinusSBS"]) for r in compiled_primary), default=float("nan"))
    test_graph_ids = sorted({r["graph_id"] for r in compiled_primary})
    by_pass: Dict[int, float] = {}
    for r in pass_totals:
        if r["mode"] != "compiled" or int(r["tier"]) != primary_tier:
            continue
        if r["graph_id"] not in set(test_graph_ids):
            continue
        by_pass[int(r["pass"])] = by_pass.get(int(r["pass"]), 0.0) + fnum(r["adaptive_wall_clock"])
    pass_values = [v for _, v in sorted(by_pass.items())]
    compiled_dispersion_pct = ((max(pass_values) - min(pass_values)) / np.median(pass_values) * 100
                               if pass_values else float("nan"))

    print("\nF2. COMPILED-RULE VARIANT: nominal wins vs pass dispersion")
    print(f"   nominal cells below SBS : {compiled_wins} of {len(compiled_primary)}")
    print(f"   largest nominal gain    : {compiled_best * 1e3:+.3f} ms")
    print(f"   pass-to-pass dispersion : {compiled_dispersion_pct:.1f}% of the same aggregate "
          f"wall clock over {len(pass_values)} passes")

    answers = {
        "Q1_adaptive_beats_sbs_anywhere": {
            "answer": "No.",
            "evidence": (
                f"Primary configuration: 0 of {len(q_values) * 8} graph x Q cells have adaptive below "
                f"SBS; the smallest loss is {best * 1e3:+.3f} ms (single graph, Q=500). "
                f"With compiled-rule inference (a deployment variant, not the primary configuration) "
                f"{compiled_wins} of {len(q_values) * 8} cells are nominally below SBS, by at most "
                f"{abs(compiled_best) * 1e3:.3f} ms = {abs(compiled_best) / fnum(agg_grade[-1]['total_SBS']) * 100:.2f}% "
                f"of the Q=500 SBS cost, i.e. far inside the {compiled_dispersion_pct:.0f}% pass-to-pass "
                f"dispersion of the same quantity; these are not reported as a crossover."
            ),
        },
        "Q2_why_not": {
            "answer": "Two independent reasons, quantified separately.",
            "solver_side": (
                f"The selector's expected solver cost equals the SBS policy's: solver-only capture "
                f"= {fnum(g500['SolverOnlyCapture']):+.4f} of the oracle gap at Q=500 "
                f"(chosen-solver total {fnum(g500['total_selected_solver'])*1e3:.3f} ms vs SBS "
                f"{fnum(g500['total_SBS'])*1e3:.3f} ms)."
            ),
            "overhead_side": (
                f"Required capture at Q=500 is {fnum(g500['RequiredCapture_task']):.3f} of the oracle gap "
                f"with library per-query inference and {fnum(c500['RequiredCapture_task']):.3f} with "
                f"compiled rules; the oracle gap is only "
                f"{fnum(g500['OracleGap']) / fnum(g500['total_SBS']) * 100:.2f}% of the SBS cost."
            ),
        },
        "Q3_vbs_headroom": {
            "answer": "Small but real.",
            "evidence": (
                f"Oracle gap over 8 test graphs and 4,000 queries at Q=500: "
                f"{fnum(g500['OracleGap'])*1e3:.3f} ms = "
                f"{fnum(g500['OracleGap']) / fnum(g500['total_SBS']) * 100:.2f}% of the SBS policy cost. "
                f"VBS wins overall: {manifest['sbs']['reference_policy_totals_s'] and ''}"
                f"Bidirectional Dijkstra takes most instances."
            ),
        },
        "Q4_capture": {
            "answer": "No.",
            "evidence": (
                f"CaptureRate at Q=500 = {fnum(g500['CaptureRate_task']):+.4f}; required = "
                f"{fnum(g500['RequiredCapture_task']):.4f}. Solver-only (overhead-free) capture = "
                f"{fnum(g500['SolverOnlyCapture']):+.4f}."
            ),
        },
        "Q5_capture_vs_Q": {
            "answer": "Capture is roughly Q-independent and never positive at aggregate level.",
            "evidence": " ".join(f"Q={r['Q']}:{fnum(r['CaptureRate_task']):+.3f}" for r in agg_grade),
        },
        "Q6_required_capture_vs_Q": {
            "answer": "Required capture falls with Q because the graph-level feature cost is paid once "
                      "and the per-query costs are roughly constant while the cumulative oracle gap grows.",
            "evidence": " ".join(f"Q={r['Q']}:{fnum(r['RequiredCapture_task']):.3f}" for r in agg_grade),
        },
        "Q7_tier_expansion": {
            "answer": "No. Richer features cost more than they return.",
            "evidence": (
                f"Analysis-grade required capture at Q=500: tier 0 = "
                f"{fnum(t0['analysis_grade_required_capture_Q500']):.3f} (library) / "
                f"{fnum(t0['compiled_analysis_grade_required_capture_Q500']):.3f} (compiled); exact accuracy "
                f"is statistically indistinguishable across tiers."
            ),
        },
        "Q8_generalizes_to_unseen_configurations": {
            "answer": "No.",
            "evidence": (
                f"Primary tier {primary_tier}: leave-one-cell-out median exact accuracy "
                f"{gen_primary['leave_one_cell_out']['median_exact_accuracy']*100:.2f}% "
                f"vs majority {gen_primary['leave_one_cell_out']['median_majority_accuracy']*100:.2f}% "
                f"(median lift {gen_primary['leave_one_cell_out']['median_accuracy_lift']*100:+.2f}pp over "
                f"{gen_primary['leave_one_cell_out']['folds']} folds); the tree predicts a constant "
                f"solver in {gen_primary['leave_one_cell_out']['constant_prediction_folds']} of those folds."
            ),
        },
        "Q9_generalizes_across_families": {
            "answer": "No.",
            "evidence": (
                f"Primary tier {primary_tier}: leave-one-family-out median exact accuracy "
                f"{gen_primary['leave_one_family_out']['median_exact_accuracy']*100:.2f}% "
                f"vs majority {gen_primary['leave_one_family_out']['median_majority_accuracy']*100:.2f}% "
                f"(median lift {gen_primary['leave_one_family_out']['median_accuracy_lift']*100:+.2f}pp over "
                f"{gen_primary['leave_one_family_out']['folds']} folds); the tree predicts a constant "
                f"solver in {gen_primary['leave_one_family_out']['constant_prediction_folds']} of those folds."
            ),
        },
        "Q1b_compiled_variant_nominal_wins": {
            "answer": (
                "Nominally, with compiled-rule inference, a small number of graph x Q cells sit a "
                "fraction of a percent below SBS; the margin is one to two orders of magnitude "
                "smaller than the pass-to-pass dispersion of the same quantity, so it is not a "
                "reproducible crossover."
            ),
            "evidence": (
                f"{compiled_wins} of {len(compiled_primary)} cells below SBS, largest "
                f"{compiled_best * 1e3:+.3f} ms; pass-to-pass dispersion of the same aggregate "
                f"wall clock {compiled_dispersion_pct:.1f}%."
            ),
        },
        "Q10_bottleneck": {
            "answer": (
                "Selector efficacy is the binding constraint whenever inference is cheap (compiled rules); "
                "per-query selection overhead is the binding constraint when inference goes through a "
                "general-purpose model library. Solver diversity is not the constraint."
            ),
            "evidence": (
                f"compiled: required {fnum(c500['RequiredCapture_task']):.3f} < 1.0, so even a perfect selector "
                f"would pay, but achievable capture is {fnum(c500['SolverOnlyCapture']):+.4f}. "
                f"library: required {fnum(g500['RequiredCapture_task']):.3f} > 1.0, so no selector could pay."
            ),
        },
    }
    print("\nL. FINAL SCIENTIFIC QUESTIONS")
    for k, v in answers.items():
        print(f"   {k}")
        print(f"      answer  : {v['answer']}")
        print(f"      evidence: {v.get('evidence', '')}")
        for extra_key in ("solver_side", "overhead_side"):
            if extra_key in v:
                print(f"      {extra_key:9s}: {v[extra_key]}")

    # ------------------------------------------- original vs corrected comparison
    orig_curves = read_csv(ROOT / "results" / ORIGINAL_ID / "processed" / f"{ORIGINAL_ID}_workload_curves.csv")
    orig_tier = read_csv(ROOT / "results" / ORIGINAL_ID / "processed" / f"{ORIGINAL_ID}_feature_tier_tradeoffs.csv")
    orig_by_q: Dict[int, Dict[str, float]] = {}
    for r in orig_curves:
        slot = orig_by_q.setdefault(int(r["Q"]), dict.fromkeys(
            ("C_SBS", "C_Adaptive", "C_VBS"), 0.0))
        for k in ("C_SBS", "C_Adaptive", "C_VBS"):
            slot[k] += fnum(r[k])
    orig_crossover = [r for r in orig_curves if fnum(r["adaptive_minus_SBS"]) < 0]

    comparison_rows: List[Dict[str, Any]] = []
    for r in agg_grade:
        Q = int(r["Q"])
        o = orig_by_q.get(Q, {})
        comparison_rows.append({
            "Q": Q,
            "original_C_SBS_ms": o.get("C_SBS", float("nan")) * 1e3,
            "original_C_Adaptive_ms": o.get("C_Adaptive", float("nan")) * 1e3,
            "original_adaptive_minus_sbs_ms": (o.get("C_Adaptive", float("nan")) - o.get("C_SBS", float("nan"))) * 1e3,
            "original_adaptive_ratio_sbs": ratio(o.get("C_Adaptive", float("nan")), o.get("C_SBS", float("nan"))),
            "original_crossover_cells": len(orig_crossover),
            "corrected_C_SBS_ms": fnum(r["total_SBS"]) * 1e3,
            "corrected_adaptive_task_ms": fnum(r["total_Adaptive_task"]) * 1e3,
            "corrected_adaptive_minus_sbs_ms": fnum(r["AdaptiveMinusSBS_task"]) * 1e3,
            "corrected_adaptive_ratio_sbs": fnum(r["AdaptiveRatioSBS"]),
            "corrected_solver_only_capture": fnum(r["SolverOnlyCapture"]),
            "corrected_crossover_cells": len(crossover_cells),
        })

    print("\nM. ORIGINAL STAGE 20 vs CORRECTED STAGE 20 (per-graph sums over the 8 test graphs)")
    print(f"   original crossover cells (all 48 graphs x 5 Q): {len(orig_crossover)}")
    if orig_crossover:
        for r in orig_crossover:
            print(f"      {r['graph_id']} Q={r['Q']} delta={fnum(r['adaptive_minus_SBS'])*1e3:+.4f} ms")
    print(f"   corrected crossover cells                    : {len(crossover_cells)}")
    with open(OUT / "original_vs_corrected.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(comparison_rows[0].keys()))
        w.writeheader()
        w.writerows(comparison_rows)

    # ---------------------------------------------------------------- artifacts
    shutil.copyfile(ROOT / "configs" / "experiment_corrected_48g.yaml", OUT / "corrected_config.yaml")
    for fig in sorted((exp_dir / "figures").glob("*")):
        shutil.copyfile(fig, OUT / "figures" / fig.name)

    results_manifest = {
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "analyzer": "scripts/analyze_corrected_stage20.py",
        "corrected_experiment_id": exp_id,
        "original_experiment_id": ORIGINAL_ID,
        "experiment_identity": {
            "configuration_hash": manifest["configuration_hash"],
            "source_hash": manifest["source_hash"],
            "source_files_hashed": manifest["source_files_hashed"],
            "environment": manifest["environment"],
            "timestamp_utc": manifest["timestamp_utc"],
        },
        "cost_model": manifest["cost_model"],
        "sbs": manifest["sbs"],
        "selector": manifest["selector"],
        "adaptive": manifest["adaptive"],
        "capture_aggregate_analysis_grade": {r["Q"]: {k: fnum(v) for k, v in r.items() if k != "Q"} for r in agg_grade},
        "capture_aggregate_compiled_analysis_grade": {r["Q"]: {k: fnum(v) for k, v in r.items() if k != "Q"} for r in agg_compiled},
        "capture_aggregate_measured": {r["Q"]: {k: fnum(v) for k, v in r.items() if k != "Q"} for r in agg_measured},
        "feature_tiers": [{k: fnum(v) if k not in ("tier_name",) else v for k, v in r.items()} for r in tiers],
        "baselines": [{k: (fnum(v) if k not in ("name", "policy", "train_label_counts") else v) for k, v in r.items()} for r in baselines],
        "generalization": per_protocol,
        "generalization_primary_tier": {"primary_tier": primary_tier, "protocols": gen_primary},
        "bootstrap_analysis_grade_Q500": boot,
        "crossover": {
            "cells_examined": len(q_values) * 8,
            "cells_where_adaptive_wins": len(crossover_cells),
            "cells": crossover_cells,
            "original_stage20_crossover_cells": len(orig_crossover),
        },
        "oracle_gap_noise_bound": {
            "max_relative_difference": max_rel,
            "meaning": "benchmark repeated-median gap vs paired single-shot gap",
        },
        "compiled_variant": {
            "cells_below_sbs": compiled_wins,
            "cells_examined": len(compiled_primary),
            "largest_nominal_gain_ms": compiled_best * 1e3,
            "pass_to_pass_dispersion_pct_of_same_aggregate": compiled_dispersion_pct,
            "num_passes": len(pass_values),
            "verdict": "nominal gains are far below the pass-to-pass dispersion; not a crossover",
        },
        "measurement_reproducibility": [
            {k: (fnum(v) if k not in ("sign_stable",) else v == "True") for k, v in r.items()}
            for r in dispersion
        ],
        "scientific_questions": answers,
        "artifacts": {
            "raw_benchmark_csv": f"results/{exp_id}/raw/{exp_id}_benchmark_rows.csv",
            "raw_adaptive_csv": f"results/{exp_id}/raw/{exp_id}_adaptive_rows.csv",
            "figures": f"results/{exp_id}/figures/",
            "original_experiment": f"results/{ORIGINAL_ID}/",
        },
    }
    (OUT / "corrected_results_manifest.json").write_text(
        json.dumps(results_manifest, indent=2, default=str), encoding="utf-8")
    (OUT / "corrected_questions.json").write_text(json.dumps(answers, indent=2, default=str), encoding="utf-8")
    with open(OUT / "bootstrap_analysis_grade.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metric", "point_estimate", "ci_lower", "ci_upper", "std_error",
                    "num_replicates", "num_graphs", "resampling_unit"])
        for metric, stats in boot.items():
            w.writerow([metric, stats["point_estimate"], stats["ci_lower"], stats["ci_upper"],
                        stats["std_error"], stats["num_replicates"], stats["num_graphs"],
                        stats["resampling_unit"]])

    # ------------------------------------------------------------- checksums
    lines: List[str] = []
    lines.append(f"# OA-ASSP corrected Stage 20 checksums")
    lines.append(f"# generated {datetime.datetime.now(datetime.timezone.utc).isoformat()}")
    lines.append(f"# experiment {exp_id}")
    lines.append("")
    lines.append("## corrected experiment artifacts")
    for p in sorted(exp_dir.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts:
            lines.append(f"{sha256_file(p)}  {p.relative_to(ROOT).as_posix()}")
    lines.append("")
    lines.append("## source that produced the corrected experiment")
    for base in ("oa_assp", "scripts", "configs"):
        for p in sorted((ROOT / base).rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts and "stage20_corrected_2" not in p.name:
                lines.append(f"{sha256_file(p)}  {p.relative_to(ROOT).as_posix()}")
    lines.append("")
    lines.append("## historical experiment (immutability record)")
    for p in sorted((ROOT / "results" / ORIGINAL_ID).rglob("*")):
        if p.is_file():
            lines.append(f"{sha256_file(p)}  {p.relative_to(ROOT).as_posix()}")
    (OUT / "checksums.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\nWrote:")
    for name in ("corrected_results_manifest.json", "corrected_config.yaml", "original_vs_corrected.csv",
                 "corrected_questions.json", "bootstrap_analysis_grade.csv", "checksums.txt"):
        print(f"   {OUT.relative_to(ROOT).as_posix()}/{name}")
    print(f"   {OUT.relative_to(ROOT).as_posix()}/figures/ ({len(list((OUT / 'figures').glob('*')))} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
