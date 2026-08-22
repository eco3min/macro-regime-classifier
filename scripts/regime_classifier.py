#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
regime_classifier.py — Eco3min Macro Regime Classifier v1.1.0
Builder code-driven (non-FRED pipeline pattern, eco3min_updater_v2.py family)

Outputs (publiés — output/datasets/, servi sous eco3min.fr/dataset/):
  regime_current.json      — signal catégoriel + inputs publics uniquement
  regime_history.csv/.xlsx — colonnes core_cols uniquement (vixcls, hy_oas_bps,
                             usaloli/g7loli exclus : licences Cboe/ICE/OECD)
Inputs locaux (NON publiés — fixtures/):
  fixtures/bamlh0a0hym2_history.csv, fixtures/wu_xia_history.csv

Invariants (pipeline-eco3min):
  - dataset_id stable: regime_current / regime_history
  - date in first column of CSV
  - regime_history: explicit derogation — multi-column classification table,
    regime_code in col 2 (not last), see pipeline_spec.md §5
  - touch WP after deploy
  - permissions 755 on OVH
"""

import json
import math
import os
import sys
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict
from typing import Optional, Dict

import pandas as pd
import numpy as np
import requests

# Shared infra — FredFetcher, touch_wordpress
from eco3min_common import FredFetcher, touch_wordpress

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
# CONFIGURATION — chemins relatifs à l'arbo du repo eco3min-data
#   scripts/regime_classifier.py  (ce fichier)
#   config/thresholds.json
#   output/datasets/              (outputs pipeline, commun avec eco3min_updater)
# ---------------------------------------------------------------------------
THRESHOLDS_VERSION = "1.1.0"

SCRIPT_DIR = Path(__file__).resolve().parent   # repo/scripts/
REPO_ROOT  = SCRIPT_DIR.parent                 # repo/

# Outputs — même dossier que le reste du pipeline
OUTPUT_DIR = REPO_ROOT / "output" / "datasets"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# --- Outil « Regime macro a une date » -------------------------------------
# Borne dure de l'historique : PCETRIM12M159SFRBDAL commence en 1978-01.
# Avant cette date l'axe inflation n'existe pas, donc le regime non plus.
HISTORY_START    = "1978-01-01"
CALIBRATION_FROM = "2003-01"   # fenetre de calibration des seuils

# Fichier lu par l'outil, servi sur https://eco3min.fr/dataset/
REGIME_LOOKUP_ID = "regime_lookup"

# Bloc marche FR. L'IPC vient de ta propre serie INSEE chainee (fr_updater.py) ;
# a defaut, repli sur l'IPCH Eurostat (1996+), logge bruyamment. Le reste vient
# de FRED (series OCDE, citation requise).
FR_OUTPUT_DIR     = REPO_ROOT / "output" / "datasets-fr"
FR_CPI_DATASET_ID = "fr-cpi"   # IPC INSEE ensemble des menages, chaine
# Serie publiee — utilisee quand le CSV local est absent (cas du CI).
FR_CPI_URL        = "https://eco3min.fr/dataset/fr/fr-cpi.json"


# WordPress touch — same endpoint as updater, same signature
WP_TOUCH_URL = "https://eco3min.fr/wp-json/eco3min/v1/touch-datasets"

# ECB SDW API
ECB_API_BASE = "https://data-api.ecb.europa.eu/service/data"

# Richmond Fed SOS
RICHMOND_FED_SOS_URL = (
    "https://www.richmondfed.org/research/national_economy/sos_recession_indicator"
)

# World Bank Brent — output du pipeline existant
WORLD_BANK_BRENT_CSV = OUTPUT_DIR / "world_bank_brent.csv"

# Local fixtures — données sous licence tierce (ICE BofA, Wu-Xia), utilisées
# comme INPUT de calcul uniquement, jamais publiées.
# ⚠️ JAMAIS dans OUTPUT_DIR : output/datasets est SFTP-é en bloc (`put *`)
# vers www/dataset/ → tout fichier qui s'y trouve devient public.
# → git mv output/datasets/bamlh0a0hym2_history.csv fixtures/
# → git mv output/datasets/wu_xia_history.csv        fixtures/   (si présent)
# → supprimer les copies éventuelles côté OVH : www/dataset/bamlh0a0hym2_history.csv, wu_xia_history.csv
FIXTURES_DIR = REPO_ROOT / "fixtures"
FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
BAMLH0A0HYM2_FIXTURE = FIXTURES_DIR / "bamlh0a0hym2_history.csv"
WU_XIA_FIXTURE        = FIXTURES_DIR / "wu_xia_history.csv"

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
# THRESHOLDS (thresholds.json v1.0.0)
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
BRENT_SHOCK        = 20.0    # YoY pct — commodity_channel / qualifiers (inchangé v1.1.0)
BRENT_DEMAND_DESTR = -20.0
# v1.1.0 — seuil DÉDIÉ au flag headline_underlying_divergence, découplé de
# BRENT_SHOCK. Backtest 1968-2026 : à +20%, le flag était actif 26,0% des mois
# post-1988 (pas un signal) ; à +40% : 17,9%, tous les épisodes de choc réels
# conservés (dont mars-mai 2026). Le qualifier commodity_channel reste à ±20.
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
        
        self.dfii10       = fetcher.get_resampled("DFII10", "monthly")  # [terminal] taux réel 10 ans
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

        # GARDE-FOU DE DOMAINE. raw_classify_inflation(nan) -> "I_neutral" et
        # classify_stress(nan) -> "neutral" : un mois hors couverture ne leve
        # aucune erreur, il ressort CLASSE et indistinguable d'un vrai.
        # On l'ecarte au lieu de le classer. Le `continue` saute aussi
        # sm.update() : pas d'observation, pas de transition d'etat.
        if (math.isnan(inputs["cfnai_ma3"])
                or math.isnan(inputs["pce_trimmed_12m"])
                or math.isnan(inputs["nfci"])):
            log.info(
                f"  {month:%Y-%m} ecarte — axe manquant "
                f"(cfnai_ma3={inputs['cfnai_ma3']}, "
                f"pce={inputs['pce_trimmed_12m']}, nfci={inputs['nfci']})"
            )
            continue

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
            # Extra columns (not in §6.2 core spec but retained for transparency)
            "global_qualifiers":            json.dumps(global_ctx["global_qualifiers"]),
            "hy_oas_bps":                   _f(hy_val),
            "icsa_4w_ma_yoy_pct":           _f(inputs.get("icsa_4w_ma_yoy_pct")),
            "icsa_corroboration_triggered": icsa_ok,
        })

    # Column order: §6.2 core 24 cols first, then extras
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

# ---------------------------------------------------------------------------
# TERMINAL — bloc `terminal` du panneau [14] (page /regime-aujourdhui/)
#   10 indicateurs curés : valeur + tendance MoM + zone descriptive (AMF-safe)
#   + drapeau drives_regime. Zones ancrees sur les constantes ci-dessus.
# ---------------------------------------------------------------------------

# ids des datasets lus depuis https://eco3min.fr/dataset/{id}.json
SCORE_DATASET_ID      = "score-eco3min"        # confirme (score_eco3min.py)
OIL_BURDEN_DATASET_ID = "oil-burden-gdp-ratio" # /!\ A CONFIRMER via la liste /dataset/
DATASET_BASE_URL      = "https://eco3min.fr/dataset"

# Cibles de lien par card (maillage interne). Card cliquable -> page dataset /
# Atlas / pilier de l'indicateur. Laisser "" = card NON cliquable (rend a
# l'identique, fail-safe : pas de lien 404). Chemins RELATIFS au domaine
# (commencent par "/"). FR = racine ; EN = prefixe "/en/". Le shortcode choisit
# url_fr ou url_en selon la langue de la page. A REMPLIR avec les vrais slugs.
# Toutes les cibles pointent vers une page DATASET BRUT (graphique + CSV),
# JAMAIS vers une etude approfondie. Verifie contre l'index A-Z du hub (liste
# canonique des datasets), pas le sitemap (des slugs d'etudes contiennent
# "-dataset"). Aucun dataset FR brut n'existe (datasets = EN only) -> fr pointe
# vers la meme page /en/ que en, comme le fait deja le hub FR ("Voir le jeu de
# donnees" -> /en/...). Blanchir un fr ("") pour card FR non cliquable.
CARD_LINKS = {
    "nfci":              {"fr": "/en/financial-conditions-index-dataset/",            "en": "/en/financial-conditions-index-dataset/"},
    "cfnai_ma3":         {"fr": "/en/cfnai-national-activity-index-dataset/",         "en": "/en/cfnai-national-activity-index-dataset/"},
    "pce_trimmed":       {"fr": "/en/trimmed-mean-pce-inflation-dataset/",            "en": "/en/trimmed-mean-pce-inflation-dataset/"},
    "yield_curve_2s10s": {"fr": "/en/yield-curve-inversion-history-dataset/",         "en": "/en/yield-curve-inversion-history-dataset/"},
    "real_rate_10y":     {"fr": "/en/real-interest-rates-history-dataset/",           "en": "/en/real-interest-rates-history-dataset/"},
    "ciss":              {"fr": "/en/euro-area-ciss-systemic-stress-dataset/",        "en": "/en/euro-area-ciss-systemic-stress-dataset/"},
    "dollar_3m":         {"fr": "/en/us-dollar-index-dataset-dtwexbgs/",              "en": "/en/us-dollar-index-dataset-dtwexbgs/"},
    "brent_yoy":         {"fr": "/en/brent-crude-oil-price-dataset/",                "en": "/en/brent-crude-oil-price-dataset/"},
    "score_eco3min":     {"fr": "/en/eco3min-inflation-regime-score-us-dataset/",     "en": "/en/eco3min-inflation-regime-score-us-dataset/"},
}

# Seuils oil burden (etude Eco3min, % du PIB)
OIL_BURDEN_SUBREC = 3.0
OIL_BURDEN_RISK   = 4.0
# Seuils HY OAS (bps) — norme historique
HY_OAS_CALM   = 300.0
HY_OAS_STRESS = 500.0
# Courbe 2s10s (pp) — convention de marche
CURVE_FLAT_HI = 0.50
# Taux reel DFII10 (%) — seuil repression financiere (Atlas)
DFII10_LOW_HI = 1.0
# Dollar Delta3M (%) — seuil dollar shortage (Atlas)
DTWEXBGS_TENSION = 5.0
# Score eco3min — bandes de regime (score_eco3min.py REGIMES)
SCORE_BANDS = [
    (-float("inf"), -0.5, "low",     "déflation",     "deflation"),
    (-0.5,           1.5, "low",     "désinflation",  "disinflation"),
    ( 1.5,           3.0, "neutral", "cible",         "target"),
    ( 3.0,          15.0, "high",    "élevée",        "elevated"),
    (15.0, float("inf"),  "stress",  "très élevée",   "very high"),
]


def _term_nan(v):
    return v is None or (isinstance(v, float) and math.isnan(v))

def _term_unavail():
    return ("unavailable", "indisponible", "unavailable")

def zone_nfci(v):
    if _term_nan(v): return _term_unavail()
    if v < NFCI_ACCOMMODATING: return ("accommodating", "accommodantes", "accommodating")
    if v < NFCI_RESTRICTIVE:   return ("neutral", "neutres", "neutral")
    if v < NFCI_ACUTE:         return ("restrictive", "restrictives", "restrictive")
    return ("stress", "stress aigu", "acute stress")

def zone_cfnai(v):
    if _term_nan(v): return _term_unavail()
    if v > G_PLUS_THRESHOLD:  return ("neutral", "au-dessus de la tendance", "above trend")
    if v < G_MINUS_THRESHOLD: return ("stress", "en contraction", "contracting")
    return ("neutral", "dans la tendance", "on trend")

def zone_pce(v):
    if _term_nan(v): return _term_unavail()
    if v > I_PLUS_THRESHOLD:  return ("high", "élevée", "elevated")
    if v < I_MINUS_THRESHOLD: return ("low", "désinflation", "decelerating")
    return ("neutral", "proche cible", "near target")

def zone_ciss(v):
    if _term_nan(v): return _term_unavail()
    if v > CISS_STRESS: return ("stress", "stress", "stress")
    return ("neutral", "calme", "calm")

def zone_curve(v):
    if _term_nan(v): return _term_unavail()
    if v < 0:             return ("restrictive", "inversée", "inverted")
    if v < CURVE_FLAT_HI: return ("neutral", "plate", "flat")
    return ("neutral", "pentue", "steep")

def zone_dfii10(v):
    if _term_nan(v): return _term_unavail()
    if v < 0:             return ("low", "négatif", "negative")
    if v < DFII10_LOW_HI: return ("neutral", "bas", "low")
    return ("high", "élevé", "elevated")

def zone_dollar(v):  # v = variation 3M en %
    if _term_nan(v): return _term_unavail()
    if v > DTWEXBGS_TENSION: return ("restrictive", "tension dollar", "dollar tension")
    return ("neutral", "neutre", "neutral")

def zone_hy(v):  # bps
    if _term_nan(v): return _term_unavail()
    if v > HY_OAS_STRESS: return ("stress", "stress de crédit", "credit stress")
    if v > HY_OAS_CALM:   return ("restrictive", "tension", "widening")
    return ("neutral", "calme", "calm")

def zone_oil(v):  # % du PIB — RESERVE : aucun dataset oil-burden publie (etude seulement).
                  # Conserve pour reactivation si un dataset oil-burden/PIB est cree un jour.
    if _term_nan(v): return _term_unavail()
    if v >= OIL_BURDEN_RISK:   return ("stress", "seuil de risque", "risk threshold")
    if v >= OIL_BURDEN_SUBREC: return ("restrictive", "élevé", "elevated")
    return ("neutral", "sous-récessionnaire", "sub-recessionary")

def zone_score(v):
    if _term_nan(v): return _term_unavail()
    for lo, hi, zk, fr, en in SCORE_BANDS:
        if lo <= v < hi:
            return (zk, fr, en)
    return _term_unavail()

def zone_brent(v):  # variation YoY en % — seuils ancres BRENT_SHOCK / BRENT_DEMAND_DESTR
    if _term_nan(v): return _term_unavail()
    if v > BRENT_SHOCK:        return ("high", "choc énergétique", "energy shock")
    if v < BRENT_DEMAND_DESTR: return ("high", "chute de la demande", "demand contraction")
    return ("neutral", "stable", "stable")


def read_dataset_latest(dataset_id, metric_key=None):
    """(value, as_of, prev_value) ou (None, None, None) si indispo.
    metric_key : colonne metrique explicite. Si None, prend la DERNIERE cle
    non-date (contrat pipeline 2.3). /!\ score-eco3min met `score` en PREMIERE
    colonne -> passer metric_key="score". Degradation gracieuse, jamais de crash."""
    try:
        url = "%s/%s.json" % (DATASET_BASE_URL, dataset_id)
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        records = r.json()
        if not records:
            return (None, None, None)
        def metric(rec):
            if metric_key and metric_key in rec:
                return rec[metric_key]
            keys = [k for k in rec.keys() if k != "date"]
            return rec[keys[-1]] if keys else None
        last = records[-1]
        prev = records[-2] if len(records) >= 2 else None
        return (metric(last), last.get("date"), metric(prev) if prev else None)
    except Exception:
        return (None, None, None)


def _term_series_latest_prev(series):
    """(latest, prev, as_of) depuis une pd.Series monthly du bundle."""
    if series is None or len(series) == 0:
        return (None, None, None)
    s = series.dropna()
    if s.empty:
        return (None, None, None)
    latest = float(s.iloc[-1])
    prev = float(s.iloc[-2]) if len(s) >= 2 else None
    as_of = str(s.index[-1].date())
    return (latest, prev, as_of)

def _term_trend(latest, prev):
    if _term_nan(latest) or _term_nan(prev):
        return (None, "flat")
    d = round(latest - prev, 2)
    return (d, "up" if d > 0 else ("down" if d < 0 else "flat"))


def build_terminal_block(bundle, growth_state, inflation_state, stress_overlay, hud):
    """Liste `terminal` a injecter dans le dict `current`. Grille curee (10) ;
    VIX/Brent/Fedfunds/ACMTP10 restent en mode `full`."""
    drives_g = growth_state    != "G_neutral"
    drives_i = inflation_state != "I_neutral"
    drives_s = stress_overlay  != "neutral"

    block = []

    def card(key, fr, en, unit, code, source, latest, prev, as_of, zone_fn, drives=False):
        zk, zfr, zen = zone_fn(latest)
        td, tdir = _term_trend(latest, prev)
        links = CARD_LINKS.get(key, {})
        block.append({
            "key": key, "label_fr": fr, "label_en": en,
            "series_code": code, "source_label": source,
            "value": (None if _term_nan(latest) else round(latest, 4)),
            "unit": unit, "as_of": as_of,
            "trend_mom": td, "trend_dir": tdir,
            "zone": zk, "zone_label_fr": zfr, "zone_label_en": zen,
            "drives_regime": bool(drives),
            "url_fr": links.get("fr", ""), "url_en": links.get("en", ""),
        })

    lv, pv, ao = _term_series_latest_prev(bundle.nfci_monthly)
    card("nfci", "NFCI", "NFCI", "", "NFCI", "FRED \u00b7 NFCI", lv, pv, ao, zone_nfci, drives_s)
    lv, pv, ao = _term_series_latest_prev(bundle.cfnai_ma3)
    card("cfnai_ma3", "CFNAI-MA3", "CFNAI-MA3", "", "CFNAI", "FRED \u00b7 CFNAI", lv, pv, ao, zone_cfnai, drives_g)
    lv, pv, ao = _term_series_latest_prev(bundle.pce_trimmed)
    card("pce_trimmed", "Trimmed Mean PCE", "Trimmed Mean PCE", "%", "PCETRIM12M159SFRBDAL", "FRED \u00b7 Dallas Fed", lv, pv, ao, zone_pce, drives_i)
    lv, pv, ao = _term_series_latest_prev(bundle.t10y2y)
    card("yield_curve_2s10s", "Courbe 2s10s", "Yield curve 2s10s", "pp", "T10Y2Y", "FRED \u00b7 T10Y2Y", lv, pv, ao, zone_curve)
    lv, pv, ao = _term_series_latest_prev(getattr(bundle, "dfii10", None))
    card("real_rate_10y", "Taux réel 10 ans", "10Y real rate", "%", "DFII10", "FRED \u00b7 DFII10", lv, pv, ao, zone_dfii10)
    lv, pv, ao = _term_series_latest_prev(bundle.ciss_monthly)
    card("ciss", "CISS (zone \u20ac)", "CISS (euro area)", "", "CISS", "ECB \u00b7 CISS", lv, pv, ao, zone_ciss)
    lv, pv, ao = _term_series_latest_prev(bundle.dtwexbgs_3m)
    card("dollar_3m", "Dollar \u03943M", "Dollar \u03943M", "%", "DTWEXBGS", "FRED \u00b7 DTWEXBGS", lv, pv, ao, zone_dollar)
    # 9. Brent YoY (energie) — remplace oil burden : pas de dataset oil-burden
    #    publie (etude seulement). Brent YoY est deja calcule, seuils ancres.
    lv, pv, ao = _term_series_latest_prev(bundle.brent_yoy)
    card("brent_yoy", "Brent (1 an)", "Brent (YoY)", "%", "MCOILBRENTEU", "World Bank CMO / FRED", lv, pv, ao, zone_brent)
    lv, ao, pv = read_dataset_latest(SCORE_DATASET_ID, metric_key="score")
    card("score_eco3min", "Score eco3min", "eco3min score", "score", "\u2014", "Eco3min Research", lv, pv, ao, zone_score)

    return block


def _save_regime_series(
    df: pd.DataFrame,
    dataset_id: str,
    unit: str,
    output_dir: Path,
) -> None:
    """
    Sauvegarde un DataFrame série en CSV + XLSX + JSON + méta,
    dans le même format que eco3min_updater.py / save_dataset().
    Colonnes attendues : date en première position, métrique en dernière.
    """
    if df is None or df.empty:
        log.warning(f"[regime_series] {dataset_id} — dataframe vide, skip")
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    meta_dir = output_dir.parent / "meta"
    meta_dir.mkdir(parents=True, exist_ok=True)

    cols = ["date"] + [c for c in df.columns if c != "date"]
    df = df[cols].dropna()

    # CSV
    csv_path = output_dir / f"{dataset_id}.csv"
    df.to_csv(csv_path, index=False)
    log.info(f"  [regime_series] CSV  → {csv_path}")

    # XLSX
    xlsx_path = output_dir / f"{dataset_id}.xlsx"
    df.to_excel(xlsx_path, index=False, engine="openpyxl")
    log.info(f"  [regime_series] XLSX → {xlsx_path}")

    # JSON (records)
    json_path = output_dir / f"{dataset_id}.json"
    df_j = df.copy()
    if "date" in df_j.columns:
        df_j["date"] = pd.to_datetime(df_j["date"]).dt.strftime("%Y-%m-%d")
    df_j.to_json(json_path, orient="records", force_ascii=False)
    log.info(f"  [regime_series] JSON → {json_path}")

    # Méta (key_stats, même structure que eco3min_updater)
    val_col  = cols[-1]
    values   = df[val_col].dropna()
    latest   = float(values.iloc[-1])
    pct      = float((values < latest).sum() / len(values) * 100)
    hi_idx   = values.idxmax()
    lo_idx   = values.idxmin()

    def _date_at(idx):
        try:
            return str(pd.to_datetime(df.loc[idx, "date"]).date())
        except Exception:
            return None

    meta = {
        "id": dataset_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "key_stats": {
            "latest_value":        round(latest, 4),
            "latest_date":         str(pd.to_datetime(df["date"]).iloc[-1].date()),
            "current_percentile":  round(pct, 1),
            "historical_average":  round(float(values.mean()), 4),
            "historical_high":     round(float(values.max()), 4),
            "historical_high_date": _date_at(hi_idx),
            "historical_low":      round(float(values.min()), 4),
            "historical_low_date": _date_at(lo_idx),
            "observations":        int(len(values)),
            "unit":                unit,
        },
    }
    meta_path = meta_dir / f"{dataset_id}.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    log.info(f"  [regime_series] Meta → {meta_path}")


def main():
    log.info("=" * 60)
    log.info("Eco3min Regime Classifier v1.1.0")
    log.info(f"Thresholds: {THRESHOLDS_VERSION}")
    log.info(f"Run time: {datetime.now(timezone.utc).isoformat()}")
    log.info("=" * 60)

    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        log.error("FRED_API_KEY not set in environment — exiting")
        sys.exit(1)

    fetcher = FredFetcher(api_key)
    bundle  = DataBundle(fetcher)

    # --- History ---
    log.info(f"[STEP 1] Running history ({HISTORY_START[:7]}–present)...")
    history = run_history(bundle, start_date=HISTORY_START)
    csv_path  = OUTPUT_DIR / "regime_history.csv"
    xlsx_path = OUTPUT_DIR / "regime_history.xlsx"
    history.to_csv(csv_path, index=False)
    history.to_excel(xlsx_path, index=False, engine="openpyxl")
    log.info(f"History: {len(history)} months → {csv_path}, {xlsx_path}")

    # --- Current ---
    log.info("[STEP 2] Resolving current regime...")
    latest = history.iloc[-1]
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
        "input_values": {
          k: _f(v) for k, v in inputs.items()
          if k not in ("hy_oas_bps", "vixcls", "usaloli_3m_delta", "g7loli_3m_delta")
        },
        "methodology_url_EN": "https://eco3min.fr/en/macro-regime-classification-methodology/",
        "methodology_url_FR": "https://eco3min.fr/methodologie-classification-regime-macro/",
    }

    # [terminal] panneau [14] — bloc additionnel, retro-compatible
    current["terminal"] = build_terminal_block(
        bundle,
        latest["growth_state"],
        latest["inflation_state"],
        latest["stress_overlay"],
        bool(latest["headline_underlying_divergence"]),
    )

    json_path = OUTPUT_DIR / "regime_current.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2, ensure_ascii=False, default=str)
    log.info(f"Current: {current['full_label_EN']}")
    log.info(f"  Data as of: {current['data_as_of']}")
    log.info(f"  headline_underlying_divergence: {current['headline_underlying_divergence']}")
    log.info(f"  data_freshness: {freshness}")

    # --- WordPress touch ---
    log.info("[STEP 3] Touching WordPress...")
    secret = os.environ.get("WP_TOUCH_SECRET")
    touch_wordpress(WP_TOUCH_URL, secret)

    # --- STEP 4 : Export des 3 séries régime en datasets standalone ---
    # CFNAI, Trimmed Mean PCE et CISS sont consommées par le classifier
    # mais n'avaient pas de page dataset. On les exporte ici dans le même
    # format que eco3min_updater.py pour créer les pages CSV/XLSX/JSON.
    # Les séries du bundle sont DÉJÀ mensuelles (get_resampled) avec un
    # DatetimeIndex — pas de re-resample ni de recompute.
    log.info("[STEP 4] Exporting regime input series as standalone datasets...")

    # 4a. CFNAI + MA3 (bundle.cfnai_ma3 déjà calculé dans le constructeur) ──────
    try:
        cfnai     = bundle.cfnai
        cfnai_ma3 = bundle.cfnai_ma3.reindex(cfnai.index)
        df_cfnai = pd.DataFrame({
            "date":      cfnai.index,
            "cfnai":     cfnai.values,
            "cfnai_ma3": cfnai_ma3.values,
        }).dropna(subset=["cfnai"])
        _save_regime_series(df_cfnai, "cfnai-national-activity-index", "", OUTPUT_DIR)
    except Exception as e:
        log.error(f"  CFNAI export failed: {e}")

    # 4b. Trimmed Mean PCE ────────────────────────────────────────────────────
    try:
        pce = bundle.pce_trimmed
        df_pce = pd.DataFrame({
            "date":            pce.index,
            "pce_trimmed_12m": pce.values,
        }).dropna()
        _save_regime_series(df_pce, "trimmed-mean-pce-inflation", "%", OUTPUT_DIR)
    except Exception as e:
        log.error(f"  Trimmed Mean PCE export failed: {e}")

    # 4c. CISS (zone euro, moyenne mensuelle déjà calculée) ────────────────────
    try:
        ciss = bundle.ciss_monthly
        if ciss is not None and not ciss.empty:
            df_ciss = pd.DataFrame({
                "date": ciss.index,
                "ciss": ciss.values,
            }).dropna()
            _save_regime_series(df_ciss, "euro-area-ciss-systemic-stress", "", OUTPUT_DIR)
        else:
            log.warning("  CISS — série vide, export ignoré")
    except Exception as e:
        log.error(f"  CISS export failed: {e}")

    # --- STEP 5 : JSON de l'outil « Regime macro a une date » ---------------
    log.info("[STEP 5] Exporting regime_lookup.json (outil date)...")
    try:
        export_regime_lookup(bundle, history, fetcher, OUTPUT_DIR)
    except Exception as e:
        log.error(f"  regime_lookup export FAILED: {e}")

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


# ---------------------------------------------------------------------------
# EXPORT — regime_lookup.json, consomme par l'outil « Regime macro a une date »
#
# Source de verite = le DataFrame `history` produit par run_history(). Aucune
# reclassification ici : si le CSV et le JSON divergeaient, le site publierait
# deux verdicts contradictoires sur le meme mois.
# ---------------------------------------------------------------------------

# Series FRED du bloc France. Choix documente :
#  - actions : indice OCDE des cours des actions francaises (base 100 = 2015),
#    mensuel depuis 1955. Ce n'est PAS le CAC 40 — le CAC 40 n'a pas de source
#    primaire libre et ne commence qu'en 1987. Le libelle affiche dit ce que
#    c'est ; on ne relabellise jamais vers une source plus propre.
#  - taux court : taux au jour le jour France puis zone euro (OCDE), mensuel
#    depuis 1955. Ce n'est PAS le taux directeur : avant 1999 la serie de la
#    Banque de France n'est pas homogene. Le libelle le dit.
FR_EQUITY_SERIES    = "SPASTT01FRM661N"   # OCDE — cours des actions, France
FR_OVERNIGHT_SERIES = "IRSTCI01FRM156N"   # OCDE — taux au jour le jour, France
FR_LONG_SERIES      = "IRLTLT01FRM156N"   # OCDE — taux long 10 ans, France
FR_CPI_FALLBACK     = "CP0000FRM086NEST"  # Eurostat — IPCH France, 1996+


def _lookup_csv_series(directory: Path, dataset_id: str) -> pd.Series:
    """Lit {dataset_id}.csv du pipeline (date en 1re col, metrique en DERNIERE)."""
    if not dataset_id:
        return pd.Series(dtype=float)
    path = Path(directory) / f"{dataset_id}.csv"
    if not path.exists():
        log.warning(f"  [lookup] absent: {path} -> champ servi en null")
        return pd.Series(dtype=float)
    try:
        df = pd.read_csv(path)
        s = pd.Series(
            pd.to_numeric(df.iloc[:, -1], errors="coerce").values,
            index=pd.to_datetime(df.iloc[:, 0], errors="coerce"),
        ).dropna()
        s = s.resample("MS").last().dropna()
        log.info(f"  [lookup] {dataset_id}: {len(s)} obs")
        return s
    except Exception as e:
        log.warning(f"  [lookup] lecture {path.name} echouee: {e}")
        return pd.Series(dtype=float)


def _lookup_shiller_sp500() -> pd.Series:
    """S&P 500 mensuel depuis 1871 via le builder Shiller du pipeline v2."""
    try:
        from eco3min_updater_v2 import fetch_shiller
        df = fetch_shiller()[["date", "sp500_price"]].dropna()
        s = pd.Series(df["sp500_price"].values,
                      index=pd.to_datetime(df["date"])).dropna()
        s = s.resample("MS").last().dropna()
        log.info(f"  [lookup] Shiller S&P 500: {len(s)} obs")
        return s
    except Exception as e:
        log.warning(f"  [lookup] Shiller indisponible ({e}) -> sp500 null")
        return pd.Series(dtype=float)


def _lookup_json_series(url: str) -> pd.Series:
    """Lit un dataset publie au format records [{date, ..., metrique}].
    Contrat pipeline : date en 1re cle, metrique en DERNIERE cle."""
    try:
        r = requests.get(url, timeout=25)
        r.raise_for_status()
        records = r.json()
        if not records:
            return pd.Series(dtype=float)
        keys = [k for k in records[0].keys() if k != "date"]
        if not keys:
            return pd.Series(dtype=float)
        metric = keys[-1]
        s = pd.Series(
            [rec.get(metric) for rec in records],
            index=pd.to_datetime([rec.get("date") for rec in records], errors="coerce"),
        )
        s = pd.to_numeric(s, errors="coerce").dropna()
        s = s[s.index.notna()].resample("MS").last().dropna()
        log.info(f"  [lookup] {url.rsplit('/', 1)[-1]}: {len(s)} obs "
                 f"({s.index.min():%Y-%m} -> {s.index.max():%Y-%m})")
        return s
    except Exception as e:
        log.warning(f"  [lookup] lecture HTTP {url} echouee: {e}")
        return pd.Series(dtype=float)


def _lookup_at(s: pd.Series, ts, floor_ym: str = None):
    """Valeur du mois exact, ou None. Jamais de report du mois precedent."""
    if floor_ym and f"{ts:%Y-%m}" < floor_ym:
        return None
    if s is None or s.empty or ts not in s.index:
        return None
    v = s.loc[ts]
    return None if pd.isna(v) else round(float(v), 4)


def _lookup_yoy(s: pd.Series, ts):
    prev = ts - pd.DateOffset(years=1)
    if s is None or s.empty or ts not in s.index or prev not in s.index:
        return None
    a, b = s.loc[ts], s.loc[prev]
    if pd.isna(a) or pd.isna(b) or b == 0:
        return None
    return round(float(a / b - 1) * 100, 2)


def _lookup_tail(s: pd.Series):
    if s is None or s.empty:
        return None
    return round(float(s.iloc[-1]), 4)


def export_regime_lookup(bundle, history, fetcher, output_dir: Path) -> None:
    cpi_us = fetcher.get_resampled("CPIAUCNS", "monthly")
    gs10   = fetcher.get_resampled("GS10", "monthly")
    ff     = bundle.fedfunds
    sp500  = _lookup_shiller_sp500()

    fr_long      = fetcher.get_resampled(FR_LONG_SERIES, "monthly")
    fr_overnight = fetcher.get_resampled(FR_OVERNIGHT_SERIES, "monthly")
    fr_equity    = fetcher.get_resampled(FR_EQUITY_SERIES, "monthly")

    # IPC francais : local -> URL publiee -> Eurostat. Jamais silencieux.
    fr_cpi = _lookup_csv_series(FR_OUTPUT_DIR, FR_CPI_DATASET_ID)
    if fr_cpi.empty:
        log.info(f"  [lookup] {FR_CPI_DATASET_ID}.csv absent en local — lecture de {FR_CPI_URL}")
        fr_cpi = _lookup_json_series(FR_CPI_URL)
    if fr_cpi.empty:
        log.warning(f"  [lookup] serie publiee injoignable — repli sur l'IPCH "
                    f"Eurostat {FR_CPI_FALLBACK} (commence en 1996, pas avant)")
        fr_cpi = fetcher.get_resampled(FR_CPI_FALLBACK, "monthly")

    months = {}
    for _, r in history.iterrows():
        ts = pd.Timestamp(r["date"])
        ym = f"{ts:%Y-%m}"
        code = int(r["regime_code"])
        colors = COLOR_MAP.get(code, COLOR_MAP[8])
        months[ym] = {
            "regime_code":     code,
            "regime_name_fr":  r["regime_name_FR"],
            "regime_name_en":  r["regime_name_EN"],
            "growth_state":    r["growth_state"],
            "inflation_state": r["inflation_state"],
            "stress_overlay":  r["stress_overlay"],
            "color_zone_hex":  colors["zone"],
            "color_line_hex":  colors["line"],
            "color_label_hex": colors["label"],
            "cfnai_ma3":       _f(r.get("cfnai_ma3")),
            "pce_trimmed_12m": _f(r.get("pce_trimmed_12m")),
            "nfci":            _f(r.get("nfci")),
            "us": {
                "cpi_yoy":   _lookup_yoy(cpi_us, ts),
                "cpi_index": _lookup_at(cpi_us, ts),
                "fedfunds":  _lookup_at(ff, ts),
                "gs10":      _lookup_at(gs10, ts),
                "sp500":     _lookup_at(sp500, ts),
            },
            "fr": {
                "cpi_yoy":        _lookup_yoy(fr_cpi, ts),
                "cpi_index":      _lookup_at(fr_cpi, ts),
                "overnight_rate": _lookup_at(fr_overnight, ts),
                "oat10":          _lookup_at(fr_long, ts),
                "equity":         _lookup_at(fr_equity, ts),
            },
        }

    keys = sorted(months)
    if not keys:
        raise RuntimeError("regime_lookup: aucun mois classe")

    doc = {
        "schema": "eco3min.regime_lookup/1",
        "coverage": {
            "min_ym": keys[0],
            "max_ym": keys[-1],
            "calibration_from": CALIBRATION_FROM,
            "vintage": datetime.now(timezone.utc).date().isoformat(),
            "thresholds_version": THRESHOLDS_VERSION,
        },
        "months": months,
        "latest": {
            "us": {"cpi_index": _lookup_tail(cpi_us), "sp500": _lookup_tail(sp500)},
            "fr": {"cpi_index": _lookup_tail(fr_cpi), "equity": _lookup_tail(fr_equity)},
        },
    }

    # --- verifications bloquantes ----------------------------------------
    expected = pd.date_range(keys[0] + "-01", keys[-1] + "-01", freq="MS")
    missing = [f"{t:%Y-%m}" for t in expected if f"{t:%Y-%m}" not in months]
    assert not missing, f"trous dans l'historique: {missing[:12]}"

    for ym in keys:
        m = months[ym]
        assert m["cfnai_ma3"] is not None, f"{ym}: axe croissance absent"
        assert m["pce_trimmed_12m"] is not None, f"{ym}: axe inflation absent — garde-fou non applique"
        assert m["nfci"] is not None, f"{ym}: axe financier absent"

    # aucune couche structurelle ne doit fuiter dans une sortie datee
    forbidden = {"secular_stagnation", "financial_repression", "fiscal_dominance",
                 "dollar_shortage"}
    for ym in keys:
        vals = {str(v) for v in months[ym].values() if isinstance(v, str)}
        assert not (vals & forbidden), f"couche structurelle dans {ym} — interdit"

    path = Path(output_dir) / f"{REGIME_LOOKUP_ID}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
    log.info(f"  regime_lookup.json — {len(keys)} mois, {keys[0]} -> {keys[-1]}, "
             f"{path.stat().st_size / 1024:.0f} Ko")

    empties = [f"us.{k}" for k in ("cpi_index", "sp500") if doc["latest"]["us"][k] is None]
    empties += [f"fr.{k}" for k in ("cpi_index", "equity") if doc["latest"]["fr"][k] is None]
    if empties:
        log.warning(f"  champs servis en null (l'outil affichera «—») : {', '.join(empties)}")


if __name__ == "__main__":
    main()
