"""Audit log writer.

Records mutating HTTP operations against the app. Append-only.
Drops the read endpoints (GET) on purpose — auditing every dashboard
poll would drown the table without adding security value.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import Request, Response
from sqlalchemy.orm import Session

from ..config import settings
from ..database import SessionLocal
from ..models.models import AuditLog
from .auth import _extract_token, decode_token

log = logging.getLogger(__name__)

# Methods we audit. GETs are read-only and skipped.
AUDITED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Path prefixes we always skip even on POST (e.g. login itself logs separately).
SKIP_PATHS = ("/api/auth/login",)


def _resource_from_path(path: str) -> tuple[Optional[str], Optional[str]]:
    """Pull a (resource_type, resource_id) guess out of the URL path."""
    parts = [p for p in path.split("/") if p]
    if len(parts) >= 2 and parts[0] == "api":
        resource_type = parts[1].rstrip("s").capitalize()  # /api/bom → "Bom"
        resource_id = parts[2] if len(parts) >= 3 else None
        return resource_type, resource_id
    return None, None


async def audit_middleware(request: Request, call_next):
    """Starlette middleware. Wraps the response and writes an AuditLog row
    after the response is generated for any mutating request.

    Auth is decoded best-effort here — the actual auth dependency runs in the
    route, so we don't repeat its strictness. If the token is invalid the
    audit row simply records anonymous + the bad attempt.
    """
    response = await call_next(request)

    if not settings.audit_enabled:
        return response
    method = request.method.upper()
    if method not in AUDITED_METHODS:
        return response
    path = request.url.path
    if any(path.startswith(p) for p in SKIP_PATHS):
        return response

    tenant_id = None
    user_id = None
    user_email = None
    try:
        token = _extract_token(request.headers.get("authorization"))
        if token:
            claims = decode_token(token)
            user_id = int(claims.get("sub")) if claims.get("sub") else None
            user_email = claims.get("email")
            tenant_id = claims.get("tid")
    except Exception:
        pass  # invalid tokens still get audited — anonymous attempt

    if tenant_id is None:
        tenant_id = settings.default_tenant_id

    resource_type, resource_id = _resource_from_path(path)

    db: Session = SessionLocal()
    try:
        db.add(AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            user_email=user_email,
            action=f"{method.lower()}.{path.lstrip('/').replace('/', '.')}",
            resource_type=resource_type,
            resource_id=resource_id,
            method=method,
            path=path,
            status_code=response.status_code,
            ip=request.client.host if request.client else None,
            user_agent=(request.headers.get("user-agent") or "")[:400],
        ))
        db.commit()
    except Exception as e:                                             # pragma: no cover
        log.warning("audit log write failed for %s %s: %s", method, path, e)
        db.rollback()
    finally:
        db.close()
    return response
