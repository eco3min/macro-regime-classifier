#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
regime_classifier.py — Eco3min Macro Regime Classifier v1.1.0

Assigns a monthly macro regime to the US economy from public institutional
indicators and a published threshold table (config/thresholds.json).

Outputs (output/):
  regime_history.csv   — one row per month from 2003-01 to the current month
  regime_current.json  — latest month, with input values and provenance fields

Usage:
  export FRED_API_KEY=your_key          # https://fred.stlouisfed.org/docs/api/api_key.html
  pip install -r requirements.txt
  python scripts/regime_classifier.py

Licence: MIT (code) · CC-BY 4.0 (derived data). See LICENSE and LICENSE-DATA.
Methodology: https://eco3min.fr/en/macro-regime-classification-methodology/

Note on third-party data
------------------------
This repository redistributes NO third-party source series. The code fetches
them at runtime from FRED, the ECB and the Richmond Fed. Series under a
restrictive licence (ICE BofA HY OAS, Cboe VIX, OECD CLIs) are used as
computation inputs where available but are never written to the published CSV
(see `core_cols` in run_history). ICE BofA history is read from an optional
local fixture that is not distributed here.

Reproducibility scope
---------------------
The classification logic in this file is identical to the one Eco3min runs in
production. Two documented differences in *inputs*, neither of which changes a
regime label:
  1. Brent — production reads the World Bank CMO monthly series; without a
     local data/world_bank_brent.csv this script falls back to FRED
     MCOILBRENTEU. Brent feeds the commodity qualifier and the
     headline/underlying divergence flag, not the growth or inflation axis.
  2. HY OAS — not a classification input in v1.1.0 (corroboration only), and
     absent from the published CSV. FRED truncates the ICE BofA series to a
     3-year rolling window since April 2026.
  3. DFII10 — production also fetches the 10-year real rate for a display panel
     on the site. That panel is not part of this repository, so the fetch is
     removed here. It never entered the classification.
