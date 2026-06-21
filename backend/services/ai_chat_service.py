"""
AI Chat Service — Task 4.3
==========================
Conversational interface for portfolio Q&A.

Flow:
  User message
    → load portfolio context (PortfolioAnalyzer)
    → RAG query on user message (MarketRAGEngine)
    → build system prompt with all context
    → stream tokens via LLMService.generate_stream()
    → yields str chunks to the FastAPI streaming endpoint
"""

import sys
import os
from typing import Iterator, Optional
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'rag'))

from services.portfolio_analyzer import PortfolioAnalyzer
from services.llm_service import LLMService
from rag.query_engine import MarketRAGEngine


# Suggested starter questions shown in the UI
SUGGESTED_QUESTIONS = [
    "What are the main risks in this portfolio?",
    "Which sectors have the highest concentration?",
    "How does the current portfolio compare to its target strategy?",
    "What are the top recommendations to improve risk-adjusted returns?",
    "Explain the recent performance trend and key drivers.",
    "Which positions have the most impact on overall volatility?",
]

# Max conversation turns to send as context (keeps token usage reasonable)
MAX_HISTORY_TURNS = 8


class AIChatService:
    """
    Streams a conversational AI response grounded in live portfolio data
    and ChromaDB RAG context.
    """

    def __init__(self, db: Session, llm: Optional[LLMService] = None):
        self.db       = db
        self.analyzer = PortfolioAnalyzer(db)
        self.rag      = MarketRAGEngine()
        self.llm      = llm or LLMService()

    def stream_response(
        self,
        portfolio_id: int,
        user_message: str,
        conversation_history: list[dict],
    ) -> Iterator[str]:
        """
        Yields string token chunks for the given user message.

        Args:
            portfolio_id:          Portfolio to use as context.
            user_message:          The current user question.
            conversation_history:  List of {role, content} dicts (prior turns).
        """
        # ── 1. Load portfolio context ────────────────────────────────────────
        portfolio_data = self.analyzer.analyze_portfolio_state(portfolio_id)

        # ── 2. RAG query — find relevant market context for this question ────
        rag_query = f"{user_message} {portfolio_data.get('portfolio_name', '')} portfolio"
        rag_results = self.rag.retrieve_context(rag_query, n_results=5)
        rag_context = self._format_rag_context(rag_results)

        # ── 3. Build system prompt with portfolio + RAG grounding ────────────
        system_prompt = self._build_system_prompt(portfolio_data, rag_context)

        # ── 4. Build message list (trim to MAX_HISTORY_TURNS) ────────────────
        trimmed_history = conversation_history[-(MAX_HISTORY_TURNS * 2):]
        messages = [
            *trimmed_history,
            {"role": "user", "content": user_message},
        ]

        # ── 5. Stream tokens ─────────────────────────────────────────────────
        yield from self.llm.generate_stream(
            task_type="analysis",
            system_prompt=system_prompt,
            messages=messages,
            max_tokens=1500,
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _build_system_prompt(portfolio_data: dict, rag_context: str) -> str:
        name         = portfolio_data.get("portfolio_name", "Unknown")
        total_value  = portfolio_data.get("total_value", 0)
        strategy     = portfolio_data.get("strategy_type", "N/A")
        sectors      = portfolio_data.get("sector_allocation", {})
        risk         = portfolio_data.get("risk_metrics", {})
        perf         = portfolio_data.get("performance_summary", {})
        concentration = portfolio_data.get("concentration_risk", {})
        top_positions = concentration.get("top_positions", [])[:5]

        top_pos_str = ", ".join(
            f"{p['ticker']} ({p['weight']:.1f}%)" for p in top_positions
        ) or "N/A"

        sector_str = ", ".join(
            f"{k}: {v:.1f}%" for k, v in list(sectors.items())[:6]
        ) or "N/A"

        return f"""You are a senior portfolio manager AI assistant for FinSight AI, \
a hedge fund portfolio intelligence platform.

You have access to live portfolio data and current market context. \
Answer questions clearly, citing specific numbers. \
Be concise but thorough. Use plain language — avoid unnecessary jargon. \
If you don't know something, say so rather than speculating.

═══ PORTFOLIO CONTEXT ═══
Portfolio:    {name}
Total Value:  ${total_value:,.0f}
Strategy:     {strategy}
Positions:    {portfolio_data.get("positions_count", "N/A")}

Sector Allocation:
{sector_str}

Top Positions:
{top_pos_str}

Risk Metrics:
- Volatility:   {risk.get("volatility", "N/A")}%
- Sharpe Ratio: {risk.get("sharpe_ratio", "N/A")}
- Max Drawdown: {risk.get("max_drawdown", "N/A")}%

Performance:
- YTD Return: {perf.get("ytd_return", "N/A")}%
- MTD Return: {perf.get("mtd_return", "N/A")}%

═══ CURRENT MARKET CONTEXT (from RAG) ═══
{rag_context}
═══════════════════════════════════════

Answer the user's question using the above data. \
Reference specific numbers and tickers where relevant."""

    @staticmethod
    def _format_rag_context(results: list) -> str:
        if not results:
            return "No relevant market context available."
        lines = []
        for i, r in enumerate(results[:5], 1):
            meta     = r.get("metadata", {})
            date_str = meta.get("date", meta.get("published_at", meta.get("period", "N/A")))
            snippet  = r.get("document", "")[:180]
            lines.append(f"[{i}] {r.get('collection', 'unknown')} ({date_str}): {snippet}")
        return "\n".join(lines)
