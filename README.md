# Eco3min Macro Regime Classifier

Assigns a monthly **macro regime** to the US economy from public institutional indicators and a
published threshold table. Descriptive, reproducible, versioned.

The verdict takes the form: *US regime — [name], under [financial conditions qualifier]*, for
example `Slowdown, under acute financial stress`. Every term traces back to a named public series
and a numeric threshold in [`config/thresholds.json`](config/thresholds.json).

**Threshold table: v1.1.0** (calibrated and frozen July 2026)
· Methodology: [`docs/methodology.md`](docs/methodology.md)
· Backtest 1968–2026: [`docs/backtest.md`](docs/backtest.md)
· Published page: <https://eco3min.fr/en/macro-regime-classification-methodology/>

---

## What it is, and what it is not

**It is** a monthly descriptive classification: a 3×3 growth × inflation grid mapping to seven
named regimes plus a transition state, prefixed by a financial-conditions qualifier derived from
the Chicago Fed's NFCI.

**It is not** a proprietary score, a trading signal, a forecast, official cycle dating (≠ NBER), or
a portfolio timing system. See [`docs/methodology.md` §10](docs/methodology.md).

---

## Quick start

```bash
git clone https://github.com/eco3min/macro-regime-classifier.git
cd macro-regime-classifier
pip install -r requirements.txt

export FRED_API_KEY=your_key   # free: https://fred.stlouisfed.org/docs/api/api_key.html
python scripts/regime_classifier.py
```

Writes to `output/`:

| File | Contents |
|---|---|
| `regime_history.csv` | one row per month, 2003-01 → current, with input values and `thresholds_version` |
| `regime_current.json` | latest month, plus `data_freshness`, `lagged_inputs`, `computed_at` |

A run takes a few minutes — the script paces its FRED calls deliberately.

A frozen snapshot of the full monthly history is committed at
[`docs/regime_history_v1.1.0.csv`](docs/regime_history_v1.1.0.csv). Re-running the code will not
always reproduce it exactly: the sources are revised, and the NFCI in particular is re-estimated
weekly over its entire history. See [`docs/SNAPSHOT.md`](docs/SNAPSHOT.md).

---

## The three axes

| Axis | States | Primary input | Hysteresis |
|---|---|---|---|
| Growth / real activity | G+ / G= / G− | CFNAI, 3-month moving average (`CFNAI`) | 2-month confirmation |
| Inflation | I+ / I= / I− | Dallas Fed Trimmed Mean PCE, 12-month (`PCETRIM12M159SFRBDAL`) | 2-month confirmation |
| Financial conditions | accommodating / neutral / restrictive / acute stress | Chicago Fed NFCI (`NFCI`) | none — updates every month |

Growth carries one exception: an **upward crossing** of the Sahm real-time rule (`SAHMREALTIME`)
through 0.50 forces G− immediately, bypassing the confirmation delay. Persistence of that G− is
then governed by the normal state machine — the crossing is the trigger, not a latch. This is the
v1.1.0 change; under v1.1.0 it cuts false-positive G− months from 55 to 4 across 1968–2026 while
preserving 8/8 NBER capture at identical entry latencies.

The 3×3 grid:

| | I− (disinflation) | I= (stable) | I+ (acceleration) |
|---|---|---|---|
| **G+** | Disinflationary Expansion | Balanced Expansion | Overheating |
| **G=** | Transition | Transition | Inflationary Pressure |
| **G−** | Disinflationary Contraction | Slowdown | Stagflation |

---

## Thresholds

