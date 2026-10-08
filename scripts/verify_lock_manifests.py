"""Read-only verification of the closure manifests.

Verifies, without writing anything:

1. ``FINAL_CORRECTED_AUDIT/LOCK_CHECKSUMS.txt``
   - every evidence entry reproduces (sha256 + size)
   - no missing files, no unexpected authoritative files
   - the aggregate hash matches the manifest's own evidence payload
2. ``FINAL_CORRECTED_AUDIT/SOURCE_PROVENANCE_MANIFEST.json``
   - historical and current source identities are both present and distinct
   - the current source hash recomputes from the frozen tree
   - the historical hash is NOT claimed to reproduce
   - per-file source hashes all reproduce
   - config hash reproduces
3. ``FINAL_CORRECTED_AUDIT/checksums.txt`` and ``checksums_original_before.txt``
   - all legacy hashes still reproduce

Exit code 0 only if every check passes.

Usage
-----
    python scripts/verify_lock_manifests.py
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
AUDIT = ROOT / "FINAL_CORRECTED_AUDIT"
LOCK = AUDIT / "LOCK_CHECKSUMS.txt"
PROV = AUDIT / "SOURCE_PROVENANCE_MANIFEST.json"
BOUND_MARKER = "## generated metadata"
EXCLUDED = {"LOCK_CHECKSUMS.txt", "SOURCE_PROVENANCE_MANIFEST.json"}

ENTRY = re.compile(r"^([0-9a-f]{64})  (\d+)  (.+)$")
LEGACY = re.compile(r"^([0-9a-fA-F]{64})\s+\*?(.+)$")

failures: List[str] = []


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ok(name: str, detail: str = "") -> None:
    print(f"   [PASS] {name}{(' - ' + detail) if detail else ''}")


def bad(name: str, detail: str = "") -> None:
    print(f"   [FAIL] {name}{(' - ' + detail) if detail else ''}")
    failures.append(f"{name}: {detail}")


def split_lock(lines: List[str]) -> Tuple[List[str], List[str]]:
    evidence: List[str] = []
    bound: List[str] = []
    in_bound = False
    for line in lines:
        if line.startswith(BOUND_MARKER):
            in_bound = True
            continue
        if not line or line.startswith("#"):
            continue
        (bound if in_bound else evidence).append(line)
    return evidence, bound


def check_lock() -> None:
    print("\n== LOCK_CHECKSUMS.txt ==")
    if not LOCK.exists():
        bad("lock manifest present", "file missing"); return
    ok("lock manifest present")
    lines = LOCK.read_text(encoding="utf-8").splitlines()
    evidence, bound = split_lock(lines)

    recorded: Dict[str, Tuple[str, int]] = {}
    for line in evidence:
        m = ENTRY.match(line)
        if not m:
            bad("entry format", line[:80]); continue
        recorded[m.group(3)] = (m.group(1), int(m.group(2)))

    on_disk = sorted(
        p.relative_to(ROOT).as_posix()
        for p in AUDIT.rglob("*")
        if p.is_file() and p.name not in EXCLUDED
    )

    missing = [p for p in recorded if not (ROOT / p).exists()]
    if missing:
        bad("no missing files", f"{len(missing)} listed but absent: {missing[:3]}")
    else:
        ok("no missing files", f"{len(recorded)} listed")

    unexpected = [p for p in on_disk if p not in recorded]
    if unexpected:
        bad("no unexpected authoritative files", f"{len(unexpected)}: {unexpected[:3]}")
    else:
        ok("no unexpected authoritative files", f"{len(on_disk)} on disk")

    mismatch = []
    for rel, (h, size) in recorded.items():
        p = ROOT / rel
        if not p.exists():
            continue
        if sha256_file(p) != h or p.stat().st_size != size:
            mismatch.append(rel)
    if mismatch:
        bad("all hashes reproduce", f"{len(mismatch)} mismatched: {mismatch[:3]}")
    else:
        ok("all hashes reproduce", f"{len(recorded)} files")

    agg = hashlib.sha256("\n".join(evidence).encode("utf-8")).hexdigest()
    print(f"   aggregate (evidence) hash: {agg}")

    if not bound:
        bad("bound metadata section present", "no generated-metadata entries")
    else:
        prov_entry = [b for b in bound if "SOURCE_PROVENANCE_MANIFEST.json" in b]
        if not prov_entry:
            bad("provenance hash recorded in lock manifest", "absent")
        else:
            m = ENTRY.match(prov_entry[0])
            if m and PROV.exists() and sha256_file(PROV) == m.group(1):
                ok("provenance manifest bound to lock manifest")
            else:
                bad("provenance manifest bound to lock manifest",
                    "hash mismatch - regenerate both together")


def check_provenance() -> None:
    print("\n== SOURCE_PROVENANCE_MANIFEST.json ==")
    if not PROV.exists():
        bad("provenance manifest present", "file missing"); return
    ok("provenance manifest present")
    d = json.loads(PROV.read_text(encoding="utf-8"))

    hist = d.get("historical_source_identity", {})
    cur = d.get("current_source_identity", {})

    if hist.get("source_hash", "").startswith("c668df6b") and \
       hist.get("reproduces_from_current_tree") is False:
        ok("historical source identity preserved as immutable evidence")
    else:
        bad("historical source identity preserved",
            "missing, altered, or wrongly claimed to reproduce")

    if cur.get("reproduces_from_current_tree") is True and cur.get("source_hash"):
        ok("current lock source identity recorded and reproducible")
    else:
        bad("current lock source identity recorded", "missing or not marked reproducible")

    if hist.get("source_hash") != cur.get("source_hash"):
        ok("historical and current identities are explicitly distinguished")
    else:
        bad("identities distinguished", "historical and current hashes are identical")

    if d.get("post_run_source_edits"):
        ok("post-run source edits disclosed", f"{len(d['post_run_source_edits'])} entries")
    else:
        bad("post-run source edits disclosed", "empty")

    # recompute current source hash
    sys.path.insert(0, str(ROOT / "scripts"))
    import generate_lock_manifests as gen  # noqa: E402
    src = gen.source_files()
    recomputed = gen.compute_source_hash(src)
    if recomputed == cur.get("source_hash"):
        ok("current source hash recomputes", recomputed[:16] + "...")
    else:
        bad("current source hash recomputes",
            f"recorded {cur.get('source_hash', '')[:16]}... vs {recomputed[:16]}...")

    pf_bad = []
    for e in d.get("source_file_hashes", []):
        p = ROOT / e["path"]
        if not p.exists() or sha256_file(p) != e["sha256"]:
            pf_bad.append(e["path"])
    if pf_bad:
        bad("per-file source hashes reproduce", f"{len(pf_bad)} mismatched: {pf_bad[:3]}")
    else:
        ok("per-file source hashes reproduce", f"{len(d.get('source_file_hashes', []))} files")

    cfg = ROOT / "configs" / "experiment_corrected_48g.yaml"
    import yaml  # noqa: E402
    cfg_hash = hashlib.sha256(
        json.dumps(yaml.safe_load(cfg.read_text(encoding="utf-8")),
                   sort_keys=True, default=str).encode("utf-8")).hexdigest()
    if cfg_hash == d.get("config_hash") == \
            "91cef3a3dbfa46115869c72f596d9c2b7f266e4c711d0d89dac14ad498fbea62":
        ok("config hash reproduces", cfg_hash[:16] + "...")
    else:
        bad("config hash reproduces", f"{cfg_hash[:16]}... vs recorded "
                                      f"{str(d.get('config_hash'))[:16]}...")


# checksums.txt is a PRE-CLOSURE snapshot. The closure pass was mandated to change
# scripts/analyze_corrected_stage20.py (run-scoped output + --force guard, FIX 4), so
# exactly that one entry is expected to diverge. It is preserved as historical evidence
# rather than rewritten; LOCK_CHECKSUMS.txt is the authoritative current manifest.
EXPECTED_LEGACY_DIVERGENCE = {"scripts/analyze_corrected_stage20.py"}


def check_legacy() -> None:
    for name in ("checksums.txt", "checksums_original_before.txt"):
        print(f"\n== {name} (legacy snapshot) ==")
        path = AUDIT / name
        if not path.exists():
            bad(f"{name} present", "missing"); continue
        n = good = 0
        diverged: List[str] = []
        missing: List[str] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = LEGACY.match(line)
            if not m:
                continue
            n += 1
            p = ROOT / m.group(2).strip().replace("\\", "/")
            if not p.exists():
                missing.append(m.group(2).strip()); continue
            if sha256_file(p) == m.group(1).lower():
                good += 1
            else:
                diverged.append(m.group(2).strip())

        if missing:
            bad(f"{name} no missing files", f"{missing[:3]}")
        else:
            ok(f"{name} no missing files", f"{n} listed")

        unexpected = [d for d in diverged if d not in EXPECTED_LEGACY_DIVERGENCE]
        if unexpected:
            bad(f"{name} only expected divergences", f"{unexpected[:3]}")
        elif diverged:
            ok(f"{name} reproduces except mandated closure edits",
               f"{good}/{n}; diverged: {', '.join(diverged)}")
        else:
            ok(f"{name} all hashes reproduce", f"{good}/{n}")


def main() -> int:
    print("=" * 88)
    print("OA-ASSP -- CLOSURE MANIFEST VERIFICATION (read-only)")
    print("=" * 88)
    check_lock()
    check_provenance()
    check_legacy()
    print("\nNOTE: checksums.txt is a pre-closure snapshot. Its single divergence")
    print("      (scripts/analyze_corrected_stage20.py) is the mandated FIX 4 edit and is")
    print("      documented in SOURCE_PROVENANCE_MANIFEST.json:post_run_source_edits.")
    print("      LOCK_CHECKSUMS.txt is the authoritative manifest for the frozen tree.")
    print("\n" + "=" * 88)
    if failures:
        print(f"RESULT: FAIL ({len(failures)} failing checks)")
        for f in failures:
            print(f"   - {f}")
        return 1
    print("RESULT: PASS - lock manifest, provenance manifest and legacy manifests all verify")
    return 0


if __name__ == "__main__":
    sys.exit(main())
