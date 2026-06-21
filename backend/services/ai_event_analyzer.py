"""
AI Event Analyzer — Task 3.2
==============================
Combines EventImpactAnalyzer (structured impact) + MarketRAGEngine (context)
+ LLMService (Claude Opus) to produce deep event impact assessments.
"""

import sys
import os
from typing import Optional, List
from sqlalchemy.orm import Session

from services.event_analyzer import EventImpactAnalyzer
from services.llm_service import LLMService, PromptLibrary
from rag.query_engine import MarketRAGEngine


class AIEventAnalyzer:
    """
    Analyzes a market event's impact on portfolios with deep AI reasoning.
    Uses Claude Opus for this task (complex, multi-factor analysis).
    """

    def __init__(self, db: Session, llm: Optional[LLMService] = None):
        self.db       = db
        self.analyzer = EventImpactAnalyzer(db)
        self.rag      = MarketRAGEngine()
        self.llm      = llm or LLMService()

    def analyze(
        self,
        event_id: int,
        portfolio_ids: Optional[List[int]] = None,
        depth: str = "deep",
    ) -> dict:
        """
        Analyze a market event and its portfolio impact with AI reasoning.

        Args:
            event_id      : market event ID from SQL Server
            portfolio_ids : optional subset of portfolios to analyze
            depth         : "deep" (Opus) or "analysis" (Sonnet)

        Returns:
            ai_assessment : str  — AI-generated impact assessment
            event_data    : dict — raw structured impact data
            rag_sources   : list — context documents used
            usage         : dict — token and cost info
        """
        event_data = self.analyzer.analyze_event_impact(event_id, portfolio_ids)

        event_title   = event_data.get("event_title", "")
        affected_secs = event_data.get("affected_sectors", [])
        event_type    = event_data.get("event_type", "")

        rag_query = (
            f"{event_title} {event_type} market impact "
            f"sectors: {' '.join(affected_secs[:4]) if isinstance(affected_secs, list) else str(affected_secs)}"
        )
        rag_results = self.rag.retrieve_context(rag_query, n_results=12)
        rag_context = self._format_rag_context(rag_results)

        prompt = PromptLibrary.event_analyzer(event_data, rag_context)
        ai_assessment = self.llm.generate(prompt, task_type=depth, max_tokens=1600)

        return {
            "event_id":     event_id,
            "ai_assessment": ai_assessment,
            "event_data":   event_data,
            "rag_sources":  [{"collection": r["collection"], "snippet": r["document"][:120]} for r in rag_results[:5]],
            "llm_usage":    self.llm.get_usage_stats(),
        }

    def quick_event_summary(self, event_id: int) -> str:
        """Two-sentence event summary using Haiku."""
        event_data = self.analyzer.analyze_event_impact(event_id)
        prompt = (
            f"In 2 sentences, summarize this market event and its key portfolio risk:\n"
            f"Event: {event_data.get('event_title')}\n"
            f"Type: {event_data.get('event_type')} | Level: {event_data.get('impact_level')}\n"
            f"Sectors: {event_data.get('affected_sectors')}\n"
            f"Portfolios affected: {event_data.get('portfolios_affected')}"
        )
        return self.llm.generate(prompt, task_type="quick", max_tokens=150)

    @staticmethod
    def _format_rag_context(results: list) -> str:
        if not results:
            return "No relevant market context retrieved."
        lines = []
        for i, r in enumerate(results[:8], 1):
            meta = r.get("metadata", {})
            date_str = meta.get("date", meta.get("published_at", meta.get("period", "N/A")))
            lines.append(
                f"[{i}] {r['collection']} ({date_str}) "
                f"[relevance: {r.get('relevance_score', 0):.2f}]: {r['document'][:220]}"
            )
        return "\n".join(lines)
