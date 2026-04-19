"""Parsers for the Google Play Store dataset's string-encoded columns."""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

_INSTALLS_RE = re.compile(r"[,+]")
_PRICE_RE = re.compile(r"[^0-9.]")


def parse_installs(value) -> float:
    """Parse Installs like '100,000+' -> 100000.0. Non-numeric -> NaN."""
    if pd.isna(value):
        return np.nan
    s = str(value).strip()
    if s in {"Free", "0", ""}:
        return 0.0
    cleaned = _INSTALLS_RE.sub("", s)
    try:
        return float(cleaned)
    except ValueError:
        return np.nan


def parse_size_mb(value) -> float:
    """Parse Size like '19M', '8.7k', 'Varies with device' -> MB as float."""
    if pd.isna(value):
        return np.nan
    s = str(value).strip()
    if s in {"", "Varies with device"}:
        return np.nan
    suffix = s[-1].lower()
    body = s[:-1]
    try:
        num = float(body)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return np.nan
    if suffix == "m":
        return num
    if suffix == "k":
        return num / 1024.0
    if suffix == "g":
        return num * 1024.0
    return np.nan


def parse_price_usd(value) -> float:
    """Parse Price like '$4.99', '0', 'Everyone' -> USD float. Invalid -> NaN."""
    if pd.isna(value):
        return np.nan
    s = str(value).strip()
    if s in {"0", "Free", ""}:
        return 0.0
    cleaned = _PRICE_RE.sub("", s)
    if cleaned == "":
        return np.nan
    try:
        return float(cleaned)
    except ValueError:
        return np.nan


def parse_last_updated(value) -> pd.Timestamp:
    """Parse 'January 7, 2018' -> pd.Timestamp. Invalid -> NaT."""
    return pd.to_datetime(value, errors="coerce", format="mixed")


def standardize_category(value) -> str:
    """Uppercase, underscore-separate, strip whitespace."""
    if pd.isna(value):
        return ""
    return str(value).strip().upper().replace(" ", "_").replace("&", "AND")


def clean_apps_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Apply all column parsers and drop known bad rows.

    Google Play's raw CSV has one notorious malformed row (shifted columns).
    We detect it by checking that Rating is parseable as numeric in [0, 5].
    """
    out = df.copy()
    out.columns = [c.strip() for c in out.columns]

    out["Rating"] = pd.to_numeric(out["Rating"], errors="coerce")
    out = out[out["Rating"].between(0, 5) | out["Rating"].isna()].copy()

    out["installs"] = out["Installs"].map(parse_installs)
    out["size_mb"] = out["Size"].map(parse_size_mb)
    out["price_usd"] = out["Price"].map(parse_price_usd)
    out["last_updated"] = parse_last_updated(out["Last Updated"])
    out["category"] = out["Category"].map(standardize_category)

    out["reviews"] = pd.to_numeric(out["Reviews"], errors="coerce")

    out = out.drop_duplicates(subset=["App"], keep="first").reset_index(drop=True)
    return out
