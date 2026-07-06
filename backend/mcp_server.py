"""
FinSight AI — FastMCP Server
============================
Exposes FinSight's portfolio intelligence as an MCP server.
Any MCP-compatible client (Claude Desktop, Cursor, etc.) can connect and
query live portfolio data, risk metrics, alerts, and market context.

Run modes
---------
  stdio (Claude Desktop):
      python backend/mcp_server.py

  HTTP/SSE (remote clients, Cursor):
      python backend/mcp_server.py --transport sse --port 8002

Claude Desktop config  (~/.config/claude/claude_desktop_config.json on Mac,
                         %APPDATA%\Claude\claude_desktop_config.json on Windows):
    {
      "mcpServers": {
        "finsight": {
          "command": "C:/Agentic_AI/FinSight-AI/finsightaivenv/Scripts/python.exe",
          "args":    ["C:/Agentic_AI/FinSight-AI/backend/mcp_server.py"]
        }
      }
    }

Tools exposed (8 total)
-----------------------
  list_portfolios            — all portfolios with customer, value, strategy
  get_portfolio_summary      — full portfolio state: sectors, top positions, performance
  get_portfolio_positions    — positions table, optionally filtered by sector
  get_portfolio_risk         — latest VaR, stress tests, factor exposure from Risk_Metrics
  get_portfolio_alerts       — active alerts (threshold / event / ai) for a portfolio
  search_market_context      — semantic search across ChromaDB (36K+ financial docs)
  get_market_events          — structured events (Fed decisions, geopolitical, sectoral)
  refresh_portfolio_risk     — trigger a fresh VaR/stress/factor computation (background)
"""

import sys
import os
import json
import argparse
from datetime import date, timedelta
from typing import List, Optional

# ── Path setup so backend modules resolve when run from project root ──────────
_backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _backend_dir)
sys.path.insert(0, os.path.join(_backend_dir, "rag"))

from mcp.server.fastmcp import FastMCP

from database import SessionLocal
from models import Portfolio, Customer, Position, Security, MarketEvent, Alert, RiskMetric
from services.portfolio_analyzer import PortfolioAnalyzer
from services.risk_analytics import compute_all
from rag.query_engine import MarketRAGEngine

# ── FastMCP app ───────────────────────────────────────────────────────────────
mcp = FastMCP(
    name="FinSight AI",
    instructions=(
        "You are connected to FinSight AI, a hedge fund portfolio intelligence platform. "
        "Use the available tools to answer questions about portfolios, risk metrics, "
        "market events, and financial context. Always call the relevant tool before "
        "answering — do not guess numbers from memory."
    ),
)

# ── Lazy singletons ───────────────────────────────────────────────────────────
_rag: Optional[MarketRAGEngine] = None


def _get_rag() -> MarketRAGEngine:
    global _rag
    if _rag is None:
        _rag = MarketRAGEngine()
    return _rag


def _db():
    """Return a fresh SQLAlchemy session (caller must close)."""
    return SessionLocal()


