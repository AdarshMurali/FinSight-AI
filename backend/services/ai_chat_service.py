"""
AI Chat Service — Task 3.4a (Agentic Upgrade)
==============================================
Upgrades /chat from static context injection to GPT-4o autonomous tool calling.

Before: user question → [pre-loaded data block] → GPT-4o → answer
After:  user question → GPT-4o thinks → calls tools → gets live data → answer

Flow:
  1. Build system prompt (no data pre-loaded — LLM decides what to fetch)
  2. Non-streaming tool-calling loop: GPT-4o picks tools, we execute them
  3. Yield {"tool_call": name} events so the frontend can show progress
  4. Streaming final answer: yield {"token": str} chunks
"""

import sys
import os
import json
from typing import Iterator
from sqlalchemy.orm import Session
from openai import OpenAI
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'rag'))

from services.ai_tools import TOOL_DEFINITIONS, execute_tool

load_dotenv()

MAX_TOOL_ITERATIONS = 5

SUGGESTED_QUESTIONS = [
    "What are the main risks in this portfolio?",
    "Which sectors have the highest concentration?",
    "What changed in my positions over the last 3 months?",
    "What market events affected the energy sector recently?",
    "Run a full risk analysis and give me recommendations",
    "Explain the current performance trend and key drivers",
]

_SYSTEM_PROMPT = """\
You are a senior portfolio manager AI for FinSight AI, a hedge fund portfolio intelligence platform.

You have tools to fetch live portfolio data. ALWAYS call the appropriate tool(s) before answering \
— never guess or fabricate numbers.

Tool selection guide:
  • Current state, sector allocation, performance, risk metrics  → get_portfolio_data
  • What changed, buys/sells, rebalancing in a time period       → get_position_history
  • Why something happened, macro/news context, sector trends    → search_market_context
  • Fed decisions, geopolitical events, policy shocks            → get_market_events
  • Concentration risk, overweights, rebalancing recommendations → run_risk_analysis

After receiving tool results, give a clear, specific analysis that cites exact numbers and tickers. \
Use plain English. Highlight causal relationships between events and portfolio movements. \
If ChromaDB is unavailable, work with the SQL data you have and note the limitation."""


class AIChatService:
    def __init__(self, db: Session):
        self.db = db
        self._client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

    def stream_response(
        self,
        portfolio_id: int,
        user_message: str,
        conversation_history: list[dict],
    ) -> Iterator[dict]:
        """
        Yields dicts:
          {"tool_call": str}  — emitted each time GPT-4o invokes a tool
          {"token": str}      — streamed text chunks of the final answer
        """
        messages: list = [
            {
                "role": "system",
                "content": f"{_SYSTEM_PROMPT}\n\nThe user is asking about portfolio #{portfolio_id}.",
            },
            *conversation_history[-(MAX_TOOL_ITERATIONS * 4):],  # last 8 turns max
            {"role": "user", "content": user_message},
        ]

        used_tools = False

        # ── Agentic tool-calling loop (non-streaming for clean arg collection) ─
        for _ in range(MAX_TOOL_ITERATIONS):
            response = self._client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
            )

            choice = response.choices[0]

            if choice.finish_reason != "tool_calls":
                if not used_tools:
                    # LLM answered directly without any tools — yield as-is
                    yield {"token": choice.message.content or ""}
                    return
                # Tools were used; break to make the streaming call below
                break

            used_tools = True

            # Append assistant's tool-call message to thread
            tool_calls = choice.message.tool_calls
            messages.append({
                "role": "assistant",
                "content": choice.message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ],
            })

            # Execute each tool and append results
            for tc in tool_calls:
                yield {"tool_call": tc.function.name}
                try:
                    args = json.loads(tc.function.arguments)
                    result = execute_tool(tc.function.name, args, self.db)
                except Exception as exc:
                    result = {"error": str(exc)}

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, default=str),
                })

        # ── Stream the final answer after all tools are resolved ─────────────
        stream = self._client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            stream=True,
        )

        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield {"token": delta.content}
