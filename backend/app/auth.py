import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import jwt
from fastapi import HTTPException, Response, status
from passlib.context import CryptContext

SECRET_KEY = os.getenv("JIRA_LITE_SECRET_KEY", "dev-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JIRA_LITE_ACCESS_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JIRA_LITE_REFRESH_DAYS", "7"))
SECURE_COOKIES = os.getenv("JIRA_LITE_SECURE_COOKIES", "false").lower() == "true"
COOKIE_SAMESITE = os.getenv("JIRA_LITE_COOKIE_SAMESITE", "lax").lower()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _expiry(delta: timedelta) -> datetime:
    return datetime.now(timezone.utc) + delta


def create_token(user_id: str, role: str, token_type: str) -> str:
    expires = _expiry(
        timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES if token_type == "access" else REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60
        )
    )
    to_encode: Dict[str, Any] = {
        "sub": user_id,
        "role": role,
        "type": token_type,
        "exp": expires,
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str, expected_type: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if payload.get("type") != expected_type:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    return payload


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=SECURE_COOKIES,
        samesite=COOKIE_SAMESITE,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=SECURE_COOKIES,
        samesite=COOKIE_SAMESITE,
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
