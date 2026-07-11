"""
Auth + multi-tenant portfolio access — Task 6.4
================================================
JWT stored in httpOnly cookies (not localStorage — safer against XSS, per plan.md).
`get_current_user` is the FastAPI dependency every authenticated route uses.
`require_portfolio_access` is the ONE dependency that replaces the repeated
"query portfolio, 404 if missing" pattern across routers — it also enforces
ownership (manager_id match, or admin bypass).

`check_portfolio_access` is the non-HTTP twin of that, for callers that can't
raise an HTTPException — the AI chat tool dispatcher and the MCP server, where
the LLM/caller picks portfolio_id directly rather than it coming from a URL path.
"""
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models import User, Portfolio


# ── Password hashing ───────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


# ── JWT ─────────────────────────────────────────────────────────────────────────

def _create_token(user: User, expires_delta: timedelta, token_type: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.user_id),
        "role": user.role,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user: User) -> str:
    return _create_token(user, timedelta(minutes=settings.JWT_ACCESS_TOKEN_MINUTES), "access")


def create_refresh_token(user: User) -> str:
    return _create_token(user, timedelta(days=settings.JWT_REFRESH_TOKEN_DAYS), "refresh")


def create_mcp_token(user: User, days: int = 365) -> str:
    """Long-lived token for mcp_server.py — one per manager, pasted into that
    manager's own claude_desktop_config.json env block. Distinct token 'type'
    from access/refresh so it can never be swapped in for a browser cookie."""
    return _create_token(user, timedelta(days=days), "mcp")


def decode_token(token: str, expected_type: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    if payload.get("type") != expected_type:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    return payload


def get_user_from_access_token(db: Session, token: Optional[str]) -> Optional[User]:
    """Non-raising token→User lookup, shared by get_current_user (HTTP, raises on
    failure) and the WebSocket handshake (routers/ws.py — no HTTP status codes to
    raise, just accept or reject the socket)."""
    if not token:
        return None
    try:
        payload = decode_token(token, "access")
    except HTTPException:
        return None
    return db.query(User).filter(User.user_id == int(payload["sub"])).first()


# ── FastAPI dependencies ────────────────────────────────────────────────────────

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_token(token, "access")
    user = db.query(User).filter(User.user_id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_portfolio_access(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Portfolio:
    """Drop-in replacement for the `db.query(Portfolio).filter(...).first(); if not: 404`
    pattern duplicated across routers — now also enforces ownership."""
    portfolio = db.query(Portfolio).filter(Portfolio.portfolio_id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if current_user.role != "admin" and portfolio.manager_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized for this portfolio")
    return portfolio


def check_portfolio_access(db: Session, user: User, portfolio_id: int) -> Optional[Portfolio]:
    """Non-HTTP twin of require_portfolio_access, for the AI chat tool dispatcher and
    MCP server — callers that can't raise an HTTPException mid-conversation/mid-tool-call.
    Returns None (not authorized or not found) instead of raising."""
    portfolio = db.query(Portfolio).filter(Portfolio.portfolio_id == portfolio_id).first()
    if not portfolio:
        return None
    if user.role != "admin" and portfolio.manager_id != user.user_id:
        return None
    return portfolio


def scope_portfolio_query(query, current_user: User):
    """Applied to list endpoints (GET /api/portfolios, GET /api/alerts with no
    portfolio_id) — narrows to the manager's own portfolios, no-op for admin."""
    if current_user.role == "admin":
        return query
    return query.filter(Portfolio.manager_id == current_user.user_id)
