"""OA-ASSP corrected Stage 20 experiment.

Fixes carried by this run relative to the historical Stage 20 experiment:

1.  A* uses a memoized Euclidean heuristic (same values, no redundant recomputation),
    and the per-query memoization cost is charged to A*.
2.  SBS is determined from TRAINING graphs only, with a hard disjointness assertion.
3.  Benchmark validity/status fields are derived from actual execution; nothing is
    hard-coded. Timeouts are explicit and are never successes.
4.  All feature tiers use IDENTICAL selector hyperparameters.
5.  The validation split is actually used, and only for hyperparameter selection.
6.  The selector is charged a measured single-row inference latency, including at Q=1.
7.  The adaptive path is executed and measured end to end; SBS/VBS references are
    measured paired in the same modality and outside the end-to-end window.
8.  Feature costs use batched repetitions with median/IQR instead of single shots.
9.  CaptureRate / RequiredCapture analysis is computed and reported.
10. Majority-policy baselines and leave-one-cell-out / leave-one-family-out
    generalization protocols are evaluated on the recorded runtimes.
11. The experiment records a configuration hash, a source hash, and the environment.

The historical experiment directory is never written to.
"""

from __future__ import annotations
import csv
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from oa_assp.analysis.capture import (
    aggregate_points_to_csv,
    build_benchmark_cost_table,
    capture_points_to_csv,
    compute_capture_analysis,
    oracle_gap_crosscheck,
    substitute_benchmark_solver_costs,
)
from oa_assp.analysis.corrected_plots import generate_corrected_figures
from oa_assp.benchmark.adaptive import run_adaptive_workload
from oa_assp.benchmark.oracle import compute_oracles, policy_cost_for_instance, save_oracle_results
from oa_assp.benchmark.runner import (
    BenchmarkRow,
    benchmark_row_fieldnames,
    build_graph,
    build_solver_set,
    run_single_query,
)
from oa_assp.benchmark.timing import time_callable
from oa_assp.features.extractor import FeatureExtractor
from oa_assp.features.schema import get_feature_names_for_tier
from oa_assp.graphs.queries import generate_query_workload
from oa_assp.graphs.base import Graph
from oa_assp.selector.baselines import MajorityPolicySelector, evaluate_constant_policy, evaluate_oracle_policy
from oa_assp.selector.dataset import DatasetSplit
from oa_assp.selector.decision_tree import DecisionTreeSelector
from oa_assp.selector.generalization import (
    build_instance_records,
    evaluate_standard_split,
    fold_results_to_csv,
    leave_one_cell_out,
    leave_one_family_out,
)
from oa_assp.selector.tuning import select_hyperparameters

CONFIG_PATH = Path("configs/experiment_corrected_48g.yaml")
SPLIT_MANIFEST = Path("configs/graph_split_manifest_48g.csv")
ORIGINAL_STATS = Path(
    "results/stage20_scaleup_48g_20260920_215427/processed/"
    "stage20_scaleup_48g_20260920_215427_graph_realized_stats.csv"
)
ORIGINAL_RAW = Path(
    "results/stage20_scaleup_48g_20260920_215427/raw/"
    "stage20_scaleup_48g_20260920_215427_benchmark_rows.csv"
)

TIER_NAMES = {0: "Tier 0: O(1)", 1: "Tier 0+1: O(V+E)", 2: "Tier 0+1+2: Structural"}


# --------------------------------------------------------------------------- utils
def load_yaml(path: Path) -> Dict[str, Any]:
    import yaml

    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def canonical_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def source_hash(root: Path) -> Tuple[str, int]:
    """Hash every Python source file that participates in the experiment."""
    files: List[Path] = []
    for base in ("oa_assp", "scripts"):
        files.extend(sorted(p for p in (root / base).rglob("*.py") if "__pycache__" not in str(p)))
    files.extend(sorted([CONFIG_PATH, SPLIT_MANIFEST]))
    h = hashlib.sha256()
    for p in files:
        h.update(str(p.as_posix()).encode("utf-8"))
        h.update(b"\0")
        h.update(p.read_bytes())
        h.update(b"\0")
    return h.hexdigest(), len(files)


def environment_info() -> Dict[str, Any]:
    info: Dict[str, Any] = {
        "python_version": sys.version.replace("\n", " "),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "cwd": str(Path.cwd()),
    }
    for mod_name in ("numpy", "scipy", "sklearn", "matplotlib"):
        try:
            mod = __import__(mod_name)
            info[f"{mod_name}_version"] = getattr(mod, "__version__", "unknown")
        except Exception:  # noqa: BLE001
            info[f"{mod_name}_version"] = "unavailable"
    return info


def build_dataset_split(
    split_name: str,
    graph_ids: Sequence[str],
    records: Sequence[Dict[str, Any]],
    feature_names: Sequence[str],
) -> DatasetSplit:
    wanted = set(str(g) for g in graph_ids)
    rows = [r for r in records if str(r["graph_id"]) in wanted]
    if rows:
        X = np.array([r["features"] for r in rows], dtype=float)
        y = [str(r["y"]) for r in rows]
    else:
        X = np.empty((0, len(feature_names)), dtype=float)
        y = []
    return DatasetSplit(
        split_name=split_name,
        graph_ids=sorted(wanted),
        X=X,
        feature_names=list(feature_names),
        y=y,
        metadata=rows,
    )


def median_of(values: Sequence[float]) -> float:
    vals = [v for v in values if v is not None and not (isinstance(v, float) and math.isnan(v))]
    return float(np.median(vals)) if vals else float("nan")


