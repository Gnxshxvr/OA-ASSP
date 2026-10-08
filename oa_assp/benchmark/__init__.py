"""Benchmark module for OA-ASSP.

Note: the historical ``run_benchmark`` helper has been removed. It was obsolete (its
``full`` profile crashed on the frozen YAML shape), it used a different seed scheme
from the frozen split manifest, and it is not used by any authoritative experiment.
Graph construction and query workload generation are unchanged.
"""

from oa_assp.benchmark.counters import OperationCounters, SearchResult
from oa_assp.benchmark.correctness import validate_results, verify_path, ValidationResult
from oa_assp.benchmark.timing import time_callable, time_solver, time_solver_single_shot, TimingResult
from oa_assp.benchmark.runner import (
    BenchmarkRow,
    benchmark_row_fieldnames,
    build_graph,
    build_solver_set,
    run_single_query,
)
from oa_assp.benchmark.oracle import (
    OracleInstance,
    OracleSummary,
    assert_reference_disjoint,
    compute_oracles,
    policy_cost_for_instance,
    save_oracle_results,
)

__all__ = [
    "OperationCounters",
    "SearchResult",
    "validate_results",
    "verify_path",
    "ValidationResult",
    "time_solver",
    "time_callable",
    "time_solver_single_shot",
    "TimingResult",
    "BenchmarkRow",
    "benchmark_row_fieldnames",
    "build_graph",
    "build_solver_set",
    "run_single_query",
    "run_adaptive_workload",
    "AdaptiveQueryRecord",
    "AdaptiveWorkloadResult",
    "OracleInstance",
    "OracleSummary",
    "assert_reference_disjoint",
    "compute_oracles",
    "policy_cost_for_instance",
    "save_oracle_results",
]

# ``oa_assp.benchmark.adaptive`` depends on ``oa_assp.selector``, which depends on
# ``oa_assp.benchmark.oracle``. Importing it eagerly here would close that cycle, so the
# adaptive symbols are resolved lazily (PEP 562). ``from oa_assp.benchmark import
# run_adaptive_workload`` continues to work.
_LAZY_ADAPTIVE = {
    "run_adaptive_workload": "oa_assp.benchmark.adaptive",
    "AdaptiveQueryRecord": "oa_assp.benchmark.adaptive",
    "AdaptiveWorkloadResult": "oa_assp.benchmark.adaptive",
}


def __getattr__(name: str):
    module_name = _LAZY_ADAPTIVE.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib

    return getattr(importlib.import_module(module_name), name)
