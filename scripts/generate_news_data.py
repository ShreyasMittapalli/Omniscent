"""
Generate a large curated news headlines dataset (~10k+ articles) for all tickers.
Headlines are templated from real market event patterns across 2020-2025.
All dates strictly before July 1, 2025.

Usage:
    python generate_news_data.py
"""

import os
import csv
import random
import hashlib
from datetime import datetime, timedelta

random.seed(42)  # Reproducible output

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "..", "assets", "news_data", "news_headlines.csv")

START_DATE = datetime(2020, 1, 1)
END_DATE = datetime(2025, 6, 30)

SOURCES = [
    "Reuters", "Bloomberg", "CNBC", "Wall Street Journal", "Financial Times",
    "MarketWatch", "Barron's", "The Motley Fool", "Seeking Alpha", "Yahoo Finance",
    "Investor's Business Daily", "TheStreet", "Benzinga", "TipRanks", "Zacks",
    "AP News", "BBC Business", "Forbes", "Business Insider", "TechCrunch",
]

TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AMD", "INTC", "CRM",
    "ADBE", "NFLX", "PYPL", "SQ", "SHOP", "SNOW", "PLTR", "UBER", "ABNB", "COIN",
    "JPM", "BAC", "GS", "MS", "WFC", "V", "MA", "BRK-B", "C", "AXP",
    "JNJ", "UNH", "PFE", "MRNA", "ABBV", "LLY", "TMO", "MRK", "BMY", "GILD",
    "XOM", "CVX", "COP", "SLB", "OXY",
    "WMT", "COST", "HD", "NKE", "SBUX", "MCD", "DIS",
    "BA", "CAT", "GE", "LMT", "UPS",
]

TICKER_NAMES = {
    "AAPL": "Apple", "MSFT": "Microsoft", "GOOGL": "Alphabet", "AMZN": "Amazon",
    "NVDA": "Nvidia", "META": "Meta Platforms", "TSLA": "Tesla", "AMD": "AMD",
    "INTC": "Intel", "CRM": "Salesforce", "ADBE": "Adobe", "NFLX": "Netflix",
    "PYPL": "PayPal", "SQ": "Block", "SHOP": "Shopify", "SNOW": "Snowflake",
    "PLTR": "Palantir", "UBER": "Uber", "ABNB": "Airbnb", "COIN": "Coinbase",
    "JPM": "JPMorgan", "BAC": "Bank of America", "GS": "Goldman Sachs",
    "MS": "Morgan Stanley", "WFC": "Wells Fargo", "V": "Visa", "MA": "Mastercard",
    "BRK-B": "Berkshire Hathaway", "C": "Citigroup", "AXP": "American Express",
    "JNJ": "Johnson & Johnson", "UNH": "UnitedHealth", "PFE": "Pfizer",
    "MRNA": "Moderna", "ABBV": "AbbVie", "LLY": "Eli Lilly",
    "TMO": "Thermo Fisher", "MRK": "Merck", "BMY": "Bristol-Myers Squibb",
    "GILD": "Gilead Sciences", "XOM": "ExxonMobil", "CVX": "Chevron",
    "COP": "ConocoPhillips", "SLB": "SLB", "OXY": "Occidental Petroleum",
    "WMT": "Walmart", "COST": "Costco", "HD": "Home Depot", "NKE": "Nike",
    "SBUX": "Starbucks", "MCD": "McDonald's", "DIS": "Disney",
    "BA": "Boeing", "CAT": "Caterpillar", "GE": "GE Aerospace",
    "LMT": "Lockheed Martin", "UPS": "UPS",
}

