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
    signal_type: str         # SANCTION | CVE | ADVISORY | STOCK_DROP | 8K_FILING | COUNTRY_RISK | DISASTER | NEWS
    category: str            # SANCTION | CYBER | FINANCIAL | NEWS | GEOPOLITICAL | DISASTER
    severity: str            # CRITICAL | HIGH | MEDIUM | LOW
    title: str
    body: str
    link: Optional[str]
    observed_at: datetime
    # Candidate strings the matcher will compare to supplier handles. Always
    # include every name/alias/vendor the source publishes — broader = better recall.
    match_strings: list[str] = field(default_factory=list)
    numeric_value: Optional[float] = None
    numeric_unit: Optional[str] = None
    # Optional direct supplier targeting (bypasses fuzzy match when set, e.g.
    # ticker- or CIK-keyed feeds where we already know the supplier id).
    direct_supplier_id: Optional[int] = None

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
    """OFAC SDN list. Live: https://www.treasury.gov/ofac/downloads/sdn.csv (real format is XML/CSV)."""
    data = _try_fetch("https://www.treasury.gov/ofac/downloads/sdn.json") or _load_fixture("ofac_sdn.json")
    for entry in data.get("entries", []):
        match_strings = [entry.get("name", "")] + list(entry.get("aliases", []))
        yield IntelCandidate(
            source="OFAC",
            source_ref=f"SDN:{entry['id']}",
            signal_type="SANCTION",
            category="SANCTION",
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


def fetch_extended_sanctions() -> Iterable[IntelCandidate]:
    """Consolidated EU/UK/BIS Entity List sanctions.

    Live endpoints:
    - EU consolidated: https://webgate.ec.europa.eu/fsd/fsf/public/files/jsonFullSanctionsList_1_1/content
    - UK OFSI:         https://ofsistorage.blob.core.windows.net/publishlive/2022format/ConList.json
    - BIS Entity List: https://www.bis.doc.gov/dpl/dpl.txt (BIS publishes as a denied persons text file)
    """
    data = _try_fetch("https://webgate.ec.europa.eu/fsd/fsf/public/files/jsonFullSanctionsList_1_1/content") \
        or _load_fixture("extended_sanctions.json")
    for e in data.get("entries", []):
        regime = e.get("regime", "")
        program = e.get("program", "")
        severity = "CRITICAL" if regime in ("BIS_ENTITY_LIST", "EU", "UK") else "HIGH"
        match_strings = [e.get("name", "")] + list(e.get("aliases", []))
        yield IntelCandidate(
            source=regime or "EXT_SANCTIONS",
            source_ref=f"{regime}:{e['id']}",
            signal_type="SANCTION",
            category="SANCTION",
            severity=severity,
            title=f"{regime} sanctions listing: {e.get('name', '?')}",
            body=f"Program: {program}. Country: {e.get('country','?')}. {e.get('summary','')}",
            link=e.get("link"),
            observed_at=_parse_dt(e.get("listed_on", "")),
            match_strings=[m for m in match_strings if m],
        )


def fetch_cisa_kev() -> Iterable[IntelCandidate]:
    """CISA Known Exploited Vulnerabilities catalog.

    Live: https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json
    """
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
            category="CYBER",
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


def fetch_nvd_cves() -> Iterable[IntelCandidate]:
    """NVD CVE catalog — broader than CISA KEV (includes non-exploited CVEs).

    Live: https://services.nvd.nist.gov/rest/json/cves/2.0?resultsPerPage=200&pubStartDate=...
    Real NVD API requires pagination and date windows; the fetcher here trims
    to high-CVSS recent CVEs to keep signal density meaningful.
    """
    data = _try_fetch("https://services.nvd.nist.gov/rest/json/cves/2.0?resultsPerPage=100") \
        or _load_fixture("nvd_cves.json")
    for v in data.get("vulnerabilities", []):
        cve_id = v.get("cveID")
        cvss = float(v.get("cvss_v3") or 0.0)
        vendor = v.get("vendor", "")
        product = v.get("product", "")
        if cvss >= 9.0:
            severity = "CRITICAL"
        elif cvss >= 7.0:
            severity = "HIGH"
        elif cvss >= 4.0:
            severity = "MEDIUM"
        else:
            severity = "LOW"
        yield IntelCandidate(
            source="NVD",
            source_ref=f"NVD:{cve_id}",
            signal_type="CVE",
            category="CYBER",
            severity=severity,
            title=f"{cve_id}: {vendor} {product} ({v.get('cwe','')})",
            body=v.get("description", ""),
            link=f"https://nvd.nist.gov/vuln/detail/{cve_id}",
            observed_at=_parse_dt(v.get("published", "")),
            match_strings=[s for s in (vendor, product, f"{vendor} {product}") if s],
            numeric_value=cvss,
            numeric_unit="CVSS",
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
            category="CYBER",
            severity=severity,
            title=f"{a['id']}: {a.get('title', 'ICS advisory')}",
            body=f"CVSSv3 {cvss}. {a.get('summary', '')}",
            link=a.get("link"),
            observed_at=_parse_dt(a.get("released", "")),
            match_strings=[s for s in match_strings if s],
            numeric_value=cvss,
            numeric_unit="CVSS",
        )


# ---------------------------------------------------------------------------
# Financial feeds
# ---------------------------------------------------------------------------

def fetch_stock_indicators() -> Iterable[IntelCandidate]:
    """Equity price signals for public suppliers.

    Live options (need API keys):
    - Alpha Vantage:  https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=RTX
    - Polygon.io:     https://api.polygon.io/v2/aggs/ticker/RTX/prev
    - Yahoo Finance (unofficial): https://query1.finance.yahoo.com/v7/finance/quote?symbols=RTX,LMT,BA

    Severity heuristics:
    - Daily move <= -7%  → CRITICAL (panic move / breaking news)
    - Daily move <= -4%  → HIGH
    - Daily move <= -2%  → MEDIUM
    - 52-week low broken → HIGH (additional signal, emitted separately)
    """
    data = _try_fetch("https://query1.finance.yahoo.com/v7/finance/quote?symbols=RTX,LMT,BA,GE,HON,TDG,SAF.PA,MOG-A") \
        or _load_fixture("stock_indicators.json")
    for q in data.get("quotes", []):
        ticker = q.get("symbol", "").upper()
        pct = float(q.get("regularMarketChangePercent") or 0.0)
        price = float(q.get("regularMarketPrice") or 0.0)
        low52 = float(q.get("fiftyTwoWeekLow") or 0.0)
        is_52w_low = low52 > 0 and price <= low52 * 1.01
        observed = _parse_dt(q.get("date", ""))

        # Daily move signal
        if pct <= -7.0:
            severity = "CRITICAL"
        elif pct <= -4.0:
            severity = "HIGH"
        elif pct <= -2.0:
            severity = "MEDIUM"
        else:
            severity = "LOW"
        if pct <= -2.0:
            yield IntelCandidate(
                source="EQUITY",
                source_ref=f"PX:{ticker}:{observed.date().isoformat()}",
                signal_type="STOCK_DROP",
                category="FINANCIAL",
                severity=severity,
                title=f"{ticker} down {pct:.1f}% on the day (${price:.2f})",
                body=f"Daily close moved {pct:.2f}%. Market cap impact may indicate breaking news, earnings miss, or sector rotation.",
                link=f"https://finance.yahoo.com/quote/{ticker}",
                observed_at=observed,
                match_strings=[ticker, q.get("longName", ""), q.get("shortName", "")],
                numeric_value=pct,
                numeric_unit="%",
            )
        if is_52w_low:
            yield IntelCandidate(
                source="EQUITY",
                source_ref=f"LOW52:{ticker}:{observed.date().isoformat()}",
                signal_type="STOCK_52W_LOW",
                category="FINANCIAL",
                severity="HIGH",
                title=f"{ticker} at 52-week low (${price:.2f})",
                body=f"Price ${price:.2f} ≤ 52-week low ${low52:.2f}. Sustained weakness often correlates with supplier financial distress.",
                link=f"https://finance.yahoo.com/quote/{ticker}",
                observed_at=observed,
                match_strings=[ticker, q.get("longName", ""), q.get("shortName", "")],
                numeric_value=price,
                numeric_unit="USD",
            )


def fetch_sec_filings() -> Iterable[IntelCandidate]:
    """SEC EDGAR 8-K material event filings.

    Live: https://data.sec.gov/submissions/CIK{0-padded-10-digit}.json
    Items of interest for supply chain risk:
    - 1.01 / 1.02   Material definitive agreement / termination
    - 2.04          Triggering events accelerating a financial obligation
    - 2.06          Material impairments
    - 4.01 / 4.02   Auditor change / non-reliance on prior financials
    - 5.02          Departure of principal officers
    - 8.01          Other events (cyber breach disclosures often filed here)
    """
    data = _try_fetch("https://data.sec.gov/submissions/CIK0000063754.json") \
        or _load_fixture("sec_filings.json")
    for f in data.get("filings", []):
        item = f.get("item", "")
        cik = f.get("cik", "")
        ticker = f.get("ticker", "")
        company = f.get("company", "")
        # Severity by item type
        high_items = {"2.04", "2.06", "4.02"}
        crit_items = {"4.02"}
        severity = "CRITICAL" if item in crit_items else "HIGH" if item in high_items else "MEDIUM"
        yield IntelCandidate(
            source="SEC_EDGAR",
            source_ref=f"8K:{cik}:{f['accession']}",
            signal_type="8K_FILING",
            category="FINANCIAL",
            severity=severity,
            title=f"{company} 8-K Item {item}: {f.get('headline','material event')}",
            body=f.get("summary", ""),
            link=f.get("link"),
            observed_at=_parse_dt(f.get("filed_at", "")),
            match_strings=[s for s in (company, ticker, cik) if s],
        )


# ---------------------------------------------------------------------------
# News / geopolitical / disaster feeds
# ---------------------------------------------------------------------------

def fetch_news_events() -> Iterable[IntelCandidate]:
    """Aerospace supplier news events.

    Live options:
    - GDELT 2.0 events:   https://api.gdeltproject.org/api/v2/doc/doc?query=...&format=json
    - NewsAPI:            https://newsapi.org/v2/everything?q=...
    - GNews:              https://gnews.io/api/v4/search?q=...
    Tone score (GDELT scale -10..+10) inverted into severity: very negative tone → HIGH.
    """
    data = _try_fetch("https://api.gdeltproject.org/api/v2/doc/doc?query=aerospace+supplier&format=json") \
        or _load_fixture("news_events.json")
    for n in data.get("articles", []):
        tone = float(n.get("tone") or 0.0)
        if tone <= -7.0:
            severity = "HIGH"
        elif tone <= -4.0:
            severity = "MEDIUM"
        elif tone <= -1.0:
            severity = "LOW"
        else:
            continue  # skip non-negative news to keep signal-to-noise
        yield IntelCandidate(
            source="GDELT",
            source_ref=f"NEWS:{n['id']}",
            signal_type="NEWS",
            category="NEWS",
            severity=severity,
            title=n.get("title", "news event"),
            body=n.get("summary", ""),
            link=n.get("url"),
            observed_at=_parse_dt(n.get("published", "")),
            match_strings=list(n.get("entities", [])),
            numeric_value=tone,
            numeric_unit="GDELT",
        )


def fetch_country_risk() -> Iterable[IntelCandidate]:
    """Country-level geopolitical risk index.

    Live options:
    - World Bank Worldwide Governance Indicators
    - State Dept travel advisories: https://travel.state.gov/_res/rss/TAsTWs.xml
    - Fragile States Index (Fund for Peace)
    Signals tag suppliers whose hq_country_code matches the country.
    """
    data = _try_fetch("https://travel.state.gov/_res/rss/TAsTWs.xml") \
        or _load_fixture("country_risk.json")
    for c in data.get("countries", []):
        score = float(c.get("risk_score") or 0.0)  # 0..100
        if score >= 80:
            severity = "CRITICAL"
        elif score >= 60:
            severity = "HIGH"
        elif score >= 40:
            severity = "MEDIUM"
        else:
            severity = "LOW"
        code = c.get("country_code", "")
        yield IntelCandidate(
            source="COUNTRY_RISK",
            source_ref=f"GEO:{code}:{c.get('as_of','')}",
            signal_type="COUNTRY_RISK",
            category="GEOPOLITICAL",
            severity=severity,
            title=f"{c.get('country_name', code)} elevated country risk ({score:.0f}/100)",
            body=c.get("summary", ""),
            link=c.get("link"),
            observed_at=_parse_dt(c.get("as_of", "")),
            # Country signals match by ISO code in match_strings — matcher can hit
            # supplier.hq_country_code when it's promoted into the supplier index.
            match_strings=[code, c.get("country_name", "")],
            numeric_value=score,
            numeric_unit="risk-index",
        )


def fetch_disaster_events() -> Iterable[IntelCandidate]:
    """Natural disasters and large industrial incidents.

    Live options:
    - USGS earthquakes (M4.5+):  https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_week.geojson
    - NOAA NHC tropical storms:  https://www.nhc.noaa.gov/CurrentStorms.json
    - GDACS global alerts:       https://www.gdacs.org/xml/rss.xml
    Match by region/country_code; severity by magnitude or alert level.
    """
    data = _try_fetch("https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_week.geojson") \
        or _load_fixture("disaster_events.json")
    for d in data.get("events", []):
        sev_label = d.get("severity", "MEDIUM").upper()
        severity = sev_label if sev_label in SEVERITY_WEIGHT else "MEDIUM"
        yield IntelCandidate(
            source="DISASTER",
            source_ref=f"DIS:{d['id']}",
            signal_type="DISASTER",
            category="DISASTER",
            severity=severity,
            title=f"{d.get('event_type','event')}: {d.get('headline','')}",
            body=d.get("summary", ""),
            link=d.get("link"),
            observed_at=_parse_dt(d.get("occurred_at", "")),
            # Match supplier HQ country code or region.
            match_strings=[d.get("country_code", ""), d.get("region", "")],
            numeric_value=float(d.get("magnitude") or 0.0),
            numeric_unit=d.get("magnitude_unit", ""),
        )


ALL_FEEDS = [
    ("OFAC", fetch_ofac_sanctions),
    ("EXT_SANCTIONS", fetch_extended_sanctions),
    ("CISA_KEV", fetch_cisa_kev),
    ("NVD", fetch_nvd_cves),
    ("CISA_ICS", fetch_cisa_ics_advisories),
    ("EQUITY", fetch_stock_indicators),
    ("SEC_EDGAR", fetch_sec_filings),
    ("GDELT", fetch_news_events),
    ("COUNTRY_RISK", fetch_country_risk),
    ("DISASTER", fetch_disaster_events),
]
