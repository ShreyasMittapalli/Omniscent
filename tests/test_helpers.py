"""
Unit tests for helper utilities.
"""

import sys
import os
import pytest
from datetime import date, datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import numpy as np
from omniscent.helpers import (
    generate_trading_days,
    get_market_holidays,
    compute_returns,
    compute_moving_averages,
    compute_ema,
    compute_volatility,
    compute_rsi,
    date_range_validator,
)


# ------------------------------------------------------------------ #
# Trading calendar
# ------------------------------------------------------------------ #

class TestTradingCalendar:
    def test_no_weekends(self):
        days = generate_trading_days("2024-01-01", "2024-01-31")
        for d in days:
            assert d.weekday() < 5, f"{d} is a weekend"

    def test_excludes_mlk_day(self):
        # MLK Day 2024: Jan 15
        days = generate_trading_days("2024-01-01", "2024-01-31")
        assert date(2024, 1, 15) not in days

    def test_excludes_christmas(self):
        days = generate_trading_days("2024-12-01", "2024-12-31")
        assert date(2024, 12, 25) not in days

    def test_inclusive_boundaries(self):
        days = generate_trading_days("2024-01-02", "2024-01-02")
        assert date(2024, 1, 2) in days

    def test_accepts_string_dates(self):
        days = generate_trading_days("2024-01-02", "2024-01-05")
        assert len(days) > 0

    def test_accepts_date_objects(self):
        days = generate_trading_days(date(2024, 1, 2), date(2024, 1, 5))
        assert len(days) > 0

    def test_holidays_count_2024(self):
        holidays = get_market_holidays(2024)
        # Expect ~10 holidays
        assert 9 <= len(holidays) <= 12

    def test_good_friday_2024(self):
        holidays = get_market_holidays(2024)
        # Good Friday 2024 = March 29
        assert date(2024, 3, 29) in holidays


# ------------------------------------------------------------------ #
# Returns
# ------------------------------------------------------------------ #

class TestReturns:
    def test_basic_returns(self):
        df = pd.DataFrame({"close": [100, 110, 105, 120]})
        ret = compute_returns(df)
        assert pd.isna(ret.iloc[0])
        assert abs(ret.iloc[1] - 0.10) < 0.001
        assert ret.iloc[2] < 0  # 110 -> 105

    def test_custom_period(self):
        df = pd.DataFrame({"close": [100, 110, 120, 130]})
        ret = compute_returns(df, periods=2)
        assert pd.isna(ret.iloc[0])
        assert pd.isna(ret.iloc[1])
        assert abs(ret.iloc[2] - 0.20) < 0.001


# ------------------------------------------------------------------ #
# Moving averages
# ------------------------------------------------------------------ #

class TestMovingAverages:
    def test_sma_columns_added(self):
        df = pd.DataFrame({"close": list(range(1, 201))})
        result = compute_moving_averages(df, windows=[5, 10])
        assert "sma_5" in result.columns
        assert "sma_10" in result.columns

    def test_does_not_mutate_original(self):
        df = pd.DataFrame({"close": list(range(1, 201))})
        _ = compute_moving_averages(df, windows=[5])
        assert "sma_5" not in df.columns

    def test_sma_correctness(self):
        df = pd.DataFrame({"close": [10, 20, 30, 40, 50]})
        result = compute_moving_averages(df, windows=[3])
        assert abs(result["sma_3"].iloc[2] - 20) < 0.001  # (10+20+30)/3
        assert abs(result["sma_3"].iloc[4] - 40) < 0.001  # (30+40+50)/3


class TestEMA:
    def test_ema_returns_series(self):
        df = pd.DataFrame({"close": list(range(1, 51))})
        ema = compute_ema(df, span=10)
        assert isinstance(ema, pd.Series)
        assert len(ema) == 50


# ------------------------------------------------------------------ #
# Volatility
# ------------------------------------------------------------------ #

class TestVolatility:
    def test_positive_for_volatile_data(self):
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(100))
        df = pd.DataFrame({"close": prices})
        vol = compute_volatility(df, window=20)
        # After warm-up, should be positive
        assert (vol.dropna() > 0).all()


# ------------------------------------------------------------------ #
# RSI
# ------------------------------------------------------------------ #

class TestRSI:
    def test_rsi_range(self):
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(200))
        df = pd.DataFrame({"close": prices})
        rsi = compute_rsi(df, period=14)
        valid = rsi.dropna()
        assert (valid >= 0).all()
        assert (valid <= 100).all()

    def test_rsi_high_after_rally(self):
        # Steadily rising prices should produce RSI >> 50
        df = pd.DataFrame({"close": list(range(100, 200))})
        rsi = compute_rsi(df, period=14)
        assert rsi.iloc[-1] > 80


# ------------------------------------------------------------------ #
# Date range validation
# ------------------------------------------------------------------ #

class TestDateRangeValidator:
    def test_valid_range(self):
        assert date_range_validator("2024-01-01", "2024-06-01") is True

    def test_start_after_end_raises(self):
        with pytest.raises(ValueError, match="start .* is after end"):
            date_range_validator("2024-06-01", "2024-01-01")

    def test_end_after_cutoff_raises(self):
        with pytest.raises(ValueError, match="exceeds cutoff"):
            date_range_validator("2024-01-01", "2025-12-01")

    def test_at_cutoff_boundary(self):
        assert date_range_validator("2025-01-01", "2025-06-30") is True