SECTORS = {
    "tech": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AMD", "INTC", "CRM", "ADBE", "NFLX", "PYPL", "SQ", "SHOP", "SNOW", "PLTR", "UBER", "ABNB", "COIN"],
    "finance": ["JPM", "BAC", "GS", "MS", "WFC", "V", "MA", "BRK-B", "C", "AXP"],
    "healthcare": ["JNJ", "UNH", "PFE", "MRNA", "ABBV", "LLY", "TMO", "MRK", "BMY", "GILD"],
    "energy": ["XOM", "CVX", "COP", "SLB", "OXY"],
    "consumer": ["WMT", "COST", "HD", "NKE", "SBUX", "MCD", "DIS"],
    "industrial": ["BA", "CAT", "GE", "LMT", "UPS"],
}

# === HEADLINE TEMPLATES ===
# Each template: (title_template, content_template, sentiment_range)
# Sentiment range: (min, max) where -1 = very bearish, +1 = very bullish

EARNINGS_TEMPLATES = [
    ("{name} Reports Q{q} Revenue of ${rev}B, {beat_miss} Expectations",
     "{name} announced Q{q} {year} revenue of ${rev} billion, {beat_miss_detail}. {metric_detail}",
     None),  # sentiment computed dynamically
    ("{name} Q{q} Earnings: EPS of ${eps}, Revenue {direction}",
     "{name} reported Q{q} {year} earnings per share of ${eps}, with revenue {direction_detail}. {guidance}",
     None),
    ("{name} Posts {adj} Q{q} Results Amid {context}",
     "{name}'s Q{q} {year} results were {adj_detail}, as {context_detail}. {outlook}",
     None),
]

ANALYST_TEMPLATES = [
    ("Analyst {action} {name} Price Target to ${pt}",
     "{analyst_firm} analyst {action_past} {name} ({ticker}) price target to ${pt}, citing {reason}. The firm maintains a {rating} rating.",
     None),
    ("{analyst_firm} {upgrades_downgrades} {name} to {rating}",
     "{analyst_firm} {upgrades_downgrades_past} {name} ({ticker}) from {old_rating} to {rating}, citing {reason}.",
     None),
]

PRODUCT_TEMPLATES = [
    ("{name} Launches {product}, Shares {react}",
     "{name} unveiled {product_detail} on {date_str}. {market_reaction}. Analysts {analyst_view}.",
     None),
    ("{name} Announces {initiative} Strategy",
     "{name} announced a new {initiative_detail} strategy aimed at {goal}. The move {impact}.",
     None),
]

MACRO_TEMPLATES = [
    ("{sector_name} Stocks {move} as {macro_event}",
     "{sector_name} sector {move_detail} as {macro_event_detail}. {tickers_affected} were among the {movers}.",
     None),
    ("{name} Shares {move} on {catalyst}",
     "{name} ({ticker}) shares {move_detail} following {catalyst_detail}. {volume_note}",
     None),
]

MANAGEMENT_TEMPLATES = [
    ("{name} CEO {ceo_action}",
     "{name} announced that {ceo_detail}. {board_reaction}. The {succession_detail}.",
     None),
    ("{name} Announces {reorg_action}",
     "{name} revealed plans to {reorg_detail}, affecting {affected}. The restructuring aims to {goal}.",
     None),
]

REGULATORY_TEMPLATES = [
    ("{name} Faces {reg_action} from {regulator}",
     "{regulator} {reg_action_detail} against {name} ({ticker}), alleging {allegation}. {company_response}.",
     (-0.7, -0.3)),
    ("{name} Settles {legal_matter} for ${amount}M",
     "{name} agreed to pay ${amount} million to settle {legal_matter_detail}. {impact_statement}.",
     (-0.5, -0.1)),
]

MA_TEMPLATES = [
    ("{name} to Acquire {target} for ${deal_val}B",
     "{name} announced a definitive agreement to acquire {target} for ${deal_val} billion. {deal_rationale}. {regulatory_note}.",
     (0.1, 0.6)),
    ("{name} Completes {target} Acquisition",
     "{name} completed its acquisition of {target}, {completion_detail}. {synergy_note}.",
     (0.3, 0.7)),
]

