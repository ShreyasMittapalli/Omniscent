"""
Verify the integrity of the historical_data.db database.
Checks row counts, date ranges, and runs sample temporal queries.

Usage:
    python verify_data.py
"""

import os
import sys
import sqlite3
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "..", "historical_data.db")
DATA_CUTOFF = "2025-06-30"


def verify_database():
    if not os.path.exists(DB_PATH):
        print("✗ Database not found at:", DB_PATH)
        print("  Run build_database.py first.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("=" * 60)
    print("DATABASE VERIFICATION REPORT")
    print(f"Database: {os.path.abspath(DB_PATH)}")
    print("=" * 60)

    # === Table summaries ===
    tables = {
        "stock_prices":     ("date",           "ticker"),
        "news_articles":    ("published_date", "ticker"),
        "social_sentiment": ("date",           "ticker"),
        "sec_filings":      ("filing_date",    "ticker"),
        "macro_indicators": ("date",           "series_id"),
    }

    all_pass = True

    for table, (date_col, group_col) in tables.items():
        print(f"\n{'─' * 40}")
        print(f"TABLE: {table}")
        print(f"{'─' * 40}")

        # Row count
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  Rows: {count:,}")

        if count == 0:
            print(f"  ⚠ TABLE IS EMPTY")
            continue

        # Date range
        cursor.execute(f"SELECT MIN({date_col}), MAX({date_col}) FROM {table}")
        min_date, max_date = cursor.fetchone()
        print(f"  Date range: {min_date} to {max_date}")

        # Future data check
        cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {date_col} > ?", (DATA_CUTOFF,))
        future_count = cursor.fetchone()[0]
        if future_count > 0:
            print(f"  ✗ FUTURE DATA LEAK: {future_count} rows after {DATA_CUTOFF}")
            all_pass = False
        else:
            print(f"  ✓ No future data (cutoff: {DATA_CUTOFF})")

        # Unique groups
        cursor.execute(f"SELECT COUNT(DISTINCT {group_col}) FROM {table}")
        unique_groups = cursor.fetchone()[0]
        print(f"  Unique {group_col}s: {unique_groups}")

        # Show top groups
        cursor.execute(f"""
            SELECT {group_col}, COUNT(*) as cnt
            FROM {table}
            GROUP BY {group_col}
            ORDER BY cnt DESC
            LIMIT 5
        """)
        top_groups = cursor.fetchall()
        print(f"  Top 5 by count:")
        for name, cnt in top_groups:
            print(f"    {name}: {cnt:,}")

    # === Temporal query test ===
    print(f"\n{'=' * 60}")
    print("TEMPORAL QUERY TESTS")
    print(f"{'=' * 60}")

    # Test 1: Get TSLA prices before June 1, 2024
    print("\n  Test 1: TSLA prices before 2024-06-01")
    cursor.execute("""
        SELECT COUNT(*), MIN(date), MAX(date)
        FROM stock_prices
        WHERE ticker = 'TSLA' AND date < '2024-06-01'
    """)
    result = cursor.fetchone()
    if result[0] > 0:
        print(f"    ✓ {result[0]} rows, {result[1]} to {result[2]}")
    else:
        print(f"    ⚠ No TSLA data found (may not be downloaded yet)")

    # Test 2: Get news articles for NVDA in 2024
    print("\n  Test 2: NVDA news articles in 2024")
    cursor.execute("""
        SELECT COUNT(*), MIN(published_date), MAX(published_date)
        FROM news_articles
        WHERE ticker = 'NVDA' AND published_date >= '2024-01-01' AND published_date < '2025-01-01'
    """)
    result = cursor.fetchone()
    if result[0] > 0:
        print(f"    ✓ {result[0]} articles, {result[1]} to {result[2]}")
    else:
        print(f"    ⚠ No NVDA news found for 2024")

    # Test 3: Social sentiment for TSLA around April 2024 layoffs
    print("\n  Test 3: TSLA social sentiment around April 2024")
    cursor.execute("""
        SELECT date, avg_sentiment, post_count
        FROM social_sentiment
        WHERE ticker = 'TSLA' AND date >= '2024-04-01' AND date <= '2024-04-30'
        ORDER BY date
    """)
    rows = cursor.fetchall()
    if rows:
        for row in rows:
            print(f"    {row[0]}: sentiment={row[1]}, posts={row[2]}")
        print(f"    ✓ {len(rows)} sentiment records found")
    else:
        print(f"    ⚠ No TSLA social sentiment for April 2024")

    # Test 4: Macro data check
    print("\n  Test 4: Federal Funds Rate data")
    cursor.execute("""
        SELECT COUNT(*), MIN(date), MAX(date)
        FROM macro_indicators
        WHERE series_id = 'FEDFUNDS'
    """)
    result = cursor.fetchone()
    if result[0] > 0:
        print(f"    ✓ {result[0]} observations, {result[1]} to {result[2]}")
    else:
        print(f"    ⚠ No FEDFUNDS data (run download_macro_data.py first)")

    # === Final verdict ===
    print(f"\n{'=' * 60}")
    if all_pass:
        print("✓ ALL CHECKS PASSED — Database is ready for use")
    else:
        print("✗ SOME CHECKS FAILED — Review issues above")
    print(f"{'=' * 60}")

    # Database size
    db_size = os.path.getsize(DB_PATH) / (1024 * 1024)
    print(f"\nDatabase size: {db_size:.1f} MB")

    conn.close()


if __name__ == "__main__":
    verify_database()
