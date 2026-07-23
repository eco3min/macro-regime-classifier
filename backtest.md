# Backtest Framework & Episode Validation

> This document specifies the backtest methodology, expected episode classifications, and the explicit treatment of the May 2026 baromètre coherence test.

---

## 1. Backtest Methodology

### 1.1 Execution approach

1. Pull all input series from FRED/ECB/OECD for the full window
2. For each month from 2003-01 to present: apply classification logic using data **available as of that month** (no look-ahead)
3. Apply hysteresis state machine — carry forward `current_state` and `pending_state`
4. Record output: regime code, regime name, growth state, inflation state, stress overlay, global context
5. Cross-reference against NBER recession dates as external validation

### 1.2 Vintage data handling

| Input | Vintage treatment |
|---|---|
| SAHMREALTIME | `SAHMREALTIME` is the real-time vintage by design. Use it. |
| CFNAI | CFNAI is revised. Use as-published in backtest context (acknowledges potential look-ahead bias). Document. |
| OECD CLI | AA variant is more stable than trend-restored; revision impact is smaller. Document revision bias. |
| Trimmed Mean PCE | Dallas Fed primarily revises small amounts at quarter-ends; limited look-ahead bias. |
| NFCI | Re-estimated weekly over its FULL history — small shifts everywhere. Observed: May 2026 monthly average −0.515 (May run) → −0.4998 (July re-estimation), flipping the overlay label at the −0.50 boundary. Boundary noise documented; not negligible at thresholds. |

### 1.3 Pre-2003 degraded extension

Available inputs: CFNAI (≥1967), Sahm (≥1960, no `SAHMREALTIME` — use `SAHMCURRENT` with bias documented), NFCI (≥1971), T10Y2Y (≥1976), Trimmed Mean PCE (≥1977), FEDFUNDS (≥1954). 

Missing: T5YIFR, SOS, and OECD CLI coverage for the global context layer (partial). Net liquidity was specified in the original design but is not implemented in v1.1.0 — see `methodology.md` §4.3.

Pre-2003 series: labeled `data_quality: "degraded"` in all outputs. The classification runs but the confidence is explicitly lower.

---

## 2. Episode Validation Matrix

### Episode 1: GFC 2008–2009 — PASS (expectation corrected v1.1.0)

**Expected (corrected v1.1.0)**: Slowdown (G− I=) under Acute stress from October 2008. The original expectation (Disinflationary Contraction G− I−) is falsified by the data: on the July 2026 vintage the Trimmed Mean PCE stays inside the I= band for the entire recession (2008 range 2.21–2.69%; the sustained I− episode arrives AFTER the recession, December 2009 → April 2011).

**Input trajectory (actual, July 2026 vintage)**:
- CFNAI-MA3: crossed −0.50 in March 2008, trough −2.69 (January 2009)
- Sahm real-time: crossed 0.50 in April 2008 (hard gate trigger) — not late 2007
- Trimmed Mean PCE: 2.21–2.69% throughout 2008 on the revised vintage — never above 2.75%, never below 1.50%. No I+ phase, no I− phase
- NFCI: monthly average peak +2.99 (November 2008). On the monthly-average convention the GFC is NOT the sample maximum — 1974 reaches +5.15. Weekly intra-month peaks are higher; the classification uses monthly averages
- HY OAS: not backtestable (pre-2023 history lost, see thresholds.json backtest_limitations)

**Classification path (actual, v1.1.0 run)**:
- G− from April 2008 (Sahm gate; latency 4 months vs NBER start — documented ambiguity, CFNAI-MA3 had crossed −0.50 in March 2008)
- I= throughout → regime = **Slowdown (G− I=)** for the full recession, 100% coverage after first trigger
- Overlay: restrictive from February 2008, **acute_stress October 2008 → April 2009**, restrictive to June 2009, as expected