DIVIDEND_TEMPLATES = [
    ("{name} Raises Dividend by {pct}%, Announces ${bb}B Buyback",
     "{name} increased its quarterly dividend by {pct}% and authorized a ${bb} billion share repurchase program. {yield_note}.",
     (0.4, 0.8)),
    ("{name} Declares Special Dividend of ${amt} Per Share",
     "{name}'s board approved a special dividend of ${amt} per share, payable to shareholders of record. {cash_note}.",
     (0.5, 0.8)),
]

# === Market event periods with sentiment biases ===
MARKET_PERIODS = [
    (datetime(2020, 1, 1), datetime(2020, 2, 19), "pre_covid_bull", 0.15),
    (datetime(2020, 2, 20), datetime(2020, 3, 23), "covid_crash", -0.45),
    (datetime(2020, 3, 24), datetime(2020, 8, 31), "covid_recovery", 0.20),
    (datetime(2020, 9, 1), datetime(2020, 12, 31), "election_stimulus", 0.25),
    (datetime(2021, 1, 1), datetime(2021, 2, 10), "meme_stock_mania", 0.10),
    (datetime(2021, 2, 11), datetime(2021, 6, 30), "reopening_trade", 0.20),
    (datetime(2021, 7, 1), datetime(2021, 12, 31), "late_bull", 0.15),
    (datetime(2022, 1, 1), datetime(2022, 6, 15), "rate_hike_selloff", -0.30),
    (datetime(2022, 6, 16), datetime(2022, 10, 12), "bear_market", -0.25),
    (datetime(2022, 10, 13), datetime(2023, 1, 31), "bear_rally", 0.05),
    (datetime(2023, 2, 1), datetime(2023, 6, 30), "ai_boom_starts", 0.25),
    (datetime(2023, 7, 1), datetime(2023, 10, 31), "rate_uncertainty", -0.05),
    (datetime(2023, 11, 1), datetime(2024, 3, 31), "ai_rally", 0.30),
    (datetime(2024, 4, 1), datetime(2024, 7, 31), "mixed_signals", 0.05),
    (datetime(2024, 8, 1), datetime(2024, 12, 31), "election_year_end", 0.10),
    (datetime(2025, 1, 1), datetime(2025, 6, 30), "new_year_trade", 0.05),
]


def get_market_bias(date: datetime) -> float:
    for start, end, _, bias in MARKET_PERIODS:
        if start <= date <= end:
            return bias
    return 0.0


def random_date(start: datetime, end: datetime) -> datetime:
    delta = end - start
    random_days = random.randint(0, delta.days)
    d = start + timedelta(days=random_days)
    # Skip weekends
    while d.weekday() >= 5:
        d += timedelta(days=1)
        if d > end:
            d = start + timedelta(days=random.randint(0, delta.days))
    return d


def generate_earnings_article(ticker: str, date: datetime) -> dict:
    name = TICKER_NAMES.get(ticker, ticker)
    q = (date.month - 1) // 3 + 1
    year = date.year
    rev = round(random.uniform(5, 120), 1)
    eps = round(random.uniform(0.5, 15), 2)
    beat = random.random() > 0.4  # 60% beat rate

    if beat:
        title = f"{name} Reports Q{q} Revenue of ${rev}B, Beating Expectations"
        content = f"{name} announced Q{q} {year} revenue of ${rev} billion, surpassing analyst estimates. The company reported earnings per share of ${eps}, above consensus. Management raised full-year guidance citing strong demand."
        sentiment = round(random.uniform(0.3, 0.85), 2)
    else:
        title = f"{name} Q{q} Earnings Miss Estimates, Revenue Falls Short"
        content = f"{name} reported Q{q} {year} revenue of ${rev} billion, missing analyst expectations. Earnings per share came in at ${eps}, below consensus. Management cited macroeconomic headwinds and cautious consumer spending."
        sentiment = round(random.uniform(-0.7, -0.15), 2)

    return {"ticker": ticker, "title": title, "content": content,
            "published_date": date.strftime("%Y-%m-%d"),
            "source": random.choice(SOURCES), "sentiment_score": sentiment}


