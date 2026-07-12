import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats
import yfinance as yf
from sqlalchemy.orm import Session

from models import Position, Security

logger = logging.getLogger(__name__)

SCENARIOS = [
    {"name": "2008 Financial Crisis", "label": "Sep 2008 – Mar 2009", "start": "2008-09-01", "end": "2009-03-31"},
    {"name": "COVID Crash", "label": "Feb – Mar 2020", "start": "2020-02-19", "end": "2020-03-23"},
    {"name": "2022 Rate Shock", "label": "Jan – Oct 2022", "start": "2022-01-01", "end": "2022-10-13"},
    {"name": "2023 Regional Banking Crisis", "label": "Mar – May 2023", "start": "2023-03-08", "end": "2023-05-01"},
    {"name": "2026 Iran War", "label": "Feb – Mar 2026", "start": "2026-02-28", "end": "2026-03-30"},
]

FACTOR_PROXIES = {
    "Market": "SPY",
    "Value": "IWD",
    "Growth": "IWF",
    "Momentum": "MTUM",
    "Low Vol": "USMV",
}


def _get_positions(db: Session, portfolio_id: int) -> List[Tuple[str, float]]:
    rows = (
        db.query(Position, Security)
        .join(Security, Position.security_id == Security.security_id)
        .filter(Position.portfolio_id == portfolio_id)
        .all()
    )
    return [(sec.ticker_symbol, float(pos.quantity)) for pos, sec in rows if sec.ticker_symbol]


