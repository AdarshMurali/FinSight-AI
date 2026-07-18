"""
Recurring weekly Market_Events refresh job — keeps the table current going
forward (earnings, macro/CPI/jobs, FOMC decisions, M&A/guidance-cuts/downgrades,
geopolitical/regulatory/policy news from Finnhub's general category).

Scheduled via AWS EventBridge + SSM Run Command on the backend EC2
(13.206.225.80, always-on), same pattern as risk_job.py / price_update_job.py,
once a week. Looks back WINDOW_DAYS to give a safety margin over the 7-day
cadence in case a run is skipped — dedup in market_event_ingest.event_exists
makes the overlap safe.

Manual run:
    cd backend
    USE_AWS_SECRETS=true backendvenv/bin/python scripts/market_events_job.py
"""
import logging
import os
import sys
import time
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

_START_TIME = time.time()
logger.info("===== MarketEventsJob RUN STARTED =====")

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from database import SessionLocal, engine
    from services.market_event_ingest import ingest_all
except Exception:
    logger.exception("MarketEventsJob RUN FAILED during import")
    logger.info(f"===== MarketEventsJob RUN ENDED (FAILED) — {time.time() - _START_TIME:.1f}s =====")
    sys.exit(1)

DB_WAKE_RETRIES = 5
DB_WAKE_DELAY = 30
WINDOW_DAYS = 10  # > 7-day cadence, gives overlap margin; dedup handles the overlap


def wait_for_db():
    from sqlalchemy import text
    for attempt in range(1, DB_WAKE_RETRIES + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info(f"[MarketEventsJob] DB ready (attempt {attempt})")
            return
        except Exception as e:
            if attempt < DB_WAKE_RETRIES:
                logger.warning(f"[MarketEventsJob] DB ping failed ({attempt}/{DB_WAKE_RETRIES}): {e}. Retrying in {DB_WAKE_DELAY}s...")
                time.sleep(DB_WAKE_DELAY)
            else:
                logger.error("[MarketEventsJob] DB unreachable. Aborting.")
                raise


def run():
    wait_for_db()
    end = datetime.utcnow()
    start = end - timedelta(days=WINDOW_DAYS)

    db = SessionLocal()
    try:
        counts = ingest_all(db, start, end, dry_run=False)
        logger.info(
            f"[MarketEventsJob] Complete — window {start.date()}..{end.date()} — "
            f"{counts['earnings']} earnings, {counts['macro']} macro, "
            f"{counts['fomc']} FOMC, {counts['news']} news-keyword events, "
            f"{counts['general']} geopolitical/regulatory/policy events"
        )
    finally:
        db.close()


if __name__ == "__main__":
    try:
        run()
    except Exception:
        logger.exception("MarketEventsJob RUN FAILED (uncaught exception)")
        logger.info(f"===== MarketEventsJob RUN ENDED (FAILED) — {time.time() - _START_TIME:.1f}s =====")
        sys.exit(1)
    else:
        logger.info(f"===== MarketEventsJob RUN ENDED (OK) — {time.time() - _START_TIME:.1f}s =====")