**Resolution**: no Stagflation interlude occurs on the current vintage — the revised Trimmed Mean PCE never exceeds 2.75% in 2008. The anticipated "elevated inflation mid-2008" exists in headline CPI, not in the trimmed measure. Vintage caveat: this narrative may shift again with future Dallas Fed revisions; the classification rule does not.

---

### Episode 2: COVID shock March–May 2020 — PASS (expectation corrected v1.1.0)

**Expected (corrected v1.1.0)**: Slowdown (G− I=) under a NEUTRAL overlay. The original expectations of I− and Acute stress are both falsified by the data.

**Input trajectory (actual, July 2026 vintage)**:
- CFNAI-MA3: April 2020 = −7.54 (sample minimum)
- Sahm real-time: 4.00 in April 2020 (hard gate trigger)
- Trimmed Mean PCE: eased to 1.73% (April) — stays in the I= band; no I− (momentum overrides are EXCLUDED_V1)
- NFCI: monthly average peak **+0.25** (April 2020); max weekly +0.27. Never approaches the +1.50 acute bound — the Fed's March 23 interventions kept aggregate financial conditions near neutral. The "~+1.5" reference of the original draft was incorrect
- HY OAS: not backtestable (fixture boundary)

**Hysteresis note**: the Sahm hard gate fires immediately — no 2-month wait. This is correct: the COVID shock was instantaneous, not gradual.

**Classification (actual)**: G− (hard gate, April 2020) + I= + neutral overlay = **Slowdown**, as expected. The divergence flag does not fire (Brent YoY −74%: demand destruction, opposite channel).

**Duration (v1.1.0)**: G− April → July 2020, exit August 2020 via the edge-triggered gate + state machine (CFNAI-MA3 back at +4.6 by July). Under the v1.0.0 level rule, the Sahm value (still 6.4 in August 2020) held Slowdown until April 2021 — 9 months of published contraction during a record rebound. Corrected in v1.1.0.

---

### Episode 3: 2021 Reopening/Reflation — PASS (expectation corrected v1.1.0)

**Expected (corrected v1.1.0)**: Overheating (G+ I+) from late 2021 only — not across the whole year.
The original expectation placed Overheating in 2021 H2; it is falsified by the trimmed measure. The
Trimmed Mean PCE crosses 2.75% in October 2021 and is confirmed in November, so the inflation axis
turns roughly six months after headline commentary did.

**Input trajectory (actual, July 2026 vintage)**:
- CFNAI-MA3: positive throughout, range −0.10 (February) to +0.92 (May) — G+ all year
- Sahm real-time: falls below 0.50 in April 2021, well clear of the gate thereafter
- Trimmed Mean PCE: 1.74% in January, 2.52% in September, 2.81% in October, 3.36% in December — the
  I+ crossing is late, not early
- NFCI: monthly range −0.54 to −0.69, accommodating for all twelve months

**Classification path (actual, v1.1.0 run)**:
- January → October 2021: G+ I= = **Balanced Expansion** under accommodating conditions
- November 2021 → May 2022: G+ I+ = **Overheating**, accommodating through January 2022, neutral from
  February as the NFCI rises toward −0.29
- June 2022: growth falls back to G= → hand-off to Inflationary Pressure (Episode 4)

**Resolution**: the reopening surge does not register as Overheating while it is happening. The
inflation axis measures persistent underlying inflation, and in early 2021 the trimmed measure was
still below 2%. This is the same design property that governs the May 2026 energy shock (§3) — the
axis is deliberately slow, and the lag is visible rather than smoothed away.

---

### Episode 4: 2022 — Tightening, Slowdown, Disinflationary Turn

**2022 H1 Expected**: Inflationary Pressure (G= I+) or Stagflation risk

**Input trajectory H1 2022**:
- CFNAI-MA3: declining from positive to near zero by mid-2022
- Trimmed Mean PCE: peaked ~5%+
- NFCI: rising rapidly toward restrictive territory (+0.5 to +1.0)
- HY OAS: rising (400–600 bps range by H2)
- Sahm: below 0.50 throughout

