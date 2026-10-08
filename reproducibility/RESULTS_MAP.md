# OA-ASSP Results Map

This document maps all experimental tables, figures, and aggregate metrics from the frozen experiment (`stage20_corrected_20260923_092749`) to their corresponding source data files and recomputation scripts.

---

## 1. Primary Aggregate Metrics ($Q = 500$, Analysis-Grade)

| Metric | Manuscript Value | Raw/Processed Evidence File | JSON Manifest Path | Verification Script |
|---|---|---|---|---|
| SBS Baseline | 1064.200 ms | `results/stage20_corrected_20260923_092749/processed/stage20_corrected_20260923_092749_aggregate.csv` | `capture_aggregate_analysis_grade.500.total_SBS` | `scratch/verify_scientific_immutability.py` |
| VBS Oracle | 941.677 ms | `results/.../processed/..._aggregate.csv` | `capture_aggregate_analysis_grade.500.total_VBS` | `scratch/verify_scientific_immutability.py` |
| Oracle Gap | 122.523 ms | `results/.../processed/..._aggregate.csv` | `capture_aggregate_analysis_grade.500.OracleGap` | `scratch/verify_scientific_immutability.py` |
| Library Adaptive | 1556.250 ms | `results/.../processed/..._aggregate.csv` | `capture_aggregate_analysis_grade.500.total_Adaptive_task` | `scratch/verify_scientific_immutability.py` |
| Library Overhead | 472.040 ms | `results/.../processed/..._aggregate.csv` | `capture_aggregate_analysis_grade.500.SelectionOverhead_task` | `scratch/verify_scientific_immutability.py` |
| Library RequiredCapture | 3.8527 | `results/.../processed/..._aggregate.csv` | `capture_aggregate_analysis_grade.500.RequiredCapture_task` | `scratch/verify_scientific_immutability.py` |
| Library CaptureRate | -4.0160 | `results/.../processed/..._aggregate.csv` | `capture_aggregate_analysis_grade.500.CaptureRate_task` | `scratch/verify_paper_numbers.py` |
| Compiled Adaptive | 1119.723 ms | `results/.../processed/..._aggregate.csv` | `capture_aggregate_compiled_analysis_grade.500.total_Adaptive_task` | `scratch/verify_scientific_immutability.py` |
| Compiled Overhead | 35.513 ms | `results/.../processed/..._aggregate.csv` | `capture_aggregate_compiled_analysis_grade.500.SelectionOverhead_task` | `scratch/verify_scientific_immutability.py` |
| Compiled RequiredCapture | 0.2898 | `results/.../processed/..._aggregate.csv` | `capture_aggregate_compiled_analysis_grade.500.RequiredCapture_task` | `scratch/verify_scientific_immutability.py` |
| Compiled CaptureRate | -0.4532 | `results/.../processed/..._aggregate.csv` | `capture_aggregate_compiled_analysis_grade.500.CaptureRate_task` | `scratch/verify_paper_numbers.py` |
| Solver-Only Capture | -0.1633 | `results/.../processed/..._aggregate.csv` | `capture_aggregate_analysis_grade.500.SolverOnlyCapture` | `scratch/verify_scientific_immutability.py` |
| Selected Solver Runtime | 1084.210 ms | `results/.../processed/..._aggregate.csv` | `capture_aggregate_analysis_grade.500.total_selected_solver` | `scratch/verify_paper_numbers.py` |
| Solver Shortfall vs SBS | 20.010 ms | `results/.../processed/..._aggregate.csv` | difference (total_selected_solver - total_SBS) | `scratch/verify_paper_numbers.py` |

---

## 2. Workload Amortization Trajectory (Table II)

- **Source Artifact:** `FINAL_CORRECTED_AUDIT/corrected_results_manifest.json` (`capture_aggregate_analysis_grade`)
- **Checkpoints:** $Q \in \{1, 10, 50, 100, 500\}$
- **Columns Verified:** SBS Cost, VBS Cost, OracleGap, Adaptive Cost, Overhead, CaptureRate, RequiredCapture, Solver-Only Capture.
- **Verification Script:** `scratch/verify_paper_numbers.py` (check: `Table II (all 5 checkpoints, 8 columns)`)

