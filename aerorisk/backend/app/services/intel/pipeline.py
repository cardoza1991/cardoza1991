"""Orchestrate: fetch feeds → match suppliers → upsert signals."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from ...config import settings
from ...models.models import Supplier, SupplierIntelSignal
from .feeds import ALL_FEEDS, IntelCandidate
from .matcher import best_match, build_supplier_index

# Signal types that fan out to every supplier matching a country code or region
# rather than matching a single supplier name. The matcher would otherwise
# pick one arbitrary supplier in the country.
FANOUT_TYPES = {"COUNTRY_RISK", "DISASTER"}

log = logging.getLogger(__name__)


@dataclass
class IntelCycleResult:
    fetched: int = 0
    matched: int = 0
    new_signals: int = 0
    updated_signals: int = 0
    unmatched: int = 0
    by_source: dict[str, int] = field(default_factory=dict)
    new_critical: list[int] = field(default_factory=list)   # signal ids — agent loop uses these

    def as_dict(self) -> dict:
        return {
            "fetched": self.fetched,
            "matched": self.matched,
            "new_signals": self.new_signals,
            "updated_signals": self.updated_signals,
            "unmatched": self.unmatched,
            "by_source": self.by_source,
            "new_critical_signal_ids": self.new_critical,
        }


def _upsert_signal(
    db: Session,
    candidate: IntelCandidate,
    supplier_id: int,
    confidence: float,
    matched_on: str,
    source_ref_override: Optional[str] = None,
) -> tuple[SupplierIntelSignal, bool]:
    """Upsert by (source, source_ref). Returns (signal, is_new)."""
    source_ref = source_ref_override or candidate.source_ref
    existing = (
        db.query(SupplierIntelSignal)
        .filter(
            SupplierIntelSignal.source == candidate.source,
            SupplierIntelSignal.source_ref == source_ref,
        )
        .first()
    )
    if existing:
        existing.supplier_id = supplier_id
        existing.category = candidate.category
        existing.signal_type = candidate.signal_type
        existing.severity = candidate.severity
        existing.title = candidate.title
        existing.body = candidate.body
        existing.link = candidate.link
        existing.observed_at = candidate.observed_at
        existing.fetched_at = datetime.utcnow()
        existing.score_weight = candidate.score_weight
        existing.numeric_value = candidate.numeric_value
        existing.numeric_unit = candidate.numeric_unit
        existing.is_active = True
        existing.match_confidence = confidence
        existing.matched_on = matched_on
        return existing, False

    sig = SupplierIntelSignal(
        supplier_id=supplier_id,
        source=candidate.source,
        source_ref=source_ref,
        category=candidate.category,
        signal_type=candidate.signal_type,
        severity=candidate.severity,
        title=candidate.title,
        body=candidate.body,
        link=candidate.link,
        observed_at=candidate.observed_at,
        fetched_at=datetime.utcnow(),
        score_weight=candidate.score_weight,
        numeric_value=candidate.numeric_value,
        numeric_unit=candidate.numeric_unit,
        is_active=True,
        match_confidence=confidence,
        matched_on=matched_on,
    )
    db.add(sig)
    return sig, True


def run_intel_cycle(db: Session) -> IntelCycleResult:
    """Single end-to-end pull. Safe to call repeatedly — dedupes by source_ref."""
    result = IntelCycleResult()
    index = build_supplier_index(db)
    if not index:
        log.info("intel cycle: no suppliers indexed yet, skipping")
        return result

    threshold = settings.intel_match_threshold

    for source_name, fetcher in ALL_FEEDS:
        try:
            candidates = list(fetcher())
        except Exception as e:  # one bad feed shouldn't kill the cycle
            log.exception("intel feed %s failed: %s", source_name, e)
            continue

        result.fetched += len(candidates)
        for cand in candidates:
            if cand.signal_type in FANOUT_TYPES:
                # Country- or region-keyed signals fan out to every supplier
                # whose HQ matches. Source_ref is suffixed with supplier_id so
                # each per-supplier row dedupes independently.
                country = next((s for s in cand.match_strings if s and len(s) <= 4), None)
                region = next((s for s in cand.match_strings if s and len(s) > 4), None)
                suppliers_q = db.query(Supplier)
                if country:
                    suppliers_q = suppliers_q.filter(Supplier.hq_country_code == country)
                elif region:
                    suppliers_q = suppliers_q.filter(Supplier.hq_region == region)
                else:
                    result.unmatched += 1
                    continue
                affected = suppliers_q.all()
                if not affected:
                    result.unmatched += 1
                    continue
                for supplier in affected:
                    matched_on = f"country_code:{country}" if country else f"region:{region}"
                    sig, is_new = _upsert_signal(
                        db, cand, supplier.id, 100.0, matched_on,
                        source_ref_override=f"{cand.source_ref}:s{supplier.id}",
                    )
                    db.flush()
                    result.matched += 1
                    result.by_source[source_name] = result.by_source.get(source_name, 0) + 1
                    if is_new:
                        result.new_signals += 1
                        if cand.severity == "CRITICAL":
                            result.new_critical.append(sig.id)
                    else:
                        result.updated_signals += 1
                continue

            match = best_match(cand.match_strings, index, threshold)
            if match is None:
                result.unmatched += 1
                continue

            sig, is_new = _upsert_signal(
                db, cand, match.supplier_id, match.confidence, match.matched_on
            )
            db.flush()
            result.matched += 1
            result.by_source[source_name] = result.by_source.get(source_name, 0) + 1
            if is_new:
                result.new_signals += 1
                if cand.severity == "CRITICAL":
                    result.new_critical.append(sig.id)
            else:
                result.updated_signals += 1

    db.commit()
    log.info(
        "intel cycle: fetched=%d matched=%d new=%d updated=%d unmatched=%d",
        result.fetched, result.matched, result.new_signals,
        result.updated_signals, result.unmatched,
    )
    return result
