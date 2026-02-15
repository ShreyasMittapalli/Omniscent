import sqlite3
import os

db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "historical_data.db")
conn = sqlite3.connect(db)
c = conn.cursor()

print("=== DATABASE SUMMARY ===")

# Stock prices
c.execute("SELECT COUNT(1) FROM stock_prices")
print(f"stock_prices: {c.fetchone()[0]} rows")
c.execute("SELECT MIN(date), MAX(date) FROM stock_prices")
r = c.fetchone()
print(f"  date range: {r[0]} to {r[1]}")
c.execute("SELECT COUNT(DISTINCT ticker) FROM stock_prices")
print(f"  unique tickers: {c.fetchone()[0]}")

# News articles
c.execute("SELECT COUNT(1) FROM news_articles")
print(f"news_articles: {c.fetchone()[0]} rows")
c.execute("SELECT MIN(published_date), MAX(published_date) FROM news_articles")
r = c.fetchone()
print(f"  date range: {r[0]} to {r[1]}")

# Social sentiment
c.execute("SELECT COUNT(1) FROM social_sentiment")
print(f"social_sentiment: {c.fetchone()[0]} rows")
c.execute("SELECT MIN(date), MAX(date) FROM social_sentiment")
r = c.fetchone()
print(f"  date range: {r[0]} to {r[1]}")

# SEC filings
c.execute("SELECT COUNT(1) FROM sec_filings")
print(f"sec_filings: {c.fetchone()[0]} rows")
c.execute("SELECT MIN(filing_date), MAX(filing_date) FROM sec_filings")
r = c.fetchone()
print(f"  date range: {r[0]} to {r[1]}")

# Macro indicators
c.execute("SELECT COUNT(1) FROM macro_indicators")
print(f"macro_indicators: {c.fetchone()[0]} rows")
c.execute("SELECT MIN(date), MAX(date) FROM macro_indicators")
r = c.fetchone()
print(f"  date range: {r[0]} to {r[1]}")

# Future data check
print("\n=== FUTURE DATA CHECK (must be 0) ===")
checks = [
    ("stock_prices", "date"),
    ("news_articles", "published_date"),
    ("social_sentiment", "date"),
    ("sec_filings", "filing_date"),
    ("macro_indicators", "date"),
]
for t, d in checks:
    c.execute(f"SELECT COUNT(1) FROM {t} WHERE {d} >= '2025-07-01'")
    cnt = c.fetchone()[0]
    status = "PASS" if cnt == 0 else "FAIL"
    print(f"  {t}: {cnt} rows after cutoff [{status}]")

# DB size
sz = os.path.getsize(db) / (1024*1024)
print(f"\nDatabase size: {sz:.1f} MB")

conn.close()
