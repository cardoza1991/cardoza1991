from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from ..database import get_db
from ..models.models import Aircraft, RiskScore, MaintenanceEvent
from ..services.risk_engine import compute_aircraft_risk

router = APIRouter(prefix="/api/fleet", tags=["fleet"])


def _enrich_aircraft(aircraft, db: Session) -> dict:
    """Add risk score to aircraft dict."""
    rs = db.query(RiskScore).filter(
        RiskScore.aircraft_id == aircraft.id,
        RiskScore.risk_type == "MISSION_READINESS"
    ).order_by(RiskScore.computed_at.desc()).first()

    score = rs.score if rs else 0
    level = "CRITICAL" if score >= 80 else "HIGH" if score >= 60 else "MEDIUM" if score >= 40 else "LOW"

    last_maint = None
    if aircraft.last_maintenance_date:
        last_maint = aircraft.last_maintenance_date.isoformat()

    next_maint = None
    days_to_next = None
    if aircraft.next_scheduled_maintenance:
        next_maint = aircraft.next_scheduled_maintenance.isoformat()
        days_to_next = (aircraft.next_scheduled_maintenance - datetime.utcnow()).days

    return {
        "id": aircraft.id,
        "tail_number": aircraft.tail_number,
        "platform": aircraft.platform,
        "squadron": aircraft.squadron,
        "base_location": aircraft.base_location,
        "mission_status": aircraft.mission_status,
        "flight_hours_total": aircraft.flight_hours_total,
        "last_maintenance_date": last_maint,
        "next_scheduled_maintenance": next_maint,
        "days_to_next_maintenance": days_to_next,
        "risk_score": score,
        "risk_level": level,
        "created_at": aircraft.created_at.isoformat() if aircraft.created_at else None,
    }


@router.get("/")
def list_aircraft(db: Session = Depends(get_db)):
    aircraft_list = db.query(Aircraft).all()
    return [_enrich_aircraft(a, db) for a in aircraft_list]


@router.get("/readiness-summary")
def readiness_summary(db: Session = Depends(get_db)):
    aircraft_list = db.query(Aircraft).all()
    total = len(aircraft_list)
    fmc = sum(1 for a in aircraft_list if a.mission_status == "FMC")
    pmc = sum(1 for a in aircraft_list if a.mission_status == "PMC")
    nmc = sum(1 for a in aircraft_list if a.mission_status == "NMC")
    at_risk = sum(1 for a in aircraft_list if a.mission_status == "AT_RISK")
    readiness_pct = (fmc / total * 100) if total > 0 else 0

    return {
        "total": total,
        "fmc": fmc,
        "pmc": pmc,
        "nmc": nmc,
        "at_risk": at_risk,
        "readiness_percentage": round(readiness_pct, 1),
        "degraded_count": nmc + at_risk,
    }


@router.get("/at-risk")
def at_risk_aircraft(db: Session = Depends(get_db)):
    aircraft_list = db.query(Aircraft).filter(
        Aircraft.mission_status.in_(["AT_RISK", "NMC"])
    ).all()
    result = [_enrich_aircraft(a, db) for a in aircraft_list]
    # Also add PMC with high risk scores
    pmc_list = db.query(Aircraft).filter(Aircraft.mission_status == "PMC").all()
    for a in pmc_list:
        enriched = _enrich_aircraft(a, db)
        if enriched["risk_score"] >= 60:
            result.append(enriched)
    result.sort(key=lambda x: x["risk_score"], reverse=True)
    return result


@router.get("/{tail_number}")
def aircraft_detail(tail_number: str, db: Session = Depends(get_db)):
    aircraft = db.query(Aircraft).filter(Aircraft.tail_number == tail_number).first()
    if not aircraft:
        raise HTTPException(status_code=404, detail=f"Aircraft {tail_number} not found")

    enriched = _enrich_aircraft(aircraft, db)

    # Add maintenance events
    events = db.query(MaintenanceEvent).filter(
        MaintenanceEvent.aircraft_id == aircraft.id
    ).order_by(MaintenanceEvent.scheduled_date.desc()).all()

    enriched["maintenance_events"] = [
        {
            "id": e.id,
            "event_type": e.event_type,
            "description": e.description,
            "scheduled_date": e.scheduled_date.isoformat() if e.scheduled_date else None,
            "completed_date": e.completed_date.isoformat() if e.completed_date else None,
            "status": e.status,
            "technician": e.technician,
            "requires_part": e.requires_part,
            "part_available": e.part_available,
            "downtime_hours": e.downtime_hours,
        }
        for e in events
    ]

    return enriched
