import json
import logging
from datetime import datetime, date
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session
from models import Alert, RiskMetric, Portfolio, Position, Security, MarketEvent
from services.portfolio_analyzer import PortfolioAnalyzer
from services.llm_service import LLMService, PromptLibrary
from rag.query_engine import MarketRAGEngine

logger = logging.getLogger(__name__)

# ── Thresholds ────────────────────────────────────────────────────────────────
VAR_95_WARNING  = 2.0   # % — 1-day VaR 95 exceeds this → warning
VAR_99_CRITICAL = 3.5   # % — 1-day VaR 99 exceeds this → critical
STRESS_WARNING  = -25.0 # % — any stress scenario worse than this → warning
STRESS_CRITICAL = -40.0 # % — any stress scenario worse than this → critical
BETA_WARNING    = 1.5   # market beta above this → warning

# Event exposure is a weight FRACTION (0-1), not a percentage — Positions.weight
# is stored as decimal(5,4), e.g. 0.25 = 25%. See database_migration.md gotchas.
EVENT_EXPOSURE_WARNING  = 0.15  # 15% combined sector+region exposure → warning
EVENT_EXPOSURE_CRITICAL = 0.30  # 30% combined sector+region exposure → critical


def _already_alerted_today(db: Session, portfolio_id: int, title: str) -> bool:
    today = date.today()
    return db.query(Alert).filter(
        Alert.portfolio_id == portfolio_id,
        Alert.title == title,
        Alert.triggered_at >= datetime(today.year, today.month, today.day),
    ).first() is not None


