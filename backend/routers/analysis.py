import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Dict, Any

from database import get_db
from models import User, Portfolio, MarketEvent
from auth import get_current_user, check_portfolio_access, scope_portfolio_query
from schemas import (
    PortfolioStateAnalysisRequest,
    PositionChangesRequest,
    EventImpactRequest,
    RecommendationRequest,
    AIPortfolioExplainRequest,
    AIChangeNarrateRequest,
    AIEventAnalyzeRequest,
    AIRecommendationRequest,
    AIChatRequest,
)
from services.portfolio_analyzer import PortfolioAnalyzer
from services.position_detector import PositionChangeDetector
from services.event_analyzer import EventImpactAnalyzer
from services.recommendation_engine import RecommendationEngine
from services.ai_portfolio_explainer import AIPortfolioExplainer
from services.ai_change_narrator import AIChangeNarrator
from services.ai_event_analyzer import AIEventAnalyzer
from services.ai_recommendation_engine import AIRecommendationEngine
from services.ai_chat_service import AIChatService, SUGGESTED_QUESTIONS

router = APIRouter()


def _require_access(db: Session, current_user: User, portfolio_id: int) -> None:
    """analysis.py's requests carry portfolio_id in the POST body, not the URL path,
    so require_portfolio_access (a path-param dependency) doesn't apply directly —
    same ownership check, called explicitly instead."""
    if not check_portfolio_access(db, current_user, portfolio_id):
        raise HTTPException(status_code=403, detail="Not authorized for this portfolio")


def _accessible_portfolio_ids(db: Session, current_user: User, requested_ids) -> list:
    """Intersect a requested portfolio_ids list (or 'all' when None) with what the
    user can access. IMPORTANT: the caller must treat an empty return as "nothing to
    show", never pass it straight to EventImpactAnalyzer — that class treats an empty
    list as falsy and falls back to querying every portfolio in the database."""
    if requested_ids:
        return [
            pid for (pid,) in
            scope_portfolio_query(db.query(Portfolio.portfolio_id), current_user)
            .filter(Portfolio.portfolio_id.in_(requested_ids)).all()
        ]
    return [pid for (pid,) in scope_portfolio_query(db.query(Portfolio.portfolio_id), current_user).all()]


def _empty_event_impact_response(db: Session, event_id: int) -> Dict[str, Any]:
    event = db.query(MarketEvent).filter(MarketEvent.event_id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail=f"Market event {event_id} not found")
    return {
        "event_id": event_id, "event_title": event.event_title,
        "event_date": event.event_date.isoformat(), "event_type": event.event_type,
        "impact_level": event.impact_level, "affected_sectors": [], "affected_regions": [],
        "portfolios_analyzed": 0, "portfolios_affected": 0, "portfolio_impacts": [],
    }


