"""
Shared Market_Events ingestion — used by both the one-time backfill
(backend/backfill_scripts/market_events_backfill.py) and the recurring
weekly job (backend/scripts/market_events_job.py). Each source function
takes a (db, tags, start, end, dry_run) window and returns a created count,
so both callers just differ in what date range and commit behavior they use.
"""
import json
import logging
import os
import re
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from models import MarketEvent, Security

logger = logging.getLogger(__name__)

# Market_Events.event_type CHECK constraint only allows these — see
# database_migration.md gotchas. M&A doesn't have its own bucket; the closest
# semantic fit is "sectoral" (company/sector-specific).
ALLOWED_EVENT_TYPES = {
    "natural_disaster", "earnings", "regulatory",
    "economic", "sectoral", "geopolitical", "policy",
}
ALLOWED_IMPACT_LEVELS = {"low", "medium", "high"}
ALLOWED_SENTIMENTS = {"positive", "negative", "neutral"}

# Headline keyword -> (event_type, sentiment). Checked in order; first match wins.
# Deliberately conservative — false negatives (missing an event) are fine for
# this feature, false positives (tagging unrelated news) are worse.
_KEYWORD_RULES = [
    (r"\b(acqui(re|res|sition)|merger|to be bought by|buyout|takeover)\b", "sectoral", "neutral"),
    (r"\b(downgrade[sd]?|cuts? (price target|rating)|lowers? (rating|outlook))\b", "sectoral", "negative"),
    (r"\b(cuts? (guidance|forecast)|lowers? guidance|slashes? outlook|guidance cut)\b", "sectoral", "negative"),
    (r"\b(raises? guidance|boosts? (guidance|forecast)|upgrade[sd]?)\b", "sectoral", "positive"),
]

# Finnhub's company-news feed for ticker X includes syndicated multi-stock
# roundup columns just because X gets a passing mention (e.g. "Intel
# downgraded, Marvell upgraded: Wall Street's top analyst calls" showing up
# under OXY's feed). These recurring templates are excluded outright — a
# roundup headline matching an M&A/downgrade keyword is a false positive
# almost by construction, not a real signal about the requested company.
_ROUNDUP_PATTERNS = [
    r"wall street'?s top analyst calls",
    r"\btop \d+ (upgrades?|downgrades?)\b",
    r"\banalyst calls\b",
]


def classify_headline(headline: str, ticker: str, company_name: Optional[str] = None) -> Optional[dict]:
    """Keyword-match a news headline into an event_type/sentiment pair, or None
    if it doesn't look like one of the categories we're tracking (M&A,
    guidance cuts, downgrades/upgrades) — or if it doesn't actually appear to
    be about `ticker` (Finnhub's per-ticker news feed includes syndicated
    multi-stock roundups that just mention the ticker in passing). Heuristic,
    not NLP — precision over recall by design."""
    text = headline.lower()

    if any(re.search(p, text) for p in _ROUNDUP_PATTERNS):
        return None

    # Require the ticker symbol or the company's distinctive name token to
    # actually appear in the headline, so a roundup mentioning three other
    # companies doesn't get attributed to this one.
    name_token = company_name.split()[0].lower() if company_name else None
    ticker_pattern = rf"\b{re.escape(ticker.lower())}\b"
    if not re.search(ticker_pattern, text) and not (name_token and name_token in text):
        return None

    for pattern, event_type, sentiment in _KEYWORD_RULES:
        if re.search(pattern, text):
            return {"event_type": event_type, "sentiment": sentiment}
    return None