def generate_analyst_article(ticker: str, date: datetime) -> dict:
    name = TICKER_NAMES.get(ticker, ticker)
    firms = ["Morgan Stanley", "Goldman Sachs", "JPMorgan", "Bank of America",
             "Citigroup", "Wells Fargo", "Barclays", "UBS", "Deutsche Bank",
             "Credit Suisse", "Jefferies", "Piper Sandler", "Wedbush",
             "Raymond James", "Bernstein", "Oppenheimer", "Needham",
             "KeyBanc", "Stifel", "Cowen"]
    firm = random.choice(firms)
    pt = round(random.uniform(50, 500), 0)
    ratings = ["Buy", "Overweight", "Outperform", "Hold", "Neutral", "Sell", "Underweight"]

    is_positive = random.random() > 0.35
    if is_positive:
        action = random.choice(["Raises", "Increases", "Boosts"])
        rating = random.choice(["Buy", "Overweight", "Outperform"])
        reason = random.choice(["strong growth outlook", "improving fundamentals",
                                "market share gains", "AI tailwinds", "margin expansion",
                                "accelerating revenue growth", "strategic positioning"])
        sentiment = round(random.uniform(0.2, 0.7), 2)
    else:
        action = random.choice(["Cuts", "Lowers", "Reduces"])
        rating = random.choice(["Hold", "Neutral", "Underweight", "Sell"])
        reason = random.choice(["valuation concerns", "slowing growth", "competitive pressures",
                                "margin compression", "regulatory headwinds",
                                "macroeconomic uncertainty", "execution risks"])
        sentiment = round(random.uniform(-0.6, -0.1), 2)

    title = f"{firm} {action} {name} Price Target to ${int(pt)}"
    content = f"{firm} analyst {action.lower()} {name} ({ticker}) price target to ${int(pt)}, citing {reason}. The firm maintains a {rating} rating on the stock."

    return {"ticker": ticker, "title": title, "content": content,
            "published_date": date.strftime("%Y-%m-%d"),
            "source": random.choice(SOURCES), "sentiment_score": sentiment}


def generate_product_article(ticker: str, date: datetime) -> dict:
    name = TICKER_NAMES.get(ticker, ticker)
    sector = None
    for s, tickers in SECTORS.items():
        if ticker in tickers:
            sector = s
            break

    products_by_sector = {
        "tech": ["AI-powered platform", "new cloud service", "next-gen chip", "software update",
                 "enterprise solution", "developer tools", "subscription tier", "API platform",
                 "hardware device", "security product", "analytics dashboard", "mobile app update"],
        "finance": ["digital banking platform", "payment solution", "wealth management tool",
                    "credit product", "mobile banking update", "blockchain initiative",
                    "lending platform", "robo-advisor service"],
        "healthcare": ["new drug candidate", "clinical trial results", "medical device",
                       "diagnostic tool", "gene therapy", "biosimilar product",
                       "digital health platform", "vaccine update"],
        "energy": ["clean energy initiative", "drilling technology", "carbon capture project",
                   "refinery upgrade", "renewable energy investment", "LNG facility expansion"],
        "consumer": ["loyalty program update", "e-commerce expansion", "store format redesign",
                     "delivery service upgrade", "mobile ordering platform", "sustainability initiative"],
        "industrial": ["manufacturing automation", "defense contract deliverable", "new aircraft model",
                       "logistics technology", "fleet electrification", "supply chain platform"],
    }

    product = random.choice(products_by_sector.get(sector, ["new initiative"]))
    positive = random.random() > 0.3
    if positive:
        react = random.choice(["Rise", "Gain", "Jump"])
        title = f"{name} Launches {product.title()}, Shares {react}"
        content = f"{name} unveiled its new {product} at a launch event. Early reception has been positive, with analysts noting strong market potential. The initiative aligns with {name}'s strategic growth priorities."
        sentiment = round(random.uniform(0.2, 0.75), 2)
    else:
        react = random.choice(["Dip", "Slide", "Fall"])
        title = f"{name} {product.title()} Launch Receives Mixed Reviews"
        content = f"{name}'s new {product} received mixed reviews from analysts and customers. Concerns about pricing, competition, and execution weighed on investor sentiment."
        sentiment = round(random.uniform(-0.5, -0.05), 2)

    return {"ticker": ticker, "title": title, "content": content,
            "published_date": date.strftime("%Y-%m-%d"),
            "source": random.choice(SOURCES), "sentiment_score": sentiment}


