import sqlite3, os, json

db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "historical_data.db")
conn = sqlite3.connect(db)
c = conn.cursor()

results = {}

# Stock prices
c.execute("SELECT COUNT(1) FROM stock_prices")
results["stock_prices_rows"] = c.fetchone()[0]
c.execute("SELECT MIN(date), MAX(date) FROM stock_prices")
r = c.fetchone()
results["stock_prices_dates"] = f"{r[0]} to {r[1]}"
c.execute("SELECT COUNT(DISTINCT ticker) FROM stock_prices")
results["stock_prices_tickers"] = c.fetchone()[0]

# News articles
c.execute("SELECT COUNT(1) FROM news_articles")
results["news_articles_rows"] = c.fetchone()[0]
c.execute("SELECT MIN(published_date), MAX(published_date) FROM news_articles")
r = c.fetchone()
results["news_articles_dates"] = f"{r[0]} to {r[1]}"

# Social sentiment
c.execute("SELECT COUNT(1) FROM social_sentiment")
results["social_sentiment_rows"] = c.fetchone()[0]
c.execute("SELECT MIN(date), MAX(date) FROM social_sentiment")
r = c.fetchone()
results["social_sentiment_dates"] = f"{r[0]} to {r[1]}"

# SEC filings
c.execute("SELECT COUNT(1) FROM sec_filings")
results["sec_filings_rows"] = c.fetchone()[0]
c.execute("SELECT MIN(filing_date), MAX(filing_date) FROM sec_filings")
r = c.fetchone()
results["sec_filings_dates"] = f"{r[0]} to {r[1]}"

# Macro
c.execute("SELECT COUNT(1) FROM macro_indicators")
results["macro_indicators_rows"] = c.fetchone()[0]
c.execute("SELECT MIN(date), MAX(date) FROM macro_indicators")
r = c.fetchone()
results["macro_indicators_dates"] = f"{r[0]} to {r[1]}"

# Future data checks
for t, d in [("stock_prices","date"),("news_articles","published_date"),
             ("social_sentiment","date"),("sec_filings","filing_date"),
             ("macro_indicators","date")]:
    c.execute(f"SELECT COUNT(1) FROM {t} WHERE {d} >= '2025-07-01'")
    results[f"{t}_future_leak"] = c.fetchone()[0]

results["db_size_mb"] = round(os.path.getsize(db) / (1024*1024), 1)

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "db_check.json")
with open(out, "w") as f:
    json.dump(results, f, indent=2)

conn.close()
print("Done. Check db_check.json")
