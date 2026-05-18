"""Auth + tenancy + audit tests."""

from __future__ import annotations

import os

# Ensure settings load BEFORE app imports
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
import jwt as pyjwt

from app.config import settings
from app.models.models import (
    AuditLog, BomUpload, ImpactScenario, Tenant, User,
)
from app.services.auth import (
    Identity, decode_token, ensure_default_tenant_and_user, hash_password,
    issue_token, verify_password,
)


# ---------------------------------------------------------------------------
# Password + token primitives
# ---------------------------------------------------------------------------

def test_hash_and_verify_password_roundtrip():
    h = hash_password("hunter2-very-secret")
    assert h.startswith("$2") and len(h) > 40
    assert verify_password("hunter2-very-secret", h) is True
    assert verify_password("wrong", h) is False
    # Junk input returns False rather than blowing up
    assert verify_password("x", "not-a-real-bcrypt-hash") is False


def test_issue_and_decode_token(db):
    ensure_default_tenant_and_user(db)
    user = db.query(User).filter(User.email == "admin@aerorisk.ai").first()
    token = issue_token(user)
    claims = decode_token(token)
    assert claims["sub"] == str(user.id)
    assert claims["email"] == user.email
    assert claims["tid"] == user.tenant_id
    assert claims["role"] == user.role


def test_decode_rejects_tampered_token(db):
    ensure_default_tenant_and_user(db)
    user = db.query(User).filter(User.email == "admin@aerorisk.ai").first()
    token = issue_token(user)
    # Flip a single character in the payload section.
    parts = token.split(".")
    parts[1] = parts[1][:-1] + ("A" if parts[1][-1] != "A" else "B")
    bad = ".".join(parts)
    with pytest.raises(pyjwt.InvalidSignatureError):
        decode_token(bad)


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

def test_ensure_default_tenant_and_user_is_idempotent(db):
    t1, u1 = ensure_default_tenant_and_user(db)
    t2, u2 = ensure_default_tenant_and_user(db)
    assert t1.id == t2.id
    assert u1.id == u2.id
    assert db.query(Tenant).count() == 1
    assert db.query(User).filter(User.email == "admin@aerorisk.ai").count() == 1


# ---------------------------------------------------------------------------
# Tenant scoping at the service layer
# ---------------------------------------------------------------------------

def test_record_scenario_persists_tenant_id(db, seeded_suppliers):
    from datetime import datetime, timedelta
    from app.models.models import Aircraft, Inventory, MaintenanceEvent, Part
    from app.services.impact_engine import simulate_supplier_failure
    from app.services.scenarios import record_scenario

    now = datetime.utcnow()
    honeywell = next(s for s in seeded_suppliers if s.name.startswith("Honeywell"))
    p = Part(part_number="HON-T1", name="Test LRU", supplier_id=honeywell.id,
             unit_cost=50_000.0, lead_time_days=30, lead_time_variance_days=5,
             is_mission_critical=True, is_single_source=True, category="Avionics")
    db.add(p); db.flush()
    db.add(Inventory(part_id=p.id, quantity_on_hand=1, quantity_on_order=0,
                     reorder_point=3, reorder_quantity=5, avg_monthly_consumption=2.0))
    ac = Aircraft(tail_number="AF-T1", platform="F-35A", squadron="X",
                  base_location="Test", mission_status="FMC", flight_hours_total=100)
    db.add(ac); db.flush()
    db.add(MaintenanceEvent(aircraft_id=ac.id, part_id=p.id, event_type="SCHEDULED",
                            description="t", status="SCHEDULED",
                            scheduled_date=now + timedelta(days=20), technician="T",
                            requires_part=True, part_available=True, downtime_hours=4))
    db.commit()

    impact = simulate_supplier_failure(db, honeywell.id, horizon_days=90)
    sc_a = record_scenario(db, impact, trigger="MANUAL", tenant_id=42)
    sc_b = record_scenario(db, impact, trigger="MANUAL", tenant_id=99)
    db.commit()
    assert sc_a.tenant_id == 42
    assert sc_b.tenant_id == 99
    # Different tenants → distinct rows even from the same impact.
    assert sc_a.id != sc_b.id


def test_analyze_bom_stamps_tenant_id(db):
    from app.services.bom import analyze_bom_upload
    result = analyze_bom_upload(
        db, filename="x.csv",
        raw="name,vendor,version\nFoo,Acme,1.0\n",
        tenant_id=7,
    )
    upload = db.query(BomUpload).filter(BomUpload.id == result.upload_id).first()
    assert upload.tenant_id == 7


# ---------------------------------------------------------------------------
# Permissive default identity resolution
# ---------------------------------------------------------------------------

def test_current_identity_anonymous_when_auth_not_required(db):
    """Default config: no token → anonymous identity, default tenant."""
    from app.services.auth import current_identity
    identity = current_identity(authorization=None, db=db)
    assert identity.anonymous is True
    assert identity.tenant_id == settings.default_tenant_id
    assert identity.role == "anonymous"


def test_current_identity_rejects_bad_token_even_in_demo_mode(db):
    from fastapi import HTTPException
    from app.services.auth import current_identity
    with pytest.raises(HTTPException) as exc:
        current_identity(authorization="Bearer not-a-token", db=db)
    assert exc.value.status_code == 401


def test_current_identity_resolves_valid_token(db):
    from app.services.auth import current_identity
    ensure_default_tenant_and_user(db)
    user = db.query(User).filter(User.email == "admin@aerorisk.ai").first()
    token = issue_token(user)
    identity = current_identity(authorization=f"Bearer {token}", db=db)
    assert identity.anonymous is False
    assert identity.user.id == user.id
    assert identity.tenant_id == user.tenant_id
    assert identity.role == "admin"
