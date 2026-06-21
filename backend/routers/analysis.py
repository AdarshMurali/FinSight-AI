import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Dict, Any

from database import get_db
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


# ── Task 3.2: AI Analysis Endpoints ──────────────────────────────────────────

@router.post("/ai/explain-portfolio", response_model=Dict[str, Any])
def ai_explain_portfolio(
    request: AIPortfolioExplainRequest,
    db: Session = Depends(get_db)
):
    """
    AI-powered portfolio state explanation.
    Combines structured portfolio analytics with RAG market context
    and Claude to produce a natural language explanation.
    """
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
    db: Session = Depends(get_db)
):
    """
    AI-powered position change causality narrative.
    Detects significant position changes and explains the market drivers
    using news, macro data, and earnings context from ChromaDB.
    """
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
    db: Session = Depends(get_db)
):
    """
    AI-powered market event impact analysis (uses Claude Opus for deep reasoning).
    Analyzes direct exposure, second-order effects, and recommended actions.
    """
    try:
        analyzer = AIEventAnalyzer(db)
        return analyzer.analyze(
            event_id=request.event_id,
            portfolio_ids=request.portfolio_ids,
            depth=request.depth,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI event analysis failed: {e}")


@router.post("/ai/recommendations", response_model=Dict[str, Any])
def ai_recommendations(
    request: AIRecommendationRequest,
    db: Session = Depends(get_db)
):
    """
    AI-enhanced portfolio recommendations.
    Combines quantitative rule-based analysis with market context
    (analyst views, macro trends, news sentiment) via RAG + Claude.
    """
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
    db: Session = Depends(get_db)
):
    """
    Streaming conversational AI endpoint (Server-Sent Events).

    Each chunk is emitted as:
        data: {"token": "<text>"}\n\n
    Terminated by:
        data: [DONE]\n\n

    The client assembles tokens into the full assistant response.
    """
    def event_stream():
        try:
            service = AIChatService(db)
            history = [
                {"role": m.role, "content": m.content}
                for m in (request.conversation_history or [])
            ]
            for token in service.stream_response(
                portfolio_id=request.portfolio_id,
                user_message=request.message,
                conversation_history=history,
            ):
                payload = json.dumps({"token": token}, ensure_ascii=False)
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
