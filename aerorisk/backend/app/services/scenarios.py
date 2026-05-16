"""Persisted impact scenarios.

A scenario is a frozen snapshot of an `ImpactResult` plus the trigger
that produced it. Snapshots exist so:

- The autonomous trigger has a durable audit trail.
- Shareable public URLs render the same numbers a sales rep saw, even
  if the live data shifts under them.
- Operators can compare last week's exposure to this week's without
  re-running simulations.
"""

from __future__ import annotations

import json
import secrets
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from ..config import settings
from ..models.models import ImpactScenario, Supplier, SupplierIntelSignal
from .impact_engine import ImpactResult, simulate_supplier_failure
from .notifications import Notification, dispatch


def _share_token() -> str:
    return secrets.token_urlsafe(24)


def record_scenario(
    db: Session,
    impact: ImpactResult,
    trigger: str,
    trigger_signal_id: Optional[int] = None,
) -> ImpactScenario:
    """Persist an ImpactResult and return the row. Idempotent per (signal, supplier)."""
    if trigger_signal_id is not None:
        existing = (
            db.query(ImpactScenario)
            .filter(
                ImpactScenario.trigger == trigger,
                ImpactScenario.trigger_signal_id == trigger_signal_id,
                ImpactScenario.supplier_id == impact.supplier_id,
            )
            .first()
        )
        if existing:
            return existing

    snap = impact.as_dict()
    scenario = ImpactScenario(
        supplier_id=impact.supplier_id,
        trigger=trigger,
        trigger_signal_id=trigger_signal_id,
        horizon_days=impact.horizon_days,
        severity=impact.severity,
        aircraft_affected=impact.aircraft_affected,
        production_delay_days=impact.production_delay_days,
        dollar_exposure_usd=impact.dollar_exposure_usd,
        confidence=impact.confidence,
        one_liner=impact.executive_one_liner,
        snapshot_json=json.dumps(snap, default=str),
        share_token=_share_token(),
        created_at=datetime.utcnow(),
    )
    db.add(scenario)
    db.flush()
    return scenario


def autonomous_trigger_for_critical_signals(
    db: Session,
    new_critical_signal_ids: list[int],
) -> list[ImpactScenario]:
    """The autonomous loop: new CRITICAL signal → impact sim → scenario → notify.

    Dedupes by signal id so re-running an agent cycle doesn't fire repeat
    notifications for the same event.
    """
    if not settings.autonomous_impact_on_critical or not new_critical_signal_ids:
        return []

    produced: list[ImpactScenario] = []
    for sig_id in new_critical_signal_ids:
        sig = db.query(SupplierIntelSignal).filter(SupplierIntelSignal.id == sig_id).first()
        if not sig or not sig.supplier_id:
            continue

        impact = simulate_supplier_failure(
            db, sig.supplier_id, horizon_days=settings.autonomous_horizon_days,
        )
        if impact is None:
            continue
        # Skip if the supplier has no parts / no operational impact — don't
        # flood the operator with empty scenarios.
        if impact.aircraft_affected == 0 and impact.dollar_exposure_usd == 0:
            continue

        scenario = record_scenario(db, impact, trigger="AUTO_INTEL", trigger_signal_id=sig_id)
        if scenario.notified:
            continue  # already dispatched on a prior cycle

        share_url = f"{settings.public_base_url.rstrip('/')}/share/{scenario.share_token}" \
            if settings.public_base_url else None
        supplier = db.query(Supplier).filter(Supplier.id == sig.supplier_id).first()
        title = (
            f"Auto-impact: {supplier.name if supplier else 'Supplier'} — "
            f"{impact.severity} (${impact.dollar_exposure_usd/1_000_000:.1f}M exposure)"
        )
        body = (
            f"Triggered by intel signal **{sig.source} {sig.source_ref}** — {sig.title}\n\n"
            f"> {impact.executive_one_liner}\n\n"
            f"Aircraft affected: **{impact.aircraft_affected}** · "
            f"production delay: **{impact.production_delay_days}d** · "
            f"confidence: **{impact.confidence*100:.0f}%**"
        )
        dispatch(db, Notification(
            title=title,
            severity=impact.severity,
            one_liner=impact.executive_one_liner,
            body_md=body,
            scenario_id=scenario.id,
            signal_id=sig_id,
            share_url=share_url,
        ))
        produced.append(scenario)

    db.commit()
    return produced
