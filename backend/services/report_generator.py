"""
Portfolio Report Generator — Task 5.4
======================================
Packages data that already exists elsewhere (PortfolioAnalyzer, the stored
Risk_Metrics row, recent Alerts, a short AI commentary paragraph) into a
downloadable PDF. No new analysis — this is presentation, not computation.

White-background, orange-accent layout (not a literal dark-terminal replica)
since this is meant to be printed/shared externally, matching how a real
research report looks rather than the app's own dark UI.
"""
import io
import json
from datetime import datetime
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
)
from sqlalchemy.orm import Session

from models import Portfolio, Position, Security, Alert, RiskMetric
from services.portfolio_analyzer import PortfolioAnalyzer
from services.ai_portfolio_explainer import AIPortfolioExplainer

ORANGE = colors.HexColor("#F5821F")
DARK   = colors.HexColor("#1A1A1A")
GRAY   = colors.HexColor("#666666")
LIGHT  = colors.HexColor("#F5F5F5")


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("ReportTitle", parent=ss["Title"], textColor=DARK, fontSize=20, spaceAfter=2))
    ss.add(ParagraphStyle("ReportSubtitle", parent=ss["Normal"], textColor=GRAY, fontSize=10, spaceAfter=16))
    ss.add(ParagraphStyle("SectionHeader", parent=ss["Heading2"], textColor=colors.white,
                           backColor=ORANGE, fontSize=11, spaceBefore=14, spaceAfter=8,
                           leftIndent=6, borderPadding=(4, 4, 4, 4)))
    ss.add(ParagraphStyle("Body", parent=ss["Normal"], fontSize=9.5, leading=14, textColor=DARK))
    ss.add(ParagraphStyle("Footnote", parent=ss["Normal"], fontSize=7.5, textColor=GRAY))
    return ss


