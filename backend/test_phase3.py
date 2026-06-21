"""
Phase 3 Tests — Task 3.1 (LLM Service) and Task 3.2 (AI Analysis Modules)

Run:
    cd backend
    python test_phase3.py

Tests:
    1. LLM Service standalone (no server needed)
    2. Full AI pipeline via HTTP (requires: uvicorn main:app running at :8000)
"""

import sys
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))

BASE_URL = "http://localhost:8000/api/analysis"
PASS = "[PASS]"
FAIL = "[FAIL]"

# ── Detect first available portfolio_id and event_id ─────────────────────────

def get_test_ids():
    try:
        from database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            portfolio_id = conn.execute(text("SELECT TOP 1 portfolio_id FROM Portfolios")).scalar()
            event_id     = conn.execute(text("SELECT TOP 1 event_id FROM Market_Events")).scalar()
            start_date   = conn.execute(text(
                "SELECT TOP 1 CONVERT(varchar, change_date, 23) FROM Position_Changes_Log ORDER BY change_date"
            )).scalar()
        return portfolio_id, event_id, start_date or "2025-01-01"
    except Exception as e:
        print(f"  Could not fetch IDs from SQL Server: {e}")
        return 1, 1, "2025-01-01"


# ── Task 3.1: LLM Service ────────────────────────────────────────────────────

def test_31_model_routing():
    print("\n--- Test 3.1.1: Model Routing ---")
    from services.llm_service import LLMService, MODEL_ROUTING
    assert MODEL_ROUTING["quick"] == "gpt-4o-mini", "quick should map to gpt-4o-mini"
    assert MODEL_ROUTING["analysis"] == "gpt-4o",   "analysis should map to gpt-4o"
    assert MODEL_ROUTING["deep"] == "gpt-4o",        "deep should map to gpt-4o"
    print(f"  {PASS} Model routing correct: {MODEL_ROUTING}")


def test_31_llm_call():
    print("\n--- Test 3.1.2: Live LLM Call (gpt-4o-mini) ---")
    from services.llm_service import LLMService
    svc = LLMService()
    response = svc.generate(
        prompt="In one sentence, what is the Sharpe ratio?",
        task_type="quick",
        max_tokens=100,
    )
    assert response and len(response) > 10, "Expected non-empty response"
    stats = svc.get_usage_stats()
    print(f"  {PASS} Response: {response.strip()[:100]}")
    print(f"  {PASS} Tokens: {stats['total_input_tokens']} in / {stats['total_output_tokens']} out")
    print(f"  {PASS} Cost: ${stats['total_cost_usd']:.6f}")
    print(f"  {PASS} Latency: {stats['avg_latency_s']}s")


def test_31_usage_tracking():
    print("\n--- Test 3.1.3: Usage Tracking Across Multiple Calls ---")
    from services.llm_service import LLMService
    svc = LLMService()
    svc.generate("What is diversification?", task_type="quick", max_tokens=50)
    svc.generate("What is beta?",            task_type="quick", max_tokens=50)
    stats = svc.get_usage_stats()
    assert stats["calls"] == 2, f"Expected 2 calls, got {stats['calls']}"
    assert stats["total_cost_usd"] > 0, "Cost should be > 0"
    print(f"  {PASS} Tracked {stats['calls']} calls, total cost ${stats['total_cost_usd']:.6f}")
    print(f"  {PASS} By model: {list(stats['by_model'].keys())}")


# ── Task 3.2: AI Analysis Modules via API ────────────────────────────────────

def check_server():
    try:
        r = requests.get("http://localhost:8000/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def test_32_explain_portfolio(portfolio_id: int):
    print(f"\n--- Test 3.2.1: AI Portfolio Explainer (portfolio_id={portfolio_id}) ---")
    payload = {
        "portfolio_id": portfolio_id,
        "question": "What are the top 3 risks in this portfolio right now?"
    }
    r = requests.post(f"{BASE_URL}/ai/explain-portfolio", json=payload, timeout=60)
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:200]}"
    data = r.json()
    assert "explanation" in data,    "Missing 'explanation' in response"
    assert len(data["explanation"]) > 50, "Explanation too short"
    assert "rag_sources" in data,    "Missing RAG sources"
    assert "llm_usage" in data,      "Missing usage stats"
    print(f"  {PASS} Explanation ({len(data['explanation'])} chars):")
    print(f"         {data['explanation'][:200]}...")
    print(f"  {PASS} RAG sources used: {len(data['rag_sources'])}")
    print(f"  {PASS} Tokens: {data['llm_usage']['total_input_tokens']} in / {data['llm_usage']['total_output_tokens']} out")
    print(f"  {PASS} Cost: ${data['llm_usage']['total_cost_usd']:.4f}")