# ─────────────────────────────────────────────────────────────────────────────
# Tool 1: list_portfolios
# ─────────────────────────────────────────────────────────────────────────────
@mcp.tool()
def list_portfolios() :
    """
    List all portfolios in the system with their owner, total value, currency,
    strategy type, and inception date. Use this first when the user does not
    specify a portfolio ID or asks 'what portfolios do we have?'.
    """
    db = _db()
    try:
        rows = (
            db.query(Portfolio, Customer)
            .join(Customer, Portfolio.customer_id == Customer.customer_id)
            .order_by(Portfolio.portfolio_id)
            .all()
        )
        return [
            {
                "portfolio_id":   p.portfolio_id,
                "portfolio_name": p.portfolio_name,
                "customer":       c.customer_name,
                "institution_type": c.institution_type,
                "total_value":    float(p.total_value or 0),
                "currency":       p.currency,
                "strategy_type":  p.strategy_type,
                "inception_date": str(p.inception_date) if p.inception_date else None,
            }
            for p, c in rows
        ]
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Tool 2: get_portfolio_summary
# ─────────────────────────────────────────────────────────────────────────────
@mcp.tool()
def get_portfolio_summary(portfolio_id: int) :
    """
    Get a full portfolio summary: sector allocation, top-10 positions by weight,
    performance metrics (YTD/MTD returns, volatility, Sharpe ratio, max drawdown),
    and cash balance. Use when the user asks about a specific portfolio's state,
    composition, or performance.
    """
    db = _db()
    try:
        analyzer = PortfolioAnalyzer(db)
        result = analyzer.analyze_portfolio_state(portfolio_id=portfolio_id)
        result.pop("region_allocation", None)
        result.pop("asset_allocation", None)
        return result
    except Exception as e:
        return {"error": str(e), "portfolio_id": portfolio_id}
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Tool 3: get_portfolio_positions
# ─────────────────────────────────────────────────────────────────────────────
@mcp.tool()
def get_portfolio_positions(portfolio_id: int, sector: str = "") :
    """
    Get the current positions in a portfolio. Returns ticker, company name,
    sector, quantity, market value, weight (%), and position type (long/short).
    Pass sector to filter (e.g. 'Technology', 'Energy'). Leave blank for all.
    """
    db = _db()
    try:
        q = (
            db.query(Position, Security)
            .join(Security, Position.security_id == Security.security_id)
            .filter(Position.portfolio_id == portfolio_id)
        )
        if sector:
            q = q.filter(Security.sector.ilike(f"%{sector}%"))
        rows = q.order_by(Position.weight.desc()).all()
        return [
            {
                "ticker":        s.ticker_symbol,
                "name":          s.security_name,
                "sector":        s.sector,
                "industry":      s.industry,
                "quantity":      float(pos.quantity or 0),
                "market_value":  float(pos.market_value or 0),
                "weight_pct":    float(pos.weight or 0),
                "position_type": pos.position_type,
                "avg_cost":      float(pos.avg_cost_basis or 0),
                "current_price": float(pos.current_price or 0),
            }
            for pos, s in rows
        ]
    except Exception as e:
        return [{"error": str(e)}]
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Tool 4: get_portfolio_risk
# ─────────────────────────────────────────────────────────────────────────────
@mcp.tool()
def get_portfolio_risk(portfolio_id: int) :
    """
    Get the latest computed risk metrics for a portfolio:
    - VaR (Value at Risk): historical 95%/99%, parametric, 1-day and 10-day
    - 6 stress tests: 2008 Crisis, COVID Crash, Rate Shock, Dot-com Bust,
      Oil Shock, Stagflation — showing portfolio impact %
    - Factor exposure: market beta, tech beta, value/growth/momentum betas
    Returns 'not_computed' status if the daily risk job has not run yet.
    Use refresh_portfolio_risk to trigger a fresh calculation.
    """
    db = _db()
    try:
        row = (
            db.query(RiskMetric)
            .filter(RiskMetric.portfolio_id == portfolio_id)
            .order_by(RiskMetric.computed_at.desc())
            .first()
        )
        if not row:
            return {
                "status": "not_computed",
                "portfolio_id": portfolio_id,
                "hint": "Call refresh_portfolio_risk to compute now (takes ~15-30s)",
            }
        var_data    = json.loads(row.var_data or "{}")
        stress_data = json.loads(row.stress_data or "[]")
        factor_data = json.loads(row.factor_data or "{}")

        # Summarise stress tests
        stress_summary = [
            {
                "scenario":         s.get("scenario"),
                "portfolio_impact": f"{s.get('portfolio_impact_pct', 0):.2f}%",
                "severity":         "critical" if s.get("portfolio_impact_pct", 0) < -25 else "warning" if s.get("portfolio_impact_pct", 0) < -10 else "ok",
            }
            for s in stress_data
        ]

        return {
            "status":       "ok",
            "portfolio_id": portfolio_id,
            "computed_at":  row.computed_at.isoformat(),
            "price_date":   str(row.price_date) if row.price_date else None,
            "var": var_data,
            "stress_tests": stress_summary,
            "factor_exposure": factor_data,
        }
    except Exception as e:
        return {"error": str(e), "portfolio_id": portfolio_id}
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Tool 5: get_portfolio_alerts
# ─────────────────────────────────────────────────────────────────────────────
@mcp.tool()
def get_portfolio_alerts(
    portfolio_id: int = 0,
    unread_only: bool = False,
    limit: int = 20,
) :
    """
    Get alerts for a portfolio. Alert types: threshold (VaR/stress/beta breach),
    event (market event affecting portfolio), ai (proactive GPT-4o analysis).
    Severities: critical, warning, info.
    Pass portfolio_id=0 to get alerts across all portfolios.
    Pass unread_only=True to see only unread alerts.
    """
    db = _db()
    try:
        q = db.query(Alert).order_by(Alert.triggered_at.desc())
        if portfolio_id:
            q = q.filter(Alert.portfolio_id == portfolio_id)
        if unread_only:
            q = q.filter(Alert.is_read == 0)
        rows = q.limit(limit).all()
        return [
            {
                "alert_id":     a.alert_id,
                "portfolio_id": a.portfolio_id,
                "type":         a.alert_type,
                "severity":     a.severity,
                "title":        a.title,
                "message":      a.message,
                "is_read":      bool(a.is_read),
                "triggered_at": a.triggered_at.isoformat() if a.triggered_at else None,
            }
            for a in rows
        ]
    except Exception as e:
        return [{"error": str(e)}]
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Tool 6: search_market_context
# ─────────────────────────────────────────────────────────────────────────────
@mcp.tool()
def search_market_context(query: str, n_results: int = 8) :
    """
    Semantic search across 36,000+ financial documents in ChromaDB:
    - Market news (live Flink stream from Finnhub)
    - FRED macro indicators (40+ series, 2019–present)
    - Fed communications (rate decisions, balance sheet)
    - SEC EDGAR filings (17,200 quarterly/annual reports)
    - OHLCV price data (5-year monthly summaries, 131 securities)
    - Dividends, earnings, analyst recommendations, volatility events

    Use for questions like: 'Why did tech drop?', 'What has the Fed said about
    rates?', 'What is NVDA's recent revenue trend?', 'What macro risks exist?'
    """
    try:
        rag = _get_rag()
        results = rag.retrieve_context(query, n_results=n_results)
        return [
            {
                "collection":  r["collection"],
                "date":        r["metadata"].get("date", r["metadata"].get("published_at", "N/A")),
                "snippet":     r["document"][:400],
                "relevance":   round(r["relevance_score"], 3),
            }
            for r in results
        ]
    except Exception as e:
        return [{"error": f"ChromaDB unavailable: {e}"}]


