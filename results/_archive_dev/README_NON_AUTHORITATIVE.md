# NON-AUTHORITATIVE — ARCHIVED DEVELOPMENT ARTIFACTS

**Everything under `results/_archive_dev/` is DEVELOPMENT-ERA material from 2026-09-20 and earlier.
It is retained as historical evidence only. Nothing here may be cited, quoted, plotted, or used as
the basis for any claim.**

## What is in here

| Archived path | Era | Contents | Why it is non-authoritative |
|---|---|---|---|
| `figures/` | 2026-09-20 | 20 dev-era figures, **including `fig07_total_cost_vs_Q_crossover.png/.pdf`** | Superseded. Contains a crossover figure derived from the original run's timing protocol. |
| `tables/` | 2026-09-20 | 21 dev-era tables (`table01..table07`) | Superseded. Not the corrected record's tables. |
| `processed/` | 2026-09-20 | 35 files, including `final_q1_q10_q50_q100_q500_*` runs and `oracle_results.csv` | Superseded intermediate analyses. |
| `raw/` | 2026-09-20 | 5 files, including `smoke_benchmark_results.csv` | Superseded / smoke-test data. |
| `preflight_stage20a_*` | 2026-09-20 | 6 preflight runs | Preflight only; not the frozen benchmark. |

## The retracted crossover

The original Stage 20 record reported a marginal adaptive win:

```
graph:      scalefree_V80_D6_s138
Q:          500
delta:      -0.037 ms   (adaptive faster than SBS)
GapClosed:  +0.79%
```

**This is NOT a current result.** It is a superseded, historical measurement that the corrected
record does not reproduce: under the corrected protocol that same cell measures **+36.84 ms**
(a loss). The original protocol lacked warm-up/median timing discipline, which compressed solver
timings and made a noise-floor artifact look like a crossover. See
`FINAL_CORRECTED_AUDIT/corrected_audit_report.md` §4 and
`FINAL_CORRECTED_AUDIT/CROSSOVER_DEFINITION.md`.

## Authoritative record

Use only:

- `results/stage20_corrected_20260923_092749/` — authoritative corrected experiment
- `FINAL_CORRECTED_AUDIT/` — authoritative audit package
- `README_CORRECTED.md` — authoritative record pointer

Historical (immutable, never modified, not the current result):
`results/stage20_scaleup_48g_20260920_215427/`

Superseded intermediate corrected run:
`results/stage20_corrected_20260922_234910/` (see its `SUPERSEDED_README.txt`)
