"""
Download key macroeconomic indicators from FRED (St. Louis Fed).
All data is strictly before July 1, 2025.
Requires FRED_API_KEY environment variable or pass as argument.

Usage:
    python download_macro_data.py
    python download_macro_data.py YOUR_API_KEY
"""

import os
import sys
import pandas as pd
from fredapi import Fred

# === CONFIG ===
START_DATE = "2020-01-01"
END_DATE = "2025-06-30"  # Strict cutoff: no data after this

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "macro_data")

# Key FRED series for financial risk analysis
FRED_SERIES = {
    "GDP":          {"id": "GDP",           "desc": "Gross Domestic Product (Quarterly)"},
    "CPIAUCSL":     {"id": "CPIAUCSL",      "desc": "Consumer Price Index (Monthly)"},
    "UNRATE":       {"id": "UNRATE",        "desc": "Unemployment Rate (Monthly)"},
    "FEDFUNDS":     {"id": "FEDFUNDS",      "desc": "Federal Funds Effective Rate (Monthly)"},
    "DGS10":        {"id": "DGS10",         "desc": "10-Year Treasury Yield (Daily)"},
    "SP500":        {"id": "SP500",         "desc": "S&P 500 Index (Daily)"},
    "VIXCLS":       {"id": "VIXCLS",        "desc": "CBOE Volatility Index VIX (Daily)"},
    "T10Y2Y":       {"id": "T10Y2Y",        "desc": "10Y-2Y Treasury Spread (Daily)"},
    "DTWEXBGS":     {"id": "DTWEXBGS",      "desc": "Trade Weighted US Dollar Index (Daily)"},
    "BAMLH0A0HYM2": {"id": "BAMLH0A0HYM2", "desc": "High Yield Corporate Bond Spread (Daily)"},
    "MORTGAGE30US":  {"id": "MORTGAGE30US",  "desc": "30-Year Fixed Mortgage Rate (Weekly)"},
    "UMCSENT":      {"id": "UMCSENT",       "desc": "U of Michigan Consumer Sentiment (Monthly)"},
}


def download_fred_data(api_key: str):
    """Download all FRED series and save as CSVs."""
    fred = Fred(api_key=api_key)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 60)
    print("DOWNLOADING FRED MACROECONOMIC DATA")
    print(f"Period: {START_DATE} to {END_DATE} (strict cutoff)")
    print(f"Series: {len(FRED_SERIES)}")
    print("=" * 60)

    all_data = []
    success_count = 0

    for name, info in FRED_SERIES.items():
        series_id = info["id"]
        desc = info["desc"]
        print(f"\n  Downloading {series_id} - {desc}...")

        try:
            series = fred.get_series(
                series_id,
                observation_start=START_DATE,
                observation_end=END_DATE
            )

            if series is None or series.empty:
                print(f"    ⚠ No data returned for {series_id}")
                continue

            # Convert to DataFrame
            df = series.reset_index()
            df.columns = ["date", "value"]

            # HARD CUTOFF: ensure no data after June 30, 2025
            df["date"] = pd.to_datetime(df["date"])
            df = df[df["date"] <= pd.Timestamp("2025-06-30")]

            # Drop NaN values
            df = df.dropna(subset=["value"])

            # Add metadata columns
            df.insert(0, "series_id", series_id)
            df["description"] = desc

            # Save individual CSV
            filepath = os.path.join(OUTPUT_DIR, f"{series_id}.csv")
            df.to_csv(filepath, index=False)
            print(f"    ✓ {len(df)} observations, {df['date'].min().date()} to {df['date'].max().date()}")

            all_data.append(df)
            success_count += 1

        except Exception as e:
            print(f"    ✗ Error: {e}")

    # Save combined file
    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        combined_path = os.path.join(OUTPUT_DIR, "_all_macro_data.csv")
        combined.to_csv(combined_path, index=False)
        print(f"\n  Combined file: {len(combined):,} total observations")

    print("\n" + "=" * 60)
    print(f"DOWNLOAD COMPLETE: {success_count}/{len(FRED_SERIES)} series")
    print(f"Output dir: {os.path.abspath(OUTPUT_DIR)}")
    print("=" * 60)


def main():
    # Get API key from argument or environment
    if len(sys.argv) > 1:
        api_key = sys.argv[1]
    else:
        api_key = os.environ.get("FRED_API_KEY")

    if not api_key:
        print("Error: FRED API key required.")
        print("Usage: python download_macro_data.py YOUR_API_KEY")
        print("   or: set FRED_API_KEY=YOUR_KEY then run script")
        sys.exit(1)

    download_fred_data(api_key)


if __name__ == "__main__":
    main()