"""

import json
import math
import os
import sys
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict

import pandas as pd
import requests
from fredapi import Fred

# ---------------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("eco3min.regime")


# ---------------------------------------------------------------------------
# FRED CLIENT
# ---------------------------------------------------------------------------
class FredFetcher:
    """
    FRED API wrapper with an in-process cache.
    One instance per run — the cache persists across series fetches.
    """

    def __init__(self, api_key: str):
        self.fred = Fred(api_key=api_key)
        self._cache: Dict[str, pd.Series] = {}

    def get_series(self, series_id: str, start: str = "1900-01-01") -> pd.Series:
        """Fetch a FRED series as a float pd.Series with a datetime index."""
        if series_id in self._cache:
            return self._cache[series_id].copy()
        log.info(f"  Fetching FRED series: {series_id}")
        try:
            s = self.fred.get_series(series_id, observation_start=start)
            s = s.dropna()
            s.index = pd.to_datetime(s.index)
            s.name = series_id
            self._cache[series_id] = s
            return s.copy()
        except Exception as e:
            log.error(f"  FRED error for {series_id}: {e}")
            raise

    def get_resampled(self, series_id: str, freq: str) -> pd.Series:
        """freq: 'daily' | 'weekly' (W-FRI) | 'quarterly' (QS) | 'monthly' (MS)."""
        s = self.get_series(series_id)
        if freq == "daily":
            return s.sort_index()
        elif freq == "weekly":
            return s.resample("W-FRI").last().dropna()
        elif freq == "quarterly":
            return s.resample("QS").last().dropna()
        else:
            return s.resample("MS").last().dropna()


# ---------------------------------------------------------------------------
# CONFIGURATION
#   scripts/regime_classifier.py   (this file)
#   config/thresholds.json         (published threshold table, semver)
#   output/                        (generated — gitignored)
#   data/                          (optional local inputs, e.g. World Bank Brent)
#   fixtures/                      (optional licensed inputs, not distributed)
# ---------------------------------------------------------------------------
THRESHOLDS_VERSION = "1.1.0"

SCRIPT_DIR = Path(__file__).resolve().parent   # repo/scripts/
REPO_ROOT  = SCRIPT_DIR.parent                 # repo/

OUTPUT_DIR = REPO_ROOT / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HISTORY_START = "2003-01-01"

# ECB Data Portal (SDMX)
ECB_API_BASE = "https://data-api.ecb.europa.eu/service/data"

# Richmond Fed SOS
RICHMOND_FED_SOS_URL = (
    "https://www.richmondfed.org/research/national_economy/sos_recession_indicator"
)

# Optional local Brent file (World Bank CMO). Absent here → FRED fallback.
WORLD_BANK_BRENT_CSV = REPO_ROOT / "data" / "world_bank_brent.csv"

# Optional local fixtures — third-party licensed series, NOT redistributed.
# Absent here by design; the classification does not depend on them.
FIXTURES_DIR = REPO_ROOT / "fixtures"
BAMLH0A0HYM2_FIXTURE = FIXTURES_DIR / "bamlh0a0hym2_history.csv"

# ---------------------------------------------------------------------------
# REGIME GRID & COLORS
# ---------------------------------------------------------------------------
REGIME_GRID = {
    ("G_plus",    "I_minus"):   (1, "Disinflationary Expansion",   "Désinflation expansive"),
    ("G_plus",    "I_neutral"): (2, "Balanced Expansion",          "Expansion équilibrée"),
    ("G_plus",    "I_plus"):    (3, "Overheating",                 "Surchauffe"),
    ("G_neutral", "I_plus"):    (4, "Inflationary Pressure",       "Pression inflationniste"),
    ("G_minus",   "I_plus"):    (5, "Stagflation",                 "Stagflation"),
    ("G_minus",   "I_neutral"): (6, "Slowdown",                    "Ralentissement"),
    ("G_minus",   "I_minus"):   (7, "Disinflationary Contraction", "Contraction désinflationniste"),
    ("G_neutral", "I_neutral"): (8, "Transition / Mixed signals",  "Transition / Signaux mixtes"),
    ("G_neutral", "I_minus"):   (8, "Transition / Mixed signals",  "Transition / Signaux mixtes"),
}

COLOR_MAP = {
    1: {"zone": "#D8E2EC", "line": "#4A6B8A", "label": "#2D4256"},
    2: {"zone": "#DCE9DC", "line": "#5A8C5A", "label": "#2E542E"},
    3: {"zone": "#F4DDD8", "line": "#C73E2E", "label": "#8B2A1F"},
    4: {"zone": "#F4DDD8", "line": "#C73E2E", "label": "#8B2A1F"},
    5: {"zone": "#ECE2D2", "line": "#B8854A", "label": "#6E4E2B"},
    6: {"zone": "#E2E2DA", "line": "#7A7A6A", "label": "#3E3E32"},
    7: {"zone": "#C8D6E4", "line": "#2D4A6A", "label": "#1A2E42"},
    8: {"zone": "#E8E8E8", "line": "#9A9A9A", "label": "#4A4A4A"},
}

# ---------------------------------------------------------------------------
# THRESHOLDS — mirror of config/thresholds.json v1.1.0
# Calibration rationale and episode validation: docs/calibration-note-v1.1.0.md
# ---------------------------------------------------------------------------
G_PLUS_THRESHOLD   =  0.10
G_MINUS_THRESHOLD  = -0.50
I_PLUS_THRESHOLD   =  2.75   # percent
I_MINUS_THRESHOLD  =  1.50   # percent
NFCI_ACCOMMODATING = -0.50
NFCI_RESTRICTIVE   =  0.50
NFCI_ACUTE         =  1.50
SAHM_THRESHOLD     =  0.50
SOS_THRESHOLD      =  0.20
ICSA_CORR_THRESH   = 15.0    # percent YoY
CISS_STRESS        =  0.30
VIX_ELEVATED       = 20.0
VIX_ACUTE          = 30.0
DOLLAR_STRONG      =  3.0    # 3m pct
DOLLAR_WEAK        = -3.0
BRENT_SHOCK        = 20.0    # YoY pct — commodity_channel qualifier (unchanged in v1.1.0)
BRENT_DEMAND_DESTR = -20.0
# v1.1.0 — threshold DEDICATED to the headline_underlying_divergence flag,
# decoupled from BRENT_SHOCK. Backtest 1968-2026: at +20% the flag was active
# 26.0% of post-1988 months (not a signal); at +40%, 17.9%, retaining every
# genuine shock episode. The commodity_channel qualifier stays at ±20.
HUD_BRENT_SHOCK    = 40.0    # YoY pct

# ---------------------------------------------------------------------------
# FETCHERS
# ---------------------------------------------------------------------------

def fetch_richmond_sos() -> pd.Series:
    """
    Fetch SOS recession indicator from Richmond Fed.
    Tries CSV download first, falls back to HTML parse.
    Returns pd.Series indexed by week-end date. Empty Series if unavailable.
    """
    csv_candidates = [
        "https://www.richmondfed.org/-/media/richmondfedorg/research/national_economy/sos/sos_data.csv",
        "https://www.richmondfed.org/-/media/richmondfedorg/research/national_economy/sos/sos.csv",
    ]
    for url in csv_candidates:
        try:
            df = pd.read_csv(url, parse_dates=[0])
            df.columns = ["date", "sos"]
            df.index = pd.to_datetime(df["date"])
            s = df["sos"].dropna()
            log.info(f"SOS fetched from CSV: {len(s)} obs, latest={s.iloc[-1]:.3f}")
            return s
        except Exception:
            pass

    try:
        from bs4 import BeautifulSoup
        import re
        resp = requests.get(
            RICHMOND_FED_SOS_URL, timeout=30,
            headers={"User-Agent": "eco3min-data-pipeline/1.0"}
        )
        resp.raise_for_status()
        text = BeautifulSoup(resp.text, "html.parser").get_text(separator=" ")
        matches = re.findall(r"(?:current\s+reading|sos)[:\s]+([0-9]\.[0-9]+)", text, re.I)
        if matches:
            val = float(matches[0])
            s = pd.Series({pd.Timestamp.now().normalize(): val}, name="SOS")
            log.info(f"SOS from HTML: {val:.3f}")
            return s
    except Exception as e:
        log.warning(f"SOS HTML parse failed: {e}")

    log.warning("SOS unavailable — proceeding without SOS signal")
    return pd.Series(dtype=float, name="SOS")


def fetch_ecb_ciss() -> pd.Series:
    """
    Fetch CISS for Euro Area from ECB SDW.
    Series: CISS.D.U2.Z0Z.4F.EC.SS_CI.IDX (daily).
    Returns pd.Series daily. Caller aggregates to monthly.
    """
    # SS_CIN = "New CISS" (methodo recalibree) — courant. L'ancienne SS_CI est
    # gelee a 2025-05. Meme echelle 0-1 (pics : 0.94 GFC, 0.74 2022, 0.37 SVB),
    # donc le seuil CISS_STRESS=0.30 reste valide. Historique SS_CIN depuis 2007.
    url = f"{ECB_API_BASE}/CISS/D.U2.Z0Z.4F.EC.SS_CIN.IDX"
    try:
        resp = requests.get(
            url,
            params={"format": "csvdata", "startPeriod": "2002-01-01"},
            headers={"Accept": "text/csv"},
            timeout=30,
        )
        resp.raise_for_status()
        from io import StringIO
        df = pd.read_csv(StringIO(resp.text))
        if "TIME_PERIOD" in df.columns and "OBS_VALUE" in df.columns:
            df.index = pd.to_datetime(df["TIME_PERIOD"])
            s = pd.to_numeric(df["OBS_VALUE"], errors="coerce").dropna()
            log.info(f"CISS fetched: {len(s)} obs, latest={s.iloc[-1]:.4f}")
            return s
    except Exception as e:
        log.warning(f"CISS fetch failed: {e}")
    return pd.Series(dtype=float, name="CISS")


def load_world_bank_brent(fetcher: FredFetcher) -> pd.Series:
    """
    Load Brent monthly prices. Uses World Bank CMO pipeline output if present;
    falls back to FRED MCOILBRENTEU.
    """
    if WORLD_BANK_BRENT_CSV.exists():
        try:
            df = pd.read_csv(WORLD_BANK_BRENT_CSV, parse_dates=[0], index_col=0)
            col = next(
                (c for c in df.columns if "brent" in c.lower() or "oil" in c.lower()), None
            )
            if col:
                s = df[col].dropna()
                s.index = pd.to_datetime(s.index)
                s = s.resample("MS").last()
                log.info(f"Brent from World Bank CMO: {len(s)} obs")
                return s
        except Exception as e:
            log.warning(f"World Bank Brent local file failed: {e}")
    log.info("Brent: falling back to FRED MCOILBRENTEU")
    return fetcher.get_resampled("MCOILBRENTEU", "monthly")


def load_local_fixture(path: Path) -> pd.Series:
    """Load a CSV fixture. Returns empty Series if absent."""
    if not path.exists():
        log.info(f"Fixture not found: {path}")
        return pd.Series(dtype=float, name=str(path))
    try:
        df = pd.read_csv(path, parse_dates=[0], index_col=0)
        s = df.iloc[:, 0].dropna()
        s.index = pd.to_datetime(s.index)
        log.info(f"Fixture loaded: {path} ({len(s)} obs)")
        return s
    except Exception as e:
        log.warning(f"Fixture load failed {path}: {e}")
        return pd.Series(dtype=float, name=str(path))

# ---------------------------------------------------------------------------
# PREPROCESSORS
# ---------------------------------------------------------------------------

def compute_cfnai_ma3(cfnai: pd.Series) -> pd.Series:
    return cfnai.rolling(window=3, min_periods=3).mean().rename("CFNAI_MA3")


def compute_nfci_monthly(nfci_weekly: pd.Series) -> pd.Series:
    """Monthly average of weekly NFCI values (W-FRI index → MS)."""
    return nfci_weekly.resample("MS").mean().rename("NFCI_monthly")


def compute_cli_delta_3m(cli: pd.Series) -> pd.Series:
    return (cli - cli.shift(3)).rename(cli.name + "_3m_delta")


def compute_brent_yoy(brent: pd.Series) -> pd.Series:
    return brent.pct_change(periods=12).mul(100).rename("brent_yoy_pct")


def compute_dtwexbgs_3m_pct(s: pd.Series) -> pd.Series:
    return s.pct_change(periods=3).mul(100).rename("dtwexbgs_3m_pct")


def compute_icsa_4w_ma_yoy(icsa_weekly: pd.Series) -> pd.Series:
    """4-week MA of weekly initial claims, then 52-week YoY change, resampled monthly."""
    ma4 = icsa_weekly.rolling(4).mean()
    yoy = ma4.pct_change(periods=52).mul(100)
    return yoy.resample("MS").last().rename("icsa_4w_ma_yoy_pct")

# ---------------------------------------------------------------------------
# LATEST AVAILABLE (handles publication lags)
# ---------------------------------------------------------------------------

def get_latest_available(
    series: pd.Series, as_of: pd.Timestamp, max_lag: int = 3
) -> tuple[float, bool]:
    """Return (value, is_lagged). Searches back up to max_lag months."""
    if series is None or series.empty:
        return float("nan"), True
    for lag in range(max_lag + 1):
        target = (as_of - pd.DateOffset(months=lag)).replace(day=1)
        if target in series.index and not pd.isna(series[target]):
            return float(series[target]), lag > 0
    return float("nan"), True

# ---------------------------------------------------------------------------
# CLASSIFIERS (stateless — hysteresis managed by RegimeStateMachine)
# ---------------------------------------------------------------------------

def classify_stress(nfci: float) -> str:
    """Stress overlay — NO hysteresis, immediate update."""
    if math.isnan(nfci):
        return "neutral"
    if nfci < NFCI_ACCOMMODATING:
        return "accommodating"
    if nfci < NFCI_RESTRICTIVE:
        return "neutral"
    if nfci < NFCI_ACUTE:
        return "restrictive"
    return "acute_stress"


def raw_classify_growth(cfnai_ma3: float, sahm: float, sos: float) -> str:
    """Candidate growth state (pre-hysteresis). Sahm gate handled in state machine."""
    if math.isnan(cfnai_ma3):
        return "G_neutral"
    if cfnai_ma3 > G_PLUS_THRESHOLD:
        return "G_plus"
    if cfnai_ma3 < G_MINUS_THRESHOLD:
        return "G_minus"
    # G_neutral band: SOS early warning upgrade
    if not math.isnan(sos) and sos >= SOS_THRESHOLD:
        return "G_minus"
    return "G_neutral"


def raw_classify_inflation(pce_12m: float) -> str:
    """Candidate inflation state (pre-hysteresis)."""
    if math.isnan(pce_12m):
        return "I_neutral"
    if pce_12m > I_PLUS_THRESHOLD:
        return "I_plus"
    if pce_12m < I_MINUS_THRESHOLD:
        return "I_minus"
    return "I_neutral"


def classify_global_context(
    us_cli_delta: float,
    g7_cli_delta: float,
    dtwexbgs_3m: float,
    brent_yoy: float,
    vix: float,
    ciss: float,
) -> dict:
    def sign(x):
        return 1 if x > 0 else (-1 if x < 0 else 0)

    if (
        not math.isnan(us_cli_delta) and not math.isnan(g7_cli_delta)
        and sign(us_cli_delta) == sign(g7_cli_delta)
        and sign(us_cli_delta) != 0
    ):
        global_sync = "synchronized"
    else:
        global_sync = "divergent"

    qualifiers = []
    commodity_channel = "neutral"

    if not math.isnan(dtwexbgs_3m):
        if dtwexbgs_3m > DOLLAR_STRONG:
            qualifiers.append("dollar strengthening (tighter global financial conditions)")
        elif dtwexbgs_3m < DOLLAR_WEAK:
            qualifiers.append("dollar weakening (easing global financial conditions)")

    if not math.isnan(brent_yoy):
        if brent_yoy > BRENT_SHOCK:
            commodity_channel = "shock"
            qualifiers.append("commodity supply/demand shock")
        elif brent_yoy < BRENT_DEMAND_DESTR:
            commodity_channel = "demand_destruction"
            qualifiers.append("commodity demand destruction")

    if not math.isnan(vix):
        if vix > VIX_ACUTE:
            qualifiers.append("acute global market stress")
        elif vix > VIX_ELEVATED:
            qualifiers.append("elevated market volatility")

    if not math.isnan(ciss) and ciss > CISS_STRESS:
        qualifiers.append("European systemic stress elevated")

    return {
        "global_sync": global_sync,
        "global_qualifiers": qualifiers,
        "commodity_channel": commodity_channel,
    }

# ---------------------------------------------------------------------------
# STATE MACHINE — hysteresis on G and I axes only
# ---------------------------------------------------------------------------

class RegimeStateMachine:
    """
    2-month confirmation hysteresis for growth and inflation axes.
    Overlay stress has NO hysteresis.
    Sahm gate — v1.1.0, EDGE-TRIGGERED : le FRANCHISSEMENT à la hausse de
    SAHM_THRESHOLD force G_minus immédiatement (entrée inchangée, sans délai).
    La persistance de G_minus est ensuite gouvernée par la machine à états
    normale (candidat CFNAI-MA3 + confirmation 2 mois). Un retour de Sahm sous
    le seuil ré-arme le gate pour le prochain franchissement.
    Justification (backtest 1968-2026) : la règle de NIVEAU v1.0.0 maintenait
    G_minus tant que Sahm restait >= 0.50, longtemps après les reprises —
    Stagflation 1991-07→1992-12 (18 m), Slowdown 2020-08→2021-04 (CFNAI-MA3
    jusqu'à +4.6), Stagflation 2024-07→10 sans récession NBER. L'edge conserve
    8/8 captures NBER et des latences d'entrée identiques, et réduit les mois
    de G_minus faux positifs de 55 à 4 (résiduel documenté : 2024-07/08,
    1976-11/12).
    """
    CONFIRMATION_MONTHS = 2

    def __init__(self, initial_g: str = "G_neutral", initial_i: str = "I_neutral"):
        self.current_growth = initial_g
        self.current_inflation = initial_i
        self._pending_g: Optional[str] = None
        self._pending_g_count: int = 0
        self._pending_i: Optional[str] = None
        self._pending_i_count: int = 0
        self._gate_level_prev: bool = False   # v1.1.0 — détection de front du gate Sahm

    def update(self, candidate_g: str, candidate_i: str, sahm: float) -> tuple[str, str]:
        # v1.1.0 — gate Sahm déclenché sur FRANCHISSEMENT (edge), plus sur niveau.
        gate_level = not math.isnan(sahm) and sahm >= SAHM_THRESHOLD
        gate_edge = gate_level and not self._gate_level_prev
        self._gate_level_prev = gate_level
        if gate_edge:
            self.current_growth = "G_minus"
            self._pending_g = None
            self._pending_g_count = 0
        else:
            self._update_axis_g(candidate_g)
        self._update_axis_i(candidate_i)
        return self.current_growth, self.current_inflation

    def _update_axis_g(self, candidate: str) -> None:
        if candidate == self.current_growth:
            self._pending_g = None
            self._pending_g_count = 0
        elif candidate == self._pending_g:
            self._pending_g_count += 1
            if self._pending_g_count >= self.CONFIRMATION_MONTHS:
                self.current_growth = candidate
                self._pending_g = None
                self._pending_g_count = 0
        else:
            self._pending_g = candidate
            self._pending_g_count = 1

    def _update_axis_i(self, candidate: str) -> None:
        if candidate == self.current_inflation:
            self._pending_i = None
            self._pending_i_count = 0
        elif candidate == self._pending_i:
            self._pending_i_count += 1
            if self._pending_i_count >= self.CONFIRMATION_MONTHS:
                self.current_inflation = candidate
                self._pending_i = None
                self._pending_i_count = 0
        else:
            self._pending_i = candidate
            self._pending_i_count = 1

# ---------------------------------------------------------------------------
# RESOLVER
# ---------------------------------------------------------------------------

_OVERLAY_PREFIX_EN = {
    "accommodating": "under accommodating financial conditions — ",
    "neutral":       "",
    "restrictive":    "under restrictive financial conditions — ",
    "acute_stress":   "under acute financial stress — ",
}
_OVERLAY_PREFIX_FR = {
    "accommodating": "dans un contexte financier accommodant — ",
    "neutral":       "",
    "restrictive":    "dans un contexte de conditions financières restrictives — ",
    "acute_stress":   "sous stress financier aigu — ",
}


def resolve_regime(
    confirmed_g: str,
    confirmed_i: str,
    stress: str,
    global_ctx: dict,
    brent_yoy: float,
) -> dict:
    code, name_en, name_fr = REGIME_GRID.get(
        (confirmed_g, confirmed_i), (8, "Transition / Mixed signals", "Transition / Signaux mixtes")
    )
    full_en = _OVERLAY_PREFIX_EN.get(stress, "") + name_en
    full_fr = _OVERLAY_PREFIX_FR.get(stress, "") + name_fr

    hud = (
        confirmed_i in ("I_neutral", "I_minus")
        and not math.isnan(brent_yoy)
        and brent_yoy > HUD_BRENT_SHOCK   # v1.1.0 : seuil dédié (+40), cf. constantes
    )

    colors = COLOR_MAP.get(code, COLOR_MAP[8])
    return {
        "regime_code":                  code,
        "regime_name_EN":               name_en,
        "regime_name_FR":               name_fr,
        "full_label_EN":                full_en,
        "full_label_FR":                full_fr,
        "headline_underlying_divergence": hud,
        "color_zone_hex":               colors["zone"],
        "color_line_hex":               colors["line"],
        "color_label_hex":              colors["label"],
    }

# ---------------------------------------------------------------------------
# DATA BUNDLE — fetches everything once, shared between history and current
# ---------------------------------------------------------------------------

class DataBundle:
    def __init__(self, fetcher: FredFetcher):
        log.info("Fetching FRED series...")
        self.cfnai        = fetcher.get_resampled("CFNAI", "monthly")
        time.sleep(1.5)
        self.cfnai_ma3    = compute_cfnai_ma3(self.cfnai)
        
        self.sahmrealtime = fetcher.get_resampled("SAHMREALTIME", "monthly")
        time.sleep(1.5)
        
        self.icsa_weekly  = fetcher.get_resampled("ICSA", "weekly")
        time.sleep(1.5)
        
        self.icsa_yoy     = compute_icsa_4w_ma_yoy(self.icsa_weekly)
        
        self.pce_trimmed  = fetcher.get_resampled("PCETRIM12M159SFRBDAL", "monthly")
        time.sleep(1.5)
        
        self.t5yifr       = fetcher.get_resampled("T5YIFR", "monthly")
        time.sleep(1.5)
        
        self.nfci_weekly  = fetcher.get_resampled("NFCI", "weekly")
        time.sleep(1.5)
        
        self.nfci_monthly = compute_nfci_monthly(self.nfci_weekly)
        
        self.t10y2y       = fetcher.get_resampled("T10Y2Y", "monthly")
        time.sleep(1.5)
        
        self.fedfunds     = fetcher.get_resampled("FEDFUNDS", "monthly")
        time.sleep(1.5)
        
        self.us_cli       = fetcher.get_resampled("USALOLITOAASTSAM", "monthly")
        time.sleep(1.5)
        
        self.g7_cli       = fetcher.get_resampled("G7LOLITOAASTSAM", "monthly")
        time.sleep(1.5)
        
        self.us_cli_delta = compute_cli_delta_3m(self.us_cli)
        self.g7_cli_delta = compute_cli_delta_3m(self.g7_cli)
        
        self.dtwexbgs     = fetcher.get_resampled("DTWEXBGS", "monthly")
        time.sleep(1.5)
        
        self.dtwexbgs_3m  = compute_dtwexbgs_3m_pct(self.dtwexbgs)
        
        self.vix          = fetcher.get_resampled("VIXCLS", "monthly")
        time.sleep(1.5)

        log.info("Fetching SOS (Richmond Fed)...")
        self.sos_weekly = fetch_richmond_sos()

        log.info("Fetching ECB CISS...")
        ciss_daily = fetch_ecb_ciss()
        self.ciss_monthly = (
            ciss_daily.resample("MS").mean()
            if not ciss_daily.empty
            else pd.Series(dtype=float)
        )

        log.info("Loading Brent...")
        self.brent_monthly = load_world_bank_brent(fetcher)
        time.sleep(1.5)
        self.brent_yoy     = compute_brent_yoy(self.brent_monthly)

        log.info("Loading local fixtures...")
        hy_fixture = load_local_fixture(BAMLH0A0HYM2_FIXTURE)
        if not hy_fixture.empty:
            # Fixture covers pre-2023; FRED covers last 3 years (corroboration only)
            try:
                hy_live = fetcher.get_resampled("BAMLH0A0HYM2", "monthly")
                time.sleep(1.5)
                self.hy_oas = hy_fixture.combine_first(hy_live)
            except Exception:
                self.hy_oas = hy_fixture
        else:
            # No fixture: only 3-year FRED window — logged as partial, not used in backtest
            try:
                self.hy_oas = fetcher.get_resampled("BAMLH0A0HYM2", "monthly")
                time.sleep(1.5)
                log.info("HY OAS: 3-year window only (no pre-2023 fixture)")
            except Exception:
                self.hy_oas = pd.Series(dtype=float)

        log.info("Data bundle complete.")

    def get_month_inputs(self, month: pd.Timestamp) -> dict:
        def g(series, lag=3):
            val, _ = get_latest_available(series, month, lag)
            return val

        # SOS: last weekly value in the month
        sos_val = float("nan")
        if not self.sos_weekly.empty:
            mask = (self.sos_weekly.index >= month) & (
                self.sos_weekly.index <= month + pd.offsets.MonthEnd(0)
            )
            subset = self.sos_weekly[mask]
            if not subset.empty:
                sos_val = float(subset.iloc[-1])

        return {
            "cfnai_ma3":          g(self.cfnai_ma3),
            "sahmrealtime":       g(self.sahmrealtime),
            "sos":                sos_val,
            "pce_trimmed_12m":    g(self.pce_trimmed),
            "t5yifr":             g(self.t5yifr),
            "nfci":               g(self.nfci_monthly),
            "hy_oas_bps":         g(self.hy_oas) if not self.hy_oas.empty else float("nan"),
            "t10y2y":             g(self.t10y2y),
            "fedfunds":           g(self.fedfunds),
            "usaloli_3m_delta":   g(self.us_cli_delta),
            "g7loli_3m_delta":    g(self.g7_cli_delta),
            "dtwexbgs_3m_pct":    g(self.dtwexbgs_3m),
            "brent_yoy_pct":      g(self.brent_yoy),
            "vixcls":             g(self.vix),
            "icsa_4w_ma_yoy_pct": g(self.icsa_yoy),
            "ciss":               g(self.ciss_monthly),
        }

# ---------------------------------------------------------------------------
# HISTORY RUNNER
# ---------------------------------------------------------------------------

def run_history(bundle: DataBundle, start_date: str = "2003-01-01") -> pd.DataFrame:
    start_ts = pd.Timestamp(start_date)
    current_month = pd.Timestamp.now().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    months = pd.date_range(start=start_ts, end=current_month, freq="MS")

    sm = RegimeStateMachine()
    rows = []

    for month in months:
        inputs = bundle.get_month_inputs(month)
        candidate_g = raw_classify_growth(
            inputs["cfnai_ma3"], inputs["sahmrealtime"], inputs["sos"]
        )
        candidate_i = raw_classify_inflation(inputs["pce_trimmed_12m"])
        sahm = inputs["sahmrealtime"]
        if math.isnan(sahm):
            sahm = 0.0

        confirmed_g, confirmed_i = sm.update(candidate_g, candidate_i, sahm)
        stress = classify_stress(inputs["nfci"])
        global_ctx = classify_global_context(
            inputs["usaloli_3m_delta"], inputs["g7loli_3m_delta"],
            inputs["dtwexbgs_3m_pct"], inputs["brent_yoy_pct"],
            inputs["vixcls"], inputs.get("ciss", float("nan")),
        )
        resolved = resolve_regime(
            confirmed_g, confirmed_i, stress, global_ctx, inputs["brent_yoy_pct"]
        )
        icsa_ok = (
            not math.isnan(inputs.get("icsa_4w_ma_yoy_pct", float("nan")))
            and inputs["icsa_4w_ma_yoy_pct"] > ICSA_CORR_THRESH
        )

        # hy_oas_bps: null pre-2023 if no fixture loaded
        hy_val = inputs.get("hy_oas_bps", float("nan"))
        if not math.isnan(hy_val) and month < pd.Timestamp("2023-05-01"):
            hy_val = float("nan")  # fixture boundary

        data_quality = "full" if month >= pd.Timestamp("2003-01-01") else "degraded"

        rows.append({
            "date":                         month.strftime("%Y-%m-%d"),
            "regime_code":                  resolved["regime_code"],
            "regime_name_EN":               resolved["regime_name_EN"],
            "regime_name_FR":               resolved["regime_name_FR"],
            "growth_state":                 confirmed_g,
            "inflation_state":              confirmed_i,
            "stress_overlay":               stress,
            "global_sync":                  global_ctx["global_sync"],
            "cfnai_ma3":                    _f(inputs.get("cfnai_ma3")),
            "sahmrealtime":                 _f(inputs.get("sahmrealtime")),
            "sos":                          _f(inputs.get("sos")),
            "pce_trimmed_12m":              _f(inputs.get("pce_trimmed_12m")),
            "t5yifr":                       _f(inputs.get("t5yifr")),
            "nfci":                         _f(inputs.get("nfci")),
            "t10y2y":                       _f(inputs.get("t10y2y")),
            "fedfunds":                     _f(inputs.get("fedfunds")),
            "usaloli_3m_delta":             _f(inputs.get("usaloli_3m_delta")),
            "g7loli_3m_delta":              _f(inputs.get("g7loli_3m_delta")),
            "dtwexbgs_3m_pct":              _f(inputs.get("dtwexbgs_3m_pct")),
            "brent_yoy_pct":                _f(inputs.get("brent_yoy_pct")),
            "vixcls":                       _f(inputs.get("vixcls")),
            "headline_underlying_divergence": resolved["headline_underlying_divergence"],
            "thresholds_version":           THRESHOLDS_VERSION,
            "data_quality":                 data_quality,
            # Extra columns (outside the core output schema, retained for transparency)
            "global_qualifiers":            json.dumps(global_ctx["global_qualifiers"]),
            "hy_oas_bps":                   _f(hy_val),
            "icsa_4w_ma_yoy_pct":           _f(inputs.get("icsa_4w_ma_yoy_pct")),
            "icsa_corroboration_triggered": icsa_ok,
        })

    # Column order: the 24 core columns first, then extras
    # NB : vixcls (CBOE), hy_oas_bps (ICE BofA), usaloli/g7loli_3m_delta (OECD) sont
    # calcules en interne (global_sync, qualifiers) mais NON publies dans le CSV/XLSX
    # pour cause de licence. Les labels derives (global_sync, global_qualifiers) restent.
    core_cols = [
        "date", "regime_code", "regime_name_EN", "regime_name_FR",
        "growth_state", "inflation_state", "stress_overlay", "global_sync",
        "cfnai_ma3", "sahmrealtime", "sos", "pce_trimmed_12m", "t5yifr",
        "nfci", "t10y2y", "fedfunds",
        "dtwexbgs_3m_pct", "brent_yoy_pct",
        "headline_underlying_divergence", "thresholds_version", "data_quality",
        "global_qualifiers", "icsa_4w_ma_yoy_pct",
        "icsa_corroboration_triggered",
    ]
    df = pd.DataFrame(rows)
    return df[[c for c in core_cols if c in df.columns]]

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    log.info("=" * 60)
    log.info("Eco3min Regime Classifier v1.1.0")
    log.info(f"Thresholds: {THRESHOLDS_VERSION}")
    log.info(f"Run time: {datetime.now(timezone.utc).isoformat()}")
    log.info("=" * 60)

    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        log.error("FRED_API_KEY not set in environment — exiting")
        log.error("Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html")
        sys.exit(1)

    fetcher = FredFetcher(api_key)
    bundle  = DataBundle(fetcher)

    # --- History ---
    log.info(f"[STEP 1] Running history ({HISTORY_START[:4]}–present)...")
    history = run_history(bundle, start_date=HISTORY_START)
    csv_path = OUTPUT_DIR / "regime_history.csv"
    history.to_csv(csv_path, index=False)
    log.info(f"History: {len(history)} months → {csv_path}")

    # --- Current ---
    log.info("[STEP 2] Resolving current regime...")
    latest   = history.iloc[-1]
    month_ts = pd.Timestamp(latest["date"])
    inputs   = bundle.get_month_inputs(month_ts)

    lagged = [
        k for k, v in inputs.items()
        if isinstance(v, float) and math.isnan(v)
        and k not in ("sos", "ciss", "hy_oas_bps")
    ]
    freshness = "lagged" if lagged else "current"

    colors = COLOR_MAP.get(int(latest["regime_code"]), COLOR_MAP[8])
    current = {
        "regime_name_EN":               latest["regime_name_EN"],
        "regime_name_FR":               latest["regime_name_FR"],
        "regime_code":                  int(latest["regime_code"]),
        "growth_state":                 latest["growth_state"],
        "inflation_state":              latest["inflation_state"],
        "stress_overlay":               latest["stress_overlay"],
        "full_label_EN":                _OVERLAY_PREFIX_EN.get(latest["stress_overlay"], "") + latest["regime_name_EN"],
        "full_label_FR":                _OVERLAY_PREFIX_FR.get(latest["stress_overlay"], "") + latest["regime_name_FR"],
        "global_sync":                  latest["global_sync"],
        "global_qualifiers":            json.loads(latest["global_qualifiers"])
                                        if isinstance(latest.get("global_qualifiers"), str) else [],
        "headline_underlying_divergence": bool(latest["headline_underlying_divergence"]),
        "color_zone_hex":               colors["zone"],
        "color_line_hex":               colors["line"],
        "color_label_hex":              colors["label"],
        "data_as_of":                   month_ts.strftime("%Y-%m-%d"),
        "computed_at":                  datetime.now(timezone.utc).isoformat(),
        "thresholds_version":           THRESHOLDS_VERSION,
        "data_freshness":               freshness,
        "lagged_inputs":                lagged,
        "icsa_corroboration_triggered": bool(latest.get("icsa_corroboration_triggered", False)),
        # Licensed inputs (ICE BofA, Cboe, OECD) are computed but not published.
        "input_values": {
            k: _f(v) for k, v in inputs.items()
            if k not in ("hy_oas_bps", "vixcls", "usaloli_3m_delta", "g7loli_3m_delta")
        },
        "methodology_url_EN": "https://eco3min.fr/en/macro-regime-classification-methodology/",
        "methodology_url_FR": "https://eco3min.fr/methodologie-classification-regime-macro/",
    }

    json_path = OUTPUT_DIR / "regime_current.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2, ensure_ascii=False, default=str)
    log.info(f"Current: {current['full_label_EN']}")
    log.info(f"  Data as of: {current['data_as_of']}")
    log.info(f"  headline_underlying_divergence: {current['headline_underlying_divergence']}")
    log.info(f"  data_freshness: {freshness}")
    log.info(f"  → {json_path}")

    log.info("[DONE]")


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _f(val) -> Optional[float]:
    """float → round(4) or None for NaN."""
    if val is None:
        return None
    try:
        v = float(val)
        return None if math.isnan(v) else round(v, 4)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    main()
