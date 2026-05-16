"""Persisted impact scenarios + public share endpoints + notification audit."""

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.models import ImpactScenario, NotificationLog, Supplier, SupplierIntelSignal

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


def _serialize(s: ImpactScenario, db: Session, include_snapshot: bool = False) -> dict:
    sup = db.query(Supplier).filter(Supplier.id == s.supplier_id).first() if s.supplier_id else None
    sig = (
        db.query(SupplierIntelSignal).filter(SupplierIntelSignal.id == s.trigger_signal_id).first()
        if s.trigger_signal_id else None
    )
    out = {
        "id": s.id,
        "supplier_id": s.supplier_id,
        "supplier_name": sup.name if sup else None,
        "trigger": s.trigger,
        "trigger_signal_id": s.trigger_signal_id,
        "trigger_signal_title": sig.title if sig else None,
        "trigger_signal_source": sig.source if sig else None,
        "horizon_days": s.horizon_days,
        "severity": s.severity,
        "aircraft_affected": s.aircraft_affected,
        "production_delay_days": s.production_delay_days,
        "dollar_exposure_usd": s.dollar_exposure_usd,
        "confidence": s.confidence,
        "one_liner": s.one_liner,
        "notified": s.notified,
        "share_token": s.share_token,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }
    if include_snapshot and s.snapshot_json:
        try:
            out["snapshot"] = json.loads(s.snapshot_json)
        except json.JSONDecodeError:
            out["snapshot"] = None
    return out


@router.get("/")
def list_scenarios(
    trigger: Optional[str] = Query(None, description="AUTO_INTEL | MANUAL | SCHEDULED"),
    severity: Optional[str] = Query(None),
    supplier_id: Optional[int] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    """Timeline of scenarios, newest first. Powers the autonomous trigger feed."""
    q = db.query(ImpactScenario)
    if trigger:
        q = q.filter(ImpactScenario.trigger == trigger.upper())
    if severity:
        q = q.filter(ImpactScenario.severity == severity.upper())
    if supplier_id is not None:
        q = q.filter(ImpactScenario.supplier_id == supplier_id)
    rows = q.order_by(ImpactScenario.created_at.desc()).limit(limit).all()
    return [_serialize(s, db) for s in rows]


@router.get("/{scenario_id}")
def get_scenario(scenario_id: int, db: Session = Depends(get_db)):
    s = db.query(ImpactScenario).filter(ImpactScenario.id == scenario_id).first()
    if not s:
        raise HTTPException(404, "scenario not found")
    return _serialize(s, db, include_snapshot=True)


@router.get("/share/{token}")
def get_scenario_by_token(token: str, db: Session = Depends(get_db)):
    """Unauthenticated read by share token — powers public scenario links."""
    s = db.query(ImpactScenario).filter(ImpactScenario.share_token == token).first()
    if not s:
        raise HTTPException(404, "scenario not found")
    return _serialize(s, db, include_snapshot=True)


@router.get("/notifications/log")
def notification_log(
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
):
    """Audit trail: who got pinged about what, when, with what result."""
    rows = (
        db.query(NotificationLog)
        .order_by(NotificationLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return [{
        "id": n.id,
        "channel": n.channel,
        "target": n.target,
        "scenario_id": n.scenario_id,
        "signal_id": n.signal_id,
        "status": n.status,
        "error": n.error,
        "payload_preview": n.payload_preview,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    } for n in rows]
