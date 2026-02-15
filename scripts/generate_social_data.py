"""
Generate a large social sentiment dataset (~50k+ records) for all tickers.
Produces daily aggregated sentiment from Reddit and Twitter, aligned to
real market patterns (higher volume during earnings, crashes, etc.)
All dates strictly before July 1, 2025.

Usage:
    python generate_social_data.py
"""

import os
import csv
import math
import random
from datetime import datetime, timedelta

random.seed(42)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "..", "assets", "social_data", "social_sentiment.csv")

START_DATE = datetime(2020, 1, 1)
END_DATE = datetime(2025, 6, 30)

PLATFORMS = ["reddit", "twitter"]

TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AMD", "INTC", "CRM",
    "ADBE", "NFLX", "PYPL", "SQ", "SHOP", "SNOW", "PLTR", "UBER", "ABNB", "COIN",
    "JPM", "BAC", "GS", "MS", "WFC", "V", "MA", "BRK-B", "C", "AXP",
    "JNJ", "UNH", "PFE", "MRNA", "ABBV", "LLY", "TMO", "MRK", "BMY", "GILD",
    "XOM", "CVX", "COP", "SLB", "OXY",
    "WMT", "COST", "HD", "NKE", "SBUX", "MCD", "DIS",
    "BA", "CAT", "GE", "LMT", "UPS",
]

# Base daily post volume (popularity tiers)
TICKER_POPULARITY = {
    # Tier 1: Very popular on social media (high volume)
    "TSLA": 1.0, "AAPL": 0.85, "NVDA": 0.80, "AMZN": 0.75, "MSFT": 0.70,
    "META": 0.70, "GOOGL": 0.65, "AMD": 0.65, "PLTR": 0.60, "COIN": 0.60,
    "NFLX": 0.55, "GME": 0.90, "AMC": 0.85,
    # Tier 2: Moderately popular
    "BA": 0.45, "DIS": 0.45, "PFE": 0.45, "MRNA": 0.45, "UBER": 0.40,
    "ABNB": 0.40, "SQ": 0.40, "PYPL": 0.40, "SHOP": 0.40, "INTC": 0.40,
    "CRM": 0.35, "ADBE": 0.35, "SNOW": 0.35, "NFLX": 0.55, "NKE": 0.35,
    "SBUX": 0.35, "MCD": 0.30, "WMT": 0.30, "JPM": 0.35, "GS": 0.30,
    # Tier 3: Less social media attention
    "XOM": 0.25, "CVX": 0.25, "HD": 0.25, "COST": 0.25, "JNJ": 0.20,
    "UNH": 0.20, "LLY": 0.30, "MRK": 0.20, "ABBV": 0.20, "BMY": 0.18,
    "GILD": 0.18, "TMO": 0.15, "V": 0.22, "MA": 0.20, "BAC": 0.22,
    "WFC": 0.22, "MS": 0.20, "C": 0.18, "AXP": 0.18, "BRK-B": 0.25,
    "COP": 0.18, "SLB": 0.15, "OXY": 0.22, "CAT": 0.18, "GE": 0.20,
    "LMT": 0.20, "UPS": 0.18,
}

# Market periods with sentiment bias and volume multiplier
MARKET_PERIODS = [
    # (start, end, name, sentiment_bias, volume_multiplier)
    (datetime(2020, 1, 1), datetime(2020, 2, 19), "pre_covid", 0.15, 1.0),
    (datetime(2020, 2, 20), datetime(2020, 3, 23), "covid_crash", -0.50, 3.5),
    (datetime(2020, 3, 24), datetime(2020, 6, 30), "covid_recovery", 0.15, 2.5),
    (datetime(2020, 7, 1), datetime(2020, 12, 31), "stimulus_rally", 0.25, 1.8),
    (datetime(2021, 1, 1), datetime(2021, 2, 10), "meme_mania", 0.10, 5.0),
    (datetime(2021, 2, 11), datetime(2021, 6, 30), "reopening", 0.20, 1.5),
    (datetime(2021, 7, 1), datetime(2021, 11, 15), "bull_market", 0.22, 1.3),
    (datetime(2021, 11, 16), datetime(2022, 1, 3), "peak_euphoria", 0.15, 1.8),
    (datetime(2022, 1, 4), datetime(2022, 3, 14), "rate_hike_fear", -0.30, 2.2),
    (datetime(2022, 3, 15), datetime(2022, 6, 15), "bear_begins", -0.25, 2.0),
    (datetime(2022, 6, 16), datetime(2022, 10, 12), "deep_bear", -0.35, 2.5),
    (datetime(2022, 10, 13), datetime(2023, 1, 31), "bear_rally", 0.05, 1.5),
    (datetime(2023, 2, 1), datetime(2023, 3, 15), "bank_crisis", -0.20, 3.0),
    (datetime(2023, 3, 16), datetime(2023, 6, 30), "ai_hype", 0.35, 2.5),
    (datetime(2023, 7, 1), datetime(2023, 10, 31), "rate_plateau", -0.05, 1.2),
    (datetime(2023, 11, 1), datetime(2024, 3, 31), "year_end_rally", 0.30, 1.8),
    (datetime(2024, 4, 1), datetime(2024, 6, 30), "mixed_2024", 0.05, 1.3),
    (datetime(2024, 7, 1), datetime(2024, 10, 31), "election_buildup", 0.00, 1.5),
    (datetime(2024, 11, 1), datetime(2024, 12, 31), "post_election", 0.15, 1.8),
    (datetime(2025, 1, 1), datetime(2025, 6, 30), "early_2025", 0.05, 1.2),
]

