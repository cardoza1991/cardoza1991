from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Optional
from ..models.models import (
    Aircraft, Part, Supplier, Inventory, PurchaseOrder,
    MaintenanceEvent, RiskScore
)


def predict_stockout_days(
    qty_on_hand: int,
    avg_monthly_consumption: float,
    qty_on_order: int,
    lead_time_days: int
) -> int:
    """Return estimated days until stockout. Returns 9999 if no stockout predicted."""
    if avg_monthly_consumption <= 0:
        return 9999
    daily_consumption = avg_monthly_consumption / 30.0
    if daily_consumption <= 0:
        return 9999
    days_of_stock = qty_on_hand / daily_consumption
    # If order arrives before stockout, extend timeline
    if qty_on_order > 0 and lead_time_days < days_of_stock:
        days_of_stock += qty_on_order / daily_consumption
    return max(0, int(days_of_stock))


def _shortage_probability(inv: Inventory, part: Part, active_po: Optional[PurchaseOrder]) -> float:
    """Compute shortage probability 0-1."""
    if inv is None:
        return 1.0
    if inv.quantity_on_hand <= 0:
        return 1.0
    ratio = inv.quantity_on_hand / max(1, inv.reorder_point)
    base = max(0.0, 1.0 - ratio * 0.5)
    # Increase if PO is delayed
    if active_po and active_po.status == "DELAYED":
        base = min(1.0, base + 0.25 + active_po.delay_days * 0.005)
    # Increase if lead time is very long
    lead_factor = min(0.3, part.lead_time_days / 360.0)
    return min(1.0, base + lead_factor)


def _lead_time_volatility(part: Part) -> float:
    """Compute lead time volatility risk 0-1."""
    if part.lead_time_days <= 0:
        return 0.0
    variance_ratio = part.lead_time_variance_days / max(1, part.lead_time_days)
    base = min(0.8, variance_ratio * 1.5)
    # Long lead times inherently riskier
    long_lead_factor = min(0.3, part.lead_time_days / 180.0)
    return min(1.0, base + long_lead_factor)


def _supplier_reliability_risk(supplier: Supplier) -> float:
    """Compute supplier reliability risk 0-1 (higher = more risky)."""
    if supplier is None:
        return 0.5
    # Lower reliability score → higher risk
    reliability_risk = 1.0 - supplier.reliability_score
    # Lower OTD → higher risk
    otd_risk = 1.0 - supplier.on_time_delivery_rate
    # Higher defect rate → higher risk
    defect_risk = min(1.0, supplier.defect_rate * 15)
    # Single source parts multiplier
    ss_factor = min(0.2, supplier.single_source_parts_count * 0.02)
    return min(1.0, (reliability_risk * 0.35 + otd_risk * 0.40 + defect_risk * 0.15 + ss_factor * 0.10))


def _mission_criticality(part: Part) -> float:
    """Compute mission criticality 0-1."""
    score = 0.3  # baseline
    if part.is_mission_critical:
        score += 0.5
    if part.is_single_source:
        score += 0.2
    return min(1.0, score)


def _historical_failure_rate(part: Part, db: Session) -> float:
    """Estimate historical failure rate from maintenance events."""
    total = db.query(MaintenanceEvent).filter(MaintenanceEvent.part_id == part.id).count()
    unscheduled = db.query(MaintenanceEvent).filter(
        MaintenanceEvent.part_id == part.id,
        MaintenanceEvent.event_type == "UNSCHEDULED"
    ).count()
    if total == 0:
        return 0.1  # baseline
    return min(1.0, unscheduled / max(1, total) + 0.1)


