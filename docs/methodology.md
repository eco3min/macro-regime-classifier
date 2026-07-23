# Eco3min Macro Regime Classification — Methodology v1.1.0

> **Source of truth.** The classification code, the published pages and the rendered outputs all derive from this document.  
> Threshold table: `config/thresholds.json` v1.1.0 · Calibrated and frozen July 2026 · Architecture unchanged since v1.0.0 (May 2026)  
> License: methodology CC-BY 4.0 · code MIT
>
> **v1.1.0 changes** — no numeric threshold moved; two behavioural changes: the Sahm gate became
> upward-crossing (edge-triggered) instead of level-based, and the `headline_underlying_divergence`
> flag got a dedicated Brent threshold at +40% YoY (decoupled from the ±20% commodity qualifier).
> Full rationale and grid sweeps: `config/thresholds.json > _meta.changelog`.

---

## 1. Purpose and Scope

### 1.1 What this classification answers

For any given month: *"What macro regime is the US economy in, and what is the global context, based solely on public data and a verifiable rule?"*

### 1.2 What it is

- A **descriptive** classification of current macro conditions
- **Reproducible**: any third party can recalculate from FRED/ECB/OECD + the published threshold table
- **Historicized**: a dated monthly series enabling the Atlas of Regimes and Crisis Hub
- **Auto-updated**: pipeline → JSON → WordPress shortcode

### 1.3 What it is NOT (to repeat prominently on the methodology page)

- Not a proprietary score (no opaque weighting)
- Not a trading signal or investment recommendation
- Not a forecast of future conditions
- Not NBER official cycle dating
- Not a market-timing system
- Not a portfolio allocation guide

---

## 2. Architecture

### 2.1 Multi-axis design (not a flat list)

A flat list ("expansion / recession / stagflation / stress") conflates orthogonal dimensions and is not mutually exclusive. The classification uses three independent axes:

| Axis | States | Role |
|---|---|---|
| **Growth / real activity** | G+ / G= / G− | Primary axis |
| **Inflation** | I+ / I= / I− | Primary axis |
| **Financial conditions & stress** | Accommodating / Neutral / Restrictive / Acute stress | Overlay — qualifies the regime, does not add a nominal axis |

The 3×3 growth×inflation grid maps to 7 named regimes + 1 transition state (§3). The overlay prefixes the name.

### 2.2 Hierarchical world architecture (not an aggregated world score)

A single aggregated world score masks inter-zone divergence (e.g., 2022: US tightening vs China easing) — this is a misleading indicator, contrary to Eco3min's editorial DNA.

**Structure:**
- **US core**: fine-grained growth × inflation classification + stress overlay. This is the primary verdict.
- **Global context layer**: qualifies the environment around the US core, on two registers:
  - **Synchronization**: is the rest of the world *synchronized* (similar regime direction) or *divergent* with the US? Based on OECD CLI multi-zone comparison.
  - **Global transmission channels**: broad dollar (global financial conditions tightening/easing, especially EM), commodities (supply shock/relief), global stress (VIX, EM spreads).

**Final verdict format:**  
`US Regime: [name] [+ stress overlay] — Global context: [synchronized / divergent], [dollar/commodities/stress qualifier]`

### 2.3 Eurozone as future second core (v1.1)

The eurozone will become a second classified core (same architecture, inputs: CISS, HICP, Eurostat, ECB rate) in v1.1, not v1.0. In v1.0, Europe enters only via the global context layer (CISS). The pipeline must be parameterized so that adding a zone-core is a configuration parameter, not a rewrite.

---

## 3. Taxonomy of Regimes

### 3.1 The 3×3 grid

| Growth \ Inflation | I− (disinflation) | I= (stable) | I+ (acceleration) |
|---|---|---|---|
| **G+** | Disinflationary Expansion | Balanced Expansion | Overheating |
| **G=** | *(→ Transition)* | *(→ Transition)* | Inflationary Pressure |
| **G−** | Disinflationary Contraction | Slowdown | Stagflation |

G= neutral states with unresolved hysteresis → Transition / Mixed signals.

### 3.2 Named regimes

