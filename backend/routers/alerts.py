import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import Alert, Portfolio, User
from auth import get_current_user, check_portfolio_access
from services.cache import get_or_set, invalidate

UNREAD_COUNT_TTL = 60  # matches the sidebar's own 60s polling interval — caching
                       # to a shorter TTL than that would be pointless

logger = logging.getLogger(__name__)
router = APIRouter()


def ensure_table():
    Base.metadata.create_all(bind=engine, tables=[Alert.__table__])


def _scoped_portfolio_ids(db: Session, current_user: User) -> Optional[List[int]]:
    """None means no restriction (admin). Otherwise the list of portfolio_ids
    this user is allowed to see alerts for."""
    if current_user.role == "admin":
        return None
    return [
        pid for (pid,) in
        db.query(Portfolio.portfolio_id).filter(Portfolio.manager_id == current_user.user_id).all()
    ]


def _apply_scope(query, portfolio_id: Optional[int], current_user: User, db: Session):
    """Shared by every alerts endpoint: if portfolio_id is given, enforce ownership
    (403 if not owned/admin); otherwise narrow to the user's own portfolios."""
    if portfolio_id is not None:
        if not check_portfolio_access(db, current_user, portfolio_id):
            raise HTTPException(status_code=403, detail="Not authorized for this portfolio")
        return query.filter(Alert.portfolio_id == portfolio_id)
    allowed = _scoped_portfolio_ids(db, current_user)
    if allowed is not None:
        return query.filter(Alert.portfolio_id.in_(allowed))
    return query


@router.get("")
def get_alerts(
    portfolio_id: Optional[int] = Query(None),
    unread_only:  bool          = Query(False),
    limit:        int           = Query(50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = _apply_scope(db.query(Alert), portfolio_id, current_user, db).order_by(Alert.triggered_at.desc())
    if unread_only:
        q = q.filter(Alert.is_read == 0)
    rows = q.limit(limit).all()
    return [_to_dict(r) for r in rows]


def _unread_count_cache_key(portfolio_id: Optional[int], current_user: User) -> str:
    # portfolio_id given -> the underlying count is the same for anyone authorized
    # to see it, so key by portfolio, not by caller. No portfolio_id -> "all mine",
    # which genuinely differs per user (or per admin, if more than one exists later).
    if portfolio_id is not None:
        return f"alerts:unread:portfolio:{portfolio_id}"
    return f"alerts:unread:user:{current_user.user_id}"


@router.get("/unread-count")
def unread_count(
    portfolio_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Ownership check must happen before caching, uncached, every time — the
    # 403 for an unauthorized portfolio_id must never be skipped.
    if portfolio_id is not None and not check_portfolio_access(db, current_user, portfolio_id):
        raise HTTPException(status_code=403, detail="Not authorized for this portfolio")

    key = _unread_count_cache_key(portfolio_id, current_user)

    def _compute():
        q = _apply_scope(db.query(Alert).filter(Alert.is_read == 0), portfolio_id, current_user, db)
        return {"count": q.count()}

    return get_or_set(key, UNREAD_COUNT_TTL, _compute)


@router.patch("/{alert_id}/read")
def mark_read(alert_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    if alert.portfolio_id is not None and not check_portfolio_access(db, current_user, alert.portfolio_id):
        raise HTTPException(status_code=403, detail="Not authorized for this alert")
    alert.is_read = 1
    db.commit()
    invalidate(f"alerts:unread:user:{current_user.user_id}")
    if alert.portfolio_id is not None:
        invalidate(f"alerts:unread:portfolio:{alert.portfolio_id}")
    return {"status": "ok"}


@router.patch("/read-all")
def mark_all_read(
    portfolio_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if portfolio_id is not None and not check_portfolio_access(db, current_user, portfolio_id):
        raise HTTPException(status_code=403, detail="Not authorized for this portfolio")

    q = _apply_scope(db.query(Alert).filter(Alert.is_read == 0), portfolio_id, current_user, db)
    q.update({"is_read": 1}, synchronize_session=False)
    db.commit()

    invalidate(f"alerts:unread:user:{current_user.user_id}")
    if portfolio_id is not None:
        invalidate(f"alerts:unread:portfolio:{portfolio_id}")
    else:
        for pid in (_scoped_portfolio_ids(db, current_user) or []):
            invalidate(f"alerts:unread:portfolio:{pid}")
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
