import json
import logging
from datetime import datetime, date
from typing import List, Dict, Any

from sqlalchemy.orm import Session
from models import Alert, RiskMetric, Portfolio

logger = logging.getLogger(__name__)

# ── Thresholds ────────────────────────────────────────────────────────────────
VAR_95_WARNING  = 2.0   # % — 1-day VaR 95 exceeds this → warning
VAR_99_CRITICAL = 3.5   # % — 1-day VaR 99 exceeds this → critical
STRESS_WARNING  = -25.0 # % — any stress scenario worse than this → warning
STRESS_CRITICAL = -40.0 # % — any stress scenario worse than this → critical
BETA_WARNING    = 1.5   # market beta above this → warning


def _already_alerted_today(db: Session, portfolio_id: int, title: str) -> bool:
    today = date.today()
    return db.query(Alert).filter(
        Alert.portfolio_id == portfolio_id,
        Alert.title == title,
        Alert.triggered_at >= datetime(today.year, today.month, today.day),
    ).first() is not None


def generate_threshold_alerts(
    db: Session,
    portfolio_id: int,
    portfolio_name: str,
    var_data: Dict[str, Any],
    stress_tests: List[Dict[str, Any]],
    factor_data: Dict[str, Any],
) -> List[Alert]:
    alerts: List[Alert] = []

    # ── VaR alerts ───────────────────────────────────────────────────────────
    hist = var_data.get("historical", {})
    var_95 = hist.get("var_95_1d_pct")
    var_99 = hist.get("var_99_1d_pct")

    if var_99 is not None and abs(var_99) >= VAR_99_CRITICAL:
        title = f"Critical VaR: {portfolio_name}"
        if not _already_alerted_today(db, portfolio_id, title):
            alerts.append(Alert(
                portfolio_id=portfolio_id,
                alert_type="threshold",
                severity="critical",
                title=title,
                message=f"99% 1-day VaR is {abs(var_99):.2f}% — exceeds critical threshold of {VAR_99_CRITICAL}%.",
            ))
    elif var_95 is not None and abs(var_95) >= VAR_95_WARNING:
        title = f"Elevated VaR: {portfolio_name}"
        if not _already_alerted_today(db, portfolio_id, title):
            alerts.append(Alert(
                portfolio_id=portfolio_id,
                alert_type="threshold",
                severity="warning",
                title=title,
                message=f"95% 1-day VaR is {abs(var_95):.2f}% — exceeds warning threshold of {VAR_95_WARNING}%.",
            ))

    # ── Stress test alerts ───────────────────────────────────────────────────
    for test in stress_tests:
        impact = test.get("portfolio_impact_pct", 0)
        name   = test.get("name", "Unknown Scenario")
        if impact <= STRESS_CRITICAL:
            title = f"Severe Stress Exposure: {portfolio_name}"
            if not _already_alerted_today(db, portfolio_id, title):
                alerts.append(Alert(
                    portfolio_id=portfolio_id,
                    alert_type="threshold",
                    severity="critical",
                    title=title,
                    message=f"Stress test '{name}' shows {impact:.1f}% portfolio impact — exceeds critical threshold.",
                ))
            break
        elif impact <= STRESS_WARNING:
            title = f"Stress Test Warning: {portfolio_name}"
            if not _already_alerted_today(db, portfolio_id, title):
                alerts.append(Alert(
                    portfolio_id=portfolio_id,
                    alert_type="threshold",
                    severity="warning",
                    title=title,
                    message=f"Stress test '{name}' shows {impact:.1f}% portfolio impact — exceeds warning threshold.",
                ))
            break

    # ── Factor / beta alert ──────────────────────────────────────────────────
    factors = factor_data.get("factors", {})
    market_factor = factors.get("Market", {})
    beta = market_factor.get("beta")
    if beta is not None and abs(beta) >= BETA_WARNING:
        title = f"High Market Beta: {portfolio_name}"
        if not _already_alerted_today(db, portfolio_id, title):
            alerts.append(Alert(
                portfolio_id=portfolio_id,
                alert_type="threshold",
                severity="warning",
                title=title,
                message=f"Market beta is {beta:.2f} — portfolio is highly sensitive to broad market moves.",
            ))

    return alerts


def run_alerts_for_portfolio(db: Session, portfolio_id: int, portfolio_name: str) -> int:
    row = (
        db.query(RiskMetric)
        .filter(RiskMetric.portfolio_id == portfolio_id)
        .order_by(RiskMetric.computed_at.desc())
        .first()
    )
    if not row:
        return 0

    try:
        var_data     = json.loads(row.var_data    or "{}")
        stress_tests = json.loads(row.stress_data or "[]")
        factor_data  = json.loads(row.factor_data or "{}")
    except Exception:
        return 0

    alerts = generate_threshold_alerts(
        db, portfolio_id, portfolio_name, var_data, stress_tests, factor_data
    )
    for alert in alerts:
        db.add(alert)
    if alerts:
        db.commit()
    return len(alerts)
