"""Offline oracle computation for Single Best Solver (SBS) and Virtual Best Solver (VBS).

Corrected relative to the historical implementation
----------------------------------------------------
The historical pipeline selected the SBS policy by minimising the fixed-policy total
over **all 48 graphs**, including the held-out test graphs (the README claimed
train-only). The corrected implementation:

* determines the SBS policy from an explicit **reference set of rows** (training
  graphs only), passed by the caller;
* records the reference graph IDs and the reference totals so the choice is auditable;
* asserts that the reference graphs are disjoint from any graph set the caller
  declares as held out;
* keeps VBS as a per-instance oracle over oracle-eligible solvers, as before.

Eligibility
-----------
``oracle_eligible`` is read from the row when present (derived from actual execution
plus declared heuristic admissibility). Legacy rows without that column fall back to
the historical rule (``valid`` and, for A*, geometric weights).
"""

from __future__ import annotations
import csv
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple, Union

from oa_assp.benchmark.runner import BenchmarkRow

POLICY_NAMES = ("Always-Dijkstra", "Always-Bidirectional-Dijkstra", "Always-A*")


@dataclass
class OracleInstance:
    """Ground-truth oracle labels and costs for an individual query."""

    graph_id: str
    query_id: str
    vbs_algorithm: str
    vbs_cost: float
    dijkstra_cost: float
    astar_cost: float
    bidirectional_cost: float
    valid_dijkstra: bool
    valid_astar: bool
    valid_bidirectional: bool
    always_dijkstra_cost: float
    always_bidi_cost: float
    always_astar_cost: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OracleSummary:
    """Summary of oracle analysis across a benchmark population."""

    instances: List[OracleInstance]
    sbs_policy: str
    sbs_total_cost: float
    vbs_total_cost: float
    policy_total_costs: Dict[str, float]
    vbs_win_counts: Dict[str, int]
    sbs_source: str = "all_rows"
    sbs_reference_graph_ids: List[str] = field(default_factory=list)
    policy_total_costs_reference: Dict[str, float] = field(default_factory=dict)
    num_reference_instances: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sbs_policy": self.sbs_policy,
            "sbs_total_cost": self.sbs_total_cost,
            "vbs_total_cost": self.vbs_total_cost,
            "policy_total_costs": self.policy_total_costs,
            "vbs_win_counts": self.vbs_win_counts,
            "num_instances": len(self.instances),
            "sbs_source": self.sbs_source,
            "sbs_reference_graph_ids": self.sbs_reference_graph_ids,
            "policy_total_costs_reference": self.policy_total_costs_reference,
            "num_reference_instances": self.num_reference_instances,
        }