**Classification path 2022**:
- 2022 Q1: G= to G+ (CFNAI still positive); I+ (PCE surging) → Inflationary Pressure or Overheating
- 2022 Q2–Q3: G= declining; I+ peak → Inflationary Pressure with Restrictive overlay
- 2022 Q4: G= to G−? CFNAI-MA3 was near −0.2 but Sahm stayed below 0.50 → this is the ambiguous zone

**Calibration resolution (v1.1.0)**: the G− threshold is calibrated at **−0.50**, not −0.35. 2022 CFNAI-MA3 range on the July 2026 vintage: +0.28 to −0.34 (minimum in December; monthly attribution moves across vintages — June 2022 reads −0.22). Never crosses −0.50 → never G−. A −0.35 threshold would leave a 0.01 margin to the 2022 minimum and 0.04 to the 2024 minimum (−0.31) — fragile to routine CFNAI revisions; rejected.

**Result (actual)**: zero Stagflation months in 2022. H1 2022 = Overheating (G+ I+), from June 2022 = **Inflationary Pressure (G= I+) under a NEUTRAL overlay** — not Restrictive: the monthly NFCI never exceeded −0.10 in 2022 despite 525 bps of hikes (excess COVID-era liquidity). The "Restrictive" expectation of the original draft is falsified by the data; the neutral reading is the empirically correct one.

---

### Episode 5: 2023–2024 Soft Landing — CORRECTED (original expectation falsified)

**Expected (corrected v1.1.0)**: Inflationary Pressure (G= I+) decelerating — NOT Disinflationary Expansion. On the current vintage the Trimmed Mean PCE stays above 2.75% until February 2025 and never approaches the 1.50% I− bound (disinflation floor ≈ 2.6%). The original G+ I− expectation described headline dynamics, not the trimmed measure.

**Input trajectory**:
- CFNAI-MA3: bounced back positive through 2023 H2
- Trimmed Mean PCE: declined from ~5% to ~2.5–3.0% through 2023
- Sahm: remained below 0.50
- NFCI: eased from restrictive back toward neutral by 2023 H2
- HY OAS: compressed as credit conditions improved

**Classification path (actual, v1.1.0 run)**:
- 2023–2024: Inflationary Pressure (G= I+), PCE 12m decelerating from ~4.9% to ~2.9%
- July–August 2024: 2-month Stagflation episode (real-time Sahm 0.53–0.57 fired the gate; exits on non-confirmation by CFNAI-MA3) — documented residual, see §5
- March 2025 → present: **Transition (G= I=)** once PCE holds below 2.75% (February 2025 = 2.73%, confirmed)

---

## 3. May 2026 Baromètre Coherence Test — Full Treatment

### 3.1 Known input values (from baromètre)

| Input | Value | Source |
|---|---|---|
| Sahm real-time | 0.20 | Baromètre |
| NFCI | −0.52 | Baromètre |
| HY OAS | 2.83% (283 bps) | Baromètre |
| VIX | ~17 | Baromètre |
| US growth (annualized) | +2.0% | Baromètre note (partial post-shutdown artefact) |
| SOS indicator | 0.000 (week ending May 9) | Richmond Fed direct |
| Brent crude | ~$108 | Baromètre (Iran/Hormuz geopolitical shock) |
| Gasoline YoY | +21.2% | Baromètre |

Missing from available data: CFNAI-MA3 for April 2026 (typically 3-week lag), Trimmed Mean PCE for March/April 2026.

**Inflation driver per the baromètre**: an energy/geopolitical supply shock — Brent at ~$108, gasoline up 21.2% YoY, attributed to Iran/Strait of Hormuz tensions. No tariff narrative in the baromètre source. Any reference to tariffs in earlier drafts of this document was an error.

### 3.2 Classification inference

