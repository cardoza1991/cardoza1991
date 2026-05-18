from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from ..database import Base


class RiskLevel(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class MissionStatus(str, enum.Enum):
    FMC = "FMC"
    PMC = "PMC"
    NMC = "NMC"
    AT_RISK = "AT_RISK"


class Tenant(Base):
    """A customer organization. Every tenant-scoped row carries a tenant_id.

    Demo mode operates against a single default tenant; production
    deployments create one tenant per customer and enforce isolation via
    the `require_auth` flag + the tenant_id filters in the routers.
    """
    __tablename__ = "tenants"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), unique=True, index=True)
    slug = Column(String(80), unique=True, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), index=True)
    email = Column(String(200), unique=True, index=True)
    full_name = Column(String(200))
    password_hash = Column(String(200))            # bcrypt
    role = Column(String(40), default="operator")  # admin | operator | viewer
    is_active = Column(Boolean, default=True)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    tenant = relationship("Tenant", back_populates="users")


class AuditLog(Base):
    """Append-only audit trail of mutating actions. Required for any defense
    deployment going through ATO / FedRAMP / NIST SP 800-53 AU-2 controls."""
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    user_email = Column(String(200), nullable=True)   # denormalized so deletes don't lose context
    action = Column(String(80), index=True)           # e.g. "bom.upload", "impact.simulate"
    resource_type = Column(String(80), nullable=True) # e.g. "BomUpload", "ImpactScenario"
    resource_id = Column(String(80), nullable=True)
    method = Column(String(10), nullable=True)
    path = Column(String(500), nullable=True)
    status_code = Column(Integer, nullable=True)
    ip = Column(String(64), nullable=True)
    user_agent = Column(String(400), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)


class Aircraft(Base):
    __tablename__ = "aircraft"
    id = Column(Integer, primary_key=True, index=True)
    tail_number = Column(String(20), unique=True, index=True)
    platform = Column(String(50))
    squadron = Column(String(50))
    base_location = Column(String(100))
    mission_status = Column(String(20), default="FMC")
    flight_hours_total = Column(Float, default=0.0)
    last_maintenance_date = Column(DateTime)
    next_scheduled_maintenance = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

    maintenance_events = relationship("MaintenanceEvent", back_populates="aircraft")
    risk_scores = relationship("RiskScore", back_populates="aircraft")


class Supplier(Base):
    __tablename__ = "suppliers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200))
    country = Column(String(100))
    reliability_score = Column(Float, default=1.0)
    avg_lead_time_days = Column(Integer, default=30)
    on_time_delivery_rate = Column(Float, default=0.95)
    defect_rate = Column(Float, default=0.02)
    single_source_parts_count = Column(Integer, default=0)
    is_approved = Column(Boolean, default=True)
    last_audit_date = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

    # Intel-matching identifiers. JSON-encoded lists in Text columns to stay
    # portable across PostgreSQL/SQLite without ARRAY/JSONB.
    aliases = Column(Text, nullable=True)         # JSON list[str]
    domain = Column(String(200), nullable=True)
    keywords = Column(Text, nullable=True)        # JSON list[str]: CVE vendor strings, product names, etc.
    ticker = Column(String(20), nullable=True, index=True)   # equity symbol (e.g. "RTX", "LMT")
    cik = Column(String(20), nullable=True, index=True)       # SEC CIK for EDGAR lookups
    hq_country_code = Column(String(4), nullable=True)        # ISO-3166-1 alpha-2 (e.g. "US", "FR", "TW")
    hq_region = Column(String(60), nullable=True)             # "North America", "Asia-Pacific", etc.

    parts = relationship("Part", back_populates="supplier")
    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")
    intel_signals = relationship("SupplierIntelSignal", back_populates="supplier", cascade="all, delete-orphan")


class Part(Base):
    __tablename__ = "parts"
    id = Column(Integer, primary_key=True, index=True)
    part_number = Column(String(50), unique=True, index=True)
    name = Column(String(200))
    description = Column(Text)
    platform_compatibility = Column(String(200))
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    unit_cost = Column(Float)
    lead_time_days = Column(Integer, default=30)
    lead_time_variance_days = Column(Integer, default=5)
    is_mission_critical = Column(Boolean, default=False)
    is_single_source = Column(Boolean, default=False)
    category = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())

    supplier = relationship("Supplier", back_populates="parts")
    inventory = relationship("Inventory", back_populates="part", uselist=False)
    purchase_orders = relationship("PurchaseOrder", back_populates="part")
    maintenance_events = relationship("MaintenanceEvent", back_populates="part")


