from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from ..database import get_db
from ..models.models import Part, Inventory, Supplier, PurchaseOrder, RiskScore
from ..services.risk_engine import predict_stockout_days, compute_part_risk
from ..services.ml_predictor import predict_stockout_probability

router = APIRouter(prefix="/api/parts", tags=["parts"])


def _enrich_part(part: Part, db: Session) -> dict:
    inv = db.query(Inventory).filter(Inventory.part_id == part.id).first()
    supplier = db.query(Supplier).filter(Supplier.id == part.supplier_id).first()
    rs = db.query(RiskScore).filter(
        RiskScore.part_id == part.id,
        RiskScore.risk_type == "SHORTAGE"
    ).order_by(RiskScore.computed_at.desc()).first()

    score = rs.score if rs else 0

    qty_on_hand = inv.quantity_on_hand if inv else 0
    qty_on_order = inv.quantity_on_order if inv else 0
    reorder_point = inv.reorder_point if inv else 0
    avg_consumption = inv.avg_monthly_consumption if inv else 1.0

    # Active PO
    active_po = db.query(PurchaseOrder).filter(
        PurchaseOrder.part_id == part.id,
        PurchaseOrder.status.in_(["PENDING", "IN_TRANSIT", "DELAYED"])
    ).order_by(PurchaseOrder.order_date.desc()).first()

    stockout_days = predict_stockout_days(qty_on_hand, avg_consumption, qty_on_order, part.lead_time_days)

    stockout_prob = predict_stockout_probability({
        "qty_on_hand": qty_on_hand,
        "avg_consumption": avg_consumption,
        "lead_time_days": part.lead_time_days,
        "qty_on_order": qty_on_order,
        "reorder_point": reorder_point,
    })

    po_info = None
    if active_po:
        po_info = {
            "po_number": active_po.po_number,
            "status": active_po.status,
            "delay_days": active_po.delay_days,
            "expected_delivery_date": active_po.expected_delivery_date.isoformat() if active_po.expected_delivery_date else None,
        }

    return {
        "id": part.id,
        "part_number": part.part_number,
        "name": part.name,
        "description": part.description,
        "platform_compatibility": part.platform_compatibility,
        "category": part.category,
        "unit_cost": part.unit_cost,
        "lead_time_days": part.lead_time_days,
        "lead_time_variance_days": part.lead_time_variance_days,
        "is_mission_critical": part.is_mission_critical,
        "is_single_source": part.is_single_source,
        "supplier_id": part.supplier_id,
        "supplier_name": supplier.name if supplier else None,
        "supplier_reliability": supplier.reliability_score if supplier else None,
        "inventory": {
            "quantity_on_hand": qty_on_hand,
            "quantity_on_order": qty_on_order,
            "reorder_point": reorder_point,
            "reorder_quantity": inv.reorder_quantity if inv else 0,
            "warehouse_location": inv.warehouse_location if inv else None,
            "avg_monthly_consumption": avg_consumption,
        } if inv else None,
        "risk_score": round(score, 1),
        "risk_level": "CRITICAL" if score >= 80 else "HIGH" if score >= 60 else "MEDIUM" if score >= 40 else "LOW",
        "stockout_days": stockout_days if stockout_days < 9999 else None,
        "stockout_probability": stockout_prob,
        "active_po": po_info,
        "explanation": rs.explanation if rs else None,
    }


@router.get("/")
def list_parts(db: Session = Depends(get_db)):
    parts = db.query(Part).all()
    return [_enrich_part(p, db) for p in parts]


@router.get("/critical-watchlist")
def critical_watchlist(db: Session = Depends(get_db)):
    """Parts with risk > 50 or qty_on_hand below reorder_point."""
    parts = db.query(Part).all()
    result = []
    for p in parts:
        enriched = _enrich_part(p, db)
        inv_info = enriched.get("inventory")
        qty_on_hand = inv_info["quantity_on_hand"] if inv_info else 0
        reorder_point = inv_info["reorder_point"] if inv_info else 0
        if enriched["risk_score"] > 50 or qty_on_hand <= reorder_point:
            result.append(enriched)
    result.sort(key=lambda x: x["risk_score"], reverse=True)
    return result


@router.get("/stockout-forecast")
def stockout_forecast(db: Session = Depends(get_db)):
    """Parts with predicted stockout within 30 days."""
    parts = db.query(Part).all()
    result = []
    for p in parts:
        enriched = _enrich_part(p, db)
        sd = enriched.get("stockout_days")
        if sd is not None and sd <= 30:
            result.append(enriched)
    result.sort(key=lambda x: x.get("stockout_days", 999))
    return result


@router.get("/{part_number}")
def part_detail(part_number: str, db: Session = Depends(get_db)):
    part = db.query(Part).filter(Part.part_number == part_number).first()
    if not part:
        raise HTTPException(status_code=404, detail=f"Part {part_number} not found")

    enriched = _enrich_part(part, db)

    # Add all POs
    all_pos = db.query(PurchaseOrder).filter(
        PurchaseOrder.part_id == part.id
    ).order_by(PurchaseOrder.order_date.desc()).all()

    enriched["purchase_orders"] = [
        {
            "po_number": po.po_number,
            "status": po.status,
            "quantity_ordered": po.quantity_ordered,
            "unit_price": po.unit_price,
            "order_date": po.order_date.isoformat() if po.order_date else None,
            "expected_delivery_date": po.expected_delivery_date.isoformat() if po.expected_delivery_date else None,
            "delay_days": po.delay_days,
            "delay_reason": po.delay_reason,
        }
        for po in all_pos
    ]

    return enriched
