"""
Standalone daily risk computation job.

Schedule via:
  - AWS EventBridge + SSM Run Command (production)
  - EC2 crontab (simple alternative)
  - Manual: python scripts/risk_job.py  (run from backend/)
"""
import sys
import os
import json
import logging
import time
from datetime import date, datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal, engine, Base
from models import Portfolio, RiskMetric, Alert
from services.risk_analytics import compute_all
from services.alert_engine import run_alerts_for_portfolio

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

DB_WAKE_RETRIES = 5
DB_WAKE_DELAY = 30  # seconds between retries (Azure SQL cold start takes ~20-40s)


def wait_for_db():
    """Retry the initial DB ping to handle Azure SQL cold-start timeouts."""
    from sqlalchemy import text
    for attempt in range(1, DB_WAKE_RETRIES + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info(f"[RiskJob] DB ready (attempt {attempt})")
            return
        except Exception as e:
            if attempt < DB_WAKE_RETRIES:
                logger.warning(
                    f"[RiskJob] DB ping failed (attempt {attempt}/{DB_WAKE_RETRIES}): {e}. "
                    f"Retrying in {DB_WAKE_DELAY}s..."
                )
                time.sleep(DB_WAKE_DELAY)
            else:
                logger.error(f"[RiskJob] DB unreachable after {DB_WAKE_RETRIES} attempts. Aborting.")
                raise


def ensure_table():
    Base.metadata.create_all(bind=engine, tables=[RiskMetric.__table__, Alert.__table__])


def save_result(db, portfolio_id: int, result: dict):
    row = RiskMetric(
        portfolio_id=portfolio_id,
        computed_at=datetime.utcnow(),
        var_data=json.dumps(result.get("var", {})),
        stress_data=json.dumps(result.get("stress_tests", [])),
        factor_data=json.dumps(result.get("factor_exposure", {})),
        price_date=date.today(),
        status="completed",
    )
    db.add(row)
    db.commit()


def run():
    wait_for_db()
    ensure_table()

    with SessionLocal() as db:
        portfolios = db.query(Portfolio.portfolio_id, Portfolio.portfolio_name).all()

    logger.info(f"[RiskJob] Starting — {len(portfolios)} portfolios")

    success, failed, total_alerts = 0, 0, 0
    for pid, pname in portfolios:
        db = SessionLocal()
        try:
            result = compute_all(db, pid)
            save_result(db, pid, result)
            n = run_alerts_for_portfolio(db, pid, pname)
            total_alerts += n
            logger.info(f"[RiskJob] Portfolio {pid} done — {n} alert(s) generated")
            success += 1
        except Exception as e:
            logger.error(f"[RiskJob] Portfolio {pid} FAILED: {e}")
            failed += 1
        finally:
            db.close()

    logger.info(f"[RiskJob] Complete — {success} succeeded, {failed} failed, {total_alerts} alerts generated")


if __name__ == "__main__":
    run()
