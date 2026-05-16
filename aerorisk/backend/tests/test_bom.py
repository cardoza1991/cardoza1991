"""BOM → CVE → fleet impact tests."""

from __future__ import annotations

import json
from datetime import datetime, timedelta

import pytest

from app.models.models import (
    Aircraft, BomComponent, BomUpload, Inventory, MaintenanceEvent, Part, Supplier,
)
from app.services.bom import analyze_bom_upload
from app.services.bom.parsers import detect_format, parse, parse_csv, parse_cyclonedx


SAMPLE_CYCLONEDX = json.dumps({
    "bomFormat": "CycloneDX",
    "specVersion": "1.5",
    "components": [
        {
            "type": "operating-system",
            "name": "Experion PKS",
            "publisher": "Honeywell",
            "version": "510.2",
            "cpe": "cpe:2.3:o:honeywell:experion_pks:510.2:*:*:*:*:*:*:*",
            "properties": [{"name": "aerospace:part_number", "value": "HON-CRIT-1"}],
        },
        {
            "type": "firmware",
            "name": "ARINC 615A Data Loader",
            "publisher": "Collins Aerospace",
            "version": "4.1",
        },
        {
            "type": "library",
            "name": "OpenSSL",
            "publisher": "OpenSSL Project",
            "version": "1.0.2",
        },
    ],
})


SAMPLE_CSV = (
    "name,vendor,version,part_number\n"
    "Flight Control LRU,Acme,2.4,LRU-CRIT-001\n"
    "Experion PKS,Honeywell,510.2,\n"
    "ARINC 615A Data Loader,Collins Aerospace,4.1,\n"
)


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------

def test_detect_format_by_extension():
    assert detect_format("sbom.cdx.json", b"{}") == "CYCLONEDX"
    assert detect_format("bom.csv", b"a,b\n1,2\n") == "CSV"
    assert detect_format("noname", b"{}") == "CYCLONEDX"
    assert detect_format("noname", b"a,b\n1,2\n") == "CSV"


def test_parse_cyclonedx_pulls_part_number_from_properties():
    components = parse_cyclonedx(SAMPLE_CYCLONEDX)
    assert len(components) == 3
    pks = next(c for c in components if c.name == "Experion PKS")
    assert pks.vendor == "Honeywell"
    assert pks.version == "510.2"
    assert pks.cpe and pks.cpe.startswith("cpe:2.3:")
    assert pks.part_number_raw == "HON-CRIT-1"


def test_parse_csv_normalizes_headers():
    components = parse_csv(SAMPLE_CSV)
    assert len(components) == 3
    fc = next(c for c in components if c.name == "Flight Control LRU")
    assert fc.vendor == "Acme"
    assert fc.part_number_raw == "LRU-CRIT-001"


def test_parse_rejects_non_cyclonedx_json():
    with pytest.raises(ValueError):
        parse_cyclonedx(json.dumps({"foo": "bar"}))


# ---------------------------------------------------------------------------
# Analyzer / enrichment
# ---------------------------------------------------------------------------