Each regime below is followed by its **verified occurrences in the published snapshot**
([`regime_history_v1.1.0.csv`](regime_history_v1.1.0.csv), 283 months, 2003-01 → 2026-07). These are
not illustrative labels: they are the months the classifier actually assigns, and every one can be
checked by filtering the file. Where a pre-2003 episode is mentioned, it is flagged as illustrative
— it falls outside the published window and can only be reproduced in degraded mode.

**Regime 1 — Disinflationary Expansion** (FR: *Désinflation expansive*) · G+ I−  
Above-trend real activity with decelerating or below-target inflation. A benign configuration, and a
rare one by construction: it requires the Trimmed Mean PCE below 1.50%, roughly the 4th percentile of
its distribution, at the same time as above-trend growth.  
*Snapshot: 3 months — 2010-05 → 2010-07.* Illustrative pre-2003: 1995–1999 (US New Economy).

**Regime 2 — Balanced Expansion** (FR: *Expansion équilibrée*) · G+ I=  
Above-trend activity with inflation near target. The textbook "Goldilocks" configuration and the
second most common state in the snapshot.  
*Snapshot: 65 months across 8 spans — longest 2003-11 → 2005-09 (23 m), then 2020-08 → 2021-10 (15 m)
and 2017-11 → 2018-10 (12 m).*

**Regime 3 — Overheating** (FR: *Surchauffe*) · G+ I+  
Above-trend activity with accelerating inflation. Typically late-cycle.  
*Snapshot: 7 months — 2021-11 → 2022-05.* Note that the post-COVID reopening surge classifies as
Balanced Expansion until November 2021: the Trimmed Mean PCE crosses 2.75% only in October–November,
so the inflation axis turns later than headline commentary did at the time.

**Regime 4 — Inflationary Pressure** (FR: *Pression inflationniste*) · G= I+  
Trend-level or stalling activity with still-rising inflation. Often the phase that follows
Overheating.  
*Snapshot: 37 months across 4 spans — longest 2022-06 → 2024-06 (25 m), then 2024-09 → 2025-02 (6 m).*

**Regime 5 — Stagflation** (FR: *Stagflation*) · G− I+  
Below-trend or contracting activity combined with accelerating inflation. The most damaging
configuration for real purchasing power.  
*Snapshot: 2 months — 2024-07 → 2024-08.* These two months are a documented residual, not a recession
call: the real-time Sahm rule genuinely printed 0.53–0.57 and the gate fired, then the state exits on
non-confirmation by activity data. Illustrative pre-2003: 1973–1975, 1979–1982 — degraded mode only.

**Regime 6 — Slowdown** (FR: *Ralentissement*) · G− I=  
Below-trend activity with inflation near or decelerating toward target. Contraction without
inflationary pressure.  
*Snapshot: 21 months across 2 spans — 2008-04 → 2009-08 (17 m, the GFC) and 2020-04 → 2020-07 (4 m,
the COVID shock).*

**Regime 7 — Disinflationary Contraction** (FR: *Contraction désinflationniste*) · G− I−  
Contracting activity with deflation risk or sharply falling inflation.  
*Snapshot: 0 months.* This is the most counter-intuitive result in the series and it is retained
rather than engineered away. The regime requires contraction and a Trimmed Mean PCE below 1.50%
**at the same time**. During the 2008–2009 recession the trimmed measure never left the 2.21–2.69%
band on the current vintage; the sustained sub-1.50% episode arrives in December 2009, after activity
had recovered. The GFC and COVID therefore classify as Slowdown, not as Disinflationary Contraction.
The cell exists in the grid and would fire on a genuinely deflationary contraction; the published
window contains none. See [`backtest.md`](backtest.md) §2, Episodes 1 and 2.

**Regime 8 — Transition / Mixed signals** (FR: *Transition / Signaux mixtes*)  
Neutral states on both axes, or an unresolved hysteresis window. Not a stable regime — it marks
ambiguity or a turning point.  
*Snapshot: 148 months, 52.3% of the window, longest span 2010-08 → 2013-10 (39 m).* A classification
that spends half its time saying "no clear regime" is doing what a threshold-based method should do
when the data is genuinely between states.

### 3.3 Stress overlay prefixes