**Growth axis:**
- Sahm = 0.20 → below 0.50 (no recession gate); SOS 0.000 → no early warning signal
- CFNAI-MA3: unknown for April, but US growth at +2.0% annualized suggests likely positive or slightly positive
- **Inference: G= to G+, NOT G−**

**Inflation axis:**
- Trimmed Mean PCE for April 2026: unknown, but an energy shock of this magnitude (+21.2% gasoline YoY) would push Trimmed Mean PCE above 2.75% if sustained
- T5YIFR (5Y5Y breakeven): if elevated expectations confirm, supports I+
- **Inference: I+ likely given energy shock scale**

**Stress overlay:**
- NFCI = −0.52 → **Accommodating** (< −0.50 threshold)
- VIX = 17 → Normal (< 20)
- **Overlay: Accommodating** despite energy shock — financial conditions are loose even as commodity prices surge

### 3.3 Rigorous classification verdict

**This depends entirely on the Trimmed Mean PCE value for April 2026 — which is not in the baromètre and was not yet published at the time of this spec.**

Two scenarios:

**Scenario A — Trimmed Mean PCE > 2.75%**: the energy shock has bled into core inflation measures. Classification → **Inflationary Pressure (G= I+)** or **Overheating (G+ I+)** under accommodating financial conditions.

**Scenario B — Trimmed Mean PCE ≤ 2.75%**: the energy shock is isolated in headline/energy components and has not transferred into underlying inflation. Classification → **Balanced Expansion (G+ I=)** under accommodating financial conditions, with global qualifier "commodity supply shock."

Scenario B is plausible. The Trimmed Mean PCE is designed by construction to exclude volatile components, including energy. A sharp spike in gasoline (+21.2% YoY) driven by a geopolitical event (Hormuz) is exactly the type of transitory supply shock that this indicator filters out. If Scenario B materializes, the classification is correct — it is the indicator doing its job, not a calibration failure.

**In Scenario B, the editorial prose must supply what the regime name does not:** "Balanced Expansion, but headline inflation is 3.3% driven by a geopolitical energy shock — underlying inflation remains contained." The classification names the measured persistent state; commentary explains the mechanism. Do not override the classification toward I+ to match the headline number — that would recreate the editorial contamination the design explicitly prevents (the anti-overfitting rule in `methodology.md` §5.3).

**Whichever scenario materializes at the data run, document it as-is. The test of coherence passes either way** — it passes as a confirmation of the design logic, not necessarily as confirmation of the baromètre label.

### 3.4 Why the baromètre used "stagflation atténuée"

The editorial baromètre was likely applying a loose colloquial usage of "stagflation" to describe a geopolitical energy supply shock (Brent $108, Hormuz) concurrent with slowing growth momentum — a valid qualitative description of the mechanism, but not a regime verdict by this classification's definition.

The classification disagrees with the label but does not disagree with the underlying data description. Stagflation as a named regime requires measured G−. Here, growth is positive, financial conditions are accommodating, and no recession signal is firing. The inflation is supply-shock-driven, not demand-driven — a valid editorial nuance that the classification does not capture in its named regime, and that commentary should supply.

### 3.5 Outcome: the editorial prose was revised, the thresholds were not

The classification took precedence and the wording was corrected in the following month's edition:

> *Superseded:* "l'économie américaine entre dans une phase de stagflation atténuée"
> *Published:* "l'économie américaine est en régime de pression inflationniste dans des conditions financières accommodantes — le choc énergétique géopolitique (Brent ~108 $, Hormuz) maintient l'inflation au-dessus de la cible sans déclencher de contraction mesurable des conditions de crédit"

The second formulation is the citable one. A reader cannot verify "stagflation atténuée" against
inputs showing G+ and an NFCI at −0.52. They can verify "pression inflationniste sous choc d'offre
énergétique" against CFNAI-MA3, a Sahm reading of 0.20, and the Brent and gasoline series.