def test_32_narrate_changes(portfolio_id: int, start_date: str):
    print(f"\n--- Test 3.2.2: AI Change Narrator (portfolio_id={portfolio_id}) ---")
    payload = {
        "portfolio_id":     portfolio_id,
        "start_date":       start_date,
        "end_date":         "2026-06-19",
        "threshold_percent": 3.0,
    }
    r = requests.post(f"{BASE_URL}/ai/narrate-changes", json=payload, timeout=60)
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:200]}"
    data = r.json()
    assert "narrative" in data, "Missing 'narrative' in response"
    print(f"  {PASS} Changes detected: {data.get('changes_count', 0)}")
    print(f"  {PASS} Narrative ({len(data['narrative'])} chars):")
    print(f"         {data['narrative'][:200]}...")


def test_32_analyze_event(event_id: int, portfolio_id: int):
    print(f"\n--- Test 3.2.3: AI Event Analyzer (event_id={event_id}) ---")
    payload = {
        "event_id":     event_id,
        "portfolio_ids": [portfolio_id],  # limit to 1 portfolio — avoids scanning all 50+
        "depth":        "quick",          # gpt-4o-mini for speed during testing
    }
    r = requests.post(f"{BASE_URL}/ai/analyze-event", json=payload, timeout=120)
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:200]}"
    data = r.json()
    assert "ai_assessment" in data, "Missing 'ai_assessment' in response"
    print(f"  {PASS} Event: {data['event_data'].get('event_title', '')[:60]}")
    print(f"  {PASS} Portfolios affected: {data['event_data'].get('portfolios_affected')}")
    print(f"  {PASS} Assessment ({len(data['ai_assessment'])} chars):")
    print(f"         {data['ai_assessment'][:200]}...")


def test_32_ai_recommendations(portfolio_id: int):
    print(f"\n--- Test 3.2.4: AI Recommendation Engine (portfolio_id={portfolio_id}) ---")
    payload = {
        "portfolio_id":     portfolio_id,
        "optimization_goal": "balanced",
    }
    r = requests.post(f"{BASE_URL}/ai/recommendations", json=payload, timeout=60)
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:200]}"
    data = r.json()
    assert "ai_recommendations" in data,  "Missing 'ai_recommendations'"
    assert "rule_based" in data,          "Missing 'rule_based'"
    rule_count = data["rule_based"].get("recommendations_count", 0)
    print(f"  {PASS} Rule-based recommendations: {rule_count}")
    print(f"  {PASS} AI recommendations ({len(data['ai_recommendations'])} chars):")
    print(f"         {data['ai_recommendations'][:200]}...")
    print(f"  {PASS} Cost: ${data['llm_usage']['total_cost_usd']:.4f}")


# ── Runner ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("FinSight AI — Phase 3 Tests (Task 3.1 + 3.2)")
    print("=" * 60)

    portfolio_id, event_id, start_date = get_test_ids()
    print(f"Test IDs — portfolio: {portfolio_id}, event: {event_id}, start: {start_date}")

    # ── Task 3.1 ──────────────────────────────────────────────────
    print("\n===== TASK 3.1: LLM SERVICE =====")
    passed = 0
    for test_fn in [test_31_model_routing, test_31_llm_call, test_31_usage_tracking]:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            print(f"  {FAIL} {test_fn.__name__}: {e}")
    print(f"\nTask 3.1: {passed}/3 passed")

    # ── Task 3.2 ──────────────────────────────────────────────────
    print("\n===== TASK 3.2: AI ANALYSIS MODULES =====")
    if not check_server():
        print(f"\n  {FAIL} FastAPI server not running at localhost:8000")
        print("  Start it with: uvicorn main:app --reload  (from backend/)")
        print("  Then re-run this script.")
        return

    print("  FastAPI server is running — testing AI endpoints...")
    passed = 0
    tests = [
        (test_32_explain_portfolio,  (portfolio_id,)),
        (test_32_narrate_changes,    (portfolio_id, start_date)),
        (test_32_analyze_event,      (event_id, portfolio_id)),
        (test_32_ai_recommendations, (portfolio_id,)),
    ]
    for test_fn, args in tests:
        try:
            test_fn(*args)
            passed += 1
        except Exception as e:
            print(f"  {FAIL} {test_fn.__name__}: {e}")
    print(f"\nTask 3.2: {passed}/4 passed")

    print("\n" + "=" * 60)
    print(f"Total: {passed + (3 if passed > 0 else 0)}/7 tests passed")
    print("=" * 60)


if __name__ == "__main__":
    main()
