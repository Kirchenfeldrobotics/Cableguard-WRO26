"""Robot link token, operator passwords and the webapp's JWT access tokens."""

import base64
import hashlib
import hmac
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, WebSocket, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User

log = logging.getLogger(__name__)

ROBOT_TOKEN = os.environ["CABLEGUARD_ROBOT_TOKEN"]

JWT_SECRET = settings.JWT_SECRET or secrets.token_urlsafe(48)
if not settings.JWT_SECRET:
    log.warning("JWT_SECRET is not set, using a random one: every restart signs the operator out")

# OWASP-recommended work factor for PBKDF2-HMAC-SHA256.
PBKDF2_ROUNDS = 600_000
_DUMMY_HASH_PASSWORD = secrets.token_urlsafe(16)


# passwords -------------------------------------------------------------------

def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def hash_password(password: str) -> str:
    """`pbkdf2_sha256$rounds$salt$hash`, with a fresh random salt every call."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${PBKDF2_ROUNDS}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, rounds, salt, digest = encoded.split("$")
        if scheme != "pbkdf2_sha256":
            return False
        computed = hashlib.pbkdf2_hmac("sha256", password.encode(), _unb64(salt), int(rounds))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(computed, _unb64(digest))


def dummy_verify(password: str) -> None:
    """Spends the same time as a real check so a wrong username is not faster."""
    verify_password(password, hash_password(_DUMMY_HASH_PASSWORD))


def nfc_key_matches(key: str) -> bool:
    """Whether `key` is the NFC_LOGIN_KEY from the robot's tag. Always False while it is unset."""
    expected = settings.NFC_LOGIN_KEY
    return bool(expected) and hmac.compare_digest(key.encode(), expected.encode())


# access tokens ---------------------------------------------------------------

def create_access_token(user: User) -> tuple[str, int]:
    """Returns the signed token and how many seconds it stays valid."""
    expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    now = datetime.now(timezone.utc)
    claims = {
        "sub": user.id,
        "username": user.username,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    return jwt.encode(claims, JWT_SECRET, algorithm=settings.JWT_ALGORITHM), expires_in


def decode_token(token: str) -> dict | None:
    """Claims of a valid, unexpired token, or None."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


# request guards --------------------------------------------------------------

_bearer = HTTPBearer(auto_error=False)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED, detail, headers={"WWW-Authenticate": "Bearer"}
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Guards every REST route that serves inspection data."""
    if credentials is None:
        raise _unauthorized("not authenticated")

    claims = decode_token(credentials.credentials)
    if claims is None:
        raise _unauthorized("invalid or expired token")

    user = db.get(User, claims.get("sub", ""))
    if user is None:
        raise _unauthorized("account no longer exists")
    return user


# websocket guards ------------------------------------------------------------

async def authenticate_robot(sock: WebSocket) -> bool:
    header = sock.headers.get("authorization", "")
    token  = header.removeprefix("Bearer ").strip()
    if not hmac.compare_digest(token, ROBOT_TOKEN):
        await sock.close(code=status.WS_1008_POLICY_VIOLATION)
        return False
    return True


async def authenticate_ui(sock: WebSocket) -> bool:
    """Browsers cannot set headers on a WebSocket, so the webapp sends the
    access token as `?token=` (see webapp/lib/config.ts)."""
    token = sock.query_params.get("token", "")
    if not token:
        token = sock.headers.get("authorization", "").removeprefix("Bearer ").strip()

    if decode_token(token) is None:
        await sock.close(code=status.WS_1008_POLICY_VIOLATION)
        return False
    return True
