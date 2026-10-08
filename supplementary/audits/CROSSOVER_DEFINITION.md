# P0-3 — Primary Crossover Definition (unified, noise-aware)

## Definitions

**PRIMARY CROSSOVER condition (used identically for library and compiled modes):**

```text
Adaptive(Q) < SBS(Q)            using the TASK-variant cost for BOTH modes
```

where task-variant cost = benchmark-median selected-solver cost + measured in-loop overhead
(graph features once + per-query query-features + vector assembly + selection; bookkeeping
excluded per the frozen task definition). The SBS side uses the same benchmark-median solver
costs. Per-cell quantities are in `p0_crossover_unified.csv` (library column recomputed from
raw; compiled column from the frozen `compiled_mode.csv` task field).

**Noise-aware GENUINE-crossover criterion.** A cell is a **GENUINE CROSSOVER** only if BOTH:

1. **Primary condition:** `Adaptive(Q) − SBS(Q) < 0` under the primary accounting; and
2. **Magnitude:** `|Adaptive(Q) − SBS(Q)| ≥ empirical measurement-noise floor` for the same
   aggregate, where the floor is `max(per-row benchmark-median IQR median, aggregate
   pass-to-pass dispersion)` = **16.3%** (components in `p0_noise_floor.csv`).

Any cell satisfying (1) but not (2) is a **nominal cell**, reported but not interpreted as a win.

## Primary result

```text
GENUINE CROSSOVER CELLS (PRIMARY): 0 / 40
  library: 0/40 nominal, 0/40 genuine   (smallest loss +0.378 ms)
  compiled: 3/40 nominal, 0/40 genuine  (largest nominal advantage −1.486 ms)
```

Both modes now use the **same** task-variant accounting, so the comparison is like-for-like. The
primary headline is unchanged: **0/40 genuine crossover cells**.

## Secondary sensitivity analysis (labeled, not primary)

**Secondary conservative compiled sensitivity analysis** — the previously-used compiled variant
whose overhead excludes the vector-assembly component:

```text
compiled (secondary conservative): 4/40 nominal cells, 0/40 genuine
  maximum nominal advantage: −2.419 ms  = 0.227% of the Q=500 SBS cost (1064.200 ms)
  empirical timing-noise floor for the same aggregate: 9.4% (compiled pass-to-pass dispersion)
  ratio: the largest nominal advantage is ~0.227% vs a 9.4% floor — roughly 1/41 of the floor,
  i.e. ~40× below the measurement resolution (stated as computed: 9.40/0.227 ≈ 41.4)
```

The four nominal cells (`random_V80_D12_s108` Q=500; `geometric_V160_D6_s126` Q=500;
`scalefree_V160_D12_s144` Q=50; `random_V40_D6_s102` Q=100) are **not suppressed and not
inflated**: they exist in the frozen tables, they are below the noise floor by more than an
order of magnitude, and they are therefore reported as measurement noise, not wins. No figure or
table presents them as a crossover.

## Why the primary criterion is the task variant

The task variant is the cost a deployment actually pays for the *decision* (feature extraction +
selection) and is measured identically in both inference modes; the conservative variant excludes
a real cost (vector assembly) and was previously applied only to the compiled mode, which made
the two modes' crossover numbers non-comparable. One definition, both modes, stated everywhere.

## Noise floor components (frozen data, `p0_noise_floor.csv`)

| Quantity | Value |
|---|---:|
| per-row benchmark-median relative IQR — median | 14.4% |
| per-row benchmark-median relative IQR — p90 | 57.5% |
| per-row benchmark-median relative IQR — max | 434.5% |
| library aggregate pass-to-pass dispersion (3 passes) | 16.3% |
| compiled aggregate pass-to-pass dispersion (3 passes) | 9.4% |
| **PRIMARY FLOOR applied to per-cell genuine test** | **16.3%** |

**Nominal advantage vs observed timing variability (summary; full table in
`p0_noise_floor.csv`):** every nominal cell in every variant sits far below its mode's
variability — library best loss +0.378 ms (no negative cells at all), compiled task best
−1.486 ms (0.14% of SBS vs 9.4% floor), compiled conservative best −2.419 ms (0.23% of SBS vs
9.4% floor). The historical −0.0371 ms crossover claim is ~1/2800 of the floor and remains
absent from the corrected record (that cell now measures +36.84 ms).
