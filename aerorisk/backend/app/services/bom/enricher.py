"""Enrich BOM components with catalog matches + CVE data.

Catalog match cascade (highest confidence first):
1. exact part_number match against Part.part_number
2. fuzzy vendor+product match against Supplier.keywords + Part.name
3. vendor-only fallback (lower confidence)

CVE enrichment uses the same fixtures the supplier intel agent ships
with: NVD bulk catalog + CISA KEV. Live mode (settings.intel_live_feeds)
can hit the real NVD API per component, but that path is opt-in due to
rate limits.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional

from rapidfuzz import fuzz
from sqlalchemy.orm import Session

from ...config import settings
from ...models.models import Part, Supplier
from ..intel.feeds import _load_fixture, _try_fetch    # reuse the intel feed plumbing


@dataclass
class CveHit:
    cve_id: str
    cvss: float
    vendor: str
    product: str
    description: str
    kev_listed: bool = False


@dataclass
class EnrichedComponent:
    matched_part_id: Optional[int] = None
    matched_supplier_id: Optional[int] = None
    match_confidence: float = 0.0
    matched_on: Optional[str] = None
    cves: list[CveHit] = field(default_factory=list)

    @property
    def cve_count(self) -> int: return len(self.cves)
    @property
    def critical_cve_count(self) -> int: return sum(1 for c in self.cves if c.cvss >= 9.0)
    @property
    def max_cvss(self) -> float: return max((c.cvss for c in self.cves), default=0.0)
    @property
    def kev_listed(self) -> bool: return any(c.kev_listed for c in self.cves)


# ---------------------------------------------------------------------------
# CVE database
# ---------------------------------------------------------------------------

class CveIndex:
    """In-memory CVE store for one BOM analysis run.

    Built from the NVD + KEV fixtures (or live data when enabled). Indexed
    by lowercased vendor and product so component lookups are O(1).
    """
    def __init__(self):
        self.by_vendor: dict[str, list[CveHit]] = {}
        self.by_product: dict[str, list[CveHit]] = {}
        self._kev_ids: set[str] = set()

    @classmethod
    def build(cls) -> "CveIndex":
        idx = cls()
        kev = _try_fetch("https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json") \
            or _load_fixture("cisa_kev.json")
        nvd = _try_fetch("https://services.nvd.nist.gov/rest/json/cves/2.0?resultsPerPage=100") \
            or _load_fixture("nvd_cves.json")
        # CISA ICS advisories include CVSS scores; treat them as third CVE source
        # for richer enrichment (most aerospace OT CVEs live here, not NVD).
        ics = _try_fetch("https://www.cisa.gov/cybersecurity-advisories/ics-advisories.json") \
            or _load_fixture("cisa_ics_advisories.json")

        # Pass 1 — collect KEV CVE IDs (used to flag entries even if their
        # actual CVSS comes from NVD/ICS).
        for v in kev.get("vulnerabilities", []) or []:
            if v.get("cveID"):
                idx._kev_ids.add(v["cveID"])

        # Pass 2 — ingest in order of CVSS-source quality (NVD > ICS > KEV
        # baseline). _ingest dedupes by cve_id within each bucket and keeps
        # whichever entry has the higher CVSS.
        for v in nvd.get("vulnerabilities", []) or []:
            idx._ingest(
                cve_id=v.get("cveID", ""),
                cvss=float(v.get("cvss_v3") or 0.0),
                vendor=v.get("vendor", ""),
                product=v.get("product", ""),
                description=v.get("description", ""),
            )
        # ICS advisories carry CVSSv3 and explicit vendor/product arrays.
        for a in ics.get("advisories", []) or []:
            cvss = float(a.get("cvss_v3") or 0.0)
            adv_id = a.get("id", "")
            for vendor in a.get("vendors", []) or []:
                for product in (a.get("products", []) or [vendor]):
                    idx._ingest(
                        cve_id=adv_id, cvss=cvss, vendor=vendor, product=product,
                        description=a.get("summary", ""),
                    )
        for v in kev.get("vulnerabilities", []) or []:
            idx._ingest(
                cve_id=v.get("cveID", ""),
                cvss=8.0,  # baseline; overridden by NVD/ICS if same id seen there
                vendor=v.get("vendorProject", ""),
                product=v.get("product", ""),
                description=v.get("shortDescription", ""),
            )
        return idx

    def _ingest(self, cve_id, cvss, vendor, product, description):
        if not cve_id or not (vendor or product):
            return
        hit = CveHit(
            cve_id=cve_id, cvss=cvss, vendor=vendor, product=product,
            description=description, kev_listed=cve_id in self._kev_ids,
        )

        def _upsert(bucket: dict[str, list[CveHit]], key: str):
            existing = bucket.setdefault(key.lower(), [])
            for i, h in enumerate(existing):
                if h.cve_id == cve_id:
                    # keep whichever has the higher CVSS, but always propagate
                    # KEV flag and the longer description.
                    if hit.cvss > h.cvss:
                        h.cvss = hit.cvss
                    if hit.kev_listed:
                        h.kev_listed = True
                    if hit.description and len(hit.description) > len(h.description or ""):
                        h.description = hit.description
                    return
            existing.append(hit)

        if vendor:
            _upsert(self.by_vendor, vendor)
        if product:
            _upsert(self.by_product, product)

    def lookup(self, vendor: Optional[str], product: Optional[str]) -> list[CveHit]:
        """Return CVEs whose (vendor, product) match the inputs. Dedupes by cve_id."""
        out: dict[str, CveHit] = {}
        v_lc = (vendor or "").lower().strip()
        p_lc = (product or "").lower().strip()
        if v_lc:
            for hit in self.by_vendor.get(v_lc, []):
                # require product overlap when both sides have a product
                if hit.product and p_lc and p_lc not in hit.product.lower() and hit.product.lower() not in p_lc:
                    continue
                out[hit.cve_id] = hit
        if p_lc:
            for hit in self.by_product.get(p_lc, []):
                # require vendor overlap when both sides have a vendor
                if hit.vendor and v_lc and v_lc not in hit.vendor.lower() and hit.vendor.lower() not in v_lc:
                    continue
                out[hit.cve_id] = hit
        return list(out.values())


# ---------------------------------------------------------------------------
# Matching against the Part / Supplier catalog
# ---------------------------------------------------------------------------

def _match_part(db: Session, comp_name: str, comp_vendor: Optional[str],
                comp_pn: Optional[str]) -> tuple[Optional[Part], float, Optional[str]]:
    """Best-effort match of a BOM line to a catalog Part."""
    if comp_pn:
        p = db.query(Part).filter(Part.part_number == comp_pn).first()
        if p:
            return p, 100.0, "part_number"

    # Fuzzy on Part.name. Cap candidates to avoid scanning the whole table for
    # nothing on every component.
    parts = db.query(Part).all()
    best: Optional[Part] = None
    best_score = 0.0
    for p in parts:
        score = fuzz.token_set_ratio(comp_name, p.name)
        # bonus when the BOM vendor matches the part's supplier keywords
        if comp_vendor and p.supplier and p.supplier.keywords:
            try:
                kws = json.loads(p.supplier.keywords)
                if any(comp_vendor.lower() in (k or "").lower() or (k or "").lower() in comp_vendor.lower() for k in kws):
                    score = min(100.0, score + 8.0)
            except (json.JSONDecodeError, AttributeError):
                pass
        if score > best_score:
            best, best_score = p, score
    if best and best_score >= 78.0:   # Looser than the intel matcher; BOM names are noisier.
        return best, best_score, "name"
    return None, 0.0, None


def _match_supplier(db: Session, comp_vendor: Optional[str]) -> tuple[Optional[Supplier], float]:
    if not comp_vendor:
        return None, 0.0
    suppliers = db.query(Supplier).all()
    best = None
    best_score = 0.0
    for s in suppliers:
        candidates = [s.name]
        if s.aliases:
            try:
                candidates.extend(json.loads(s.aliases))
            except json.JSONDecodeError:
                pass
        if s.keywords:
            try:
                candidates.extend(json.loads(s.keywords))
            except json.JSONDecodeError:
                pass
        score = max((fuzz.token_set_ratio(comp_vendor, c) for c in candidates if c), default=0)
        if score > best_score:
            best, best_score = s, score
    if best and best_score >= 82.0:
        return best, float(best_score)
    return None, 0.0


def enrich(db: Session, comp_name: str, comp_vendor: Optional[str],
           comp_version: Optional[str], comp_pn: Optional[str],
           cve_index: CveIndex) -> EnrichedComponent:
    """Match against catalog and enrich with CVE data."""
    out = EnrichedComponent()

    part, conf, on = _match_part(db, comp_name, comp_vendor, comp_pn)
    if part:
        out.matched_part_id = part.id
        out.matched_supplier_id = part.supplier_id
        out.match_confidence = conf
        out.matched_on = on
    else:
        supplier, sc = _match_supplier(db, comp_vendor)
        if supplier:
            out.matched_supplier_id = supplier.id
            out.match_confidence = sc
            out.matched_on = "vendor"

    out.cves = cve_index.lookup(comp_vendor, comp_name)
    return out