def compute_part_risk(db: Session, part_id: int) -> dict:
    """Compute all risk factors for a part. Returns dict with score and components."""
    part = db.query(Part).filter(Part.id == part_id).first()
    if not part:
        return {}

    inv = db.query(Inventory).filter(Inventory.part_id == part_id).first()
    supplier = db.query(Supplier).filter(Supplier.id == part.supplier_id).first()

    # Get most recent open PO
    active_po = db.query(PurchaseOrder).filter(
        PurchaseOrder.part_id == part_id,
        PurchaseOrder.status.in_(["PENDING", "IN_TRANSIT", "DELAYED"])
    ).order_by(PurchaseOrder.order_date.desc()).first()

    shortage_prob = _shortage_probability(inv, part, active_po)
    ltv = _lead_time_volatility(part)
    sup_risk = _supplier_reliability_risk(supplier)
    criticality = _mission_criticality(part)
    failure_rate = _historical_failure_rate(part, db)

    score = (shortage_prob * 25) + (ltv * 20) + (sup_risk * 20) + (criticality * 20) + (failure_rate * 15)

    stockout_days = 9999
    if inv:
        lead = part.lead_time_days + (active_po.delay_days if active_po and active_po.status == "DELAYED" else 0)
        on_order = inv.quantity_on_order if inv.quantity_on_order else 0
        stockout_days = predict_stockout_days(inv.quantity_on_hand, inv.avg_monthly_consumption, on_order, lead)

    explanation = _build_part_explanation(part, inv, supplier, active_po, shortage_prob, score)

    return {
        "score": round(score, 1),
        "shortage_probability": round(shortage_prob, 3),
        "lead_time_volatility": round(ltv, 3),
        "supplier_reliability_risk": round(sup_risk, 3),
        "mission_criticality": round(criticality, 3),
        "historical_failure_rate": round(failure_rate, 3),
        "confidence_level": 0.85,
        "stockout_days": stockout_days,
        "explanation": explanation,
        "part": part,
        "inventory": inv,
        "supplier": supplier,
        "active_po": active_po,
    }


def _build_part_explanation(part, inv, supplier, active_po, shortage_prob, score) -> str:
    parts = [f"{part.part_number} ({part.name}):"]
    if inv:
        parts.append(f"Stock: {inv.quantity_on_hand} units (reorder point: {inv.reorder_point}).")
    if supplier:
        parts.append(f"Supplier: {supplier.name}, OTD: {supplier.on_time_delivery_rate*100:.0f}%, lead time: {part.lead_time_days} days.")
    if active_po:
        if active_po.status == "DELAYED":
            parts.append(f"PO {active_po.po_number} DELAYED {active_po.delay_days} days: {active_po.delay_reason or 'reason unknown'}.")
        else:
            parts.append(f"PO {active_po.po_number} status: {active_po.status}.")
    if part.is_single_source:
        parts.append("SINGLE SOURCE — no alternative supplier available.")
    return " ".join(parts)


def compute_aircraft_risk(db: Session, aircraft_id: int) -> dict:
    """Aggregate part risks for an aircraft's pending maintenance needs."""
    aircraft = db.query(Aircraft).filter(Aircraft.id == aircraft_id).first()
    if not aircraft:
        return {}

    # Get upcoming maintenance events needing parts
    pending_events = db.query(MaintenanceEvent).filter(
        MaintenanceEvent.aircraft_id == aircraft_id,
        MaintenanceEvent.status.in_(["SCHEDULED", "IN_PROGRESS"]),
        MaintenanceEvent.requires_part == True
    ).all()

    max_risk = 0.0
    explanations = []
    blocking_parts = []

    for event in pending_events:
        if event.part_id:
            pr = compute_part_risk(db, event.part_id)
            if pr:
                if pr["score"] > max_risk:
                    max_risk = pr["score"]
                if not event.part_available:
                    blocking_parts.append(pr.get("part"))
                    explanations.append(f"Maintenance event '{event.description}' requires {pr.get('part', {}).part_number if pr.get('part') else 'unknown'} — NOT AVAILABLE.")
                elif pr["score"] > 50:
                    explanations.append(f"Required part has risk score {pr['score']:.0f}. {pr['explanation']}")

    # Weight the aircraft's own status
    status_penalty = {"NMC": 30, "AT_RISK": 20, "PMC": 5, "FMC": 0}.get(aircraft.mission_status, 0)
    final_score = min(100, max_risk + status_penalty * 0.3)

    explanation = f"Aircraft {aircraft.tail_number} ({aircraft.platform}), status: {aircraft.mission_status}. "
    if explanations:
        explanation += " ".join(explanations)
    elif final_score < 30:
        explanation += "No significant supply chain risks identified."

    return {
        "score": round(final_score, 1),
        "explanation": explanation,
        "blocking_parts": blocking_parts,
        "pending_events": pending_events,
    }


