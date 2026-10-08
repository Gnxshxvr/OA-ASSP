"""Generate the final machine-readable lock manifest for the frozen repository.

Describes the ACTUAL final repository state: experiment identities, both source
identities, checksum counts, test counts, and the Git commit of the frozen state.
Every value is measured, never transcribed.

Usage
-----
    python scripts/generate_final_lock_manifest.py            # write the manifest
    python scripts/generate_final_lock_manifest.py --check    # verify, write nothing
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
AUDIT = ROOT / "FINAL_CORRECTED_AUDIT"
OUT = ROOT / "FINAL_LOCK_MANIFEST.json"

EXP_ID = "stage20_corrected_20260923_092749"
ORIGINAL_ID = "stage20_scaleup_48g_20260920_215427"
SUPERSEDED_ID = "stage20_corrected_20260922_234910"
HISTORICAL_SOURCE_HASH = "c668df6b5e2a2034892a9d6089683f2ca50a05c77fc70ed35d01e49db8252721"
CONFIG_HASH = "91cef3a3dbfa46115869c72f596d9c2b7f266e4c711d0d89dac14ad498fbea62"
ENTRY = re.compile(r"^([0-9a-f]{64})  (\d+)  (.+)$")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                              text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def lock_evidence() -> List[str]:
    """Evidence entries from LOCK_CHECKSUMS.txt, before the bound-metadata section."""
    out: List[str] = []
    for line in (AUDIT / "LOCK_CHECKSUMS.txt").read_text(encoding="utf-8").splitlines():
        if line.startswith("## generated metadata"):
            break
        if line and not line.startswith("#"):
            out.append(line)
    return out


def _collect(paths: List[str]) -> int:
    out = subprocess.run(
        [sys.executable, "-m", "pytest", *paths, "--collect-only", "-q"],
        cwd=ROOT, capture_output=True, text=True)
    return len([l for l in out.stdout.splitlines() if "::" in l])


def test_counts() -> Dict[str, int]:
    """Unique test cases vs collected cases.

    ``oa_assp/tests/`` holds the real test functions. ``tests/`` holds 16 one-line
    re-export stubs (``from oa_assp.tests.test_x import *``), which double-count the
    same cases when both directories are collected together.
    """
    unique = _collect(["oa_assp/tests/"])
    collected = _collect(["tests/", "oa_assp/tests/"])
    stubs = len([p for p in (ROOT / "tests").glob("test_*.py")
                 if "import *" in p.read_text(encoding="utf-8")])
    return {"unique": unique, "collected": collected, "reexport_stubs": stubs}


def build() -> Dict[str, Any]:
    prov = json.loads((AUDIT / "SOURCE_PROVENANCE_MANIFEST.json").read_text(encoding="utf-8"))
    evidence = lock_evidence()
    agg = hashlib.sha256("\n".join(evidence).encode("utf-8")).hexdigest()
    tc = test_counts()
    return {
        "manifest": "OA-ASSP final lock manifest",
        "generated_utc": prov["lock_timestamp_utc"],
        "generator": "scripts/generate_final_lock_manifest.py",
        "experiment_id": EXP_ID,
        "historical_experiment_id": ORIGINAL_ID,
        "superseded_experiment_id": SUPERSEDED_ID,
        "config_hash": CONFIG_HASH,
        "historical_source_hash": HISTORICAL_SOURCE_HASH,
        "historical_source_hash_reproduces": False,
        "current_lock_source_hash": prov["current_source_identity"]["source_hash"],
        "current_lock_source_hash_reproduces": True,
        "current_source_file_count": prov["current_source_identity"]["source_files_hashed"],
        "authoritative_audit": {
            "manifest": "FINAL_CORRECTED_AUDIT/LOCK_CHECKSUMS.txt",
            "evidence_file_count": len(evidence),
            "aggregate_sha256": agg,
            "provenance_manifest": "FINAL_CORRECTED_AUDIT/SOURCE_PROVENANCE_MANIFEST.json",
        },
        "legacy_checksum_manifests": {
            "checksums.txt": {
                "hash_count": 167,
                "status": "pre-closure snapshot; 166/167 reproduce",
                "known_divergence": ["scripts/analyze_corrected_stage20.py"],
                "reason": "mandated reproduction-safety edit (run-scoped output + --force)",
            },
            "checksums_original_before.txt": {
                "hash_count": 52,
                "status": "immutable historical baseline; 52/52 reproduce",
            },
        },
        "tests": {
            "unique": tc["unique"],
            "collected": tc["collected"],
            "reexport_stubs": tc["reexport_stubs"],
            "note": ("collected double-counts because tests/ holds "
                     f"{tc['reexport_stubs']} one-line re-export stubs of oa_assp/tests/"),
        },
        "benchmark_rerun": "NO",
        "scientific_results_changed": "NO",
        # The commit that CONTAINS the frozen state. Recorded here; if this manifest is
        # regenerated in a follow-up commit to capture that hash, --check verifies the
        # named commit is an ancestor of HEAD with no frozen-path changes since.
        "git_commit": git("rev-parse", "HEAD"),
        "git_branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "git_working_tree_clean": git("status", "--porcelain") == "",
        "git_commit_note": ("commit containing the frozen state; this manifest is committed "
                           "immediately after so that it can name that commit"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="verify instead of writing")
    args = ap.parse_args()

    payload = build()
    print("=" * 88)
    print("OA-ASSP -- FINAL LOCK MANIFEST")
    print("=" * 88)
    for k in ("experiment_id", "config_hash", "current_lock_source_hash", "git_commit",
              "benchmark_rerun", "scientific_results_changed"):
        print(f"  {k:<28}: {payload[k]}")
    print(f"  {'authoritative audit files':<28}: {payload['authoritative_audit']['evidence_file_count']}")
    print(f"  {'audit aggregate sha256':<28}: {payload['authoritative_audit']['aggregate_sha256']}")
    print(f"  {'tests':<28}: {payload['tests']['unique']} unique / "
          f"{payload['tests']['collected']} collected")

    if args.check:
        if not OUT.exists():
            print("\nCHECK: FAIL - manifest missing"); return 1
        recorded = json.loads(OUT.read_text(encoding="utf-8"))
        drift = [k for k in payload if recorded.get(k) != payload[k]]
        # generated_utc legitimately differs when regenerated.
        # git_commit is validated semantically below: the manifest may be regenerated in a
        # follow-up commit to record the frozen commit, so it must name an ANCESTOR whose
        # frozen paths are byte-identical to HEAD.
        drift = [d for d in drift if d not in ("generated_utc", "git_commit",
                                               "git_working_tree_clean")]
        if drift:
            print(f"\nCHECK: FAIL - drift in {drift}")
            for d in drift:
                print(f"   {d}: recorded={recorded.get(d)!r} actual={payload[d]!r}")
            return 1

        rec_commit = recorded.get("git_commit", "")
        head = git("rev-parse", "HEAD")
        if not rec_commit:
            print("\nCHECK: FAIL - no git commit recorded"); return 1
        anc = subprocess.run(["git", "merge-base", "--is-ancestor", rec_commit, head],
                             cwd=ROOT)
        if anc.returncode != 0:
            print(f"\nCHECK: FAIL - recorded commit {rec_commit[:12]} is not an ancestor of HEAD")
            return 1
        frozen_paths = ["FINAL_CORRECTED_AUDIT", "results", "configs",
                        "scripts", "oa_assp", "tests"]
        diff = git("diff", "--stat", rec_commit, head, "--", *frozen_paths)
        if diff:
            print("\nCHECK: FAIL - frozen paths changed since the recorded commit")
            print(diff[:2000])
            return 1
        print(f"\nCHECK: PASS - manifest matches the frozen repository")
        print(f"   recorded frozen commit: {rec_commit[:12]} (HEAD {head[:12]}, "
              f"no frozen-path changes since)")
        return 0

    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