def _table(data, col_widths=None, header=True):
    t = Table(data, colWidths=col_widths)
    style = [
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [colors.white, LIGHT]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    t.setStyle(TableStyle(style))
    return t


def generate_portfolio_pdf(db: Session, portfolio_id: int) -> bytes:
    portfolio = db.query(Portfolio).filter(Portfolio.portfolio_id == portfolio_id).first()
    if not portfolio:
        raise ValueError(f"Portfolio {portfolio_id} not found")

    ss = _styles()
    data = PortfolioAnalyzer(db).analyze_portfolio_state(portfolio_id)
    perf = data.get("performance_summary", {})
    risk = data.get("risk_metrics", {})

    try:
        commentary = AIPortfolioExplainer(db).quick_summary(portfolio_id)
    except Exception:
        commentary = "AI commentary unavailable for this report (RAG/LLM service not reachable)."

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        topMargin=0.6 * inch, bottomMargin=0.6 * inch,
        leftMargin=0.6 * inch, rightMargin=0.6 * inch,
    )
    story = []

    # ── Header ──────────────────────────────────────────────────────────────
    story.append(Paragraph(portfolio.portfolio_name.upper(), ss["ReportTitle"]))
    story.append(Paragraph(
        f"Portfolio Risk Report &nbsp;|&nbsp; Strategy: {portfolio.strategy_type or 'N/A'} "
        f"&nbsp;|&nbsp; Currency: {portfolio.currency or 'USD'} "
        f"&nbsp;|&nbsp; Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        ss["ReportSubtitle"],
    ))

    # ── Overview ────────────────────────────────────────────────────────────
    story.append(Paragraph("OVERVIEW", ss["SectionHeader"]))
    overview_rows = [
        ["Total Value", f"${data.get('total_value', 0):,.0f}"],
        ["Cash Balance", f"${data.get('cash_balance', 0):,.0f}"],
        ["Positions", str(data.get("positions_count", 0))],
        ["YTD Return", f"{perf.get('ytd_return', 0) or 0:.2%}" if perf.get("ytd_return") is not None else "N/A"],
        ["Sharpe Ratio", f"{risk.get('sharpe_ratio'):.2f}" if risk.get("sharpe_ratio") is not None else "N/A"],
        ["Volatility", f"{risk.get('volatility'):.2%}" if risk.get("volatility") is not None else "N/A"],
    ]
    story.append(_table(overview_rows, col_widths=[2 * inch, 2 * inch], header=False))
    story.append(Spacer(1, 10))

    # ── AI Commentary ───────────────────────────────────────────────────────
    story.append(Paragraph("AI COMMENTARY", ss["SectionHeader"]))
    story.append(Paragraph(commentary.replace("\n", "<br/>"), ss["Body"]))
    story.append(Spacer(1, 6))

    # ── Sector Allocation ───────────────────────────────────────────────────
    sectors = data.get("sector_allocation", {})
    if sectors:
        story.append(Paragraph("SECTOR ALLOCATION", ss["SectionHeader"]))
        rows = [["Sector", "Weight"]] + [
            [s, f"{w:.1%}"] for s, w in sorted(sectors.items(), key=lambda x: -x[1])
        ]
        story.append(_table(rows, col_widths=[3 * inch, 1.5 * inch]))
        story.append(Spacer(1, 6))

    # ── Risk Analytics (from the latest stored Risk_Metrics row) ──────────
    risk_row = (
        db.query(RiskMetric)
        .filter(RiskMetric.portfolio_id == portfolio_id)
        .order_by(RiskMetric.computed_at.desc())
        .first()
    )
    if risk_row:
        story.append(Paragraph("RISK ANALYTICS", ss["SectionHeader"]))
        story.append(Paragraph(
            f"<i>Computed {risk_row.computed_at.strftime('%Y-%m-%d %H:%M UTC')} · "
            f"Price date {risk_row.price_date}</i>", ss["Footnote"],
        ))
        story.append(Spacer(1, 4))

        var_data = json.loads(risk_row.var_data or "{}").get("historical", {})
        if var_data:
            var_rows = [
                ["Metric", "1-Day", "10-Day"],
                ["95% VaR", f"{var_data.get('var_95_1d_pct', 0):.2f}%", f"{var_data.get('var_95_10d_pct', 0):.2f}%"],
                ["99% VaR", f"{var_data.get('var_99_1d_pct', 0):.2f}%", f"{var_data.get('var_99_10d_pct', 0):.2f}%"],
            ]
            story.append(_table(var_rows, col_widths=[2 * inch, 1.5 * inch, 1.5 * inch]))
            story.append(Spacer(1, 8))

        stress = json.loads(risk_row.stress_data or "[]")
        if stress:
            stress_rows = [["Scenario", "Portfolio Impact", "Worst Position"]] + [
                [s.get("label", s.get("name", "")), f"{s.get('portfolio_impact_pct', 0):.1f}%", s.get("worst_position", "N/A")]
                for s in stress
            ]
            story.append(_table(stress_rows, col_widths=[2.5 * inch, 1.5 * inch, 1.5 * inch]))
            story.append(Spacer(1, 8))

        factors = json.loads(risk_row.factor_data or "{}").get("factors", {})
        if factors:
            factor_rows = [["Factor", "Beta", "R²"]] + [
                [name, f"{f.get('beta', 0):.2f}", f"{f.get('r_squared', 0):.1%}"]
                for name, f in factors.items()
            ]
            story.append(_table(factor_rows, col_widths=[2 * inch, 1.5 * inch, 1.5 * inch]))
    else:
        story.append(Paragraph("RISK ANALYTICS", ss["SectionHeader"]))
        story.append(Paragraph("Not yet computed for this portfolio.", ss["Body"]))

    story.append(Spacer(1, 10))

    # ── Top Positions ───────────────────────────────────────────────────────
    story.append(Paragraph("TOP POSITIONS", ss["SectionHeader"]))
    positions = (
        db.query(Position, Security)
        .join(Security, Position.security_id == Security.security_id)
        .filter(Position.portfolio_id == portfolio_id)
        .order_by(Position.weight.desc())
        .limit(15)
        .all()
    )
    if positions:
        pos_rows = [["Ticker", "Sector", "Weight", "Market Value", "Type"]] + [
            [
                sec.ticker_symbol, sec.sector or "N/A", f"{float(pos.weight or 0):.1%}",
                f"${float(pos.market_value or 0):,.0f}", pos.position_type or "long",
            ]
            for pos, sec in positions
        ]
        story.append(_table(pos_rows, col_widths=[0.9 * inch, 1.6 * inch, 0.9 * inch, 1.6 * inch, 0.9 * inch]))
    story.append(Spacer(1, 10))

    # ── Recent Alerts ────────────────────────────────────────────────────────
    alerts = (
        db.query(Alert)
        .filter(Alert.portfolio_id == portfolio_id)
        .order_by(Alert.triggered_at.desc())
        .limit(8)
        .all()
    )
    story.append(Paragraph("RECENT ALERTS", ss["SectionHeader"]))
    if alerts:
        alert_rows = [["Severity", "Title", "Date"]] + [
            [a.severity.upper(), a.title[:70], a.triggered_at.strftime("%Y-%m-%d")]
            for a in alerts
        ]
        story.append(_table(alert_rows, col_widths=[0.9 * inch, 3.8 * inch, 1.2 * inch]))
    else:
        story.append(Paragraph("No alerts on record for this portfolio.", ss["Body"]))

    story.append(Spacer(1, 16))
    story.append(Paragraph(
        "FinSight AI — synthetic demo data for portfolio intelligence platform evaluation. "
        "Not investment advice.", ss["Footnote"],
    ))

    doc.build(story)
    return buf.getvalue()
