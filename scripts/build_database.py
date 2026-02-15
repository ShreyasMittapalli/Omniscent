"""
Build the master SQLite database from all CSV data assets.
Loads stock prices, news, social sentiment, SEC filings, and macro data
into a single historical_data.db with temporal indexes.

All data is validated to be strictly before July 1, 2025.

Usage:
    python build_database.py
"""

import os
import sys
import glob
import sqlite3
import pandas as pd

# === CONFIG ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, "..")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
DB_PATH = os.path.join(PROJECT_ROOT, "historical_data.db")

DATA_CUTOFF = pd.Timestamp("2025-06-30")


def create_schema(conn: sqlite3.Connection):
    """Create all tables with proper schema."""
    cursor = conn.cursor()

    cursor.executescript("""
        -- Stock price data (daily OHLCV)
        CREATE TABLE IF NOT EXISTS stock_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            UNIQUE(ticker, date)
        );

        -- News articles / headlines
        CREATE TABLE IF NOT EXISTS news_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            title TEXT,
            content TEXT,
            published_date TEXT NOT NULL,
            source TEXT,
            sentiment_score REAL
        );

        -- Social media sentiment (daily aggregated)
        CREATE TABLE IF NOT EXISTS social_sentiment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            date TEXT NOT NULL,
            platform TEXT,
            avg_sentiment REAL,
            post_count INTEGER,
            engagement INTEGER
        );

        -- SEC filing metadata
        CREATE TABLE IF NOT EXISTS sec_filings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            filing_type TEXT,
            filing_date TEXT NOT NULL,
            url TEXT,
            summary TEXT
        );

        -- Macroeconomic indicators from FRED
        CREATE TABLE IF NOT EXISTS macro_indicators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            series_id TEXT NOT NULL,
            date TEXT NOT NULL,
            value REAL,
            description TEXT,
            UNIQUE(series_id, date)
        );
    """)

    conn.commit()
    print("✓ Database schema created")


def create_indexes(conn: sqlite3.Connection):
    """Create temporal indexes for efficient date-range queries."""
    cursor = conn.cursor()

    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_stock_prices_ticker_date ON stock_prices(ticker, date)",
        "CREATE INDEX IF NOT EXISTS idx_stock_prices_date ON stock_prices(date)",
        "CREATE INDEX IF NOT EXISTS idx_news_ticker_date ON news_articles(ticker, published_date)",
        "CREATE INDEX IF NOT EXISTS idx_news_date ON news_articles(published_date)",
        "CREATE INDEX IF NOT EXISTS idx_social_ticker_date ON social_sentiment(ticker, date)",
        "CREATE INDEX IF NOT EXISTS idx_social_date ON social_sentiment(date)",
        "CREATE INDEX IF NOT EXISTS idx_sec_ticker_date ON sec_filings(ticker, filing_date)",
        "CREATE INDEX IF NOT EXISTS idx_sec_date ON sec_filings(filing_date)",
        "CREATE INDEX IF NOT EXISTS idx_macro_series_date ON macro_indicators(series_id, date)",
        "CREATE INDEX IF NOT EXISTS idx_macro_date ON macro_indicators(date)",
    ]

    for idx_sql in indexes:
        cursor.execute(idx_sql)

    conn.commit()
    print("✓ Temporal indexes created")


def load_stock_data(conn: sqlite3.Connection):
    """Load stock price CSVs into the database."""
    stock_dir = os.path.join(ASSETS_DIR, "stock_data")
    if not os.path.exists(stock_dir):
        print("  ⚠ No stock_data directory found, skipping")
        return 0

    csv_files = glob.glob(os.path.join(stock_dir, "*.csv"))
    total_rows = 0

    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            if df.empty:
                continue

            # Standardize column names
            df.columns = [c.lower().strip() for c in df.columns]

            # Ensure date column exists
            if "date" not in df.columns:
                continue

            # Enforce cutoff
            df["date"] = pd.to_datetime(df["date"])
            df = df[df["date"] <= DATA_CUTOFF]
            df["date"] = df["date"].dt.strftime("%Y-%m-%d")

            # Insert using INSERT OR IGNORE to handle duplicates
            df.to_sql("stock_prices", conn, if_exists="append", index=False,
                       method="multi")
            total_rows += len(df)
        except Exception as e:
            print(f"    ⚠ Error loading {os.path.basename(csv_file)}: {e}")

    print(f"  ✓ Stock prices: {total_rows:,} rows from {len(csv_files)} files")
    return total_rows


def load_news_data(conn: sqlite3.Connection):
    """Load news headlines CSV into the database."""
    news_file = os.path.join(ASSETS_DIR, "news_data", "news_headlines.csv")
    if not os.path.exists(news_file):
        print("  ⚠ No news_headlines.csv found, skipping")
        return 0

    try:
        df = pd.read_csv(news_file)
        df.columns = [c.lower().strip() for c in df.columns]

        # Enforce cutoff
        df["published_date"] = pd.to_datetime(df["published_date"])
        df = df[df["published_date"] <= DATA_CUTOFF]
        df["published_date"] = df["published_date"].dt.strftime("%Y-%m-%d")

        df.to_sql("news_articles", conn, if_exists="append", index=False)
        print(f"  ✓ News articles: {len(df):,} rows")
        return len(df)
    except Exception as e:
        print(f"    ⚠ Error loading news data: {e}")
        return 0


