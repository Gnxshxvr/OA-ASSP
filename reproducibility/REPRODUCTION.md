# OA-ASSP — Reproduction and Verification

Authoritative experiment: `stage20_corrected_20260923_092749`
Historical experiment (immutable): `stage20_scaleup_48g_20260920_215427`

> **`FINAL_CORRECTED_AUDIT/` is READ-ONLY.** Every analysis and audit script writes to a run-scoped
> `audit_runs/<run_id>/` directory by default. Writing into the frozen package requires an explicit
> `--output-dir FINAL_CORRECTED_AUDIT --force` and is only for regenerating the record itself.

---

## A. Re-running the experiment (produces a NEW experiment id)

The corrected benchmark writes `results/stage20_corrected_<timestamp>/` and does **not** modify the
frozen audit package.

```bash
python -u scripts/run_stage20_corrected.py      # benchmark + adaptive passes + tuning + generalization (~5 min)
```

This creates a new experiment directory. The frozen `stage20_corrected_20260923_092749` is never
overwritten.

---

## B. Post-hoc analysis (run-scoped, non-destructive)

```bash
python -u scripts/analyze_corrected_stage20.py                 # newest experiment -> audit_runs/analyze_<ts>/
python -u scripts/analyze_corrected_stage20.py <experiment_id> # pin an experiment
python -u scripts/analyze_corrected_stage20.py --output-dir my_out   # explicit safe location
```

Default output: `audit_runs/analyze_<UTC timestamp>/`.
Refuses `--output-dir FINAL_CORRECTED_AUDIT` without `--force`.

---

## C. Verification sequence

Run in this order. Every step below is read-only with respect to the frozen package except where
noted; steps 6 and 7 write only to `audit_runs/`.

| # | Step | Command | Writes |
|---|---|---|---|
| 1 | Unit tests | `python -m pytest tests/ oa_assp/tests/ -q` | cache only |
| 2 | Environment / config identity | `python -u scripts/generate_lock_manifests.py --check` | nothing |
| 3 | Closure manifest verification | `python -u scripts/verify_lock_manifests.py` | nothing |
| 4 | Integrity audit (15 checks) | `python -u scripts/verify_corrected_stage20.py` | nothing |
| 5 | Legacy checksum replay | included in step 3 | nothing |
| 6 | P0 verification (10 checks) | `python -u scratch/p0_core.py` | `audit_runs/p0_<ts>/` |
| 7 | Independent recomputation | `python -u scratch/adversarial_recompute.py` | `audit_runs/adversarial_<ts>/` |
| 8 | Solver correctness (10 checks) | `python -u scratch/solver_correctness_audit.py` | nothing |
| 9 | Historical immutability | included in step 4 (check 1) + step 3 | nothing |
| 10 | Scientific immutability gate | `python -u scratch/verify_scientific_immutability.py` | nothing |
| 11 | Final lock verification | `python -u scripts/verify_lock_manifests.py` | nothing |

```bash
# full sequence
python -m pytest tests/ oa_assp/tests/ -q
python -u scripts/generate_lock_manifests.py --check
python -u scripts/verify_lock_manifests.py
python -u scripts/verify_corrected_stage20.py
python -u scratch/p0_core.py
python -u scratch/adversarial_recompute.py
python -u scratch/solver_correctness_audit.py
python -u scratch/verify_scientific_immutability.py
python -u scripts/verify_lock_manifests.py
```

### Expected results

| Check | Expected |
|---|---|
| Unit tests | pass — **79 unique tests / 158 collected cases** (the 158 double-counts: `tests/` holds 16 one-line re-export stubs of `oa_assp/tests/`) |
| `generate_lock_manifests.py --check` | `CHECK: PASS` |
| `verify_lock_manifests.py` | `RESULT: PASS` |
| `verify_corrected_stage20.py` | `ALL 15 INTEGRITY CHECKS PASSED` |
| `p0_core.py` | `P0 CORE: 10/10 checks pass` |
| `adversarial_recompute.py` | `64 PASS`, 10 triaged findings (all disclosed; F6 is a resolved **false positive**) |
| `solver_correctness_audit.py` | `SOLVER CORRECTNESS: 10/10 checks passed` |
| `verify_scientific_immutability.py` | `RESULT: PASS - all headline scientific values unchanged` |

---

## D. Provenance

`FINAL_CORRECTED_AUDIT/SOURCE_PROVENANCE_MANIFEST.json` records two distinct identities:

- **HISTORICAL EXPERIMENT SOURCE IDENTITY** — `c668df6b…`, the hash recorded at run time on
  2026-09-23. Immutable evidence. It does **not** reproduce from the current tree.
- **CURRENT FROZEN REPOSITORY SOURCE IDENTITY** — recorded in the manifest and reproducible from
  the frozen tree (74 source files: `oa_assp/**.py`, `scripts/**.py`, the corrected config and the
  frozen split manifest).

The manifest also lists **post-run source edits**, so the divergence between the two identities is
explicit rather than silent. Config hash `91cef3a3…` reproduces exactly.

---

## E. Checksum layers

| Manifest | Scope | Status |
|---|---|---|
| `FINAL_CORRECTED_AUDIT/LOCK_CHECKSUMS.txt` | `FINAL_CORRECTED_AUDIT/**` (44 evidence files; path + SHA-256 + size) | **AUTHORITATIVE** for the frozen tree |
| `FINAL_CORRECTED_AUDIT/SOURCE_PROVENANCE_MANIFEST.json` | source identity + per-file hashes | bound into the lock manifest |
| `FINAL_CORRECTED_AUDIT/checksums.txt` | 167 hashes: 40 experiment + 75 source/config + 52 historical | **pre-closure snapshot**, retained as historical evidence |
| `FINAL_CORRECTED_AUDIT/checksums_original_before.txt` | 52 historical files | immutable baseline, 52/52 reproduce |

`checksums.txt` diverges on exactly one entry, `scripts/analyze_corrected_stage20.py`, which the
closure pass was mandated to change for reproduction safety. It is preserved rather than rewritten,
and the divergence is disclosed in the provenance manifest.

---

## F. What must not be modified after the lock

- `results/stage20_corrected_20260923_092749/**` (authoritative experiment)
- `results/stage20_scaleup_48g_20260920_215427/**` (historical, immutable)
- `FINAL_CORRECTED_AUDIT/**` (audit package; read-only)
- `configs/graph_split_manifest_48g.csv`, `configs/experiment_corrected_48g.yaml` (frozen identity)
- `oa_assp/**`, `scripts/run_stage20_corrected.py` (source of record)

Any change to the above requires a **new experiment version**, not an edit.

## G. What may continue safely after the lock

- Writing the manuscript (drawing only on the frozen corrected record)
- Adding new analysis scripts that write to `audit_runs/`
- New experiments under new experiment IDs (`stage20_corrected_<new timestamp>`)
- Documentation, tests, and tooling that do not alter the frozen artifacts
