from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any

from database import get_db
from schemas import (
    PortfolioStateAnalysisRequest,
    PositionChangesRequest,
    EventImpactRequest,
    RecommendationRequest
)
from services.portfolio_analyzer import PortfolioAnalyzer
from services.position_detector import PositionChangeDetector
from services.event_analyzer import EventImpactAnalyzer
from services.recommendation_engine import RecommendationEngine

router = APIRouter()


@router.post("/portfolio-state", response_model=Dict[str, Any])
def analyze_portfolio_state(
    request: PortfolioStateAnalysisRequest,
    db: Session = Depends(get_db)
):
    """Analyze current portfolio state and provide insights"""
    analyzer = PortfolioAnalyzer(db)
    analysis = analyzer.analyze_portfolio_state(
        portfolio_id=request.portfolio_id,
        as_of_date=request.as_of_date
    )
    return analysis


@router.post("/position-changes", response_model=Dict[str, Any])
def detect_position_changes(
    request: PositionChangesRequest,
    db: Session = Depends(get_db)
):
    """Detect significant position changes over a time period"""
    detector = PositionChangeDetector(db)
    changes = detector.detect_significant_changes(
        portfolio_id=request.portfolio_id,
        start_date=request.start_date,
        end_date=request.end_date,
        threshold_percent=request.threshold_percent
    )
    return changes


@router.post("/event-impact", response_model=Dict[str, Any])
def analyze_event_impact(
    request: EventImpactRequest,
    db: Session = Depends(get_db)
):
    """Analyze the impact of a market event on portfolios"""
    analyzer = EventImpactAnalyzer(db)
    impact = analyzer.analyze_event_impact(
        event_id=request.event_id,
        portfolio_ids=request.portfolio_ids
    )
    return impact


@router.post("/recommendations", response_model=Dict[str, Any])
def get_recommendations(
    request: RecommendationRequest,
    db: Session = Depends(get_db)
):
    """Get portfolio optimization recommendations"""
    engine = RecommendationEngine(db)
    recommendations = engine.generate_recommendations(
        portfolio_id=request.portfolio_id,
        risk_tolerance=request.risk_tolerance,
        optimization_goal=request.optimization_goal
    )
    return recommendations
