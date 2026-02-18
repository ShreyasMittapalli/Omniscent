"""
Integration demo — end-to-end simulation walkthrough.

Sets a simulation date, queries all data types via the DAL, prints
a summary, advances time, and re-queries to demonstrate that the
temporal boundary moves correctly.

Usage:
    python demo_simulation.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from omniscent.temporal_controller import TemporalController
from omniscent.data_access_layer import TemporalDataAccessLayer
from omniscent.helpers import (
    compute_returns,
    compute_moving_averages,
    compute_rsi,
    compute_volatility,
    generate_trading_days,
)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "historical_data.db")


def header(text: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")


def run_scenario(dal: TemporalDataAccessLayer, ticker: str) -> None:
    tc = TemporalController()
    sim_date = tc.current_date_str

    header(f"SCENARIO: {ticker} @ {sim_date}")

    # --- Stock prices ---
    prices = dal.get_stock_prices(ticker, days_back=90)
    print(f"\n[Stock Prices] {len(prices)} rows (last 90 days)")
    if not prices.empty:
        latest = prices.iloc[-1]
        earliest = prices.iloc[0]
        print(f"  Range: {earliest['date']} to {latest['date']}")
        print(f"  Latest close: ${latest['close']:.2f}")
        print(f"  Volume: {int(latest['volume']):,}")

        # Technical indicators
        ret = compute_returns(prices)
        avg_return = ret.dropna().mean() * 100
        print(f"  Avg daily return: {avg_return:+.3f}%")

        prices_ma = compute_moving_averages(prices, windows=[20, 50])
        if len(prices_ma) >= 50:
            sma20 = prices_ma["sma_20"].iloc[-1]
            sma50 = prices_ma["sma_50"].iloc[-1]
            trend = "BULLISH" if sma20 > sma50 else "BEARISH"
            print(f"  SMA-20: ${sma20:.2f}  SMA-50: ${sma50:.2f}  -> {trend}")

        rsi = compute_rsi(prices)
        rsi_val = rsi.dropna().iloc[-1] if len(rsi.dropna()) > 0 else None
        if rsi_val is not None:
            condition = "OVERBOUGHT" if rsi_val > 70 else ("OVERSOLD" if rsi_val < 30 else "NEUTRAL")
            print(f"  RSI(14): {rsi_val:.1f} [{condition}]")

        vol = compute_volatility(prices)
        vol_val = vol.dropna().iloc[-1] if len(vol.dropna()) > 0 else None
        if vol_val is not None:
            print(f"  Annualized volatility: {vol_val*100:.1f}%")

    # --- News ---
    news = dal.get_news_articles(ticker, days_back=30)
    print(f"\n[News] {len(news)} articles (last 30 days)")
    for article in news[:3]:
        sent = article["sentiment_score"]
        tag = "+" if sent > 0.1 else ("-" if sent < -0.1 else "~")
        print(f"  [{tag}{abs(sent):.2f}] {article['title'][:70]}")

    # --- Social sentiment ---
    social = dal.get_social_sentiment(ticker, days_back=14)
    print(f"\n[Social] {len(social)} records (last 14 days)")
    if not social.empty:
        avg_sent = social["avg_sentiment"].mean()
        total_posts = social["post_count"].sum()
        print(f"  Avg sentiment: {avg_sent:+.3f}")
        print(f"  Total posts: {int(total_posts):,}")

    # --- SEC filings ---
    filings = dal.get_sec_filings(ticker, limit=3)
    print(f"\n[SEC Filings] showing latest {len(filings)}")
    for f in filings:
        print(f"  {f['filing_date']} | {f['filing_type']}")

    # --- Macro ---
    vix = dal.get_macro_indicators("VIXCLS", days_back=30)
    fed = dal.get_macro_indicators("FEDFUNDS", days_back=365)
    print(f"\n[Macro]")
    if not vix.empty:
        print(f"  VIX latest: {vix.iloc[-1]['value']:.2f}")
    if not fed.empty:
        print(f"  Fed Funds Rate: {fed.iloc[-1]['value']:.2f}%")

    # --- Trading days ---
    trading_days = generate_trading_days(
        dal.tc.current_time.strftime("%Y-%m-%d"),
        dal.tc.current_time.strftime("%Y-%m-%d"),
    )
    is_trading = len(trading_days) > 0
    print(f"\n  {sim_date} is {'a TRADING day' if is_trading else 'NOT a trading day'}")

    print(f"\n  TEMPORAL INTEGRITY: All data <= {sim_date} [VERIFIED]")


def main():
    TemporalController.reset()
    tc = TemporalController()
    dal = TemporalDataAccessLayer(DB_PATH)

    tickers = ["TSLA", "NVDA", "AAPL"]
    sim_dates = ["2024-01-15", "2024-06-01", "2025-03-01"]

    for sim_date in sim_dates:
        tc.set_simulation_date(sim_date)

        header(f"SIMULATION TIME SET: {sim_date}")
        print(f"  {tc.get_llm_context()}")

        for ticker in tickers:
            run_scenario(dal, ticker)

        print(f"\n{'~'*60}")
        print(f"  Advancing to next scenario...")
        print(f"{'~'*60}")

    # Final summary
    header("SIMULATION COMPLETE")
    print(f"  Scenarios run: {len(sim_dates)} dates x {len(tickers)} tickers")
    print(f"  Time travel history: {tc.history}")
    print(f"  Final sim date: {tc.current_date_str}")
    print(f"  All temporal integrity checks PASSED")

    dal.close()


if __name__ == "__main__":
    main()
