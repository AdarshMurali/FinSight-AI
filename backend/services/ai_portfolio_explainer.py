"""
AI Portfolio Explainer — Task 3.2
==================================
Combines PortfolioAnalyzer (structured data) + MarketRAGEngine (context)
+ LLMService (Claude) to produce natural language portfolio explanations.
"""

import sys
import os
from typing import Optional
from datetime import date
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'rag'))

from services.portfolio_analyzer import PortfolioAnalyzer
from services.llm_service import LLMService, PromptLibrary
from rag.query_engine import MarketRAGEngine


class AIPortfolioExplainer:
    """
    Explains the current state of a portfolio in natural language,
    grounded in real portfolio data and RAG-retrieved market context.
    """

    def __init__(self, db: Session, llm: Optional[LLMService] = None):
        self.db       = db
        self.analyzer = PortfolioAnalyzer(db)
        self.rag      = MarketRAGEngine()
        self.llm      = llm or LLMService()

    def explain(
        self,
        portfolio_id: int,
        as_of_date: Optional[date] = None,
        question: str = "Explain the current state and key drivers of this portfolio.",
    ) -> dict:
        """
        Generate a natural language explanation of the portfolio state.

        Returns:
            explanation  : str  — AI-generated narrative
            portfolio_data: dict — raw structured analysis
            rag_sources  : list — documents used as context
            usage        : dict — token and cost info
        """
        portfolio_data = self.analyzer.analyze_portfolio_state(portfolio_id, as_of_date)

        rag_query = (
            f"{portfolio_data.get('portfolio_name', '')} portfolio analysis "
            f"sector allocation {list(portfolio_data.get('sector_allocation', {}).keys())[:3]}"
        )
        rag_results = self.rag.retrieve_context(rag_query, n_results=8)
        rag_context = self._format_rag_context(rag_results)

        prompt = PromptLibrary.portfolio_explainer(portfolio_data, rag_context, question)
        explanation = self.llm.generate(prompt, task_type="analysis", max_tokens=1200)

        return {
            "portfolio_id":   portfolio_id,
            "question":       question,
            "explanation":    explanation,
            "portfolio_data": portfolio_data,
            "rag_sources":    [{"collection": r["collection"], "snippet": r["document"][:120]} for r in rag_results[:5]],
            "llm_usage":      self.llm.get_usage_stats(),
        }

    def quick_summary(self, portfolio_id: int) -> str:
        """One-paragraph quick summary — uses Haiku for speed."""
        portfolio_data = self.analyzer.analyze_portfolio_state(portfolio_id)
        prompt = (
            f"Summarize this portfolio in one paragraph:\n"
            f"Name: {portfolio_data['portfolio_name']}\n"
            f"Value: ${portfolio_data['total_value']:,.0f}\n"
            f"Top sectors: {list(portfolio_data.get('sector_allocation', {}).items())[:3]}\n"
            f"YTD return: {portfolio_data.get('performance_summary', {}).get('ytd_return')}\n"
            f"Sharpe: {portfolio_data.get('risk_metrics', {}).get('sharpe_ratio')}"
        )
        return self.llm.generate(prompt, task_type="quick", max_tokens=300)

    @staticmethod
    def _format_rag_context(results: list) -> str:
        if not results:
            return "No relevant market context retrieved."
        lines = []
        for i, r in enumerate(results[:6], 1):
            meta = r.get("metadata", {})
            date_str = meta.get("date", meta.get("published_at", meta.get("period", "N/A")))
            lines.append(f"[{i}] {r['collection']} ({date_str}): {r['document'][:200]}")
        return "\n".join(lines)
