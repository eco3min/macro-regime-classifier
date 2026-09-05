#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
eco3min_common.py — Shared utilities for Eco3min data pipelines.

Imported by:
  - eco3min_updater.py (FRED datasets pipeline)
  - regime_classifier.py (macro regime classifier)

Contains:
  - FredFetcher (FRED API wrapper with cache)
  - align_series (multi-series alignment to DataFrame)
  - touch_wordpress (WP REST endpoint ping)
"""

import os
import logging
from typing import Dict

import pandas as pd
from fredapi import Fred
import requests

log = logging.getLogger("eco3min")


class FredFetcher:
    """
    FRED API wrapper with in-process cache.
    One instance per pipeline run — cache persists across series fetches.

    Usage:
        api_key = os.environ["FRED_API_KEY"]
        fetcher = FredFetcher(api_key)
        monthly = fetcher.get_resampled("CFNAI", "monthly")
        weekly  = fetcher.get_resampled("NFCI", "weekly")
    """

    def __init__(self, api_key: str):
        self.fred = Fred(api_key=api_key)
        self._cache: Dict[str, pd.Series] = {}

    def get_series(self, series_id: str, start: str = "1900-01-01") -> pd.Series:
        """
        Fetch a FRED series. Returns pd.Series with datetime index, float values.
        NaN values dropped. Cached after first fetch.
        """
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
        """
        Fetch and resample to the requested frequency.
        freq: "daily" | "weekly" (W-FRI) | "quarterly" (QS) | "monthly" (default, MS)
        """
        s = self.get_series(series_id)
        if freq == "daily":
            return s.sort_index()
        elif freq == "weekly":
            return s.resample("W-FRI").last().dropna()
        elif freq == "quarterly":
            return s.resample("QS").last().dropna()
        else:
            return s.resample("MS").last().dropna()


def align_series(series_dict: Dict[str, pd.Series], freq: str) -> pd.DataFrame:
    """
    Concatenate a dict of Series into a DataFrame aligned by index.
    Forward-fills daily data; drops rows with any NaN for other frequencies.
    """
    if not series_dict:
        return pd.DataFrame()
    df = pd.concat(series_dict, axis=1)
    if freq == "daily":
        df = df.ffill().dropna()
    else:
        df = df.dropna()
    df.index.name = "date"
    df = df.reset_index()
    return df


def touch_wordpress(touch_url: str, secret: str) -> None:
    """
    POST to the Eco3min WP REST touch endpoint to refresh dateModified on dataset pages.

    Endpoint accepts:  POST data={"key": secret}
    Returns JSON:      {"touched": N, "date": "..."}

    Args:
        touch_url: full URL, e.g. "https://eco3min.fr/wp-json/eco3min/v1/touch-datasets"
        secret:    value of WP_TOUCH_SECRET env var
    """
    if not touch_url or not secret:
        log.warning("touch_wordpress: missing touch_url or secret — skipping.")
        return
    log.info(f"Touching WordPress via {touch_url}")
    try:
        resp = requests.post(touch_url, data={"key": secret}, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        touched = result.get("touched", 0)
        log.info(f"  WordPress touch OK — {touched} pages updated at {result.get('date', '?')}")
    except requests.exceptions.RequestException as e:
        log.error(f"  WordPress touch FAILED: {e}")
    except Exception as e:
        log.error(f"  WordPress touch unexpected error: {e}")
