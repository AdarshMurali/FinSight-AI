"""
AI Change Narrator — Task 3.2
==============================
Combines PositionChangeDetector (structured changes) + MarketRAGEngine (context)
+ LLMService (Claude) to produce causality narratives for portfolio changes.
"""

import sys
import os
from typing import Optional
from datetime import date
from sqlalchemy.orm import Session

from services.position_detector import PositionChangeDetector
from services.llm_service import LLMService, PromptLibrary
from rag.query_engine import MarketRAGEngine


class AIChangeNarrator:
    """
    Explains WHY portfolio position changes happened by correlating
    detected changes with market events, news, and macro context via RAG.
    """

    def __init__(self, db: Session, llm: Optional[LLMService] = None):
        self.db       = db
        self.detector = PositionChangeDetector(db)
        self.rag      = MarketRAGEngine()
        self.llm      = llm or LLMService()

    def narrate(
        self,
        portfolio_id: int,
        start_date: date,
        end_date: date,
        threshold_percent: float = 5.0,
    ) -> dict:
        """
        Detect significant position changes and generate a causal narrative.

        Returns:
            narrative     : str  — AI-generated causality story
            changes_data  : dict — raw detected changes
            rag_sources   : list — context documents used
            usage         : dict — token and cost info
        """
        changes_data = self.detector.detect_significant_changes(
            portfolio_id, start_date, end_date, threshold_percent
        )

        significant = changes_data.get("significant_changes", [])
        tickers = [
            c.get("ticker_symbol", "") or c.get("security_name", "")
            for c in significant[:5]
            if c.get("ticker_symbol") or c.get("security_name")
        ]
        sectors = list({c.get("sector", "") for c in significant if c.get("sector")})

        rag_query = (
            f"portfolio position changes {start_date} to {end_date} "
            f"{'  '.join(tickers)} sectors: {'  '.join(sectors[:3])}"
        )
        rag_results = self.rag.retrieve_context(rag_query, n_results=10)
        rag_context = self._format_rag_context(rag_results)

        prompt = PromptLibrary.change_narrator(changes_data, rag_context)
        narrative = self.llm.generate(prompt, task_type="analysis", max_tokens=1400)

        return {
            "portfolio_id":   portfolio_id,
            "period":         f"{start_date} to {end_date}",
            "changes_count":  len(significant),
            "narrative":      narrative,
            "changes_data":   changes_data,
            "rag_sources":    [{"collection": r["collection"], "snippet": r["document"][:120]} for r in rag_results[:5]],
            "llm_usage":      self.llm.get_usage_stats(),
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
            prefix = f"[{ticker}] " if ticker else ""
            lines.append(f"[{i}] {r['collection']} ({date_str}): {prefix}{r['document'][:200]}")
        return "\n".join(lines)