def load_security_tags(db: Session) -> dict:
    """ticker_symbol -> {sector, country, name} for every tracked security,
    plus the full distinct sector list (used to tag broad/macro events so
    event_analyzer.py's plain list-membership exposure check — which does
    NOT understand alert_engine.py's "All Sectors"/"Global" sentinel — still
    matches every relevant holding instead of silently matching nothing)."""
    rows = db.query(Security.ticker_symbol, Security.sector, Security.country, Security.security_name).all()
    by_ticker = {r.ticker_symbol: {"sector": r.sector, "country": r.country, "name": r.security_name} for r in rows}
    all_sectors = sorted({r.sector for r in rows if r.sector})
    return {"by_ticker": by_ticker, "all_sectors": all_sectors}


def impact_from_surprise(surprise_pct: Optional[float]) -> str:
    if surprise_pct is None:
        return "medium"
    magnitude = abs(surprise_pct)
    if magnitude >= 10:
        return "high"
    if magnitude >= 3:
        return "medium"
    return "low"


def sentiment_from_surprise(surprise_pct: Optional[float]) -> str:
    if surprise_pct is None:
        return "neutral"
    if surprise_pct > 1:
        return "positive"
    if surprise_pct < -1:
        return "negative"
    return "neutral"


def reported_quarter_label(report_date: datetime) -> str:
    """Companies report earnings ~1-6 weeks after the quarter they're reporting
    ON closes — e.g. JPM reporting in mid-July is reporting Q2 (Apr-Jun)
    results, not Q3 (the calendar quarter the report date itself falls in).
    Approximate the reported quarter by shifting back one month before taking
    the calendar quarter, which is right for the vast majority of reporters."""
    month = report_date.month - 1
    year = report_date.year
    if month == 0:
        month, year = 12, year - 1
    quarter = (month - 1) // 3 + 1
    return f"Q{quarter} {year}"


def event_exists(db: Session, event_type: str, title: str, event_date: datetime) -> bool:
    """Dedup key: same type + title + calendar day. Makes reruns of either
    script safe (backfill re-run, or the weekly job's window overlapping a
    prior week) — no duplicate rows, no duplicate alerts downstream."""
    day_start = event_date.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start.replace(hour=23, minute=59, second=59)
    return db.query(MarketEvent.event_id).filter(
        MarketEvent.event_type == event_type,
        MarketEvent.event_title == title,
        MarketEvent.event_date >= day_start,
        MarketEvent.event_date <= day_end,
    ).first() is not None


def build_event(
    event_date: datetime,
    event_type: str,
    title: str,
    description: str,
    sectors: list,
    regions: list,
    impact_level: str,
    sentiment: str,
    source_url: Optional[str] = None,
) -> MarketEvent:
    assert event_type in ALLOWED_EVENT_TYPES, f"bad event_type: {event_type}"
    assert impact_level in ALLOWED_IMPACT_LEVELS, f"bad impact_level: {impact_level}"
    assert sentiment in ALLOWED_SENTIMENTS, f"bad sentiment: {sentiment}"
    return MarketEvent(
        event_date=event_date,
        event_type=event_type,
        event_title=title[:300],
        event_description=description,
        affected_sectors=json.dumps(sectors),
        affected_regions=json.dumps(regions),
        impact_level=impact_level,
        sentiment=sentiment,
        source_url=source_url,
    )


def _save(db: Session, ev: MarketEvent, dry_run: bool):
    if not dry_run:
        db.add(ev)
        db.commit()


# ── Earnings (yfinance — unlimited history, needs lxml) ─────────────────────

