"""Landing stats endpoint — drives the marketing page hero numbers."""

from datetime import datetime, timedelta

from app.models.models import (
    Aircraft, ImpactScenario, SupplierIntelSignal,
)
from app.routers.landing import landing_stats


def test_landing_stats_returns_counts_and_latest_share_token(db, seeded_suppliers):
    db.add(SupplierIntelSignal(
        supplier_id=seeded_suppliers[0].id, source="CISA_KEV",
        signal_type="CVE", severity="CRITICAL",
        title="Test KEV — Honeywell Experion",
        body="Active exploit",
        observed_at=datetime.utcnow() - timedelta(hours=2),
        fetched_at=datetime.utcnow() - timedelta(hours=2),
        is_active=True,
    ))
    db.add(Aircraft(
        tail_number="AF-L1", platform="F-35A", squadron="X",
        base_location="L", mission_status="FMC", flight_hours_total=10,
    ))
    db.add(ImpactScenario(
        supplier_id=seeded_suppliers[0].id, trigger="MANUAL", severity="HIGH",
        horizon_days=90, dollar_exposure_usd=1.0, aircraft_affected=0,
        production_delay_days=0, confidence=0.5,
        one_liner="test",
        snapshot_json="{}", share_token="abc123def456",
        created_at=datetime.utcnow(),
    ))
    db.commit()

    data = landing_stats(db=db)
    # Required shape — every key the frontend reads.
    for key in (
        "aircraft_monitored", "suppliers_tracked", "intel_signals_24h",
        "intel_signals_total", "scenarios_generated", "boms_analyzed",
        "cves_cross_referenced", "latest_share_token",
    ):
        assert key in data, f"missing key {key}"
    assert data["suppliers_tracked"] >= len(seeded_suppliers)
    assert data["intel_signals_24h"] >= 1
    assert data["intel_signals_total"] >= 1
    assert data["aircraft_monitored"] >= 1
    assert data["scenarios_generated"] >= 1
    assert data["latest_share_token"] == "abc123def456"


def test_landing_stats_handles_empty_db(db):
    """No data → zeros, not 500s. The marketing page must render cold."""
    data = landing_stats(db=db)
    assert data["aircraft_monitored"] == 0
    assert data["scenarios_generated"] == 0
    assert data["latest_share_token"] is None


def test_landing_stats_ignores_old_signals_in_24h_bucket(db, seeded_suppliers):
    """Anything older than 24h should not inflate the 'recent activity' number."""
    db.add(SupplierIntelSignal(
        supplier_id=seeded_suppliers[0].id, source="OFAC",
        signal_type="SANCTION", severity="HIGH",
        title="Old", body="x",
        observed_at=datetime.utcnow() - timedelta(days=3),
        fetched_at=datetime.utcnow() - timedelta(days=3),
        is_active=True,
    ))
    db.commit()
    data = landing_stats(db=db)
    assert data["intel_signals_24h"] == 0
    assert data["intel_signals_total"] >= 1
