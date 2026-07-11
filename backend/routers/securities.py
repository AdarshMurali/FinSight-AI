from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from models import Security, User
from auth import get_current_user
from schemas import SecurityResponse

router = APIRouter()


@router.get("/", response_model=List[SecurityResponse])
def get_securities(
    skip: int = 0,
    limit: int = 100,
    security_type: Optional[str] = None,
    sector: Optional[str] = None,
    country: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all securities with optional filtering — reference data, any logged-in user"""
    query = db.query(Security)

    if security_type:
        query = query.filter(Security.security_type == security_type)
    if sector:
        query = query.filter(Security.sector == sector)
    if country:
        query = query.filter(Security.country == country)

    securities = query.order_by(Security.security_id).offset(skip).limit(limit).all()
    return securities


@router.get("/{security_id}", response_model=SecurityResponse)
def get_security(security_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get detailed security information"""
    security = db.query(Security).filter(Security.security_id == security_id).first()
    if not security:
        raise HTTPException(status_code=404, detail="Security not found")
    return security


@router.get("/ticker/{ticker_symbol}", response_model=SecurityResponse)
def get_security_by_ticker(ticker_symbol: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get security information by ticker symbol"""
    security = db.query(Security).filter(Security.ticker_symbol == ticker_symbol).first()
    if not security:
        raise HTTPException(status_code=404, detail="Security not found")
    return security
