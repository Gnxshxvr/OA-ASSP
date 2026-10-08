# Final File Inventory

This inventory documents the purpose, authority status, and reproduction requirement for all files included in the final release package of OA-ASSP.

---

## 1. Top-Level Package Root

| Path | Purpose | Authoritative? | Archival? | Required for Reproduction? |
|---|---|:---:|:---:|:---:|
| `README.md` | Primary package overview, quickstart, and structure documentation | Yes | No | No |
| `LICENSE.txt` | MIT open-source software license | Yes | No | No |
| `CITATION.cff` | Citation metadata for academic attribution | Yes | No | No |
| `FINAL_LOCK_MANIFEST.json` | Machine-readable cryptographic lock manifest for frozen experiment | Yes | No | Yes |
| `requirements.txt` | Python runtime dependencies specification | Yes | No | Yes |
| `.gitignore` | Version-control exclusion configuration | Yes | No | No |
| `.gitattributes` | Version-control attributes configuration | Yes | No | No |

---

## 2. Manuscript (`manuscript/`)

| Path | Purpose | Authoritative? | Archival? | Required for Reproduction? |
|---|---|:---:|:---:|:---:|
| `manuscript/OA-ASSP_Final_Manuscript.tex` | Final IEEE conference paper LaTeX source (clean, no debug history) | Yes | No | No |
| `manuscript/OA-ASSP_Final_Manuscript.pdf` | Final compiled 10-page camera-ready conference paper PDF | Yes | No | No |
| `manuscript/main.tex` | Canonical build source for LaTeX compilation | Yes | No | No |
| `manuscript/main.pdf` | Canonical compiled PDF output | Yes | No | No |
| `manuscript/PAPER_REVIEW_AUDIT.md` | Simulated IEEE review audit against reviewer concerns | Yes | No | No |
| `manuscript/draft_manuscript.md` | Markdown manuscript companion | Informational | No | No |
| `manuscript/figures/` | Publication vector and raster figures embedded in LaTeX source | Yes | No | No |

---

## 3. Publication Figures (`figures/`)

| Path | Purpose | Authoritative? | Archival? | Required for Reproduction? |
|---|---|:---:|:---:|:---:|
| `figures/fig1_pipeline.pdf` / `.png` | Figure 1: Overhead-priced selection pipeline diagram | Yes | No | No |
| `figures/fig2_cost_vs_q.pdf` / `.png` | Figure 2: Cumulative execution cost vs workload size $Q$ | Yes | No | No |
| `figures/fig3_required_capture.pdf` / `.png` | Figure 3: RequiredCapture trajectory vs $Q$ (break-even line) | Yes | No | No |
| `figures/fig4_overhead_economics.pdf` / `.png` | Figure 4: Computational economics bar chart at $Q=500$ | Yes | No | No |
| `figures/fig5_selector_accuracy.pdf` / `.png` | Figure 5: Exact selector accuracy vs majority-class baseline | Yes | No | No |
| `figures/fig6_per_graph_delta.pdf` / `.png` | Figure 6: Per-graph runtime delta at $Q=500$ vs noise floor | Yes | No | No |
| `figures/README.md` | Documentation of figures and visual encoding | Yes | No | No |

---

## 4. Source Code (`src/` and `oa_assp/`)

| Path | Purpose | Authoritative? | Archival? | Required for Reproduction? |
|---|---|:---:|:---:|:---:|
| `oa_assp/__init__.py` | Package root initialization | Yes | No | Yes |
| `oa_assp/algorithms/` | Implementations of Dijkstra, Bidirectional Dijkstra, A*, Bellman-Ford | Yes | No | Yes |
| `oa_assp/analysis/` | Cost accounting, RequiredCapture, SolverOnlyCapture, crossover logic | Yes | No | Yes |
| `oa_assp/benchmark/` | Multi-repetition benchmark timing harness, warm-up, and timer abstraction | Yes | No | Yes |
| `oa_assp/features/` | Pre-solver graph-level and query-level feature extractors (Tiers 0, 1, 2) | Yes | No | Yes |
| `oa_assp/graphs/` | Deterministic graph generators (ER, geometric, BA) and graph loaders | Yes | No | Yes |
| `oa_assp/selector/` | Decision tree training, cross-validation, and native branch rule compiler | Yes | No | Yes |
| `oa_assp/tests/` | Internal package unit test suite (79 test functions) | Yes | No | Yes |

---

## 5. Reproduction & Verification Scripts (`scripts/`)

| Path | Purpose | Authoritative? | Archival? | Required for Reproduction? |
|---|---|:---:|:---:|:---:|
| `scripts/run_stage20_corrected.py` | Full experiment driver (generates new experiment ID; non-destructive) | Yes | No | Yes |
| `scripts/analyze_corrected_stage20.py` | Non-destructive analysis runner (writes to run-scoped `audit_runs/`) | Yes | No | Yes |
| `scripts/verify_corrected_stage20.py` | 15-check authoritative integrity verifier against raw records | Yes | No | Yes |
| `scripts/verify_lock_manifests.py` | Read-only verification of cryptographic lock and provenance manifests | Yes | No | Yes |
| `scripts/generate_lock_manifests.py` | Manifest generator for `LOCK_CHECKSUMS.txt` & `SOURCE_PROVENANCE_MANIFEST` | Yes | No | Yes |
| `scripts/generate_final_lock_manifest.py` | Verifier and generator for `FINAL_LOCK_MANIFEST.json` | Yes | No | Yes |
| `scripts/run_experiments.py` | Historical experiment runner stub | Informational | Yes | No |
| `scripts/run_preflight_stage20a.py` | Pre-flight smoke validation harness | Informational | Yes | No |
| `scripts/run_selector_pipeline.py` | Pipeline invocation utility | Informational | Yes | No |
| `scripts/run_smoke_test.py` | Quick smoke test runner | Informational | No | Yes |
| `scripts/run_stage20_experiment.py` | Historical experiment driver (superseded) | Archival | Yes | No |
| `scripts/setup_scaleup_manifest.py` | Historical split generator script | Archival | Yes | No |
| `scripts/verify_and_finalize_stage20.py` | Historical integrity audit script (superseded) | Archival | Yes | No |

