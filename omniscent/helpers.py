"""
Helper utilities for the Omniscent simulation engine.

Provides:
  - Trading-day calendar (US market holidays, weekday-only date lists)
  - Technical indicators (returns, SMA, EMA, volatility, RSI)
  - Date-range validation
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import List, Optional, Sequence, Union

import pandas as pd
import numpy as np


# ===================================================================== #
# Trading-day calendar
# ===================================================================== #

# Fixed-date US market holidays (month, day).
# Holidays that fall on weekends are observed on the nearest weekday –
# that adjustment is handled inside ``_is_market_holiday``.
_FIXED_HOLIDAYS = [
    (1, 1),   # New Year's Day
    (7, 4),   # Independence Day
    (12, 25), # Christmas Day
]


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """Return the *n*-th occurrence of *weekday* in *month*/*year*.

    *weekday*: 0 = Monday … 6 = Sunday.
    """
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    """Return the last occurrence of *weekday* in *month*/*year*."""
    last_day = date(year, month + 1, 1) - timedelta(days=1) if month < 12 \
        else date(year, 12, 31)
    offset = (last_day.weekday() - weekday) % 7
    return last_day - timedelta(days=offset)


def get_market_holidays(year: int) -> List[date]:
    """Return a list of US stock-market holidays for *year*.

    Covers: New Year, MLK Day, Presidents' Day, Good Friday,
    Memorial Day, Juneteenth, Independence Day, Labor Day,
    Thanksgiving, Christmas.
    """
    holidays: list[date] = []

    # --- Fixed holidays (with weekend → weekday adjustment) ---
    for m, d in _FIXED_HOLIDAYS:
        h = date(year, m, d)
        if h.weekday() == 5:       # Saturday → observe Friday
            h -= timedelta(days=1)
        elif h.weekday() == 6:     # Sunday → observe Monday
            h += timedelta(days=1)
        holidays.append(h)

    # --- Floating holidays ---
    holidays.append(_nth_weekday(year, 1, 0, 3))   # MLK Day: 3rd Mon Jan
    holidays.append(_nth_weekday(year, 2, 0, 3))   # Presidents: 3rd Mon Feb

    # Good Friday (2 days before Easter Sunday — basic algorithm)
    holidays.append(_good_friday(year))

    # Memorial Day: last Mon of May
    holidays.append(_last_weekday(year, 5, 0))

    # Juneteenth (since 2021)
    if year >= 2021:
        j = date(year, 6, 19)
        if j.weekday() == 5:
            j -= timedelta(days=1)
        elif j.weekday() == 6:
            j += timedelta(days=1)
        holidays.append(j)

    # Labor Day: 1st Mon of Sep
    holidays.append(_nth_weekday(year, 9, 0, 1))

    # Thanksgiving: 4th Thu of Nov
    holidays.append(_nth_weekday(year, 11, 3, 4))

    return sorted(holidays)


def _good_friday(year: int) -> date:
    """Compute Good Friday for *year* using the Anonymous Gregorian algorithm."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    easter = date(year, month, day)
    return easter - timedelta(days=2)


def generate_trading_days(
    start: Union[str, date, datetime],
    end: Union[str, date, datetime],
) -> List[date]:
    """Return an ordered list of US trading days between *start* and *end* (inclusive).

    Excludes weekends and market holidays.
    """
    if isinstance(start, str):
        start = datetime.strptime(start, "%Y-%m-%d").date()
    elif isinstance(start, datetime):
        start = start.date()

    if isinstance(end, str):
        end = datetime.strptime(end, "%Y-%m-%d").date()
    elif isinstance(end, datetime):
        end = end.date()

    # Collect holidays for all years in range
    holidays: set[date] = set()
    for yr in range(start.year, end.year + 1):
        holidays.update(get_market_holidays(yr))

    days: list[date] = []
    current = start
    while current <= end:
        if current.weekday() < 5 and current not in holidays:
            days.append(current)
        current += timedelta(days=1)
    return days


# ===================================================================== #
# Technical indicators
# ===================================================================== #

def compute_returns(
    df: pd.DataFrame,
    price_col: str = "close",
    periods: int = 1,
) -> pd.Series:
    """Compute percentage returns over *periods*.

    Returns a Series of the same length as *df* (first *periods* values
    are ``NaN``).
    """
    return df[price_col].pct_change(periods=periods)


def compute_moving_averages(
    df: pd.DataFrame,
    windows: Sequence[int] = (20, 50, 200),
    price_col: str = "close",
) -> pd.DataFrame:
    """Add simple-moving-average columns (``sma_<n>``) to *df*.

    Returns a **copy** to avoid mutating the original.
    """
    out = df.copy()
    for w in windows:
        out[f"sma_{w}"] = out[price_col].rolling(window=w).mean()
    return out


def compute_ema(
    df: pd.DataFrame,
    span: int = 20,
    price_col: str = "close",
) -> pd.Series:
    """Return an exponential moving average with the given *span*."""
    return df[price_col].ewm(span=span, adjust=False).mean()


def compute_volatility(
    df: pd.DataFrame,
    window: int = 20,
    price_col: str = "close",
) -> pd.Series:
    """Rolling annualised volatility (standard deviation of daily returns × sqrt(252))."""
    returns = df[price_col].pct_change()
    return returns.rolling(window=window).std() * np.sqrt(252)


def compute_rsi(
    df: pd.DataFrame,
    period: int = 14,
    price_col: str = "close",
) -> pd.Series:
    """Compute the Relative Strength Index (RSI).

    Uses the *smoothed* (Wilder) variant — identical to most trading
    platforms.

    Returns a Series in the range [0, 100].
    """
    delta = df[price_col].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


# ===================================================================== #
# Date-range validation
# ===================================================================== #

def date_range_validator(
    start: str,
    end: str,
    cutoff: str = "2025-06-30",
) -> bool:
    """Return ``True`` if *start* ≤ *end* ≤ *cutoff*.

    All arguments are ``YYYY-MM-DD`` strings.
    Raises ``ValueError`` with a descriptive message on failure.
    """
    s = datetime.strptime(start, "%Y-%m-%d")
    e = datetime.strptime(end, "%Y-%m-%d")
    c = datetime.strptime(cutoff, "%Y-%m-%d")

    if s > e:
        raise ValueError(f"start ({start}) is after end ({end})")
    if e > c:
        raise ValueError(f"end ({end}) exceeds cutoff ({cutoff})")
    return True