| Overlay level | Condition | Prefix example |
|---|---|---|
| Accommodating | NFCI < −0.5, HY OAS < 300 bps | "Overheating under accommodating conditions" |
| Neutral | NFCI −0.5 to +0.5 | No prefix (default) |
| Restrictive | NFCI +0.5 to +1.5, HY OAS 500–800 bps | "Slowdown under restrictive conditions" |
| Acute stress | NFCI > +1.5 or HY OAS > 800 bps | "Disinflationary Contraction under acute financial stress" |

### 3.4 Brand kit color mapping

The brand kit v1.0 defines 6 regime color families. This taxonomy requires 8 named states. Two families are extended in brand kit v1.1:

| Regime | Brand kit family | Zone hex | Line hex | Label hex |
|---|---|---|---|---|
| Disinflationary Expansion | Désinflationniste (existing) | `#D8E2EC` | `#4A6B8A` | `#2D4256` |
| Balanced Expansion | **NEW: Neutre expansif** | `#DCE9DC` | `#5A8C5A` | `#2E542E` |
| Overheating | Inflationniste (existing) | `#F4DDD8` | `#C73E2E` | `#8B2A1F` |
| Inflationary Pressure | Inflationniste, mid-tone | `#F4DDD8` | `#C73E2E` | `#8B2A1F` |
| Stagflation | Stagflation (existing) | `#ECE2D2` | `#B8854A` | `#6E4E2B` |
| Slowdown | **NEW: Ralentissement** | `#E2E2DA` | `#7A7A6A` | `#3E3E32` |
| Disinflationary Contraction | Désinflationniste, dark | `#C8D6E4` | `#2D4A6A` | `#1A2E42` |
| Transition | Neutre (gris) | `#E8E8E8` | `#9A9A9A` | `#4A4A4A` |

Stress overlay color families: Accommodating → Liquidité abondante (existing `#DCE5D6`); Restrictive → Restriction (existing `#DDD4DD`); Acute stress → Crise systémique (existing `#D8D5D3`).

**Brand kit update required**: add "Neutre expansif" (`#5A8C5A` line family) and "Ralentissement" (`#7A7A6A` line family) to brand-kit-eco3min v1.1. Document the addition explicitly — no orphan color.

---

## 4. Inputs

### 4.1 US Core inputs

Every series the classifier actually fetches, with its effect on the verdict. Three tiers: inputs
that **determine** a regime label, inputs that are **published for context** but cannot change the
label, and inputs that are **fetched for corroboration only**.

| Input | Code | Source | Treatment | Effect on the verdict |
|---|---|---|---|---|
| Chicago Fed NAI | `CFNAI` | Chicago Fed / FRED | 3-month MA | **Determines** the growth axis |
| Sahm real-time | `SAHMREALTIME` | FRED | Level | **Determines** — upward crossing of 0.50 forces G− |
| SOS indicator | *(Richmond Fed, scraped)* | Richmond Fed | Level | **Determines** in principle — inert in practice, see below |
| Trimmed Mean PCE | `PCETRIM12M159SFRBDAL` | Dallas Fed / FRED | 12-month rate, as published | **Determines** the inflation axis |
| NFCI | `NFCI` | Chicago Fed / FRED | Monthly average of weekly values | **Determines** the financial-conditions qualifier |
| 5Y5Y forward breakeven | `T5YIFR` | FRED | Monthly | Published for context |
| Yield curve 2s10s | `T10Y2Y` | FRED | Monthly | Published for context |
| Effective fed funds | `FEDFUNDS` | FRED | Monthly | Published for context |
| Initial jobless claims | `ICSA` | FRED | 4-week MA, 52-week YoY | Corroboration flag only (`icsa_corroboration_triggered`) |
| HY OAS | `BAMLH0A0HYM2` | ICE / FRED | Monthly | Corroboration only — restricted licence, excluded from all output |

**On the SOS gate.** Within the CFNAI-MA3 neutral band, an SOS reading at or above 0.20 promotes the
candidate state to G−. The series is not reliably retrievable programmatically, and the column is
empty on all 283 rows of the published snapshot: the gate has never fired and no verdict in this
series depends on it. It is retained in the code and in the schema because it is part of the
specified method; removing it would hide the gap rather than document it.

**On HY OAS.** Since April 2026 FRED returns only a three-year rolling window for ICE BofA series.
The code reads an optional local fixture for the earlier history. HY OAS is not a classification
input in v1.1.0 and never appears in the published CSV or JSON.

### 4.2 Global context inputs

