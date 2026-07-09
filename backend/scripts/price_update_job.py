"""
Standalone daily price refresh job.

Securities.current_price / Positions.market_value / Portfolios.total_value are
only ever set once at synthetic data generation and never refresh — this job
fixes that. Intended to run right before risk_job.py in the daily schedule.

Schedule via:
  - AWS EventBridge + SSM Run Command (production), same pattern as risk_job.py
  - Manual: python scripts/price_update_job.py  (run from backend/)
"""
import sys
import os
import logging
import time
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

_START_TIME = time.time()
logger.info("===== PriceUpdateJob RUN STARTED =====")

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import yfinance as yf
    from database import SessionLocal, engine
    from models import Security, Position, Portfolio
except Exception:
    logger.exception("PriceUpdateJob RUN FAILED during import")
    logger.info(f"===== PriceUpdateJob RUN ENDED (FAILED) — {time.time() - _START_TIME:.1f}s =====")
    sys.exit(1)

DB_WAKE_RETRIES = 5
DB_WAKE_DELAY = 30  # seconds between retries (Azure SQL cold start takes ~20-40s)


def wait_for_db():
    """Retry the initial DB ping to handle Azure SQL cold-start timeouts."""
    from sqlalchemy import text
    for attempt in range(1, DB_WAKE_RETRIES + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info(f"[PriceUpdateJob] DB ready (attempt {attempt})")
            return
        except Exception as e:
            if attempt < DB_WAKE_RETRIES:
                logger.warning(
                    f"[PriceUpdateJob] DB ping failed (attempt {attempt}/{DB_WAKE_RETRIES}): {e}. "
                    f"Retrying in {DB_WAKE_DELAY}s..."
                )
                time.sleep(DB_WAKE_DELAY)
            else:
                logger.error(f"[PriceUpdateJob] DB unreachable after {DB_WAKE_RETRIES} attempts. Aborting.")
                raise


def fetch_latest_prices(db) -> tuple[dict, int, int]:
    """Fetch latest price per ticker via yfinance and update Securities.current_price. Returns {security_id: price}, success, failed."""
    securities = db.query(Security.security_id, Security.ticker_symbol).all()
    prices: dict[int, float] = {}
    success, failed = 0, 0

    for sec_id, ticker in securities:
        try:
            info = yf.Ticker(ticker).fast_info
            price = info.get("lastPrice") or info.get("last_price")
            if price is None:
                raise ValueError("no lastPrice in fast_info")
            prices[sec_id] = float(price)
            success += 1
        except Exception as e:
            logger.warning(f"[PriceUpdateJob] {ticker} (security_id={sec_id}) price fetch FAILED: {e}")
            failed += 1

    for sec_id, price in prices.items():
        db.query(Security).filter(Security.security_id == sec_id).update({"current_price": price})
    db.commit()

    logger.info(f"[PriceUpdateJob] Securities.current_price: {success} updated, {failed} failed")
    return prices, success, failed


def refresh_positions_and_portfolios(db, prices: dict) -> tuple[int, int]:
    """Recompute Positions.market_value from fresh prices, then roll up Portfolios.total_value + weights."""
    positions = db.query(Position).all()
    for pos in positions:
        price = prices.get(pos.security_id)
        if price is None:
            continue  # leave stale value if this ticker's fetch failed
        pos.current_price = price
        pos.market_value = float(pos.quantity) * price
        pos.last_updated = datetime.utcnow()
    db.commit()

    # weight is DECIMAL(5,4) in the actual DB (models.py incorrectly declares DECIMAL(5,2)) —
    # stored as a FRACTION of portfolio value (0.28 = 28%), not a percentage. Max magnitude
    # 9.9999. Clamp defensively: extreme short concentration or near-zero total_value could
    # otherwise overflow the column.
    WEIGHT_CLAMP = 9.9999

    portfolio_ids = [pid for (pid,) in db.query(Portfolio.portfolio_id).all()]
    updated, failed = 0, 0
    for portfolio_id in portfolio_ids:
        try:
            portfolio = db.query(Portfolio).filter(Portfolio.portfolio_id == portfolio_id).one()
            portfolio_positions = (
                db.query(Position).filter(Position.portfolio_id == portfolio_id).all()
            )
            total_position_value = sum(float(p.market_value or 0) for p in portfolio_positions)
            total_value = total_position_value + float(portfolio.cash_balance or 0)
            portfolio.total_value = total_value

            for pos in portfolio_positions:
                raw_weight = (
                    round(float(pos.market_value or 0) / total_value, 4)
                    if total_value else 0
                )
                clamped = max(min(raw_weight, WEIGHT_CLAMP), -WEIGHT_CLAMP)
                if clamped != raw_weight:
                    logger.warning(
                        f"[PriceUpdateJob] Position {pos.position_id} weight {raw_weight} "
                        f"clamped to {clamped} (portfolio {portfolio_id})"
                    )
                pos.weight = clamped
            db.commit()
            updated += 1
        except Exception as e:
            db.rollback()
            logger.error(f"[PriceUpdateJob] Portfolio {portfolio_id} rollup FAILED: {e}")
            failed += 1

    logger.info(f"[PriceUpdateJob] Portfolios: {updated} rolled up, {failed} failed")
    return updated, failed


def run():
    wait_for_db()

    with SessionLocal() as db:
        prices, price_ok, price_failed = fetch_latest_prices(db)
        port_ok, port_failed = refresh_positions_and_portfolios(db, prices)

    logger.info(
        f"[PriceUpdateJob] Complete — prices: {price_ok} ok / {price_failed} failed, "
        f"portfolios: {port_ok} ok / {port_failed} failed"
    )


if __name__ == "__main__":
    try:
        run()
    except Exception:
        logger.exception("PriceUpdateJob RUN FAILED (uncaught exception)")
        logger.info(f"===== PriceUpdateJob RUN ENDED (FAILED) — {time.time() - _START_TIME:.1f}s =====")
        sys.exit(1)
    else:
        logger.info(f"===== PriceUpdateJob RUN ENDED (OK) — {time.time() - _START_TIME:.1f}s =====")
