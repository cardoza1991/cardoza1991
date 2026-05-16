import json
from datetime import datetime
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler

from ..models.models import (
    Aircraft, Part, Supplier, Inventory, PurchaseOrder,
    RiskScore, AgentRecommendation, MaintenanceEvent
)
from .risk_engine import run_full_risk_assessment, get_nmc_risk_aircraft
from .ml_predictor import predict_supplier_delay_probability, predict_stockout_probability
from ..database import SessionLocal

_scheduler = None


def run_agent_cycle(db: Session):
    """Run one full agent analysis cycle."""
    # Step 1: Run full risk assessment
    run_full_risk_assessment(db)

    # Step 2: Check parts with high risk → EXPEDITE_ORDER
    high_risk_parts = db.query(RiskScore).filter(
        RiskScore.risk_type == "SHORTAGE",
        RiskScore.score > 70,
        RiskScore.part_id.isnot(None)
    ).all()

    for rs in high_risk_parts:
        part = db.query(Part).filter(Part.id == rs.part_id).first()
        if not part:
            continue
        inv = db.query(Inventory).filter(Inventory.part_id == part.id).first()
        supplier = db.query(Supplier).filter(Supplier.id == part.supplier_id).first()

        # Check if recommendation already exists (open)
        existing = db.query(AgentRecommendation).filter(
            AgentRecommendation.part_affected == part.part_number,
            AgentRecommendation.recommendation_type == "EXPEDITE_ORDER",
            AgentRecommendation.status == "OPEN"
        ).first()

        if not existing:
            priority = "CRITICAL" if rs.score >= 85 else "HIGH"
            title = f"{priority}: Expedite order for {part.part_number} — risk score {rs.score:.0f}"
            description = rs.explanation or f"{part.part_number} supply chain risk detected."
            steps = [
                f"Contact {supplier.name if supplier else 'supplier'} immediately to expedite delivery",
                f"Review current stock: {inv.quantity_on_hand if inv else 'unknown'} units on hand",
                "Check sister units for available inventory",
                "Evaluate emergency procurement options",
                "Update maintenance schedule if part delivery will be delayed",
            ]
            rec = AgentRecommendation(
                title=title,
                recommendation_type="EXPEDITE_ORDER",
                priority=priority,
                part_affected=part.part_number,
                supplier_affected=supplier.name if supplier else None,
                description=description,
                rationale=f"Risk score {rs.score:.0f}/100. Shortage probability: {rs.shortage_probability:.0%}.",
                estimated_impact=f"Parts shortage could ground aircraft within {30} days.",
                action_steps=json.dumps(steps),
                status="OPEN",
            )
            db.add(rec)

    # Step 3: Check suppliers with high delay probability → FIND_ALT_SUPPLIER
    suppliers = db.query(Supplier).all()
    for supplier in suppliers:
        days_since_audit = 0
        if supplier.last_audit_date:
            days_since_audit = (datetime.utcnow() - supplier.last_audit_date).days

        delay_prob = predict_supplier_delay_probability({
            "reliability_score": supplier.reliability_score,
            "avg_lead_time": supplier.avg_lead_time_days,
            "on_time_rate": supplier.on_time_delivery_rate,
            "defect_rate": supplier.defect_rate,
            "days_since_audit": days_since_audit,
        })

        if delay_prob > 0.6:
            existing = db.query(AgentRecommendation).filter(
                AgentRecommendation.supplier_affected == supplier.name,
                AgentRecommendation.recommendation_type == "FIND_ALT_SUPPLIER",
                AgentRecommendation.status == "OPEN"
            ).first()

            if not existing:
                title = f"HIGH: Qualify alternative supplier — {supplier.name} delay probability {delay_prob:.0%}"
                steps = [
                    f"Initiate alternative supplier qualification process for {supplier.name} parts",
                    "Submit Corrective Action Request to supplier",
                    "Schedule emergency supplier audit",
                    "Review single-source parts for dual-source qualification",
                    "Brief supply chain leadership on risk",
                ]
                rec = AgentRecommendation(
                    title=title,
                    recommendation_type="FIND_ALT_SUPPLIER",
                    priority="HIGH",
                    supplier_affected=supplier.name,
                    description=f"{supplier.name} has {delay_prob:.0%} probability of delivery delay based on ML model analysis.",
                    rationale=f"OTD rate: {supplier.on_time_delivery_rate*100:.0f}%, reliability: {supplier.reliability_score:.2f}, defect rate: {supplier.defect_rate*100:.1f}%.",
                    estimated_impact=f"Supplier delay affects {supplier.single_source_parts_count} single-source parts.",
                    action_steps=json.dumps(steps),
                    status="OPEN",
                )
                db.add(rec)

    # Step 4: Check AT_RISK aircraft → ALERT
    at_risk_aircraft = db.query(Aircraft).filter(
        Aircraft.mission_status.in_(["AT_RISK", "NMC"])
    ).all()

    for aircraft in at_risk_aircraft:
        existing = db.query(AgentRecommendation).filter(
            AgentRecommendation.aircraft_affected == aircraft.tail_number,
            AgentRecommendation.recommendation_type == "ALERT",
            AgentRecommendation.status == "OPEN"
        ).first()

        if not existing:
            rs = db.query(RiskScore).filter(
                RiskScore.aircraft_id == aircraft.id,
                RiskScore.risk_type == "MISSION_READINESS"
            ).order_by(RiskScore.computed_at.desc()).first()

            score = rs.score if rs else 0
            explanation = rs.explanation if rs else f"{aircraft.tail_number} is {aircraft.mission_status}."

            priority = "CRITICAL" if aircraft.mission_status == "NMC" or score >= 85 else "HIGH"
            title = f"{priority}: {aircraft.tail_number} ({aircraft.platform}) is {aircraft.mission_status} — supply chain risk"

            steps = [
                f"Notify {aircraft.squadron} maintenance officer immediately",
                "Initiate NMCS/NMCM status documentation",
                "Brief operations officer on mission schedule impact",
                "Activate emergency supply chain protocols",
                "Submit AFMC/NAVAIR logistics escalation",
            ]
            rec = AgentRecommendation(
                title=title,
                recommendation_type="ALERT",
                priority=priority,
                aircraft_affected=aircraft.tail_number,
                description=explanation,
                rationale=f"Aircraft risk score: {score:.0f}/100. Status: {aircraft.mission_status}.",
                estimated_impact="Mission schedule impact — see affected missions in flight schedule.",
                action_steps=json.dumps(steps),
                status="OPEN",
            )
            db.add(rec)

    db.commit()


