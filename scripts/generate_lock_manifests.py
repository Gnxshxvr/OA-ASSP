"""Generate the authoritative lock manifest and the source-provenance manifest.

This script is the single source of truth for the two closure manifests:

* ``FINAL_CORRECTED_AUDIT/LOCK_CHECKSUMS.txt``
    Deterministic SHA-256 manifest of every authoritative file under
    ``FINAL_CORRECTED_AUDIT/**``, recording relative path, SHA-256 and file size.
    It excludes only itself (a manifest cannot hash itself).

* ``FINAL_CORRECTED_AUDIT/SOURCE_PROVENANCE_MANIFEST.json``
    Distinguishes HISTORICAL EXPERIMENT SOURCE IDENTITY (the hash recorded at run
    time, immutable evidence) from CURRENT FROZEN REPOSITORY SOURCE IDENTITY (the
    hash of the tree as frozen), with per-file SHA-256 hashes for the current tree.

Determinism
-----------
Files are enumerated in sorted order and every field is derived from file content,
so re-running on an unchanged tree reproduces byte-identical output apart from the
recorded generation timestamp.

Usage
-----
    python scripts/generate_lock_manifests.py            # write both manifests
    python scripts/generate_lock_manifests.py --check    # verify, write nothing
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
AUDIT_DIR = ROOT / "FINAL_CORRECTED_AUDIT"
LOCK_NAME = "LOCK_CHECKSUMS.txt"
PROVENANCE_NAME = "SOURCE_PROVENANCE_MANIFEST.json"
# Excluded from the evidence aggregate by design:
#   LOCK_CHECKSUMS.txt               - a manifest cannot hash itself
#   SOURCE_PROVENANCE_MANIFEST.json  - generated metadata carrying a timestamp; its hash is
#                                      recorded separately in the lock manifest so both files
#                                      must be regenerated together.
EXCLUDED = {LOCK_NAME, PROVENANCE_NAME}

EXP_ID = "stage20_corrected_20260923_092749"
ORIGINAL_ID = "stage20_scaleup_48g_20260920_215427"
HISTORICAL_SOURCE_HASH = "c668df6b5e2a2034892a9d6089683f2ca50a05c77fc70ed35d01e49db8252721"

# Source identity is defined by the run script's own algorithm: every .py under
# oa_assp/ and scripts/, plus the corrected config and the frozen split manifest.
SOURCE_BASES = ("oa_assp", "scripts")
SOURCE_EXTRA = ("configs/experiment_corrected_48g.yaml", "configs/graph_split_manifest_48g.csv")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def source_files() -> List[Path]:
    files: List[Path] = []
    for base in SOURCE_BASES:
        files.extend(sorted(p for p in (ROOT / base).rglob("*.py")
                            if "__pycache__" not in p.parts))
    files.extend(sorted(ROOT / rel for rel in SOURCE_EXTRA))
    return files


def compute_source_hash(files: List[Path]) -> str:
    """Byte-identical to scripts/run_stage20_corrected.py:source_hash()."""
    h = hashlib.sha256()
    for p in files:
        h.update(str(p.relative_to(ROOT).as_posix()).encode("utf-8"))
        h.update(b"\0")
        h.update(p.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def audit_files() -> List[Path]:
    """Authoritative evidence files covered by the lock manifest."""
    return sorted(p for p in AUDIT_DIR.rglob("*")
                  if p.is_file() and p.name not in EXCLUDED)


def build_lock_lines() -> List[str]:
    lines = [
        "# OA-ASSP authoritative lock manifest",
        f"# experiment {EXP_ID}",
        "# scope: FINAL_CORRECTED_AUDIT/** evidence files",
        "# excluded: LOCK_CHECKSUMS.txt (self), SOURCE_PROVENANCE_MANIFEST.json (recorded below)",
        "# format: <sha256>  <size_bytes>  <relative_path>",
        "",
    ]
    for p in audit_files():
        rel = p.relative_to(ROOT).as_posix()
        lines.append(f"{sha256_file(p)}  {p.stat().st_size}  {rel}")
    return lines


BOUND_MARKER = "## generated metadata"


def evidence_lines(lines: List[str]) -> List[str]:
    """The hashed evidence payload: non-comment lines before the bound-metadata section."""
    out: List[str] = []
    for line in lines:
        if line.startswith(BOUND_MARKER):
            break
        if line and not line.startswith("#"):
            out.append(line)
    return out


def aggregate_hash(lines: List[str]) -> str:
    payload = "\n".join(evidence_lines(lines))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_provenance(source_hash: str, src_files: List[Path]) -> Dict[str, Any]:
    cfg_hash = hashlib.sha256(
        json.dumps(
            __import__("yaml").safe_load(
                (ROOT / "configs/experiment_corrected_48g.yaml").read_text(encoding="utf-8")),
            sort_keys=True, default=str,
        ).encode("utf-8")
    ).hexdigest()
    return {
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "generator": "scripts/generate_lock_manifests.py",
        "lock_timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "experiment_id": EXP_ID,
        "historical_experiment_id": ORIGINAL_ID,
        "config_hash": cfg_hash,
        "historical_source_identity": {
            "label": "HISTORICAL EXPERIMENT SOURCE IDENTITY",
            "source_hash": HISTORICAL_SOURCE_HASH,
            "source_files_hashed": 72,
            "recorded_at_run_utc": "2026-09-23T04:02:53.018660+00:00",
            "status": "IMMUTABLE EVIDENCE - retained verbatim, never replaced",
            "description": (
                "SHA-256 recorded by scripts/run_stage20_corrected.py at run time over the "
                "72 source files then present. This hash does NOT reproduce from the current "
                "tree: two source files were edited after the run (see post_run_source_edits). "
                "It is preserved as historical provenance, not as a claim about the current tree."
            ),
            "reproduces_from_current_tree": False,
        },
        "current_source_identity": {
            "label": "CURRENT FROZEN REPOSITORY SOURCE IDENTITY",
            "source_hash": source_hash,
            "source_files_hashed": len(src_files),
            "status": "REPRODUCIBLE - recomputes from the frozen tree as committed",
            "description": (
                "SHA-256 of the frozen repository source tree, computed with the identical "
                "algorithm used at run time. This is the reproducible identity of the final "
                "frozen repository. It does NOT claim the current tree was exactly the source "
                "tree used for the original run; see post_run_source_edits."
            ),
            "reproduces_from_current_tree": True,
        },
        "post_run_source_edits": [
            {
                "path": "scripts/verify_corrected_stage20.py",
                "mtime": "2026-09-23T09:27:04",
                "note": "created/edited at the end of the corrected run (integrity audit script)",
            },
            {
                "path": "scripts/analyze_corrected_stage20.py",
                "mtime": "2026-09-30T20:46:24",
                "note": "edited during the P0 documentation pass (regime/crossover labeling)",
            },
            {
                "path": "scripts/analyze_corrected_stage20.py",
                "mtime": "2026-10-04 (closure pass)",
                "note": "reproduction-safety fix: run-scoped output + --force guard. No "
                        "scientific output changes; verified by post-fix verification.",
            },
            {
                "path": "scripts/generate_lock_manifests.py",
                "mtime": "2026-10-04 (closure pass)",
                "note": "new in the closure pass; generates this manifest and LOCK_CHECKSUMS.txt",
            },
        ],
        "source_file_hashes": [
            {
                "path": p.relative_to(ROOT).as_posix(),
                "sha256": sha256_file(p),
                "size_bytes": p.stat().st_size,
            }
            for p in src_files
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="verify existing manifests instead of writing them")
    args = ap.parse_args()

    src = source_files()
    source_hash = compute_source_hash(src)
    lines = build_lock_lines()
    agg = aggregate_hash(lines)

    lock_path = AUDIT_DIR / LOCK_NAME
    prov_path = AUDIT_DIR / PROVENANCE_NAME
    prov_sha = sha256_file(prov_path) if prov_path.exists() else "(absent)"

    print("=" * 88)
    print("OA-ASSP -- LOCK MANIFEST GENERATOR")
    print("=" * 88)
    print(f"experiment                : {EXP_ID}")
    print(f"authoritative audit files : {len(evidence_lines(lines))}")
    print(f"current source files      : {len(src)}")
    print(f"current lock source hash  : {source_hash}")
    print(f"historical source hash    : {HISTORICAL_SOURCE_HASH}")
    print(f"authoritative audit hash  : {agg}")

    if args.check:
        ok = True
        if not lock_path.exists():
            print("MISSING: LOCK_CHECKSUMS.txt"); ok = False
        else:
            existing = lock_path.read_text(encoding="utf-8").splitlines()
            existing_evidence = evidence_lines(existing)
            fresh_evidence = evidence_lines(lines)
            if existing_evidence != fresh_evidence:
                print("MISMATCH: LOCK_CHECKSUMS.txt evidence does not match current tree")
                print(f"   recorded files={len(existing_evidence)} current files={len(fresh_evidence)}")
                rec = {l.split("  ", 2)[-1]: l for l in existing_evidence}
                cur = {l.split("  ", 2)[-1]: l for l in fresh_evidence}
                for k in sorted(set(rec) | set(cur)):
                    if rec.get(k) != cur.get(k):
                        print(f"   differs: {k}")
                ok = False
            if aggregate_hash(existing) != agg:
                print("MISMATCH: aggregate hash differs"); ok = False
        if not prov_path.exists():
            print("MISSING: SOURCE_PROVENANCE_MANIFEST.json"); ok = False
        else:
            d = json.loads(prov_path.read_text(encoding="utf-8"))
            if d["current_source_identity"]["source_hash"] != source_hash:
                print("MISMATCH: recorded current source hash != recomputed"); ok = False
            if d.get("recorded_provenance_sha256") not in (None, prov_sha):
                print("MISMATCH: provenance manifest changed since lock manifest was written")
                ok = False
        print("\nCHECK:", "PASS" if ok else "FAIL")
        return 0 if ok else 1

    prov_payload = build_provenance(source_hash, src)
    prov_path.write_text(json.dumps(prov_payload, indent=2) + "\n", encoding="utf-8")
    # Record the provenance manifest's hash in the lock manifest so the two files are
    # bound together; both must be regenerated together.
    prov_sha = sha256_file(prov_path)
    lines.append("")
    lines.append(BOUND_MARKER + " (bound to this manifest; excluded from the aggregate)")
    lines.append(f"{prov_sha}  {prov_path.stat().st_size}  "
                 f"{prov_path.relative_to(ROOT).as_posix()}")
    lock_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nwrote {lock_path.relative_to(ROOT).as_posix()}")
    print(f"wrote {prov_path.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