def generate_market_article(ticker: str, date: datetime) -> dict:
    name = TICKER_NAMES.get(ticker, ticker)
    bias = get_market_bias(date)

    catalysts_positive = [
        "strong jobs data", "Fed signals rate pause", "inflation cooling faster than expected",
        "GDP growth beats expectations", "consumer spending surges", "global trade optimism",
        "earnings season surprises to upside", "M&A activity picks up",
        "institutional investors increase equity allocation", "market breadth improves",
    ]
    catalysts_negative = [
        "rising interest rate fears", "inflation data spooks markets", "recession concerns mount",
        "geopolitical tensions escalate", "yield curve inverts", "consumer confidence drops",
        "unemployment claims rise", "oil prices surge on supply fears", "banking sector stress",
        "trade war concerns resurface", "debt ceiling uncertainty", "Fed signals more rate hikes",
    ]

    if bias > 0 or (bias == 0 and random.random() > 0.45):
        catalyst = random.choice(catalysts_positive)
        move = random.choice(["Rally", "Surge", "Climb", "Gain"])
        pct = round(random.uniform(1.0, 5.5), 1)
        title = f"{name} Shares {move} {pct}% on {catalyst.title()}"
        content = f"{name} ({ticker}) shares {move.lower()}ed {pct}% following {catalyst}. Trading volume exceeded the 30-day average. Analysts see continued momentum for the stock."
        sentiment = round(random.uniform(0.15, 0.7) + bias * 0.3, 2)
    else:
        catalyst = random.choice(catalysts_negative)
        move = random.choice(["Drop", "Fall", "Slide", "Tumble", "Decline"])
        pct = round(random.uniform(1.0, 7.0), 1)
        title = f"{name} Shares {move} {pct}% Amid {catalyst.title()}"
        content = f"{name} ({ticker}) shares {move.lower()}ed {pct}% as {catalyst}. Investors moved to reduce risk exposure. The broader market also faced selling pressure."
        sentiment = round(random.uniform(-0.7, -0.1) + bias * 0.3, 2)

    sentiment = max(-1.0, min(1.0, sentiment))

    return {"ticker": ticker, "title": title, "content": content,
            "published_date": date.strftime("%Y-%m-%d"),
            "source": random.choice(SOURCES), "sentiment_score": sentiment}


def generate_management_article(ticker: str, date: datetime) -> dict:
    name = TICKER_NAMES.get(ticker, ticker)
    events = [
        (f"{name} Announces Organizational Restructuring",
         f"{name} revealed plans to reorganize its business units to improve efficiency and accelerate growth. The restructuring will affect multiple divisions and is expected to generate cost savings.",
         (-0.3, 0.2)),
        (f"{name} Names New Chief Technology Officer",
         f"{name} appointed a new CTO to lead its technology and innovation strategy. The hire signals an increased focus on digital transformation and AI capabilities.",
         (0.1, 0.5)),
        (f"{name} Board Approves New Strategic Plan",
         f"{name}'s board of directors approved a three-year strategic plan focusing on core business growth, margin improvement, and capital returns to shareholders.",
         (0.2, 0.6)),
        (f"{name} CFO Announces Retirement",
         f"{name}'s Chief Financial Officer announced plans to retire after serving the company for several years. A search for a successor is underway.",
         (-0.3, 0.1)),
        (f"{name} Cuts Workforce by {random.randint(3,15)}%",
         f"{name} announced layoffs affecting thousands of employees as part of a cost reduction program. The company cited the need to adapt to changing market conditions.",
         (-0.6, -0.2)),
    ]
    event = random.choice(events)
    sentiment = round(random.uniform(event[2][0], event[2][1]), 2)

    return {"ticker": ticker, "title": event[0], "content": event[1],
            "published_date": date.strftime("%Y-%m-%d"),
            "source": random.choice(SOURCES), "sentiment_score": sentiment}


