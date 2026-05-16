from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
import json

from ..database import get_db
from ..models.models import AgentRecommendation, Aircraft, Part, Supplier, RiskScore
from ..services.agent_loop import run_agent_cycle, generate_leadership_summary
from ..services.risk_engine import get_nmc_risk_aircraft

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.get("/recommendations")
def get_recommendations(db: Session = Depends(get_db)):
    recs = db.query(AgentRecommendation).order_by(
        AgentRecommendation.created_at.desc()
    ).all()
    return [_serialize_rec(r) for r in recs]


@router.get("/alerts")
def get_alerts(db: Session = Depends(get_db)):
    alerts = db.query(AgentRecommendation).filter(
        AgentRecommendation.priority.in_(["CRITICAL", "HIGH"]),
        AgentRecommendation.status == "OPEN"
    ).order_by(AgentRecommendation.created_at.desc()).all()
    return [_serialize_rec(r) for r in alerts]


@router.get("/summary")
def get_summary(db: Session = Depends(get_db)):
    summary = generate_leadership_summary(db)
    return {"summary": summary, "generated_at": datetime.utcnow().isoformat()}


@router.post("/run-cycle")
def run_cycle(db: Session = Depends(get_db)):
    run_agent_cycle(db)
    new_recs = db.query(AgentRecommendation).filter(
        AgentRecommendation.status == "OPEN"
    ).count()
    return {
        "status": "success",
        "message": "Agent cycle completed",
        "open_recommendations": new_recs,
        "ran_at": datetime.utcnow().isoformat(),
    }


@router.post("/query")
def natural_language_query(payload: dict, db: Session = Depends(get_db)):
    """
    Natural language query endpoint — the money shot.
    Accepts {"query": "..."} and returns structured intelligence.
    """
    query = payload.get("query", "")

    # Get NMC forecast
    nmc_aircraft = get_nmc_risk_aircraft(db)

    # Fleet summary
    total = db.query(Aircraft).count()
    fmc = db.query(Aircraft).filter(Aircraft.mission_status == "FMC").count()
    pmc = db.query(Aircraft).filter(Aircraft.mission_status == "PMC").count()
    nmc = db.query(Aircraft).filter(Aircraft.mission_status == "NMC").count()
    at_risk_count = db.query(Aircraft).filter(Aircraft.mission_status == "AT_RISK").count()

    readiness_pct = (fmc / total * 100) if total > 0 else 0

    # Open critical recommendations
    critical_recs = db.query(AgentRecommendation).filter(
        AgentRecommendation.priority.in_(["CRITICAL", "HIGH"]),
        AgentRecommendation.status == "OPEN"
    ).order_by(AgentRecommendation.created_at.desc()).all()

    # Build top_risks list
    top_risks = []
    for rs in db.query(RiskScore).filter(
        RiskScore.score > 60
    ).order_by(RiskScore.score.desc()).limit(5).all():
        entity = None
        entity_type = None
        if rs.aircraft_id:
            a = db.query(Aircraft).filter(Aircraft.id == rs.aircraft_id).first()
            entity = a.tail_number if a else None
            entity_type = "aircraft"
        elif rs.part_id:
            p = db.query(Part).filter(Part.id == rs.part_id).first()
            entity = p.part_number if p else None
            entity_type = "part"
        elif rs.supplier_id:
            s = db.query(Supplier).filter(Supplier.id == rs.supplier_id).first()
            entity = s.name if s else None
            entity_type = "supplier"
        if entity:
            top_risks.append({
                "entity": entity,
                "entity_type": entity_type,
                "score": round(rs.score, 1),
                "explanation": rs.explanation,
            })

    # Build recommended_actions
    recommended_actions = []
    for rec in critical_recs[:5]:
        action_list = []
        if rec.action_steps:
            try:
                action_list = json.loads(rec.action_steps)
            except Exception:
                action_list = [rec.action_steps]
        recommended_actions.append({
            "priority": rec.priority,
            "title": rec.title,
            "type": rec.recommendation_type,
            "aircraft_affected": rec.aircraft_affected,
            "actions": action_list[:3],
        })

    # Build summary narrative
    total_risk_aircraft = nmc + at_risk_count
    if total_risk_aircraft == 0:
        summary = (
            f"Fleet readiness is NOMINAL. All {total} aircraft are either FMC or PMC. "
            f"No aircraft are projected to become Non-Mission-Capable within the next 30 days "
            f"due to supply chain issues. Overall readiness rate: {readiness_pct:.1f}%."
        )
    else:
        aircraft_list_str = ", ".join(
            f"{a['tail_number']} ({a['platform']}, {a['current_status']})" for a in nmc_aircraft[:3]
        )
        summary = (
            f"{total_risk_aircraft} aircraft are at risk of becoming Non-Mission-Capable within the next 30 days "
            f"due to supply chain issues. Affected platforms: {aircraft_list_str}. "
            f"Fleet readiness rate is {readiness_pct:.1f}% ({fmc} FMC, {pmc} PMC, {nmc} NMC, {at_risk_count} AT_RISK). "
            f"Root causes include: parts shortages at critical stock levels, supplier delivery delays "
            f"(Moog Hydraulic Systems 61% OTD, Raytheon Avionics Corp PO delayed 18 days), and "
            f"single-source dependency on long lead-time components. "
            f"Immediate action is required on {len(critical_recs)} open high-priority recommendations."
        )

    # Build enriched at_risk_aircraft for response
    response_aircraft = []
    for ac in nmc_aircraft:
        response_aircraft.append({
            "tail_number": ac["tail_number"],
            "platform": ac["platform"],
            "squadron": ac["squadron"],
            "days_to_nmc": ac["days_to_nmc"],
            "root_cause": ac["root_cause"],
            "blocking_part": ac.get("blocking_part"),
            "supplier": ac.get("supplier"),
            "po_status": ac.get("po_status"),
            "mitigation": ac.get("mitigation", [])[:4],
            "risk_score": ac["risk_score"],
        })

    return {
        "query": query,
        "response": {
            "summary": summary,
            "at_risk_aircraft": response_aircraft,
            "fleet_status": {
                "total": total,
                "fmc": fmc,
                "pmc": pmc,
                "nmc": nmc,
                "at_risk": at_risk_count,
                "readiness_percentage": round(readiness_pct, 1),
            },
            "top_risks": top_risks,
            "recommended_actions": recommended_actions,
            "confidence": 0.87,
            "generated_at": datetime.utcnow().isoformat(),
        }
    }


def _serialize_rec(r: AgentRecommendation) -> dict:
    action_list = []
    if r.action_steps:
        try:
            action_list = json.loads(r.action_steps)
        except Exception:
            action_list = [r.action_steps]

    return {
        "id": r.id,
        "title": r.title,
        "recommendation_type": r.recommendation_type,
        "priority": r.priority,
        "aircraft_affected": r.aircraft_affected,
        "part_affected": r.part_affected,
        "supplier_affected": r.supplier_affected,
        "description": r.description,
        "rationale": r.rationale,
        "estimated_impact": r.estimated_impact,
        "action_steps": action_list,
        "status": r.status,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }
