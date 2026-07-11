import json
import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import Base, get_db, engine
from models import RiskMetric, Portfolio
from auth import require_portfolio_access
from services.risk_analytics import compute_all

logger = logging.getLogger(__name__)
router = APIRouter()


def ensure_table():
    Base.metadata.create_all(bind=engine, tables=[RiskMetric.__table__])


def _save(db: Session, portfolio_id: int, result: Dict[str, Any]):
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


def _latest(db: Session, portfolio_id: int):
    return (
        db.query(RiskMetric)
        .filter(RiskMetric.portfolio_id == portfolio_id)
        .order_by(RiskMetric.computed_at.desc())
        .first()
    )


def _run_and_save(portfolio_id: int):
    from database import SessionLocal
    db = SessionLocal()
    try:
        result = compute_all(db, portfolio_id)
        _save(db, portfolio_id, result)
        logger.info(f"[Risk] Portfolio {portfolio_id} metrics saved")
    except Exception as e:
        logger.error(f"[Risk] Portfolio {portfolio_id} computation failed: {e}")
    finally:
        db.close()


@router.get("/{portfolio_id}")
def get_risk_metrics(portfolio: Portfolio = Depends(require_portfolio_access), db: Session = Depends(get_db)):
    row = _latest(db, portfolio.portfolio_id)
    if not row:
        return {"status": "not_computed"}
    return {
        "status":        "ok",
        "portfolio_id":  portfolio.portfolio_id,
        "computed_at":   row.computed_at.isoformat(),
        "price_date":    str(row.price_date) if row.price_date else None,
        "var":           json.loads(row.var_data or "{}"),
        "stress_tests":  json.loads(row.stress_data or "[]"),
        "factor_exposure": json.loads(row.factor_data or "{}"),
    }


@router.get("/{portfolio_id}/history")
def get_risk_history(
    days: int = Query(default=30, ge=1, le=365),
    portfolio: Portfolio = Depends(require_portfolio_access),
    db: Session = Depends(get_db),
):
    cutoff = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.query(RiskMetric)
        .filter(
            RiskMetric.portfolio_id == portfolio.portfolio_id,
            RiskMetric.computed_at >= cutoff,
        )
        .order_by(RiskMetric.computed_at.asc())
        .all()
    )
    result = []
    for row in rows:
        try:
            var_json    = json.loads(row.var_data or "{}")
            stress_json = json.loads(row.stress_data or "[]")
            hist        = var_json.get("historical", {})
            worst       = min((s.get("portfolio_impact_pct", 0) for s in stress_json), default=None)
        except Exception:
            continue
        result.append({
            "computed_at":      row.computed_at.isoformat(),
            "price_date":       str(row.price_date) if row.price_date else None,
            "var_95_1d_pct":    hist.get("var_95_1d_pct"),
            "var_99_1d_pct":    hist.get("var_99_1d_pct"),
            "stress_worst_pct": worst,
        })
    return result


@router.post("/{portfolio_id}/refresh")
def refresh_risk_metrics(
    background_tasks: BackgroundTasks,
    portfolio: Portfolio = Depends(require_portfolio_access),
    db: Session = Depends(get_db),
):
    background_tasks.add_task(_run_and_save, portfolio.portfolio_id)
    return {"status": "computing", "portfolio_id": portfolio.portfolio_id}