These qualify the environment around the US verdict — they populate `global_sync`,
`global_qualifiers` and the `headline_underlying_divergence` flag. **None of them can change the
regime name.**

| Input | Code | Source | Role |
|---|---|---|---|
| US CLI, amplitude adjusted | `USALOLITOAASTSAM` | OECD / FRED | Synchronization baseline |
| G7 CLI, amplitude adjusted | `G7LOLITOAASTSAM` | OECD / FRED | Synchronization — G7 against US |
| CISS, euro area | ECB `CISS.D.U2.Z0Z.4F.EC.SS_CIN.IDX`, monthly average | ECB Data Portal | European systemic stress |
| Broad dollar | `DTWEXBGS` | FRED | Global financial conditions channel |
| Brent crude | World Bank CMO, or `MCOILBRENTEU` as fallback | World Bank / FRED | Commodity channel and divergence flag |
| VIX | `VIXCLS` | Cboe / FRED | Global market stress |

**On the CISS series code.** The classifier reads `SS_CIN` — the recalibrated "new CISS". The earlier
`SS_CI` variant is frozen at May 2025. Both run on the same 0–1 scale, so the 0.30 stress threshold
carries over unchanged.

**On OECD CLI variants.** Only the `*LOLITOAASTSAM` (amplitude adjusted) series are used. The
"trend restored" variants carry a discontinuation risk and are avoided.

**Licence note.** The OECD CLIs, the Cboe VIX and the ICE BofA series are used as computation inputs
but never written to the published output. Only the categorical labels derived from them survive, in
`global_sync` and `global_qualifiers`.

### 4.3 Specified but not implemented in v1.1.0

The original design named several further inputs. None of them is fetched, computed, or used by the
code in this repository, and none appears in the published output. They are listed here so that the
gap between the design and the implementation is explicit rather than discoverable:

- **Net liquidity** (`WALCL` − `WTREGEN` − `RRPONTSYD`) — intended as a liquidity dimension of the
  stress overlay. Not implemented; the overlay rests on the NFCI alone.
- **Wu-Xia shadow rate** — Atlanta Fed updates suspended in April 2022 and will not resume until
  policy rates return to the lower bound. Restrictiveness is carried by `FEDFUNDS` and the NFCI.
- **Copper/gold ratio** — intended as a growth and risk-appetite signal in the global layer.
- **EM high-yield spreads** (`BAMLEMHBHYCRPIOAS`) — same ICE truncation problem as `BAMLH0A0HYM2`.

---

## 5. Threshold Table

### 5.1 Institutional thresholds (fixed, non-negotiable)

| Input | Threshold | Direction | Basis |
|---|---|---|---|
| Sahm real-time (`SAHMREALTIME`) | 0.50 | ≥ 0.50 → recession gate fires | Sahm (2019), institutional standard |
| SOS indicator | 0.20 | ≥ 0.20 → early recession corroboration | O'Trakoun & Scavette, Economics Letters 2025 |
| NFCI | 0.00 | > 0 → tighter than historical average | Chicago Fed definition |
| T10Y2Y | 0.00 | < 0 → inverted curve | Market convention, institutional |
| Trimmed Mean PCE | 2.00% | Fed's symmetric target | Federal Reserve official target |

### 5.2 Calibrated thresholds (v1.1.0 — calibrated and frozen, July 2026)

Values calibrated by percentile rank on the full available history and validated by grid backtest 1968–2026 (sensitivity sweeps, episode scoring against a pre-registered ground-truth matrix, calibration/validation split). Full evidence: `thresholds.json` v1.1.0 changelog and `backtest_framework.md`. Any modification = version bump + changelog entry.

#### Growth axis — CFNAI-MA3

| State | CFNAI-MA3 threshold | Basis (calibrated) |
|---|---|---|
| G+ | > +0.10 | 55th percentile of the 1967–2026 CFNAI-MA3 distribution; buffers the zero-trend boundary against noise. Grid −0.05→+0.20: no historical episode discriminates; +0.10 balances G+ share (38% of months) vs Transition share (25%) |
| G= | −0.50 to +0.10 | Transition band |
| G− | < −0.50 | 10.6th percentile. Grid −0.30→−0.80: NBER capture 8/8 at every value; −0.50 dominates on detection latency (2001: 0 vs 3 months at −0.70; 1990-91: 3 vs 4) with maximum robustness margin to the 2022/2024 non-recession minima (−0.34 / −0.31). Not a Chicago Fed guidance value — an Eco3min calibration |

