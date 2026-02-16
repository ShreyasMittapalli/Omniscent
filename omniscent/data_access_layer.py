"""
Temporal Data Access Layer — every query auto-filters by simulation time.

All database reads pass through this layer.  The DAL obtains the current
simulation clock from ``TemporalController`` and appends a temporal-ceiling
predicate to every SQL statement, guaranteeing that **no future data can
leak** into the simulation.

Usage:
    from omniscent import TemporalController, TemporalDataAccessLayer

    tc = TemporalController()
    tc.set_simulation_date("2024-06-01")

    dal = TemporalDataAccessLayer("historical_data.db")
    prices = dal.get_stock_prices("TSLA")          # up to 2024-06-01
    news   = dal.get_news_articles("TSLA", 30)     # last 30 days
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from omniscent.temporal_controller import TemporalController


class TemporalDataAccessLayer:
    """
    All data queries go through this layer.
    Automatically filters out future data based on simulation time.
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row  # dict-like rows
        self.tc = TemporalController()       # singleton

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    def _sim_date_str(self) -> str:
        """Current simulation date as YYYY-MM-DD (convenience)."""
        return self.tc.current_date_str

    def _start_date_str(self, days_back: int) -> str:
        """Compute a start-date string *days_back* before the sim clock."""
        dt = self.tc.current_time - pd.Timedelta(days=days_back)
        return dt.strftime("%Y-%m-%d")

    @staticmethod
    def _assert_no_leak(df: pd.DataFrame, date_col: str,
                        sim_date: datetime) -> None:
        """Post-query assertion — raises if any row is after the sim clock."""
        if df.empty:
            return
        max_date = pd.to_datetime(df[date_col]).max()
        assert max_date <= sim_date, (
            f"FUTURE DATA LEAK DETECTED!  "
            f"max({date_col})={max_date.date()}, sim_date={sim_date.date()}"
        )

    # ------------------------------------------------------------------ #
    # Stock prices
    # ------------------------------------------------------------------ #

    def get_stock_prices(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        days_back: int = 365,
    ) -> pd.DataFrame:
        """Return OHLCV prices for *ticker* up to the simulation date.

        Parameters
        ----------
        ticker : str
            Stock symbol (e.g. ``"TSLA"``).
        start_date : str or None
            Explicit start date (``YYYY-MM-DD``).  Overrides *days_back*.
        days_back : int
            Number of calendar days to look back from the sim date.

        Returns
        -------
        pd.DataFrame
            Columns: ``date, open, high, low, close, volume``.
        """
        sim = self._sim_date_str()
        start = start_date or self._start_date_str(days_back)

        query = """
            SELECT date, open, high, low, close, volume
            FROM   stock_prices
            WHERE  ticker = ?
              AND  date >= ?
              AND  date <= ?
            ORDER BY date
        """

        df = pd.read_sql_query(query, self.conn, params=(ticker, start, sim))
        self._assert_no_leak(df, "date", self.tc.current_time)
        return df

    # ------------------------------------------------------------------ #
    # News articles
    # ------------------------------------------------------------------ #

    def get_news_articles(
        self,
        ticker: str,
        days_back: int = 30,
    ) -> List[Dict[str, Any]]:
        """Return news articles for *ticker* within the look-back window.

        Parameters
        ----------
        ticker : str
        days_back : int

        Returns
        -------
        list[dict]
            Keys: ``title, content, published_date, source, sentiment_score``.
        """
        sim = self._sim_date_str()
        start = self._start_date_str(days_back)

        query = """
            SELECT title, content, published_date, source, sentiment_score
            FROM   news_articles
            WHERE  ticker = ?
              AND  published_date >= ?
              AND  published_date <= ?
            ORDER BY published_date DESC
        """

        cursor = self.conn.cursor()
        cursor.execute(query, (ticker, start, sim))
        columns = [desc[0] for desc in cursor.description]
        articles = [dict(zip(columns, row)) for row in cursor.fetchall()]

        # Leak check via DataFrame proxy
        if articles:
            tmp = pd.DataFrame(articles)
            self._assert_no_leak(tmp, "published_date", self.tc.current_time)

        return articles

    # ------------------------------------------------------------------ #
    # Social sentiment
    # ------------------------------------------------------------------ #

    def get_social_sentiment(
        self,
        ticker: str,
        days_back: int = 7,
        platform: Optional[str] = None,
    ) -> pd.DataFrame:
        """Return social-media sentiment for *ticker*.

        Parameters
        ----------
        ticker : str
        days_back : int
        platform : str or None
            ``"reddit"`` or ``"twitter"``.  ``None`` returns both.

        Returns
        -------
        pd.DataFrame
            Columns: ``date, platform, avg_sentiment, post_count, engagement``.
        """
        sim = self._sim_date_str()
        start = self._start_date_str(days_back)

        query = """
            SELECT date, platform, avg_sentiment, post_count, engagement
            FROM   social_sentiment
            WHERE  ticker = ?
              AND  date >= ?
              AND  date <= ?
        """
        params: list[Any] = [ticker, start, sim]

        if platform:
            query += " AND platform = ?"
            params.append(platform)

        query += " ORDER BY date"

        df = pd.read_sql_query(query, self.conn, params=params)
        self._assert_no_leak(df, "date", self.tc.current_time)
        return df

    # ------------------------------------------------------------------ #
    # SEC filings
    # ------------------------------------------------------------------ #

    def get_sec_filings(
        self,
        ticker: str,
        filing_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Return SEC filings for *ticker* up to the simulation date.

        Parameters
        ----------
        ticker : str
        filing_type : str or None
            ``"10-K"``, ``"10-Q"``, or ``"8-K"``.  ``None`` = all types.
        limit : int
            Max filings returned (newest first).

        Returns
        -------
        list[dict]
            Keys: ``filing_type, filing_date, url, summary``.
        """
        sim = self._sim_date_str()

        query = """
            SELECT filing_type, filing_date, url, summary
            FROM   sec_filings
            WHERE  ticker = ?
              AND  filing_date <= ?
        """
        params: list[Any] = [ticker, sim]

        if filing_type:
            query += " AND filing_type = ?"
            params.append(filing_type)

        query += f" ORDER BY filing_date DESC LIMIT {limit}"

        cursor = self.conn.cursor()
        cursor.execute(query, params)
        columns = [desc[0] for desc in cursor.description]
        filings = [dict(zip(columns, row)) for row in cursor.fetchall()]

        if filings:
            tmp = pd.DataFrame(filings)
            self._assert_no_leak(tmp, "filing_date", self.tc.current_time)

        return filings

    # ------------------------------------------------------------------ #
    # Macro indicators
    # ------------------------------------------------------------------ #

    def get_macro_indicators(
        self,
        series_id: str,
        days_back: int = 365,
        start_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """Return FRED macro data for *series_id* up to the simulation date.

        Parameters
        ----------
        series_id : str
            FRED series code (e.g. ``"FEDFUNDS"``, ``"VIXCLS"``).
        days_back : int
        start_date : str or None

        Returns
        -------
        pd.DataFrame
            Columns: ``date, value, series_id, description``.
        """
        sim = self._sim_date_str()
        start = start_date or self._start_date_str(days_back)

        query = """
            SELECT date, value, series_id, description
            FROM   macro_indicators
            WHERE  series_id = ?
              AND  date >= ?
              AND  date <= ?
            ORDER BY date
        """

        df = pd.read_sql_query(query, self.conn, params=(series_id, start, sim))
        self._assert_no_leak(df, "date", self.tc.current_time)
        return df

    # ------------------------------------------------------------------ #
    # Combined snapshot
    # ------------------------------------------------------------------ #

    def get_market_snapshot(
        self,
        ticker: str,
        days_back_prices: int = 30,
        days_back_news: int = 7,
        days_back_social: int = 7,
    ) -> Dict[str, Any]:
        """Build a combined market snapshot for *ticker* at the sim date.

        Returns a dict with keys ``prices``, ``news``, ``social``,
        ``sec_filings``, ``macro`` (VIX + FEDFUNDS).
        """
        return {
            "ticker": ticker,
            "simulation_date": self._sim_date_str(),
            "prices": self.get_stock_prices(ticker, days_back=days_back_prices),
            "news": self.get_news_articles(ticker, days_back=days_back_news),
            "social": self.get_social_sentiment(ticker, days_back=days_back_social),
            "sec_filings": self.get_sec_filings(ticker),
            "macro": {
                "vix": self.get_macro_indicators("VIXCLS", days_back=days_back_prices),
                "fed_funds": self.get_macro_indicators("FEDFUNDS", days_back=days_back_prices),
            },
        }

    # ------------------------------------------------------------------ #
    # Available tickers
    # ------------------------------------------------------------------ #

    def get_available_tickers(self) -> List[str]:
        """Return a sorted list of all tickers in the stock_prices table."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT DISTINCT ticker FROM stock_prices ORDER BY ticker")
        return [row[0] for row in cursor.fetchall()]

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __repr__(self) -> str:
        return (
            f"TemporalDataAccessLayer(db='{self.db_path}', "
            f"sim_date={self._sim_date_str()})"
        )
