"""Public endpoint that powers live numbers on the landing page.

Returns reconstructible counts pulled from the live DB, plus the share
token of the most recent CRITICAL scenario so the marketing page can
deep-link to a real sample report instead of a static screenshot.

Intentionally unauthenticated — these are aggregate counts that don't
expose any tenant-scoped data, and a landing page that requires a token
to render its hero stats defeats the point of a landing page.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.models import (
    Aircraft, BomComponent, BomUpload, ImpactScenario, Supplier,
    SupplierIntelSignal,
)

router = APIRouter(prefix="/api/landing", tags=["landing"])


@router.get("/stats")
def landing_stats(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    day_ago = now - timedelta(days=1)

    # Recent CRITICAL scenario gets featured as the "live sample report" CTA.
    latest_share_token = None
    latest = (
        db.query(ImpactScenario)
        .filter(ImpactScenario.share_token.isnot(None))
        .order_by(ImpactScenario.created_at.desc())
        .first()
    )
    if latest:
        latest_share_token = latest.share_token

    bom_cves = db.query(func.coalesce(func.sum(BomComponent.cve_count), 0)).scalar() or 0

    return {
        "aircraft_monitored": db.query(func.count(Aircraft.id)).scalar() or 0,
        "suppliers_tracked": db.query(func.count(Supplier.id)).scalar() or 0,
        "intel_signals_24h": db.query(func.count(SupplierIntelSignal.id))
                                .filter(SupplierIntelSignal.fetched_at >= day_ago).scalar() or 0,
        "intel_signals_total": db.query(func.count(SupplierIntelSignal.id)).scalar() or 0,
        "scenarios_generated": db.query(func.count(ImpactScenario.id)).scalar() or 0,
        "boms_analyzed": db.query(func.count(BomUpload.id)).scalar() or 0,
        "cves_cross_referenced": int(bom_cves),
        "latest_share_token": latest_share_token,
    }
