"""
Download historical stock data (OHLCV) for 50+ tickers using yfinance.
All data is strictly before July 1, 2025.
Saves one CSV per ticker in assets/stock_data/
"""

import os
import sys
import time
import yfinance as yf
import pandas as pd

# === CONFIG ===
START_DATE = "2020-01-01"
END_DATE = "2025-07-01"  # yfinance end is exclusive, so this gets data up to 2025-06-30
DATA_CUTOFF = pd.Timestamp("2025-06-30")  # Hard cutoff: nothing after this date

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "stock_data")

# 50+ tickers spanning tech, finance, healthcare, energy, consumer, industrial
TICKERS = [
    # Tech / Growth
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AMD", "INTC", "CRM",
    "ADBE", "NFLX", "PYPL", "SQ", "SHOP", "SNOW", "PLTR", "UBER", "ABNB", "COIN",
    # Finance
    "JPM", "BAC", "GS", "MS", "WFC", "V", "MA", "BRK-B", "C", "AXP",
    # Healthcare
    "JNJ", "UNH", "PFE", "MRNA", "ABBV", "LLY", "TMO", "MRK", "BMY", "GILD",
    # Energy
    "XOM", "CVX", "COP", "SLB", "OXY",
    # Consumer / Retail
    "WMT", "COST", "HD", "NKE", "SBUX", "MCD", "DIS",
    # Industrial / Other
    "BA", "CAT", "GE", "LMT", "UPS",
]


def download_ticker(ticker: str) -> pd.DataFrame | None:
    """Download OHLCV data for a single ticker."""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(start=START_DATE, end=END_DATE, auto_adjust=True)

        if df.empty:
            print(f"  ⚠ {ticker}: No data returned")
            return None

        # Reset index so Date is a column
        df = df.reset_index()

        # Ensure Date column is timezone-naive for consistent handling
        if hasattr(df["Date"].dtype, "tz") and df["Date"].dt.tz is not None:
            df["Date"] = df["Date"].dt.tz_localize(None)

        # HARD CUTOFF: remove any data on or after July 1, 2025
        df = df[df["Date"] <= DATA_CUTOFF]

        if df.empty:
            print(f"  ⚠ {ticker}: No data after cutoff filter")
            return None

        # Standardize column names
        df = df.rename(columns={
            "Date": "date",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        })

        # Keep only the columns we need
        df = df[["date", "open", "high", "low", "close", "volume"]]

        # Add ticker column
        df.insert(0, "ticker", ticker)

        # Round prices to 2 decimals
        for col in ["open", "high", "low", "close"]:
            df[col] = df[col].round(2)
        df["volume"] = df["volume"].astype(int)

        return df

    except Exception as e:
        print(f"  ✗ {ticker}: Error - {e}")
        return None


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 60)
    print("DOWNLOADING HISTORICAL STOCK DATA")
    print(f"Period: {START_DATE} to {DATA_CUTOFF.date()} (strict cutoff)")
    print(f"Tickers: {len(TICKERS)}")
    print("=" * 60)

    success_count = 0
    fail_count = 0
    total_rows = 0

    for i, ticker in enumerate(TICKERS, 1):
        print(f"\n[{i}/{len(TICKERS)}] Downloading {ticker}...")
        df = download_ticker(ticker)

        if df is not None and not df.empty:
            filepath = os.path.join(OUTPUT_DIR, f"{ticker}.csv")
            df.to_csv(filepath, index=False)
            row_count = len(df)
            total_rows += row_count
            date_range = f"{df['date'].min().date()} to {df['date'].max().date()}"
            print(f"  ✓ {ticker}: {row_count} rows, {date_range}")
            success_count += 1
        else:
            fail_count += 1

        # Be nice to Yahoo Finance servers
        time.sleep(0.5)

    print("\n" + "=" * 60)
    print("DOWNLOAD COMPLETE")
    print(f"  ✓ Success: {success_count}/{len(TICKERS)} tickers")
    if fail_count > 0:
        print(f"  ✗ Failed:  {fail_count}/{len(TICKERS)} tickers")
    print(f"  Total rows: {total_rows:,}")
    print(f"  Output dir: {os.path.abspath(OUTPUT_DIR)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
