"""Fuzzy match external intel candidates to suppliers in the catalog."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable, Optional

from rapidfuzz import fuzz, process
from sqlalchemy.orm import Session

from ...models.models import Supplier


@dataclass(frozen=True)
class SupplierIndexEntry:
    supplier_id: int
    handle: str           # the actual string we matched against (name / alias / keyword)
    handle_kind: str      # "name" | "alias" | "keyword" | "domain"


@dataclass(frozen=True)
class Match:
    supplier_id: int
    confidence: float     # 0..100
    matched_on: str       # "<kind>:<handle>"


def _decode_list(blob: Optional[str]) -> list[str]:
    if not blob:
        return []
    try:
        v = json.loads(blob)
        return [str(x).strip() for x in v if str(x).strip()]
    except (json.JSONDecodeError, TypeError):
        return []


def build_supplier_index(db: Session) -> list[SupplierIndexEntry]:
    """Flatten suppliers into one handle per row for the matcher."""
    index: list[SupplierIndexEntry] = []
    for s in db.query(Supplier).all():
        if s.name:
            index.append(SupplierIndexEntry(s.id, s.name, "name"))
        for alias in _decode_list(s.aliases):
            index.append(SupplierIndexEntry(s.id, alias, "alias"))
        for kw in _decode_list(s.keywords):
            index.append(SupplierIndexEntry(s.id, kw, "keyword"))
        if s.domain:
            index.append(SupplierIndexEntry(s.id, s.domain, "domain"))
        if s.ticker:
            index.append(SupplierIndexEntry(s.id, s.ticker, "ticker"))
        if s.cik:
            # Keep the raw CIK and a zero-stripped variant — EDGAR pads to 10 digits.
            index.append(SupplierIndexEntry(s.id, s.cik, "cik"))
            stripped = s.cik.lstrip("0")
            if stripped and stripped != s.cik:
                index.append(SupplierIndexEntry(s.id, stripped, "cik"))
        if s.hq_country_code:
            index.append(SupplierIndexEntry(s.id, s.hq_country_code, "country_code"))
    return index


def best_match(
    candidates: Iterable[str],
    index: list[SupplierIndexEntry],
    threshold: float,
) -> Optional[Match]:
    """Return the best supplier match across all candidate strings.

    Uses token_set_ratio so "Collins Aerospace" matches "Collins Aerospace Solutions"
    and "Honeywell" matches "Honeywell Aerospace Tech". Substring containment
    (one side fully contained in the other) is treated as a strong match even
    when the ratio is borderline — vendor strings in CVE/advisory feeds are
    often short tokens like "GE" or "Honeywell" that legitimately appear inside
    longer supplier names.
    """
    if not index:
        return None

    handles = [entry.handle for entry in index]
    best: Optional[Match] = None

    for cand in candidates:
        cand = (cand or "").strip()
        if not cand:
            continue

        cand_lc = cand.lower()
        for entry in index:
            handle_lc = entry.handle.lower()
            if handle_lc == cand_lc:
                score = 100.0
            elif cand_lc in handle_lc or handle_lc in cand_lc:
                score = max(92.0, fuzz.token_set_ratio(cand, entry.handle))
            else:
                score = fuzz.token_set_ratio(cand, entry.handle)

            if score >= threshold and (best is None or score > best.confidence):
                best = Match(
                    supplier_id=entry.supplier_id,
                    confidence=float(score),
                    matched_on=f"{entry.handle_kind}:{entry.handle}",
                )

    return best
