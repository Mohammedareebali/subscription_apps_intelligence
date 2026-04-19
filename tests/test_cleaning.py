"""Known-answer tests for the raw-CSV parsers."""

import math

import numpy as np
import pandas as pd
import pytest

from src.cleaning import (
    parse_installs,
    parse_price_usd,
    parse_size_mb,
    standardize_category,
    parse_last_updated,
)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("100,000+", 100_000.0),
        ("1,000,000+", 1_000_000.0),
        ("500+", 500.0),
        ("0", 0.0),
        ("Free", 0.0),
        ("", 0.0),
    ],
)
def test_parse_installs_known_values(raw, expected):
    assert parse_installs(raw) == expected


def test_parse_installs_nan_passthrough():
    assert math.isnan(parse_installs(np.nan))


@pytest.mark.parametrize(
    "raw, expected",
    [("19M", 19.0), ("8.7k", 8.7 / 1024.0), ("1.2G", 1228.8)],
)
def test_parse_size_mb_units(raw, expected):
    assert parse_size_mb(raw) == pytest.approx(expected)


def test_parse_size_mb_varies_is_nan():
    assert math.isnan(parse_size_mb("Varies with device"))


@pytest.mark.parametrize(
    "raw, expected",
    [("$4.99", 4.99), ("$0.99", 0.99), ("0", 0.0), ("Free", 0.0)],
)
def test_parse_price_usd_known(raw, expected):
    assert parse_price_usd(raw) == pytest.approx(expected)


def test_standardize_category_uppercase_underscore():
    assert standardize_category("auto & vehicles") == "AUTO_AND_VEHICLES"
    assert standardize_category("Health & Fitness") == "HEALTH_AND_FITNESS"
    assert standardize_category(np.nan) == ""


def test_parse_last_updated_valid_and_invalid():
    assert parse_last_updated("January 7, 2018") == pd.Timestamp("2018-01-07")
    assert pd.isna(parse_last_updated("not a date"))