@router.post("/portfolio-state", response_model=Dict[str, Any])
def analyze_portfolio_state(
    request: PortfolioStateAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Analyze current portfolio state and provide insights"""
    _require_access(db, current_user, request.portfolio_id)
    analyzer = PortfolioAnalyzer(db)
    analysis = analyzer.analyze_portfolio_state(
        portfolio_id=request.portfolio_id,
        as_of_date=request.as_of_date
    )
    return analysis


@router.post("/position-changes", response_model=Dict[str, Any])
def detect_position_changes(
    request: PositionChangesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Detect significant position changes over a time period"""
    _require_access(db, current_user, request.portfolio_id)
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Analyze the impact of a market event on portfolios the user has access to"""
    portfolio_ids = _accessible_portfolio_ids(db, current_user, request.portfolio_ids)
    if not portfolio_ids:
        return _empty_event_impact_response(db, request.event_id)

    analyzer = EventImpactAnalyzer(db)
    impact = analyzer.analyze_event_impact(
        event_id=request.event_id,
        portfolio_ids=portfolio_ids
    )
    return impact


@router.post("/recommendations", response_model=Dict[str, Any])
def get_recommendations(
    request: RecommendationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get portfolio optimization recommendations"""
    _require_access(db, current_user, request.portfolio_id)
    engine = RecommendationEngine(db)
    recommendations = engine.generate_recommendations(
        portfolio_id=request.portfolio_id,
        risk_tolerance=request.risk_tolerance,
        optimization_goal=request.optimization_goal
    )
    return recommendations


# ── Task 3.2: AI Analysis Endpoints ──────────────────────────────────────────

@router.post("/ai/explain-portfolio", response_model=Dict[str, Any])
def ai_explain_portfolio(
    request: AIPortfolioExplainRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    AI-powered portfolio state explanation.
    Combines structured portfolio analytics with RAG market context
    and Claude to produce a natural language explanation.
    """
    _require_access(db, current_user, request.portfolio_id)
    try:
        explainer = AIPortfolioExplainer(db)
        return explainer.explain(
            portfolio_id=request.portfolio_id,
            as_of_date=request.as_of_date,
            question=request.question,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {e}")


@router.post("/ai/narrate-changes", response_model=Dict[str, Any])
def ai_narrate_changes(
    request: AIChangeNarrateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    AI-powered position change causality narrative.
    Detects significant position changes and explains the market drivers
    using news, macro data, and earnings context from ChromaDB.
    """
    _require_access(db, current_user, request.portfolio_id)
    try:
        narrator = AIChangeNarrator(db)
        return narrator.narrate(
            portfolio_id=request.portfolio_id,
            start_date=request.start_date,
            end_date=request.end_date,
            threshold_percent=request.threshold_percent,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI narration failed: {e}")


@router.post("/ai/analyze-event", response_model=Dict[str, Any])
def ai_analyze_event(
    request: AIEventAnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    AI-powered market event impact analysis (uses Claude Opus for deep reasoning).
    Analyzes direct exposure, second-order effects, and recommended actions.
    """
    portfolio_ids = _accessible_portfolio_ids(db, current_user, request.portfolio_ids)
    if not portfolio_ids:
        event_data = _empty_event_impact_response(db, request.event_id)
        return {"ai_assessment": "No accessible portfolios to analyze for this event.", "event_data": event_data}
    try:
        analyzer = AIEventAnalyzer(db)
        return analyzer.analyze(
            event_id=request.event_id,
            portfolio_ids=portfolio_ids,
            depth=request.depth,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI event analysis failed: {e}")


@router.post("/ai/recommendations", response_model=Dict[str, Any])
def ai_recommendations(
    request: AIRecommendationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    AI-enhanced portfolio recommendations.
    Combines quantitative rule-based analysis with market context
    (analyst views, macro trends, news sentiment) via RAG + Claude.
    """
    _require_access(db, current_user, request.portfolio_id)
    try:
        engine = AIRecommendationEngine(db)
        return engine.recommend(
            portfolio_id=request.portfolio_id,
            risk_tolerance=request.risk_tolerance,
            optimization_goal=request.optimization_goal,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI recommendations failed: {e}")


# ── Task 4.3: AI Chat Streaming Endpoint ──────────────────────────────────────

@router.get("/ai/chat/suggested-questions")
def get_suggested_questions():
    """Return the list of suggested starter questions for the chat UI."""
    return {"questions": SUGGESTED_QUESTIONS}


@router.post("/ai/chat")
def ai_chat_stream(
    request: AIChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Streaming conversational AI endpoint (Server-Sent Events).

    Each chunk is emitted as:
        data: {"token": "<text>"}\n\n
    Terminated by:
        data: [DONE]\n\n

    The client assembles tokens into the full assistant response.

    Ownership is checked twice: once here for the portfolio_id the conversation
    starts with, and again inside execute_tool() (ai_tools.py) for every
    portfolio_id GPT-4o's tool-calling requests mid-conversation — the LLM can
    ask for any portfolio_id, so the second check can't be skipped.
    """
    _require_access(db, current_user, request.portfolio_id)

    def event_stream():
        try:
            service = AIChatService(db, current_user)
            history = [
                {"role": m.role, "content": m.content}
                for m in (request.conversation_history or [])
            ]
            for event in service.stream_response(
                portfolio_id=request.portfolio_id,
                user_message=request.message,
                conversation_history=history,
            ):
                payload = json.dumps(event, ensure_ascii=False)
                yield f"data: {payload}\n\n"
        except ValueError as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': f'Chat failed: {e}'})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":        "keep-alive",
        },
    )