class Inventory(Base):
    __tablename__ = "inventory"
    id = Column(Integer, primary_key=True, index=True)
    part_id = Column(Integer, ForeignKey("parts.id"), unique=True)
    quantity_on_hand = Column(Integer, default=0)
    quantity_on_order = Column(Integer, default=0)
    reorder_point = Column(Integer, default=5)
    reorder_quantity = Column(Integer, default=10)
    warehouse_location = Column(String(50))
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())
    avg_monthly_consumption = Column(Float, default=1.0)

    part = relationship("Part", back_populates="inventory")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    id = Column(Integer, primary_key=True, index=True)
    po_number = Column(String(50), unique=True)
    part_id = Column(Integer, ForeignKey("parts.id"))
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    quantity_ordered = Column(Integer)
    unit_price = Column(Float)
    order_date = Column(DateTime)
    expected_delivery_date = Column(DateTime)
    actual_delivery_date = Column(DateTime, nullable=True)
    status = Column(String(50))
    delay_days = Column(Integer, default=0)
    delay_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    part = relationship("Part", back_populates="purchase_orders")
    supplier = relationship("Supplier", back_populates="purchase_orders")


class MaintenanceEvent(Base):
    __tablename__ = "maintenance_events"
    id = Column(Integer, primary_key=True, index=True)
    aircraft_id = Column(Integer, ForeignKey("aircraft.id"))
    part_id = Column(Integer, ForeignKey("parts.id"), nullable=True)
    event_type = Column(String(100))
    description = Column(Text)
    scheduled_date = Column(DateTime)
    completed_date = Column(DateTime, nullable=True)
    status = Column(String(50))
    technician = Column(String(100))
    requires_part = Column(Boolean, default=False)
    part_available = Column(Boolean, default=True)
    downtime_hours = Column(Float, default=0.0)
    created_at = Column(DateTime, server_default=func.now())

    aircraft = relationship("Aircraft", back_populates="maintenance_events")
    part = relationship("Part", back_populates="maintenance_events")


class FlightSchedule(Base):
    __tablename__ = "flight_schedule"
    id = Column(Integer, primary_key=True, index=True)
    aircraft_id = Column(Integer, ForeignKey("aircraft.id"))
    mission_name = Column(String(200))
    mission_type = Column(String(100))
    scheduled_date = Column(DateTime)
    duration_hours = Column(Float)
    priority = Column(String(20))
    status = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())


class RiskScore(Base):
    __tablename__ = "risk_scores"
    id = Column(Integer, primary_key=True, index=True)
    aircraft_id = Column(Integer, ForeignKey("aircraft.id"), nullable=True)
    part_id = Column(Integer, ForeignKey("parts.id"), nullable=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    risk_type = Column(String(50))
    score = Column(Float)
    shortage_probability = Column(Float, default=0.0)
    lead_time_volatility = Column(Float, default=0.0)
    supplier_reliability_risk = Column(Float, default=0.0)
    mission_criticality = Column(Float, default=0.0)
    historical_failure_rate = Column(Float, default=0.0)
    confidence_level = Column(Float, default=0.0)
    days_to_event = Column(Integer, nullable=True)
    explanation = Column(Text)
    computed_at = Column(DateTime, server_default=func.now())

    aircraft = relationship("Aircraft", back_populates="risk_scores")


class SupplierIntelSignal(Base):
    """External-source signal attributed to a supplier.

    A signal is a single observation (a sanction listing, a CVE in a product
    line, an ICS advisory, a cyber incident report) — not a derived score.
    The risk engine aggregates active signals into a supplier intel risk
    component; the agent loop converts new CRITICAL signals into operator
    recommendations.
    """
    __tablename__ = "supplier_intel_signals"
    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True, index=True)

    # Provenance
    source = Column(String(50), index=True)          # OFAC | CISA_KEV | CISA_ICS | CUSTOM
    source_ref = Column(String(200), index=True)     # SDN ID, CVE id, advisory id — used for dedupe
    link = Column(String(500), nullable=True)

    # Classification
    category = Column(String(30), index=True)        # SANCTION | CYBER | FINANCIAL | NEWS | GEOPOLITICAL | DISASTER
    signal_type = Column(String(40), index=True)     # SANCTION | CVE | ADVISORY | CYBER_INCIDENT | NEWS | STOCK_DROP | 8K_FILING | COUNTRY_RISK | DISASTER
    severity = Column(String(20))                    # CRITICAL | HIGH | MEDIUM | LOW
    score_weight = Column(Float, default=0.0)        # 0..1 contribution to intel risk component
    numeric_value = Column(Float, nullable=True)     # stock pct change, CVSS, tone score — whatever the feed publishes
    numeric_unit = Column(String(20), nullable=True) # "%", "USD", "CVSS", "GDELT"

    # Content
    title = Column(String(500))
    body = Column(Text, nullable=True)

    # Lifecycle
    observed_at = Column(DateTime)                   # when the source published it
    fetched_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=True)     # null = no expiry; risk engine treats expired as inactive
    is_active = Column(Boolean, default=True)

    # Matching
    match_confidence = Column(Float, default=0.0)    # 0..100 from fuzzy match
    matched_on = Column(String(200), nullable=True)  # which alias/keyword triggered the match

    supplier = relationship("Supplier", back_populates="intel_signals")


