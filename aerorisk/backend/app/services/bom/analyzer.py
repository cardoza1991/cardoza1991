"""Orchestrate parse → match → enrich → roll up fleet impact."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from ...models.models import (
    Aircraft, BomComponent, BomUpload, MaintenanceEvent, Part,
)
from .enricher import CveIndex, enrich
from .parsers import ParsedComponent, parse


@dataclass
class AnalysisResult:
    upload_id: int
    component_count: int
    matched_part_count: int
    matched_supplier_count: int
    cve_count: int
    critical_cve_count: int
    max_cvss: float
    risk_score: float
    affected_aircraft_count: int
    affected_tails: list[str]


def analyze_bom_upload(
    db: Session,
    *,
    filename: str,
    raw: bytes | str,
    upload_name: Optional[str] = None,
    target_platform: Optional[str] = None,
    target_tail_number: Optional[str] = None,
) -> AnalysisResult:
    """Single entry point. Parses, persists components, enriches, scores."""
    fmt, components = parse(filename, raw)
    upload = BomUpload(
        name=upload_name or filename,
        source_format=fmt,
        target_platform=target_platform,
        target_tail_number=target_tail_number,
        component_count=len(components),
        created_at=datetime.utcnow(),
    )
    db.add(upload)
    db.flush()

    cve_index = CveIndex.build()

    matched_parts: set[int] = set()
    matched_suppliers: set[int] = set()
    total_cves = 0
    total_critical = 0
    max_cvss = 0.0
    component_rows: list[BomComponent] = []

    for pc in components:
        enriched = enrich(
            db,
            comp_name=pc.name,
            comp_vendor=pc.vendor,
            comp_version=pc.version,
            comp_pn=pc.part_number_raw,
            cve_index=cve_index,
        )
        if enriched.matched_part_id:
            matched_parts.add(enriched.matched_part_id)
        if enriched.matched_supplier_id:
            matched_suppliers.add(enriched.matched_supplier_id)
        total_cves += enriched.cve_count
        total_critical += enriched.critical_cve_count
        max_cvss = max(max_cvss, enriched.max_cvss)

        row = BomComponent(
            bom_upload_id=upload.id,
            name=pc.name,
            vendor=pc.vendor,
            version=pc.version,
            purl=pc.purl,
            cpe=pc.cpe,
            part_number_raw=pc.part_number_raw,
            matched_part_id=enriched.matched_part_id,
            matched_supplier_id=enriched.matched_supplier_id,
            match_confidence=enriched.match_confidence,
            matched_on=enriched.matched_on,
            cve_count=enriched.cve_count,
            critical_cve_count=enriched.critical_cve_count,
            max_cvss=enriched.max_cvss,
            kev_listed=enriched.kev_listed,
            cves_json=json.dumps([{
                "cve_id": c.cve_id, "cvss": c.cvss, "vendor": c.vendor,
                "product": c.product, "description": c.description[:300],
                "kev_listed": c.kev_listed,
            } for c in enriched.cves]),
        )
        db.add(row)
        component_rows.append(row)

    db.flush()

    # Fleet impact: aircraft that have a MaintenanceEvent for any matched Part.
    tails: set[str] = set()
    if matched_parts:
        rows = (
            db.query(Aircraft.tail_number)
            .join(MaintenanceEvent, MaintenanceEvent.aircraft_id == Aircraft.id)
            .filter(MaintenanceEvent.part_id.in_(matched_parts))
        )
        if target_platform:
            rows = rows.filter(Aircraft.platform == target_platform)
        if target_tail_number:
            rows = rows.filter(Aircraft.tail_number == target_tail_number)
        tails = {r[0] for r in rows.distinct().all()}

    # Aggregate risk score. Tunable, but the gist: KEV CVEs are worse than
    # plain CVEs, critical CVSS is worse than high, and fleet exposure
    # outweighs catalog exposure.
    kev_count = sum(1 for r in component_rows if r.kev_listed)
    risk = (
        min(40.0, total_critical * 6.0)
        + min(20.0, (total_cves - total_critical) * 1.0)
        + min(15.0, kev_count * 5.0)
        + min(15.0, len(tails) * 3.0)
        + min(10.0, len(matched_suppliers) * 1.0)
    )
    risk = min(100.0, risk)

    upload.matched_part_count = len(matched_parts)
    upload.matched_supplier_count = len(matched_suppliers)
    upload.cve_count = total_cves
    upload.critical_cve_count = total_critical
    upload.max_cvss = max_cvss
    upload.affected_aircraft_count = len(tails)
    upload.affected_tails = json.dumps(sorted(tails))
    upload.risk_score = round(risk, 1)
    db.commit()

    return AnalysisResult(
        upload_id=upload.id,
        component_count=upload.component_count,
        matched_part_count=upload.matched_part_count,
        matched_supplier_count=upload.matched_supplier_count,
        cve_count=upload.cve_count,
        critical_cve_count=upload.critical_cve_count,
        max_cvss=upload.max_cvss,
        risk_score=upload.risk_score,
        affected_aircraft_count=upload.affected_aircraft_count,
        affected_tails=sorted(tails),
    )
