from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import date, datetime, timedelta
import json

from models import (
    MarketEvent, Portfolio, Position, Security,
    PositionChangeLog, PortfolioPerformance
)


class EventImpactAnalyzer:
    """Analyzes the impact of market events on portfolios"""

    def __init__(self, db: Session):
        self.db = db

    def analyze_event_impact(
        self,
        event_id: int,
        portfolio_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """Analyze how a market event impacted portfolios"""
        event = self.db.query(MarketEvent).filter(
            MarketEvent.event_id == event_id
        ).first()

        if not event:
            raise ValueError(f"Market event {event_id} not found")

        if portfolio_ids:
            portfolios = self.db.query(Portfolio).filter(
                Portfolio.portfolio_id.in_(portfolio_ids)
            ).all()
        else:
            portfolios = self.db.query(Portfolio).all()

        affected_sectors = self._parse_json_field(event.affected_sectors)
        affected_regions = self._parse_json_field(event.affected_regions)

        portfolio_impacts = []
        for portfolio in portfolios:
            impact = self._calculate_portfolio_impact(
                portfolio, event, affected_sectors, affected_regions
            )
            if impact["exposure_score"] > 0:
                portfolio_impacts.append(impact)

        portfolio_impacts.sort(key=lambda x: x["exposure_score"], reverse=True)

        return {
            "event_id": event_id,
            "event_title": event.event_title,
            "event_date": event.event_date.isoformat(),
            "event_type": event.event_type,
            "impact_level": event.impact_level,
            "affected_sectors": affected_sectors,
            "affected_regions": affected_regions,
            "portfolios_analyzed": len(portfolios),
            "portfolios_affected": len(portfolio_impacts),
            "portfolio_impacts": portfolio_impacts
        }

    def _calculate_portfolio_impact(
        self,
        portfolio: Portfolio,
        event: MarketEvent,
        affected_sectors: List[str],
        affected_regions: List[str]
    ) -> Dict[str, Any]:
        """Calculate impact score for a specific portfolio"""
        positions = self.db.query(Position).filter(
            Position.portfolio_id == portfolio.portfolio_id
        ).all()

        sector_exposure = 0
        region_exposure = 0
        affected_positions = []

        for position in positions:
            security = self.db.query(Security).filter(
                Security.security_id == position.security_id
            ).first()

            if not security:
                continue

            position_weight = float(position.weight or 0)

            if security.sector in affected_sectors:
                sector_exposure += position_weight
                affected_positions.append({
                    "security_id": security.security_id,
                    "ticker_symbol": security.ticker_symbol,
                    "sector": security.sector,
                    "weight": position_weight,
                    "exposure_type": "sector"
                })

            if security.country in affected_regions:
                region_exposure += position_weight
                if not any(p["security_id"] == security.security_id for p in affected_positions):
                    affected_positions.append({
                        "security_id": security.security_id,
                        "ticker_symbol": security.ticker_symbol,
                        "country": security.country,
                        "weight": position_weight,
                        "exposure_type": "region"
                    })

        exposure_score = sector_exposure + region_exposure

        position_changes = self._get_related_position_changes(
            portfolio.portfolio_id, event.event_id
        )

        performance_impact = self._calculate_performance_impact(
            portfolio.portfolio_id, event.event_date
        )

        return {
            "portfolio_id": portfolio.portfolio_id,
            "portfolio_name": portfolio.portfolio_name,
            "exposure_score": exposure_score,
            "sector_exposure": sector_exposure,
            "region_exposure": region_exposure,
            "affected_positions_count": len(affected_positions),
            "affected_positions": affected_positions,
            "position_changes": position_changes,
            "performance_impact": performance_impact
        }

    def _get_related_position_changes(
        self,
        portfolio_id: int,
        event_id: int
    ) -> List[Dict[str, Any]]:
        """Get position changes related to this event"""
        changes = self.db.query(PositionChangeLog).filter(
            PositionChangeLog.portfolio_id == portfolio_id,
            PositionChangeLog.related_event_id == event_id
        ).all()

        result = []
        for change in changes:
            security = self.db.query(Security).filter(
                Security.security_id == change.security_id
            ).first()

            result.append({
                "security_id": change.security_id,
                "ticker_symbol": security.ticker_symbol if security else None,
                "change_date": change.change_date.isoformat(),
                "change_type": change.change_type,
                "weight_change": float(change.new_weight or 0) - float(change.old_weight or 0)
            })

        return result

    def _calculate_performance_impact(
        self,
        portfolio_id: int,
        event_date: datetime
    ) -> Dict[str, Any]:
        """Calculate performance around the event date"""
        event_day = event_date.date()
        before_date = event_day - timedelta(days=5)
        after_date = event_day + timedelta(days=5)

        before_perf = self.db.query(PortfolioPerformance).filter(
            PortfolioPerformance.portfolio_id == portfolio_id,
            PortfolioPerformance.as_of_date == before_date
        ).first()

        event_perf = self.db.query(PortfolioPerformance).filter(
            PortfolioPerformance.portfolio_id == portfolio_id,
            PortfolioPerformance.as_of_date == event_day
        ).first()

        after_perf = self.db.query(PortfolioPerformance).filter(
            PortfolioPerformance.portfolio_id == portfolio_id,
            PortfolioPerformance.as_of_date == after_date
        ).first()

        return {
            "before_event": float(before_perf.daily_return) if before_perf and before_perf.daily_return else None,
            "event_day": float(event_perf.daily_return) if event_perf and event_perf.daily_return else None,
            "after_event": float(after_perf.daily_return) if after_perf and after_perf.daily_return else None
        }

    def _parse_json_field(self, field_value: Optional[str]) -> List[str]:
        """Parse JSON array field from database"""
        if not field_value:
            return []

        try:
            if isinstance(field_value, str):
                return json.loads(field_value)
            return field_value
        except:
            return []
