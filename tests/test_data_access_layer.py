"""
Unit tests for TemporalDataAccessLayer.

These tests use the real historical_data.db — ensuring that the DAL
correctly filters data by the simulation clock.
"""

import sys
import os
import pytest
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
from omniscent.temporal_controller import TemporalController
from omniscent.data_access_layer import TemporalDataAccessLayer

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "historical_data.db")


@pytest.fixture(autouse=True)
def fresh_controller():
    TemporalController.reset()
    yield
    TemporalController.reset()


@pytest.fixture
def dal():
    tc = TemporalController()
    tc.set_simulation_date("2024-06-01")
    dal = TemporalDataAccessLayer(DB_PATH)
    yield dal
    dal.close()


# ------------------------------------------------------------------ #
# Stock prices — no future data leak
# ------------------------------------------------------------------ #

class TestStockPrices:
    def test_returns_dataframe(self, dal):
        df = dal.get_stock_prices("AAPL")
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert list(df.columns) == ["date", "open", "high", "low", "close", "volume"]

    def test_no_future_data(self, dal):
        df = dal.get_stock_prices("AAPL")
        max_date = pd.to_datetime(df["date"]).max()
        assert max_date <= datetime(2024, 6, 1)

    def test_respects_days_back(self, dal):
        df = dal.get_stock_prices("AAPL", days_back=30)
        min_date = pd.to_datetime(df["date"]).min()
        # Should be roughly >= 2024-05-01 (some slack for weekends)
        assert min_date >= datetime(2024, 4, 25)

    def test_explicit_start_date(self, dal):
        df = dal.get_stock_prices("AAPL", start_date="2024-01-01")
        min_date = pd.to_datetime(df["date"]).min()
        assert min_date >= datetime(2024, 1, 1)

    def test_changing_sim_date_changes_results(self):
        tc = TemporalController()

        tc.set_simulation_date("2024-03-01")
        dal = TemporalDataAccessLayer(DB_PATH)
        df_march = dal.get_stock_prices("AAPL", days_back=365)
        max_march = pd.to_datetime(df_march["date"]).max()

        tc.set_simulation_date("2024-06-01")
        df_june = dal.get_stock_prices("AAPL", days_back=365)
        max_june = pd.to_datetime(df_june["date"]).max()

        # Core invariant: each query's max date respects the sim boundary
        assert max_march <= datetime(2024, 3, 1)
        assert max_june <= datetime(2024, 6, 1)
        # The June window reaches further into the future than March
        assert max_june > max_march
        dal.close()


# ------------------------------------------------------------------ #
# News articles
# ------------------------------------------------------------------ #

class TestNewsArticles:
    def test_returns_list(self, dal):
        articles = dal.get_news_articles("TSLA", days_back=365)
        assert isinstance(articles, list)

    def test_no_future_data(self, dal):
        articles = dal.get_news_articles("AAPL", days_back=365 * 5)
        if articles:
            max_date = max(a["published_date"] for a in articles)
            assert max_date <= "2024-06-01"

    def test_article_keys(self, dal):
        articles = dal.get_news_articles("TSLA", days_back=365)
        if articles:
            expected = {"title", "content", "published_date", "source", "sentiment_score"}
            assert set(articles[0].keys()) == expected


# ------------------------------------------------------------------ #
# Social sentiment
# ------------------------------------------------------------------ #

class TestSocialSentiment:
    def test_returns_dataframe(self, dal):
        df = dal.get_social_sentiment("TSLA", days_back=30)
        assert isinstance(df, pd.DataFrame)

    def test_no_future_data(self, dal):
        df = dal.get_social_sentiment("TSLA", days_back=365)
        if not df.empty:
            max_date = pd.to_datetime(df["date"]).max()
            assert max_date <= datetime(2024, 6, 1)

    def test_platform_filter(self, dal):
        df = dal.get_social_sentiment("TSLA", days_back=365, platform="reddit")
        if not df.empty:
            assert (df["platform"] == "reddit").all()


# ------------------------------------------------------------------ #
# SEC filings
# ------------------------------------------------------------------ #

class TestSECFilings:
    def test_returns_list(self, dal):
        filings = dal.get_sec_filings("AAPL")
        assert isinstance(filings, list)

    def test_no_future_data(self, dal):
        filings = dal.get_sec_filings("AAPL")
        if filings:
            max_date = max(f["filing_date"] for f in filings)
            assert max_date <= "2024-06-01"

    def test_filing_type_filter(self, dal):
        filings = dal.get_sec_filings("AAPL", filing_type="10-K")
        for f in filings:
            assert f["filing_type"] == "10-K"


# ------------------------------------------------------------------ #
# Macro indicators
# ------------------------------------------------------------------ #

class TestMacroIndicators:
    def test_returns_dataframe(self, dal):
        df = dal.get_macro_indicators("FEDFUNDS", days_back=365)
        assert isinstance(df, pd.DataFrame)

    def test_no_future_data(self, dal):
        df = dal.get_macro_indicators("VIXCLS", days_back=365 * 5)
        if not df.empty:
            max_date = pd.to_datetime(df["date"]).max()
            assert max_date <= datetime(2024, 6, 1)


# ------------------------------------------------------------------ #
# Market snapshot (combined)
# ------------------------------------------------------------------ #

class TestMarketSnapshot:
    def test_snapshot_keys(self, dal):
        snap = dal.get_market_snapshot("AAPL")
        assert "ticker" in snap
        assert "simulation_date" in snap
        assert "prices" in snap
        assert "news" in snap
        assert "social" in snap
        assert "sec_filings" in snap
        assert "macro" in snap

    def test_snapshot_date(self, dal):
        snap = dal.get_market_snapshot("AAPL")
        assert snap["simulation_date"] == "2024-06-01"


# ------------------------------------------------------------------ #
# Edge cases
# ------------------------------------------------------------------ #

class TestEdgeCases:
    def test_very_early_sim_date(self):
        tc = TemporalController()
        tc.set_simulation_date("2020-01-03")  # very early
        dal = TemporalDataAccessLayer(DB_PATH)
        df = dal.get_stock_prices("AAPL", days_back=30)
        if not df.empty:
            max_date = pd.to_datetime(df["date"]).max()
            assert max_date <= datetime(2020, 1, 3)
        dal.close()

    def test_unknown_ticker_returns_empty(self, dal):
        df = dal.get_stock_prices("ZZZZZ")
        assert df.empty

    def test_available_tickers(self, dal):
        tickers = dal.get_available_tickers()
        assert isinstance(tickers, list)
        assert "AAPL" in tickers
        assert "TSLA" in tickers
        assert len(tickers) >= 50