On the driver itself: the May 2026 inflation impulse is energy and geopolitical in origin. Earlier
drafts of this document carried a tariff narrative; it is not supported by the underlying data and
has been removed.

### 3.6 Resolution (July 2026 data run, v1.1.0)

The scenario is resolved: Trimmed Mean PCE April/May 2026 = 2.34–2.41% → **I=** (Scenario B family), but CFNAI-MA3 ≈ −0.03 → **G=**, not the G+ that Scenario B anticipated. Verdict: **Transition / Mixed signals (G= I=)**, `headline_underlying_divergence = true` from March to May 2026 (Brent YoY +41.8 / +72.2 / +66.2%), off from June (+19.5%). Overlay note: the May 2026 monthly NFCI sits exactly on the −0.50 accommodating boundary (−0.515 at the May production run, −0.4998 after the July weekly re-estimation) — the label is boundary-unstable that month by construction (no-hysteresis overlay); documented, not patched.

---

## 4. Backtest Results — v1.1.0 calibrated run (July 2026, 1968–2026, 703 months)

Key-episode rows (extended pre-2003, `data_quality = degraded` before 2003-01):

| Date | Regime (EN) | Growth | Inflation | Stress | CFNAI-MA3 | Sahm | PCE 12m | NFCI | Quality |
|---|---|---|---|---|---|---|---|---|---|
| 1970-06 | Slowdown | G− | I= | neutral | −0.43 | 1.37 | — | — | degraded |
| 1974-09 | Slowdown | G− | I= | acute_stress | −0.62 | 0.83 | — | +4.25 | degraded |
| 1980-04 | Stagflation | G− | I+ | acute_stress | −1.32 | 0.67 | 8.55 | +3.96 | degraded |
| 1982-03 | Stagflation | G− | I+ | acute_stress | −0.63 | 1.47 | 6.20 | +2.08 | degraded |
| 1990-12 | Stagflation | G− | I+ | restrictive | −1.09 | 0.60 | 3.84 | +0.50 | degraded |
| 2001-06 | Slowdown | G− | I= | neutral | −0.75 | 0.53 | 2.67 | −0.45 | degraded |
| 2008-12 | Slowdown | G− | I= | acute_stress | −2.05 | 2.07 | 2.21 | +2.91 | full |
| 2020-04 | Slowdown | G− | I= | neutral | −7.54 | 4.00 | 1.73 | +0.25 | full |
| 2021-12 | Overheating | G+ | I+ | accommodating | +0.58 | −0.27 | 3.36 | −0.54 | full |
| 2022-06 | Inflationary Pressure | G= | I+ | neutral | −0.22 | 0.00 | 4.66 | −0.20 | full |
| 2024-08 | Stagflation (residual, 2 m) | G− | I+ | neutral | −0.23 | 0.57 | 2.81 | −0.37 | full |
| 2026-05 | Transition / Mixed signals | G= | I= | boundary* | −0.03 | 0.10 | 2.41 | −0.4998 | full |

\* May 2026 overlay sits exactly on the −0.50 accommodating boundary (−0.515 at the May production run before the NFCI weekly re-estimation) — see §3.6.

**Scorecard (pre-registered metrics, v1.1.0 configuration)**
- NBER capture: **8/8** recessions (calibration set 5/5, validation set 3/3), latency avg 2.8 months, max 4
- False-positive G− outside [NBER start −3 m, end +6 m]: **4 months** in 2 episodes (1976-11/12; 2024-07/08) — was 55 months / 10 episodes under the v1.0.0 level gate
- Out-of-recession Stagflation: **2 months** (2024-07/08) — was 19
- Post-recession G− tails beyond NBER end: max **+3 months** (COVID) — was up to +21 (1990-91)
- Stability: 1.26 regime changes/year (layer 1); Transition share 28.9%
- Inflation axis: Grande Inflation 1978-83 = 71/72 months I+; 2010–2019 = 0 I+ months; 2013-16 = 92% I=; deflation-risk I− episode Dec 2009 → Apr 2011 = 17/17 months
- Overlay: acute = GFC Oct 2008 → Apr 2009 (7/7) + 1973-75 + 1980-82; zero acute post-1990 outside the GFC; 2022 never restrictive; COVID neutral (data-forced)
- Divergence flag (+40%): 17.9% of post-1988 months (was 26.0% at +20)

