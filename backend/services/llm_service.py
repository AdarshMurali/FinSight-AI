"""
LLM Service — Task 3.1
======================
Abstraction layer over OpenAI GPT models with:
  - Task-based model routing (gpt-4o-mini/gpt-4o by complexity)
  - Token and cost tracking across the session
  - Centralized prompt template library
"""

import os
import time
from typing import Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ── Model routing ─────────────────────────────────────────────────────────────
# task_type → model ID
MODEL_ROUTING: dict[str, str] = {
    "quick":           "gpt-4o-mini",  # fast summaries, simple Q&A
    "analysis":        "gpt-4o",       # portfolio explanations, narratives
    "recommendations": "gpt-4o",       # rebalancing suggestions
    "deep":            "gpt-4o",       # complex event / risk analysis
}

# Approximate USD per 1M tokens (OpenAI list pricing)
_INPUT_COST: dict[str, float] = {
    "gpt-4o-mini": 0.15,
    "gpt-4o":      2.50,
}
_OUTPUT_COST: dict[str, float] = {
    "gpt-4o-mini":  0.60,
    "gpt-4o":      10.00,
}


@dataclass
class UsageRecord:
    model: str
    task_type: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_s: float
    timestamp: float = field(default_factory=time.time)


class LLMService:
    """
    Central LLM service used by all AI analysis modules.

    Usage:
        svc = LLMService()
        response = svc.generate(
            prompt="Explain this portfolio...",
            task_type="analysis",
            system_prompt="You are a senior portfolio manager."
        )
        print(svc.get_usage_stats())
    """

    def __init__(self, api_key: Optional[str] = None):
        self._client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY", ""))
        self._usage: list[UsageRecord] = []

    def generate(
        self,
        prompt: str,
        task_type: str = "analysis",
        system_prompt: Optional[str] = None,
        max_tokens: int = 1500,
    ) -> str:
        """
        Call the appropriate GPT model for the given task type.
        Returns the text response. Tracks tokens and cost internally.
        """
        model = MODEL_ROUTING.get(task_type, MODEL_ROUTING["analysis"])
        system = system_prompt or PromptLibrary.system_prompt(task_type)

        t0 = time.time()
        resp = self._client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": prompt},
            ],
        )
        latency = time.time() - t0

        input_tokens  = resp.usage.prompt_tokens
        output_tokens = resp.usage.completion_tokens
        cost = (
            input_tokens  / 1_000_000 * _INPUT_COST.get(model, 2.50) +
            output_tokens / 1_000_000 * _OUTPUT_COST.get(model, 10.0)
        )

        self._usage.append(UsageRecord(
            model=model,
            task_type=task_type,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=round(cost, 6),
            latency_s=round(latency, 2),
        ))

        return resp.choices[0].message.content

    def get_usage_stats(self) -> dict:
        """Return aggregated token and cost summary for this session."""
        if not self._usage:
            return {"calls": 0, "total_input_tokens": 0, "total_output_tokens": 0, "total_cost_usd": 0.0}

        by_model: dict[str, dict] = {}
        for r in self._usage:
            if r.model not in by_model:
                by_model[r.model] = {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}
            by_model[r.model]["calls"]         += 1
            by_model[r.model]["input_tokens"]  += r.input_tokens
            by_model[r.model]["output_tokens"] += r.output_tokens
            by_model[r.model]["cost_usd"]      += r.cost_usd

        return {
            "calls":               len(self._usage),
            "total_input_tokens":  sum(r.input_tokens  for r in self._usage),
            "total_output_tokens": sum(r.output_tokens for r in self._usage),
            "total_cost_usd":      round(sum(r.cost_usd for r in self._usage), 4),
            "avg_latency_s":       round(sum(r.latency_s for r in self._usage) / len(self._usage), 2),
            "by_model":            by_model,
        }


# ── Prompt Library ────────────────────────────────────────────────────────────

