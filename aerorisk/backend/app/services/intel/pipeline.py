"""Orchestrate: fetch feeds → match suppliers → upsert signals."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.orm import Session

from ...config import settings
from ...models.models import SupplierIntelSignal
from .feeds import ALL_FEEDS, IntelCandidate
from .matcher import best_match, build_supplier_index

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
) -> tuple[SupplierIntelSignal, bool]:
    """Upsert by (source, source_ref). Returns (signal, is_new)."""
    existing = (
        db.query(SupplierIntelSignal)
        .filter(
            SupplierIntelSignal.source == candidate.source,
            SupplierIntelSignal.source_ref == candidate.source_ref,
        )
        .first()
    )
    if existing:
        existing.supplier_id = supplier_id
        existing.signal_type = candidate.signal_type
        existing.severity = candidate.severity
        existing.title = candidate.title
        existing.body = candidate.body
        existing.link = candidate.link
        existing.observed_at = candidate.observed_at
        existing.fetched_at = datetime.utcnow()
        existing.score_weight = candidate.score_weight
        existing.is_active = True
        existing.match_confidence = confidence
        existing.matched_on = matched_on
        return existing, False

    sig = SupplierIntelSignal(
        supplier_id=supplier_id,
        source=candidate.source,
        source_ref=candidate.source_ref,
        signal_type=candidate.signal_type,
        severity=candidate.severity,
        title=candidate.title,
        body=candidate.body,
        link=candidate.link,
        observed_at=candidate.observed_at,
        fetched_at=datetime.utcnow(),
        score_weight=candidate.score_weight,
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
