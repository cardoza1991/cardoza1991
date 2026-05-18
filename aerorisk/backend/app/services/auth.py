"""Auth + tenancy primitives.

- bcrypt password hashing (no plaintext, ever)
- JWT issuance/validation
- FastAPI dependencies for `current_user` and `current_tenant`

Permissive by default (`require_auth=false`): anonymous requests resolve
to the default tenant + a synthetic "anonymous" user. This keeps the
demo working. Flip `require_auth=true` in any real deployment.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models.models import Tenant, User


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("ascii"))
    except (ValueError, TypeError):
        return False


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------

def issue_token(user: User) -> str:
    now = datetime.utcnow()
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "tid": user.tenant_id,
        "role": user.role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_expiry_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


# ---------------------------------------------------------------------------
# Identity resolution
# ---------------------------------------------------------------------------

@dataclass
class Identity:
    user: Optional[User]
    tenant_id: int
    anonymous: bool

    @property
    def email(self) -> str:
        return self.user.email if self.user else "anonymous"

    @property
    def role(self) -> str:
        return self.user.role if self.user else "anonymous"


def _extract_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split(None, 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return None


def current_identity(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> Identity:
    """Resolve the caller. Behavior depends on `require_auth`:

    - `require_auth=false` (default demo mode):
        * No token → anonymous identity in the default tenant.
        * Valid token → authenticated identity in token's tenant.
        * Invalid token → 401 (a bad token is still a bug).
    - `require_auth=true`:
        * No or invalid token → 401.
    """
    token = _extract_token(authorization)
    if not token:
        if settings.require_auth:
            raise HTTPException(401, "authentication required")
        return Identity(user=None, tenant_id=settings.default_tenant_id, anonymous=True)

    try:
        claims = decode_token(token)
    except jwt.PyJWTError as e:
        raise HTTPException(401, f"invalid token: {e.__class__.__name__}")

    user_id = int(claims.get("sub", 0))
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()  # noqa: E712
    if not user:
        raise HTTPException(401, "user not found or inactive")
    return Identity(user=user, tenant_id=user.tenant_id, anonymous=False)


def require_role(*roles: str):
    """Dependency factory for role-gated endpoints."""
    def _check(identity: Identity = Depends(current_identity)) -> Identity:
        if settings.require_auth and identity.anonymous:
            raise HTTPException(401, "authentication required")
        if roles and identity.role not in roles and not identity.anonymous:
            raise HTTPException(403, f"role {identity.role} not authorized")
        return identity
    return _check


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

def ensure_default_tenant_and_user(db: Session) -> tuple[Tenant, Optional[User]]:
    """Idempotent: create the demo tenant + admin user if they don't exist.

    Called at startup. The default password is intentionally weak — operators
    are expected to rotate it on first login. The hashed value is stored, not
    the plaintext.
    """
    tenant = db.query(Tenant).filter(Tenant.id == settings.default_tenant_id).first()
    if not tenant:
        tenant = Tenant(
            id=settings.default_tenant_id, name="Demo Aerospace Co.",
            slug="demo-aerospace", is_active=True,
        )
        db.add(tenant)
        db.flush()

    user = db.query(User).filter(User.email == "admin@aerorisk.ai").first()
    if not user:
        user = User(
            tenant_id=tenant.id, email="admin@aerorisk.ai",
            full_name="Demo Administrator", role="admin",
            password_hash=hash_password("demo1234"),
            is_active=True,
        )
        db.add(user)
        db.flush()
    db.commit()
    return tenant, user
