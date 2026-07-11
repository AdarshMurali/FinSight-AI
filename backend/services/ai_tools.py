"""
AI Tool Definitions and Executors — Task 3.4a
=============================================
Exposes FinSight's analytical services as OpenAI function-calling tools.
GPT-4o decides which tools to call; this module executes them and returns
JSON-serializable results that get appended back to the message thread.
"""

import sys
import os
import json
import time
from datetime import date, timedelta
from typing import Any
from sqlalchemy.orm import Session
import yfinance as yf

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'rag'))

from services.portfolio_analyzer import PortfolioAnalyzer
from services.position_detector import PositionChangeDetector
from services.recommendation_engine import RecommendationEngine
from rag.query_engine import MarketRAGEngine, _parse_doc_date
from models import MarketEvent, User
from auth import check_portfolio_access

# Tools that take a caller-supplied portfolio_id and therefore need an ownership
# check before touching real data — the LLM (or a malicious prompt) could ask for
# any portfolio_id it wants, so this can't be trusted the way a URL path param
# scoped by require_portfolio_access is.
_PORTFOLIO_SCOPED_TOOLS = {"get_portfolio_data", "get_position_history", "run_risk_analysis"}


# ── OpenAI tool schemas (passed as tools=[...] in API call) ──────────────────

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_portfolio_data",
            "description": (
                "Retrieve the current state of a portfolio: sector allocation, "
                "top positions, risk metrics (volatility, Sharpe ratio, max drawdown), "
                "and performance (YTD/MTD returns, total value). Use when the user asks "
                "about current portfolio composition, performance, or sector exposure."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "portfolio_id": {
                        "type": "integer",
                        "description": "The portfolio ID to analyze",
                    },
                    "as_of_date": {
                        "type": "string",
                        "description": "ISO date string YYYY-MM-DD. Omit for today.",
                    },
                },
                "required": ["portfolio_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_position_history",
            "description": (
                "Retrieve significant position changes (buys, sells, rebalances) "
                "for a portfolio over a date range. Use when the user asks what changed, "
                "what was bought or sold, what happened in a specific month, or why a "
                "sector weight moved."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "portfolio_id": {
                        "type": "integer",
                        "description": "The portfolio ID",
                    },
                    "from_date": {
                        "type": "string",
                        "description": "Start date YYYY-MM-DD. Default: 90 days ago.",
                    },
                    "to_date": {
                        "type": "string",
                        "description": "End date YYYY-MM-DD. Default: today.",
                    },
                    "threshold_percent": {
                        "type": "number",
                        "description": "Minimum weight change % to report. Default: 3.",
                    },
                },
                "required": ["portfolio_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_market_context",
            "description": (
                "Semantic search across ChromaDB collections: market news, "
                "Fed communications, macro indicators, earnings filings, "
                "analyst research, volatility events, and OHLCV price data. "
                "Use when the user asks why something happened, about macro context, "
                "sector trends, or specific market events."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language query for semantic search",
                    },
                    "n_results": {
                        "type": "integer",
                        "description": "Number of results to return. Default: 8.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_market_events",
            "description": (
                "Retrieve structured market events from the database: Fed rate decisions, "
                "geopolitical events, sector shocks, policy changes. Use when the user "
                "asks about events that affected the market, a sector, or the portfolio."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "impact_level": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "Filter by impact level. Omit to get all levels.",
                    },
                    "event_type": {
                        "type": "string",
                        "description": "Filter by type: policy, geopolitical, sectoral, economic. Omit for all.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max events to return. Default: 10.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_risk_analysis",
            "description": (
                "Run a full risk and optimization analysis for a portfolio. Returns "
                "concentration risk flags, sector overweight warnings, risk metric "
                "alerts (volatility, drawdown, Sharpe), and prioritised rebalancing "
                "recommendations. Use when the user asks about risks, what to fix, "
                "or how to improve the portfolio."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "portfolio_id": {
                        "type": "integer",
                        "description": "The portfolio ID to analyze",
                    },
                    "risk_tolerance": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Risk tolerance override. Omit to use the customer's profile.",
                    },
                },
                "required": ["portfolio_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_quote",
            "description": (
                "Get the live/current price of a single ticker right now — last price, "
                "day change %, and volume. Use for 'what's X trading at' or 'current price "
                "of X' style questions. This is NOT for historical or 'recent performance' "
                "questions — use search_market_context for those."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Ticker symbol, e.g. AAPL, MSFT, TSLA",
                    },
                },
                "required": ["ticker"],
            },
        },
    },
]


# ── Lazy RAG singleton (ChromaDB client is expensive to init) ─────────────────

_rag_engine: MarketRAGEngine | None = None


def _get_rag() -> MarketRAGEngine:
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = MarketRAGEngine()
    return _rag_engine


# ── Live quote — short in-process TTL cache (placeholder for Redis, Phase 6) ──