def load_benchmark_rows(
    benchmark_data: Union[List[BenchmarkRow], List[Dict[str, Any]], str, Path],
) -> List[Dict[str, Any]]:
    """Normalise benchmark data (dataclasses, dicts or CSV path) into dict rows."""
    rows: List[Dict[str, Any]] = []
    if isinstance(benchmark_data, (str, Path)):
        path = Path(benchmark_data)
        if not path.exists():
            raise FileNotFoundError(f"Benchmark file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            rows.extend(dict(r) for r in csv.DictReader(f))
    else:
        for item in benchmark_data:
            if isinstance(item, BenchmarkRow):
                rows.append(item.to_dict())
            elif isinstance(item, dict):
                rows.append(item)
            else:
                raise TypeError(f"Unsupported row type: {type(item)}")
    if not rows:
        raise ValueError("Cannot compute oracles on empty benchmark data.")
    return rows


def _row_is_success(row: Dict[str, Any]) -> bool:
    val = row.get("success", True)
    if isinstance(val, str):
        return val.strip().lower() == "true"
    return bool(val)


def _row_timeout(row: Dict[str, Any]) -> bool:
    val = row.get("timeout", False)
    if isinstance(val, str):
        return val.strip().lower() == "true"
    return bool(val)


def _row_is_eligible(row: Dict[str, Any]) -> bool:
    """Eligibility of a solver row for the oracle, derived from data when available."""
    if not _row_is_success(row) or _row_timeout(row):
        return False
    if "oracle_eligible" in row:
        val = row["oracle_eligible"]
        if isinstance(val, str):
            return val.strip().lower() == "true"
        return bool(val)
    # Legacy fallback: A* eligible only on geometric weights, otherwise valid flag.
    valid = row.get("valid", True)
    if isinstance(valid, str):
        valid = valid.strip().lower() == "true"
    algorithm = str(row.get("algorithm", ""))
    if algorithm == "A*":
        return bool(valid) and str(row.get("weight_model", "")) == "geometric"
    return bool(valid)


def assert_reference_disjoint(
    reference_graph_ids: Iterable[str],
    held_out_graph_ids: Iterable[str],
    label: str = "held-out",
) -> None:
    """Hard assertion that the SBS reference graphs are disjoint from held-out graphs."""
    ref = set(str(g) for g in reference_graph_ids)
    held = set(str(g) for g in held_out_graph_ids)
    overlap = ref & held
    if overlap:
        raise ValueError(
            f"SBS leakage: reference graphs intersect {label} graphs: {sorted(overlap)}"
        )


def compute_oracles(
    benchmark_data: Union[List[BenchmarkRow], List[Dict[str, Any]], str, Path],
    sbs_reference_graph_ids: Optional[Sequence[str]] = None,
    sbs_source: str = "all_rows",
    must_exclude_graph_ids: Optional[Sequence[str]] = None,
) -> OracleSummary:
    """Compute offline SBS (from a declared reference set) and per-instance VBS.

    Parameters
    ----------
    benchmark_data
        Rows, dataclasses or a CSV path. All rows are used for VBS and for the
        fixed-policy totals reported per split.
    sbs_reference_graph_ids
        Graph IDs whose rows define the SBS policy. When ``None`` the policy is
        chosen over every supplied row (historical behaviour) and ``sbs_source`` is
        used for labelling. Callers in the corrected pipeline always pass the
        training graph IDs explicitly.
    must_exclude_graph_ids
        When given, a hard assertion verifies the reference set is disjoint from it.
    """
    rows = load_benchmark_rows(benchmark_data)

    if sbs_reference_graph_ids is not None:
        ref_ids = set(str(g) for g in sbs_reference_graph_ids)
        present = set(str(r["graph_id"]) for r in rows)
        missing = ref_ids - present
        if missing:
            raise ValueError(f"SBS reference graphs missing from benchmark rows: {sorted(missing)}")
    else:
        ref_ids = set(str(r["graph_id"]) for r in rows)

    if must_exclude_graph_ids is not None:
        assert_reference_disjoint(ref_ids, must_exclude_graph_ids)

    # 1. Group by (graph_id, query_id)
    grouped: Dict[Tuple[str, str], Dict[str, Dict[str, Any]]] = {}
    for r in rows:
        key = (str(r["graph_id"]), str(r["query_id"]))
        grouped.setdefault(key, {})[str(r["algorithm"])] = r

    instances: List[OracleInstance] = []
    policy_totals = {name: 0.0 for name in POLICY_NAMES}
    policy_totals_reference = {name: 0.0 for name in POLICY_NAMES}
    vbs_win_counts = {"Dijkstra": 0, "Bidirectional Dijkstra": 0, "A*": 0}
    num_reference_instances = 0

    for (gid, qid), algos in grouped.items():
        def _cost(name: str) -> float:
            row = algos.get(name)
            if row is None:
                return float("inf")
            return float(row.get("runtime_median", float("inf")))

        dijk_cost = _cost("Dijkstra")
        bidi_cost = _cost("Bidirectional Dijkstra")
        astar_cost = _cost("A*")

        dijk_ok = _row_is_eligible(algos["Dijkstra"]) if "Dijkstra" in algos else False
        bidi_ok = (
            _row_is_eligible(algos["Bidirectional Dijkstra"])
            if "Bidirectional Dijkstra" in algos
            else False
        )
        astar_ok = _row_is_eligible(algos["A*"]) if "A*" in algos else False

        candidate_costs: Dict[str, float] = {}
        if dijk_ok and dijk_cost < float("inf"):
            candidate_costs["Dijkstra"] = dijk_cost
        if bidi_ok and bidi_cost < float("inf"):
            candidate_costs["Bidirectional Dijkstra"] = bidi_cost
        if astar_ok and astar_cost < float("inf"):
            candidate_costs["A*"] = astar_cost

        if not candidate_costs:
            # No eligible solver: record an infinite-cost, unreachable-by-oracle instance.
            vbs_algo = "none"
            vbs_cost = float("inf")
        else:
            vbs_algo = min(candidate_costs, key=candidate_costs.get)
            vbs_cost = candidate_costs[vbs_algo]
            if vbs_algo in vbs_win_counts:
                vbs_win_counts[vbs_algo] += 1

        # Fixed-policy costs. Always-A* falls back to Dijkstra when A* is not eligible.
        c_always_dijk = dijk_cost
        c_always_bidi = bidi_cost
        c_always_astar = astar_cost if astar_ok else dijk_cost

        policy_totals["Always-Dijkstra"] += c_always_dijk
        policy_totals["Always-Bidirectional-Dijkstra"] += c_always_bidi
        policy_totals["Always-A*"] += c_always_astar
        if gid in ref_ids:
            num_reference_instances += 1
            policy_totals_reference["Always-Dijkstra"] += c_always_dijk
            policy_totals_reference["Always-Bidirectional-Dijkstra"] += c_always_bidi
            policy_totals_reference["Always-A*"] += c_always_astar

        instances.append(
            OracleInstance(
                graph_id=gid,
                query_id=qid,
                vbs_algorithm=vbs_algo,
                vbs_cost=vbs_cost,
                dijkstra_cost=dijk_cost,
                astar_cost=astar_cost,
                bidirectional_cost=bidi_cost,
                valid_dijkstra=bool(dijk_ok),
                valid_astar=bool(astar_ok),
                valid_bidirectional=bool(bidi_ok),
                always_dijkstra_cost=c_always_dijk,
                always_bidi_cost=c_always_bidi,
                always_astar_cost=c_always_astar,
            )
        )

    # SBS policy is chosen on the reference set ONLY.
    sbs_policy = min(policy_totals_reference, key=policy_totals_reference.get)
    if num_reference_instances == 0:
        raise ValueError("SBS reference set contains no instances.")

    vbs_total = sum(inst.vbs_cost for inst in instances if inst.vbs_algorithm != "none")

    return OracleSummary(
        instances=instances,
        sbs_policy=sbs_policy,
        sbs_total_cost=policy_totals[sbs_policy],
        vbs_total_cost=vbs_total,
        policy_total_costs=policy_totals,
        vbs_win_counts=vbs_win_counts,
        sbs_source=sbs_source,
        sbs_reference_graph_ids=sorted(ref_ids),
        policy_total_costs_reference=policy_totals_reference,
        num_reference_instances=num_reference_instances,
    )


def policy_cost_for_instance(inst: OracleInstance, policy: str) -> float:
    """Return the cost of a fixed policy on one oracle instance."""
    if policy == "Always-Dijkstra":
        return inst.always_dijkstra_cost
    if policy == "Always-Bidirectional-Dijkstra":
        return inst.always_bidi_cost
    if policy == "Always-A*":
        return inst.always_astar_cost
    raise ValueError(f"Unknown policy: {policy}")


def save_oracle_results(summary: OracleSummary, output_path: Union[str, Path]) -> str:
    """Save oracle ground-truth instances to a CSV file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if not summary.instances:
        raise ValueError("No oracle instances to save.")

    field_names = list(summary.instances[0].to_dict().keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=field_names)
        writer.writeheader()
        for inst in summary.instances:
            writer.writerow(inst.to_dict())

    return str(path)