*Calibration resolution (v1.1.0)*: the −0.35 hypothesis is **rejected** — it leaves a 0.01–0.04 margin to the 2022 and 2024 non-recession CFNAI-MA3 minima (−0.34 / −0.31 on the July 2026 vintage), fragile to routine data revisions, with no latency gain that the Sahm gate does not already provide. −0.50 retained.

*Secondary gates*: Sahm ≥ 0.50 is a **hard gate** — the upward crossing forces immediate G−, whatever the CFNAI-MA3 level; persistence is then governed by the normal state machine (v1.1.0 edge semantics, see §7). SOS ≥ 0.20 upgrades the candidate state to G− when CFNAI-MA3 sits inside the −0.50 to +0.10 band (live-only signal — not covered by the historical backtest, series not retrievable).

#### Inflation axis — Trimmed Mean PCE (12m)

| State | Threshold | Hypothesis basis |
|---|---|---|
| I+ | > 2.75% | Above Fed target with momentum: 75 bps buffer for sustained acceleration |
| I= | 1.50%–2.75% | Fed comfort zone ± buffer |
| I− | < 1.50% | Sustained below target; deflation risk zone |

*Axis definition*: this axis measures **persistent underlying inflation**. The Trimmed Mean PCE excludes, by construction, the most volatile price components — including energy. A transitory energy shock (a gasoline or Brent spike) can therefore leave this axis at "stable" even as *headline* inflation climbs. This is intended behaviour, not a failure: the shock then surfaces in the global context (commodity channel) and in the `headline_underlying_divergence` flag, **not** in the regime name.

*Momentum overrides*: **EXCLUDED_V1** (architecture decision — simple rule = reproducible = defensible). The 12-month rate as published is the sole primary input. Calibration evidence for the bands: I+ 2.75% (61.5th pct) — 2021 switch October–November, zero I+ months 2010–2019, 99% Grande Inflation coverage; I− 1.50% (4.1th pct) — the unique value keeping 2013-16 at 92% I= while covering the December 2009 → April 2011 deflation-risk episode 17/17 months (1.75 flips 2013-16 to 96% I−; 1.25 loses 3 episode months).

*Secondary confirmation*: T5YIFR (5Y5Y breakeven) anchors expectations:
- Elevated (> 2.50%): corroborates I+
- Anchored (2.00%–2.50%): neutral
- Disanchored low (< 1.75%): corroborates I−

#### Stress overlay — NFCI (sole primary)

| Level | NFCI | Action |
|---|---|---|
| Accommodating | < −0.50 | Prefix "under accommodating conditions" |
| Neutral | −0.50 to +0.50 | No prefix (default) |
| Restrictive | +0.50 to +1.50 | Prefix "under restrictive conditions" |
| Acute stress | > +1.50 | Prefix "under acute financial stress" |

*Rule*: NFCI is the **sole primary** input. It already incorporates a credit-spread subindex, which makes HY OAS partially redundant. No NFCI / HY OAS weighting.

*HY OAS status*: NOT a primary input in v1.0. Since April 2026, FRED truncates all ICE BofA series to a rolling 3 years — the full 1996–present history is inaccessible without a pre-April 2026 local fixture. Runtime rule: if `data/bamlh0a0hym2_history.csv` exists → log HY OAS as corroboration only; if absent → proceed with NFCI alone. **Absence does not degrade classification quality.** HY OAS percentile bands, for reference only if a fixture is later recovered: < 300 bps ≈ 25th pct of 1996–2026; 450–700 ≈ 60th–85th; > 700 ≈ 85th pct+ / GFC-type events.

#### Global context — Synchronization

| Signal | Definition | Condition |
|---|---|---|
| Synchronized | G7 CLI direction same as US CLI direction | Both rising or both falling (3m delta) |
| Divergent | G7 CLI direction opposite to US CLI | US rising / G7 falling, or vice versa |

Dollar channel: DTWEXBGS 3m change > +3% = dollar strengthening (tighter global conditions, EM stress); < −3% = dollar weakening (easing). Within ±3% = neutral.