# ---------------------------------------------------------------------- main run
def run_corrected() -> int:
    t_start = time.perf_counter()
    print("=" * 88)
    print("OA-ASSP -- CORRECTED STAGE 20 EXPERIMENT")
    print("=" * 88)

    cfg = load_yaml(CONFIG_PATH)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    exp_id = f"stage20_corrected_{timestamp}"

    config_hash = canonical_hash(cfg)
    src_hash, n_src_files = source_hash(Path("."))
    env = environment_info()

    print(f"Experiment ID     : {exp_id}")
    print(f"Configuration hash: {config_hash}")
    print(f"Source hash       : {src_hash} ({n_src_files} files)")
    print(f"Python            : {env['python_version'].split()[0]}")
    print(f"numpy/sklearn     : {env.get('numpy_version')}/{env.get('sklearn_version')}")

    # ---------------------------------------------------------------- directories
    exp_dir = Path(f"results/{exp_id}")
    raw_dir = exp_dir / "raw"
    proc_dir = exp_dir / "processed"
    fig_dir = exp_dir / "figures"
    tbl_dir = exp_dir / "tables"
    for d in (raw_dir, proc_dir, fig_dir, tbl_dir):
        d.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------------- graph spec
    with open(SPLIT_MANIFEST, "r", encoding="utf-8") as f:
        frozen = [
            {
                "graph_id": r["graph_id"],
                "family": r["family"],
                "V": int(r["V"]),
                "D": float(r["D"]),
                "seed": int(r["seed"]),
                "split": r["split"],
            }
            for r in csv.DictReader(f)
        ]
    assert len(frozen) == 48, f"Expected 48 frozen graphs, got {len(frozen)}"

    train_ids = [g["graph_id"] for g in frozen if g["split"] == "train"]
    val_ids = [g["graph_id"] for g in frozen if g["split"] == "validation"]
    test_ids = [g["graph_id"] for g in frozen if g["split"] == "test"]
    assert len(train_ids) == 32 and len(val_ids) == 8 and len(test_ids) == 8
    assert not (set(train_ids) & set(val_ids) or set(train_ids) & set(test_ids) or set(val_ids) & set(test_ids))

    print(f"Splits            : {len(train_ids)} train / {len(val_ids)} validation / {len(test_ids)} test")

    gen = cfg["graphs"]["generation"]
    directed = bool(cfg["graphs"].get("directed", False))
    timing_cfg = cfg["solvers"]["timing"]

    # --------------------------------------------------- build graphs + queries
    print("\n--- [1] GRAPH CONSTRUCTION AND INSTANCE IDENTITY CHECK ---")
    graphs: Dict[str, Graph] = {}
    queries_by_graph: Dict[str, List[Any]] = {}

    for spec in frozen:
        g = build_graph(
            family=spec["family"],
            num_vertices=spec["V"],
            average_degree=spec["D"],
            seed=spec["seed"],
            weight_model="geometric" if spec["family"] == "geometric" else "positive_random",
            weight_c=float(gen["geometric_weight_c"]),
            weight_eps=float(gen["geometric_weight_eps"]),
            directed=directed,
            weight_min=float(gen["random_weight_min"]),
            weight_max=float(gen["random_weight_max"]),
            geometric_mechanism=str(gen["geometric_mechanism"]),
        )
        assert g.graph_id == spec["graph_id"], (g.graph_id, spec["graph_id"])
        graphs[g.graph_id] = g
        queries = generate_query_workload(g, count=int(cfg["queries"]["count_per_graph"]), global_seed=spec["seed"] + 2000)
        queries_by_graph[g.graph_id] = queries

    # Verify that graph instances and query workloads are identical to the original run.
    with open(ORIGINAL_STATS, "r", encoding="utf-8") as f:
        orig_stats = {r["graph_id"]: r for r in csv.DictReader(f)}
    # NOTE on E: the historical statistics file stores ``E = graph.num_edges``, which
    # counts *arcs* (both directions for an undirected graph), while the raw benchmark
    # rows store ``E = metadata['num_edges']``, the number of *undirected* edges. Both
    # conventions are preserved exactly so that the corrected artifacts stay
    # column-comparable with the historical ones, and both are checked here.
    with open(ORIGINAL_RAW, "r", encoding="utf-8") as f:
        orig_qids: Dict[str, List[str]] = {}
        orig_row_e: Dict[str, int] = {}
        for r in csv.DictReader(f):
            orig_qids.setdefault(r["graph_id"], [])
            if r["query_id"] not in orig_qids[r["graph_id"]]:
                orig_qids[r["graph_id"]].append(r["query_id"])
            orig_row_e[r["graph_id"]] = int(r["E"])

    identity_mismatches: List[str] = []
    for gid, g in graphs.items():
        o = orig_stats[gid]
        undirected_e = int(g.metadata.get("num_edges", 0))
        if int(o["V"]) != g.num_nodes:
            identity_mismatches.append(f"{gid}: V {o['V']} -> {g.num_nodes}")
        if int(o["E"]) != int(g.num_edges):
            identity_mismatches.append(f"{gid}: arcs {o['E']} -> {g.num_edges}")
        if orig_row_e.get(gid) != undirected_e:
            identity_mismatches.append(f"{gid}: row E {orig_row_e.get(gid)} -> {undirected_e}")
        if not directed and 2 * undirected_e != int(g.num_edges):
            identity_mismatches.append(f"{gid}: arc/edge convention broken")
        if abs(float(o["actual_average_degree"]) - float(g.metadata.get("actual_average_degree", 0.0))) > 1e-9:
            identity_mismatches.append(f"{gid}: degree changed")
        if orig_qids.get(gid, []) != [q.query_id for q in queries_by_graph[gid]]:
            identity_mismatches.append(f"{gid}: query workload changed")
    assert not identity_mismatches, f"Graph/query identity changed: {identity_mismatches[:5]}"
    print("   PASS: 48 graphs and 24,000 query identifiers are identical to the historical run")
    print(f"   PASS: E convention checked both ways (arcs in statistics, undirected in raw rows)")

    # ------------------------------------------------------- benchmark execution
    print("\n--- [2] CORRECTED BENCHMARK EXECUTION (warmup + 5 repetitions, median) ---")
    raw_csv = raw_dir / f"{exp_id}_benchmark_rows.csv"
    fieldnames = benchmark_row_fieldnames()

    n_queries = 0
    n_rows = 0
    n_failures = 0
    n_timeouts = 0
    alg_counts: Dict[str, int] = {}
    t_bench0 = time.perf_counter()

    with open(raw_csv, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        for i, spec in enumerate(frozen, start=1):
            g = graphs[spec["graph_id"]]
            for q in queries_by_graph[spec["graph_id"]]:
                rows = run_single_query(
                    graph=g,
                    query=q,
                    experiment_id=exp_id,
                    warmup_runs=int(timing_cfg["warmup_runs"]),
                    repetitions=int(timing_cfg["repetitions"]),
                    timeout_seconds=float(timing_cfg["timeout_seconds"]),
                    enforce_timeout=bool(timing_cfg.get("enforce_timeout", False)),
                )
                n_queries += 1
                for r in rows:
                    d = r.to_dict()
                    writer.writerow(d)
                    n_rows += 1
                    alg_counts[r.algorithm] = alg_counts.get(r.algorithm, 0) + 1
                    if r.timeout:
                        n_timeouts += 1
                    if not r.valid:
                        n_failures += 1
                    # status consistency: a timeout can never be a success or valid
                    assert not (r.timeout and (r.success or r.valid)), "timeout reported as success"
                    assert not (r.valid and not r.success), "valid without success"
            f_out.flush()
            act = g.metadata.get("actual_average_degree", 0.0)
            print(f"   [{i:02d}/48] {spec['graph_id']:<28} V={g.num_nodes:<4} E={g.metadata.get('num_edges'):<5} d={act:.3f} split={spec['split']}")

    bench_seconds = time.perf_counter() - t_bench0
    print(f"   Rows: {n_rows}  queries: {n_queries}  solver runs: {sum(alg_counts.values())}")
    print(f"   Non-valid rows: {n_failures}   timeouts: {n_timeouts}")
    print(f"   Wall clock: {bench_seconds:.1f}s")
    assert n_rows == 72000, f"Expected 72,000 rows, got {n_rows}"
    assert n_queries == 24000
    assert n_failures == 0, f"{n_failures} non-valid solver results"
    assert n_timeouts == 0, f"{n_timeouts} timeouts"

    with open(raw_csv, "r", encoding="utf-8") as f:
        all_rows = list(csv.DictReader(f))

    # --------------------------------------------------------------- SBS / VBS
    print("\n--- [3] SBS (TRAINING-ONLY) AND VBS ---")
    oracle = compute_oracles(
        all_rows,
        sbs_reference_graph_ids=train_ids,
        sbs_source="training_graphs_only (32 graphs, 16,000 instances)",
        must_exclude_graph_ids=list(val_ids) + list(test_ids),
    )
    print(f"   SBS source: {oracle.sbs_source}")
    print(f"   Selected SBS policy: {oracle.sbs_policy}")
    for name, cost in oracle.policy_total_costs_reference.items():
        print(f"     TRAIN  {name:<32} {cost*1e3:10.3f} ms")
    print(f"   VBS wins (all rows): {oracle.vbs_win_counts}")

    save_oracle_results(oracle, proc_dir / f"{exp_id}_oracle_results.csv")
    oracle_map = {(i.graph_id, i.query_id): i for i in oracle.instances}

    with open(proc_dir / f"{exp_id}_sbs_audit.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["split", "graph_count", "instance_count", "policy", "fixed_policy_total_cost_s"])
        for split_name, ids in (("train", train_ids), ("validation", val_ids), ("test", test_ids)):
            insts = [oracle_map[(g, q)] for (g, q) in oracle_map if g in set(ids)]
            for pol in ("Always-Dijkstra", "Always-Bidirectional-Dijkstra", "Always-A*"):
                w.writerow([split_name, len(ids), len(insts), pol, sum(policy_cost_for_instance(i, pol) for i in insts)])
        w.writerow(["sbs_source", "", "", oracle.sbs_source, ""])
        w.writerow(["sbs_selected_policy", "", "", oracle.sbs_policy, ""])

    # ------------------------------------------------------------ micro timing
    print("\n--- [4] FEATURE / SELECTION TIMING CALIBRATION (batched repetitions) ---")
    mt = cfg["features"]["micro_timing"]
    tiers = [int(t) for t in cfg["features"]["tiers"]]

    graph_feature_times: Dict[int, Dict[str, float]] = {t: {} for t in tiers}
    graph_feature_stats: Dict[int, Dict[str, Dict[str, float]]] = {t: {} for t in tiers}
    query_feature_times: Dict[int, Dict[str, float]] = {t: {} for t in tiers}
    query_feature_stats: Dict[int, Dict[str, Dict[str, float]]] = {t: {} for t in tiers}

    for tier in tiers:
        ex = FeatureExtractor(default_tier=tier)
        for gid, g in graphs.items():
            st = time_callable(
                lambda g=g: ex.extract_graph_features(g, tier=tier),
                repetitions=int(mt["graph_feature_repetitions"]),
                warmup_runs=int(mt["graph_feature_warmup"]),
                batch=1,
            )
            graph_feature_times[tier][gid] = st["median_runtime"]
            graph_feature_stats[tier][gid] = st
        print(f"   Tier {tier}: graph features  median {median_of(list(graph_feature_times[tier].values()))*1e6:.2f} us/graph")

    sample_per_graph = int(mt["query_feature_sample_per_graph"])
    batch = int(mt["query_feature_batch"])
    for tier in tiers:
        ex = FeatureExtractor(default_tier=tier)
        per_graph_medians: Dict[str, float] = {}
        per_graph_stats: Dict[str, Dict[str, float]] = {}
        for gid, g in graphs.items():
            qs = [q for q in queries_by_graph[gid][:sample_per_graph] if (gid, q.query_id) in oracle_map]
            if not qs:
                continue
            q = qs[0]
            per_graph_stats[gid] = time_callable(
                lambda g=g, q=q: ex.extract_query_features(g, q, tier=tier),
                repetitions=int(mt["query_feature_repetitions"]),
                warmup_runs=int(mt["query_feature_warmup"]),
                batch=batch,
            )
            per_graph_medians[gid] = per_graph_stats[gid]["median_runtime"]
        query_feature_times[tier] = per_graph_medians
        query_feature_stats[tier] = per_graph_stats
        print(f"   Tier {tier}: query features   median {median_of(list(per_graph_medians.values()))*1e6:.3f} us/query (batch={batch}, single query repeated)")

    # ------------------------------------------------- instance records + tuning
    print("\n--- [5] VALIDATION-BASED SELECTOR CONFIGURATION SELECTION ---")
    records_by_tier: Dict[int, List[Dict[str, Any]]] = {}
    feature_names_by_tier: Dict[int, List[str]] = {}
    for tier in tiers:
        names = sorted(get_feature_names_for_tier(tier))
        feature_names_by_tier[tier] = names
        records_by_tier[tier] = build_instance_records(graphs, queries_by_graph, oracle_map, tier, names)
        print(f"   Tier {tier}: {len(feature_names_by_tier[tier])} features, {len(records_by_tier[tier])} instances")

    grid_cfg = cfg["selector"]["grid"]
    grid = [
        {"criterion": c, "max_depth": d, "min_samples_leaf": leaf}
        for c in grid_cfg["criterion"]
        for d in grid_cfg["max_depth"]
        for leaf in grid_cfg["min_samples_leaf"]
    ]
    frozen_hp = dict(cfg["selector"]["frozen_reference"])
    epsilon = float(cfg["selector"]["epsilon"])

    selected_hp, tuning_rows = select_hyperparameters(
        records=records_by_tier[1],
        train_graph_ids=train_ids,
        val_graph_ids=val_ids,
        feature_names=feature_names_by_tier[1],
        grid=grid,
        epsilon=epsilon,
        random_state=int(cfg["selector"]["random_state"]),
    )
    print(f"   Grid size: {len(tuning_rows)} configurations")
    print(f"   Validation-selected configuration: {selected_hp}")
    print(f"   Historical a-priori configuration: {frozen_hp}")
    for r in sorted(tuning_rows, key=lambda x: x.val_objective)[:5]:
        print(f"     depth={r.max_depth} leaf={r.min_samples_leaf} leaves={r.num_leaves} "
              f"valAcc={r.val_exact_accuracy:.4f} valCost={r.val_solver_cost*1e3:.3f}ms obj={r.val_objective*1e3:.3f}ms")

    with open(proc_dir / f"{exp_id}_selector_tuning.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(tuning_rows[0].to_dict().keys()))
        w.writeheader()
        for r in tuning_rows:
            w.writerow(r.to_dict())

    # ------------------------------------------------------ selector on test
    print("\n--- [6] FROZEN SELECTOR: SINGLE TEST EVALUATION ---")
    hyperparams_per_tier = {t: dict(selected_hp) for t in tiers}  # identical across tiers

    TierSummary: Dict[int, Dict[str, Any]] = {}
    for tier in tiers:
        names = feature_names_by_tier[tier]
        recs = records_by_tier[tier]
        train_split = build_dataset_split("train", train_ids, recs, names)
        val_split = build_dataset_split("val", val_ids, recs, names)
        test_split = build_dataset_split("test", test_ids, recs, names)

        selector = DecisionTreeSelector(
            max_depth=int(hyperparams_per_tier[tier]["max_depth"]),
            min_samples_leaf=int(hyperparams_per_tier[tier]["min_samples_leaf"]),
            random_state=int(cfg["selector"]["random_state"]),
            criterion=str(hyperparams_per_tier[tier].get("criterion", "gini")),
        )
        selector.fit(train_split)

        x_sample = test_split.X[0]
        latency_stats = selector.measure_single_row_latency(
            x_sample,
            repetitions=int(mt["selection_latency_repetitions"]),
            warmup_runs=int(mt["selection_latency_warmup"]),
        )
        single_row_latency = latency_stats["median_runtime"]
        compiled_stats = selector.measure_compiled_latency(
            x_sample,
            repetitions=int(mt["selection_latency_repetitions"]),
            warmup_runs=int(mt["selection_latency_warmup"]),
        )

        eval_res = selector.evaluate(test_split, epsilon=epsilon, selection_latency=single_row_latency)

        TierSummary[tier] = {
            "selector": selector,
            "train_split": train_split,
            "val_split": val_split,
            "test_split": test_split,
            "eval": eval_res,
            "selection_latency": single_row_latency,
            "selection_latency_stats": latency_stats,
            "compiled_latency": compiled_stats["median_runtime"],
            "compiled_latency_stats": compiled_stats,
        }
        print(f"   Tier {tier}: exact={eval_res.exact_accuracy*100:.2f}%  near-best(eps={epsilon})={eval_res.near_best_accuracy*100:.2f}%  "
              f"single-row latency={single_row_latency*1e6:.1f}us  finite gap: "
              f"{eval_res.total_selected_solver_runtime*1e3:.3f}ms")

    primary_tier = 1
    primary_eval = TierSummary[primary_tier]["eval"]
    with open(proc_dir / f"{exp_id}_decision_tree_structure.txt", "w", encoding="utf-8") as f:
        f.write(primary_eval.tree_text)
    with open(proc_dir / f"{exp_id}_decision_tree_nodes.json", "w", encoding="utf-8") as f:
        json.dump(TierSummary[primary_tier]["selector"].export_tree_nodes(), f, indent=2)

    # ------------------------------------------------------------- baselines
    print("\n--- [7] BASELINES ---")
    test_set = set(test_ids)
    train_set = set(train_ids)
    test_instances = [inst for (g, q), inst in oracle_map.items() if g in test_set and inst.vbs_algorithm != "none"]
    train_instances = [inst for (g, q), inst in oracle_map.items() if g in train_set and inst.vbs_algorithm != "none"]

    majority = MajorityPolicySelector().fit_instances(train_instances)
    baseline_rows = [
        evaluate_oracle_policy(test_instances, "Always-Dijkstra", epsilon=epsilon).to_dict(),
        evaluate_oracle_policy(test_instances, "Always-Bidirectional-Dijkstra", epsilon=epsilon).to_dict(),
        evaluate_oracle_policy(test_instances, "Always-A*", epsilon=epsilon).to_dict(),
        evaluate_constant_policy(test_instances, str(majority.policy), epsilon=epsilon, name=f"majority_label({majority.policy})").to_dict(),
    ]
    for b in baseline_rows:
        b["train_label_counts"] = json.dumps(majority.label_counts) if b["name"].startswith("majority") else ""
    with open(proc_dir / f"{exp_id}_baselines.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(baseline_rows[0].keys()))
        w.writeheader()
        w.writerows(baseline_rows)
    for b in baseline_rows:
        print(f"   {b['name']:<38} exact={b['exact_accuracy']*100:6.2f}%  near={b['near_best_accuracy']*100:6.2f}%  "
              f"solverCost={b['total_selected_solver_runtime']*1e3:9.3f}ms")

    # --------------------------------------------------- adaptive end-to-end
    print("\n--- [8] END-TO-END ADAPTIVE EXECUTION (test graphs) ---")
    passes = int(cfg["adaptive"]["passes"])
    adaptive_rows_path = raw_dir / f"{exp_id}_adaptive_rows.csv"
    adaptive_fieldnames = list(
        run_adaptive_workload(
            graph=graphs[test_ids[0]],
            queries=queries_by_graph[test_ids[0]][:1],
            selector=TierSummary[primary_tier]["selector"],
            feature_extractor=FeatureExtractor(default_tier=primary_tier),
            tier=primary_tier,
            feature_names=feature_names_by_tier[primary_tier],
            oracle_map=oracle_map,
            sbs_policy=oracle.sbs_policy,
            solver_set=build_solver_set(graphs[test_ids[0]]),
            experiment_id=exp_id,
        ).records[0].to_dict().keys()
    )

    adaptive_records: Dict[int, Dict[str, List[Dict[str, Any]]]] = {t: {} for t in tiers}
    pass_totals: List[Dict[str, Any]] = []

    with open(adaptive_rows_path, "w", newline="", encoding="utf-8") as f_out:
        w = csv.DictWriter(f_out, fieldnames=adaptive_fieldnames)
        w.writeheader()
        for tier in tiers:
            ex = FeatureExtractor(default_tier=tier)
            for p in range(passes):
                for gid in test_ids:
                    g = graphs[gid]
                    res = run_adaptive_workload(
                        graph=g,
                        queries=queries_by_graph[gid],
                        selector=TierSummary[tier]["selector"],
                        feature_extractor=ex,
                        tier=tier,
                        feature_names=feature_names_by_tier[tier],
                        oracle_map=oracle_map,
                        sbs_policy=oracle.sbs_policy,
                        solver_set=build_solver_set(g),
                        experiment_id=exp_id,
                        pass_index=p,
                        timeout_seconds=float(timing_cfg["timeout_seconds"]),
                        verify_distances=bool(cfg["adaptive"]["verify_distances_on_first_pass"]) and p == 0 and tier == primary_tier,
                    )
                    adaptive_records[tier].setdefault(gid, [])
                    for r in res.records:
                        adaptive_records[tier][gid].append(r.to_dict())
                        w.writerow(r.to_dict())
                    pass_totals.append({
                        "mode": "library", "tier": tier, "pass": p, "graph_id": gid,
                        "adaptive_wall_clock": res.adaptive_wall_clock,
                        "component_sum": res.component_sum,
                        "unaccounted": res.unaccounted,
                        "sum_solver": res.sum_solver,
                        "sum_sbs_solver": res.sum_sbs_solver,
                        "sum_vbs_solver": res.sum_vbs_solver,
                        "sum_query_feature": res.sum_query_feature,
                        "sum_selection": res.sum_selection,
                        "sum_graph_feature": res.sum_graph_feature,
                    })
                print(f"   tier {tier} pass {p}: completed {len(test_ids)} test graphs")

    # Correctness verification summary from the first primary pass
    verified_total = [r for r in adaptive_records[primary_tier].values() for r in r if r["pass_index"] == 0]
    n_verified_pass0 = len(verified_total)
    n_matched = sum(1 for r in verified_total if r["solver_distance_matches"])
    print(f"   Distance cross-checks (primary tier, pass 0): {n_matched}/{n_verified_pass0} matched")
    assert n_matched == n_verified_pass0, "Adaptive path produced a wrong distance"

    # Median across passes per (graph, query) for the capture analysis
    def median_series(tier: int, gid: str) -> List[Dict[str, Any]]:
        rows = adaptive_records[tier][gid]
        by_q: Dict[str, List[Dict[str, Any]]] = {}
        order: List[str] = []
        for r in rows:
            if r["query_id"] not in by_q:
                by_q[r["query_id"]] = []
                order.append(r["query_id"])
            by_q[r["query_id"]].append(r)
        series: List[Dict[str, Any]] = []
        for qid in order:
            chunk = by_q[qid]
            series.append({
                "query_id": qid,
                "query_feature_time": median_of([c["query_feature_time"] for c in chunk]),
                "feature_vector_time": median_of([c["feature_vector_time"] for c in chunk]),
                "selection_time": median_of([c["selection_time"] for c in chunk]),
                "bookkeeping_time": median_of([c["bookkeeping_time"] for c in chunk]),
                "solver_time": median_of([c["solver_time"] for c in chunk]),
                "sbs_solver_time": median_of([c["sbs_solver_time"] for c in chunk]),
                "vbs_solver_time": median_of([c["vbs_solver_time"] for c in chunk]),
                "selected_algorithm": chunk[0]["selected_algorithm"],
                "sbs_algorithm": chunk[0]["sbs_algorithm"],
                "vbs_algorithm": chunk[0]["vbs_algorithm"],
            })
        return series

    graph_meta = {
        gid: {"family": graphs[gid].metadata.get("graph_family"), "V": graphs[gid].num_nodes,
              "target_D": graphs[gid].metadata.get("target_average_degree")}
        for gid in test_ids
    }
    q_checkpoints = [int(q) for q in cfg["queries"]["q_checkpoints"]]

    capture_primary = compute_capture_analysis(
        per_graph_queries={gid: median_series(primary_tier, gid) for gid in test_ids},
        graph_feature_times={gid: median_of([r["graph_feature_time"] for r in adaptive_records[primary_tier][gid]]) for gid in test_ids},
        graph_meta=graph_meta,
        q_checkpoints=q_checkpoints,
    )
    capture_points_to_csv(capture_primary, proc_dir / f"{exp_id}_capture_per_graph.csv")
    aggregate_points_to_csv(capture_primary, proc_dir / f"{exp_id}_capture_aggregate.csv")

    print(f"\n   PRIMARY TIER {primary_tier} ({TIER_NAMES[primary_tier]}) -- measured end-to-end capture analysis")
    print(f"   {'Q':>5} {'C_SBS':>11} {'C_VBS':>11} {'C_Adapt':>10} {'overhead':>10} "
          f"{'gap':>9} {'Capture':>10} {'Required':>10} {'pays':>6}")
    print(f"   {'':>5} {'(ms)':>11} {'(ms)':>11} {'(ms)':>10} {'(ms)':>10} {'(ms)':>9} {'frac gap':>10} {'frac gap':>10} {'':>6}")
    for Q in sorted(capture_primary.aggregate_points):
        p = capture_primary.aggregate_points[Q]
        print(f"   {Q:>5} {p['total_SBS']*1e3:11.3f} {p['total_VBS']*1e3:11.3f} {p['total_Adaptive_task']*1e3:10.3f} "
              f"{p['SelectionOverhead_task']*1e3:10.3f} {p['OracleGap']*1e3:9.3f} "
              f"{p['CaptureRate_task']:10.4f} {p['RequiredCapture_task']:10.4f} {str(p['Pays_for_itself_task']):>6}")
    p500 = capture_primary.aggregate_points[500]
    print(f"   accounting bounds at Q=500: narrow required={p500['RequiredCapture']:.4f}  "
          f"task required={p500['RequiredCapture_task']:.4f}  "
          f"instrumented-wall required={p500['RequiredCapture_e2e']:.4f}  "
          f"(instrumented wall clock {p500['total_Adaptive_e2e']*1e3:.3f}ms vs task cost "
          f"{p500['total_Adaptive_task']*1e3:.3f}ms; the {p500['total_bookkeeping']*1e3:.3f}ms difference is instrumentation)")

    # ------------------------------------- oracle-gap cross-check (noise bound)
    query_order = {gid: [q.query_id for q in queries_by_graph[gid] if (gid, q.query_id) in oracle_map]
                   for gid in test_ids}
    cross = oracle_gap_crosscheck(all_rows, oracle.sbs_policy, query_order, q_checkpoints)
    with open(proc_dir / f"{exp_id}_oracle_gap_crosscheck.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Q", "SBS_benchmark_ms", "VBS_benchmark_ms", "OracleGap_benchmark_ms",
                    "SBS_paired_ms", "VBS_paired_ms", "OracleGap_paired_ms", "gap_relative_difference"])
        for Q in sorted(cross["aggregate"]):
            bm = cross["aggregate"][Q]
            paired = capture_primary.aggregate_points[Q]
            gap_paired = paired["OracleGap"]
            rel = (abs(bm["OracleGap_benchmark"] - gap_paired) / abs(gap_paired)) if abs(gap_paired) > 1e-12 else float("nan")
            bm["gap_relative_difference"] = rel
            w.writerow([Q, bm["SBS_benchmark"] * 1e3, bm["VBS_benchmark"] * 1e3, bm["OracleGap_benchmark"] * 1e3,
                        paired["total_SBS"] * 1e3, paired["total_VBS"] * 1e3, gap_paired * 1e3, rel])
            print(f"   gap cross-check Q={Q:<4} benchmark-median gap={bm['OracleGap_benchmark']*1e3:9.3f}ms  "
                  f"paired single-shot gap={gap_paired*1e3:9.3f}ms  relative difference={rel:6.2%}")

    with open(proc_dir / f"{exp_id}_oracle_gap_crosscheck_per_graph.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["graph_id", "Q", "SBS_benchmark_ms", "VBS_benchmark_ms", "OracleGap_benchmark_ms",
                    "OracleGap_paired_ms", "RequiredCapture_benchmark", "RequiredCapture_paired"])
        for gid in test_ids:
            bm_point = cross["per_graph"][gid][500]
            pts = [p for p in capture_primary.graph_points if p.graph_id == gid and p.Q == 500]
            gap_paired = pts[0].OracleGap if pts else float("nan")
            req_bm = (pts[0].SelectionOverhead_e2e / bm_point["OracleGap_benchmark"]) if pts and bm_point["OracleGap_benchmark"] > 1e-12 else float("nan")
            req_paired = pts[0].RequiredCapture_e2e if pts else float("nan")
            w.writerow([gid, 500, bm_point["SBS_benchmark"] * 1e3, bm_point["VBS_benchmark"] * 1e3,
                        bm_point["OracleGap_benchmark"] * 1e3, gap_paired * 1e3, req_bm, req_paired])

    # End-to-end vs component reconciliation at Q=500
    prim = capture_primary.aggregate_points[500]
    wall = sum(
        t["adaptive_wall_clock"] for t in pass_totals if t["tier"] == primary_tier and t["pass"] == 0
    )
    print(f"   Reconciliation at Q=500 (pass 0): end-to-end wall clock {wall*1e3:.3f}ms vs "
          f"component+overhead {prim['total_Adaptive']*1e3:.3f}ms "
          f"(delta {(wall - prim['total_Adaptive'])*1e3:.3f}ms)")

    # ------------------------------------------- compiled-rule deployment mode
    # -------------------------------------------------- analysis-grade variant
    # The adaptive passes measure SBS/VBS single-shot; that is the only modality in
    # which C_Adaptive - C_SBS is a legitimate paired difference, but tens of
    # microseconds of single-shot solver timing are noisy. This variant keeps the
    # *measured* overhead (features, vector assembly, selection, bookkeeping) exactly as
    # observed on the real adaptive path and replaces each solver cost with the
    # benchmark's repeated-median runtime for the algorithm that was actually selected.
    print("\n--- [8c] ANALYSIS-GRADE VARIANT (measured overhead + benchmark-median solver costs) ---")
    bench_table = build_benchmark_cost_table(all_rows)
    capture_hybrid = compute_capture_analysis(
        per_graph_queries={
            gid: substitute_benchmark_solver_costs(median_series(primary_tier, gid), bench_table, gid)
            for gid in test_ids
        },
        graph_feature_times={gid: median_of([r["graph_feature_time"] for r in adaptive_records[primary_tier][gid]]) for gid in test_ids},
        graph_meta=graph_meta,
        q_checkpoints=q_checkpoints,
    )
    aggregate_points_to_csv(capture_hybrid, proc_dir / f"{exp_id}_capture_aggregate_analysis_grade.csv")
    capture_points_to_csv(capture_hybrid, proc_dir / f"{exp_id}_capture_per_graph_analysis_grade.csv")
    print(f"   {'Q':>5} {'C_SBS':>11} {'C_VBS':>11} {'overhead':>10} {'gap':>9} {'Capture':>10} {'Required':>10} {'pays':>6}")
    for Q in sorted(capture_hybrid.aggregate_points):
        p = capture_hybrid.aggregate_points[Q]
        print(f"   {Q:>5} {p['total_SBS']*1e3:11.3f} {p['total_VBS']*1e3:11.3f} {p['SelectionOverhead_task']*1e3:10.3f} "
              f"{p['OracleGap']*1e3:9.3f} {p['CaptureRate_task']:10.4f} {p['RequiredCapture_task']:10.4f} {str(p['Pays_for_itself_task']):>6}")
    h500 = capture_hybrid.aggregate_points[500]
    print(f"   solver-only capture achievable at Q=500: {h500['SolverOnlyCapture']:.4f} of the oracle gap "
          f"(required to break even: narrow {h500['RequiredCapture']:.4f} / task {h500['RequiredCapture_task']:.4f} / "
          f"instrumented wall {h500['RequiredCapture_e2e']:.4f})")
    print(f"   best attainable operating point: even with a perfect selector, capture would be "
          f"{h500['SolverOnlyCapture']:.4f} vs required {h500['RequiredCapture_task']:.4f} -> "
          f"{'pays' if h500['SolverOnlyCapture'] >= h500['RequiredCapture_task'] else 'does NOT pay'}")

    print("\n--- [8b] COMPILED-RULE INFERENCE MODE (primary tier, same pass count) ---")
    compiled_path = proc_dir / f"{exp_id}_compiled_mode.csv"
    compiled_records: Dict[str, List[Dict[str, Any]]] = {}
    for p in range(passes):
        for gid in test_ids:
            g = graphs[gid]
            res = run_adaptive_workload(
                graph=g,
                queries=queries_by_graph[gid],
                selector=TierSummary[primary_tier]["selector"],
                feature_extractor=FeatureExtractor(default_tier=primary_tier),
                tier=primary_tier,
                feature_names=feature_names_by_tier[primary_tier],
                oracle_map=oracle_map,
                sbs_policy=oracle.sbs_policy,
                solver_set=build_solver_set(g),
                experiment_id=exp_id,
                pass_index=p,
                timeout_seconds=float(timing_cfg["timeout_seconds"]),
                selection_mode="compiled",
            )
            compiled_records.setdefault(gid, []).extend(r.to_dict() for r in res.records)
            pass_totals.append({
                "mode": "compiled", "tier": primary_tier, "pass": p, "graph_id": gid,
                "adaptive_wall_clock": res.adaptive_wall_clock,
                "component_sum": res.component_sum,
                "unaccounted": res.unaccounted,
                "sum_solver": res.sum_solver,
                "sum_sbs_solver": res.sum_sbs_solver,
                "sum_vbs_solver": res.sum_vbs_solver,
                "sum_query_feature": res.sum_query_feature,
                "sum_selection": res.sum_selection,
                "sum_graph_feature": res.sum_graph_feature,
            })
        print(f"   compiled pass {p}: completed {len(test_ids)} test graphs")

    with open(proc_dir / f"{exp_id}_adaptive_pass_totals.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(pass_totals[0].keys()))
        w.writeheader()
        w.writerows(pass_totals)

    def compiled_median_series(gid: str) -> List[Dict[str, Any]]:
        by_q: Dict[str, List[Dict[str, Any]]] = {}
        order: List[str] = []
        for r in compiled_records[gid]:
            if r["query_id"] not in by_q:
                by_q[r["query_id"]] = []
                order.append(r["query_id"])
            by_q[r["query_id"]].append(r)
        series: List[Dict[str, Any]] = []
        for qid in order:
            chunk = by_q[qid]
            series.append({
                "query_id": qid,
                "query_feature_time": median_of([c["query_feature_time"] for c in chunk]),
                "feature_vector_time": median_of([c["feature_vector_time"] for c in chunk]),
                "selection_time": median_of([c["selection_time"] for c in chunk]),
                "bookkeeping_time": median_of([c["bookkeeping_time"] for c in chunk]),
                "solver_time": median_of([c["solver_time"] for c in chunk]),
                "sbs_solver_time": median_of([c["sbs_solver_time"] for c in chunk]),
                "vbs_solver_time": median_of([c["vbs_solver_time"] for c in chunk]),
                "selected_algorithm": chunk[0]["selected_algorithm"],
                "sbs_algorithm": chunk[0]["sbs_algorithm"],
                "vbs_algorithm": chunk[0]["vbs_algorithm"],
            })
        return series

    capture_compiled = compute_capture_analysis(
        per_graph_queries={gid: compiled_median_series(gid) for gid in test_ids},
        graph_feature_times={gid: median_of([r["graph_feature_time"] for r in compiled_records[gid]]) for gid in test_ids},
        graph_meta=graph_meta,
        q_checkpoints=q_checkpoints,
    )
    capture_points_to_csv(capture_compiled, compiled_path)

    # Analysis-grade compiled variant: measured compiled overhead + benchmark medians.
    capture_compiled_hybrid = compute_capture_analysis(
        per_graph_queries={
            gid: substitute_benchmark_solver_costs(compiled_median_series(gid), bench_table, gid)
            for gid in test_ids
        },
        graph_feature_times={gid: median_of([r["graph_feature_time"] for r in compiled_records[gid]]) for gid in test_ids},
        graph_meta=graph_meta,
        q_checkpoints=q_checkpoints,
    )
    aggregate_points_to_csv(capture_compiled_hybrid, proc_dir / f"{exp_id}_capture_aggregate_compiled_analysis_grade.csv")
    pc = capture_compiled_hybrid.aggregate_points.get(500, {})
    print(f"   compiled inference: selection latency {TierSummary[primary_tier]['compiled_latency']*1e6:.3f}us/query "
          f"(library: {TierSummary[primary_tier]['selection_latency']*1e6:.2f}us/query), {passes} passes)")
    print(f"   analysis-grade Q=500: C_SBS={pc.get('total_SBS', float('nan'))*1e3:.3f}ms  "
          f"overhead(task)={pc.get('SelectionOverhead_task', float('nan'))*1e3:.3f}ms  "
          f"gap={pc.get('OracleGap', float('nan'))*1e3:.3f}ms  "
          f"RequiredCapture(narrow/task/wall)={pc.get('RequiredCapture', float('nan')):.4f}/{pc.get('RequiredCapture_task', float('nan')):.4f}/{pc.get('RequiredCapture_e2e', float('nan')):.4f}  "
          f"achievable_solver_capture={pc.get('SolverOnlyCapture', float('nan')):.4f}  "
          f"pays={pc.get('Pays_for_itself_task', False)}")

    # ------------------------------------------------------------ tier compare
    print("\n--- [9] FEATURE-TIER COMPARISON (identical hyperparameters) ---")
    tier_rows: List[Dict[str, Any]] = []
    for tier in tiers:
        cap = compute_capture_analysis(
            per_graph_queries={gid: median_series(tier, gid) for gid in test_ids},
            graph_feature_times={gid: median_of([r["graph_feature_time"] for r in adaptive_records[tier][gid]]) for gid in test_ids},
            graph_meta=graph_meta,
            q_checkpoints=q_checkpoints,
        )
        hybrid = compute_capture_analysis(
            per_graph_queries={
                gid: substitute_benchmark_solver_costs(median_series(tier, gid), bench_table, gid)
                for gid in test_ids
            },
            graph_feature_times={gid: median_of([r["graph_feature_time"] for r in adaptive_records[tier][gid]]) for gid in test_ids},
            graph_meta=graph_meta,
            q_checkpoints=q_checkpoints,
        )
        ev = TierSummary[tier]["eval"]
        agg500 = cap.aggregate_points.get(500, {})
        h500 = hybrid.aggregate_points.get(500, {})
        tier_rows.append({
            "tier": tier,
            "tier_name": TIER_NAMES[tier],
            "feature_count": len(feature_names_by_tier[tier]),
            "max_depth": hyperparams_per_tier[tier]["max_depth"],
            "min_samples_leaf": hyperparams_per_tier[tier]["min_samples_leaf"],
            "graph_feature_time_ms_median": median_of(list(graph_feature_times[tier].values())) * 1e3,
            "graph_feature_iqr_ms": float(np.median([graph_feature_stats[tier][g]["iqr_runtime"] for g in graph_feature_stats[tier]])) * 1e3,
            "query_feature_time_us_median": median_of(list(query_feature_times[tier].values())) * 1e6,
            "query_feature_iqr_us": float(np.median([query_feature_stats[tier][g]["iqr_runtime"] for g in query_feature_stats[tier]])) * 1e6,
            "query_feature_batch": batch,
            "selection_latency_us": TierSummary[tier]["selection_latency"] * 1e6,
            "selection_latency_iqr_us": TierSummary[tier]["selection_latency_stats"]["iqr_runtime"] * 1e6,
            "selection_latency_compiled_us": TierSummary[tier]["compiled_latency"] * 1e6,
            "selection_latency_compiled_iqr_us": TierSummary[tier]["compiled_latency_stats"]["iqr_runtime"] * 1e6,
            "exact_accuracy": ev.exact_accuracy,
            "near_best_accuracy": ev.near_best_accuracy,
            "C_adaptive_ms_Q500": agg500.get("total_Adaptive", float("nan")) * 1e3,
            "C_adaptive_e2e_ms_Q500": agg500.get("total_Adaptive_e2e", float("nan")) * 1e3,
            "C_SBS_ms_Q500": agg500.get("total_SBS", float("nan")) * 1e3,
            "C_VBS_ms_Q500": agg500.get("total_VBS", float("nan")) * 1e3,
            "SelectionOverhead_ms_Q500": agg500.get("SelectionOverhead", float("nan")) * 1e3,
            "SelectionOverhead_e2e_ms_Q500": agg500.get("SelectionOverhead_e2e", float("nan")) * 1e3,
            "CaptureRate_Q500": agg500.get("CaptureRate", float("nan")),
            "CaptureRate_e2e_Q500": agg500.get("CaptureRate_e2e", float("nan")),
            "RequiredCapture_Q500": agg500.get("RequiredCapture", float("nan")),
            "RequiredCapture_e2e_Q500": agg500.get("RequiredCapture_e2e", float("nan")),
            "GapClosed_Q500": agg500.get("GapClosed", float("nan")),
            "GapClosed_e2e_Q500": agg500.get("GapClosed_e2e", float("nan")),
            "pays_for_itself_Q500": agg500.get("Pays_for_itself", False),
            "analysis_grade_gap_Q500_ms": h500.get("OracleGap", float("nan")) * 1e3,
            "analysis_grade_overhead_Q500_ms": h500.get("SelectionOverhead_task", float("nan")) * 1e3,
            "analysis_grade_required_capture_Q500": h500.get("RequiredCapture_task", float("nan")),
            "analysis_grade_required_capture_narrow_Q500": h500.get("RequiredCapture", float("nan")),
            "analysis_grade_required_capture_instrumented_Q500": h500.get("RequiredCapture_e2e", float("nan")),
            "analysis_grade_solver_capture_Q500": h500.get("SolverOnlyCapture", float("nan")),
            "analysis_grade_pays_Q500": h500.get("Pays_for_itself_task", False),
            "compiled_analysis_grade_required_capture_Q500": float("nan"),
            "compiled_analysis_grade_solver_capture_Q500": float("nan"),
            "compiled_analysis_grade_pays_Q500": False,
        })
        # Compiled-inference economics for this tier: the same measured overhead with the
        # selection charge replaced by the compiled-rule latency.
        compiled_series_tier: Dict[str, List[Dict[str, Any]]] = {}
        for gid in test_ids:
            g = graphs[gid]
            res_c = run_adaptive_workload(
                graph=g,
                queries=queries_by_graph[gid],
                selector=TierSummary[tier]["selector"],
                feature_extractor=FeatureExtractor(default_tier=tier),
                tier=tier,
                feature_names=feature_names_by_tier[tier],
                oracle_map=oracle_map,
                sbs_policy=oracle.sbs_policy,
                solver_set=build_solver_set(g),
                experiment_id=exp_id,
                pass_index=0,
                timeout_seconds=float(timing_cfg["timeout_seconds"]),
                selection_mode="compiled",
            )
            compiled_series_tier[gid] = [r.to_dict() for r in res_c.records]
        compiled_hybrid_tier = compute_capture_analysis(
            per_graph_queries={
                gid: substitute_benchmark_solver_costs(compiled_series_tier[gid], bench_table, gid)
                for gid in test_ids
            },
            graph_feature_times={gid: median_of([r["graph_feature_time"] for r in compiled_series_tier[gid]]) for gid in test_ids},
            graph_meta=graph_meta,
            q_checkpoints=q_checkpoints,
        )
        ch500 = compiled_hybrid_tier.aggregate_points.get(500, {})
        tier_rows[-1]["compiled_analysis_grade_required_capture_Q500"] = ch500.get("RequiredCapture_e2e", float("nan"))
        tier_rows[-1]["compiled_analysis_grade_solver_capture_Q500"] = ch500.get("SolverOnlyCapture", float("nan"))
        tier_rows[-1]["compiled_analysis_grade_pays_Q500"] = ch500.get("Pays_for_itself", False)
        print(f"   Tier {tier} analysis-grade Q=500: overhead(task)={h500.get('SelectionOverhead_task', float('nan'))*1e3:8.3f}ms "
              f"gap={h500.get('OracleGap', float('nan'))*1e3:7.3f}ms required={h500.get('RequiredCapture_task', float('nan')):8.4f} "
              f"achievable={h500.get('SolverOnlyCapture', float('nan')):7.4f} | compiled required={ch500.get('RequiredCapture_task', float('nan')):7.4f}")
        tier_rows[-1]["compiled_analysis_grade_required_capture_Q500"] = ch500.get("RequiredCapture_task", float("nan"))
        print(f"   Tier {tier}: feats={len(feature_names_by_tier[tier]):>2} acc={ev.exact_accuracy*100:5.2f}% "
              f"gfeat={median_of(list(graph_feature_times[tier].values()))*1e6:8.2f}us qfeat={median_of(list(query_feature_times[tier].values()))*1e6:6.3f}us "
              f"sel(lib)={TierSummary[tier]['selection_latency']*1e6:6.1f}us sel(compiled)={TierSummary[tier]['compiled_latency']*1e6:5.2f}us "
              f"Capture_e2e={agg500.get('CaptureRate_e2e', float('nan')):8.4f} Req_e2e={agg500.get('RequiredCapture_e2e', float('nan')):8.4f} "
              f"pays={agg500.get('Pays_for_itself', False)}")

    with open(proc_dir / f"{exp_id}_feature_tier_tradeoffs.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(tier_rows[0].keys()))
        w.writeheader()
        w.writerows(tier_rows)

    # ----------------------------------------------------------- generalization
    print("\n--- [10] SELECTOR GENERALIZATION ---")
    gen_rows: List[Dict[str, Any]] = []
    for tier in [int(t) for t in cfg["generalization"]["tiers"]]:
        recs = records_by_tier[tier]
        names = feature_names_by_tier[tier]
        hp = hyperparams_per_tier[tier]
        gen_rows.append(evaluate_standard_split(recs, train_ids, test_ids, names, hp, epsilon, tier=tier).to_dict())
        gen_rows.extend(r.to_dict() for r in leave_one_cell_out(recs, names, hp, epsilon, tier=tier))
        gen_rows.extend(r.to_dict() for r in leave_one_family_out(recs, names, hp, epsilon, tier=tier))

    with open(proc_dir / f"{exp_id}_generalization.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(gen_rows[0].keys()))
        w.writeheader()
        w.writerows(gen_rows)

    for tier in [int(t) for t in cfg["generalization"]["tiers"]]:
        for protocol in ("standard_held_out", "leave_one_cell_out", "leave_one_family_out"):
            sub = [r for r in gen_rows
                   if r["protocol"] == protocol and int(r["tier"]) == tier and r["num_train_instances"] > 0]
            if not sub:
                continue
            acc = median_of([r["exact_accuracy"] for r in sub])
            maj = median_of([r["majority_exact_accuracy"] for r in sub])
            lift = median_of([r["accuracy_lift_over_majority"] for r in sub])
            cap = median_of([r["solver_only_capture"] for r in sub])
            print(f"   tier {tier} {protocol:<20} folds={len(sub):>3}  median exact={acc*100:6.2f}%  "
                  f"majority={maj*100:6.2f}%  median lift={lift*100:+6.2f}pp  median solver-capture={cap:8.4f}")

    # ---------------------------------------------------------------- bootstrap
    print("\n--- [11] GRAPH-LEVEL BOOTSTRAP (paired, test graphs only) ---")
    rng = np.random.default_rng(int(cfg["seeds"]["bootstrap_seed"]))
    per_graph_series = {gid: median_series(primary_tier, gid) for gid in test_ids}
    gf = {gid: median_of([r["graph_feature_time"] for r in adaptive_records[primary_tier][gid]]) for gid in test_ids}

    def graph_metrics(gids: Sequence[str]) -> Dict[str, float]:
        adapt = 0.0
        sbs = 0.0
        vbs = 0.0
        overhead = 0.0
        for gid in gids:
            overhead += gf[gid]
            adapt += gf[gid]
            for r in per_graph_series[gid]:
                qf = r["query_feature_time"]
                sl = r["selection_time"]
                extra = r.get("feature_vector_time", 0.0) + r.get("bookkeeping_time", 0.0)
                overhead += qf + sl + extra
                adapt += qf + sl + extra + r["solver_time"]
                sbs += r["sbs_solver_time"]
                vbs += r["vbs_solver_time"]
        gap = sbs - vbs
        saves = sbs - adapt
        return {
            "adaptive_minus_sbs": adapt - sbs,
            "adaptive_ratio_sbs": (adapt / sbs) if sbs > 0 else float("nan"),
            "gap_closed": (-saves / gap) if gap > 1e-12 else float("nan"),
            "capture_rate": (saves / gap) if gap > 1e-12 else float("nan"),
            "required_capture": (overhead / gap) if gap > 1e-12 else float("nan"),
        }

    point = graph_metrics(test_ids)
    boot: Dict[str, List[float]] = {k: [] for k in point}
    g = list(test_ids)
    for _ in range(int(cfg["bootstrap"]["samples"])):
        sample = [g[i] for i in rng.integers(0, len(g), size=len(g))]
        m = graph_metrics(sample)
        for k, v in m.items():
            if not math.isnan(v):
                boot[k].append(v)

    alpha = 1.0 - float(cfg["bootstrap"]["confidence_level"])
    boot_rows: List[Dict[str, Any]] = []
    for k, vals in boot.items():
        if not vals:
            continue
        lo, hi = np.percentile(vals, 100 * alpha / 2), np.percentile(vals, 100 * (1 - alpha / 2))
        boot_rows.append({
            "metric": k, "point_estimate": point[k], "ci_lower": float(lo), "ci_upper": float(hi),
            "confidence_level": float(cfg["bootstrap"]["confidence_level"]),
            "std_error": float(np.std(vals)), "num_replicates": len(vals),
            "num_graphs": len(test_ids), "graph_sampling": "paired_graph_level",
            "caveat": "8 purposively designed test graphs; intervals bound this sample, not a population",
        })
        print(f"   {k:<22} point={point[k]:9.5f}  95% CI [{lo:9.5f}, {hi:9.5f}]")

    with open(proc_dir / f"{exp_id}_bootstrap_results.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(boot_rows[0].keys()))
        w.writeheader()
        w.writerows(boot_rows)

    # ------------------------------------------------------- pass dispersion
    # How reproducible is the headline quantity within one execution? Each pass is an
    # independent repetition of the whole adaptive workload on the test graphs, so the
    # spread across passes is the measurement reproducibility floor of these numbers.
    print("\n--- [11b] MEASUREMENT REPRODUCIBILITY (adaptive workload repeated per pass) ---")
    disp_rows: List[Dict[str, Any]] = []
    for tier in tiers:
        for Q in (1, 10, 500):
            per_pass_adapt: List[float] = []
            per_pass_sbs: List[float] = []
            per_pass_gfeat: List[float] = []
            for p in range(passes):
                total_adapt = 0.0
                total_sbs = 0.0
                total_gfeat = 0.0
                for gid in test_ids:
                    rows_p = [r for r in adaptive_records[tier][gid] if r["pass_index"] == p]
                    if not rows_p:
                        continue
                    gf_p = median_of([r["graph_feature_time"] for r in rows_p])
                    total_gfeat += gf_p
                    total_adapt += gf_p
                    for r in rows_p[:min(Q, len(rows_p))]:
                        total_adapt += (r["query_feature_time"] + r["feature_vector_time"]
                                        + r["selection_time"] + r["bookkeeping_time"] + r["solver_time"])
                        total_sbs += r["sbs_solver_time"]
                per_pass_adapt.append(total_adapt)
                per_pass_sbs.append(total_sbs)
                per_pass_gfeat.append(total_gfeat)
            deltas = [a - s for a, s in zip(per_pass_adapt, per_pass_sbs)]
            ratios = [a / s if s > 0 else float("nan") for a, s in zip(per_pass_adapt, per_pass_sbs)]
            med_delta = float(np.median(deltas))
            disp_rows.append({
                "tier": tier, "Q": Q, "num_passes": passes,
                "C_adaptive_min_ms": min(per_pass_adapt) * 1e3,
                "C_adaptive_median_ms": float(np.median(per_pass_adapt)) * 1e3,
                "C_adaptive_max_ms": max(per_pass_adapt) * 1e3,
                "C_adaptive_range_relative": (max(per_pass_adapt) - min(per_pass_adapt)) / float(np.median(per_pass_adapt)),
                "C_graph_feature_median_ms": float(np.median(per_pass_gfeat)) * 1e3,
                "C_SBS_median_ms": float(np.median(per_pass_sbs)) * 1e3,
                "adaptive_minus_sbs_min_ms": min(deltas) * 1e3,
                "adaptive_minus_sbs_median_ms": med_delta * 1e3,
                "adaptive_minus_sbs_max_ms": max(deltas) * 1e3,
                "adaptive_minus_sbs_range_relative": (
                    (max(deltas) - min(deltas)) / abs(med_delta) if abs(med_delta) > 1e-12 else float("nan")),
                "adaptive_ratio_sbs_min": min(ratios),
                "adaptive_ratio_sbs_median": float(np.median(ratios)),
                "adaptive_ratio_sbs_max": max(ratios),
                "sign_stable": bool(all(d < 0 for d in deltas) or all(d > 0 for d in deltas)),
            })
            print(f"   tier {tier} Q={Q:<4} C_adaptive across passes: min={min(per_pass_adapt)*1e3:.3f} "
                  f"median={float(np.median(per_pass_adapt))*1e3:.3f} max={max(per_pass_adapt)*1e3:.3f} ms | "
                  f"Adaptive-SBS: min={min(deltas)*1e3:+.3f} median={med_delta*1e3:+.3f} max={max(deltas)*1e3:+.3f} ms "
                  f"(sign stable: {disp_rows[-1]['sign_stable']})")

    with open(proc_dir / f"{exp_id}_pass_dispersion.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(disp_rows[0].keys()))
        w.writeheader()
        w.writerows(disp_rows)

    # ------------------------------------------------------------------ figures
    print("\n--- [12] FIGURES ---")
    fig_files = generate_corrected_figures(
        output_dir=fig_dir,
        capture=capture_primary,
        tier_rows=tier_rows,
        tuning_rows=[r.to_dict() for r in tuning_rows],
        generality_rows=gen_rows,
        baseline_rows=baseline_rows,
        pass_totals=pass_totals,
        primary_tier=primary_tier,
        capture_hybrid=capture_hybrid,
        capture_compiled_hybrid=capture_compiled_hybrid,
    )
    for p in fig_files:
        print(f"   {p}")

    # ------------------------------------------------------------------ manifest
    total_wall = time.perf_counter() - t_start
    manifest = {
        "experiment_id": exp_id,
        "experiment_family": cfg["experiment_family"],
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "configuration_hash": config_hash,
        "source_hash": src_hash,
        "source_files_hashed": n_src_files,
        "git_commit": None,
        "git_note": "no version control present in this workspace",
        "environment": env,
        "config_file": str(CONFIG_PATH.as_posix()),
        "graph_manifest_file": str(SPLIT_MANIFEST.as_posix()),
        "train_graph_ids": sorted(train_ids),
        "validation_graph_ids": sorted(val_ids),
        "test_graph_ids": sorted(test_ids),
        "num_graphs": 48,
        "num_queries_per_graph": int(cfg["queries"]["count_per_graph"]),
        "total_queries": 24000,
        "total_solver_runs": int(sum(alg_counts.values())),
        "timing_protocol": {
            "warmup_runs": int(timing_cfg["warmup_runs"]),
            "repetitions": int(timing_cfg["repetitions"]),
            "statistic": "median",
            "dispersion": "iqr and std",
            "timeout_seconds": float(timing_cfg["timeout_seconds"]),
        },
        "sbs": {
            "source": oracle.sbs_source,
            "policy": oracle.sbs_policy,
            "reference_graph_ids": oracle.sbs_reference_graph_ids,
            "reference_policy_totals_s": oracle.policy_total_costs_reference,
            "assertion": "reference graphs disjoint from validation and test graphs",
        },
        "selector": {
            "hyperparameter_selection": "validation split only",
            "validation_selected_configuration": selected_hp,
            "historical_frozen_configuration": frozen_hp,
            "identical_hyperparameters_across_tiers": True,
            "selection_charge": "measured single-row inference latency",
        },
        "adaptive": {
            "passes": passes,
            "graphs": sorted(test_ids),
            "measurement": "end-to-end wall clock of the adaptive path only; SBS/VBS paired in an adjacent loop",
            "primary_tier": primary_tier,
            "inference_modes": ["library (sklearn single-row predict)", "compiled (nested conditionals)"],
            "passes_compiled": passes,
        },
        "cost_model": {
            "primary_definition": (
                "analysis-grade: C_SBS / C_VBS / selected-solver costs from the benchmark's "
                "warm-up+repetitions medians; SelectionOverhead measured on the real adaptive "
                "path; C_Adaptive = SelectionOverhead + C_selected_solver"
            ),
            "secondary_definition": (
                "measured end-to-end: every solver call single-shot inside the adaptive loop, "
                "which is the only modality in which C_Adaptive - C_SBS is a paired difference"
            ),
            "selection_charge": "measured single-row latency; library and compiled-rule modes reported separately",
        },
        "capture_aggregate": {str(Q): capture_primary.aggregate_points[Q] for Q in sorted(capture_primary.aggregate_points)},
        "capture_aggregate_analysis_grade": {str(Q): capture_hybrid.aggregate_points[Q] for Q in sorted(capture_hybrid.aggregate_points)},
        "capture_aggregate_compiled": {str(Q): capture_compiled.aggregate_points[Q] for Q in sorted(capture_compiled.aggregate_points)},
        "capture_aggregate_compiled_analysis_grade": {str(Q): capture_compiled_hybrid.aggregate_points[Q] for Q in sorted(capture_compiled_hybrid.aggregate_points)},
        "oracle_gap_crosscheck": {
            "meaning": "benchmark repeated-median gap vs paired single-shot gap; a large relative difference means the measured gap is noise-dominated",
            "by_Q": {str(Q): {k: v for k, v in cross["aggregate"][Q].items()} for Q in sorted(cross["aggregate"])},
        },
        "artifacts": {
            "raw_benchmark_csv": str(raw_csv.as_posix()),
            "adaptive_rows_csv": str(adaptive_rows_path.as_posix()),
            "oracle_csv": str((proc_dir / f"{exp_id}_oracle_results.csv").as_posix()),
            "sbs_audit_csv": str((proc_dir / f"{exp_id}_sbs_audit.csv").as_posix()),
            "capture_aggregate_csv": str((proc_dir / f"{exp_id}_capture_aggregate.csv").as_posix()),
            "capture_per_graph_csv": str((proc_dir / f"{exp_id}_capture_per_graph.csv").as_posix()),
            "selector_tuning_csv": str((proc_dir / f"{exp_id}_selector_tuning.csv").as_posix()),
            "feature_tier_tradeoffs_csv": str((proc_dir / f"{exp_id}_feature_tier_tradeoffs.csv").as_posix()),
            "baselines_csv": str((proc_dir / f"{exp_id}_baselines.csv").as_posix()),
            "generalization_csv": str((proc_dir / f"{exp_id}_generalization.csv").as_posix()),
            "bootstrap_csv": str((proc_dir / f"{exp_id}_bootstrap_results.csv").as_posix()),
            "pass_dispersion_csv": str((proc_dir / f"{exp_id}_pass_dispersion.csv").as_posix()),
            "compiled_mode_csv": str(compiled_path.as_posix()),
            "capture_aggregate_analysis_grade_csv": str((proc_dir / f"{exp_id}_capture_aggregate_analysis_grade.csv").as_posix()),
            "capture_per_graph_analysis_grade_csv": str((proc_dir / f"{exp_id}_capture_per_graph_analysis_grade.csv").as_posix()),
            "capture_aggregate_compiled_analysis_grade_csv": str((proc_dir / f"{exp_id}_capture_aggregate_compiled_analysis_grade.csv").as_posix()),
            "oracle_gap_crosscheck_csv": str((proc_dir / f"{exp_id}_oracle_gap_crosscheck.csv").as_posix()),
            "oracle_gap_crosscheck_per_graph_csv": str((proc_dir / f"{exp_id}_oracle_gap_crosscheck_per_graph.csv").as_posix()),
            "figures_dir": str(fig_dir.as_posix()),
        },
        "runtime_seconds": total_wall,
        "bug_fixes_applied": [
            "A* Euclidean heuristic memoized per (node,target); memo cost charged per query",
            "SBS determined from training graphs only, with disjointness assertion",
            "validity/timeout derived from execution; no hard-coded valid=True",
            "timeout implemented and never reported as success",
            "identical selector hyperparameters across feature tiers",
            "validation split used only for hyperparameter selection",
            "single-row selection latency charged per query (no batch amortization at Q=1)",
            "end-to-end adaptive path measured directly",
            "feature/selection costs measured with batched repetitions and dispersion",
            "capture-rate and required-capture analysis computed",
            "majority-policy baselines added",
            "leave-one-cell-out and leave-one-family-out generalization added",
            "configuration hash extended to all result-affecting parameters; source hash recorded",
        ],
    }
    manifest_path = proc_dir / f"{exp_id}_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, default=str)

    print("\n" + "=" * 88)
    print(f"CORRECTED STAGE 20 COMPLETE in {total_wall:.1f}s ({total_wall/60:.2f} min)")
    print(f"EXPERIMENT ID : {exp_id}")
    print(f"MANIFEST      : {manifest_path}")
    print("=" * 88)
    return 0


if __name__ == "__main__":
    sys.exit(run_corrected())
