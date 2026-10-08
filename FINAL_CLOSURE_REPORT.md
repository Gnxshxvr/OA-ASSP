# OA-ASSP Final Research Closure & Reproducibility Audit Report

**Date of Audit:** 2026-10-07 / 2026-10-08  
**Auditor Role:** Independent Reproducibility, Manuscript Consistency & Release Manager  
**Project:** OA-ASSP (Overhead-Aware Adaptive Algorithm Selection for Exact Shortest Paths)  
**Authoritative Experiment ID:** `stage20_corrected_20260923_092749`  
**Historical Experiment ID:** `stage20_scaleup_48g_20260920_215427`  
**Configuration SHA-256:** `91cef3a3dbfa46115869c72f596d9c2b7f266e4c711d0d89dac14ad498fbea62`  
**Current Lock Source SHA-256:** `9759103dd1cb90826a9f64ad876609ba973bc862331c9f5bad0e26f4f6a5ff77`  
**Audit Package Aggregate SHA-256:** `2b901af8e478a5cbd88bdde8167ea311642074b47f2f6fa42289d4d556e166e7`  
**Frozen Git Commit:** `d6ce56284e840cb589c26acee9a70aa26e46acd8`  
**Head Git Commit:** `7ebf2b2d66952201bcb7044dd724809cfd004e55`  

---

## A. Executive Verdict

**FINAL VERDICT: READY FOR FINAL UPLOAD**

The OA-ASSP research project has successfully passed the final independent closure audit. All frozen empirical results remain strictly immutable. Every quantitative, empirical, and methodological claim in the publication manuscript matches the authoritative evidence to the last decimal place. All internal development history and retracted legacy crossovers have been eliminated from the final manuscript and cleanly quarantined in labeled archival records. The repository is organized in a professional, self-contained structure and validated via an automated end-to-end verification sequence.

---

## B. Frozen Experiment Integrity

**Status: PASS**

1. **Experiment Identity:** The authoritative experiment is confirmed as `stage20_corrected_20260923_092749`.
2. **Config Hash Verification:** `91cef3a3dbfa46115869c72f596d9c2b7f266e4c711d0d89dac14ad498fbea62` reproduces exactly across all manifests.
3. **Source Tree Integrity:** The frozen source tree hash (`9759103dd1cb9082...`) recomputes deterministically over all 75 source files (`oa_assp/**`, `scripts/**`, frozen split manifest, and experiment config).
4. **Audit Evidence Hash:** All 44 files in `FINAL_CORRECTED_AUDIT/` match their recorded SHA-256 digests in `LOCK_CHECKSUMS.txt`, producing the byte-identical aggregate hash `2b901af8e478a5cbd88bdde8167ea311642074b47f2f6fa42289d4d556e166e7`.
5. **Historical Baseline Immutability:** All 52 original baseline files in `results/stage20_scaleup_48g_20260920_215427/` match `checksums_original_before.txt` exactly (52/52).
6. **Scientific Immutability Gate (`scratch/verify_scientific_immutability.py`):**
   - SBS $Q=500$: $1064.200\,\mathrm{ms}$ (PASS)
   - VBS $Q=500$: $941.677\,\mathrm{ms}$ (PASS)
   - OracleGap: $122.523\,\mathrm{ms}$ (PASS)
   - Adaptive Library: $1556.250\,\mathrm{ms}$ (PASS)
   - Adaptive Compiled: $1119.723\,\mathrm{ms}$ (PASS)
   - Selection Overhead Library: $472.040\,\mathrm{ms}$ (PASS)
   - Selection Overhead Compiled: $35.513\,\mathrm{ms}$ (PASS)
   - RequiredCapture Library: $3.8527$ (PASS)
   - RequiredCapture Compiled: $0.2898$ (PASS)
   - Solver-Only Capture: $-0.1633$ (PASS)
   - End-to-End Measured: $1191.045\,\mathrm{ms}$ (PASS)
   - Genuine Crossovers: $0 / 40$ (PASS)
   - Nominal Primary Compiled: $3 / 40$ (PASS)
   - Nominal Conservative Compiled: $4 / 40$ (PASS)
   - Max Conservative Nominal Advantage: $-2.419\,\mathrm{ms}$ ($0.227\%$ of SBS) (PASS)
   - Pass-to-Pass Dispersion: Library $16.32\%$, Compiled $9.40\%$ (PASS)
   - Generalization Median Lifts: LOCO T0 $0.00\,\mathrm{pp}$, LOCO T1 $0.00\,\mathrm{pp}$, LOFO T0 $+0.06\,\mathrm{pp}$, LOFO T1 $0.00\,\mathrm{pp}$ (PASS)

