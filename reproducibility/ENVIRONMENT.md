# Execution and Verification Environment

## Operating System & Hardware

- **Platform:** x86_64 / AMD64 Architecture
- **CPU:** Intel 12th-Generation Core Processor (12 execution cores)
- **Host OS:** Microsoft Windows 11 Home / Pro (64-bit)
- **High-Resolution Timer:** `time.perf_counter` (Windows `QueryPerformanceCounter` backed, ~100 ns resolution)

## Software Runtime & Toolchain

- **Python Runtime:** CPython 3.13.7 (64-bit)
- **TeX Engine:** TinyTeX / pdfTeX (TeX Live 2026, Version 3.141592653-2.6-1.40.29)
- **Shell:** Windows PowerShell 5.1 / PowerShell Core 7.x

## Core Dependencies (`requirements.txt`)

```text
numpy>=1.24.0
scipy>=1.10.0
networkx>=3.0
scikit-learn>=1.3.0
pyyaml>=6.0
pandas>=2.0.0
matplotlib>=3.7.0
pytest>=7.4.0
pymupdf>=1.24.0
```

## Determinism & Random Number Generation

- **Global Experiment Seed:** `42` (defined in `configs/experiment_corrected_48g.yaml`)
- **Per-Graph Seeds:** Deterministic derivation formula: `seed = global_seed + family_offset + cell_index * 2 + seed_idx`
- **Query Generation:** 500 deterministic $(s, t)$ pairs per graph generated via seeded pseudo-random sampler; identical queries evaluated across all algorithms.
- **Bootstrap Resampling:** $B = 1{,}000$ paired graph-level resamples using fixed random seed (`42`).
