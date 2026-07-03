import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import Alert

logger = logging.getLogger(__name__)
router = APIRouter()


def ensure_table():
    Base.metadata.create_all(bind=engine, tables=[Alert.__table__])


@router.get("")
def get_alerts(
    portfolio_id: Optional[int] = Query(None),
    unread_only:  bool          = Query(False),
    limit:        int           = Query(50),
    db: Session = Depends(get_db),
):
    q = db.query(Alert).order_by(Alert.triggered_at.desc())
    if portfolio_id is not None:
        q = q.filter(Alert.portfolio_id == portfolio_id)
    if unread_only:
        q = q.filter(Alert.is_read == 0)
    rows = q.limit(limit).all()
    return [_to_dict(r) for r in rows]


@router.get("/unread-count")
def unread_count(
    portfolio_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Alert).filter(Alert.is_read == 0)
    if portfolio_id is not None:
        q = q.filter(Alert.portfolio_id == portfolio_id)
    return {"count": q.count()}


@router.patch("/{alert_id}/read")
def mark_read(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_read = 1
    db.commit()
    return {"status": "ok"}


@router.patch("/read-all")
def mark_all_read(
    portfolio_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Alert).filter(Alert.is_read == 0)
    if portfolio_id is not None:
        q = q.filter(Alert.portfolio_id == portfolio_id)
    q.update({"is_read": 1})
    db.commit()
    return {"status": "ok"}


def _to_dict(a: Alert) -> dict:
    return {
        "alert_id":     a.alert_id,
        "portfolio_id": a.portfolio_id,
        "alert_type":   a.alert_type,
        "severity":     a.severity,
        "title":        a.title,
        "message":      a.message,
        "is_read":      bool(a.is_read),
        "triggered_at": a.triggered_at.isoformat() if a.triggered_at else None,
    }
