"""Autonomous trigger + scenario persistence + notification audit tests."""

from __future__ import annotations

import json
from datetime import datetime, timedelta

import pytest

from app.models.models import (
    Aircraft, Part, Supplier, Inventory, MaintenanceEvent,
    SupplierIntelSignal, ImpactScenario, NotificationLog,
)
from app.services.scenarios import autonomous_trigger_for_critical_signals, record_scenario
from app.services.impact_engine import simulate_supplier_failure
from app.services.agent_loop import run_agent_cycle


def _bootstrap_ops_with_intel(db):
    """Supplier with critical part + aircraft + active CRITICAL intel signal."""
    now = datetime.utcnow()
    s = Supplier(name="Acme Critical", country="US", reliability_score=0.6,
                 on_time_delivery_rate=0.7, defect_rate=0.04, single_source_parts_count=1,
                 is_approved=True, avg_lead_time_days=60,
                 aliases=json.dumps([]), keywords=json.dumps(["Acme"]),
                 hq_country_code="US")
    s_alt = Supplier(name="Phoenix Alt", country="US", reliability_score=0.93,
                     on_time_delivery_rate=0.95, defect_rate=0.01,
                     is_approved=True, avg_lead_time_days=40)
    db.add_all([s, s_alt]); db.flush()

    part = Part(part_number="LRU-001", name="Flight Control LRU",
                supplier_id=s.id, unit_cost=120_000.0, lead_time_days=60,
                lead_time_variance_days=20, is_mission_critical=True, is_single_source=True,
                category="Avionics")
    alt_part = Part(part_number="LRU-002", name="Alt LRU",
                    supplier_id=s_alt.id, unit_cost=130_000.0, lead_time_days=45,
                    lead_time_variance_days=10, is_mission_critical=True, is_single_source=False,
                    category="Avionics")
    db.add_all([part, alt_part]); db.flush()

    db.add(Inventory(part_id=part.id, quantity_on_hand=2, quantity_on_order=0,
                     reorder_point=5, reorder_quantity=10, avg_monthly_consumption=3.0))
    ac = Aircraft(tail_number="AF-100", platform="F-35A", squadron="421FS",
                  base_location="Hill AFB", mission_status="FMC", flight_hours_total=850)
    db.add(ac); db.flush()
    db.add(MaintenanceEvent(aircraft_id=ac.id, part_id=part.id, event_type="SCHEDULED",
                            description="200hr inspection", status="SCHEDULED",
                            scheduled_date=now + timedelta(days=30), technician="Sgt Doe",
                            requires_part=True, part_available=True, downtime_hours=8))

    sig = SupplierIntelSignal(
        supplier_id=s.id, source="OFAC", source_ref="SDN:TEST-1",
        category="SANCTION", signal_type="SANCTION", severity="CRITICAL",
        title="OFAC: Acme designated", body="Test signal",
        observed_at=now, fetched_at=now, is_active=True,
        match_confidence=100.0, matched_on="name:Acme Critical", score_weight=0.55,
    )
    db.add(sig); db.commit()
    return {"supplier": s, "signal": sig}


def test_autonomous_trigger_creates_scenario_and_notifies(db):
    ctx = _bootstrap_ops_with_intel(db)
    produced = autonomous_trigger_for_critical_signals(db, [ctx["signal"].id])
    assert len(produced) == 1
    sc = produced[0]
    assert sc.trigger == "AUTO_INTEL"
    assert sc.trigger_signal_id == ctx["signal"].id
    assert sc.supplier_id == ctx["supplier"].id
    assert sc.aircraft_affected >= 1
    assert sc.dollar_exposure_usd > 0
    assert sc.share_token and len(sc.share_token) >= 20
    # Snapshot is full ImpactResult JSON
    snap = json.loads(sc.snapshot_json)
    assert snap["supplier_name"] == ctx["supplier"].name
    assert "alternates" in snap
    # Console dispatcher always runs in test config
    logs = db.query(NotificationLog).filter(NotificationLog.scenario_id == sc.id).all()
    assert any(l.channel == "console" and l.status == "SENT" for l in logs)
    # Scenario marked notified
    assert sc.notified is True


