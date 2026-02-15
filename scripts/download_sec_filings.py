"""
Download SEC EDGAR filing metadata for target companies.
Uses the free EDGAR full-text search API (EFTS) - no API key needed.
All data is strictly before July 1, 2025.
Saves filing metadata CSVs to assets/sec_filings/
"""

import os
import time
import json
import requests
import pandas as pd

# === CONFIG ===
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "sec_filings")
DATA_CUTOFF = "2025-06-30"

# SEC EDGAR requires a User-Agent header with contact info
HEADERS = {
    "User-Agent": "OmniscentMVP/1.0 (research@example.com)",
    "Accept": "application/json",
}

# Target companies - ticker to CIK mapping
# CIK numbers for our target stocks (you can look these up on SEC EDGAR)
COMPANY_CIKS = {
    "AAPL":  "0000320193",
    "MSFT":  "0000789019",
    "GOOGL": "0001652044",
    "AMZN":  "0001018724",
    "NVDA":  "0001045810",
    "META":  "0001326801",
    "TSLA":  "0001318605",
    "JPM":   "0000019617",
    "BAC":   "0000070858",
    "JNJ":   "0000200406",
    "UNH":   "0000731766",
    "XOM":   "0000034088",
    "WMT":   "0000104169",
    "DIS":   "0001744489",
    "BA":    "0000012927",
    "GS":    "0000886982",
    "PFE":   "0000078003",
    "AMD":   "0000002488",
    "NFLX":  "0001065280",
    "CRM":   "0001108524",
}

FILING_TYPES = ["10-K", "10-Q", "8-K"]


def fetch_filings(cik: str, ticker: str, filing_type: str) -> list:
    """Fetch filing metadata from SEC EDGAR submissions API."""
    # Use the submissions endpoint
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        filings = []
        recent = data.get("filings", {}).get("recent", {})

        if not recent:
            return filings

        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        accessions = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])

        for i in range(len(forms)):
            form = forms[i]
            filing_date = dates[i]

            # Filter by filing type and date
            if form != filing_type:
                continue
            if filing_date > DATA_CUTOFF:
                continue
            if filing_date < "2020-01-01":
                continue

            accession = accessions[i].replace("-", "")
            doc = primary_docs[i] if i < len(primary_docs) else ""
            filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{accession}/{doc}"

            filings.append({
                "ticker": ticker,
                "filing_type": form,
                "filing_date": filing_date,
                "accession_number": accessions[i],
                "url": filing_url,
                "summary": f"{ticker} {form} filed on {filing_date}",
            })

        return filings

    except Exception as e:
        print(f"    ✗ Error fetching {ticker} {filing_type}: {e}")
        return []


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 60)
    print("DOWNLOADING SEC EDGAR FILING METADATA")
    print(f"Period: 2020-01-01 to {DATA_CUTOFF} (strict cutoff)")
    print(f"Companies: {len(COMPANY_CIKS)}")
    print(f"Filing types: {FILING_TYPES}")
    print("=" * 60)

    all_filings = []

    for ticker, cik in COMPANY_CIKS.items():
        print(f"\n  {ticker} (CIK: {cik}):")

        for filing_type in FILING_TYPES:
            filings = fetch_filings(cik, ticker, filing_type)
            all_filings.extend(filings)
            print(f"    {filing_type}: {len(filings)} filings")

        # Respect SEC rate limit (10 req/sec)
        time.sleep(0.5)

    if all_filings:
        df = pd.DataFrame(all_filings)

        # HARD CUTOFF validation
        df["filing_date"] = pd.to_datetime(df["filing_date"])
        df = df[df["filing_date"] <= pd.Timestamp(DATA_CUTOFF)]

        # Sort by date
        df = df.sort_values(["ticker", "filing_date"]).reset_index(drop=True)

        # Save combined file
        combined_path = os.path.join(OUTPUT_DIR, "all_sec_filings.csv")
        df.to_csv(combined_path, index=False)

        # Also save per-ticker files
        for ticker in df["ticker"].unique():
            ticker_df = df[df["ticker"] == ticker]
            ticker_path = os.path.join(OUTPUT_DIR, f"{ticker}_filings.csv")
            ticker_df.to_csv(ticker_path, index=False)

        print("\n" + "=" * 60)
        print(f"DOWNLOAD COMPLETE: {len(df)} total filings")
        print(f"  Date range: {df['filing_date'].min().date()} to {df['filing_date'].max().date()}")
        for ft in FILING_TYPES:
            count = len(df[df["filing_type"] == ft])
            print(f"  {ft}: {count} filings")
        print(f"  Output dir: {os.path.abspath(OUTPUT_DIR)}")
        print("=" * 60)
    else:
        print("\n  ⚠ No filings downloaded")


if __name__ == "__main__":
    main()