def compute_supplier_risk(db: Session, supplier_id: int) -> dict:
    """Compute supplier reliability risk."""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        return {}

    sup_risk = _supplier_reliability_risk(supplier)
    # Check delayed POs
    delayed_pos = db.query(PurchaseOrder).filter(
        PurchaseOrder.supplier_id == supplier_id,
        PurchaseOrder.status == "DELAYED"
    ).count()
    delay_factor = min(0.3, delayed_pos * 0.1)
    score = min(100, (sup_risk + delay_factor) * 100)

    explanation = (
        f"{supplier.name}: reliability {supplier.reliability_score:.2f}, "
        f"OTD {supplier.on_time_delivery_rate*100:.0f}%, "
        f"defect rate {supplier.defect_rate*100:.1f}%, "
        f"{supplier.single_source_parts_count} single-source parts, "
        f"{delayed_pos} delayed POs."
    )

    return {
        "score": round(score, 1),
        "supplier_reliability_risk": round(sup_risk, 3),
        "delayed_pos": delayed_pos,
        "explanation": explanation,
    }


def run_full_risk_assessment(db: Session):
    """Recompute all RiskScore records."""
    now = datetime.utcnow()

    # Part risks
    parts = db.query(Part).all()
    for part in parts:
        pr = compute_part_risk(db, part.id)
        if not pr:
            continue
        # Upsert RiskScore for this part
        existing = db.query(RiskScore).filter(
            RiskScore.part_id == part.id,
            RiskScore.risk_type == "SHORTAGE"
        ).first()
        if existing:
            existing.score = pr["score"]
            existing.shortage_probability = pr["shortage_probability"]
            existing.lead_time_volatility = pr["lead_time_volatility"]
            existing.supplier_reliability_risk = pr["supplier_reliability_risk"]
            existing.mission_criticality = pr["mission_criticality"]
            existing.historical_failure_rate = pr["historical_failure_rate"]
            existing.explanation = pr["explanation"]
            existing.computed_at = now
        else:
            rs = RiskScore(
                part_id=part.id,
                risk_type="SHORTAGE",
                score=pr["score"],
                shortage_probability=pr["shortage_probability"],
                lead_time_volatility=pr["lead_time_volatility"],
                supplier_reliability_risk=pr["supplier_reliability_risk"],
                mission_criticality=pr["mission_criticality"],
                historical_failure_rate=pr["historical_failure_rate"],
                confidence_level=pr["confidence_level"],
                explanation=pr["explanation"],
                computed_at=now,
            )
            db.add(rs)

    # Aircraft risks
    aircraft_list = db.query(Aircraft).all()
    for aircraft in aircraft_list:
        ar = compute_aircraft_risk(db, aircraft.id)
        if not ar:
            continue
        existing = db.query(RiskScore).filter(
            RiskScore.aircraft_id == aircraft.id,
            RiskScore.risk_type == "MISSION_READINESS"
        ).first()
        if existing:
            existing.score = ar["score"]
            existing.explanation = ar["explanation"]
            existing.computed_at = now
        else:
            rs = RiskScore(
                aircraft_id=aircraft.id,
                risk_type="MISSION_READINESS",
                score=ar["score"],
                explanation=ar["explanation"],
                confidence_level=0.85,
                computed_at=now,
            )
            db.add(rs)

    # Supplier risks
    suppliers = db.query(Supplier).all()
    for supplier in suppliers:
        sr = compute_supplier_risk(db, supplier.id)
        if not sr:
            continue
        existing = db.query(RiskScore).filter(
            RiskScore.supplier_id == supplier.id,
            RiskScore.risk_type == "SUPPLIER_DELAY"
        ).first()
        if existing:
            existing.score = sr["score"]
            existing.explanation = sr["explanation"]
            existing.computed_at = now
        else:
            rs = RiskScore(
                supplier_id=supplier.id,
                risk_type="SUPPLIER_DELAY",
                score=sr["score"],
                supplier_reliability_risk=sr["supplier_reliability_risk"],
                explanation=sr["explanation"],
                confidence_level=0.80,
                computed_at=now,
            )
            db.add(rs)

    db.commit()


