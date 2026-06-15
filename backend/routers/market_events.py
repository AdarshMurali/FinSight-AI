from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from typing import List, Optional
from datetime import date, datetime

from database import get_db
from models import MarketEvent, Position, Security, Portfolio, PositionChangeLog
from schemas import MarketEventResponse, PortfolioResponse

router = APIRouter()


@router.get("/", response_model=List[MarketEventResponse])
def get_market_events(
    skip: int = 0,
    limit: int = 100,
    event_type: Optional[str] = None,
    impact_level: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """Get all market events with optional filtering"""
    query = db.query(MarketEvent)

    if event_type:
        query = query.filter(MarketEvent.event_type == event_type)
    if impact_level:
        query = query.filter(MarketEvent.impact_level == impact_level)
    if start_date:
        query = query.filter(MarketEvent.event_date >= start_date)
    if end_date:
        query = query.filter(MarketEvent.event_date <= end_date)

    events = query.order_by(MarketEvent.event_date.desc(), MarketEvent.event_id).offset(skip).limit(limit).all()
    return events


@router.get("/{event_id}", response_model=MarketEventResponse)
def get_market_event(event_id: int, db: Session = Depends(get_db)):
    """Get detailed market event information"""
    event = db.query(MarketEvent).filter(MarketEvent.event_id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Market event not found")
    return event


@router.get("/{event_id}/affected-portfolios", response_model=List[dict])
def get_affected_portfolios(
    event_id: int,
    db: Session = Depends(get_db)
):
    """Get portfolios affected by a specific market event"""
    event = db.query(MarketEvent).filter(MarketEvent.event_id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Market event not found")

    position_changes = db.query(PositionChangeLog).filter(
        PositionChangeLog.related_event_id == event_id
    ).all()

    affected_portfolio_ids = list(set([pc.portfolio_id for pc in position_changes]))

    portfolios = db.query(Portfolio).filter(
        Portfolio.portfolio_id.in_(affected_portfolio_ids)
    ).all()

    result = []
    for portfolio in portfolios:
        portfolio_changes = [pc for pc in position_changes if pc.portfolio_id == portfolio.portfolio_id]

        result.append({
            "portfolio_id": portfolio.portfolio_id,
            "portfolio_name": portfolio.portfolio_name,
            "changes_count": len(portfolio_changes),
            "total_weight_change": sum(
                float(pc.new_weight or 0) - float(pc.old_weight or 0)
                for pc in portfolio_changes
            )
        })

    return result