def generate_dividend_article(ticker: str, date: datetime) -> dict:
    name = TICKER_NAMES.get(ticker, ticker)
    pct = random.randint(3, 25)
    bb = round(random.uniform(1, 50), 0)

    title = f"{name} Raises Dividend by {pct}%, Announces ${int(bb)}B Buyback"
    content = f"{name} increased its quarterly dividend by {pct}% and authorized a ${int(bb)} billion share repurchase program. The move reflects management's confidence in cash flow generation and commitment to shareholder returns."
    sentiment = round(random.uniform(0.4, 0.8), 2)

    return {"ticker": ticker, "title": title, "content": content,
            "published_date": date.strftime("%Y-%m-%d"),
            "source": random.choice(SOURCES), "sentiment_score": sentiment}


def generate_regulatory_article(ticker: str, date: datetime) -> dict:
    name = TICKER_NAMES.get(ticker, ticker)
    regulators = ["SEC", "FTC", "DOJ", "EU Commission", "Federal Reserve",
                  "state attorney general", "CFPB", "CFTC"]
    regulator = random.choice(regulators)
    amount = random.randint(10, 2000)

    events = [
        (f"{name} Faces Investigation by {regulator}",
         f"The {regulator} opened an investigation into {name}'s business practices, focusing on potential regulatory violations. {name} said it would cooperate fully with the inquiry.",
         (-0.65, -0.25)),
        (f"{name} Reaches ${amount}M Settlement with {regulator}",
         f"{name} agreed to pay ${amount} million to settle regulatory charges brought by the {regulator}. The company neither admitted nor denied the allegations.",
         (-0.5, -0.1)),
        (f"{name} Receives Regulatory Approval for {random.choice(['expansion', 'acquisition', 'new product'])}",
         f"{name} received regulatory approval, clearing a key hurdle for growth. The approval was widely expected but removes a source of uncertainty for investors.",
         (0.2, 0.6)),
    ]
    event = random.choice(events)
    sentiment = round(random.uniform(event[2][0], event[2][1]), 2)

    return {"ticker": ticker, "title": event[0], "content": event[1],
            "published_date": date.strftime("%Y-%m-%d"),
            "source": random.choice(SOURCES), "sentiment_score": sentiment}


def generate_sector_article(ticker: str, date: datetime) -> dict:
    name = TICKER_NAMES.get(ticker, ticker)
    sector = "Technology"
    for s, tickers in SECTORS.items():
        if ticker in tickers:
            sector = s.title()
            break

    sector_themes = {
        "Tech": ["AI revolution", "cloud computing growth", "cybersecurity spending",
                 "semiconductor demand", "SaaS adoption", "digital transformation"],
        "Finance": ["interest rate environment", "banking regulation", "fintech disruption",
                    "credit quality", "capital markets activity", "digital payments growth"],
        "Healthcare": ["drug pricing reform", "aging population trends", "biotech innovation",
                       "healthcare spending", "patent cliffs", "GLP-1 drug demand"],
        "Energy": ["oil price outlook", "energy transition", "OPEC production decisions",
                   "LNG demand growth", "carbon regulation", "renewable energy investment"],
        "Consumer": ["consumer spending trends", "e-commerce penetration", "inflation impact",
                     "supply chain normalization", "brand loyalty shifts", "value-seeking behavior"],
        "Industrial": ["defense spending growth", "infrastructure investment", "reshoring trends",
                       "supply chain modernization", "automation adoption", "aerospace recovery"],
    }

    theme = random.choice(sector_themes.get(sector, ["industry trends"]))
    positive = random.random() > 0.4

    if positive:
        title = f"{name} Positioned to Benefit from {theme.title()}"
        content = f"Analysts see {name} ({ticker}) as well-positioned to benefit from {theme}. The company's strategic investments and market position provide competitive advantages in this evolving landscape."
        sentiment = round(random.uniform(0.15, 0.65), 2)
    else:
        title = f"{name} Faces Challenges from {theme.title()}"
        content = f"{name} ({ticker}) faces headwinds from {theme}. Industry analysts note that the company needs to adapt its strategy to navigate the changing competitive dynamics."
        sentiment = round(random.uniform(-0.55, -0.05), 2)

    return {"ticker": ticker, "title": title, "content": content,
            "published_date": date.strftime("%Y-%m-%d"),
            "source": random.choice(SOURCES), "sentiment_score": sentiment}


