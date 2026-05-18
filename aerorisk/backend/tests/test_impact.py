"""Operational Impact Engine tests.

These verify the headline numbers actually reconstruct from the data
(no fabrication) and that the simulator produces sane shapes.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.models.models import (
    Aircraft, Part, Supplier, Inventory, MaintenanceEvent,
)
from app.services.impact_engine import (
    simulate_supplier_failure, rank_operational_risks,
)


@pytest.fixture()
def mini_ops(db):
    """Tiny scenario: one supplier with one critical, single-source part used
    by two F-35As in upcoming maintenance events."""
    now = datetime.utcnow()
    s_bad = Supplier(name="Acme Sole-Source", country="US", reliability_score=0.6,
                     on_time_delivery_rate=0.7, defect_rate=0.04, single_source_parts_count=1,
                     is_approved=True, avg_lead_time_days=60)
    s_alt = Supplier(name="Phoenix Alt Source", country="US", reliability_score=0.93,
                     on_time_delivery_rate=0.95, defect_rate=0.01, single_source_parts_count=0,
                     is_approved=True, avg_lead_time_days=40)
    db.add_all([s_bad, s_alt]); db.flush()

    part = Part(part_number="LRU-CRIT-001", name="Flight Control LRU",
                supplier_id=s_bad.id, unit_cost=120_000.0, lead_time_days=60,
                lead_time_variance_days=20, is_mission_critical=True, is_single_source=True,
                category="Avionics")
    alt_part = Part(part_number="LRU-ALT-001", name="Alt LRU",
                    supplier_id=s_alt.id, unit_cost=130_000.0, lead_time_days=45,
                    lead_time_variance_days=10, is_mission_critical=True, is_single_source=False,
                    category="Avionics")
    db.add_all([part, alt_part]); db.flush()

    inv = Inventory(part_id=part.id, quantity_on_hand=2, quantity_on_order=0,
                    reorder_point=5, reorder_quantity=10, avg_monthly_consumption=3.0,
                    warehouse_location="DEPOT-A")
    db.add(inv); db.flush()

    ac1 = Aircraft(tail_number="AF-001", platform="F-35A", squadron="421FS",
                   base_location="Hill AFB", mission_status="FMC", flight_hours_total=850)
    ac2 = Aircraft(tail_number="AF-002", platform="F-35A", squadron="421FS",
                   base_location="Hill AFB", mission_status="PMC", flight_hours_total=920)
    db.add_all([ac1, ac2]); db.flush()

    db.add_all([
        MaintenanceEvent(aircraft_id=ac1.id, part_id=part.id, event_type="SCHEDULED",
                         description="200hr inspection", status="SCHEDULED",
                         scheduled_date=now + timedelta(days=30), technician="Sgt Doe",
                         requires_part=True, part_available=True, downtime_hours=8),
        MaintenanceEvent(aircraft_id=ac2.id, part_id=part.id, event_type="SCHEDULED",
                         description="LRU swap", status="SCHEDULED",
                         scheduled_date=now + timedelta(days=45), technician="Sgt Roe",
                         requires_part=True, part_available=False, downtime_hours=12),
    ])
    db.commit()
    return {"bad": s_bad, "alt": s_alt, "part": part, "aircraft": [ac1, ac2]}


def test_simulate_returns_affected_aircraft_and_platforms(db, mini_ops):
    impact = simulate_supplier_failure(db, mini_ops["bad"].id, horizon_days=90)
    assert impact is not None
    # 2 F-35As use the single-source part and have events within horizon
    assert impact.aircraft_affected == 2
    assert set(impact.tails) == {"AF-001", "AF-002"}
    assert impact.platforms == {"F-35A": 2}


def test_simulate_produces_nonzero_dollar_exposure(db, mini_ops):
    impact = simulate_supplier_failure(db, mini_ops["bad"].id, horizon_days=90)
    # Mission-critical single-source part + 2 grounded aircraft must produce >0 USD.
    assert impact.dollar_exposure_usd > 0
    # And the executive one-liner must mention dollars and alternates.
    assert "$" in impact.executive_one_liner
    assert "Phoenix Alt Source" in impact.executive_one_liner


def test_simulate_ranks_alternate_supplier(db, mini_ops):
    impact = simulate_supplier_failure(db, mini_ops["bad"].id, horizon_days=90)
    assert len(impact.alternates) >= 1
    top = impact.alternates[0]
    assert top.name == "Phoenix Alt Source"
    assert "Avionics" in top.overlap_categories


def test_severity_escalates_with_mission_critical_aircraft(db, mini_ops):
    impact = simulate_supplier_failure(db, mini_ops["bad"].id, horizon_days=90)
    # PMC aircraft + critical single-source part should not be LOW.
    assert impact.severity in ("CRITICAL", "HIGH", "MEDIUM")


def test_supplier_with_no_parts_returns_low_severity(db):
    """Edge case — supplier in catalog with zero parts has no impact."""
    s = Supplier(name="No Parts Co", country="US", reliability_score=0.9,
                 on_time_delivery_rate=0.9, defect_rate=0.01, is_approved=True)
    db.add(s); db.commit()
    impact = simulate_supplier_failure(db, s.id)
    assert impact is not None
    assert impact.aircraft_affected == 0
    assert impact.severity == "LOW"


def test_rank_operational_risks_returns_top_n(db, mini_ops):
    results = rank_operational_risks(db, horizon_days=90, top_n=3)
    # The bad supplier should be in the top results.
    names = [r["supplier_name"] for r in results]
    assert mini_ops["bad"].name in names


def test_unknown_supplier_returns_none(db):
    assert simulate_supplier_failure(db, supplier_id=99999) is None
