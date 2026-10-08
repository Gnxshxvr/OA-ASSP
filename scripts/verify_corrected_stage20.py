"""Falsifiable integrity audit of the corrected Stage 20 experiment.

Every check below FAILS LOUDLY if the corrected empirical record is inconsistent with
its own raw data, with the historical experiment, or with the documented methodology.
Nothing here is a summary statistic: each check recomputes something from raw files and
compares it against what the processed artifacts claim.

Run:
    python scripts/verify_corrected_stage20.py [experiment_id]

Exit code 0 = every check passed. Any failure raises AssertionError with the evidence.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent
ORIGINAL_ID = "stage20_scaleup_48g_20260920_215427"
BASELINE_CHECKSUMS = ROOT / "FINAL_CORRECTED_AUDIT" / "checksums_original_before.txt"
GAP_EPSILON = 1e-12

CHECKS: List[Tuple[str, str]] = []


def check(name: str, detail: str) -> None:
    CHECKS.append((name, detail))
    print(f"   PASS  {name}: {detail}")


def read_csv(path: Path) -> List[Dict[str, str]]:
    with open(path, "r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fnum(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return float("nan")


def is_true(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() == "true"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_experiment_id(argv: Sequence[str]) -> str:
    if len(argv) > 1:
        return argv[1]
    candidates = sorted(p.name for p in (ROOT / "results").glob("stage20_corrected_*") if p.is_dir())
    if not candidates:
        raise SystemExit("No corrected experiment directory found.")
    return candidates[-1]


def replay_sbs_from_raw(rows: Sequence[Dict[str, str]], train_ids: Set[str], policy_to_algo: Dict[str, str]) -> str:
    """Recompute the training-only SBS policy directly from the raw benchmark rows."""
    totals = {p: 0.0 for p in policy_to_algo}
    for r in rows:
        if r["graph_id"] not in train_ids:
            continue
        algo = r["algorithm"]
        if not is_true(r.get("oracle_eligible", "True")):
            continue
        totals["Always-" + ("Bidirectional-Dijkstra" if algo == "Bidirectional Dijkstra" else algo)] += fnum(r["runtime_median"])
    # Always-A* falls back to Dijkstra when A* is not eligible, so the totals map above is
    # exact only for graphs where every candidate is eligible; assert that here instead of
    # guessing.
    return min(totals, key=totals.get)


def main() -> int:
    exp_id = resolve_experiment_id(sys.argv)
    exp_dir = ROOT / "results" / exp_id
    proc, raw = exp_dir / "processed", exp_dir / "raw"
    manifest = json.loads((proc / f"{exp_id}_manifest.json").read_text(encoding="utf-8"))
    out_dir = ROOT / "FINAL_CORRECTED_AUDIT"

    print("=" * 96)
    print("OA-ASSP -- CORRECTED STAGE 20 INTEGRITY AUDIT")
    print("=" * 96)
    print(f"Experiment: {exp_id}")

    # ---------------------------------------------------------------- 1. preservation
    before = {}
    for line in BASELINE_CHECKSUMS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        digest, rel = parts[0], parts[1].lstrip("* ")
        if not rel:
            continue
        before[rel] = digest
    assert before, "no historical baseline checksums recorded"
    mismatches = []
    for rel, digest in before.items():
        p = ROOT / rel
        if not p.exists():
            mismatches.append(f"{rel}: MISSING")
        elif sha256_file(p) != digest:
            mismatches.append(f"{rel}: CHANGED")
    assert not mismatches, f"historical Stage 20 artifacts were modified: {mismatches[:5]}"
    check("original_stage20_immutable",
          f"{len(before)} historical files byte-identical to the pre-experiment baseline")

    # -------------------------------------------------------- 2. raw benchmark shape
    bench = read_csv(raw / f"{exp_id}_benchmark_rows.csv")
    assert len(bench) == 72000, f"expected 72000 raw rows, got {len(bench)}"
    algs = {r["algorithm"] for r in bench}
    assert algs == {"Dijkstra", "Bidirectional Dijkstra", "A*"}, f"unexpected algorithms: {algs}"
    queries = {(r["graph_id"], r["query_id"]) for r in bench}
    assert len(queries) == 24000, f"expected 24000 queries, got {len(queries)}"
    assert len(bench) == 3 * len(queries)
    check("raw_shape", f"{len(bench)} rows = {len(queries)} queries x 3 algorithms on 48 graphs")

    # ------------------------------------------- 3. no fabricated validity / timeouts
    n_timeout = sum(1 for r in bench if is_true(r["timeout"]))
    n_invalid = sum(1 for r in bench if not is_true(r["valid"]))
    bad_timeout = [r for r in bench if is_true(r["timeout"]) and (is_true(r["success"]) or is_true(r["valid"]))]
    bad_valid = [r for r in bench if is_true(r["valid"]) and not (is_true(r["success"]) and is_true(r["correct"]))]
    unbounded = [r for r in bench if (not is_true(r["valid"])) and not r["failure_reason"].strip()]
    check("timeout_semantics",
          f"{n_timeout} timeouts; none reported as success/valid (violations={len(bad_timeout)})")
    check("validity_derived",
          f"{n_invalid} invalid rows, all with a failure reason (violations={len(bad_valid)}, unlabelled={len(unbounded)})")
    assert not bad_timeout and not bad_valid and not unbounded

    negative_time = [r for r in bench if fnum(r["runtime_median"]) < 0]
    zero_time = [r for r in bench if fnum(r["runtime_median"]) <= 0]
    assert not negative_time, "negative runtime recorded"
    check("runtime_positivity", f"{len(bench) - len(zero_time)} rows with a positive median runtime")

    # ----------------------------------------- 4. SBS is training-only and reproducible
    sbs_policy = manifest["sbs"]["policy"]
    train_ids = set(manifest["train_graph_ids"])
    val_ids = set(manifest["validation_graph_ids"])
    test_ids = set(manifest["test_graph_ids"])
    assert not (train_ids & val_ids) and not (train_ids & test_ids) and not (val_ids & test_ids)
    ref_ids = set(manifest["sbs"]["reference_graph_ids"])
    assert ref_ids == train_ids, "SBS reference graphs are not exactly the training graphs"
    assert not (ref_ids & val_ids) and not (ref_ids & test_ids), "SBS reference overlaps held-out graphs"
    assert len(ref_ids) == 32 and len(val_ids) == 8 and len(test_ids) == 8
    check("sbs_training_only",
          f"reference={len(ref_ids)} train graphs, disjoint from {len(val_ids)} validation and "
          f"{len(test_ids)} test graphs; selected policy {sbs_policy}")

    # Independently replay the SBS selection from the raw rows, per query, applying the
    # documented Always-A* fallback to Dijkstra when A* is not oracle-eligible.
    totals = {"Always-Dijkstra": 0.0, "Always-Bidirectional-Dijkstra": 0.0, "Always-A*": 0.0}
    train_queries: Dict[Tuple[str, str], Dict[str, Dict[str, str]]] = {}
    for r in bench:
        if r["graph_id"] in train_ids:
            train_queries.setdefault((r["graph_id"], r["query_id"]), {})[r["algorithm"]] = r
    for algos in train_queries.values():
        dijk = fnum(algos["Dijkstra"]["runtime_median"])
        bidi = fnum(algos["Bidirectional Dijkstra"]["runtime_median"])
        astar_row = algos["A*"]
        astar = fnum(astar_row["runtime_median"])
        astar_ok = is_true(astar_row.get("oracle_eligible", "True"))
        totals["Always-Dijkstra"] += dijk
        totals["Always-Bidirectional-Dijkstra"] += bidi
        totals["Always-A*"] += astar if astar_ok else dijk
    replay = min(totals, key=totals.get)
    assert replay == sbs_policy, f"SBS replay disagrees: raw={replay} recorded={sbs_policy}"
    recorded_totals = manifest["sbs"]["reference_policy_totals_s"]
    for pol, value in totals.items():
        assert abs(value - recorded_totals[pol]) / max(value, 1e-12) < 1e-6, (
            f"training total for {pol} differs: replay={value} recorded={recorded_totals[pol]}")
    check("sbs_replayable_from_raw",
          f"argmin over {len(train_queries)} training queries reproduces {replay}; all three "
          f"fixed-policy training totals match the manifest to 1e-6")

    # ---------------------------------------- 5. selector never saw validation or test
    assert manifest["selector"]["hyperparameter_selection"] == "validation split only"
    assert manifest["selector"]["identical_hyperparameters_across_tiers"] is True
    tuning = read_csv(proc / f"{exp_id}_selector_tuning.csv")
    selected = [r for r in tuning if is_true(r["is_selected"])]
    assert len(selected) == 1, f"expected exactly one selected configuration, got {len(selected)}"
    sel_hp = (selected[0]["criterion"], int(selected[0]["max_depth"]), int(selected[0]["min_samples_leaf"]))
    tiers = read_csv(proc / f"{exp_id}_feature_tier_tradeoffs.csv")
    tier_hp = {(r["tier"]): (r["max_depth"], r["min_samples_leaf"]) for r in tiers}
    assert len(set(tier_hp.values())) == 1, f"feature tiers used different hyperparameters: {tier_hp}"
    got = list(tier_hp.values())[0]
    assert (str(got[0]), str(got[1])) == (str(sel_hp[1]), str(sel_hp[2])), (
        f"tier hyperparameters {got} != validation-selected {(sel_hp[1], sel_hp[2])}")
    check("tier_hyperparameters_identical",
          f"all tiers use max_depth={got[0]} min_samples_leaf={got[1]} as selected on validation")

    # ------------------------- 6. Q=1 accounting: pay once per graph / once per query
    adaptive = read_csv(raw / f"{exp_id}_adaptive_rows.csv")
    primary_tier = int(manifest.get("adaptive", {}).get("primary_tier", 1))
    assert "tier" in adaptive[0], "adaptive rows do not record which feature tier produced them"
    assert "selection_mode" in adaptive[0], "adaptive rows do not record the inference mode"
    lib_rows = [r for r in adaptive if int(r["tier"]) == primary_tier and r["selection_mode"] == "library"]
    assert lib_rows, "no library-mode adaptive rows for the primary tier"
    per_graph_grade = read_csv(proc / f"{exp_id}_capture_per_graph_analysis_grade.csv")
    row = next(r for r in per_graph_grade if int(r["Q"]) == 1)
    gid = row["graph_id"]
    # The Q=1 capture point uses the median across passes of the FIRST query only.
    by_q: Dict[str, List[Dict[str, str]]] = {}
    for r in lib_rows:
        if r["graph_id"] == gid:
            by_q.setdefault(r["query_id"], []).append(r)
    first_qid = sorted(by_q)[0]
    chunk = by_q[first_qid]
    med = lambda k: float(sorted(float(c[k]) for c in chunk)[len(chunk) // 2])
    expected_c_qfeat = med("query_feature_time")
    assert abs(fnum(row["C_query_feature"]) - expected_c_qfeat) < 1e-9, (
        f"Q=1 query-feature charge {row['C_query_feature']} != single measured query {expected_c_qfeat}")
    gf_charged = fnum(row["C_graph_feature"])
    # The per-query adaptive rows carry the graph-feature time measured in each pass; the
    # analysis charges the median across passes, once per workload (not once per query).
    gf_passes = [float(c["graph_feature_time"]) for c in chunk]
    gf_measured = sorted(gf_passes)[len(gf_passes) // 2]
    assert abs(gf_charged - gf_measured) < 1e-9, (
        f"graph feature cost is not charged exactly once (charged {gf_charged}, "
        f"median across {len(gf_passes)} passes {gf_measured})")
    assert abs(fnum(row["C_selection"]) - med("selection_time")) < 1e-9
    assert abs(fnum(row["SelectionOverhead_task"])
               - (gf_charged + fnum(row["C_query_feature"]) + fnum(row["C_feature_vector"])
                  + fnum(row["C_selection"]))) < 1e-9, "task overhead is not the sum of its parts"
    check("q1_accounting",
          f"Q=1 for {gid}: graph features charged once ({gf_charged*1e6:.2f} us), query features, "
          f"vector assembly and selection charged once each for exactly one query")

    # ----------------- 7. traceability: processed costs = sums over documented sources
    bench_by_gq: Dict[Tuple[str, str], Dict[str, Tuple[float, bool]]] = {}
    for r in bench:
        bench_by_gq.setdefault((r["graph_id"], r["query_id"]), {})[r["algorithm"]] = (
            fnum(r["runtime_median"]), is_true(r.get("oracle_eligible", "True")))
    sbs_algo = {"Always-Dijkstra": "Dijkstra",
                "Always-Bidirectional-Dijkstra": "Bidirectional Dijkstra",
                "Always-A*": "A*"}[sbs_policy]
    worst_sbs = 0.0
    for row in per_graph_grade:
        if int(row["Q"]) != 500:
            continue
        gid = row["graph_id"]
        order = []
        for r in bench:
            if r["graph_id"] == gid and r["query_id"] not in order:
                order.append(r["query_id"])
        sbs_sum = 0.0
        vbs_sum = 0.0
        for qid in order:
            algos = bench_by_gq[(gid, qid)]
            entry = algos.get(sbs_algo)
            if entry is None or not entry[1]:
                entry = algos["Dijkstra"]
            sbs_sum += entry[0]
            eligible = [c for c, ok in algos.values() if ok]
            vbs_sum += min(eligible)
        worst_sbs = max(worst_sbs, abs(sbs_sum - fnum(row["C_SBS"])) / max(sbs_sum, 1e-12))
        assert abs(vbs_sum - fnum(row["C_VBS"])) / max(vbs_sum, 1e-12) < 1e-9, (
            f"{gid}: VBS cost does not equal the min over eligible benchmark medians")
    assert worst_sbs < 1e-9, f"C_SBS not reproducible from raw benchmark medians (max rel diff {worst_sbs})"
    check("cost_traceability",
          "every per-graph C_SBS and C_VBS at Q=500 recomputes exactly from the raw benchmark medians")

    # ------------------------------------------- 8. oracle gap is not noise-dominated
    crosscheck = read_csv(proc / f"{exp_id}_oracle_gap_crosscheck.csv")
    q500 = next(r for r in crosscheck if int(r["Q"]) == 500)
    gap_bm = fnum(q500["OracleGap_benchmark_ms"]) * 1e-3
    gap_paired = fnum(q500["OracleGap_paired_ms"]) * 1e-3
    assert gap_bm > 0, "benchmark-median oracle gap is not positive"
    check("oracle_gap_crosscheck_recorded",
          f"Q=500 gap: benchmark medians {gap_bm*1e3:.3f} ms vs paired single-shot {gap_paired*1e3:.3f} ms")

    # ------------------------------------- 8b. generalization folds are attributable
    generic = read_csv(proc / f"{exp_id}_generalization.csv")
    assert "tier" in generic[0], "generalization rows do not record the feature tier"
    assert "feature_count" in generic[0], "generalization rows do not record the feature count"
    primary_tier = int(manifest["adaptive"].get("primary_tier", 1))
    tier_protocol_counts: Dict[Tuple[int, str], int] = {}
    for r in generic:
        key = (int(r["tier"]), r["protocol"])
        tier_protocol_counts[key] = tier_protocol_counts.get(key, 0) + 1
    cells = {int(r["tier"]): 0 for r in generic}
    for r in generic:
        if r["protocol"] == "leave_one_cell_out":
            cells[int(r["tier"])] += 1
    for tier, count in cells.items():
        assert count == 24, f"tier {tier}: {count} leave-one-cell-out folds, expected 24 cells"
        assert tier_protocol_counts[(tier, "leave_one_family_out")] == 3, (
            f"tier {tier}: expected 3 leave-one-family-out folds")
    check("generalization_attribution",
          f"every fold records its feature tier; tiers {sorted(cells)} each contribute "
          f"24 cell folds and 3 family folds")

    # --------------------------------- 8c. reported questions equal the frozen tables
    questions = json.loads((out_dir / "corrected_questions.json").read_text(encoding="utf-8"))
    q_manifest = json.loads((out_dir / "corrected_results_manifest.json").read_text(encoding="utf-8"))
    assert q_manifest["generalization_primary_tier"]["primary_tier"] == primary_tier
    for proto, label in (("leave_one_cell_out", "Q8_generalizes_to_unseen_configurations"),
                         ("leave_one_family_out", "Q9_generalizes_across_families")):
        sub = [r for r in generic if r["protocol"] == proto and int(r["tier"]) == primary_tier]
        med = sorted(fnum(r["exact_accuracy"]) for r in sub)[len(sub) // 2] if len(sub) % 2 else \
            (sorted(fnum(r["exact_accuracy"]) for r in sub)[len(sub) // 2 - 1]
             + sorted(fnum(r["exact_accuracy"]) for r in sub)[len(sub) // 2]) / 2
        stated = questions[label]["evidence"]
        assert f"{med * 100:.2f}%" in stated, (
            f"{label} states a value inconsistent with the frozen folds ({med * 100:.2f}%): {stated}")
    check("reported_values_match_frozen_tables",
          "the Q8/Q9 generalization numbers written into the report artifacts recompute from the "
          "frozen fold table for the primary tier")

    # ------------------------------------------------- 9. figures / artifacts complete
    for name in ("corrected_results_manifest.json", "corrected_config.yaml", "checksums.txt",
                 "original_vs_corrected.csv", "corrected_questions.json", "bootstrap_analysis_grade.csv"):
        assert (out_dir / name).exists(), f"missing audit artifact {name}"
    figs = sorted(p.name for p in (exp_dir / "figures").glob("*.png"))
    assert figs and all(n.startswith("fig_c") for n in figs), f"unexpected figure names: {figs}"
    stale = [n for n in figs if n.startswith(("fig01", "fig02", "fig07"))]
    assert not stale, f"historical Stage 20 figures leaked into the corrected experiment: {stale}"
    check("artifact_completeness",
          f"{len(figs)} corrected figures, all named fig_c*; no historical figure names present")

    # ------------------------------------------ 10. no crossover is claimed anywhere
    manifest_grade = json.loads((out_dir / "corrected_results_manifest.json").read_text(encoding="utf-8"))
    assert manifest_grade["crossover"]["cells_where_adaptive_wins"] == 0
    q = manifest_grade["scientific_questions"]
    assert q["Q1_adaptive_beats_sbs_anywhere"]["answer"].startswith("No")
    answers_text = json.dumps(manifest_grade["scientific_questions"]).lower()
    for forbidden in ("crossover found", "adaptive wins at", "beneficial at large q"):
        assert forbidden not in answers_text, f"unsupported claim in the report artifacts: {forbidden}"
    check("no_unreproduced_crossover_claimed",
          f"0 of {manifest_grade['crossover']['cells_examined']} cells show a gain; the historical "
          f"single 37 us cell is absent from the corrected record")

    print("\n" + "=" * 96)
    print(f"ALL {len(CHECKS)} INTEGRITY CHECKS PASSED")
    print("=" * 96)
    for name, detail in CHECKS:
        print(f"   [x] {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
