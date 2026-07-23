# Frozen output snapshots

Reproducing a *past* verdict requires the threshold table **and** the vintage of the input data.
Sources are revised: the CFNAI is revised routinely, the NFCI is re-estimated weekly over its entire
history, and the Dallas Fed revises the Trimmed Mean PCE at quarter-ends. Re-running this code
tomorrow will not always reproduce a row computed today, even with identical thresholds — that is a
property of the data, not a defect of the method.

Each threshold version therefore ships a frozen snapshot of the full monthly history. These files
are never edited after publication; a correction produces a new version, not an in-place change.

| File | Threshold version | Rows | Coverage | Data vintage |
|---|---|---|---|---|
| `regime_history_v1.1.0.csv` | 1.1.0 | 283 | 2003-01 → 2026-07 | July 2026 |

Licence: CC-BY 4.0 (see `../LICENSE-DATA`).

---

## Reading the file

24 columns. `date` first, then the verdict (`regime_code`, `regime_name_EN`, `regime_name_FR`,
`growth_state`, `inflation_state`, `stress_overlay`, `global_sync`), then the input values that
produced it, then provenance (`thresholds_version`, `data_quality`).

All 283 rows carry `thresholds_version = 1.1.0` and `data_quality = full` — the snapshot starts at
2003-01, inside the full-resolution window, so no degraded rows appear here.

## Four things to know before you compute anything from this file

**1. Three inputs are computed but not published.** ICE BofA HY OAS, the Cboe VIX and the OECD
composite leading indicators carry restrictive licences and are excluded by design. Only the
categorical labels derived from them survive, in `global_sync` and `global_qualifiers`. You cannot
recompute `global_sync` from this file alone; fetch the OECD series from its publisher.

**2. `sos` is empty on every row.** The Richmond Fed SOS indicator is an early-warning gate on the
growth axis: within the CFNAI-MA3 neutral band, an SOS reading at or above 0.20 promotes the
candidate state to G−. The series is not retrievable programmatically in a usable historical form,
so the gate is inert throughout this snapshot and never affected a single verdict here. It is kept
in the schema and in the code because it is part of the specified method, and removing the column
would hide the gap rather than document it. Every G− in this file comes from the CFNAI-MA3
threshold or the Sahm crossing, never from the SOS.

**3. `dtwexbgs_3m_pct` is empty for the first 39 rows** (2003-01 → 2006-03). The broad dollar index
`DTWEXBGS` starts in 2006. The dollar qualifier is simply absent before then; the regime name is
unaffected, since the dollar feeds the global context layer only.

**4. The regime shares in this file are not the backtest shares.** `docs/backtest.md` reports
metrics over 1968–2026 (703 months, degraded before 2003). This snapshot covers 2003–2026 only.
Computed on this file, Transition is 52.3% of months and the regime changes 1.23 times per year;
the backtest reports 28.9% and 1.26/year over the longer window. Both are correct for their
respective windows — do not read the gap as an inconsistency.

## Known documentation gap in the v1.1.0 changelog

`config/thresholds.json > _meta.changelog` summarises one of the corrected windows as
`2009-09..2010-07 (Slowdown -> Transition)`. That shorthand is imprecise: under the v1.1.0
edge-triggered Sahm gate the window resolves as Transition from 2009-09 to 2010-04, then
Disinflationary Expansion from 2010-05 to 2010-07, as CFNAI-MA3 crosses +0.10 and is confirmed by
the two-month rule. This file is the authoritative record; the changelog sentence will be corrected
at the next version bump.
