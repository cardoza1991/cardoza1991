from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from ..database import get_db
from ..models.models import Supplier, Part, PurchaseOrder, RiskScore, SupplierIntelSignal
from ..services.ml_predictor import predict_supplier_delay_probability
from ..services.risk_engine import _supplier_intel_risk, SUPPLIER_INTEL_WEIGHT

router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])


def _enrich_supplier(supplier: Supplier, db: Session) -> dict:
    rs = db.query(RiskScore).filter(
        RiskScore.supplier_id == supplier.id,
        RiskScore.risk_type == "SUPPLIER_DELAY"
    ).order_by(RiskScore.computed_at.desc()).first()

    score = rs.score if rs else 0

    # Count parts
    parts_count = db.query(Part).filter(Part.supplier_id == supplier.id).count()

    # Open POs
    open_pos = db.query(PurchaseOrder).filter(
        PurchaseOrder.supplier_id == supplier.id,
        PurchaseOrder.status.in_(["PENDING", "IN_TRANSIT", "DELAYED"])
    ).count()

    delayed_pos = db.query(PurchaseOrder).filter(
        PurchaseOrder.supplier_id == supplier.id,
        PurchaseOrder.status == "DELAYED"
    ).count()

    # ML delay prediction
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

    intel_risk, active_signals = _supplier_intel_risk(db, supplier.id)
    by_severity = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    by_category = {}
    for s in active_signals:
        by_severity[s.severity] = by_severity.get(s.severity, 0) + 1
        cat = s.category or "UNCATEGORIZED"
        by_category[cat] = by_category.get(cat, 0) + 1

    return {
        "id": supplier.id,
        "name": supplier.name,
        "country": supplier.country,
        "reliability_score": supplier.reliability_score,
        "avg_lead_time_days": supplier.avg_lead_time_days,
        "on_time_delivery_rate": supplier.on_time_delivery_rate,
        "defect_rate": supplier.defect_rate,
        "single_source_parts_count": supplier.single_source_parts_count,
        "is_approved": supplier.is_approved,
        "last_audit_date": supplier.last_audit_date.isoformat() if supplier.last_audit_date else None,
        "days_since_audit": days_since_audit,
        "parts_count": parts_count,
        "open_pos": open_pos,
        "delayed_pos": delayed_pos,
        "risk_score": round(score, 1),
        "risk_level": "CRITICAL" if score >= 80 else "HIGH" if score >= 60 else "MEDIUM" if score >= 40 else "LOW",
        "delay_probability": delay_prob,
        "explanation": rs.explanation if rs else None,
        "ticker": supplier.ticker,
        "cik": supplier.cik,
        "hq_country_code": supplier.hq_country_code,
        "hq_region": supplier.hq_region,
        "intel_signal_count": len(active_signals),
        "intel_contribution": round(intel_risk * SUPPLIER_INTEL_WEIGHT, 1),
        "intel_by_severity": by_severity,
        "intel_by_category": by_category,
        "intel_signals": [
            {
                "id": s.id,
                "source": s.source,
                "source_ref": s.source_ref,
                "category": s.category,
                "signal_type": s.signal_type,
                "severity": s.severity,
                "title": s.title,
                "body": s.body,
                "link": s.link,
                "observed_at": s.observed_at.isoformat() if s.observed_at else None,
                "match_confidence": s.match_confidence,
                "matched_on": s.matched_on,
                "numeric_value": s.numeric_value,
                "numeric_unit": s.numeric_unit,
            }
            for s in active_signals[:5]
        ],
    }


@router.get("/")
def list_suppliers(db: Session = Depends(get_db)):
    suppliers = db.query(Supplier).all()
    return [_enrich_supplier(s, db) for s in suppliers]


@router.get("/risk-map")
def risk_map(db: Session = Depends(get_db)):
    """Suppliers sorted by risk, with affected parts and aircraft context."""
    suppliers = db.query(Supplier).all()
    result = []

    for s in suppliers:
        enriched = _enrich_supplier(s, db)

        # Add affected parts summary
        parts = db.query(Part).filter(Part.supplier_id == s.id).all()
        critical_parts = [p.part_number for p in parts if p.is_mission_critical]
        single_source_parts = [p.part_number for p in parts if p.is_single_source]

        enriched["critical_parts"] = critical_parts[:5]
        enriched["single_source_parts"] = single_source_parts[:5]

        result.append(enriched)

    result.sort(key=lambda x: x["risk_score"], reverse=True)
    return result


@router.get("/{supplier_id}/intel")
def supplier_intel(supplier_id: int, db: Session = Depends(get_db)):
    """Full intel signal feed for a supplier — all active signals, newest first."""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail=f"Supplier {supplier_id} not found")

    signals = (
        db.query(SupplierIntelSignal)
        .filter(SupplierIntelSignal.supplier_id == supplier_id)
        .order_by(SupplierIntelSignal.observed_at.desc())
        .all()
    )
    return {
        "supplier_id": supplier.id,
        "supplier_name": supplier.name,
        "signals": [
            {
                "id": s.id,
                "source": s.source,
                "source_ref": s.source_ref,
                "signal_type": s.signal_type,
                "severity": s.severity,
                "title": s.title,
                "body": s.body,
                "link": s.link,
                "observed_at": s.observed_at.isoformat() if s.observed_at else None,
                "fetched_at": s.fetched_at.isoformat() if s.fetched_at else None,
                "is_active": s.is_active,
                "match_confidence": s.match_confidence,
                "matched_on": s.matched_on,
                "score_weight": s.score_weight,
            }
            for s in signals
        ],
    }


@router.get("/{supplier_id}")
def supplier_detail(supplier_id: int, db: Session = Depends(get_db)):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail=f"Supplier {supplier_id} not found")

    enriched = _enrich_supplier(supplier, db)

    # Add all parts
    parts = db.query(Part).filter(Part.supplier_id == supplier.id).all()
    enriched["parts"] = [
        {
            "part_number": p.part_number,
            "name": p.name,
            "category": p.category,
            "is_mission_critical": p.is_mission_critical,
            "is_single_source": p.is_single_source,
            "lead_time_days": p.lead_time_days,
        }
        for p in parts
    ]

    # All POs
    all_pos = db.query(PurchaseOrder).filter(
        PurchaseOrder.supplier_id == supplier.id
    ).order_by(PurchaseOrder.order_date.desc()).limit(20).all()

    enriched["purchase_orders"] = [
        {
            "po_number": po.po_number,
            "status": po.status,
            "delay_days": po.delay_days,
            "delay_reason": po.delay_reason,
            "expected_delivery_date": po.expected_delivery_date.isoformat() if po.expected_delivery_date else None,
        }
        for po in all_pos
    ]

    return enriched
