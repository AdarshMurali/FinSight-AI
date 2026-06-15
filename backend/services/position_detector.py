from sqlalchemy.orm import Session
from typing import Dict, Any, List
from datetime import date, datetime
from decimal import Decimal

from models import Position, PositionChangeLog, Security, Portfolio


class PositionChangeDetector:
    """Detects and analyzes significant position changes"""

    def __init__(self, db: Session):
        self.db = db

    def detect_significant_changes(
        self,
        portfolio_id: int,
        start_date: date,
        end_date: date,
        threshold_percent: float = 5.0
    ) -> Dict[str, Any]:
        """Detect significant position weight changes over a period"""
        portfolio = self.db.query(Portfolio).filter(
            Portfolio.portfolio_id == portfolio_id
        ).first()

        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found")

        change_logs = self.db.query(PositionChangeLog).filter(
            PositionChangeLog.portfolio_id == portfolio_id,
            PositionChangeLog.change_date >= start_date,
            PositionChangeLog.change_date <= end_date
        ).order_by(PositionChangeLog.change_date).all()

        significant_changes = []
        for log in change_logs:
            old_weight = float(log.old_weight or 0)
            new_weight = float(log.new_weight or 0)
            weight_change = abs(new_weight - old_weight)

            if weight_change >= threshold_percent:
                security = self.db.query(Security).filter(
                    Security.security_id == log.security_id
                ).first()

                significant_changes.append({
                    "log_id": log.log_id,
                    "change_date": log.change_date.isoformat(),
                    "security_id": log.security_id,
                    "ticker_symbol": security.ticker_symbol if security else None,
                    "security_name": security.security_name if security else None,
                    "sector": security.sector if security else None,
                    "change_type": log.change_type,
                    "old_weight": old_weight,
                    "new_weight": new_weight,
                    "weight_change": new_weight - old_weight,
                    "weight_change_abs": weight_change,
                    "reason": log.reason,
                    "related_event_id": log.related_event_id
                })

        rebalancing_events = self._identify_rebalancing_events(change_logs)
        entry_exit_positions = self._identify_entry_exit(change_logs)
        change_patterns = self._analyze_change_patterns(significant_changes)

        return {
            "portfolio_id": portfolio_id,
            "portfolio_name": portfolio.portfolio_name,
            "analysis_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "threshold_percent": threshold_percent,
            "significant_changes_count": len(significant_changes),
            "significant_changes": significant_changes,
            "rebalancing_events": rebalancing_events,
            "entry_exit_positions": entry_exit_positions,
            "change_patterns": change_patterns
        }

    def _identify_rebalancing_events(self, change_logs: List) -> List[Dict[str, Any]]:
        """Identify days with multiple position changes (rebalancing)"""
        changes_by_date = {}
        for log in change_logs:
            date_key = log.change_date.date().isoformat()
            if date_key not in changes_by_date:
                changes_by_date[date_key] = []
            changes_by_date[date_key].append(log)

        rebalancing_events = []
        for date_key, logs in changes_by_date.items():
            if len(logs) >= 3:
                rebalancing_events.append({
                    "date": date_key,
                    "changes_count": len(logs),
                    "change_types": list(set(log.change_type for log in logs if log.change_type))
                })

        return rebalancing_events

    def _identify_entry_exit(self, change_logs: List) -> Dict[str, Any]:
        """Identify new positions and closed positions"""
        entries = []
        exits = []

        for log in change_logs:
            old_weight = float(log.old_weight or 0)
            new_weight = float(log.new_weight or 0)

            if old_weight == 0 and new_weight > 0:
                security = self.db.query(Security).filter(
                    Security.security_id == log.security_id
                ).first()
                entries.append({
                    "date": log.change_date.isoformat(),
                    "security_id": log.security_id,
                    "ticker_symbol": security.ticker_symbol if security else None,
                    "new_weight": new_weight
                })

            elif old_weight > 0 and new_weight == 0:
                security = self.db.query(Security).filter(
                    Security.security_id == log.security_id
                ).first()
                exits.append({
                    "date": log.change_date.isoformat(),
                    "security_id": log.security_id,
                    "ticker_symbol": security.ticker_symbol if security else None,
                    "old_weight": old_weight
                })

        return {
            "new_positions": entries,
            "closed_positions": exits,
            "new_positions_count": len(entries),
            "closed_positions_count": len(exits)
        }

    def _analyze_change_patterns(self, significant_changes: List[Dict]) -> Dict[str, Any]:
        """Analyze patterns in position changes"""
        if not significant_changes:
            return {
                "most_changed_sectors": [],
                "increase_vs_decrease": {"increases": 0, "decreases": 0}
            }

        sector_changes = {}
        increases = 0
        decreases = 0

        for change in significant_changes:
            sector = change.get("sector", "Unknown")
            weight_change = change["weight_change"]

            if sector not in sector_changes:
                sector_changes[sector] = {"total_change": 0, "count": 0}

            sector_changes[sector]["total_change"] += abs(weight_change)
            sector_changes[sector]["count"] += 1

            if weight_change > 0:
                increases += 1
            else:
                decreases += 1

        most_changed_sectors = sorted(
            [
                {"sector": k, "total_change": v["total_change"], "count": v["count"]}
                for k, v in sector_changes.items()
            ],
            key=lambda x: x["total_change"],
            reverse=True
        )

        return {
            "most_changed_sectors": most_changed_sectors[:5],
            "increase_vs_decrease": {
                "increases": increases,
                "decreases": decreases
            }
        }