Vintage caveat: all values on the July 2026 revised vintage — see `thresholds.json > backtest_limitations`. Full monthly table: `regime_history.csv` (regenerated by the pipeline under `thresholds_version = 1.1.0`).

---

## 5. Honest Assessment of Likely Misclassifications

### 5.1 Pre-registered concerns (written *before* the v1.1.0 run — retained for transparency)

These three were the failure modes anticipated at design time. They are kept here unedited in
substance so the pre-registration is auditable; the actual outcomes are in §5.2 and in §4. Where
the run contradicts the expectation, the run wins.

**Potential miss 1: 1979–1982 Volcker period**  
The NFCI wasn't as constructed then. The period before Volcker disinflation may be ambiguously classified if Trimmed Mean PCE thresholds don't capture the 10%+ inflation of 1979–1980. The extended retroactive classification (degraded mode) will need to handle this.
→ *Outcome*: Grande Inflation 1978–83 classified 71/72 months I+; acute overlay fires in 1980–82. Concern not realised.

**Potential miss 2: 2001 recession**  
The 2001 NBER recession was shallow and brief. CFNAI-MA3 may have crossed the G− bound only briefly, and Sahm stayed below 0.50 for most of it. The classification may produce Slowdown (G− I=) rather than Disinflationary Contraction (G− I−) — which is arguably more accurate for 2001.
→ *Outcome*: 2001 is captured with 0 months of entry latency at the −0.50 bound (3 months at −0.70). The Slowdown-rather-than-Contraction reading did materialise and is retained as the defensible one.

**Potential miss 3: 2015–2016 manufacturing recession**  
The US entered a manufacturing recession without an NBER recession. The classification may produce Slowdown or Transition rather than a full contraction regime. This is epistemically honest — it WAS a partial contraction.
→ *Outcome*: 23/24 months G=, no contraction regime. Excluded from scoring as genuinely ambiguous (§5.2, item 4).

**Rule**: document these explicitly rather than patching thresholds to "fix" them.

### 5.2 Documented ambiguities after the v1.1.0 run

All retained, none patched.
1. **1970 recession mid-dip**: under the edge gate, G− runs Feb–Jun 1970, dips to Transition Jul–Oct (CFNAI-MA3 hovering at −0.20/−0.47, above the −0.50 bound), re-enters G− Nov 1970. Degraded-mode ambiguity (no NFCI, no PCE). An equivalent mid-recession dip already existed in 1973-75 under the v1.0.0 level rule (first G− run ends April 1974, re-entry September 1974) — the phenomenon is a property of a mild first recession phase, not of the gate change.
2. **1976-11/12**: real-time Sahm touched exactly 0.50 in November 1976 → 2-month Slowdown blip (CFNAI-MA3 +0.34). The ≥ rule working as specified on a documented near-signal.
3. **2024-07/08**: 2-month Stagflation — the real-time Sahm signal genuinely fired (0.53–0.57); the classifier shows it and exits on non-confirmation by activity data. Under v1.0.0 this episode lasted 4 months; a system honoring the real-time Sahm rule cannot show zero here without an ad-hoc patch.
4. **2015-16 manufacturing recession**: 23/24 months G=, no contraction regime — excluded from scoring as genuinely ambiguous; the neutral reading is defensible.
5. **GFC entry latency**: 4 months (April 2008 vs NBER December 2007) — the Sahm gate handles fast shocks (COVID: 2 months); slow-onset recessions carry a structural lag. Documented since v1.0.0.
