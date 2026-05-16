"""Intel feed adapters.

Each feed returns a list of `IntelCandidate` records — provenance-tagged,
classified, but NOT yet matched to a supplier. The pipeline runs them
through the matcher and persists matches.

Live HTTP is gated behind `settings.intel_live_feeds`. When disabled, or
when the live fetch fails (timeout, non-200, parse error), the feed falls
back to its bundled fixture so the demo always has signals to show.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

import httpx

from ...config import settings

log = logging.getLogger(__name__)

FIXTURE_DIR = Path(__file__).parent / "fixtures"

# Severity → score weight (0..1). The risk engine caps the aggregate at 1.0.
SEVERITY_WEIGHT = {
    "CRITICAL": 0.55,
    "HIGH": 0.35,
    "MEDIUM": 0.20,
    "LOW": 0.08,
}


@dataclass
class IntelCandidate:
    """A normalized intel observation before supplier matching."""
    source: str
    source_ref: str          # stable id used for dedupe
    signal_type: str         # SANCTION | CVE | ADVISORY | CYBER_INCIDENT
    severity: str            # CRITICAL | HIGH | MEDIUM | LOW
    title: str
    body: str
    link: Optional[str]
    observed_at: datetime
    # Candidate strings the matcher will compare to supplier handles. Always
    # include every name/alias/vendor the source publishes — broader = better recall.
    match_strings: list[str] = field(default_factory=list)

    @property
    def score_weight(self) -> float:
        return SEVERITY_WEIGHT.get(self.severity, 0.10)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_fixture(name: str) -> dict:
    path = FIXTURE_DIR / name
    with path.open() as f:
        return json.load(f)


def _try_fetch(url: str) -> Optional[dict]:
    """Attempt a live JSON fetch. Returns None on any failure (caller falls back)."""
    if not settings.intel_live_feeds:
        return None
    try:
        with httpx.Client(timeout=settings.intel_http_timeout_seconds, follow_redirects=True) as client:
            r = client.get(url, headers={"User-Agent": "AeroRisk-Intel/1.0"})
            r.raise_for_status()
            return r.json()
    except (httpx.HTTPError, json.JSONDecodeError) as e:
        log.warning("intel feed live fetch failed for %s: %s — falling back to fixture", url, e)
        return None


def _parse_dt(value: str) -> datetime:
    if not value:
        return datetime.utcnow()
    v = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(v).replace(tzinfo=None)
    except ValueError:
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d")
        except ValueError:
            return datetime.utcnow()


# ---------------------------------------------------------------------------
# Feed implementations
# ---------------------------------------------------------------------------

def fetch_ofac_sanctions() -> Iterable[IntelCandidate]:
    """OFAC SDN list. Synthetic schema; real list uses a different format."""
    data = _try_fetch("https://www.treasury.gov/ofac/downloads/sdn.json") or _load_fixture("ofac_sdn.json")
    for entry in data.get("entries", []):
        match_strings = [entry.get("name", "")] + list(entry.get("aliases", []))
        yield IntelCandidate(
            source="OFAC",
            source_ref=f"SDN:{entry['id']}",
            signal_type="SANCTION",
            severity="CRITICAL",  # any sanctions hit is operationally CRITICAL
            title=f"OFAC SDN listing: {entry.get('name', 'unknown entity')}",
            body=(
                f"Program: {entry.get('program', 'unknown')}. "
                f"Country: {entry.get('country', 'unknown')}. "
                f"{entry.get('summary', '')}"
            ),
            link=entry.get("link"),
            observed_at=_parse_dt(entry.get("listed_on", "")),
            match_strings=[m for m in match_strings if m],
        )


def fetch_cisa_kev() -> Iterable[IntelCandidate]:
    """CISA Known Exploited Vulnerabilities catalog."""
    data = (
        _try_fetch("https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json")
        or _load_fixture("cisa_kev.json")
    )
    for v in data.get("vulnerabilities", []):
        ransomware = (v.get("knownRansomwareCampaignUse") or "").lower() == "known"
        severity = "CRITICAL" if ransomware else "HIGH"
        vendor = v.get("vendorProject", "")
        product = v.get("product", "")
        yield IntelCandidate(
            source="CISA_KEV",
            source_ref=f"KEV:{v['cveID']}",
            signal_type="CVE",
            severity=severity,
            title=f"{v['cveID']}: {v.get('vulnerabilityName', vendor + ' ' + product)}",
            body=(
                f"{v.get('shortDescription', '')} "
                f"Required action: {v.get('requiredAction', 'see CISA catalog')}. "
                f"Due: {v.get('dueDate', 'n/a')}."
                + (" Known ransomware campaign use." if ransomware else "")
            ),
            link=v.get("notes"),
            observed_at=_parse_dt(v.get("dateAdded", "")),
            match_strings=[s for s in (vendor, product, f"{vendor} {product}") if s],
        )


def fetch_cisa_ics_advisories() -> Iterable[IntelCandidate]:
    """CISA ICS-CERT advisories — high-CVSS items affecting industrial vendors."""
    data = _try_fetch("https://www.cisa.gov/cybersecurity-advisories/ics-advisories.json") \
        or _load_fixture("cisa_ics_advisories.json")
    for a in data.get("advisories", []):
        cvss = float(a.get("cvss_v3") or 0.0)
        if cvss >= 9.0:
            severity = "CRITICAL"
        elif cvss >= 7.0:
            severity = "HIGH"
        elif cvss >= 4.0:
            severity = "MEDIUM"
        else:
            severity = "LOW"

        vendors = a.get("vendors", []) or []
        products = a.get("products", []) or []
        match_strings = list(vendors) + list(products) + [
            f"{v} {p}" for v in vendors for p in products
        ]

        yield IntelCandidate(
            source="CISA_ICS",
            source_ref=f"ADV:{a['id']}",
            signal_type="ADVISORY",
            severity=severity,
            title=f"{a['id']}: {a.get('title', 'ICS advisory')}",
            body=f"CVSSv3 {cvss}. {a.get('summary', '')}",
            link=a.get("link"),
            observed_at=_parse_dt(a.get("released", "")),
            match_strings=[s for s in match_strings if s],
        )


ALL_FEEDS = [
    ("OFAC", fetch_ofac_sanctions),
    ("CISA_KEV", fetch_cisa_kev),
    ("CISA_ICS", fetch_cisa_ics_advisories),
]