# Special high-volume events (ticker-specific)
SPECIAL_EVENTS = {
    "TSLA": [
        (datetime(2020, 8, 31), 0.80, 8.0, "stock split"),
        (datetime(2020, 12, 21), 0.85, 7.0, "S&P inclusion"),
        (datetime(2021, 1, 8), 0.75, 5.0, "Musk richest"),
        (datetime(2022, 4, 25), -0.40, 6.0, "Twitter deal"),
        (datetime(2022, 11, 4), -0.55, 7.0, "Twitter distraction"),
        (datetime(2024, 4, 15), -0.65, 6.0, "mass layoffs"),
    ],
    "NVDA": [
        (datetime(2023, 5, 24), 0.92, 10.0, "blowout earnings"),
        (datetime(2023, 5, 30), 0.88, 8.0, "$1T market cap"),
        (datetime(2024, 2, 21), 0.90, 9.0, "record revenue"),
        (datetime(2024, 5, 22), 0.85, 7.0, "stock split"),
        (datetime(2024, 6, 18), 0.82, 8.0, "most valuable company"),
    ],
    "META": [
        (datetime(2021, 10, 28), -0.20, 8.0, "Meta rebrand"),
        (datetime(2022, 2, 3), -0.75, 9.0, "earnings crash"),
        (datetime(2022, 10, 26), -0.80, 8.0, "metaverse losses"),
        (datetime(2023, 2, 1), 0.82, 7.0, "year of efficiency"),
        (datetime(2024, 2, 1), 0.88, 8.0, "blowout Q4 + dividend"),
    ],
    "COIN": [
        (datetime(2021, 4, 14), 0.78, 8.0, "IPO day"),
        (datetime(2022, 5, 12), -0.82, 7.0, "crypto crash"),
        (datetime(2022, 11, 9), -0.85, 10.0, "FTX collapse"),
        (datetime(2024, 1, 10), 0.72, 7.0, "Bitcoin ETF"),
    ],
    "PFE": [
        (datetime(2020, 11, 9), 0.90, 10.0, "vaccine efficacy"),
        (datetime(2020, 12, 11), 0.88, 9.0, "FDA authorization"),
    ],
    "MRNA": [
        (datetime(2020, 11, 16), 0.88, 9.0, "vaccine results"),
        (datetime(2020, 11, 30), 0.85, 8.0, "94% efficacy"),
    ],
    "BA": [
        (datetime(2020, 11, 18), 0.45, 5.0, "737 MAX ungrounded"),
        (datetime(2024, 1, 5), -0.85, 10.0, "door plug blowout"),
        (datetime(2024, 3, 25), -0.65, 6.0, "CEO steps down"),
    ],
    "AAPL": [
        (datetime(2020, 7, 30), 0.78, 5.0, "stock split"),
        (datetime(2022, 1, 3), 0.85, 6.0, "$3T market cap"),
        (datetime(2024, 2, 2), -0.20, 5.0, "Vision Pro launch"),
        (datetime(2024, 6, 10), 0.55, 6.0, "Apple Intelligence"),
    ],
    "GOOGL": [
        (datetime(2023, 2, 6), -0.30, 7.0, "Bard demo error"),
        (datetime(2024, 8, 5), -0.65, 8.0, "antitrust ruling"),
    ],
    "AMZN": [
        (datetime(2023, 1, 4), -0.60, 6.0, "18k layoffs"),
    ],
    "NFLX": [
        (datetime(2022, 1, 20), -0.70, 7.0, "subscriber loss"),
        (datetime(2022, 4, 19), -0.82, 8.0, "200k sub loss"),
        (datetime(2024, 1, 23), 0.80, 6.0, "password crackdown win"),
    ],
    "LLY": [
        (datetime(2023, 11, 8), 0.85, 6.0, "Zepbound approval"),
    ],
    "UNH": [
        (datetime(2024, 2, 21), -0.72, 7.0, "cyberattack"),
    ],
}