# ─────────────────────────────────────────────────────────────────────────────
# Tool 7: get_market_events
# ─────────────────────────────────────────────────────────────────────────────
@mcp.tool()
def get_market_events(
    impact_level: str = "",
    event_type: str = "",
    limit: int = 10,
) :
    """
    Retrieve structured market events stored in the database:
    Fed rate decisions, geopolitical events, sector shocks, policy changes.

    impact_level: 'high', 'medium', 'low' — leave blank for all
    event_type:   'policy', 'geopolitical', 'sectoral', 'economic' — leave blank for all
    Returns events sorted newest first.
    """
    db = _db()
    try:
        from sqlalchemy import desc
        q = db.query(MarketEvent)
        if impact_level:
            q = q.filter(MarketEvent.impact_level == impact_level)
        if event_type:
            q = q.filter(MarketEvent.event_type == event_type)
        events = q.order_by(desc(MarketEvent.event_date)).limit(limit).all()
        return [
            {
                "event_id":        e.event_id,
                "date":            e.event_date.isoformat() if e.event_date else None,
                "type":            e.event_type,
                "title":           e.event_title,
                "description":     (e.event_description or "")[:300],
                "affected_sectors": e.affected_sectors,
                "impact_level":    e.impact_level,
            }
            for e in events
        ]
    except Exception as e:
        return [{"error": str(e)}]
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Tool 8: refresh_portfolio_risk
# ─────────────────────────────────────────────────────────────────────────────
@mcp.tool()
def refresh_portfolio_risk(portfolio_id: int) :
    """
    Trigger a fresh VaR, stress test, and factor exposure computation for a
    portfolio. Fetches latest prices from yfinance and recomputes all risk metrics.
    This runs synchronously and takes 15-30 seconds. After it completes, call
    get_portfolio_risk to see the updated results.
    Use when the stored metrics are stale or the user asks for an up-to-date risk number.
    """
    db = _db()
    try:
        result = compute_all(db, portfolio_id)

        from datetime import datetime
        row = RiskMetric(
            portfolio_id=portfolio_id,
            computed_at=datetime.utcnow(),
            var_data=json.dumps(result.get("var", {})),
            stress_data=json.dumps(result.get("stress_tests", [])),
            factor_data=json.dumps(result.get("factor_exposure", {})),
            price_date=date.today(),
            status="completed",
        )
        db.add(row)
        db.commit()

        var_hist = result.get("var", {}).get("historical", {})
        return {
            "status":        "completed",
            "portfolio_id":  portfolio_id,
            "computed_at":   row.computed_at.isoformat(),
            "var_95_1d_pct": var_hist.get("var_95_1d_pct"),
            "var_99_1d_pct": var_hist.get("var_99_1d_pct"),
            "stress_tests":  len(result.get("stress_tests", [])),
            "hint":          "Call get_portfolio_risk for full details",
        }
    except Exception as e:
        return {"status": "error", "portfolio_id": portfolio_id, "error": str(e)}
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FinSight AI MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport mode: stdio for Claude Desktop, sse for HTTP clients (default: stdio)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8002,
        help="Port for SSE transport (default: 8002)",
    )
    args = parser.parse_args()

    if args.transport == "sse":
        print(f"[FinSight MCP] Starting SSE server on port {args.port}", flush=True)
        mcp.run(transport="sse", port=args.port)
    else:
        mcp.run(transport="stdio")