class AgentRecommendation(Base):
    __tablename__ = "agent_recommendations"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300))
    recommendation_type = Column(String(50))
    priority = Column(String(20))
    aircraft_affected = Column(String(200))
    part_affected = Column(String(100))
    supplier_affected = Column(String(200))
    description = Column(Text)
    rationale = Column(Text)
    estimated_impact = Column(Text)
    action_steps = Column(Text)
    status = Column(String(50), default="OPEN")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class ImpactScenario(Base):
    """Persisted snapshot of an operational impact simulation.

    Created by:
    - the autonomous trigger (every new CRITICAL intel signal),
    - manual user simulation from the UI,
    - scheduled portfolio runs.

    Holds the full impact result as JSON so the page renders without
    re-simulating, and so shareable links surface a stable view even
    after the underlying data shifts. share_token enables a public
    read-only URL — no auth required.
    """
    __tablename__ = "impact_scenarios"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), index=True)
    trigger = Column(String(30), index=True)              # AUTO_INTEL | MANUAL | SCHEDULED
    trigger_signal_id = Column(Integer, ForeignKey("supplier_intel_signals.id"), nullable=True)
    horizon_days = Column(Integer)
    severity = Column(String(20), index=True)
    aircraft_affected = Column(Integer, default=0)
    production_delay_days = Column(Integer, default=0)
    dollar_exposure_usd = Column(Float, default=0.0)
    confidence = Column(Float, default=0.0)
    one_liner = Column(Text)
    snapshot_json = Column(Text)                          # full ImpactResult.as_dict()
    share_token = Column(String(64), unique=True, index=True)
    notified = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now(), index=True)


class BomUpload(Base):
    """An uploaded Bill-of-Materials manifest (CycloneDX / SPDX / CSV).

    The BOM is parsed into BomComponent rows, each enriched against NVD/KEV
    for vulnerabilities and matched against the existing Part catalog. The
    result is a per-upload risk roll-up plus, when components map to parts
    that map to aircraft, a fleet-level cyber-physical impact summary.
    """
    __tablename__ = "bom_uploads"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    name = Column(String(200))
    source_format = Column(String(20))                    # CYCLONEDX | SPDX | CSV
    target_platform = Column(String(50), nullable=True)   # e.g. "F-35A" — scopes fleet impact
    target_tail_number = Column(String(20), nullable=True)
    component_count = Column(Integer, default=0)
    matched_part_count = Column(Integer, default=0)       # components that hit an existing Part
    matched_supplier_count = Column(Integer, default=0)
    cve_count = Column(Integer, default=0)
    critical_cve_count = Column(Integer, default=0)
    max_cvss = Column(Float, default=0.0)
    risk_score = Column(Float, default=0.0)               # 0..100 aggregate
    affected_aircraft_count = Column(Integer, default=0)
    affected_tails = Column(Text, nullable=True)          # JSON list[str]
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)

    components = relationship("BomComponent", back_populates="upload", cascade="all, delete-orphan")


class BomComponent(Base):
    """A single line item parsed from a BOM."""
    __tablename__ = "bom_components"
    id = Column(Integer, primary_key=True, index=True)
    bom_upload_id = Column(Integer, ForeignKey("bom_uploads.id"), index=True)

    # Identity (from the BOM)
    name = Column(String(300))
    vendor = Column(String(200), nullable=True)
    version = Column(String(80), nullable=True)
    purl = Column(String(500), nullable=True)             # CycloneDX purl
    cpe = Column(String(500), nullable=True)              # CPE 2.3 if available
    part_number_raw = Column(String(80), nullable=True)   # if the BOM listed one

    # Catalog match
    matched_part_id = Column(Integer, ForeignKey("parts.id"), nullable=True, index=True)
    matched_supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True, index=True)
    match_confidence = Column(Float, default=0.0)
    matched_on = Column(String(80), nullable=True)        # "part_number" | "name" | "vendor+product"

    # Enrichment
    cve_count = Column(Integer, default=0)
    critical_cve_count = Column(Integer, default=0)
    max_cvss = Column(Float, default=0.0)
    kev_listed = Column(Boolean, default=False)
    cves_json = Column(Text, nullable=True)               # JSON list of CVE refs

    upload = relationship("BomUpload", back_populates="components")


class NotificationLog(Base):
    """Audit trail for outbound notifications. One row per dispatch attempt."""
    __tablename__ = "notification_logs"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    channel = Column(String(30), index=True)              # webhook | slack | console | email
    target = Column(String(500))                          # URL, channel name, address — redacted at display time
    scenario_id = Column(Integer, ForeignKey("impact_scenarios.id"), nullable=True)
    signal_id = Column(Integer, ForeignKey("supplier_intel_signals.id"), nullable=True)
    status = Column(String(20))                           # SENT | FAILED | SKIPPED
    error = Column(Text, nullable=True)
    payload_preview = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