def get_nmc_risk_aircraft(db: Session) -> list:
    """Returns aircraft likely to go NMC within 30 days with full explanation."""
    at_risk = []
    aircraft_list = db.query(Aircraft).filter(
        Aircraft.mission_status.in_(["AT_RISK", "NMC", "PMC"])
    ).all()

    for aircraft in aircraft_list:
        # Get latest risk score
        rs = db.query(RiskScore).filter(
            RiskScore.aircraft_id == aircraft.id,
            RiskScore.risk_type == "MISSION_READINESS"
        ).order_by(RiskScore.computed_at.desc()).first()

        score = rs.score if rs else 0

        if score < 40 and aircraft.mission_status == "PMC":
            continue

        # Find blocking maintenance events
        blocking_events = db.query(MaintenanceEvent).filter(
            MaintenanceEvent.aircraft_id == aircraft.id,
            MaintenanceEvent.status.in_(["SCHEDULED", "IN_PROGRESS"]),
            MaintenanceEvent.requires_part == True,
            MaintenanceEvent.part_available == False
        ).all()

        # Days to NMC estimate
        days_to_nmc = rs.days_to_event if rs and rs.days_to_event else 30
        if aircraft.mission_status == "NMC":
            days_to_nmc = 0

        # Build blocking part info
        blocking_part = None
        supplier_name = None
        po_status_str = None
        mitigation = []

        if blocking_events:
            be = blocking_events[0]
            if be.part_id:
                part = db.query(Part).filter(Part.id == be.part_id).first()
                if part:
                    blocking_part = part.part_number
                    sup = db.query(Supplier).filter(Supplier.id == part.supplier_id).first()
                    if sup:
                        supplier_name = sup.name
                    active_po = db.query(PurchaseOrder).filter(
                        PurchaseOrder.part_id == part.id,
                        PurchaseOrder.status.in_(["PENDING", "IN_TRANSIT", "DELAYED"])
                    ).order_by(PurchaseOrder.order_date.desc()).first()
                    if active_po:
                        if active_po.status == "DELAYED":
                            po_status_str = f"DELAYED {active_po.delay_days} days"
                        else:
                            po_status_str = active_po.status
                    inv = db.query(Inventory).filter(Inventory.part_id == part.id).first()
                    mitigation = _build_mitigation(aircraft, part, inv, sup, active_po)

        root_cause = rs.explanation if rs else f"Aircraft {aircraft.tail_number} has supply chain risk."

        at_risk.append({
            "tail_number": aircraft.tail_number,
            "platform": aircraft.platform,
            "squadron": aircraft.squadron,
            "current_status": aircraft.mission_status,
            "days_to_nmc": days_to_nmc,
            "risk_score": score,
            "root_cause": root_cause,
            "blocking_part": blocking_part,
            "supplier": supplier_name,
            "po_status": po_status_str,
            "mitigation": mitigation,
        })

    # Sort by risk score descending
    at_risk.sort(key=lambda x: x["risk_score"], reverse=True)
    return at_risk


def _build_mitigation(aircraft, part, inv, supplier, active_po) -> list:
    actions = []
    if active_po and active_po.status == "DELAYED":
        actions.append(f"Expedite PO {active_po.po_number} with {supplier.name if supplier else 'supplier'} — authorize premium freight")
    if supplier and supplier.reliability_score < 0.80:
        actions.append(f"Engage alternative supplier — {supplier.name} OTD rate {supplier.on_time_delivery_rate*100:.0f}% is below threshold")
    if inv and inv.quantity_on_hand <= 1:
        actions.append(f"Survey sister units for {part.part_number} loan/exchange")
        actions.append("Submit emergency requisition to depot supply chain")
    actions.append(f"Evaluate deferring {aircraft.tail_number} maintenance if operationally feasible")
    actions.append("Update mission planning to reflect aircraft availability constraints")
    return actions
