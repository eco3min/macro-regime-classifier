# -*- coding: utf-8 -*-
"""
eco3min_series.py — transformations de séries partagées par tous les pipelines (pandas seul,
aucune dépendance FRED : importable par fr_updater, ecb_updater, eia_updater).

pct_change_by_date : variation en % contre l'observation datée exactement `periods` plus tôt.

Pourquoi pas `Series.pct_change(periods)` : il décale de N LIGNES, pas de N périodes. Dès qu'une
observation manque dans la série (CPIAUCSL et CPILFESL : octobre 2025 jamais publié par le BLS,
shutdown fédéral ; `get_resampled` retire la ligne vide), toutes les variations postérieures sont
calculées sur 13 mois au lieu de 12. Constaté le 18/09/2026 : us-cpi-inflation publiait 3,71 % pour
août 2026 au lieu de 3,35 %, et les composites *_YOY sur CPIAUCSL avec lui. Règle : tout calcul
glissant se fait sur l'axe des dates ; une base absente donne NaN, jamais une valeur inventée.
"""
import pandas as pd

_OFFSETS = {
    "monthly": lambda n: pd.DateOffset(months=n),
    "quarterly": lambda n: pd.DateOffset(months=3 * n),
    "weekly": lambda n: pd.DateOffset(weeks=n),
    "annual": lambda n: pd.DateOffset(years=n),
}


def pct_change_by_date(s: pd.Series, periods: int, freq: str = "monthly") -> pd.Series:
    """Variation en % de `s` contre sa valeur `periods` périodes plus tôt, alignée par DATE.

    - `freq` ∈ monthly (index MS), quarterly (QS), weekly (W-FRI), annual ; `daily` garde la
      position (jours ouvrés, pas de calendrier fixe : la série est dense par construction).
    - Une observation absente à la date de base -> NaN sur cette ligne, la ligne n'est pas décalée.
    - Index dupliqués et NaN de `s` sont ignorés ; l'index doit être un DatetimeIndex.
    """
    if freq == "daily":
        return s.pct_change(periods=periods) * 100
    if freq not in _OFFSETS:
        raise ValueError(f"freq inconnue : {freq!r} (monthly, quarterly, weekly, annual, daily)")
    s = s.dropna().sort_index()
    s = s[~s.index.duplicated(keep="last")]
    base = s.copy()
    base.index = base.index + _OFFSETS[freq](periods)
    base = base[~base.index.duplicated(keep="last")].reindex(s.index)
    return (s / base - 1.0) * 100.0