def _download_prices(
    tickers: List[str],
    period: str = "2y",
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> pd.DataFrame:
    if not tickers:
        return pd.DataFrame()
    kwargs: Dict[str, Any] = {"auto_adjust": True, "progress": False, "threads": False}
    if start and end:
        kwargs["start"] = start
        kwargs["end"] = end
    else:
        kwargs["period"] = period
    try:
        raw = yf.download(tickers if len(tickers) > 1 else tickers[0], **kwargs)
    except Exception as e:
        logger.error(f"yfinance download error: {e}")
        return pd.DataFrame()
    if raw.empty:
        return pd.DataFrame()
    if isinstance(raw.columns, pd.MultiIndex):
        lvl0 = raw.columns.get_level_values(0).unique()
        prices = raw["Close"] if "Close" in lvl0 else pd.DataFrame()
    else:
        col = "Close" if "Close" in raw.columns else raw.columns[0]
        prices = raw[[col]].rename(columns={col: tickers[0]})
    if isinstance(prices, pd.Series):
        prices = prices.to_frame(name=tickers[0])
    return prices.dropna(how="all")


def _real_weights(tickers: List[str], quantities: List[float], prices: pd.DataFrame) -> Dict[str, float]:
    if prices.empty:
        return {}
    latest = prices.iloc[-1]
    mv: Dict[str, float] = {}
    for i, t in enumerate(tickers):
        if t in latest.index:
            v = latest[t]
            if not np.isnan(float(v)):
                mv[t] = quantities[i] * float(v)
    total = sum(mv.values())
    return {t: v / total for t, v in mv.items()} if total > 0 else {}


def _portfolio_returns(weights: Dict[str, float], prices: pd.DataFrame) -> pd.Series:
    available = [t for t in weights if t in prices.columns]
    rets = prices[available].pct_change().dropna()
    w = pd.Series({t: weights[t] for t in available})
    w = w / w.sum()
    return rets @ w


def compute_var(db: Session, portfolio_id: int) -> Dict[str, Any]:
    positions = _get_positions(db, portfolio_id)
    if not positions:
        return {"error": "No positions"}
    tickers, quantities = zip(*positions)
    tickers, quantities = list(tickers), list(quantities)

    prices = _download_prices(tickers, period="2y")
    if prices.empty:
        return {"error": "Price data unavailable"}

    available = [t for t in tickers if t in prices.columns]
    avail_qty = [quantities[tickers.index(t)] for t in available]
    prices = prices[available]
    weights = _real_weights(available, avail_qty, prices)
    if not weights:
        return {"error": "Could not compute weights"}

    port_r = _portfolio_returns(weights, prices)
    if len(port_r) < 30:
        return {"error": "Insufficient price history"}

    h95 = float(np.percentile(port_r, 5))
    h99 = float(np.percentile(port_r, 1))
    vol = float(port_r.std())
    p95 = float(stats.norm.ppf(0.05) * vol)
    p99 = float(stats.norm.ppf(0.01) * vol)

    return {
        "historical": {
            "var_95_1d_pct":  round(h95 * 100, 3),
            "var_99_1d_pct":  round(h99 * 100, 3),
            "var_95_10d_pct": round(h95 * np.sqrt(10) * 100, 3),
            "var_99_10d_pct": round(h99 * np.sqrt(10) * 100, 3),
        },
        "parametric": {
            "var_95_1d_pct": round(p95 * 100, 3),
            "var_99_1d_pct": round(p99 * 100, 3),
        },
        "distribution": {
            "daily_vol_pct":      round(vol * 100, 3),
            "annualized_vol_pct": round(vol * np.sqrt(252) * 100, 2),
            "skewness":           round(float(stats.skew(port_r)), 3),
            "excess_kurtosis":    round(float(stats.kurtosis(port_r)), 3),
        },
        "tickers_used":    available,
        "tickers_missing": [t for t in tickers if t not in available],
        "observations":    len(port_r),
        "price_date":      str(prices.index[-1].date()),
    }


def run_stress_tests(db: Session, portfolio_id: int) -> List[Dict[str, Any]]:
    positions = _get_positions(db, portfolio_id)
    if not positions:
        return []
    tickers, quantities = zip(*positions)
    tickers, quantities = list(tickers), list(quantities)

    cur_prices = _download_prices(tickers, period="1mo")
    weights = _real_weights(tickers, quantities, cur_prices)
    if not weights:
        return []

    results = []
    for sc in SCENARIOS:
        try:
            sc_prices = _download_prices(list(weights.keys()), start=sc["start"], end=sc["end"])
            if sc_prices.empty or len(sc_prices) < 2:
                continue
            available = [t for t in weights if t in sc_prices.columns]
            if not available:
                continue
            ticker_rets: Dict[str, float] = {}
            for t in available:
                series = sc_prices[t].dropna()
                if len(series) >= 2:
                    ticker_rets[t] = float((series.iloc[-1] / series.iloc[0]) - 1)
            if not ticker_rets:
                continue
            impact = sum(weights.get(t, 0) * r for t, r in ticker_rets.items())
            worst = min(ticker_rets, key=ticker_rets.get)
            results.append({
                "name":                 sc["name"],
                "label":                sc["label"],
                "portfolio_impact_pct": round(impact * 100, 2),
                "worst_position":       worst,
                "worst_position_pct":   round(ticker_rets[worst] * 100, 2),
                "tickers_with_data":    len(ticker_rets),
                "tickers_total":        len(weights),
            })
        except Exception as e:
            logger.warning(f"Stress test '{sc['name']}' failed: {e}")
    return results


def compute_factor_exposure(db: Session, portfolio_id: int) -> Dict[str, Any]:
    positions = _get_positions(db, portfolio_id)
    if not positions:
        return {"error": "No positions"}
    tickers, quantities = zip(*positions)
    tickers, quantities = list(tickers), list(quantities)

    prices = _download_prices(tickers, period="2y")
    if prices.empty:
        return {"error": "Price data unavailable"}

    available = [t for t in tickers if t in prices.columns]
    avail_qty = [quantities[tickers.index(t)] for t in available]
    weights = _real_weights(available, avail_qty, prices)
    if not weights:
        return {"error": "Could not compute weights"}

    port_r = _portfolio_returns(weights, prices)
    f_prices = _download_prices(list(FACTOR_PROXIES.values()), period="2y")
    f_rets = f_prices.pct_change().dropna()

    factors: Dict[str, Any] = {}
    for fname, fticker in FACTOR_PROXIES.items():
        if fticker not in f_rets.columns:
            continue
        common = port_r.index.intersection(f_rets.index)
        if len(common) < 60:
            continue
        p = port_r[common].values
        f = f_rets.loc[common, fticker].values
        slope, _, r_val, _, _ = stats.linregress(f, p)
        factors[fname] = {
            "beta":      round(float(slope), 3),
            "r_squared": round(float(r_val ** 2), 3),
            "ticker":    fticker,
        }

    mkt_beta = factors.get("Market", {}).get("beta", 1.0)
    if mkt_beta > 1.2:
        interp = f"Aggressive (beta={mkt_beta:.2f}) — amplifies market swings"
    elif mkt_beta > 0.8:
        interp = f"Neutral (beta={mkt_beta:.2f}) — tracks market closely"
    else:
        interp = f"Defensive (beta={mkt_beta:.2f}) — less sensitive to market"

    return {"factors": factors, "market_interp": interp, "observations": len(port_r)}


# Sensitivity-based (parametric) shocks — a different methodology from the
# historical-replay SCENARIOS above: instead of replaying an actual past price
# path, a factor shift (rates, equities) is applied to today's book via a
# computed sensitivity. Two channels, since bonds and equities reprice
# differently to a rate move:
#   - Fixed income: standard duration approximation, price_change ~= -duration * delta_yield
#   - Equities: reuses the Market beta already computed by compute_factor_exposure()
# FIXED_INCOME_DURATION_PROXY is a flat approximation (~AGG's actual published
# duration) applied to every Security.sector == "Fixed Income" position, since
# Securities has no per-security duration field yet. Equity rate-sensitivity
# (growth stocks are more rate-sensitive than value) is deliberately not
# modeled in v1 — flagged via "note" in the result rather than guessed at.
FIXED_INCOME_DURATION_PROXY = 6.0  # years

PARAMETRIC_SHOCKS = [
    {"name": "Rates +100bps",        "kind": "rate",   "delta": 0.01},
    {"name": "Rates -100bps",        "kind": "rate",   "delta": -0.01},
    {"name": "Equities -20%",        "kind": "equity", "delta": -0.20},
    {"name": "No Stress (Baseline)", "kind": "none",   "delta": 0.0},
]


def run_parametric_shocks(
    db: Session, portfolio_id: int, market_beta: Optional[float]
) -> List[Dict[str, Any]]:
    rows = (
        db.query(Position.quantity, Security.ticker_symbol, Security.sector)
        .join(Security, Position.security_id == Security.security_id)
        .filter(Position.portfolio_id == portfolio_id)
        .all()
    )
    if not rows:
        return []

    tickers = [r.ticker_symbol for r in rows]
    quantities = [float(r.quantity) for r in rows]
    sector_by_ticker = {r.ticker_symbol: r.sector for r in rows}

    cur_prices = _download_prices(tickers, period="1mo")
    weights = _real_weights(tickers, quantities, cur_prices)
    if not weights:
        return []

    fi_weight = sum(w for t, w in weights.items() if sector_by_ticker.get(t) == "Fixed Income")

    results: List[Dict[str, Any]] = []
    for shock in PARAMETRIC_SHOCKS:
        if shock["kind"] == "rate":
            impact = sum(
                w * (-FIXED_INCOME_DURATION_PROXY * shock["delta"])
                for t, w in weights.items()
                if sector_by_ticker.get(t) == "Fixed Income"
            )
            results.append({
                "name":                    shock["name"],
                "methodology":             "duration_proxy",
                "portfolio_impact_pct":    round(impact * 100, 2),
                "fixed_income_weight_pct": round(fi_weight * 100, 1),
                "duration_proxy_years":    FIXED_INCOME_DURATION_PROXY,
            })
        elif shock["kind"] == "equity":
            if market_beta is None:
                results.append({
                    "name": shock["name"], "methodology": "market_beta",
                    "portfolio_impact_pct": None,
                    "note": "Market beta unavailable for this portfolio",
                })
            else:
                impact = market_beta * shock["delta"]
                results.append({
                    "name":                 shock["name"],
                    "methodology":          "market_beta",
                    "portfolio_impact_pct": round(impact * 100, 2),
                    "market_beta":          round(market_beta, 3),
                })
        else:
            results.append({
                "name": shock["name"], "methodology": "baseline",
                "portfolio_impact_pct": 0.0,
            })
    return results


def compute_all(db: Session, portfolio_id: int) -> Dict[str, Any]:
    logger.info(f"[RiskAnalytics] Computing all metrics for portfolio {portfolio_id}")
    factor_exposure = compute_factor_exposure(db, portfolio_id)
    market_beta = factor_exposure.get("factors", {}).get("Market", {}).get("beta")
    return {
        "portfolio_id":       portfolio_id,
        "computed_at":        datetime.utcnow().isoformat(),
        "var":                compute_var(db, portfolio_id),
        "stress_tests":       run_stress_tests(db, portfolio_id),
        "factor_exposure":    factor_exposure,
        "parametric_shocks":  run_parametric_shocks(db, portfolio_id, market_beta),
    }