---

## C. Manuscript ↔ Evidence Consistency

**Status: PASS**

The complete manuscript (`paper/main.tex` and `manuscript/OA-ASSP_Final_Manuscript.tex`) was audited against the frozen evidence records. A 39-check programmatic audit script (`scratch/verify_paper_numbers.py`) passed all 39 checks without warnings or mismatches.

Key verifications:
* **Graph Corpus:** 48 graphs, 3 families (ER, geometric, BA), $V \in \{40, 80, 160, 320\}$, $D \in \{6, 12\}$, 24 parameter cells, 2 seeds per cell.
* **Partitioning:** 32 train, 8 validation, 8 test graphs. 8 test graphs span 8 of 24 parameter combinations (3 geometric, 3 random, 2 scale-free).
* **Workload:** 500 deterministic queries per graph, 24,000 total queries, 72,000 candidate solver executions.
* **Statistical Unit:** The manuscript explicitly specifies the graph as the resampling unit, correctly stating that the 40 cells are evaluation conditions, not 40 independent samples. Paired graph-level bootstrap with $B=1{,}000$ replicates was conducted.
* **$A^*$ Policy Scoping:** Conservative metadata-driven safety policy on non-geometric graphs; explicitly noted as not claiming empirical proof of heuristic inadmissibility.
* **Complementarity:** Geometric graphs show genuine solver diversity (Bidi $37.8\%$--$66.8\%$, Dijkstra $23.4\%$--$50.4\%$, $A^*$ $5.6\%$--$19.6\%$). The lack of crossover is properly attributed to the $0/1$ loss objective and selector generalization, not absence of problem structure.
* **Overclaim Check:** Automated text analysis confirmed zero occurrences of "proves", "universally", "impossible", "eliminates", "guarantees", "fundamentally", "no prior work", or "always overhead-bound". All conclusions are precisely scoped to the evaluated experimental envelope.
* **Internal Debug History Removal:** The historical retracted crossover paragraph ($\Delta = -0.0371\,\mathrm{ms}$, $+0.79\%$) was removed from Section V-F of the manuscript.

---

## D. Reproducibility Status

**Status: PASS WITH DISCLOSURE**

### Disclosure:
The reproduction procedure has been fully verified and executed through automated verification and validation scripts. In accordance with the project rules ("DO NOT rerun a new research experiment; DO NOT rerun the full benchmark"), the full 72,000-query benchmark (`run_stage20_corrected.py`) was statically verified and sanity-checked, but not re-executed in full to prevent generating redundant compute or risking non-deterministic overwrites.

### Verification Checklist:
- [x] Environment and hardware requirements documented (`ENVIRONMENT.md`)
- [x] Dependencies pinned (`requirements.txt`)
- [x] Random seeds and deterministic generation formulas documented
- [x] Split manifest frozen (`configs/graph_split_manifest_48g.csv`)
- [x] 15-check authoritative integrity audit passed (`verify_corrected_stage20.py`)
- [x] Cryptographic lock manifest passed (`verify_lock_manifests.py`)
- [x] 10-check P0 core verification passed (`p0_core.py`)
- [x] 10-check solver correctness audit passed (`solver_correctness_audit.py`)
- [x] Full test suite passed (79 unique unit tests / 158 collected cases via `pytest`)
- [x] Reproduction sequence documented and operational (`REPRODUCTION.md`)

---

## E. Reference Integrity

**Status: PASS**

- All 17 bibliographic items in the manuscript are authentic, complete, correctly formatted, and cited in ascending numerical order in the body text.
- Automated format audit (`scratch/check_manuscript_format.py`) confirms: 17 bibitems, 17 cited, 0 orphaned, 0 undefined.
- Proper scientific attribution: Algorithm selection is attributed to Rice (1976); portfolio architectures to SATzilla, ASlib, LLAMA, claspfolio 2, and AutoFolio; landscape analysis to Gholami Shiri et al. (2026); and feature budget awareness to van der Blom & Vermetten (2026). No false novelty claims are made.

