"""
ONE-TIME cleanup for duplicate Market_Events rows created before the two
dedup fixes in market_event_ingest.py (2026-07-16):

  1. Same article synidcated across multiple tickers' Finnhub company-news
     feeds (e.g. a PayPal/Stripe article naming Visa, Mastercard, and
     American Express created 3 near-identical rows). Cleaned up by
     (event_type, source_url) — keeps the earliest event_id per group.

  2. Same ongoing story re-reported by different outlets over a few days
     (e.g. Uber/Delivery Hero acquisition talks covered ~6 times).
     Cleaned up per (ticker, event_type="sectoral") with a 5-day rolling
     window — keeps the first event in each window, drops the rest.

NOT wired into any schedule — run by hand, once, after deploying the
ingestion fixes:

    cd backend
    USE_AWS_SECRETS=true backendvenv/bin/python backfill_scripts/market_events_dedup_cleanup.py [--dry-run]
"""
import argparse
import logging
import os
import re
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

_START_TIME = time.time()
logger.info("===== MarketEventsDedupCleanup RUN STARTED =====")

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from database import SessionLocal, engine
    from models import MarketEvent
    from sqlalchemy import func
except Exception:
    logger.exception("MarketEventsDedupCleanup RUN FAILED during import")
    logger.info(f"===== MarketEventsDedupCleanup RUN ENDED (FAILED) — {time.time() - _START_TIME:.1f}s =====")
    sys.exit(1)

DB_WAKE_RETRIES = 5
DB_WAKE_DELAY = 30
TICKER_PREFIX = re.compile(r"^([A-Za-z.\-=]+):\s")


def wait_for_db():
    from sqlalchemy import text
    for attempt in range(1, DB_WAKE_RETRIES + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info(f"[Cleanup] DB ready (attempt {attempt})")
            return
        except Exception as e:
            if attempt < DB_WAKE_RETRIES:
                logger.warning(f"[Cleanup] DB ping failed ({attempt}/{DB_WAKE_RETRIES}): {e}. Retrying in {DB_WAKE_DELAY}s...")
                time.sleep(DB_WAKE_DELAY)
            else:
                logger.error("[Cleanup] DB unreachable. Aborting.")
                raise


def cleanup_source_url_duplicates(db, dry_run: bool) -> int:
    dupe_groups = (
        db.query(MarketEvent.event_type, MarketEvent.source_url, func.count().label("cnt"))
        .filter(MarketEvent.source_url.isnot(None))
        .group_by(MarketEvent.event_type, MarketEvent.source_url)
        .having(func.count() > 1)
        .all()
    )
    deleted = 0
    for event_type, source_url, _cnt in dupe_groups:
        rows = (
            db.query(MarketEvent)
            .filter(MarketEvent.event_type == event_type, MarketEvent.source_url == source_url)
            .order_by(MarketEvent.event_id.asc())
            .all()
        )
        keep, drop = rows[0], rows[1:]
        for r in drop:
            logger.info(f"[Cleanup/URL] {'[dry-run] ' if dry_run else ''}delete #{r.event_id}: {r.event_title[:80]} (dup of #{keep.event_id})")
            if not dry_run:
                db.delete(r)
        deleted += len(drop)
    if not dry_run and deleted:
        db.commit()
    return deleted


def cleanup_ticker_window_duplicates(db, dry_run: bool, window_days: int = 5) -> int:
    rows = (
        db.query(MarketEvent)
        .filter(MarketEvent.event_type == "sectoral")
        .order_by(MarketEvent.event_date.asc())
        .all()
    )
    by_ticker: dict = {}
    for r in rows:
        m = TICKER_PREFIX.match(r.event_title or "")
        if not m:
            continue
        by_ticker.setdefault(m.group(1), []).append(r)

    deleted = 0
    for ticker, group in by_ticker.items():
        group.sort(key=lambda r: r.event_date)
        window_anchor = None
        for r in group:
            if window_anchor is None or (r.event_date - window_anchor).days > window_days:
                window_anchor = r.event_date
                continue  # first in a new window — kept
            logger.info(f"[Cleanup/Window] {'[dry-run] ' if dry_run else ''}delete #{r.event_id}: {r.event_title[:80]} (within {window_days}d of prior {ticker} event)")
            if not dry_run:
                db.delete(r)
            deleted += 1
    if not dry_run and deleted:
        db.commit()
    return deleted


def run(dry_run: bool):
    wait_for_db()
    db = SessionLocal()
    try:
        n_url = cleanup_source_url_duplicates(db, dry_run)
        n_window = cleanup_ticker_window_duplicates(db, dry_run)
        logger.info(
            f"[Cleanup] Complete{' (DRY RUN — nothing deleted)' if dry_run else ''} — "
            f"{n_url} source-url duplicates, {n_window} same-saga duplicates"
        )
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="List what would be deleted, but don't delete")
    args = parser.parse_args()

    try:
        run(args.dry_run)
    except Exception:
        logger.exception("MarketEventsDedupCleanup RUN FAILED (uncaught exception)")
        logger.info(f"===== MarketEventsDedupCleanup RUN ENDED (FAILED) — {time.time() - _START_TIME:.1f}s =====")
        sys.exit(1)
    else:
        logger.info(f"===== MarketEventsDedupCleanup RUN ENDED (OK) — {time.time() - _START_TIME:.1f}s =====")
