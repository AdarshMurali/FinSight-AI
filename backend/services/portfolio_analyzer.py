from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any, Optional
from datetime import date, datetime, timedelta
from decimal import Decimal
import numpy as np

from models import Portfolio, Position, Security, PortfolioPerformance


class PortfolioAnalyzer:
    """Analyzes portfolio metrics, allocations, and risk exposures"""

    def __init__(self, db: Session):
        self.db = db

    def analyze_portfolio_state(
        self,
        portfolio_id: int,
        as_of_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Complete analysis of portfolio state"""
        if not as_of_date:
            as_of_date = date.today()

        portfolio = self.db.query(Portfolio).filter(
            Portfolio.portfolio_id == portfolio_id
        ).first()

        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found")

        positions = self.db.query(Position).filter(
            Position.portfolio_id == portfolio_id
        ).all()

        sector_allocation = self._calculate_sector_allocation(positions)
        region_allocation = self._calculate_region_allocation(positions)
        asset_allocation = self._calculate_asset_allocation(positions)
        risk_metrics = self._calculate_risk_metrics(portfolio_id, as_of_date)
        concentration_risk = self._calculate_concentration_risk(positions)
        performance_summary = self._get_performance_summary(portfolio_id, as_of_date)

        return {
            "portfolio_id": portfolio_id,
            "portfolio_name": portfolio.portfolio_name,
            "analysis_date": as_of_date.isoformat(),
            "total_value": float(portfolio.total_value) if portfolio.total_value else 0,
            "cash_balance": float(portfolio.cash_balance) if portfolio.cash_balance else 0,
            "positions_count": len(positions),
            "sector_allocation": sector_allocation,
            "region_allocation": region_allocation,
            "asset_allocation": asset_allocation,
            "risk_metrics": risk_metrics,
            "concentration_risk": concentration_risk,
            "performance_summary": performance_summary,
        }

    def _calculate_sector_allocation(self, positions) -> Dict[str, float]:
        """Calculate portfolio allocation by sector"""
        sector_weights = {}
        for position in positions:
            security = self.db.query(Security).filter(
                Security.security_id == position.security_id
            ).first()

            if security and security.sector:
                sector = security.sector
                weight = float(position.weight or 0)
                sector_weights[sector] = sector_weights.get(sector, 0) + weight

        return sector_weights

    def _calculate_region_allocation(self, positions) -> Dict[str, float]:
        """Calculate portfolio allocation by region/country"""
        region_weights = {}
        for position in positions:
            security = self.db.query(Security).filter(
                Security.security_id == position.security_id
            ).first()

            if security and security.country:
                country = security.country
                weight = float(position.weight or 0)
                region_weights[country] = region_weights.get(country, 0) + weight

        return region_weights

    def _calculate_asset_allocation(self, positions) -> Dict[str, float]:
        """Calculate portfolio allocation by asset type"""
        asset_weights = {}
        for position in positions:
            security = self.db.query(Security).filter(
                Security.security_id == position.security_id
            ).first()

            if security and security.security_type:
                asset_type = security.security_type
                weight = float(position.weight or 0)
                asset_weights[asset_type] = asset_weights.get(asset_type, 0) + weight

        return asset_weights

    def _calculate_risk_metrics(
        self,
        portfolio_id: int,
        as_of_date: date
    ) -> Dict[str, Any]:
        """Calculate portfolio risk metrics"""
        start_date = as_of_date - timedelta(days=365)

        performance_data = self.db.query(PortfolioPerformance).filter(
            PortfolioPerformance.portfolio_id == portfolio_id,
            PortfolioPerformance.as_of_date >= start_date,
            PortfolioPerformance.as_of_date <= as_of_date
        ).order_by(PortfolioPerformance.as_of_date).all()

        if not performance_data:
            return {
                "volatility": None,
                "sharpe_ratio": None,
                "max_drawdown": None,
                "data_points": 0
            }

        latest_performance = performance_data[-1] if performance_data else None

        daily_returns = [float(p.daily_return) for p in performance_data if p.daily_return]

        if daily_returns and len(daily_returns) > 1:
            volatility = float(np.std(daily_returns) * np.sqrt(252))
        else:
            volatility = float(latest_performance.volatility) if latest_performance and latest_performance.volatility else None

        return {
            "volatility": volatility,
            "sharpe_ratio": float(latest_performance.sharpe_ratio) if latest_performance and latest_performance.sharpe_ratio else None,
            "max_drawdown": float(latest_performance.max_drawdown) if latest_performance and latest_performance.max_drawdown else None,
            "data_points": len(performance_data)
        }

    def _calculate_concentration_risk(self, positions) -> Dict[str, Any]:
        """Detect portfolio concentration risks"""
        weights = [float(pos.weight or 0) for pos in positions]

        if not weights:
            return {
                "herfindahl_index": 0,
                "largest_position": 0,
                "top_5_positions": 0,
                "top_10_positions": 0
            }

        herfindahl_index = sum(w**2 for w in weights)

        weights.sort(reverse=True)

        return {
            "herfindahl_index": herfindahl_index,
            "largest_position": weights[0] if weights else 0,
            "top_5_positions": sum(weights[:5]) if len(weights) >= 5 else sum(weights),
            "top_10_positions": sum(weights[:10]) if len(weights) >= 10 else sum(weights)
        }

    def _get_performance_summary(
        self,
        portfolio_id: int,
        as_of_date: date
    ) -> Dict[str, Any]:
        """Get recent performance summary"""
        latest_performance = self.db.query(PortfolioPerformance).filter(
            PortfolioPerformance.portfolio_id == portfolio_id,
            PortfolioPerformance.as_of_date <= as_of_date
        ).order_by(PortfolioPerformance.as_of_date.desc()).first()

        if not latest_performance:
            return {}

        return {
            "as_of_date": latest_performance.as_of_date.isoformat(),
            "total_value": float(latest_performance.total_value) if latest_performance.total_value else None,
            "daily_return": float(latest_performance.daily_return) if latest_performance.daily_return else None,
            "mtd_return": float(latest_performance.mtd_return) if latest_performance.mtd_return else None,
            "ytd_return": float(latest_performance.ytd_return) if latest_performance.ytd_return else None,
        }
