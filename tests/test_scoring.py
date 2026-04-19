"""Tests for composite scoring and normalization."""

import numpy as np
import pandas as pd
import pytest

from src.scoring import composite_score, normalize_minmax, rank_stability


def test_normalize_minmax_bounds():
    s = pd.Series([1, 3, 5, 7, 9])
    out = normalize_minmax(s)
    assert out.min() == 0.0
    assert out.max() == 1.0


def test_normalize_minmax_constant_series():
    s = pd.Series([4, 4, 4])
    out = normalize_minmax(s)
    assert (out == 0.0).all()


def test_composite_score_weighted_sum():
    df = pd.DataFrame({"a": [0, 5, 10], "b": [10, 5, 0]})
    out = composite_score(df, {"a": 1.0, "b": 1.0})
    # After min-max each col becomes [0, .5, 1] and [1, .5, 0] -> sum/2 = .5 everywhere.
    assert out.round(3).tolist() == [0.5, 0.5, 0.5]


def test_composite_score_negative_weight_reverses_contribution():
    df = pd.DataFrame({"a": [0, 5, 10]})
    out = composite_score(df, {"a": -1.0})
    # Weighted sum / sum(|w|) = (-normalized(a))/1.
    assert out.round(3).tolist() == [0.0, -0.5, -1.0]


def test_rank_stability_returns_tau_in_bounds():
    rng = np.random.default_rng(42)
    df = pd.DataFrame({"a": rng.uniform(size=50), "b": rng.uniform(size=50)})
    schemes = {"balanced": {"a": 1, "b": 1}, "a_heavy": {"a": 3, "b": 1}}
    out = rank_stability(df, schemes)
    assert len(out) == 1
    tau = out.iloc[0]["kendall_tau"]
    assert -1 <= tau <= 1
    assert 0 < tau <= 1  # a_heavy is a perturbation of balanced -> positive correlation