def generate_leadership_summary(db: Session) -> str:
    """Generate a rich text summary suitable for a commander's briefing."""
    now = datetime.utcnow()

    # Fleet status
    total = db.query(Aircraft).count()
    fmc = db.query(Aircraft).filter(Aircraft.mission_status == "FMC").count()
    pmc = db.query(Aircraft).filter(Aircraft.mission_status == "PMC").count()
    nmc = db.query(Aircraft).filter(Aircraft.mission_status == "NMC").count()
    at_risk = db.query(Aircraft).filter(Aircraft.mission_status == "AT_RISK").count()
    readiness_pct = (fmc / total * 100) if total > 0 else 0

    # Top risks
    nmc_aircraft = get_nmc_risk_aircraft(db)
    top_risks = nmc_aircraft[:3]

    # Open recommendations
    open_recs = db.query(AgentRecommendation).filter(
        AgentRecommendation.status == "OPEN",
        AgentRecommendation.priority.in_(["CRITICAL", "HIGH"])
    ).count()

    # Delayed POs
    delayed_pos = db.query(PurchaseOrder).filter(PurchaseOrder.status == "DELAYED").count()

    lines = [
        f"AERORISK AI — COMMANDER'S SUPPLY CHAIN BRIEF",
        f"Generated: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC",
        f"{'=' * 60}",
        f"",
        f"FLEET READINESS STATUS",
        f"  Total Aircraft: {total}",
        f"  Fully Mission Capable (FMC): {fmc} ({fmc/total*100:.0f}%)" if total > 0 else "  FMC: 0",
        f"  Partially Mission Capable (PMC): {pmc}",
        f"  Non-Mission-Capable (NMC): {nmc}",
        f"  At Risk (AT_RISK): {at_risk}",
        f"  Overall Readiness: {readiness_pct:.1f}%",
        f"",
        f"SUPPLY CHAIN RISK SUMMARY",
        f"  Open Critical/High Recommendations: {open_recs}",
        f"  Delayed Purchase Orders: {delayed_pos}",
        f"",
        f"TOP 3 NMC RISK AIRCRAFT (NEXT 30 DAYS)",
    ]

    for i, aircraft in enumerate(top_risks, 1):
        lines.append(f"")
        lines.append(f"  {i}. {aircraft['tail_number']} ({aircraft['platform']}) — {aircraft['current_status']}")
        lines.append(f"     Risk Score: {aircraft['risk_score']:.0f}/100 | Days to NMC: {aircraft['days_to_nmc']}")
        lines.append(f"     Root Cause: {aircraft['root_cause'][:200]}...")
        if aircraft.get("blocking_part"):
            lines.append(f"     Blocking Part: {aircraft['blocking_part']}")
        if aircraft.get("supplier"):
            lines.append(f"     Supplier: {aircraft['supplier']}")
        if aircraft.get("po_status"):
            lines.append(f"     PO Status: {aircraft['po_status']}")
        if aircraft.get("mitigation"):
            lines.append(f"     Recommended Action: {aircraft['mitigation'][0]}")

    lines.extend([
        f"",
        f"{'=' * 60}",
        f"ASSESSMENT: {'DEGRADED READINESS' if (nmc + at_risk) > 2 else 'CAUTION' if (nmc + at_risk) > 0 else 'NOMINAL'}",
        f"Immediate action required on {open_recs} open recommendations.",
        f"",
        f"[AeroRisk AI v1.0 — Autonomous Supply Chain Intelligence]",
    ])

    return "\n".join(lines)


def _agent_job():
    """Scheduled job wrapper."""
    db = SessionLocal()
    try:
        run_agent_cycle(db)
    except Exception as e:
        print(f"Agent cycle error: {e}")
    finally:
        db.close()


def start_scheduler():
    """Start the APScheduler background scheduler."""
    global _scheduler
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(_agent_job, "interval", seconds=60, id="agent_cycle", replace_existing=True)
    _scheduler.start()