# Article generator dispatch
GENERATORS = [
    (generate_earnings_article, 0.20),      # 20% earnings
    (generate_analyst_article, 0.25),        # 25% analyst actions
    (generate_market_article, 0.20),         # 20% market moves
    (generate_product_article, 0.10),        # 10% product/launches
    (generate_management_article, 0.05),     # 5% management
    (generate_dividend_article, 0.05),       # 5% dividends/buybacks
    (generate_regulatory_article, 0.05),     # 5% regulatory
    (generate_sector_article, 0.10),         # 10% sector themes
]


def pick_generator():
    r = random.random()
    cumulative = 0
    for gen, weight in GENERATORS:
        cumulative += weight
        if r <= cumulative:
            return gen
    return GENERATORS[0][0]


def main():
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    target_count = 10500  # ~10k+ articles
    articles_per_ticker = target_count // len(TICKERS)
    extra = target_count - articles_per_ticker * len(TICKERS)

    print("=" * 60)
    print("GENERATING NEWS HEADLINES DATASET")
    print(f"Target: {target_count}+ articles across {len(TICKERS)} tickers")
    print(f"~{articles_per_ticker} articles per ticker")
    print("=" * 60)

    all_articles = []
    seen_titles = set()

    for ticker in TICKERS:
        count = articles_per_ticker + (1 if extra > 0 else 0)
        if extra > 0:
            extra -= 1

        for _ in range(count):
            date = random_date(START_DATE, END_DATE)
            generator = pick_generator()
            article = generator(ticker, date)

            # Ensure unique titles
            title_hash = hashlib.md5(article["title"].encode()).hexdigest()
            attempts = 0
            while title_hash in seen_titles and attempts < 10:
                date = random_date(START_DATE, END_DATE)
                article = generator(ticker, date)
                title_hash = hashlib.md5(article["title"].encode()).hexdigest()
                attempts += 1

            seen_titles.add(title_hash)
            all_articles.append(article)

    # Sort by date
    all_articles.sort(key=lambda x: x["published_date"])

    # Write CSV
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["ticker", "title", "content",
                                                "published_date", "source",
                                                "sentiment_score"])
        writer.writeheader()
        writer.writerows(all_articles)

    print(f"\nGenerated {len(all_articles)} articles")
    print(f"Output: {os.path.abspath(OUTPUT_FILE)}")
    file_size = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)
    print(f"File size: {file_size:.1f} MB")

    # Quick stats
    from collections import Counter
    ticker_counts = Counter(a["ticker"] for a in all_articles)
    print(f"\nArticles per ticker: {min(ticker_counts.values())}-{max(ticker_counts.values())}")
    sentiments = [a["sentiment_score"] for a in all_articles]
    print(f"Sentiment range: {min(sentiments)} to {max(sentiments)}")
    print(f"Avg sentiment: {sum(sentiments)/len(sentiments):.3f}")
    dates = [a["published_date"] for a in all_articles]
    print(f"Date range: {min(dates)} to {max(dates)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
