"""Composite opportunity scoring + rank-stability sensitivity analysis."""

from __future__ import annotations

from typing import Mapping

import numpy as np
import pandas as pd
from scipy.stats import kendalltau


def normalize_minmax(series: pd.Series) -> pd.Series:
    """Scale to [0, 1]. Constant series -> all zeros."""
    s = series.astype(float)
    lo, hi = s.min(skipna=True), s.max(skipna=True)
    if pd.isna(lo) or pd.isna(hi) or hi == lo:
        return pd.Series(np.zeros(len(s)), index=s.index)
    return (s - lo) / (hi - lo)


def composite_score(
    df: pd.DataFrame, weights: Mapping[str, float], normalize: bool = True
) -> pd.Series:
    """Weighted sum of (optionally normalized) columns.

    Weights may be negative to indicate 'lower is better'.
    """
    parts = []
    for col, w in weights.items():
        col_series = df[col]
        if normalize:
            col_series = normalize_minmax(col_series)
        parts.append(col_series * w)
    total = sum(parts)
    weight_sum = sum(abs(w) for w in weights.values())
    if weight_sum == 0:
        return total
    return total / weight_sum


def rank_stability(
    df: pd.DataFrame,
    weight_sets: Mapping[str, Mapping[str, float]],
    top_k: int = 10,
) -> pd.DataFrame:
    """Score under multiple weight schemes; return pairwise Kendall τ between rankings."""
    rankings = {}
    for name, weights in weight_sets.items():
        scores = composite_score(df, weights)
        rankings[name] = scores.rank(ascending=False, method="min")
    names = list(rankings)
    rows = []
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            tau, _ = kendalltau(rankings[a], rankings[b])
            rows.append({"scheme_a": a, "scheme_b": b, "kendall_tau": tau})
    return pd.DataFrame(rows)
