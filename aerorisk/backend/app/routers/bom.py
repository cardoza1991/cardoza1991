"""BOM upload + analysis endpoints."""

import json
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.models import BomComponent, BomUpload, Part, Supplier
from ..services.auth import Identity, current_identity
from ..services.bom import analyze_bom_upload

router = APIRouter(prefix="/api/bom", tags=["bom"])


def _serialize_upload(u: BomUpload, db: Session, include_components: bool = False) -> dict:
    out = {
        "id": u.id,
        "name": u.name,
        "source_format": u.source_format,
        "target_platform": u.target_platform,
        "target_tail_number": u.target_tail_number,
        "component_count": u.component_count,
        "matched_part_count": u.matched_part_count,
        "matched_supplier_count": u.matched_supplier_count,
        "cve_count": u.cve_count,
        "critical_cve_count": u.critical_cve_count,
        "max_cvss": u.max_cvss,
        "risk_score": u.risk_score,
        "affected_aircraft_count": u.affected_aircraft_count,
        "affected_tails": json.loads(u.affected_tails) if u.affected_tails else [],
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }
    if include_components:
        rows = db.query(BomComponent).filter(BomComponent.bom_upload_id == u.id).all()
        out["components"] = [_serialize_component(c, db) for c in rows]
    return out


def _serialize_component(c: BomComponent, db: Session) -> dict:
    part = db.query(Part).filter(Part.id == c.matched_part_id).first() if c.matched_part_id else None
    supplier = db.query(Supplier).filter(Supplier.id == c.matched_supplier_id).first() if c.matched_supplier_id else None
    return {
        "id": c.id,
        "name": c.name,
        "vendor": c.vendor,
        "version": c.version,
        "purl": c.purl,
        "cpe": c.cpe,
        "part_number_raw": c.part_number_raw,
        "matched_part_id": c.matched_part_id,
        "matched_part_number": part.part_number if part else None,
        "matched_supplier_id": c.matched_supplier_id,
        "matched_supplier_name": supplier.name if supplier else None,
        "match_confidence": c.match_confidence,
        "matched_on": c.matched_on,
        "cve_count": c.cve_count,
        "critical_cve_count": c.critical_cve_count,
        "max_cvss": c.max_cvss,
        "kev_listed": c.kev_listed,
        "cves": json.loads(c.cves_json) if c.cves_json else [],
    }


def _tenant_or_404(u: BomUpload, identity: Identity) -> None:
    """Legacy rows with NULL tenant_id stay visible to default tenant; cross-
    tenant accesses 404 to avoid information leaks."""
    if u.tenant_id is not None and u.tenant_id != identity.tenant_id:
        raise HTTPException(404, "BOM upload not found")


@router.post("/upload")
async def upload_bom(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    target_platform: Optional[str] = Form(None),
    target_tail_number: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    identity: Identity = Depends(current_identity),
):
    """Upload an SBOM (CycloneDX JSON or simple CSV). Returns the analysis."""
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "empty file")
    try:
        result = analyze_bom_upload(
            db,
            filename=file.filename or "upload",
            raw=raw,
            upload_name=name,
            target_platform=target_platform,
            target_tail_number=target_tail_number,
            tenant_id=identity.tenant_id,
        )
    except ValueError as e:
        raise HTTPException(400, f"could not parse SBOM: {e}")
    upload = db.query(BomUpload).filter(BomUpload.id == result.upload_id).first()
    return _serialize_upload(upload, db, include_components=True)


@router.get("/")
def list_uploads(
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    identity: Identity = Depends(current_identity),
):
    rows = (
        db.query(BomUpload)
        .filter((BomUpload.tenant_id == identity.tenant_id) | (BomUpload.tenant_id.is_(None)))
        .order_by(BomUpload.created_at.desc())
        .limit(limit)
        .all()
    )
    return [_serialize_upload(u, db) for u in rows]


@router.get("/{upload_id}")
def get_upload(
    upload_id: int,
    db: Session = Depends(get_db),
    identity: Identity = Depends(current_identity),
):
    u = db.query(BomUpload).filter(BomUpload.id == upload_id).first()
    if not u:
        raise HTTPException(404, "BOM upload not found")
    _tenant_or_404(u, identity)
    return _serialize_upload(u, db, include_components=True)


@router.delete("/{upload_id}")
def delete_upload(
    upload_id: int,
    db: Session = Depends(get_db),
    identity: Identity = Depends(current_identity),
):
    u = db.query(BomUpload).filter(BomUpload.id == upload_id).first()
    if not u:
        raise HTTPException(404, "BOM upload not found")
    _tenant_or_404(u, identity)
    db.delete(u)
    db.commit()
    return {"status": "deleted", "id": upload_id}
