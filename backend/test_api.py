"""
Test script for FinSight AI API endpoints
Demonstrates basic functionality of all API endpoints
"""

import requests
import json
from datetime import date, timedelta

BASE_URL = "http://localhost:8000"


def print_response(title, response):
    """Pretty print API response"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(json.dumps(data, indent=2, default=str)[:500])  # First 500 chars
    else:
        print(f"Error: {response.text}")


def test_health():
    """Test health check endpoint"""
    response = requests.get(f"{BASE_URL}/health")
    print_response("HEALTH CHECK", response)


def test_portfolios():
    """Test portfolio endpoints"""
    # Get all portfolios
    response = requests.get(f"{BASE_URL}/api/portfolios/")
    print_response("GET ALL PORTFOLIOS", response)

    # Get specific portfolio
    if response.status_code == 200 and response.json():
        portfolio_id = response.json()[0]["portfolio_id"]
        response = requests.get(f"{BASE_URL}/api/portfolios/{portfolio_id}")
        print_response(f"GET PORTFOLIO {portfolio_id}", response)

        # Get positions
        response = requests.get(f"{BASE_URL}/api/portfolios/{portfolio_id}/positions")
        print_response(f"GET POSITIONS FOR PORTFOLIO {portfolio_id}", response)

        # Get performance
        response = requests.get(f"{BASE_URL}/api/portfolios/{portfolio_id}/performance?limit=5")
        print_response(f"GET PERFORMANCE FOR PORTFOLIO {portfolio_id}", response)


def test_securities():
    """Test securities endpoints"""
    response = requests.get(f"{BASE_URL}/api/securities/?limit=5")
    print_response("GET SECURITIES (LIMIT 5)", response)


def test_market_events():
    """Test market events endpoints"""
    response = requests.get(f"{BASE_URL}/api/market-events/?limit=5")
    print_response("GET MARKET EVENTS (LIMIT 5)", response)


def test_analysis():
    """Test analysis endpoints"""
    # Get a portfolio ID first
    response = requests.get(f"{BASE_URL}/api/portfolios/")
    if response.status_code == 200 and response.json():
        portfolio_id = response.json()[0]["portfolio_id"]

        # Test portfolio state analysis
        payload = {
            "portfolio_id": portfolio_id,
            "as_of_date": date.today().isoformat()
        }
        response = requests.post(
            f"{BASE_URL}/api/analysis/portfolio-state",
            json=payload
        )
        print_response("PORTFOLIO STATE ANALYSIS", response)

        # Test position changes detection
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        payload = {
            "portfolio_id": portfolio_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "threshold_percent": 5.0
        }
        response = requests.post(
            f"{BASE_URL}/api/analysis/position-changes",
            json=payload
        )
        print_response("POSITION CHANGES DETECTION", response)

        # Test recommendations
        payload = {
            "portfolio_id": portfolio_id,
            "risk_tolerance": "medium",
            "optimization_goal": "balanced"
        }
        response = requests.post(
            f"{BASE_URL}/api/analysis/recommendations",
            json=payload
        )
        print_response("PORTFOLIO RECOMMENDATIONS", response)


if __name__ == "__main__":
    print("\n" + "="*60)
    print("FINSIGHT AI API TESTING")
    print("="*60)

    try:
        # Run tests
        test_health()
        test_portfolios()
        test_securities()
        test_market_events()
        test_analysis()

        print("\n" + "="*60)
        print("ALL TESTS COMPLETED")
        print("="*60)

    except requests.exceptions.ConnectionError:
        print("\n[ERROR] Cannot connect to API server.")
        print("Make sure the server is running at http://localhost:8000")
        print("Start it with: python main.py")
    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