---

## 6. Unit Tests (`tests/`)

| Path | Purpose | Authoritative? | Archival? | Required for Reproduction? |
|---|---|:---:|:---:|:---:|
| `tests/test_*.py` (15 files) | Test suite entry points and re-export stubs targeting `oa_assp/tests/` | Yes | No | Yes |

---

## 7. Configurations (`configs/`)

| Path | Purpose | Authoritative? | Archival? | Required for Reproduction? |
|---|---|:---:|:---:|:---:|
| `configs/experiment_corrected_48g.yaml` | Authoritative frozen configuration file (hash: `91cef3a3...`) | Yes | No | Yes |
| `configs/graph_split_manifest_48g.csv` | Frozen 48-graph train (32), validation (8), and test (8) split manifest | Yes | No | Yes |
| `configs/stage20_scaleup_48g.yaml` | Historical baseline configuration file | Archival | Yes | No |

---

## 8. Authoritative Audit Evidence (`FINAL_CORRECTED_AUDIT/`)

| Path | Purpose | Authoritative? | Archival? | Required for Reproduction? |
|---|---|:---:|:---:|:---:|
| `LOCK_CHECKSUMS.txt` | Cryptographic SHA-256 seal of all 44 authoritative audit files | Yes | No | Yes |
| `SOURCE_PROVENANCE_MANIFEST.json` | Historical and frozen source tree hashes and post-run disclosures | Yes | No | Yes |
| `corrected_results_manifest.json` | Complete machine-readable experimental aggregates and CIs | Yes | No | Yes |
| `bootstrap_analysis_grade.csv` | Paired graph-level bootstrap point estimates and 95% CIs | Yes | No | Yes |
| `common_query_sbs.csv` | Common-query subset fixed-policy evaluation records | Yes | No | Yes |
| `p0_crossover_unified.csv` | Complete 40-cell unified crossover evaluation table | Yes | No | Yes |
| `p0_noise_floor.csv` | Empirical pass-to-pass dispersion and relative IQR metrics | Yes | No | Yes |
| `p0_regime_reconciliation.csv` | Analysis-grade vs end-to-end physical measured cost table | Yes | No | Yes |
| `original_vs_corrected.csv` | Paired comparison between historical baseline and corrected record | Yes | No | Yes |
| `ADVERSARIAL_AUDIT.md` | Formal response to adversarial audit and forensic recomputations | Yes | No | No |
| `corrected_audit_report.md` | Narrative report on corrected experiment outcomes | Yes | No | No |
| `checksums.txt` | Pre-closure 167-hash legacy snapshot (166/167 reproduce) | Archival | Yes | Yes |
| `checksums_original_before.txt` | Historical 52-hash baseline snapshot (52/52 reproduce) | Archival | Yes | Yes |

---

## 9. Experimental Benchmark Data (`results/`)

| Path | Purpose | Authoritative? | Archival? | Required for Reproduction? |
|---|---|:---:|:---:|:---:|
| `results/stage20_corrected_20260923_092749/` | **Authoritative frozen experiment:** raw query logs & processed CSVs | **Yes** | No | Yes |
| `results/stage20_scaleup_48g_20260920_215427/` | Immutable historical baseline dataset | Informational | Yes | Yes |
| `results/stage20_corrected_20260922_234910/` | Superseded intermediate run (retained for provenance) | Archival | Yes | No |
| `results/_archive_dev/` | Archived development test logs and artifacts | Archival | Yes | No |

---

## 10. Reproducibility Documentation (`reproducibility/`)

| Path | Purpose | Authoritative? | Archival? | Required for Reproduction? |
|---|---|:---:|:---:|:---:|
| `reproducibility/REPRODUCTION.md` | Step-by-step reproduction and verification instructions | Yes | No | Yes |
| `reproducibility/ENVIRONMENT.md` | Hardware, OS, Python, and compiler environment requirements | Yes | No | Yes |
| `reproducibility/RESULTS_MAP.md` | Comprehensive map from paper tables to evidence files | Yes | No | Yes |
| `reproducibility/MANUSCRIPT_EVIDENCE_MAP.md` | Detailed manuscript-to-evidence claim traceability matrix | Yes | No | Yes |
| `reproducibility/FINAL_PROJECT_MANIFEST.json` | Structured metadata for release packaging | Yes | No | Yes |
| `reproducibility/FINAL_FILE_INVENTORY.md` | This file inventory | Yes | No | Yes |
| `reproducibility/FINAL_RELEASE_SHA256SUMS.txt` | Cryptographic SHA-256 manifest of the entire release | Yes | No | Yes |
| `reproducibility/FINAL_CLOSURE_REPORT.md` | Final independent closure audit verdict and report | Yes | No | Yes |
