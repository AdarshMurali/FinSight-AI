"""
ONE-TIME backfill for Market_Events — NOT part of the recurring pipeline,
NOT wired into EventBridge/cron. See backend/scripts/market_events_job.py
for the recurring weekly job.

Populates historical 2026 events from the free-tier sources that actually
have that history:
  - Earnings: yfinance (unlimited history)
  - Macro (CPI, jobs) + FOMC decisions: FRED (unlimited history)
  - M&A / guidance cuts / downgrades: Finnhub company-news, keyword-matched.
    Finnhub's free tier caps company-news lookback to ~2-3 days regardless
    of --start-date, so this part of the backfill is necessarily thin —
    accepted tradeoff, see plan.md "Live Market Events Feed".

Run by hand on the backend EC2 (never scheduled):

    cd backend
    USE_AWS_SECRETS=true backendvenv/bin/python backfill_scripts/market_events_backfill.py \\
        --start-date 2026-01-01 --end-date 2026-07-16 [--dry-run]

Safe to re-run — every insert is deduped against existing rows
(same event_type + title + calendar day).
"""
import argparse
import logging
import os
import sys
import time
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

_START_TIME = time.time()
logger.info("===== MarketEventsBackfill RUN STARTED =====")

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from database import SessionLocal, engine
    from services.market_event_ingest import ingest_all
except Exception:
    logger.exception("MarketEventsBackfill RUN FAILED during import")
    logger.info(f"===== MarketEventsBackfill RUN ENDED (FAILED) — {time.time() - _START_TIME:.1f}s =====")
    sys.exit(1)

DB_WAKE_RETRIES = 5
DB_WAKE_DELAY = 30


def wait_for_db():
    from sqlalchemy import text
    for attempt in range(1, DB_WAKE_RETRIES + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info(f"[Backfill] DB ready (attempt {attempt})")
            return
        except Exception as e:
            if attempt < DB_WAKE_RETRIES:
                logger.warning(f"[Backfill] DB ping failed ({attempt}/{DB_WAKE_RETRIES}): {e}. Retrying in {DB_WAKE_DELAY}s...")
                time.sleep(DB_WAKE_DELAY)
            else:
                logger.error("[Backfill] DB unreachable. Aborting.")
                raise


def run(start: datetime, end: datetime, dry_run: bool):
    wait_for_db()
    db = SessionLocal()
    try:
        counts = ingest_all(db, start, end, dry_run)
        logger.info(
            f"[Backfill] Complete{' (DRY RUN — nothing written)' if dry_run else ''} — "
            f"{counts['earnings']} earnings, {counts['macro']} macro, "
            f"{counts['fomc']} FOMC, {counts['news']} news-keyword events"
        )
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and log, but don't write to the DB")
    args = parser.parse_args()

    start_dt = datetime.strptime(args.start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(args.end_date, "%Y-%m-%d") + timedelta(hours=23, minutes=59)

    try:
        run(start_dt, end_dt, args.dry_run)
    except Exception:
        logger.exception("MarketEventsBackfill RUN FAILED (uncaught exception)")
        logger.info(f"===== MarketEventsBackfill RUN ENDED (FAILED) — {time.time() - _START_TIME:.1f}s =====")
        sys.exit(1)
    else:
        logger.info(f"===== MarketEventsBackfill RUN ENDED (OK) — {time.time() - _START_TIME:.1f}s =====")
