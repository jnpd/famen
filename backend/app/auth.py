from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .models import User, UserSession

PASSWORD_ITERATIONS = 260_000
SESSION_DAYS = 7
security = HTTPBearer(auto_error=False)


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    if not salt:
        salt_bytes = secrets.token_bytes(16)
        salt = base64.urlsafe_b64encode(salt_bytes).decode("ascii")
    else:
        salt_bytes = base64.urlsafe_b64decode(salt.encode("ascii"))
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_bytes,
        PASSWORD_ITERATIONS,
    )
    return base64.urlsafe_b64encode(digest).decode("ascii"), salt


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    calculated, _ = hash_password(password, salt)
    return hmac.compare_digest(calculated, stored_hash)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(db: Session, user: User) -> tuple[str, UserSession]:
    raw_token = secrets.token_urlsafe(48)
    session = UserSession(
        user_id=user.id,
        token_hash=token_hash(raw_token),
        expires_at=datetime.now() + timedelta(days=SESSION_DAYS),
        last_seen_at=datetime.now(),
    )
    db.add(session)
    db.flush()
    return raw_token, session


def authenticate_token(db: Session, raw_token: str) -> User:
    hashed = token_hash(raw_token)
    session = db.scalar(select(UserSession).where(UserSession.token_hash == hashed))
    if not session:
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录")

    if session.expires_at <= datetime.now():
        db.delete(session)
        db.commit()
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")

    user = db.get(User, session.user_id)
    if not user or not user.enabled:
        raise HTTPException(status_code=403, detail="用户已停用")

    session.last_seen_at = datetime.now()
    db.commit()
    return user


def require_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="请先登录")
    return authenticate_token(db, credentials.credentials)


def current_token_hash(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> str:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="请先登录")
    return token_hash(credentials.credentials)
