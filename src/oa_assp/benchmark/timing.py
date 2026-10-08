"""High-resolution timing infrastructure for shortest-path benchmarks.

Timing protocol (corrected)
---------------------------
Every reported wall-clock cost is produced by the *same* protocol:

* ``warmup_runs`` untimed executions (excluded from statistics),
* ``repetitions`` timed executions,
* the reported value is the **median** of the timed executions,
* dispersion is reported as inter-quartile range and standard deviation,
* the number of repetitions and warm-up runs is recorded with the value.

Timeouts
--------
A timeout is never reported as a success. Two enforcement modes exist:

* ``enforce_timeout=False`` (default, used by the microbenchmarks): the call is
  executed directly and the measured elapsed time is compared against
  ``timeout_seconds`` afterwards. A completed call that exceeded the budget is
  classified as ``timeout=True, success=False`` and is excluded from every
  downstream aggregate. This is exact for completed calls but cannot interrupt a
  hung call, so it must not be described as a hard wall-clock guarantee.
* ``enforce_timeout=True`` (guarded mode, used by the timeout unit tests): the
  call is dispatched to a worker thread and awaited with a deadline, so a hung
  call is detected even if it never returns. The abandoned worker cannot be
  killed (CPython), which is why this mode is not used for the microbenchmarks
  -- thread dispatch overhead would dominate a ~100 microsecond solver call.

Micro-operations
----------------
Feature extraction is 1--3 microseconds. A single ``perf_counter`` window around
such an operation is not a measurement at that scale. ``time_callable`` supports
batched repetition: the operation is executed ``batch`` times inside one window
and the total is divided by ``batch``, and the *median over repetitions of the
batched mean* is reported. The batch size is recorded with the value.
"""

from __future__ import annotations
import concurrent.futures
from dataclasses import dataclass, field
import numpy as np
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from oa_assp.algorithms.base import SearchResult


@dataclass
class TimingResult:
    """Structured timing result across multiple repetitions."""

    median_runtime: float
    mean_runtime: float
    std_runtime: float
    iqr_runtime: float
    min_runtime: float
    max_runtime: float
    raw_runtimes: List[float] = field(default_factory=list)
    repetitions: int = 0
    warmup_runs: int = 0
    timeout: bool = False
    success: bool = True
    error: Optional[str] = None
    search_result: Optional[SearchResult] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "median_runtime": self.median_runtime,
            "mean_runtime": self.mean_runtime,
            "std_runtime": self.std_runtime,
            "iqr_runtime": self.iqr_runtime,
            "min_runtime": self.min_runtime,
            "max_runtime": self.max_runtime,
            "raw_runtimes": self.raw_runtimes,
            "repetitions": self.repetitions,
            "warmup_runs": self.warmup_runs,
            "timeout": self.timeout,
            "success": self.success,
            "error": self.error,
        }


def summarize_durations(durations: List[float], repetitions: int, warmup_runs: int) -> Dict[str, float]:
    """Summarise a list of durations using the project-wide timing protocol."""
    if not durations:
        return {
            "median": 0.0,
            "mean": 0.0,
            "std": 0.0,
            "iqr": 0.0,
            "min": 0.0,
            "max": 0.0,
        }
    arr = np.array(durations, dtype=float)
    q1, q3 = np.percentile(arr, 25.0), np.percentile(arr, 75.0)
    return {
        "median": float(np.median(arr)),
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr)),
        "iqr": float(q3 - q1),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
    }


def _failed_timing_result(
    error: Optional[str],
    timeout: bool,
    raw: Optional[List[float]] = None,
    repetitions: int = 0,
    warmup_runs: int = 0,
) -> TimingResult:
    """Build a result that is explicitly NOT a success."""
    return TimingResult(
        median_runtime=0.0,
        mean_runtime=0.0,
        std_runtime=0.0,
        iqr_runtime=0.0,
        min_runtime=0.0,
        max_runtime=0.0,
        raw_runtimes=list(raw or []),
        repetitions=repetitions,
        warmup_runs=warmup_runs,
        timeout=timeout,
        success=False,
        error=error,
        search_result=None,
    )


