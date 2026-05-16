"""Operational Impact Engine — translate a supplier failure into mission impact.

This is the wedge: instead of "supplier risk score = 78", produce
"Failure of Moog Hydraulic Systems likely causes a 27-day delay across
8 F-35As in the 4th squadron, ~$14.2M in exposure, recommend alternates
Honeywell / Collins."

Every output number is reconstructible from the data model — no LLM
hallucination, no model that has to be retrained. Defense buyers won't
sign anything they can't audit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from ..models.models import (
    Aircraft, Part, Supplier, Inventory, PurchaseOrder,
    MaintenanceEvent, FlightSchedule, SupplierIntelSignal,
)


# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------

# How long it realistically takes to qualify a new supplier for a flight-
# critical part on a defense program. Conservative midpoint of public AS9100
# qualification timelines for aerospace. Surfaced separately in the output
# so customers can override.
QUALIFICATION_DAYS_DEFAULT = 120

# Multiplier on dollar exposure when a part is flagged mission-critical
# (a grounded sortie costs vastly more than a routine consumable).
MISSION_CRITICAL_COST_MULTIPLIER = 4.0

# Per-day cost of a grounded aircraft (industry rule-of-thumb for a tactical
# fighter: roughly $50k/day in carrying costs, deferred-maintenance burden,
# and lost training value). Surface as a parameter so the buyer can override.
GROUNDED_AIRCRAFT_COST_PER_DAY = 50_000


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class AffectedPart:
    part_number: str
    name: str
    category: str
    is_mission_critical: bool
    is_single_source: bool
    unit_cost: float
    lead_time_days: int
    quantity_on_hand: int
    days_of_stock: int
    gap_days: int                          # days within horizon without coverage
    affected_tail_numbers: list[str]


@dataclass
class AffectedAircraft:
    tail_number: str
    platform: str
    squadron: str
    base_location: str
    current_status: str
    blocking_part_numbers: list[str]
    days_to_impact: int                    # earliest gap_days across its blocking parts
    sortie_value_at_risk: float            # grounded-cost × horizon coverage


@dataclass
class AlternateSupplier:
    supplier_id: int
    name: str
    country: str
    reliability_score: float
    on_time_delivery_rate: float
    overlap_categories: list[str]
    overlap_part_count: int
    has_active_intel: bool
    rank_score: float                      # higher = better candidate


@dataclass
class ImpactResult:
    supplier_id: int
    supplier_name: str
    horizon_days: int
    qualification_days: int

    # Headline numbers
    aircraft_affected: int
    tails: list[str]
    platforms: dict[str, int]              # {"F-35A": 8, "F-22A": 3}
    production_delay_days: int             # max gap among critical parts
    dollar_exposure_usd: float
    confidence: float                      # 0..1
    severity: str                          # CRITICAL | HIGH | MEDIUM | LOW

    # Drilldowns
    affected_parts: list[AffectedPart] = field(default_factory=list)
    affected_aircraft: list[AffectedAircraft] = field(default_factory=list)
    alternates: list[AlternateSupplier] = field(default_factory=list)
    cascading_signals: list[dict] = field(default_factory=list)
    mitigation_actions: list[str] = field(default_factory=list)
    executive_one_liner: str = ""

    def as_dict(self) -> dict:
        return {
            "supplier_id": self.supplier_id,
            "supplier_name": self.supplier_name,
            "horizon_days": self.horizon_days,
            "qualification_days": self.qualification_days,
            "aircraft_affected": self.aircraft_affected,
            "tails": self.tails,
            "platforms": self.platforms,
            "production_delay_days": self.production_delay_days,
            "dollar_exposure_usd": round(self.dollar_exposure_usd, 0),
            "confidence": round(self.confidence, 2),
            "severity": self.severity,
            "executive_one_liner": self.executive_one_liner,
            "affected_parts": [p.__dict__ for p in self.affected_parts],
            "affected_aircraft": [a.__dict__ for a in self.affected_aircraft],
            "alternates": [a.__dict__ for a in self.alternates],
            "cascading_signals": self.cascading_signals,
            "mitigation_actions": self.mitigation_actions,
        }


# ---------------------------------------------------------------------------
# Core calculation
# ---------------------------------------------------------------------------

def _days_of_stock(inv: Optional[Inventory]) -> int:
    if not inv or inv.avg_monthly_consumption <= 0:
        return 9999
    daily = inv.avg_monthly_consumption / 30.0
    if daily <= 0:
        return 9999
    return int(inv.quantity_on_hand / daily)


def simulate_supplier_failure(
    db: Session,
    supplier_id: int,
    horizon_days: int = 90,
    qualification_days: int = QUALIFICATION_DAYS_DEFAULT,
    grounded_cost_per_day: float = GROUNDED_AIRCRAFT_COST_PER_DAY,
) -> Optional[ImpactResult]:
    """Compute full operational impact of supplier failure over `horizon_days`."""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        return None

    now = datetime.utcnow()
    horizon_end = now + timedelta(days=horizon_days)

    parts = db.query(Part).filter(Part.supplier_id == supplier_id).all()
    if not parts:
        return ImpactResult(
            supplier_id=supplier_id, supplier_name=supplier.name,
            horizon_days=horizon_days, qualification_days=qualification_days,
            aircraft_affected=0, tails=[], platforms={},
            production_delay_days=0, dollar_exposure_usd=0,
            confidence=0.9, severity="LOW",
            executive_one_liner=f"{supplier.name}: no catalog parts depend on this supplier.",
        )

    # Per-part impact
    affected_parts: list[AffectedPart] = []
    aircraft_blockers: dict[str, dict] = {}  # tail → {parts: set, earliest_gap, aircraft_obj}
    total_dollar = 0.0
    max_delay = 0

    for part in parts:
        inv = db.query(Inventory).filter(Inventory.part_id == part.id).first()
        days_stock = _days_of_stock(inv)

        # If the supplier fails today, replacement timeline:
        # cushion = days_stock, then dependent on qualification of an alternate
        # supplier OR depletion (whichever first).
        coverage_days = days_stock
        gap_days = max(0, horizon_days - coverage_days)

        # Maintenance events within horizon needing this part
        events = (
            db.query(MaintenanceEvent)
            .filter(
                MaintenanceEvent.part_id == part.id,
                MaintenanceEvent.status.in_(["SCHEDULED", "IN_PROGRESS"]),
                MaintenanceEvent.scheduled_date <= horizon_end,
            )
            .all()
        )

        affected_tails_for_part: list[str] = []
        for e in events:
            aircraft = db.query(Aircraft).filter(Aircraft.id == e.aircraft_id).first()
            if not aircraft:
                continue
            # Days from now until this event — used to set days_to_impact
            days_to_event = max(0, (e.scheduled_date - now).days) if e.scheduled_date else horizon_days
            # Only count events that fall in the gap window
            if days_to_event >= coverage_days:
                affected_tails_for_part.append(aircraft.tail_number)
                rec = aircraft_blockers.setdefault(aircraft.tail_number, {
                    "aircraft": aircraft,
                    "parts": set(),
                    "earliest_gap": days_to_event - coverage_days,
                })
                rec["parts"].add(part.part_number)
                rec["earliest_gap"] = min(rec["earliest_gap"], days_to_event - coverage_days)

        # Part-level dollar exposure: missed-demand × unit_cost × criticality mult
        if gap_days > 0 and inv and inv.avg_monthly_consumption > 0:
            missed = (inv.avg_monthly_consumption / 30.0) * gap_days
            crit_mult = MISSION_CRITICAL_COST_MULTIPLIER if part.is_mission_critical else 1.0
            total_dollar += missed * (part.unit_cost or 0) * crit_mult

        # Production delay heuristic: the binding constraint is qualification of
        # an alternate when this is single-source, otherwise the part's own
        # lead time. Clamp to horizon.
        if part.is_single_source:
            part_delay = min(horizon_days, max(0, qualification_days - coverage_days))
        else:
            part_delay = min(horizon_days, max(0, part.lead_time_days - coverage_days))
        if part.is_mission_critical and part_delay > max_delay:
            max_delay = part_delay

        affected_parts.append(AffectedPart(
            part_number=part.part_number,
            name=part.name,
            category=part.category,
            is_mission_critical=part.is_mission_critical,
            is_single_source=part.is_single_source,
            unit_cost=part.unit_cost or 0.0,
            lead_time_days=part.lead_time_days,
            quantity_on_hand=inv.quantity_on_hand if inv else 0,
            days_of_stock=days_stock if days_stock < 9999 else -1,
            gap_days=gap_days,
            affected_tail_numbers=sorted(set(affected_tails_for_part)),
        ))

    # Aircraft rollup
    affected_aircraft: list[AffectedAircraft] = []
    platform_counts: dict[str, int] = {}
    for tail, rec in aircraft_blockers.items():
        aircraft: Aircraft = rec["aircraft"]
        days_to_impact = rec["earliest_gap"]
        # Grounded-cost contribution: assume the aircraft is unavailable for
        # the remaining horizon once the gap starts.
        coverage_in_horizon = max(0, horizon_days - days_to_impact)
        sortie_value = grounded_cost_per_day * coverage_in_horizon
        total_dollar += sortie_value
        affected_aircraft.append(AffectedAircraft(
            tail_number=tail,
            platform=aircraft.platform,
            squadron=aircraft.squadron,
            base_location=aircraft.base_location,
            current_status=aircraft.mission_status,
            blocking_part_numbers=sorted(rec["parts"]),
            days_to_impact=days_to_impact,
            sortie_value_at_risk=sortie_value,
        ))
        platform_counts[aircraft.platform] = platform_counts.get(aircraft.platform, 0) + 1

    affected_aircraft.sort(key=lambda a: a.days_to_impact)

    # Alternates
    alternates = _rank_alternate_suppliers(db, supplier, parts)

    # Cascading intel signals — active signals already attributed to this supplier
    intel = (
        db.query(SupplierIntelSignal)
        .filter(SupplierIntelSignal.supplier_id == supplier_id,
                SupplierIntelSignal.is_active == True)  # noqa: E712
        .order_by(SupplierIntelSignal.observed_at.desc())
        .limit(8)
        .all()
    )
    cascading = [{
        "source": s.source, "category": s.category, "severity": s.severity,
        "title": s.title, "observed_at": s.observed_at.isoformat() if s.observed_at else None,
    } for s in intel]

    # Severity
    mc_aircraft = sum(1 for a in affected_aircraft if a.current_status in ("NMC", "AT_RISK", "PMC"))
    if total_dollar >= 10_000_000 or len(affected_aircraft) >= 10 or mc_aircraft >= 3:
        severity = "CRITICAL"
    elif total_dollar >= 1_000_000 or len(affected_aircraft) >= 3:
        severity = "HIGH"
    elif total_dollar > 0 or affected_aircraft:
        severity = "MEDIUM"
    else:
        severity = "LOW"

    # Confidence: inventory coverage we trust + matched intel
    confidence = 0.75
    if any(p.is_single_source for p in parts):
        confidence -= 0.1  # less alternative data
    if intel:
        confidence += 0.1
    confidence = max(0.4, min(0.95, confidence))

    # Mitigation playbook
    mitigation = _build_mitigation(supplier, parts, alternates, severity)

    # The headline line CIOs read
    one_liner = _format_one_liner(
        supplier, len(affected_aircraft), platform_counts, max_delay, total_dollar, alternates,
    )

    return ImpactResult(
        supplier_id=supplier_id,
        supplier_name=supplier.name,
        horizon_days=horizon_days,
        qualification_days=qualification_days,
        aircraft_affected=len(affected_aircraft),
        tails=[a.tail_number for a in affected_aircraft],
        platforms=platform_counts,
        production_delay_days=max_delay,
        dollar_exposure_usd=total_dollar,
        confidence=confidence,
        severity=severity,
        affected_parts=sorted(affected_parts, key=lambda p: (-p.gap_days, p.part_number)),
        affected_aircraft=affected_aircraft,
        alternates=alternates,
        cascading_signals=cascading,
        mitigation_actions=mitigation,
        executive_one_liner=one_liner,
    )


def _rank_alternate_suppliers(db: Session, failed: Supplier, parts: list[Part]) -> list[AlternateSupplier]:
    """Suppliers carrying parts in the same categories, ranked by viability."""
    if not parts:
        return []
    categories = {p.category for p in parts if p.category}
    if not categories:
        return []

    candidates = (
        db.query(Supplier)
        .join(Part, Part.supplier_id == Supplier.id)
        .filter(
            Supplier.id != failed.id,
            Supplier.is_approved == True,                           # noqa: E712
            Part.category.in_(categories),
        )
        .distinct()
        .all()
    )

    out: list[AlternateSupplier] = []
    for cand in candidates:
        cand_parts = db.query(Part).filter(Part.supplier_id == cand.id, Part.category.in_(categories)).all()
        overlap_cats = sorted({p.category for p in cand_parts})
        # Active intel?
        has_intel = (
            db.query(SupplierIntelSignal)
            .filter(SupplierIntelSignal.supplier_id == cand.id,
                    SupplierIntelSignal.is_active == True,          # noqa: E712
                    SupplierIntelSignal.severity.in_(("CRITICAL", "HIGH")))
            .first()
        ) is not None
        # Rank: reliability + OTD - intel penalty + category-overlap bonus
        rank = (
            cand.reliability_score * 0.4
            + cand.on_time_delivery_rate * 0.35
            + min(0.15, len(overlap_cats) * 0.05)
            - (0.25 if has_intel else 0)
            - (cand.defect_rate * 3)
        )
        out.append(AlternateSupplier(
            supplier_id=cand.id,
            name=cand.name,
            country=cand.country,
            reliability_score=cand.reliability_score,
            on_time_delivery_rate=cand.on_time_delivery_rate,
            overlap_categories=overlap_cats,
            overlap_part_count=len(cand_parts),
            has_active_intel=has_intel,
            rank_score=round(rank, 3),
        ))
    out.sort(key=lambda a: a.rank_score, reverse=True)
    return out[:5]


def _build_mitigation(supplier: Supplier, parts: list[Part],
                      alternates: list[AlternateSupplier], severity: str) -> list[str]:
    actions: list[str] = []
    crit_count = sum(1 for p in parts if p.is_mission_critical)
    ss_count = sum(1 for p in parts if p.is_single_source)

    if severity == "CRITICAL":
        actions.append(f"DECLARE supply chain incident — {supplier.name} loss exceeds mission-critical thresholds")
    if alternates:
        top = alternates[0]
        actions.append(
            f"Initiate qualification of {top.name} as alternate "
            f"(reliability {top.reliability_score:.2f}, OTD {top.on_time_delivery_rate*100:.0f}%, "
            f"covers {top.overlap_part_count} parts in {len(top.overlap_categories)} categories)"
        )
        if len(alternates) > 1:
            actions.append(f"Parallel-qualify {alternates[1].name} as second source to break single-source dependency")
    else:
        actions.append("No approved alternate suppliers identified — escalate to engineering for emergency source approval")
    if ss_count > 0:
        actions.append(f"Engineering review: {ss_count} single-source parts require dual-source qualification plan")
    if crit_count > 0:
        actions.append(f"Pre-position safety stock for the {crit_count} mission-critical part(s) before depletion")
    actions.append("Issue Corrective Action Request to supplier and request continuity-of-supply attestation")
    actions.append("Brief PEO / program office with this impact report")
    return actions


def _format_one_liner(supplier: Supplier, n_aircraft: int, platforms: dict[str, int],
                      delay_days: int, dollar: float, alternates: list[AlternateSupplier]) -> str:
    platform_str = ", ".join(f"{c} {p}" for p, c in sorted(platforms.items(), key=lambda x: -x[1])[:3])
    alt_str = ", ".join(a.name for a in alternates[:3]) if alternates else "NO APPROVED ALTERNATE"
    return (
        f"Failure of {supplier.name} likely causes a {delay_days}-day production delay, "
        f"affects {n_aircraft} aircraft"
        + (f" ({platform_str})" if platform_str else "")
        + f", projected exposure ${dollar/1_000_000:.1f}M. "
        f"Recommend alternates: {alt_str}."
    )


# ---------------------------------------------------------------------------
# Portfolio view
# ---------------------------------------------------------------------------

def rank_operational_risks(db: Session, horizon_days: int = 90, top_n: int = 5) -> list[dict]:
    """Run the simulator across every supplier; return the top N by impact.

    This is the "what's our worst exposure right now" view. Expensive — only
    call on-demand or as a scheduled job.
    """
    results = []
    for supplier in db.query(Supplier).all():
        impact = simulate_supplier_failure(db, supplier.id, horizon_days=horizon_days)
        if impact is None or impact.aircraft_affected == 0:
            continue
        results.append({
            "supplier_id": supplier.id,
            "supplier_name": supplier.name,
            "severity": impact.severity,
            "aircraft_affected": impact.aircraft_affected,
            "platforms": impact.platforms,
            "production_delay_days": impact.production_delay_days,
            "dollar_exposure_usd": round(impact.dollar_exposure_usd, 0),
            "confidence": impact.confidence,
            "one_liner": impact.executive_one_liner,
            "top_alternate": impact.alternates[0].name if impact.alternates else None,
        })
    results.sort(key=lambda r: (r["dollar_exposure_usd"], r["aircraft_affected"]), reverse=True)
    return results[:top_n]
