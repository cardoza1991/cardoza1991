from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.models import RiskScore, Part, Aircraft, Supplier
from ..services.risk_engine import run_full_risk_assessment, get_nmc_risk_aircraft

router = APIRouter(prefix="/api/risk", tags=["risk"])


@router.get("/scores")
def all_risk_scores(db: Session = Depends(get_db)):
    scores = db.query(RiskScore).order_by(RiskScore.score.desc()).all()
    result = []
    for rs in scores:
        item = {
            "id": rs.id,
            "risk_type": rs.risk_type,
            "score": rs.score,
            "shortage_probability": rs.shortage_probability,
            "lead_time_volatility": rs.lead_time_volatility,
            "supplier_reliability_risk": rs.supplier_reliability_risk,
            "mission_criticality": rs.mission_criticality,
            "historical_failure_rate": rs.historical_failure_rate,
            "confidence_level": rs.confidence_level,
            "days_to_event": rs.days_to_event,
            "explanation": rs.explanation,
            "computed_at": rs.computed_at.isoformat() if rs.computed_at else None,
        }
        if rs.aircraft_id:
            a = db.query(Aircraft).filter(Aircraft.id == rs.aircraft_id).first()
            item["entity"] = a.tail_number if a else None
            item["entity_type"] = "aircraft"
        elif rs.part_id:
            p = db.query(Part).filter(Part.id == rs.part_id).first()
            item["entity"] = p.part_number if p else None
            item["entity_type"] = "part"
        elif rs.supplier_id:
            s = db.query(Supplier).filter(Supplier.id == rs.supplier_id).first()
            item["entity"] = s.name if s else None
            item["entity_type"] = "supplier"
        result.append(item)
    return result


@router.get("/dashboard")
def risk_dashboard(db: Session = Depends(get_db)):
    """Summary for main dashboard — top risks by category."""
    # Top parts by risk
    top_part_scores = db.query(RiskScore).filter(
        RiskScore.risk_type == "SHORTAGE",
        RiskScore.part_id.isnot(None)
    ).order_by(RiskScore.score.desc()).limit(5).all()

    top_parts = []
    for rs in top_part_scores:
        p = db.query(Part).filter(Part.id == rs.part_id).first()
        if p:
            top_parts.append({
                "part_number": p.part_number,
                "name": p.name,
                "score": rs.score,
                "explanation": rs.explanation,
            })

    # Top aircraft
    top_aircraft_scores = db.query(RiskScore).filter(
        RiskScore.risk_type == "MISSION_READINESS",
        RiskScore.aircraft_id.isnot(None)
    ).order_by(RiskScore.score.desc()).limit(5).all()

    top_aircraft = []
    for rs in top_aircraft_scores:
        a = db.query(Aircraft).filter(Aircraft.id == rs.aircraft_id).first()
        if a:
            top_aircraft.append({
                "tail_number": a.tail_number,
                "platform": a.platform,
                "status": a.mission_status,
                "score": rs.score,
                "explanation": rs.explanation,
            })

    # Top suppliers
    top_supplier_scores = db.query(RiskScore).filter(
        RiskScore.risk_type == "SUPPLIER_DELAY",
        RiskScore.supplier_id.isnot(None)
    ).order_by(RiskScore.score.desc()).limit(5).all()

    top_suppliers = []
    for rs in top_supplier_scores:
        s = db.query(Supplier).filter(Supplier.id == rs.supplier_id).first()
        if s:
            top_suppliers.append({
                "name": s.name,
                "country": s.country,
                "on_time_rate": s.on_time_delivery_rate,
                "score": rs.score,
                "explanation": rs.explanation,
            })

    # Risk distribution
    all_scores = db.query(RiskScore.score).all()
    scores = [s[0] for s in all_scores if s[0] is not None]
    critical = sum(1 for s in scores if s >= 80)
    high = sum(1 for s in scores if 60 <= s < 80)
    medium = sum(1 for s in scores if 40 <= s < 60)
    low = sum(1 for s in scores if s < 40)

    return {
        "top_parts": top_parts,
        "top_aircraft": top_aircraft,
        "top_suppliers": top_suppliers,
        "risk_distribution": {
            "critical": critical,
            "high": high,
            "medium": medium,
            "low": low,
        },
        "total_scores": len(scores),
        "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
    }


@router.post("/recompute")
def recompute_risks(db: Session = Depends(get_db)):
    """Trigger full risk recomputation."""
    run_full_risk_assessment(db)
    return {"status": "success", "message": "Full risk assessment completed"}


@router.get("/nmc-forecast")
def nmc_forecast(db: Session = Depends(get_db)):
    """The money shot — aircraft likely NMC in 30 days with full explanation."""
    result = get_nmc_risk_aircraft(db)
    return {
        "forecast_horizon_days": 30,
        "at_risk_count": len(result),
        "aircraft": result,
        "generated_at": __import__("datetime").datetime.utcnow().isoformat(),
    }
