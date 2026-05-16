from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models.models import AuditLog, Tenant, User
from ..services.auth import (
    Identity, current_identity, hash_password, issue_token,
    require_role, verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    token: str
    user: dict
    tenant: dict
    expires_in_seconds: int


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not user.is_active or not verify_password(req.password, user.password_hash):
        # Record the failed attempt for audit (login bypasses the middleware
        # SKIP_PATHS but we still want failures logged).
        if settings.audit_enabled:
            db.add(AuditLog(
                tenant_id=user.tenant_id if user else settings.default_tenant_id,
                user_id=user.id if user else None,
                user_email=req.email,
                action="auth.login.failed",
                method="POST", path="/api/auth/login", status_code=401,
                ip=request.client.host if request.client else None,
                user_agent=(request.headers.get("user-agent") or "")[:400],
            ))
            db.commit()
        raise HTTPException(401, "invalid email or password")

    user.last_login_at = datetime.utcnow()
    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    token = issue_token(user)

    if settings.audit_enabled:
        db.add(AuditLog(
            tenant_id=user.tenant_id, user_id=user.id, user_email=user.email,
            action="auth.login.success", method="POST", path="/api/auth/login",
            status_code=200, ip=request.client.host if request.client else None,
            user_agent=(request.headers.get("user-agent") or "")[:400],
        ))
    db.commit()

    return LoginResponse(
        token=token,
        user={
            "id": user.id, "email": user.email, "full_name": user.full_name,
            "role": user.role, "tenant_id": user.tenant_id,
        },
        tenant={"id": tenant.id, "name": tenant.name, "slug": tenant.slug} if tenant else {},
        expires_in_seconds=settings.jwt_expiry_minutes * 60,
    )


@router.get("/me")
def me(identity: Identity = Depends(current_identity), db: Session = Depends(get_db)):
    if identity.anonymous:
        return {
            "anonymous": True,
            "tenant_id": identity.tenant_id,
            "require_auth": settings.require_auth,
        }
    tenant = db.query(Tenant).filter(Tenant.id == identity.tenant_id).first()
    return {
        "anonymous": False,
        "user": {
            "id": identity.user.id, "email": identity.user.email,
            "full_name": identity.user.full_name, "role": identity.user.role,
        },
        "tenant": {"id": tenant.id, "name": tenant.name, "slug": tenant.slug} if tenant else None,
        "require_auth": settings.require_auth,
    }


class CreateUserRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: str = "operator"


@router.post("/users")
def create_user(
    req: CreateUserRequest,
    db: Session = Depends(get_db),
    identity: Identity = Depends(require_role("admin")),
):
    """Admin-only. Creates a user in the caller's tenant."""
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(409, "email already registered")
    if req.role not in ("admin", "operator", "viewer"):
        raise HTTPException(400, "invalid role")
    user = User(
        tenant_id=identity.tenant_id, email=req.email, full_name=req.full_name,
        role=req.role, password_hash=hash_password(req.password), is_active=True,
    )
    db.add(user); db.commit()
    return {"id": user.id, "email": user.email, "role": user.role, "tenant_id": user.tenant_id}


@router.get("/audit-log")
def get_audit_log(
    limit: int = Query(200, le=1000),
    action_prefix: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    identity: Identity = Depends(require_role("admin")),
):
    """Tenant-scoped audit log. Admin only."""
    q = db.query(AuditLog).filter(AuditLog.tenant_id == identity.tenant_id)
    if action_prefix:
        q = q.filter(AuditLog.action.like(f"{action_prefix}%"))
    rows = q.order_by(AuditLog.created_at.desc()).limit(limit).all()
    return [{
        "id": r.id, "user_email": r.user_email, "action": r.action,
        "resource_type": r.resource_type, "resource_id": r.resource_id,
        "method": r.method, "path": r.path, "status_code": r.status_code,
        "ip": r.ip, "user_agent": r.user_agent,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in rows]
