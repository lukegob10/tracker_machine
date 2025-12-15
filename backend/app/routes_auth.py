from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from .auth import (
    clear_auth_cookies,
    create_token,
    decode_token,
    hash_password,
    set_auth_cookies,
    verify_password,
)
from .deps import get_db, require_user
from .models import User
from .schemas import UserCreate, UserLogin, UserRead

router = APIRouter()

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def _get_user_by_email(session: Session, email: str) -> Optional[User]:
    return session.query(User).filter(User.email == email.lower()).first()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, response: Response, session: Session = Depends(get_db)):
    existing = _get_user_by_email(session, str(payload.email))
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = User(
        email=str(payload.email).lower(),
        display_name=payload.display_name,
        password_hash=hash_password(payload.password),
        role="user",
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    access_token = create_token(user.user_id, user.role, "access")
    refresh_token = create_token(user.user_id, user.role, "refresh")
    set_auth_cookies(response, access_token, refresh_token)
    return user


@router.post("/login", response_model=UserRead)
def login(payload: UserLogin, response: Response, session: Session = Depends(get_db)):
    user = _get_user_by_email(session, str(payload.email))
    now = datetime.now(timezone.utc)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

    if user.locked_until and user.locked_until > now:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Account locked. Try again later.")

    if not verify_password(payload.password, user.password_hash):
        user.failed_attempts += 1
        if user.failed_attempts >= MAX_FAILED_ATTEMPTS:
            user.locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
        session.add(user)
        session.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    user.failed_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    session.add(user)
    session.commit()
    session.refresh(user)

    access_token = create_token(user.user_id, user.role, "access")
    refresh_token = create_token(user.user_id, user.role, "refresh")
    set_auth_cookies(response, access_token, refresh_token)
    return user


@router.post("/refresh", response_model=UserRead)
def refresh(request: Request, response: Response, session: Session = Depends(get_db)):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_token(token, expected_type="refresh")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = session.query(User).filter(User.user_id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or missing")
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Account locked")

    access_token = create_token(user.user_id, user.role, "access")
    refresh_token = create_token(user.user_id, user.role, "refresh")
    set_auth_cookies(response, access_token, refresh_token)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    clear_auth_cookies(response)
    return None


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(require_user)):
    return current_user