def _already_alerted_ever(db: Session, portfolio_id: int, title: str) -> bool:
    """Market events are static/historical, not a live feed — dedupe once per
    event per portfolio (not per-day like threshold alerts), or every risk_job
    run would re-raise the same event alert forever."""
    return db.query(Alert).filter(
        Alert.portfolio_id == portfolio_id,
        Alert.title == title,
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


def _parse_tag_list(value) -> List[str]:
    """Market_Events.affected_sectors/affected_regions are stored as plain comma-separated
    strings (e.g. 'Financials,Real Estate,Utilities'), NOT JSON despite the column comment —
    confirmed against production data. event_analyzer.py's _parse_json_field() calls
    json.loads() on this and silently swallows the resulting JSONDecodeError, so it has
    always returned [] / zero exposure for every event. Not fixing that file here since it
    also feeds the /api/analysis/event-impact endpoint and ai_event_analyzer.py — flagging
    it separately rather than changing behavior other code paths depend on."""
    if not value:
        return []
    if isinstance(value, list):
        return value
    return [v.strip() for v in value.split(",") if v.strip()]


def generate_event_alerts(db: Session) -> List[Alert]:
    """Scan all Market_Events for portfolio exposure and raise alert_type='event' alerts.

    Deliberately does NOT reuse EventImpactAnalyzer — that class does a per-portfolio,
    per-position N+1 query (plus PositionChangeLog/PortfolioPerformance lookups it needs
    for its rich API response) which is fine for one on-demand event but far too slow
    scanning all events on every risk_job.py run (500+ queries per event; dropped the
    Azure SQL connection mid-scan during testing). This does the same sector/region
    exposure math with two bulk queries total, independent of event count."""
    alerts: List[Alert] = []
    events = db.query(MarketEvent).all()
    if not events:
        return alerts

    position_rows = (
        db.query(Position.portfolio_id, Position.weight, Security.sector, Security.industry,
                  Security.country, Security.ticker_symbol)
        .join(Security, Position.security_id == Security.security_id)
        .all()
    )
    positions_by_portfolio: Dict[int, List[Any]] = {}
    for row in position_rows:
        positions_by_portfolio.setdefault(row.portfolio_id, []).append(row)

    for event in events:
        sector_tags = set(_parse_tag_list(event.affected_sectors))
        region_tags = set(_parse_tag_list(event.affected_regions))
        if not sector_tags and not region_tags:
            continue

        # "All Sectors" / "Global" (or an unset tag list) means that dimension imposes no
        # constraint. Otherwise a security must match BOTH sector and region to count —
        # OR semantics would mean any "United States"-tagged event (12 of 15 events) matches
        # ~90% of every portfolio's weight regardless of sector, since 105/135 securities in
        # this dataset are US-domiciled. That made every event fire on every portfolio in
        # testing (720 alerts) — not a useful signal. AND semantics ("Financials, in the US")
        # is the standard sector x geography overlay and matches what "affected" should mean.
        all_sectors = (not sector_tags) or ("All Sectors" in sector_tags)
        all_regions = (not region_tags) or ("Global" in region_tags)

        def sector_hit(r):
            return all_sectors or r.sector in sector_tags or r.industry in sector_tags

        def region_hit(r):
            return all_regions or r.country in region_tags

        for portfolio_id, rows in positions_by_portfolio.items():
            exposure = sum(float(r.weight or 0) for r in rows if sector_hit(r) and region_hit(r))
            if exposure < EVENT_EXPOSURE_WARNING:
                continue

            if exposure >= EVENT_EXPOSURE_CRITICAL or (
                event.impact_level == "high" and exposure >= EVENT_EXPOSURE_WARNING
            ):
                severity = "critical"
            else:
                severity = "warning"

            title = f"Event Impact #{event.event_id}: {event.event_title[:80]}"
            if _already_alerted_ever(db, portfolio_id, title):
                continue

            tickers = [r.ticker_symbol for r in rows if sector_hit(r) and region_hit(r)]
            alerts.append(Alert(
                portfolio_id=portfolio_id,
                alert_type="event",
                severity=severity,
                title=title,
                message=(
                    f"'{event.event_title}' ({event.event_type}, {event.impact_level} impact) "
                    f"affects {exposure:.0%} of this portfolio via {len(tickers)} "
                    f"position(s): {', '.join(tickers[:5])}."
                ),
            ))

    return alerts


def run_event_alerts(db: Session) -> int:
    alerts = generate_event_alerts(db)
    for alert in alerts:
        db.add(alert)
    if alerts:
        db.commit()
    return len(alerts)


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


def _ai_alert_already_generated_today(db: Session, portfolio_id: int) -> bool:
    """One AI scan per portfolio per day, regardless of title — unlike threshold/event
    alerts, AI output text varies call to call, so title-based dedup wouldn't cap volume
    or cost. Checked BEFORE calling the LLM so a re-run today doesn't spend money twice."""
    today = date.today()
    return db.query(Alert).filter(
        Alert.portfolio_id == portfolio_id,
        Alert.alert_type == "ai",
        Alert.triggered_at >= datetime(today.year, today.month, today.day),
    ).first() is not None


def _format_rag_context(results: list) -> str:
    if not results:
        return "No relevant market context retrieved."
    lines = []
    for i, r in enumerate(results[:6], 1):
        meta = r.get("metadata", {})
        date_str = meta.get("date", meta.get("published_at", meta.get("period", "N/A")))
        ticker = meta.get("ticker", "")
        label = f"[{ticker}] " if ticker else ""
        lines.append(f"[{i}] {r['collection']} ({date_str}): {label}{r['document'][:200]}")
    return "\n".join(lines)


def generate_ai_alert_for_portfolio(
    db: Session, portfolio_id: int, portfolio_name: str,
    llm: Optional[LLMService] = None, commit: bool = True,
) -> Optional[Alert]:
    """GPT-4o-mini reviews one portfolio's top holdings + recent market context and
    decides whether there's something concrete worth flagging today. Returns None
    (no DB write, no LLM call) if already scanned today or there's nothing to analyze."""
    if _ai_alert_already_generated_today(db, portfolio_id):
        return None

    top_rows = (
        db.query(Position.weight, Security.ticker_symbol, Security.sector)
        .join(Security, Position.security_id == Security.security_id)
        .filter(Position.portfolio_id == portfolio_id)
        .order_by(Position.weight.desc())
        .limit(5)
        .all()
    )
    if not top_rows:
        return None
    top_positions = [
        {"ticker": r.ticker_symbol, "weight": float(r.weight or 0), "sector": r.sector}
        for r in top_rows
    ]

    portfolio_data = PortfolioAnalyzer(db).analyze_portfolio_state(portfolio_id)

    rag_query = " ".join(p["ticker"] for p in top_positions[:3]) + " risk news outlook volatility"
    try:
        rag_results = MarketRAGEngine().retrieve_context(rag_query, n_results=6)
    except Exception:
        logger.warning(f"[AlertEngine] RAG unavailable for AI alert scan, portfolio {portfolio_id}")
        rag_results = []
    rag_context = _format_rag_context(rag_results)

    prompt = PromptLibrary.ai_alert_scan(portfolio_data, top_positions, rag_context)
    llm = llm or LLMService()
    try:
        raw = llm.generate(prompt, task_type="ai_alert", max_tokens=350, json_mode=True)
        parsed = json.loads(raw)
    except Exception:
        logger.exception(f"[AlertEngine] AI alert scan failed for portfolio {portfolio_id}")
        return None

    if not parsed.get("alert_worthy"):
        return None

    severity = parsed.get("severity")
    if severity not in ("critical", "warning", "info"):
        severity = "info"
    title = str(parsed.get("title", "")).strip()[:255]
    message = str(parsed.get("message", "")).strip()
    if not title or not message:
        return None

    alert = Alert(
        portfolio_id=portfolio_id,
        alert_type="ai",
        severity=severity,
        title=title,
        message=message,
    )
    db.add(alert)
    if commit:
        db.commit()
    return alert


def run_ai_alerts(db: Session, portfolios: List[tuple], llm: Optional[LLMService] = None) -> Dict[str, Any]:
    llm = llm or LLMService()
    count = 0
    for pid, pname in portfolios:
        try:
            if generate_ai_alert_for_portfolio(db, pid, pname, llm=llm):
                count += 1
        except Exception as e:
            logger.error(f"[AlertEngine] AI alert scan failed for portfolio {pid}: {e}")
    return {"count": count, "usage": llm.get_usage_stats()}