def ingest_earnings(db: Session, tags: dict, start: datetime, end: datetime, dry_run: bool) -> int:
    import yfinance as yf
    import pandas as pd

    by_ticker = tags["by_ticker"]
    created = 0
    for ticker, meta in by_ticker.items():
        try:
            df = yf.Ticker(ticker).get_earnings_dates(limit=16)
        except Exception as e:
            logger.warning(f"[MarketEvents/Earnings] {ticker}: fetch failed ({e})")
            continue
        if df is None or df.empty:
            continue

        for idx, row in df.iterrows():
            event_date = idx.to_pydatetime().replace(tzinfo=None)
            if not (start <= event_date <= end):
                continue

            eps_est = row.get("EPS Estimate")
            eps_actual = row.get("Reported EPS")
            surprise_pct = row.get("Surprise(%)")
            surprise_pct = float(surprise_pct) if pd.notna(surprise_pct) else None

            if pd.isna(eps_actual):
                continue  # future/unreported quarter within range — nothing to report yet

            title = f"{ticker} Earnings — {reported_quarter_label(event_date)}"
            if event_exists(db, "earnings", title, event_date):
                continue

            desc = f"{ticker} reported EPS of {eps_actual:.2f}"
            if pd.notna(eps_est):
                desc += f" vs. estimate of {eps_est:.2f}"
            if surprise_pct is not None:
                desc += f" ({surprise_pct:+.1f}% surprise)"
            desc += "."

            sector, country = meta.get("sector"), meta.get("country")
            ev = build_event(
                event_date=event_date, event_type="earnings", title=title, description=desc,
                sectors=[sector] if sector else [], regions=[country] if country else [],
                impact_level=impact_from_surprise(surprise_pct),
                sentiment=sentiment_from_surprise(surprise_pct),
            )
            _save(db, ev, dry_run)
            created += 1
            logger.info(f"[MarketEvents/Earnings] {'[dry-run] ' if dry_run else ''}{title}")

    return created


# ── Macro prints (FRED — unlimited history) ──────────────────────────────────

MACRO_SERIES = {
    "CPIAUCSL": ("US CPI (All Items)", "economic"),
    "PAYEMS":   ("US Nonfarm Payrolls", "economic"),
}


def ingest_macro(db: Session, tags: dict, start: datetime, end: datetime, dry_run: bool) -> int:
    from fredapi import Fred

    fred_key = os.environ.get("FRED_API_KEY")
    if not fred_key:
        logger.warning("[MarketEvents/Macro] FRED_API_KEY not set — skipping")
        return 0
    fred = Fred(api_key=fred_key)
    all_sectors = tags["all_sectors"]
    created = 0

    for series_id, (name, event_type) in MACRO_SERIES.items():
        try:
            raw = fred.get_series(series_id, observation_start=start.date(), observation_end=end.date())
        except Exception as e:
            logger.warning(f"[MarketEvents/Macro] {series_id}: fetch failed ({e})")
            continue

        prev_value = None
        for date, value in raw.items():
            event_date = date.to_pydatetime()
            if value is None or (prev_value is not None and value == prev_value):
                prev_value = value
                continue

            change = f" ({'+' if prev_value is not None and value > prev_value else ''}{value - prev_value:.1f} vs. prior)" if prev_value is not None else ""
            title = f"{name} — {event_date.strftime('%B %Y')}"
            if event_exists(db, event_type, title, event_date):
                prev_value = value
                continue

            ev = build_event(
                event_date=event_date, event_type=event_type, title=title,
                description=f"{name} released at {value:.1f}{change}.",
                sectors=all_sectors, regions=["United States"],
                impact_level="medium", sentiment="neutral",
            )
            _save(db, ev, dry_run)
            created += 1
            logger.info(f"[MarketEvents/Macro] {'[dry-run] ' if dry_run else ''}{title}")
            prev_value = value

    return created


# ── FOMC decisions (FRED daily target-rate series) ──────────────────────────

