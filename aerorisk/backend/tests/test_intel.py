"""Intel pipeline + risk integration tests.

These exercise the offline fixture path — no live HTTP. They're the
contract for matcher behavior, dedupe, and risk score impact.
"""

from __future__ import annotations

from app.services.intel.matcher import build_supplier_index, best_match
from app.services.intel.pipeline import run_intel_cycle
from app.services.risk_engine import compute_supplier_risk
from app.models.models import SupplierIntelSignal


def test_matcher_hits_name_alias_and_keyword(db, seeded_suppliers):
    index = build_supplier_index(db)

    # Exact name
    m = best_match(["Honeywell Aerospace Tech"], index, threshold=86.0)
    assert m and m.confidence == 100.0
    assert m.matched_on.startswith("name:")

    # Vendor keyword only (CVE feed uses "Honeywell")
    m = best_match(["Honeywell"], index, threshold=86.0)
    assert m is not None
    honeywell_id = next(s.id for s in seeded_suppliers if s.name.startswith("Honeywell"))
    assert m.supplier_id == honeywell_id

    # Alias (sanction list refers to "Hydraulic Equipment LLC")
    m = best_match(["Hydraulic Equipment LLC"], index, threshold=86.0)
    assert m is not None
    moog_id = next(s.id for s in seeded_suppliers if s.name.startswith("Moog"))
    assert m.supplier_id == moog_id
    assert m.matched_on.startswith("alias:")


def test_matcher_rejects_unrelated_strings(db, seeded_suppliers):
    index = build_supplier_index(db)
    assert best_match(["Acme Bolts of Toledo"], index, threshold=86.0) is None
    assert best_match([""], index, threshold=86.0) is None


def test_intel_cycle_persists_and_dedupes(db, seeded_suppliers):
    result1 = run_intel_cycle(db)
    assert result1.matched > 0
    assert result1.new_signals > 0
    first_count = db.query(SupplierIntelSignal).count()
    assert first_count == result1.matched

    # Idempotent rerun — no new rows, all updates.
    result2 = run_intel_cycle(db)
    assert result2.new_signals == 0
    assert result2.updated_signals == result2.matched
    assert db.query(SupplierIntelSignal).count() == first_count


def test_critical_intel_lifts_supplier_risk_score(db, seeded_suppliers):
    honeywell = next(s for s in seeded_suppliers if s.name.startswith("Honeywell"))

    # Score before any intel.
    before = compute_supplier_risk(db, honeywell.id)
    assert before["intel_signal_count"] == 0

    # Pull intel. Fixture contains a CRITICAL Honeywell CVE.
    run_intel_cycle(db)

    after = compute_supplier_risk(db, honeywell.id)
    assert after["intel_signal_count"] >= 1
    assert after["intel_contribution"] > 0
    assert after["score"] >= before["score"]
    # Explanation should mention the intel signal.
    assert "Intel:" in after["explanation"]


def test_ticker_match_picks_up_stock_signal(db, seeded_suppliers):
    """Equity feed must hook into the matcher via supplier.ticker."""
    run_intel_cycle(db)
    moog = next(s for s in seeded_suppliers if s.ticker == "MOG-A")
    moog_signals = [s for s in moog.intel_signals if s.source == "EQUITY"]
    assert any(s.signal_type == "STOCK_DROP" for s in moog_signals), \
        "Moog had a >7% drop in the fixture; should produce a STOCK_DROP signal"
    # Numeric value should round-trip.
    drop = next(s for s in moog_signals if s.signal_type == "STOCK_DROP")
    assert drop.numeric_value is not None and drop.numeric_value <= -7.0
    assert drop.numeric_unit == "%"


def test_country_risk_fans_out_to_all_suppliers_in_country(db, seeded_suppliers):
    """COUNTRY_RISK signals must apply to every supplier in the matching country."""
    run_intel_cycle(db)
    safran = next(s for s in seeded_suppliers if s.hq_country_code == "FR")
    fr_geo = [s for s in safran.intel_signals if s.signal_type == "COUNTRY_RISK"]
    assert len(fr_geo) >= 1
    assert fr_geo[0].matched_on == "country_code:FR"


def test_categories_are_set_on_persisted_signals(db, seeded_suppliers):
    run_intel_cycle(db)
    cats = {s.category for s in db.query(SupplierIntelSignal).all()}
    # We expect at least these categories from the fixtures.
    assert "SANCTION" in cats
    assert "CYBER" in cats
    assert "FINANCIAL" in cats
    assert "GEOPOLITICAL" in cats


def test_sanction_match_creates_intel_alert_via_agent_cycle(db, seeded_suppliers):
    from app.services.agent_loop import run_agent_cycle
    from app.models.models import AgentRecommendation

    run_agent_cycle(db)

    intel_alerts = (
        db.query(AgentRecommendation)
        .filter(AgentRecommendation.recommendation_type == "INTEL_ALERT")
        .all()
    )
    assert len(intel_alerts) >= 1
    # At least one alert mentions Moog (the OFAC fixture targets a Moog alias).
    assert any("Moog" in (a.supplier_affected or "") for a in intel_alerts)