class PromptLibrary:
    """Centralized prompt templates for all AI analysis modules."""

    @staticmethod
    def system_prompt(task_type: str) -> str:
        prompts = {
            "quick": (
                "You are a concise financial analyst assistant for a hedge fund. "
                "Provide brief, accurate summaries. Use plain English. No jargon."
            ),
            "analysis": (
                "You are a senior portfolio manager at a quantitative hedge fund. "
                "You have deep expertise in equity markets, macro economics, and risk management. "
                "Your role is to explain portfolio states and market dynamics clearly and accurately. "
                "Always ground your analysis in the data provided. Be specific — cite numbers, tickers, and dates. "
                "Highlight causal relationships between market events and portfolio movements."
            ),
            "recommendations": (
                "You are a portfolio optimization specialist at an institutional investment firm. "
                "You provide actionable, risk-aware rebalancing recommendations. "
                "Consider transaction costs, tax implications, and risk limits. "
                "Prioritize recommendations by urgency and expected impact. "
                "Be specific: name the securities, suggest target weights, and explain the rationale."
            ),
            "deep": (
                "You are a chief investment officer with 20+ years of institutional investing experience. "
                "You specialize in macro event analysis, geopolitical risk, and portfolio stress testing. "
                "Provide deep, nuanced analysis that considers second-order effects, sector correlations, "
                "and historical precedents. Reference specific market data and events when available."
            ),
        }
        return prompts.get(task_type, prompts["analysis"])

    @staticmethod
    def portfolio_explainer(portfolio_data: dict, rag_context: str, question: str) -> str:
        return f"""You have been given structured portfolio data and relevant market context.
Analyze the portfolio and answer the question below.

PORTFOLIO DATA:
- Name: {portfolio_data.get('portfolio_name')}
- Total Value: ${portfolio_data.get('total_value', 0):,.0f}
- Positions: {portfolio_data.get('positions_count')}
- Sector Allocation: {portfolio_data.get('sector_allocation')}
- Top Concentration Risk: {portfolio_data.get('concentration_risk', {}).get('top_positions', [])[:3]}
- Performance (YTD): {portfolio_data.get('performance_summary', {}).get('ytd_return')}
- Sharpe Ratio: {portfolio_data.get('risk_metrics', {}).get('sharpe_ratio')}
- Volatility: {portfolio_data.get('risk_metrics', {}).get('volatility')}

RELEVANT MARKET CONTEXT (from ChromaDB RAG):
{rag_context}

QUESTION: {question}

Provide a clear, specific explanation. Reference the portfolio data and market context.
Highlight the most important factors driving the current portfolio state."""

    @staticmethod
    def change_narrator(changes_data: dict, rag_context: str) -> str:
        portfolio_name = changes_data.get("portfolio_name", "the portfolio")
        changes = changes_data.get("significant_changes", [])
        period = f"{changes_data.get('start_date')} to {changes_data.get('end_date')}"
        change_summary = "\n".join([
            f"  - {c.get('ticker', c.get('security_id'))}: "
            f"{c.get('old_weight', 0):.1f}% → {c.get('new_weight', 0):.1f}% "
            f"({c.get('change_type', '')})"
            for c in changes[:10]
        ])

        return f"""Analyze the following portfolio position changes and explain what drove them.

PORTFOLIO: {portfolio_name}
PERIOD: {period}
SIGNIFICANT CHANGES ({len(changes)} total):
{change_summary}

RELEVANT MARKET CONTEXT (news, macro data, earnings):
{rag_context}

Write a cohesive narrative (3-5 paragraphs) that:
1. Summarizes the overall portfolio shift
2. Identifies the most likely market drivers for each major change
3. Explains the causal chain (event → sentiment → position change)
4. Notes any patterns (risk-off rotation, sector rebalancing, earnings-driven moves)"""

    @staticmethod
    def event_analyzer(event_data: dict, rag_context: str) -> str:
        return f"""Analyze the impact of this market event on the affected portfolios.

EVENT:
- Title: {event_data.get('event_title')}
- Date: {event_data.get('event_date')}
- Type: {event_data.get('event_type')} | Impact Level: {event_data.get('impact_level')}
- Affected Sectors: {event_data.get('affected_sectors')}
- Affected Regions: {event_data.get('affected_regions')}
- Portfolios Affected: {event_data.get('portfolios_affected')} of {event_data.get('portfolios_analyzed')}

TOP EXPOSED PORTFOLIOS:
{event_data.get('portfolio_impacts', [])[:3]}

RELEVANT MARKET CONTEXT:
{rag_context}

Provide:
1. A concise event summary and why it matters for equity portfolios
2. Analysis of direct exposure (sectors, securities held)
3. Second-order effects (supply chains, correlations, sentiment)
4. Short-term vs medium-term expected impact
5. Recommended hedging or positioning actions"""

    @staticmethod
    def ai_recommendations(portfolio_data: dict, rule_based_recs: list, rag_context: str) -> str:
        def _priority_label(p) -> str:
            if isinstance(p, int):
                return "HIGH" if p >= 7 else "MEDIUM" if p >= 4 else "LOW"
            return str(p).upper()

        rec_summary = "\n".join([
            f"  [{_priority_label(r.get('priority', 'medium'))}] {r.get('type', '')}: {r.get('description', '')}"
            for r in rule_based_recs[:8]
        ])

        return f"""You are reviewing a portfolio and a set of rule-based recommendations.
Enhance these recommendations with AI-driven insights from the current market context.

PORTFOLIO SNAPSHOT:
- Name: {portfolio_data.get('portfolio_name')}
- Value: ${portfolio_data.get('total_value', 0):,.0f}
- Strategy: {portfolio_data.get('strategy_type', 'N/A')}
- Sector Allocation: {portfolio_data.get('sector_allocation')}
- Risk Metrics: {portfolio_data.get('risk_metrics')}

RULE-BASED RECOMMENDATIONS (from quantitative analysis):
{rec_summary}

CURRENT MARKET CONTEXT (macro, news, analyst views):
{rag_context}

Provide enhanced recommendations that:
1. Validate or challenge each rule-based recommendation with market context
2. Add market-timing considerations (is now a good time to act?)
3. Identify opportunities the rules may have missed (sentiment shifts, upcoming catalysts)
4. Suggest specific securities to add/reduce with target weights
5. Prioritize by expected risk-adjusted impact

Format as clear, actionable bullet points grouped by urgency (Immediate / Near-term / Strategic)."""