Commodity channel: Brent YoY change > +20% = supply/demand shock; < −20% = deflation/demand destruction; otherwise neutral. The `headline_underlying_divergence` flag uses its **own** trigger: Brent YoY > **+40%** (v1.1.0 — at +20% the flag was active 26% of post-1988 months, an ordinary oil-bull-market indicator; at +40%: 17.9%, with every genuine shock episode preserved, including March–May 2026). The commodity-channel qualifier keeps the ±20% bounds.

Global stress: VIX > 25 = elevated; VIX > 35 = acute. Combine with EM spreads if available.

### 5.3 Calibration method

1. Pull full history for each input (through latest available before FRED ICE truncation for HY OAS)
2. For non-institutional thresholds: compute percentile distribution across full sample
3. Assign tercile/quartile boundaries as first-pass thresholds
4. Validate against the episode matrix in [`backtest.md`](backtest.md) §2: the 2008, 2020, 2021, 2022 and 2023–24 episodes must classify without forcing
5. If an episode misclassifies: document explicitly rather than patch threshold ad hoc
6. Lock thresholds once validated → version `thresholds.json` (semver; current: **v1.1.0**, calibrated July 2026)

**Anti-overfitting rule**: no threshold can be adjusted more than 20% from the percentile-derived value solely to match a historical episode. If an episode requires a >20% adjustment, document it as "classification ambiguity — genuine transition period" in the episode analysis.

---

## 6. Classification Logic

### 6.1 Intra-axis aggregation

**Growth axis**: primary = CFNAI-MA3. Secondary override gates: Sahm ≥ 0.50 or SOS ≥ 0.20 → G− override. ICSA 4-week MA (YoY change > +15%) → corroboration signal, not primary.

Rule: CFNAI-MA3 determines the state. Secondary gates can upgrade to G− only (they cannot upgrade to G+).

**Inflation axis**: primary = Trimmed Mean PCE (12m). Secondary modifier: 3m annualized momentum + T5YIFR direction. Momentum can upgrade I= to I+ or I−, but cannot change I+ to I−.

**Stress overlay**: NFCI only. HY OAS is fetched for corroboration but is not part of the rule and is excluded from all published output (§4.1). Levels in §5.2.

### 6.2 Cross-axis resolution → regime name

Via the 3×3 grid (§3.1). G= + I= = Transition unless one secondary input provides sufficient conviction to place in an adjacent cell — document when this override is applied.

### 6.3 Global context

1. Compute 3-month direction (delta) for `USALOLITOAASTSAM` and `G7LOLITOAASTSAM`
2. If same sign (both up or both down): Synchronized
3. If opposite sign: Divergent
4. Add dollar channel qualifier (DTWEXBGS)
5. Add commodity qualifier (Brent)
6. Add stress qualifier (VIX ± EM spreads)

### 6.4 Hysteresis — anti-flickering mechanism