@pytest.fixture()
def aerospace_catalog(db):
    """Seed a small catalog: 2 suppliers, 1 critical part, 2 aircraft, events."""
    now = datetime.utcnow()
    honeywell = Supplier(
        name="Honeywell Aerospace Tech", country="USA",
        reliability_score=0.87, on_time_delivery_rate=0.91, defect_rate=0.012,
        is_approved=True, avg_lead_time_days=35,
        aliases=json.dumps(["Honeywell International"]),
        keywords=json.dumps(["Honeywell", "Experion PKS"]),
        hq_country_code="US",
    )
    collins = Supplier(
        name="Collins Aerospace Solutions", country="USA",
        reliability_score=0.95, on_time_delivery_rate=0.94, defect_rate=0.008,
        is_approved=True, avg_lead_time_days=30,
        aliases=json.dumps(["Collins Aerospace"]),
        keywords=json.dumps(["Collins Aerospace", "ARINC 615A"]),
        hq_country_code="US",
    )
    db.add_all([honeywell, collins]); db.flush()

    p = Part(part_number="HON-CRIT-1", name="Experion PKS controller",
             supplier_id=honeywell.id, unit_cost=80_000.0, lead_time_days=45,
             lead_time_variance_days=10, is_mission_critical=True, is_single_source=True,
             category="Avionics")
    db.add(p); db.flush()
    db.add(Inventory(part_id=p.id, quantity_on_hand=1, quantity_on_order=0,
                     reorder_point=3, reorder_quantity=5, avg_monthly_consumption=2.0))
    ac = Aircraft(tail_number="AF-BOM1", platform="F-35A", squadron="421FS",
                  base_location="Hill AFB", mission_status="FMC", flight_hours_total=500)
    db.add(ac); db.flush()
    db.add(MaintenanceEvent(aircraft_id=ac.id, part_id=p.id, event_type="SCHEDULED",
                            description="LRU swap", status="SCHEDULED",
                            scheduled_date=now + timedelta(days=20), technician="Sgt T",
                            requires_part=True, part_available=True, downtime_hours=6))
    db.commit()
    return {"honeywell": honeywell, "collins": collins, "part": p, "aircraft": ac}


def test_analyze_cyclonedx_matches_parts_and_finds_cves(db, aerospace_catalog):
    result = analyze_bom_upload(
        db, filename="defense-sbom.cdx.json", raw=SAMPLE_CYCLONEDX,
        upload_name="F-35A avionics SBOM", target_platform="F-35A",
    )
    # We expect Honeywell PKS to match HON-CRIT-1 by exact part number, and
    # Collins to match by vendor (no part_number_raw on that line).
    assert result.matched_part_count >= 1
    assert result.matched_supplier_count >= 1
    # The CISA KEV fixture includes a Honeywell Experion PKS CVE — must hit.
    assert result.cve_count >= 1
    # Critical CVSS expected from the NVD / KEV fixtures.
    assert result.max_cvss >= 9.0
    # The mission-critical part hangs off an aircraft → fleet impact > 0
    assert result.affected_aircraft_count == 1
    assert result.affected_tails == ["AF-BOM1"]


def test_analyze_csv_produces_same_aircraft_link(db, aerospace_catalog):
    result = analyze_bom_upload(db, filename="bom.csv", raw=SAMPLE_CSV)
    # CSV variant includes LRU-CRIT-001 which isn't in our catalog, but the
    # Honeywell Experion line should still match by name + vendor.
    assert result.matched_part_count >= 1
    assert "AF-BOM1" in result.affected_tails


def test_unmatched_components_are_persisted_with_zero_match(db, aerospace_catalog):
    result = analyze_bom_upload(db, filename="bom.csv", raw=SAMPLE_CSV)
    rows = db.query(BomComponent).filter(BomComponent.bom_upload_id == result.upload_id).all()
    assert len(rows) == 3
    # At least one row should have a part match.
    assert any(r.matched_part_id is not None for r in rows)


def test_risk_score_is_zero_when_no_cves_and_no_matches(db):
    """Empty catalog + no CVE-relevant vendors → risk should be 0."""
    result = analyze_bom_upload(
        db, filename="bom.csv",
        raw="name,vendor,version\nLogitech MX Master,Logitech,3.0\n",
    )
    assert result.cve_count == 0
    assert result.matched_part_count == 0
    assert result.risk_score == 0.0


def test_upload_persists_with_aggregate_fields(db, aerospace_catalog):
    result = analyze_bom_upload(
        db, filename="sbom.json", raw=SAMPLE_CYCLONEDX,
        upload_name="My BOM", target_platform="F-35A",
    )
    u = db.query(BomUpload).filter(BomUpload.id == result.upload_id).first()
    assert u is not None
    assert u.source_format == "CYCLONEDX"
    assert u.target_platform == "F-35A"
    assert u.risk_score > 0
    assert json.loads(u.affected_tails) == ["AF-BOM1"]
