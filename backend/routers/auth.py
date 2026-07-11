from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import User
from config import settings
from auth import (
    verify_password, create_access_token, create_refresh_token,
    decode_token, get_current_user,
)

router = APIRouter()

ACCESS_COOKIE_MAX_AGE = 60 * 60          # 1 hour, matches JWT_ACCESS_TOKEN_MINUTES
REFRESH_COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 days, matches JWT_REFRESH_TOKEN_DAYS


class LoginRequest(BaseModel):
    email: str
    password: str


def _set_auth_cookies(response: Response, user: User) -> None:
    response.set_cookie(
        "access_token", create_access_token(user),
        max_age=ACCESS_COOKIE_MAX_AGE, httponly=True, secure=settings.COOKIE_SECURE, samesite="lax",
    )
    response.set_cookie(
        "refresh_token", create_refresh_token(user),
        max_age=REFRESH_COOKIE_MAX_AGE, httponly=True, secure=settings.COOKIE_SECURE, samesite="lax",
        path="/auth/refresh",
    )


def _user_dict(user: User) -> dict:
    return {
        "user_id": user.user_id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
    }


@router.post("/login")
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    _set_auth_cookies(response, user)
    return _user_dict(user)


@router.post("/refresh")
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token")
    payload = decode_token(token, "refresh")
    user = db.query(User).filter(User.user_id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    _set_auth_cookies(response, user)
    return _user_dict(user)


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token", path="/auth/refresh")
    return {"status": "ok"}


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return _user_dict(current_user)
