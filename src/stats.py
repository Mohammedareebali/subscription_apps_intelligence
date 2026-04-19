"""Statistical helpers used in the market landscape and ratings notebooks."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class WelchResult:
    t_stat: float
    p_value: float
    df: float
    mean_a: float
    mean_b: float
    mean_diff: float
    n_a: int
    n_b: int


def welch_test(a: pd.Series | np.ndarray, b: pd.Series | np.ndarray) -> WelchResult:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    a = a[~np.isnan(a)]
    b = b[~np.isnan(b)]
    t, p = stats.ttest_ind(a, b, equal_var=False)
    va, vb = a.var(ddof=1), b.var(ddof=1)
    na, nb = len(a), len(b)
    df = (va / na + vb / nb) ** 2 / (
        (va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1)
    )
    return WelchResult(
        t_stat=float(t),
        p_value=float(p),
        df=float(df),
        mean_a=float(a.mean()),
        mean_b=float(b.mean()),
        mean_diff=float(a.mean() - b.mean()),
        n_a=na,
        n_b=nb,
    )


def cohens_d(a: pd.Series | np.ndarray, b: pd.Series | np.ndarray) -> float:
    """Pooled-SD Cohen's d. Positive means group a > group b."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    a = a[~np.isnan(a)]
    b = b[~np.isnan(b)]
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return float("nan")
    pooled_sd = np.sqrt(((na - 1) * a.var(ddof=1) + (nb - 1) * b.var(ddof=1)) / (na + nb - 2))
    if pooled_sd == 0:
        return float("nan")
    return float((a.mean() - b.mean()) / pooled_sd)


def within_group_comparison(
    df: pd.DataFrame,
    group_col: str,
    outcome_col: str,
    treatment_col: str,
    min_n: int = 30,
) -> pd.DataFrame:
    """Run Welch + Cohen's d per group. Used for within-category free vs paid."""
    rows = []
    for group, sub in df.groupby(group_col):
        treated = sub.loc[sub[treatment_col] == 1, outcome_col].dropna()
        control = sub.loc[sub[treatment_col] == 0, outcome_col].dropna()
        if len(treated) < min_n or len(control) < min_n:
            continue
        r = welch_test(treated, control)
        rows.append(
            {
                group_col: group,
                "n_treated": r.n_a,
                "n_control": r.n_b,
                "mean_treated": r.mean_a,
                "mean_control": r.mean_b,
                "mean_diff": r.mean_diff,
                "t_stat": r.t_stat,
                "p_value": r.p_value,
                "cohens_d": cohens_d(treated, control),
            }
        )
    return pd.DataFrame(rows).sort_values("cohens_d", ascending=False)