---

## 3. Overhead Breakdown & Deployment Regimes (Table III)

- **Source Artifact:** `FINAL_CORRECTED_AUDIT/p0_regime_reconciliation.csv` and `corrected_results_manifest.json`
- **Breakdown Items:**
  - One-time Graph Features: Library $8.46\,\mathrm{ms}$, Compiled $8.51\,\mathrm{ms}$
  - Query Features: Library $20.78\,\mathrm{ms}$, Compiled $14.49\,\mathrm{ms}$
  - Feature-Vector Assembly: Library $11.49\,\mathrm{ms}$, Compiled $9.12\,\mathrm{ms}$
  - Selector Inference: Library $431.30\,\mathrm{ms}$, Compiled $3.40\,\mathrm{ms}$
- **Per-Query Inference Latency:** Library $87.9\,\mu\mathrm{s}$ vs Compiled $0.8\,\mu\mathrm{s}$ ($\approx 110\times$ speedup)
- **Verification Script:** `scratch/verify_paper_numbers.py` (check: `Table III (library vs compiled at Q=500, all rows)`)

---

## 4. Crossover & Noise Qualification (Table IV)

- **Source Artifacts:**
  - `FINAL_CORRECTED_AUDIT/p0_crossover_unified.csv`
  - `FINAL_CORRECTED_AUDIT/p0_noise_floor.csv`
- **Genuine Crossovers:** $0 / 40$ cells in all modes and accountings.
- **Nominal Cells:**
  - Library: $0 / 40$ (smallest loss $+0.378\,\mathrm{ms}$)
  - Compiled (Task): $3 / 40$ (max advantage $-1.486\,\mathrm{ms}$)
  - Compiled (Conservative): $4 / 40$ (max advantage $-2.419\,\mathrm{ms}$)
- **Noise Floors:**
  - Library Pass Dispersion: $16.32\%$
  - Compiled Pass Dispersion: $9.40\%$
  - Median Solver Relative IQR: $14.39\%$
- **Verification Script:** `scratch/verify_paper_numbers.py` and `scratch/verify_scientific_immutability.py`

---

## 5. Selector Generalization & Cross-Validation (Table V)

- **Source Artifact:** `results/stage20_corrected_20260923_092749/processed/stage20_corrected_20260923_092749_generalization.csv`
- **Evaluated Protocols:**
  - Held-out test (Tier 1): $72.50\%$ vs majority $72.60\%$ ($0/1$ constant folds)
  - LOCO (Tier 0): $79.10\%$ vs majority $77.95\%$ ($15/24$ constant folds)
  - LOCO (Tier 1): $80.80\%$ vs majority $77.95\%$ ($9/24$ constant folds)
  - LOFO (Tier 0): $83.76\%$ vs majority $83.45\%$ ($1/3$ constant folds)
  - LOFO (Tier 1): $79.09\%$ vs majority $83.45\%$ ($1/3$ constant folds)
- **Median Accuracy Lift:** $+0.00$ pp across all folds (Tier 0 LOFO $+0.06$ pp)
- **Verification Script:** `scratch/verify_paper_numbers.py` (check: `Table V accuracy values`, `Table V constant folds`)

---

## 6. Cost Regime Reconciliation (Table VI)

- **Source Artifact:** `FINAL_CORRECTED_AUDIT/p0_regime_reconciliation.csv`
- **End-to-End Measured:** Total $1191.05\,\mathrm{ms}$ (Solver part: $699.87\,\mathrm{ms}$ single-shot, Decision part: $491.17\,\mathrm{ms}$)
- **Analysis-Grade:** Total $1556.25\,\mathrm{ms}$ (Solver part: $1084.21\,\mathrm{ms}$ 5-rep median, Decision part: $472.04\,\mathrm{ms}$)
- **SBS Reference:** Total $1064.20\,\mathrm{ms}$ (5-rep median)
- **Verification Script:** `scratch/verify_paper_numbers.py` (check: `regime reconciliation values`)
