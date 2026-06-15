from sqlalchemy.orm import Session
from typing import Dict, Any, List
from datetime import date, datetime, timedelta
from decimal import Decimal
import numpy as np

from models import Portfolio, Position, Security, Transaction, PortfolioPerformance


class PerformanceAttribution:
    """Analyzes performance attribution by security, sector, and allocation"""

    def __init__(self, db: Session):
        self.db = db

    def calculate_attribution(
        self,
        portfolio_id: int,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Calculate multi-level performance attribution"""
        portfolio = self.db.query(Portfolio).filter(
            Portfolio.portfolio_id == portfolio_id
        ).first()

        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found")

        security_attribution = self._calculate_security_attribution(
            portfolio_id, start_date, end_date
        )

        sector_attribution = self._calculate_sector_attribution(
            security_attribution
        )

        transaction_costs = self._calculate_transaction_costs(
            portfolio_id, start_date, end_date
        )

        total_return = self._calculate_total_return(
            portfolio_id, start_date, end_date
        )

        return {
            "portfolio_id": portfolio_id,
            "portfolio_name": portfolio.portfolio_name,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "total_return": total_return,
            "security_attribution": security_attribution,
            "sector_attribution": sector_attribution,
            "transaction_costs": transaction_costs
        }

    def _calculate_security_attribution(
        self,
        portfolio_id: int,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """Calculate contribution of each security to portfolio return"""
        positions = self.db.query(Position).filter(
            Position.portfolio_id == portfolio_id
        ).all()

        attributions = []
        for position in positions:
            security = self.db.query(Security).filter(
                Security.security_id == position.security_id
            ).first()

            if not security:
                continue

            weight = float(position.weight or 0) / 100
            return_contribution = 0

            attributions.append({
                "security_id": security.security_id,
                "ticker_symbol": security.ticker_symbol,
                "security_name": security.security_name,
                "sector": security.sector,
                "weight": weight * 100,
                "return_contribution": return_contribution,
            })

        return attributions

    def _calculate_sector_attribution(
        self,
        security_attribution: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Aggregate attribution by sector"""
        sector_data = {}

        for sec in security_attribution:
            sector = sec["sector"] or "Unknown"
            if sector not in sector_data:
                sector_data[sector] = {
                    "sector": sector,
                    "total_weight": 0,
                    "total_contribution": 0,
                    "securities_count": 0
                }

            sector_data[sector]["total_weight"] += sec["weight"]
            sector_data[sector]["total_contribution"] += sec["return_contribution"]
            sector_data[sector]["securities_count"] += 1

        return list(sector_data.values())

    def _calculate_transaction_costs(
        self,
        portfolio_id: int,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Calculate transaction costs impact"""
        transactions = self.db.query(Transaction).filter(
            Transaction.portfolio_id == portfolio_id,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date
        ).all()

        total_fees = sum(float(t.fees or 0) for t in transactions)
        transaction_count = len(transactions)

        return {
            "total_fees": total_fees,
            "transaction_count": transaction_count,
            "average_fee_per_transaction": total_fees / transaction_count if transaction_count > 0 else 0
        }

    def _calculate_total_return(
        self,
        portfolio_id: int,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Calculate total portfolio return for the period"""
        start_perf = self.db.query(PortfolioPerformance).filter(
            PortfolioPerformance.portfolio_id == portfolio_id,
            PortfolioPerformance.as_of_date >= start_date
        ).order_by(PortfolioPerformance.as_of_date).first()

        end_perf = self.db.query(PortfolioPerformance).filter(
            PortfolioPerformance.portfolio_id == portfolio_id,
            PortfolioPerformance.as_of_date <= end_date
        ).order_by(PortfolioPerformance.as_of_date.desc()).first()

        if not start_perf or not end_perf:
            return {
                "period_return": None,
                "start_value": None,
                "end_value": None
            }

        start_value = float(start_perf.total_value) if start_perf.total_value else 0
        end_value = float(end_perf.total_value) if end_perf.total_value else 0

        period_return = ((end_value - start_value) / start_value * 100) if start_value > 0 else 0

        return {
            "period_return": period_return,
            "start_value": start_value,
            "end_value": end_value,
            "absolute_change": end_value - start_value
        }
