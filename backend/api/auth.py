"""
auth.py — JWT Authentication Middleware
=========================================
PIN-based staff login → JWT token tied to shift duration.
Token expiry = min(shift end, max 12 hours).

Env vars:
  JWT_SECRET  — HMAC-SHA256 signing key (REQUIRED in production)
  JWT_ALGORITHM — default HS256
  JWT_DEFAULT_EXPIRY_HOURS — fallback expiry if no shift end (default 8)
"""

import os
import logging
from datetime import datetime, timezone, timedelta

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

logger = logging.getLogger("petpooja.auth")


def _env_int(name: str, default: int, *, min_value: int = 1, max_value: int | None = None) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except (TypeError, ValueError):
        logger.warning("Invalid %s=%r; using default %d", name, raw, default)
        return default
    if value < min_value:
        logger.warning("%s must be >= %d; using default %d", name, min_value, default)
        return default
    if max_value is not None and value > max_value:
        logger.warning("%s must be <= %d; using default %d", name, max_value, default)
        return default
    return value


_JWT_SECRET = os.getenv("JWT_SECRET", "")
_JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
_JWT_DEFAULT_EXPIRY_HOURS = _env_int("JWT_DEFAULT_EXPIRY_HOURS", 8, min_value=1, max_value=12)

# When True, all endpoints require a valid JWT.
# Set to False (or unset) during development to keep current open behavior.
AUTH_ENABLED = os.getenv("AUTH_ENABLED", "false").lower() in ("1", "true", "yes")

_bearer_scheme = HTTPBearer(auto_error=False)


def _check_secret():
    if not _JWT_SECRET:
        raise RuntimeError(
            "JWT_SECRET env var is not set. "
            "Set a strong random secret before enabling authentication."
        )


def create_token(staff_id: int, role: str, shift_end: datetime | None = None) -> str:
    """
    Issue a JWT for an authenticated staff member.

    Args:
        staff_id: staff.id from DB
        role: waiter | cashier | manager | chef
        shift_end: if known, token expires at shift end; otherwise default hours

    Returns:
        Signed JWT string
    """
    _check_secret()
    now = datetime.now(timezone.utc)

    if shift_end and shift_end > now:
        exp = shift_end
    else:
        exp = now + timedelta(hours=_JWT_DEFAULT_EXPIRY_HOURS)

    # Hard cap at 12 hours regardless
    max_exp = now + timedelta(hours=12)
    if exp > max_exp:
        exp = max_exp

    payload = {
        "sub": str(staff_id),
        "role": role,
        "iat": now,
        "exp": exp,
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)


def verify_token(token: str) -> dict:
    """Decode and validate a JWT. Returns the payload dict."""
    _check_secret()
    try:
        payload = jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
        )


async def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict:
    """
    FastAPI dependency — gates endpoints behind JWT auth.

    When AUTH_ENABLED=false (default/dev), returns a dummy payload
    so existing code keeps working without tokens.
    """
    if not AUTH_ENABLED:
        return {"sub": "0", "role": "manager"}

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return verify_token(credentials.credentials)


def require_role(*allowed_roles: str):
    """
    Factory for role-gated dependencies.

    Usage:
        @router.get("/admin-only", dependencies=[Depends(require_role("manager"))])
    """
    async def _check(payload: dict = Depends(require_auth)):
        if payload["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{payload['role']}' not permitted. Requires: {', '.join(allowed_roles)}",
            )
        return payload
    return _check


# ── Login endpoint helper ──

def authenticate_staff(pin: str, db: Session) -> dict:
    """
    Verify a staff PIN and return a JWT.

    Args:
        pin: raw PIN string (4-6 digits)
        db: database session

    Returns:
        {"token": "...", "staff_id": ..., "name": ..., "role": ...}
    """
    import hashlib
    from models import Staff, Shift

    if not pin or not pin.isdigit() or not (4 <= len(pin) <= 6):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PIN must be 4-6 digits",
        )

    pin_hash = hashlib.sha256(pin.encode()).hexdigest()

    staff = db.query(Staff).filter(
        Staff.pin_hash == pin_hash,
        Staff.is_active.is_(True),
    ).first()

    if not staff:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid PIN",
        )

    # Find current open shift to set token expiry
    current_shift = db.query(Shift).filter(
        Shift.status == "open",
    ).order_by(Shift.started_at.desc()).first()

    shift_end = None
    if current_shift and current_shift.ended_at:
        shift_end = current_shift.ended_at

    token = create_token(staff.id, staff.role, shift_end=shift_end)

    return {
        "token": token,
        "staff_id": staff.id,
        "name": staff.name,
        "role": staff.role,
    }
