"""
AI Recommendation Engine — Task 3.2
=====================================
Combines RecommendationEngine (rule-based) + MarketRAGEngine (market context)
+ LLMService (Claude) to produce AI-enhanced portfolio rebalancing suggestions.
"""

import sys
import os
from typing import Optional
from sqlalchemy.orm import Session

from services.recommendation_engine import RecommendationEngine
from services.portfolio_analyzer import PortfolioAnalyzer
from services.llm_service import LLMService, PromptLibrary
from rag.query_engine import MarketRAGEngine


class AIRecommendationEngine:
    """
    Enhances rule-based portfolio recommendations with AI reasoning
    grounded in current macro, news, analyst views, and earnings context.
    """

    def __init__(self, db: Session, llm: Optional[LLMService] = None):
        self.db          = db
        self.rule_engine = RecommendationEngine(db)
        self.analyzer    = PortfolioAnalyzer(db)
        self.rag         = MarketRAGEngine()
        self.llm         = llm or LLMService()

    def recommend(
        self,
        portfolio_id: int,
        risk_tolerance: Optional[str] = None,
        optimization_goal: str = "balanced",
    ) -> dict:
        """
        Generate AI-enhanced portfolio recommendations.

        Returns:
            ai_recommendations : str  — AI-generated actionable suggestions
            rule_based         : dict — quantitative rule-based output
            portfolio_snapshot : dict — current portfolio state
            rag_sources        : list — context documents used
            usage              : dict — token and cost info
        """
        rule_output = self.rule_engine.generate_recommendations(
            portfolio_id, risk_tolerance, optimization_goal
        )
        portfolio_data = self.analyzer.analyze_portfolio_state(portfolio_id)

        top_sectors = list(portfolio_data.get("sector_allocation", {}).keys())[:4]
        rag_query = (
            f"portfolio rebalancing recommendations {optimization_goal} "
            f"sectors {' '.join(top_sectors)} "
            f"analyst outlook macro outlook risk"
        )
        rag_results = self.rag.retrieve_context(rag_query, n_results=10)
        rag_context = self._format_rag_context(rag_results)

        rule_recs = rule_output.get("recommendations", [])

        # Enrich portfolio_data with strategy info for prompt
        portfolio_data["strategy_type"] = (
            self.db.execute(
                __import__("sqlalchemy").text(
                    "SELECT strategy_type FROM Portfolios WHERE portfolio_id = :pid"
                ),
                {"pid": portfolio_id}
            ).scalar()
        )

        prompt = PromptLibrary.ai_recommendations(portfolio_data, rule_recs, rag_context)
        ai_recs = self.llm.generate(prompt, task_type="recommendations", max_tokens=1500)

        return {
            "portfolio_id":       portfolio_id,
            "optimization_goal":  optimization_goal,
            "risk_tolerance":     risk_tolerance or portfolio_data.get("risk_tolerance", "medium"),
            "ai_recommendations": ai_recs,
            "rule_based":         rule_output,
            "portfolio_snapshot": {
                "total_value":      portfolio_data.get("total_value"),
                "sector_allocation": portfolio_data.get("sector_allocation"),
                "risk_metrics":     portfolio_data.get("risk_metrics"),
            },
            "rag_sources":  [{"collection": r["collection"], "snippet": r["document"][:120]} for r in rag_results[:5]],
            "llm_usage":    self.llm.get_usage_stats(),
        }

    @staticmethod
    def _format_rag_context(results: list) -> str:
        if not results:
            return "No relevant market context retrieved."
        lines = []
        for i, r in enumerate(results[:8], 1):
            meta = r.get("metadata", {})
            date_str = meta.get("date", meta.get("published_at", meta.get("period", "N/A")))
            ticker = meta.get("ticker", "")
            label = f"[{ticker}] " if ticker else ""
            lines.append(f"[{i}] {r['collection']} ({date_str}): {label}{r['document'][:200]}")
        return "\n".join(lines)