def ingest_fomc(db: Session, tags: dict, start: datetime, end: datetime, dry_run: bool) -> int:
    from fredapi import Fred

    fred_key = os.environ.get("FRED_API_KEY")
    if not fred_key:
        logger.warning("[MarketEvents/FOMC] FRED_API_KEY not set — skipping")
        return 0
    fred = Fred(api_key=fred_key)
    all_sectors = tags["all_sectors"]
    created = 0

    try:
        raw = fred.get_series("DFEDTARU", observation_start=start.date(), observation_end=end.date())
    except Exception as e:
        logger.warning(f"[MarketEvents/FOMC] DFEDTARU fetch failed ({e})")
        return 0

    prev_value = None
    for date, value in raw.items():
        event_date = date.to_pydatetime()
        if value is None:
            continue
        if prev_value is not None and value != prev_value:
            direction = "raised" if value > prev_value else "cut"
            title = f"FOMC Rate Decision — {direction.capitalize()} to {value:.2f}%"
            if not event_exists(db, "policy", title, event_date):
                ev = build_event(
                    event_date=event_date, event_type="policy", title=title,
                    description=f"Federal Reserve {direction} the target rate (upper bound) from {prev_value:.2f}% to {value:.2f}%.",
                    sectors=all_sectors, regions=["United States"],
                    impact_level="high", sentiment="negative" if direction == "raised" else "positive",
                )
                _save(db, ev, dry_run)
                created += 1
                logger.info(f"[MarketEvents/FOMC] {'[dry-run] ' if dry_run else ''}{title}")
        prev_value = value

    return created


# ── M&A / guidance cuts / downgrades (Finnhub company-news, keyword-matched) ─
# Free tier caps lookback to ~2-3 days regardless of `start` passed in — fine
# for the weekly job's window, makes the one-time backfill thin by nature.

def ingest_news_keywords(db: Session, tags: dict, start: datetime, end: datetime, dry_run: bool) -> int:
    import time as _time
    import requests

    finnhub_key = os.environ.get("FINNHUB_API_KEY")
    if not finnhub_key:
        logger.warning("[MarketEvents/News] FINNHUB_API_KEY not set — skipping")
        return 0

    by_ticker = tags["by_ticker"]
    created = 0
    for ticker, meta in by_ticker.items():
        # Finnhub free tier is 60 calls/min; 135 tracked tickers with no
        # throttling risks a 429 partway through and silently losing
        # coverage on whichever tickers come after it in iteration order.
        _time.sleep(1.1)
        try:
            r = requests.get(
                "https://finnhub.io/api/v1/company-news",
                params={"symbol": ticker, "from": start.date().isoformat(), "to": end.date().isoformat(), "token": finnhub_key},
                timeout=15,
            )
            r.raise_for_status()
            articles = r.json()
        except Exception as e:
            logger.warning(f"[MarketEvents/News] {ticker}: fetch failed ({e})")
            continue

        for article in articles:
            headline = article.get("headline", "")
            classified = classify_headline(headline, ticker, meta.get("name"))
            if not classified:
                continue

            event_date = datetime.utcfromtimestamp(article["datetime"])
            if not (start <= event_date <= end):
                continue

            title = f"{ticker}: {headline}"[:300]
            if event_exists(db, classified["event_type"], title, event_date):
                continue

            sector, country = meta.get("sector"), meta.get("country")
            ev = build_event(
                event_date=event_date, event_type=classified["event_type"], title=title,
                description=article.get("summary") or headline,
                sectors=[sector] if sector else [], regions=[country] if country else [],
                impact_level="medium", sentiment=classified["sentiment"],
                source_url=article.get("url"),
            )
            _save(db, ev, dry_run)
            created += 1
            logger.info(f"[MarketEvents/News] {'[dry-run] ' if dry_run else ''}{title}")

    return created


def ingest_all(db: Session, start: datetime, end: datetime, dry_run: bool = False) -> dict:
    """Run every source over [start, end]. Returns a dict of per-source counts."""
    tags = load_security_tags(db)
    logger.info(f"[MarketEvents] {len(tags['by_ticker'])} tracked securities, {len(tags['all_sectors'])} distinct sectors")
    return {
        "earnings": ingest_earnings(db, tags, start, end, dry_run),
        "macro":    ingest_macro(db, tags, start, end, dry_run),
        "fomc":     ingest_fomc(db, tags, start, end, dry_run),
        "news":     ingest_news_keywords(db, tags, start, end, dry_run),
    }