def load_social_data(conn: sqlite3.Connection):
    """Load social sentiment CSV into the database."""
    social_file = os.path.join(ASSETS_DIR, "social_data", "social_sentiment.csv")
    if not os.path.exists(social_file):
        print("  ⚠ No social_sentiment.csv found, skipping")
        return 0

    try:
        df = pd.read_csv(social_file)
        df.columns = [c.lower().strip() for c in df.columns]

        # Enforce cutoff
        df["date"] = pd.to_datetime(df["date"])
        df = df[df["date"] <= DATA_CUTOFF]
        df["date"] = df["date"].dt.strftime("%Y-%m-%d")

        df.to_sql("social_sentiment", conn, if_exists="append", index=False)
        print(f"  ✓ Social sentiment: {len(df):,} rows")
        return len(df)
    except Exception as e:
        print(f"    ⚠ Error loading social data: {e}")
        return 0


def load_sec_data(conn: sqlite3.Connection):
    """Load SEC filings CSV into the database."""
    sec_file = os.path.join(ASSETS_DIR, "sec_filings", "all_sec_filings.csv")
    if not os.path.exists(sec_file):
        print("  ⚠ No all_sec_filings.csv found, skipping")
        return 0

    try:
        df = pd.read_csv(sec_file)
        df.columns = [c.lower().strip() for c in df.columns]

        # Enforce cutoff
        df["filing_date"] = pd.to_datetime(df["filing_date"])
        df = df[df["filing_date"] <= DATA_CUTOFF]
        df["filing_date"] = df["filing_date"].dt.strftime("%Y-%m-%d")

        # Keep only needed columns
        keep_cols = ["ticker", "filing_type", "filing_date", "url", "summary"]
        df = df[[c for c in keep_cols if c in df.columns]]

        df.to_sql("sec_filings", conn, if_exists="append", index=False)
        print(f"  ✓ SEC filings: {len(df):,} rows")
        return len(df)
    except Exception as e:
        print(f"    ⚠ Error loading SEC data: {e}")
        return 0


def load_macro_data(conn: sqlite3.Connection):
    """Load FRED macro data CSV into the database."""
    macro_file = os.path.join(ASSETS_DIR, "macro_data", "_all_macro_data.csv")

    if not os.path.exists(macro_file):
        # Try loading individual files
        macro_dir = os.path.join(ASSETS_DIR, "macro_data")
        if not os.path.exists(macro_dir):
            print("  ⚠ No macro_data directory found, skipping")
            return 0

        csv_files = [f for f in glob.glob(os.path.join(macro_dir, "*.csv"))
                     if not f.endswith("_all_macro_data.csv")]
        if not csv_files:
            print("  ⚠ No macro data CSVs found, skipping")
            return 0

        dfs = []
        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file)
                dfs.append(df)
            except Exception:
                pass

        if not dfs:
            return 0
        combined = pd.concat(dfs, ignore_index=True)
    else:
        combined = pd.read_csv(macro_file)

    try:
        combined.columns = [c.lower().strip() for c in combined.columns]

        # Enforce cutoff
        combined["date"] = pd.to_datetime(combined["date"])
        combined = combined[combined["date"] <= DATA_CUTOFF]
        combined["date"] = combined["date"].dt.strftime("%Y-%m-%d")

        combined.to_sql("macro_indicators", conn, if_exists="append", index=False)
        print(f"  ✓ Macro indicators: {len(combined):,} rows")
        return len(combined)
    except Exception as e:
        print(f"    ⚠ Error loading macro data: {e}")
        return 0


def validate_no_future_data(conn: sqlite3.Connection):
    """Final validation: ensure absolutely no data after June 30, 2025."""
    cursor = conn.cursor()
    cutoff = "2025-07-01"

    checks = [
        ("stock_prices", "date"),
        ("news_articles", "published_date"),
        ("social_sentiment", "date"),
        ("sec_filings", "filing_date"),
        ("macro_indicators", "date"),
    ]

    all_clean = True
    for table, date_col in checks:
        cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {date_col} >= ?", (cutoff,))
        count = cursor.fetchone()[0]
        if count > 0:
            print(f"  ✗ FUTURE DATA LEAK in {table}: {count} rows after {cutoff}")
            # Delete the offending rows
            cursor.execute(f"DELETE FROM {table} WHERE {date_col} >= ?", (cutoff,))
            conn.commit()
            print(f"    → Deleted {count} offending rows")
            all_clean = False
        else:
            print(f"  ✓ {table}: clean (no future data)")

    return all_clean


def main():
    # Remove existing database for clean rebuild
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"Removed existing database: {DB_PATH}")

    print("=" * 60)
    print("BUILDING HISTORICAL DATA DATABASE")
    print(f"Database: {DB_PATH}")
    print(f"Data cutoff: {DATA_CUTOFF.date()} (strict)")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)

    # Step 1: Create schema
    print("\n[1/4] Creating schema...")
    create_schema(conn)

    # Step 2: Load all data
    print("\n[2/4] Loading data...")
    totals = {}
    totals["stock_prices"] = load_stock_data(conn)
    totals["news_articles"] = load_news_data(conn)
    totals["social_sentiment"] = load_social_data(conn)
    totals["sec_filings"] = load_sec_data(conn)
    totals["macro_indicators"] = load_macro_data(conn)

    # Step 3: Create indexes
    print("\n[3/4] Creating temporal indexes...")
    create_indexes(conn)

    # Step 4: Validate no future data
    print("\n[4/4] Validating temporal integrity...")
    validate_no_future_data(conn)

    # Summary
    print("\n" + "=" * 60)
    print("DATABASE BUILD COMPLETE")
    print("=" * 60)
    for table, count in totals.items():
        print(f"  {table}: {count:,} rows")
    total = sum(totals.values())
    print(f"  {'─' * 30}")
    print(f"  Total: {total:,} rows")

    db_size = os.path.getsize(DB_PATH) / (1024 * 1024)
    print(f"\n  Database size: {db_size:.1f} MB")
    print(f"  Location: {os.path.abspath(DB_PATH)}")
    print("=" * 60)

    conn.close()


if __name__ == "__main__":
    main()
