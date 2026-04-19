"""Feature engineering for the cleaned apps frame."""

from __future__ import annotations

import numpy as np
import pandas as pd


PRICE_BANDS = [
    ("Free", 0.0, 0.0),
    ("$0.01-0.99", 0.01, 0.99),
    ("$1.00-2.99", 1.00, 2.99),
    ("$3.00-4.99", 3.00, 4.99),
    ("$5.00-9.99", 5.00, 9.99),
    ("$10.00+", 10.00, float("inf")),
]


def assign_price_band(price: float) -> str:
    if pd.isna(price):
        return "Unknown"
    for label, lo, hi in PRICE_BANDS:
        if lo <= price <= hi:
            return label
    return "Unknown"


def add_features(
    df: pd.DataFrame, snapshot_date: pd.Timestamp | None = None
) -> pd.DataFrame:
    """Add derived columns used across notebooks.

    snapshot_date defaults to max(last_updated) so age_days is always >= 0.
    """
    out = df.copy()
    out["is_paid"] = (out["price_usd"] > 0).astype(int)
    out["price_band"] = out["price_usd"].map(assign_price_band)
    out["log_installs"] = np.log1p(out["installs"])
    out["log_size_mb"] = np.log1p(out["size_mb"])
    out["log_reviews"] = np.log1p(out["reviews"])

    if snapshot_date is None:
        snapshot_date = out["last_updated"].max()
    out["age_days"] = (snapshot_date - out["last_updated"]).dt.days
    out["reviews_per_install"] = out["reviews"] / out["installs"].replace(0, np.nan)
    return out