def test_autonomous_trigger_is_idempotent_per_signal(db):
    ctx = _bootstrap_ops_with_intel(db)
    autonomous_trigger_for_critical_signals(db, [ctx["signal"].id])
    autonomous_trigger_for_critical_signals(db, [ctx["signal"].id])
    autonomous_trigger_for_critical_signals(db, [ctx["signal"].id])
    scenarios = db.query(ImpactScenario).filter(
        ImpactScenario.trigger_signal_id == ctx["signal"].id
    ).all()
    assert len(scenarios) == 1
    # Console log fires exactly once
    sends = db.query(NotificationLog).filter(
        NotificationLog.scenario_id == scenarios[0].id,
        NotificationLog.channel == "console",
        NotificationLog.status == "SENT",
    ).all()
    assert len(sends) == 1


def test_signal_with_no_operational_impact_skipped(db):
    """Critical signal hitting a supplier with no parts shouldn't fire a notification."""
    now = datetime.utcnow()
    s = Supplier(name="Lonely Supplier", country="US", reliability_score=0.9,
                 on_time_delivery_rate=0.9, defect_rate=0.01, is_approved=True)
    db.add(s); db.flush()
    sig = SupplierIntelSignal(
        supplier_id=s.id, source="OFAC", source_ref="SDN:LONELY",
        category="SANCTION", signal_type="SANCTION", severity="CRITICAL",
        title="OFAC: Lonely listed", observed_at=now, fetched_at=now,
        is_active=True, match_confidence=100.0, matched_on="name:Lonely Supplier",
        score_weight=0.55,
    )
    db.add(sig); db.commit()
    produced = autonomous_trigger_for_critical_signals(db, [sig.id])
    assert len(produced) == 0


def test_manual_scenario_persistence(db):
    ctx = _bootstrap_ops_with_intel(db)
    impact = simulate_supplier_failure(db, ctx["supplier"].id, horizon_days=90)
    sc = record_scenario(db, impact, trigger="MANUAL")
    db.commit()
    assert sc.trigger == "MANUAL"
    assert sc.trigger_signal_id is None
    assert sc.share_token
    # Manual records always create a NEW scenario (no signal dedup key).
    sc2 = record_scenario(db, impact, trigger="MANUAL")
    db.commit()
    assert sc.id != sc2.id


def test_full_agent_cycle_creates_auto_scenarios(db, seeded_suppliers):
    """End-to-end: seeded suppliers + parts/aircraft + agent cycle produces AUTO_INTEL scenarios.

    The conftest seeded_suppliers fixture only creates suppliers; we attach
    one mission-critical part + an aircraft + an upcoming maintenance event
    so that auto-impact actually has operational substance to attribute.
    Without this, intel signals correctly skip (no operational ripple).
    """
    now = datetime.utcnow()
    honeywell = next(s for s in seeded_suppliers if s.name.startswith("Honeywell"))
    part = Part(part_number="HON-CRIT-1", name="Honeywell critical LRU",
                supplier_id=honeywell.id, unit_cost=80_000.0, lead_time_days=45,
                lead_time_variance_days=10, is_mission_critical=True, is_single_source=True,
                category="Avionics")
    db.add(part); db.flush()
    db.add(Inventory(part_id=part.id, quantity_on_hand=1, quantity_on_order=0,
                     reorder_point=3, reorder_quantity=5, avg_monthly_consumption=2.0))
    ac = Aircraft(tail_number="AF-HON1", platform="F-35A", squadron="421FS",
                  base_location="Hill AFB", mission_status="FMC", flight_hours_total=500)
    db.add(ac); db.flush()
    db.add(MaintenanceEvent(aircraft_id=ac.id, part_id=part.id, event_type="SCHEDULED",
                            description="LRU swap", status="SCHEDULED",
                            scheduled_date=now + timedelta(days=20), technician="Sgt T",
                            requires_part=True, part_available=True, downtime_hours=6))
    db.commit()

    run_agent_cycle(db)
    auto = db.query(ImpactScenario).filter(ImpactScenario.trigger == "AUTO_INTEL").all()
    assert len(auto) >= 1, "expected at least one auto-triggered scenario from CRITICAL intel + operational impact"
    # And the share_token must be unique per scenario.
    tokens = {s.share_token for s in auto}
    assert len(tokens) == len(auto)
