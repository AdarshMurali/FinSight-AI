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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

_START_TIME = time.time()
logger.info("===== RiskJob RUN STARTED =====")
logger.info("[CICD-DEPLOY-VERIFY-20260717] risk_job.py code-refresh-via-CD test marker")

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from database import SessionLocal, engine, Base
    from models import Portfolio, RiskMetric, Alert
    from services.risk_analytics import compute_all
    from services.alert_engine import run_alerts_for_portfolio, run_event_alerts, generate_ai_alert_for_portfolio
    from services.llm_service import LLMService
except Exception:
    logger.exception("RiskJob RUN FAILED during import")
    logger.info(f"===== RiskJob RUN ENDED (FAILED) — {time.time() - _START_TIME:.1f}s =====")
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
        parametric_data=json.dumps(result.get("parametric_shocks", [])),
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

    success, failed = 0, 0
    total_new, total_bumped, total_resolved = 0, 0, 0
    ai_llm = LLMService()
    ai_alert_count = 0
    for pid, pname in portfolios:
        db = SessionLocal()
        try:
            result = compute_all(db, pid)
            save_result(db, pid, result)
            counts = run_alerts_for_portfolio(db, pid, pname)
            total_new += counts["new"]
            total_bumped += counts["bumped"]
            total_resolved += counts["resolved"]

            ai_alert = generate_ai_alert_for_portfolio(db, pid, pname, llm=ai_llm)
            if ai_alert:
                ai_alert_count += 1

            logger.info(
                f"[RiskJob] Portfolio {pid} done — {counts['new']} new, {counts['bumped']} bumped, "
                f"{counts['resolved']} resolved threshold alert(s), {1 if ai_alert else 0} AI alert(s)"
            )
            success += 1
        except Exception as e:
            logger.error(f"[RiskJob] Portfolio {pid} FAILED: {e}")
            failed += 1
        finally:
            db.close()

    ai_usage = ai_llm.get_usage_stats()
    logger.info(
        f"[RiskJob] AI alerts — {ai_alert_count} generated, "
        f"${ai_usage['total_cost_usd']:.4f} spent across {ai_usage['calls']} calls"
    )

    event_alert_count = 0
    db = SessionLocal()
    try:
        event_alert_count = run_event_alerts(db)
        logger.info(f"[RiskJob] Event alerts — {event_alert_count} generated")
    except Exception as e:
        logger.error(f"[RiskJob] Event alert scan FAILED: {e}")
    finally:
        db.close()

    logger.info(
        f"[RiskJob] Complete — {success} succeeded, {failed} failed, "
        f"{total_new} new threshold alerts, {total_bumped} bumped, {total_resolved} resolved, "
        f"{ai_alert_count} AI alerts, {event_alert_count} event alerts"
    )


if __name__ == "__main__":
    try:
        run()
    except Exception:
        logger.exception("RiskJob RUN FAILED (uncaught exception)")
        logger.info(f"===== RiskJob RUN ENDED (FAILED) — {time.time() - _START_TIME:.1f}s =====")
        sys.exit(1)
    else:
        logger.info(f"===== RiskJob RUN ENDED (OK) — {time.time() - _START_TIME:.1f}s =====")