A regime change is confirmed only after **2 consecutive months** with all primary axis inputs beyond the threshold, OR via a "hard gate" (Sahm ≥ 0.50 = immediate G− with no delay, given it's a confirmed recession signal). The Sahm hard gate is **edge-triggered** (v1.1.0): the upward crossing of 0.50 switches the state immediately; the *persistence* of G− is then governed by the normal 2-month state machine on CFNAI-MA3, and a fall of the Sahm value back below 0.50 re-arms the gate. Rationale: the Sahm rule detects recession *onsets* but stays elevated deep into recoveries — the v1.0.0 level rule produced post-recession tails (18 months of Stagflation in 1991-92; Slowdown until April 2021 with CFNAI-MA3 at +4.6). Confirmation length: 1 and 2 months are indistinguishable on the 1968–2026 history (the 3-month moving average already smooths the candidate); 3 months degrades (state carry-over, +9 false-positive months). 2 retained as insurance against noisier future data.

Implementation: maintain `pending_state` and `current_state`. The regime published is `current_state`. `pending_state` becomes `current_state` after 2 consecutive months confirmation. On reset (indicators move back within threshold), `pending_state` resets, `current_state` remains.

Exception: the stress overlay does NOT use hysteresis — it reflects current conditions and can move week-to-week (that's its function). The primary G/I axes use hysteresis; the overlay does not.

### 6.5 Missing data / publication lags

| Scenario | Rule |
|---|---|
| CFNAI not yet published (typical: 3-week lag) | Hold last known value. Flag `data_freshness: "lagged"` in JSON. |
| Trimmed Mean PCE lag (2–3 week lag) | Hold last known value. |
| OECD CLI lag (typically 6 weeks) | Hold last known value. Synchronization signal updates on new release only. |
| SOS missing (typically 2-week lag for insured unemployment) | Flag in JSON, do not impute. |
| Any input revision | Recompute regime for affected months. Log revision in `regime_history.csv`. |

Current regime note: "Classification based on data available as of [date]. Subject to revision when inputs are revised."

---

## 7. Backtest and Validation

The classification was backtested over 1968–2026 (703 months) against a ground-truth matrix
registered before any threshold was tuned: NBER recession dates, per-episode expectations, and
pre-declared metrics for false positives, entry latency and stability. Candidate threshold values
were swept on a grid; the retained values, the rejected alternatives and the reason for each
rejection are in `../config/thresholds.json > _meta.changelog`.

Full treatment — execution approach, vintage handling, the pre-2003 degraded extension, the
episode-by-episode matrix with actual outcomes, the scorecard, and the documented ambiguities that
were *not* patched away — is in **[`backtest.md`](backtest.md)**. That document is the authoritative
validation record; it is not duplicated here.

The published monthly output is **[`regime_history_v1.1.0.csv`](regime_history_v1.1.0.csv)**
(283 rows, 2003-01 → 2026-07). Every episode claim in this document is checkable against it —
see [`SNAPSHOT.md`](SNAPSHOT.md) for what the file does and does not contain.

**Validation rule.** When an episode does not classify as expected, the finding is documented — as
genuine ambiguity, input lag, or threshold positioning — and the threshold is left alone. An honest
"the data was ambiguous at the time" is the correct outcome, not a defect to be engineered away.

---

## 8. Limitations and Epistemic Honesty

1. **Revision risk**: the current month's regime may change after input revisions. Always timestamped.
2. **Look-ahead bias in calibration**: thresholds set before seeing post-2026 data.
3. **CFNAI revision**: backtest uses revised CFNAI where vintage unavailable — potential look-ahead bias, documented.
4. **Aggregation loss**: combining 3+ inputs into one axis state loses nuance. The raw input values are always published alongside the regime name.
5. **Historical window instability**: pre-2003 classification uses reduced inputs — labeled "degraded" throughout.
6. **OECD CLI lag**: typically 6 weeks. The synchronization signal is slower-moving than the US core.
7. **No prediction**: this is a current-state descriptor, not a leading indicator. The OECD CLI is leading within the global context layer only.
8. **Wu-Xia gap (2022–present)**: restrictiveness signal relies on FEDFUNDS + NFCI for current production; the shadow rate dimension is unavailable until ZLB returns.

---

## 9. Citation Format

FR: *« Selon la classification de régime macro d'Eco3min, fondée sur le NFCI de la Chicago Fed, l'indice CFNAI et la Trimmed Mean PCE de la Dallas Fed, l'économie américaine est en [régime] dans un contexte mondial [synchronisé/divergent]. »*

EN: *"According to Eco3min's macro regime classification, based on the Chicago Fed's NFCI, the CFNAI, and the Dallas Fed's Trimmed Mean PCE, the US economy is in [regime] within a [synchronized/divergent] global context."*

Each term verifiable: NFCI code `NFCI`, CFNAI code `CFNAI`, Trimmed Mean PCE code `PCETRIM12M159SFRBDAL`, thresholds published at [methodology URL].

---

## 10. AMF Compliance

This classification describes macro conditions. It does not:
- Assign portfolio allocations (no "40% equities in regime X")
- Issue trading signals (no "buy X when regime = Y")
- Make forward projections (the regime is a current-state description, not a forecast)
- Recommend investor types for each regime

Any regime–asset association on the site (Atlas) is presented as a **descriptive historical statistical observation** with empirical anchoring, not as prescriptive guidance. Language uses: "historically associated with," "data shows," "observed during" — never "should," "favored," "avoid."

The regime names themselves describe macro nature only: "Overheating" = growth + inflation state; "Stagflation" = growth + inflation state. Not "equity-unfavorable" or "bond-friendly."