---

## F. Repository Organization Status

**Status: PASS**

The repository has been structured cleanly into professional, self-explanatory directories:
- `manuscript/`: Final LaTeX source (`OA-ASSP_Final_Manuscript.tex`), compiled PDF, and review audit.
- `figures/`: Vector and high-resolution raster publication figures.
- `src/`: Complete `oa_assp` research library source code.
- `scripts/`: All 13 reproduction and verification scripts.
- `tests/`: 15 unit test modules.
- `configs/`: Frozen experiment configuration and split manifest.
- `data/`: Dataset documentation and generation specifications.
- `experiments/`: Frozen experiment metadata and historical baseline notice.
- `results/`: Authoritative benchmark data (`stage20_corrected_20260923_092749`) and historical records.
- `FINAL_CORRECTED_AUDIT/`: 44 frozen audit evidence files sealed by `LOCK_CHECKSUMS.txt`.
- `supplementary/`: Presentation slide deck, slide renders, and audit reports.
- `reproducibility/`: Complete maps, environment specifications, manifests, and instructions.
- `archive/`: Documentation of superseded trials and legacy development artifacts.

---

## G. PDF Quality Status

**Status: PASS**

- **Document Class:** IEEEtran conference layout (2-column format).
- **Page Count:** Exactly 10 pages (9 pages of main text and figures + balanced references on page 10).
- **Visual Balance:** Column heights on pages 1–9 terminate at ~718.9 pt. Column heights on page 10 are exactly equalized (204.3 pt each).
- **Artifacts & Overflows:** Zero text clipping, zero blank pages, zero missing symbols.
- **Draft Markings:** Zero occurrences of `TODO`, `TBD`, `DRAFT`, `retracted`, or `-0.0371`.
- **Figures & Tables:** 6 numbered figures and 6 numbered tables, all cited in ascending numerical order.

---

## H. ZIP / Package Status

**Status: PASS**

- Package Name: `OA-ASSP_FINAL_SUBMISSION_PACKAGE.zip`
- Archive Root: Single top-level directory `OA-ASSP_FINAL/`
- Exclusions Verified: No `__pycache__`, `.pytest_cache`, `.git`, `.freebuff`, temporary editor backups, or OS metadata.
- Validation: Clean-room extraction test verified all file paths, checksums, and manuscript PDF readability.

---

## I. Known Limitations (Disclosed in Manuscript & Audit)

1. **Synthetic Undirected Graphs:** Evaluation is conducted on Erdős–Rényi, random geometric, and Barabási–Albert models; real-world transportation/transit networks are not evaluated.
2. **Graph Scale ($V \le 320$):** Headroom and winner shares are characterized for small/moderate graphs where queries take hundreds of microseconds.
3. **Candidate Portfolio:** Three textbook exact solvers (Dijkstra, Bidirectional Dijkstra, $A^*$). Preprocessing-based techniques (e.g., contraction hierarchies) are not included.
4. **Selector Objective:** The decision tree was trained under unweighted $0/1$ classification loss; cost-sensitive and runtime-regret variants remain an open research opportunity.
5. **Environment-Specific Microsecond Values:** Absolute microsecond timings reflect CPython 3.13 on Windows 11; the ratio structure ($\mathrm{RequiredCapture}$, $\mathrm{SolverOnlyCapture}$) is the invariant finding.

---

## J. Exact Final Paths

- **Release Package (ZIP):** `OA-ASSP_FINAL_SUBMISSION_PACKAGE.zip`
- **Release Directory:** `.` (Repository Root)
- **Final Manuscript PDF:** `manuscript/OA-ASSP_Final_Manuscript.pdf`
- **Final Manuscript TeX:** `manuscript/OA-ASSP_Final_Manuscript.tex`
- **Authoritative Experiment:** `results/stage20_corrected_20260923_092749/`
- **Authoritative Audit Package:** `FINAL_CORRECTED_AUDIT/`
- **Final Project Manifest:** `FINAL_PROJECT_MANIFEST.json`
- **Release Checksums:** `reproducibility/FINAL_RELEASE_SHA256SUMS.txt`
