from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import date, datetime
import numpy as np

from models import Portfolio, Position, Security, PortfolioPerformance
from services.portfolio_analyzer import PortfolioAnalyzer


class RecommendationEngine:
    """Generates portfolio optimization recommendations"""

    def __init__(self, db: Session):
        self.db = db
        self.analyzer = PortfolioAnalyzer(db)

    def generate_recommendations(
        self,
        portfolio_id: int,
        risk_tolerance: Optional[str] = None,
        optimization_goal: str = "balanced"
    ) -> Dict[str, Any]:
        """Generate actionable portfolio recommendations"""
        portfolio = self.db.query(Portfolio).filter(
            Portfolio.portfolio_id == portfolio_id
        ).first()

        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found")

        if not risk_tolerance:
            # risk_profile lives on Customer, not Portfolio
            customer_risk = (
                portfolio.customer.risk_profile
                if portfolio.customer else None
            )
            risk_tolerance = customer_risk or "medium"

        analysis = self.analyzer.analyze_portfolio_state(portfolio_id)

        recommendations = []

        concentration_recs = self._check_concentration_risk(analysis)
        recommendations.extend(concentration_recs)

        sector_recs = self._check_sector_allocation(analysis, optimization_goal)
        recommendations.extend(sector_recs)

        risk_recs = self._check_risk_metrics(analysis, risk_tolerance)
        recommendations.extend(risk_recs)

        performance_recs = self._check_performance(portfolio_id)
        recommendations.extend(performance_recs)

        recommendations.sort(key=lambda x: x["priority"], reverse=True)

        return {
            "portfolio_id": portfolio_id,
            "portfolio_name": portfolio.portfolio_name,
            "risk_tolerance": risk_tolerance,
            "optimization_goal": optimization_goal,
            "analysis_date": date.today().isoformat(),
            "recommendations_count": len(recommendations),
            "recommendations": recommendations,
            "summary": self._generate_summary(recommendations)
        }

    def _check_concentration_risk(self, analysis: Dict) -> List[Dict[str, Any]]:
        """Check for concentration risk issues"""
        recommendations = []
        concentration = analysis["concentration_risk"]

        if concentration["largest_position"] > 15:
            recommendations.append({
                "type": "concentration",
                "priority": 8,
                "title": "High Single Position Concentration",
                "description": f"Largest position represents {concentration['largest_position']:.1f}% of portfolio",
                "action": "Consider reducing largest position to below 10-12% to mitigate idiosyncratic risk",
                "impact": "high"
            })

        if concentration["top_5_positions"] > 50:
            recommendations.append({
                "type": "concentration",
                "priority": 7,
                "title": "Top 5 Positions Concentration",
                "description": f"Top 5 positions represent {concentration['top_5_positions']:.1f}% of portfolio",
                "action": "Diversify holdings to reduce concentration in top positions",
                "impact": "medium"
            })

        return recommendations

    def _check_sector_allocation(
        self,
        analysis: Dict,
        optimization_goal: str
    ) -> List[Dict[str, Any]]:
        """Check sector allocation and suggest rebalancing"""
        recommendations = []
        sector_allocation = analysis["sector_allocation"]

        for sector, weight in sector_allocation.items():
            if weight > 30:
                recommendations.append({
                    "type": "sector_allocation",
                    "priority": 6,
                    "title": f"High {sector} Sector Exposure",
                    "description": f"{sector} sector represents {weight:.1f}% of portfolio",
                    "action": f"Consider reducing {sector} exposure to 20-25% range",
                    "impact": "medium"
                })

            if weight < 5 and optimization_goal == "diversified":
                recommendations.append({
                    "type": "sector_allocation",
                    "priority": 3,
                    "title": f"Low {sector} Sector Exposure",
                    "description": f"{sector} sector represents only {weight:.1f}% of portfolio",
                    "action": f"Consider increasing {sector} exposure for better diversification",
                    "impact": "low"
                })

        return recommendations

    def _check_risk_metrics(
        self,
        analysis: Dict,
        risk_tolerance: str
    ) -> List[Dict[str, Any]]:
        """Check risk metrics against risk tolerance"""
        recommendations = []
        risk_metrics = analysis["risk_metrics"]

        volatility = risk_metrics.get("volatility")
        sharpe_ratio = risk_metrics.get("sharpe_ratio")
        max_drawdown = risk_metrics.get("max_drawdown")

        risk_thresholds = {
            "low": {"volatility": 10, "max_drawdown": -10},
            "medium": {"volatility": 15, "max_drawdown": -15},
            "high": {"volatility": 25, "max_drawdown": -25}
        }

        threshold = risk_thresholds.get(risk_tolerance.lower(), risk_thresholds["medium"])

        if volatility and volatility > threshold["volatility"]:
            recommendations.append({
                "type": "risk",
                "priority": 7,
                "title": "High Portfolio Volatility",
                "description": f"Volatility of {volatility:.1f}% exceeds {risk_tolerance} risk tolerance threshold",
                "action": "Increase allocation to lower volatility assets or defensive sectors",
                "impact": "high"
            })

        if max_drawdown and max_drawdown < threshold["max_drawdown"]:
            recommendations.append({
                "type": "risk",
                "priority": 6,
                "title": "Significant Drawdown Risk",
                "description": f"Maximum drawdown of {max_drawdown:.1f}% exceeds tolerance",
                "action": "Implement downside protection strategies or reduce equity exposure",
                "impact": "high"
            })

        if sharpe_ratio and sharpe_ratio < 0.5:
            recommendations.append({
                "type": "performance",
                "priority": 5,
                "title": "Low Risk-Adjusted Returns",
                "description": f"Sharpe ratio of {sharpe_ratio:.2f} indicates poor risk-adjusted performance",
                "action": "Review holdings for underperformers or consider factor-based rebalancing",
                "impact": "medium"
            })

        return recommendations

    def _check_performance(self, portfolio_id: int) -> List[Dict[str, Any]]:
        """Check recent performance trends"""
        recommendations = []

        latest_perf = self.db.query(PortfolioPerformance).filter(
            PortfolioPerformance.portfolio_id == portfolio_id
        ).order_by(PortfolioPerformance.as_of_date.desc()).first()

        if not latest_perf:
            return recommendations

        ytd_return = float(latest_perf.ytd_return) if latest_perf.ytd_return else None

        if ytd_return and ytd_return < -5:
            recommendations.append({
                "type": "performance",
                "priority": 6,
                "title": "Negative YTD Performance",
                "description": f"Portfolio down {ytd_return:.1f}% year-to-date",
                "action": "Review underperforming positions and consider tax-loss harvesting opportunities",
                "impact": "medium"
            })

        return recommendations

    def _generate_summary(self, recommendations: List[Dict]) -> Dict[str, Any]:
        """Generate executive summary of recommendations"""
        high_priority = [r for r in recommendations if r["priority"] >= 7]
        medium_priority = [r for r in recommendations if 4 <= r["priority"] < 7]
        low_priority = [r for r in recommendations if r["priority"] < 4]

        return {
            "total_recommendations": len(recommendations),
            "high_priority_count": len(high_priority),
            "medium_priority_count": len(medium_priority),
            "low_priority_count": len(low_priority),
            "action_required": len(high_priority) > 0
        }