def time_solver(
    solver_fn: Callable[..., SearchResult],
    graph: Any,
    source: Any,
    target: Any,
    warmup_runs: int = 1,
    repetitions: int = 5,
    timeout_seconds: Optional[float] = 30.0,
    return_path: bool = True,
    enforce_timeout: bool = False,
    executor: Optional[concurrent.futures.Executor] = None,
    **kwargs: Any,
) -> TimingResult:
    """Execute and time a shortest-path solver under controlled repetitions.

    ``enforce_timeout=True`` requires an ``executor`` (or creates a temporary one)
    and provides a hard deadline; see the module docstring for the trade-off.
    """
    if repetitions < 1:
        raise ValueError("repetitions must be at least 1.")
    if warmup_runs < 0:
        raise ValueError("warmup_runs must be non-negative.")
    if enforce_timeout and timeout_seconds is None:
        raise ValueError("enforce_timeout=True requires a finite timeout_seconds.")

    def _execute() -> SearchResult:
        return solver_fn(graph, source, target, return_path=return_path, **kwargs)

    owned_executor = None
    if enforce_timeout and executor is None:
        owned_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        executor = owned_executor

    try:
        # 1. Warm-up runs (excluded from statistics)
        for _ in range(warmup_runs):
            try:
                if enforce_timeout:
                    future = executor.submit(_execute)  # type: ignore[union-attr]
                    future.result(timeout=timeout_seconds)
                else:
                    _ = _execute()
            except concurrent.futures.TimeoutError:
                return _failed_timing_result(
                    error=f"Timeout after {timeout_seconds}s during warm-up",
                    timeout=True,
                    warmup_runs=warmup_runs,
                )
            except Exception as e:  # noqa: BLE001 - recorded, not swallowed
                return _failed_timing_result(error=str(e), timeout=False, warmup_runs=warmup_runs)

        # 2. Timed repetitions
        raw_runtimes: List[float] = []
        last_result: Optional[SearchResult] = None

        for _ in range(repetitions):
            t0 = time.perf_counter()
            try:
                if enforce_timeout:
                    future = executor.submit(_execute)  # type: ignore[union-attr]
                    try:
                        res = future.result(timeout=timeout_seconds)
                    except concurrent.futures.TimeoutError:
                        return _failed_timing_result(
                            error=f"Timeout after {timeout_seconds}s",
                            timeout=True,
                            raw=raw_runtimes,
                            repetitions=repetitions,
                            warmup_runs=warmup_runs,
                        )
                    elapsed = time.perf_counter() - t0
                else:
                    res = _execute()
                    elapsed = time.perf_counter() - t0
                    if timeout_seconds is not None and elapsed > timeout_seconds:
                        return _failed_timing_result(
                            error=f"Timeout after {timeout_seconds}s (observed {elapsed:.6f}s)",
                            timeout=True,
                            raw=raw_runtimes,
                            repetitions=repetitions,
                            warmup_runs=warmup_runs,
                        )
                raw_runtimes.append(elapsed)
                last_result = res
            except Exception as e:  # noqa: BLE001 - recorded, not swallowed
                return _failed_timing_result(
                    error=str(e),
                    timeout=False,
                    raw=raw_runtimes,
                    repetitions=repetitions,
                    warmup_runs=warmup_runs,
                )

        stats = summarize_durations(raw_runtimes, repetitions, warmup_runs)
        return TimingResult(
            median_runtime=stats["median"],
            mean_runtime=stats["mean"],
            std_runtime=stats["std"],
            iqr_runtime=stats["iqr"],
            min_runtime=stats["min"],
            max_runtime=stats["max"],
            raw_runtimes=raw_runtimes,
            repetitions=repetitions,
            warmup_runs=warmup_runs,
            timeout=False,
            success=True,
            error=None,
            search_result=last_result,
        )
    finally:
        if owned_executor is not None:
            owned_executor.shutdown(wait=False)


def time_callable(
    fn: Callable[[], Any],
    repetitions: int = 20,
    warmup_runs: int = 2,
    batch: int = 1,
) -> Dict[str, Any]:
    """Time a cheap callable using batched repetitions.

    The callable is executed ``batch`` times inside a single timing window and the
    window is divided by ``batch``. Results are summarized with the project-wide
    protocol (median over repetitions, IQR, std). ``batch`` is recorded so the
    batching is auditable.

    Returns a dictionary of statistics plus ``batch``, ``repetitions`` and
    ``warmup_runs``.
    """
    if repetitions < 1:
        raise ValueError("repetitions must be at least 1.")
    if batch < 1:
        raise ValueError("batch must be at least 1.")

    for _ in range(warmup_runs):
        for _ in range(batch):
            fn()

    per_call: List[float] = []
    for _ in range(repetitions):
        t0 = time.perf_counter()
        for _ in range(batch):
            fn()
        per_call.append((time.perf_counter() - t0) / float(batch))

    stats = summarize_durations(per_call, repetitions, warmup_runs)
    return {
        "median_runtime": stats["median"],
        "mean_runtime": stats["mean"],
        "std_runtime": stats["std"],
        "iqr_runtime": stats["iqr"],
        "min_runtime": stats["min"],
        "max_runtime": stats["max"],
        "raw_runtimes": per_call,
        "batch": batch,
        "repetitions": repetitions,
        "warmup_runs": warmup_runs,
    }


def time_solver_single_shot(
    solver_fn: Callable[..., SearchResult],
    graph: Any,
    source: Any,
    target: Any,
    timeout_seconds: Optional[float] = 30.0,
    return_path: bool = True,
    **kwargs: Any,
) -> Tuple[float, Optional[SearchResult], bool, Optional[str]]:
    """Time exactly one execution of a solver, as a real workload would invoke it.

    Returns ``(elapsed, search_result, timed_out, error)``. Used by the end-to-end
    adaptive execution path, where repeating the call would change the workload
    being measured. Timeouts are reported explicitly and never as successes.
    """
    t0 = time.perf_counter()
    try:
        res = solver_fn(graph, source, target, return_path=return_path, **kwargs)
    except Exception as e:  # noqa: BLE001 - recorded, not swallowed
        return (time.perf_counter() - t0, None, False, str(e))
    elapsed = time.perf_counter() - t0
    if timeout_seconds is not None and elapsed > timeout_seconds:
        return (elapsed, None, True, f"Timeout after {timeout_seconds}s (observed {elapsed:.6f}s)")
    return (elapsed, res, False, None)
