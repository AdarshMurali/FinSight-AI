from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from database import get_db
from models import Portfolio, Position, Transaction, PortfolioPerformance, Customer, User
from auth import get_current_user, require_portfolio_access, scope_portfolio_query
from services.cache import get_or_set
from schemas import (
    PortfolioResponse,
    PortfolioDetailsResponse,
    PositionResponse,
    TransactionResponse,
    PerformanceResponse,
    CustomerResponse
)

router = APIRouter()

# Heavy joins recomputed on every page load even though the underlying data
# (transactions, position weights) changes rarely. Same TTL bucket as
# plan.md's original table — no cross-EC2 invalidation concern here the way
# risk metrics has, since 5 min is already short enough to bound staleness
# from price_update_job.py's daily run without needing to invalidate at all.
PORTFOLIO_SUMMARY_TTL = 300


@router.get("/", response_model=List[PortfolioResponse])
def get_portfolios(
    skip: int = 0,
    limit: int = 100,
    customer_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get portfolios the current user manages (all 50 for admin), optional customer filter"""
    query = scope_portfolio_query(db.query(Portfolio), current_user)
    if customer_id:
        query = query.filter(Portfolio.customer_id == customer_id)
    portfolios = query.order_by(Portfolio.portfolio_id).offset(skip).limit(limit).all()
    return portfolios


@router.get("/{portfolio_id}", response_model=PortfolioDetailsResponse)
def get_portfolio(portfolio: Portfolio = Depends(require_portfolio_access), db: Session = Depends(get_db)):
    """Get detailed portfolio information"""
    def _compute():
        portfolio_id = portfolio.portfolio_id
        positions_count = db.query(Position).filter(Position.portfolio_id == portfolio_id).count()

        total_positions_value = db.query(Position).filter(
            Position.portfolio_id == portfolio_id
        ).with_entities(Position.market_value).all()
        total_value = sum(float(pv[0]) if pv[0] else 0 for pv in total_positions_value)

        customer = db.query(Customer).filter(Customer.customer_id == portfolio.customer_id).first()

        portfolio_dict = {
            **portfolio.__dict__,
            "positions_count": positions_count,
            "total_positions_value": total_value,
            "customer": customer
        }
        # Serialize through the response schema now (not left to FastAPI on the way
        # out) so nested ORM objects / Decimals / datetimes are plain JSON-safe
        # types before this ever reaches the cache's json.dumps.
        return PortfolioDetailsResponse.model_validate(portfolio_dict).model_dump(mode="json")

    return get_or_set(f"portfolio:summary:{portfolio.portfolio_id}", PORTFOLIO_SUMMARY_TTL, _compute)


@router.get("/{portfolio_id}/positions", response_model=List[PositionResponse])
def get_portfolio_positions(
    position_type: Optional[str] = None,
    sector: Optional[str] = None,
    portfolio: Portfolio = Depends(require_portfolio_access),
    db: Session = Depends(get_db)
):
    """Get all positions for a portfolio with optional filters"""
    def _compute():
        query = db.query(Position).filter(Position.portfolio_id == portfolio.portfolio_id)
        if position_type:
            query = query.filter(Position.position_type == position_type)
        positions = query.all()
        return [PositionResponse.model_validate(p).model_dump(mode="json") for p in positions]

    key = f"portfolio:positions:{portfolio.portfolio_id}:{position_type or 'all'}"
    return get_or_set(key, PORTFOLIO_SUMMARY_TTL, _compute)


@router.get("/{portfolio_id}/performance", response_model=List[PerformanceResponse])
def get_portfolio_performance(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(default=30, le=365),
    portfolio: Portfolio = Depends(require_portfolio_access),
    db: Session = Depends(get_db)
):
    """Get performance metrics for a portfolio"""
    query = db.query(PortfolioPerformance).filter(
        PortfolioPerformance.portfolio_id == portfolio.portfolio_id
    )

    if start_date:
        query = query.filter(PortfolioPerformance.as_of_date >= start_date)
    if end_date:
        query = query.filter(PortfolioPerformance.as_of_date <= end_date)

    performance = query.order_by(PortfolioPerformance.as_of_date.desc()).limit(limit).all()
    return performance


@router.get("/{portfolio_id}/history", response_model=List[TransactionResponse])
def get_portfolio_history(
    transaction_type: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(default=100, le=1000),
    portfolio: Portfolio = Depends(require_portfolio_access),
    db: Session = Depends(get_db)
):
    """Get transaction history for a portfolio"""
    query = db.query(Transaction).filter(Transaction.portfolio_id == portfolio.portfolio_id)

    if transaction_type:
        query = query.filter(Transaction.transaction_type == transaction_type)
    if start_date:
        query = query.filter(Transaction.transaction_date >= start_date)
    if end_date:
        query = query.filter(Transaction.transaction_date <= end_date)

    transactions = query.order_by(Transaction.transaction_date.desc()).limit(limit).all()
    return transactions
