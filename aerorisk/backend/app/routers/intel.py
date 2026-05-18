from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..models.models import Supplier, SupplierIntelSignal
from ..schemas.schemas import IntelCycleSummary, SupplierIntelSignalOut
from ..services.intel import run_intel_cycle

router = APIRouter(prefix="/api/intel", tags=["intel"])


def _to_out(sig: SupplierIntelSignal) -> dict:
    return {
        "id": sig.id,
        "supplier_id": sig.supplier_id,
        "supplier_name": sig.supplier.name if sig.supplier else None,
        "source": sig.source,
        "source_ref": sig.source_ref,
        "category": sig.category,
        "signal_type": sig.signal_type,
        "severity": sig.severity,
        "title": sig.title,
        "body": sig.body,
        "link": sig.link,
        "observed_at": sig.observed_at.isoformat() if sig.observed_at else None,
        "fetched_at": sig.fetched_at.isoformat() if sig.fetched_at else None,
        "expires_at": sig.expires_at.isoformat() if sig.expires_at else None,
        "is_active": sig.is_active,
        "match_confidence": sig.match_confidence,
        "matched_on": sig.matched_on,
        "score_weight": sig.score_weight,
        "numeric_value": sig.numeric_value,
        "numeric_unit": sig.numeric_unit,
    }


@router.get("/signals")
def list_signals(
    severity: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    supplier_id: Optional[int] = Query(None),
    active_only: bool = Query(True),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
):
    """Recent intel signals across all suppliers, newest first."""
    q = db.query(SupplierIntelSignal)
    if severity:
        q = q.filter(SupplierIntelSignal.severity == severity.upper())
    if source:
        q = q.filter(SupplierIntelSignal.source == source.upper())
    if category:
        q = q.filter(SupplierIntelSignal.category == category.upper())
    if supplier_id is not None:
        q = q.filter(SupplierIntelSignal.supplier_id == supplier_id)
    if active_only:
        q = q.filter(SupplierIntelSignal.is_active == True)  # noqa: E712
    signals = q.order_by(SupplierIntelSignal.observed_at.desc()).limit(limit).all()
    return [_to_out(s) for s in signals]


@router.get("/feeds")
def list_feeds():
    """Static catalog of feeds the intel agent knows how to pull."""
    from ..services.intel.feeds import ALL_FEEDS
    return [{"id": name, "function": fn.__name__} for name, fn in ALL_FEEDS]


@router.post("/refresh", response_model=IntelCycleSummary)
def refresh(db: Session = Depends(get_db)):
    """Force a single intel pull. Idempotent — safe to call repeatedly."""
    result = run_intel_cycle(db)
    return result.as_dict()


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    """Counts for the SupplierRisk page header."""
    from sqlalchemy import func as sql_func
    base = db.query(SupplierIntelSignal).filter(SupplierIntelSignal.is_active == True)  # noqa: E712
    total = base.count()
    critical = base.filter(SupplierIntelSignal.severity == "CRITICAL").count()
    high = base.filter(SupplierIntelSignal.severity == "HIGH").count()
    sanctioned_suppliers = (
        db.query(SupplierIntelSignal.supplier_id)
        .filter(SupplierIntelSignal.is_active == True,                                  # noqa: E712
                SupplierIntelSignal.signal_type == "SANCTION",
                SupplierIntelSignal.supplier_id.isnot(None))
        .distinct().count()
    )

    # by_category, by_source counts for the UI filter chips.
    cat_rows = (
        db.query(SupplierIntelSignal.category, sql_func.count(SupplierIntelSignal.id))
        .filter(SupplierIntelSignal.is_active == True)                                  # noqa: E712
        .group_by(SupplierIntelSignal.category).all()
    )
    src_rows = (
        db.query(SupplierIntelSignal.source, sql_func.count(SupplierIntelSignal.id))
        .filter(SupplierIntelSignal.is_active == True)                                  # noqa: E712
        .group_by(SupplierIntelSignal.source).all()
    )
    return {
        "total_active": total,
        "critical": critical,
        "high": high,
        "sanctioned_suppliers": sanctioned_suppliers,
        "by_category": {k or "UNCATEGORIZED": v for k, v in cat_rows},
        "by_source": {k or "UNKNOWN": v for k, v in src_rows},
    }
