# Non-Authoritative Historical Experiment Baseline

## Historical Experiment ID: `stage20_scaleup_48g_20260920_215427`

> [!WARNING]
> This directory and its associated result files under `results/stage20_scaleup_48g_20260920_215427/` represent an early development baseline. They are **NON-AUTHORITATIVE** and preserved solely for forensic provenance and historical comparison.

## Provenance Context

The historical baseline was collected using un-warmed, single-shot solver timing, which introduced timing noise artifacts (including a single nominal negative delta of $-0.0371\,\mathrm{ms}$ on cell `scalefree_V80_D6_s138` at $Q=500$). 

When standardized multi-repetition median timing was instituted in the authoritative experiment (`stage20_corrected_20260923_092749`), this cell measured $+36.836\,\mathrm{ms}$ (slower than SBS). The historical nominal finding was a timing artifact and was retracted.

All 52 historical baseline files have been verified to match their original cryptographic digests in `FINAL_CORRECTED_AUDIT/checksums_original_before.txt` (52/52 byte-identical).

Do NOT use the historical baseline files for primary scientific conclusions.