_QUOTE_CACHE_TTL = 30  # seconds
_quote_cache: dict[str, tuple[float, dict]] = {}


def _get_current_quote(ticker: str) -> dict:
    ticker = ticker.upper().strip()

    cached = _quote_cache.get(ticker)
    if cached and (time.time() - cached[0]) < _QUOTE_CACHE_TTL:
        return cached[1]

    try:
        info = yf.Ticker(ticker).fast_info
        last_price = info.get("lastPrice") or info.get("last_price")
        prev_close = info.get("previousClose") or info.get("previous_close")
        change_pct = (
            round((last_price - prev_close) / prev_close * 100, 2)
            if last_price is not None and prev_close
            else None
        )
        result = {
            "ticker": ticker,
            "price": round(last_price, 2) if last_price is not None else None,
            "previous_close": round(prev_close, 2) if prev_close is not None else None,
            "change_pct": change_pct,
            "volume": info.get("lastVolume") or info.get("last_volume"),
            "as_of": "live quote, fetched now",
        }
    except Exception as e:
        return {"error": f"Could not fetch live quote for {ticker}: {e}"}

    _quote_cache[ticker] = (time.time(), result)
    return result


# ── Tool executor ─────────────────────────────────────────────────────────────

def execute_tool(name: str, arguments: dict, db: Session, current_user: User) -> Any:
    """
    Dispatch a tool name to the right service call.
    Returns a JSON-serializable dict/list.
    Errors are caught and returned as {"error": "..."} so the LLM can react.

    current_user is required (not optional) so this can never silently run
    unscoped — every call site must have an authenticated user by this point.
    """
    if name in _PORTFOLIO_SCOPED_TOOLS and "portfolio_id" in arguments:
        if not check_portfolio_access(db, current_user, int(arguments["portfolio_id"])):
            return {"error": f"Not authorized to access portfolio {arguments['portfolio_id']}."}

    if name == "get_portfolio_data":
        analyzer = PortfolioAnalyzer(db)
        as_of = None
        if "as_of_date" in arguments:
            try:
                as_of = date.fromisoformat(arguments["as_of_date"])
            except ValueError:
                pass
        result = analyzer.analyze_portfolio_state(
            portfolio_id=int(arguments["portfolio_id"]),
            as_of_date=as_of,
        )
        # Drop heavy allocations not needed for chat answers
        result.pop("region_allocation", None)
        result.pop("asset_allocation", None)
        return result

    elif name == "get_position_history":
        detector = PositionChangeDetector(db)
        today = date.today()
        from_d = (
            date.fromisoformat(arguments["from_date"])
            if "from_date" in arguments
            else today - timedelta(days=90)
        )
        to_d = (
            date.fromisoformat(arguments["to_date"])
            if "to_date" in arguments
            else today
        )
        threshold = float(arguments.get("threshold_percent", 3.0))
        result = detector.detect_significant_changes(
            portfolio_id=int(arguments["portfolio_id"]),
            start_date=from_d,
            end_date=to_d,
            threshold_percent=threshold,
        )
        # Cap list to avoid flooding the context window
        result["significant_changes"] = result.get("significant_changes", [])[:20]
        return result

    elif name == "search_market_context":
        try:
            rag = _get_rag()
            n = int(arguments.get("n_results", 8))
            results = rag.retrieve_context(arguments["query"], n_results=n)
            return [
                {
                    "collection": r["collection"],
                    "date": (
                        d.isoformat() if (d := _parse_doc_date(r["metadata"])) else "N/A"
                    ),
                    "snippet": r["document"][:350],
                    "relevance": round(r["relevance_score"], 3),
                }
                for r in results
            ]
        except Exception as e:
            return {"error": f"ChromaDB unavailable: {e}"}

    elif name == "get_market_events":
        from sqlalchemy import desc
        query = db.query(MarketEvent)
        if "impact_level" in arguments:
            query = query.filter(MarketEvent.impact_level == arguments["impact_level"])
        if "event_type" in arguments:
            query = query.filter(MarketEvent.event_type == arguments["event_type"])
        limit = int(arguments.get("limit", 10))
        events = query.order_by(desc(MarketEvent.event_date)).limit(limit).all()
        return [
            {
                "event_id": e.event_id,
                "date": e.event_date.isoformat() if e.event_date else None,
                "type": e.event_type,
                "title": e.event_title,
                "description": (e.event_description or "")[:250],
                "affected_sectors": e.affected_sectors,
                "impact_level": e.impact_level,
            }
            for e in events
        ]

    elif name == "run_risk_analysis":
        engine = RecommendationEngine(db)
        return engine.generate_recommendations(
            portfolio_id=int(arguments["portfolio_id"]),
            risk_tolerance=arguments.get("risk_tolerance"),
            optimization_goal="balanced",
        )

    elif name == "get_current_quote":
        return _get_current_quote(str(arguments["ticker"]))

    else:
        return {"error": f"Unknown tool: {name}"}