Institutional thresholds are set by the producing institutions, not by Eco3min: Sahm rule at 0.50
(Sahm, 2019), SOS at 0.20 (O'Trakoun & Scavette, *Economics Letters*, 2025), NFCI reference level
at 0, the Fed's 2% symmetric inflation target.

The remaining thresholds are calibrated: candidate values were swept on a grid over the full
1968–2026 history and scored against a **pre-registered** ground-truth matrix (NBER dates, episode
expectations, false-positive and stability metrics) before any tuning. The reported percentile of
each retained value is *descriptive* — it reports where the chosen value sits in the distribution;
it is not the selection criterion. Sweeps, competing candidates and the reason each was rejected
are in `config/thresholds.json > _meta.changelog` and [`docs/backtest.md` §4](docs/backtest.md).

Any change to a threshold requires a version bump and a changelog entry. Reproducibility of a past
verdict depends on threshold immutability for a given version.

---

## Data: what this repository does and does not contain

**No source series are redistributed here.** The code fetches everything at runtime:

| Source | Series | Access |
|---|---|---|
| FRED (St. Louis Fed) | `CFNAI`, `SAHMREALTIME`, `PCETRIM12M159SFRBDAL`, `T5YIFR`, `NFCI`, `T10Y2Y`, `FEDFUNDS`, `ICSA`, `DTWEXBGS`, `DFII10` | API key required |
| ECB Data Portal | CISS, euro area | open, no key |
| Richmond Fed | SOS recession indicator | scraped, degrades gracefully if unavailable |

Three inputs carry restrictive third-party licences — ICE BofA HY OAS (`BAMLH0A0HYM2`), Cboe VIX
(`VIXCLS`), OECD composite leading indicators (`USALOLITOAASTSAM`, `G7LOLITOAASTSAM`). They are
used as computation inputs where available but are **never written to the published CSV or JSON**
(see `core_cols` in `run_history`). Only the categorical labels derived from them survive into the
output — `global_sync`, `global_qualifiers`. If you need those series, get them from their
publishers.

Two consequences for anyone reproducing this:

1. **Brent.** Production reads the World Bank CMO monthly series. Without a local
   `data/world_bank_brent.csv`, this script falls back to FRED `MCOILBRENTEU`. Brent feeds the
   commodity qualifier and the `headline_underlying_divergence` flag — never the growth or
   inflation axis, so the regime name is unaffected.
2. **HY OAS.** Not a classification input in v1.1.0 (corroboration only) and absent from the
   published output. FRED has truncated ICE BofA series to a 3-year rolling window since April 2026;
   the code reads an optional local fixture that is not distributed here.

Neither difference can change a regime label.

---

## Known limitations

Publication lags (CFNAI ≈ 3 weeks, OECD CLI ≈ 6 weeks), revision risk (the current month's regime
can change after a source revision — the NFCI is re-estimated weekly over its *full* history, which
is enough to flip a label sitting on a boundary), degraded classification before 2003 (reduced
input set, flagged `data_quality: "degraded"`), and the design property that the Trimmed Mean PCE
excludes volatile components — so an energy shock can leave the inflation axis at I= while headline
CPI climbs. That case is surfaced by the `headline_underlying_divergence` flag rather than hidden.

Fuller treatment: [`docs/methodology.md` §8](docs/methodology.md) and
[`docs/backtest.md` §5](docs/backtest.md).

---

## Licence

- **Code** — MIT. See [`LICENSE`](LICENSE).
- **Threshold table, methodology, and derived outputs** (`regime_history.csv`, `regime_current.json`) — CC-BY 4.0. See [`LICENSE-DATA`](LICENSE-DATA).
- **Source series** — governed by their respective publishers' terms. Not redistributed here.

## Citation

> Eco3min Macro Regime Classification, based on the Chicago Fed's NFCI and CFNAI and the Dallas Fed's
> Trimmed Mean PCE. Threshold table v1.1.0.
> <https://eco3min.fr/en/macro-regime-classification-methodology/>

---

## Disclaimer

Provided for informational and educational purposes. This is a descriptive classification of
measured macro conditions — not investment advice, not a personalised recommendation, not a
solicitation to buy or sell any financial instrument, and not a forecast. eco3min.fr is not a
licensed financial institution and does not provide investment advisory services within the meaning
of applicable regulations (MiFID II; French Monetary and Financial Code, articles L.541-1 et seq.).
Past performance does not indicate future results.
