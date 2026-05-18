from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..services.auth import Identity, current_identity
from ..services.impact_engine import (
    simulate_supplier_failure, rank_operational_risks,
    QUALIFICATION_DAYS_DEFAULT, GROUNDED_AIRCRAFT_COST_PER_DAY,
)
from ..services.executive_brief import generate_executive_brief
from ..services.scenarios import record_scenario

router = APIRouter(prefix="/api/impact", tags=["impact"])


class SimulateRequest(BaseModel):
    supplier_id: int
    horizon_days: int = 90
    qualification_days: int = QUALIFICATION_DAYS_DEFAULT
    grounded_cost_per_day: float = GROUNDED_AIRCRAFT_COST_PER_DAY


@router.post("/simulate")
def simulate(
    req: SimulateRequest,
    db: Session = Depends(get_db),
    identity: Identity = Depends(current_identity),
):
    """What-if: simulate the full operational ripple of supplier failure.

    Also persists the snapshot as an ImpactScenario so it gets a
    shareable URL and shows up in the autonomous timeline.
    """
    result = simulate_supplier_failure(
        db, req.supplier_id,
        horizon_days=req.horizon_days,
        qualification_days=req.qualification_days,
        grounded_cost_per_day=req.grounded_cost_per_day,
    )
    if result is None:
        raise HTTPException(status_code=404, detail=f"Supplier {req.supplier_id} not found")
    scenario = record_scenario(db, result, trigger="MANUAL", tenant_id=identity.tenant_id)
    db.commit()
    payload = result.as_dict()
    payload["scenario_id"] = scenario.id
    payload["share_token"] = scenario.share_token
    return payload


@router.get("/supplier/{supplier_id}")
def supplier_impact(
    supplier_id: int,
    horizon_days: int = Query(90, ge=7, le=365),
    db: Session = Depends(get_db),
):
    """Default-parameter impact report for a single supplier."""
    result = simulate_supplier_failure(db, supplier_id, horizon_days=horizon_days)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Supplier {supplier_id} not found")
    return result.as_dict()


@router.get("/top-risks")
def top_risks(
    horizon_days: int = Query(90, ge=7, le=365),
    top_n: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """Ranked top supplier-failure scenarios across the catalog."""
    return rank_operational_risks(db, horizon_days=horizon_days, top_n=top_n)


@router.get("/brief")
def executive_brief(
    horizon_days: int = Query(90, ge=7, le=365),
    db: Session = Depends(get_db),
):
    """One-page markdown executive brief. Pipes cleanly into a PDF renderer."""
    return {"markdown": generate_executive_brief(db, horizon_days=horizon_days)}
