"""
Internal, unauthenticated endpoints for service-to-service calls (e.g. the
Flink EC2 fetching its live ticker universe). No user auth here on purpose --
the data returned is non-sensitive (public ticker symbols only, no portfolio
or financial data), and requiring a service JWT for a machine like the Flink
producer would just add a token-refresh problem for no real security benefit.
"""
from fastapi import APIRouter
from sqlalchemy.orm import Session
from fastapi import Depends

from database import get_db
from models import Security

router = APIRouter()


@router.get("/tickers")
def get_tracked_tickers(db: Session = Depends(get_db)):
    """
    Ticker universe for real-time coverage (Flink trade producer + volatility
    detector). Filtered to security_type in (stock, etf) -- excludes
    commodity/currency rows (e.g. GC=F, EURUSD=X), which aren't tradeable via
    Finnhub's equity trade websocket the same way.
    """
    rows = (
        db.query(Security.ticker_symbol)
        .filter(Security.security_type.in_(["stock", "etf"]))
        .distinct()
        .order_by(Security.ticker_symbol)
        .all()
    )
    return {"tickers": [r.ticker_symbol for r in rows]}