def get_period_params(date: datetime):
    for start, end, name, bias, vol_mult in MARKET_PERIODS:
        if start <= date <= end:
            return bias, vol_mult, name
    return 0.0, 1.0, "normal"


def get_special_event(ticker: str, date: datetime):
    events = SPECIAL_EVENTS.get(ticker, [])
    for evt_date, sentiment, vol_mult, desc in events:
        # Event affects sentiment for 3 days
        if abs((date - evt_date).days) <= 2:
            decay = 1.0 - (abs((date - evt_date).days) * 0.3)
            return sentiment * decay, vol_mult * decay
    return None, None


def generate_daily_record(ticker: str, date: datetime, platform: str) -> dict:
    popularity = TICKER_POPULARITY.get(ticker, 0.2)
    period_bias, period_vol, period_name = get_period_params(date)
    
    # Base post count (varies by popularity and platform)
    if platform == "reddit":
        base_posts = int(50 + popularity * 300)
    else:
        base_posts = int(100 + popularity * 800)

    # Apply period volume multiplier
    posts = int(base_posts * period_vol)

    # Check for special events
    evt_sentiment, evt_vol = get_special_event(ticker, date)
    if evt_vol is not None:
        posts = int(posts * evt_vol)

    # Add daily noise
    posts = max(5, int(posts * random.uniform(0.5, 1.5)))

    # Engagement (correlated with posts but with multiplier)
    engagement_mult = random.uniform(3, 12)
    engagement = int(posts * engagement_mult)

    # Sentiment calculation
    base_sentiment = period_bias
    if evt_sentiment is not None:
        base_sentiment = evt_sentiment  # Override with event sentiment

    # Add ticker-specific noise
    noise = random.gauss(0, 0.15)
    sentiment = base_sentiment + noise
    sentiment = max(-1.0, min(1.0, round(sentiment, 2)))

    return {
        "ticker": ticker,
        "date": date.strftime("%Y-%m-%d"),
        "platform": platform,
        "avg_sentiment": sentiment,
        "post_count": posts,
        "engagement": engagement,
    }


def main():
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    print("=" * 60)
    print("GENERATING SOCIAL SENTIMENT DATASET")
    print(f"Tickers: {len(TICKERS)}")
    print(f"Period: {START_DATE.date()} to {END_DATE.date()}")
    print("=" * 60)

    all_records = []
    total_days = (END_DATE - START_DATE).days

    for ticker_idx, ticker in enumerate(TICKERS):
        if (ticker_idx + 1) % 10 == 0:
            print(f"  Processing {ticker_idx + 1}/{len(TICKERS)} tickers...")

        # Generate records at varying frequency per ticker
        popularity = TICKER_POPULARITY.get(ticker, 0.2)

        # High-popularity tickers get daily records, low get every few days
        if popularity >= 0.6:
            days_between = 1  # daily
        elif popularity >= 0.35:
            days_between = 2  # every other day
        else:
            days_between = 3  # every 3 days

        current_date = START_DATE
        while current_date <= END_DATE:
            # Skip weekends
            if current_date.weekday() < 5:
                # Generate for each platform
                for platform in PLATFORMS:
                    # Reddit more consistent, Twitter more sporadic
                    if platform == "twitter" and random.random() < 0.3:
                        current_date += timedelta(days=1)
                        continue

                    record = generate_daily_record(ticker, current_date, platform)
                    all_records.append(record)

            current_date += timedelta(days=days_between)

    # Sort by date
    all_records.sort(key=lambda x: (x["date"], x["ticker"]))

    # Write CSV
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["ticker", "date", "platform",
                                                "avg_sentiment", "post_count",
                                                "engagement"])
        writer.writeheader()
        writer.writerows(all_records)

    print(f"\nGenerated {len(all_records):,} records")
    print(f"Output: {os.path.abspath(OUTPUT_FILE)}")
    file_size = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)
    print(f"File size: {file_size:.1f} MB")

    # Stats
    from collections import Counter
    platform_counts = Counter(r["platform"] for r in all_records)
    print(f"\nBy platform:")
    for p, c in platform_counts.items():
        print(f"  {p}: {c:,}")

    sentiments = [r["avg_sentiment"] for r in all_records]
    print(f"\nSentiment range: {min(sentiments)} to {max(sentiments)}")
    print(f"Avg sentiment: {sum(sentiments)/len(sentiments):.3f}")

    total_posts = sum(r["post_count"] for r in all_records)
    total_engagement = sum(r["engagement"] for r in all_records)
    print(f"\nTotal post count: {total_posts:,}")
    print(f"Total engagement: {total_engagement:,}")

    dates = [r["date"] for r in all_records]
    print(f"Date range: {min(dates)} to {max(dates)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
