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
    signal_type = Column(String(40), index=True)     # SANCTION | CVE | ADVISORY | CYBER_INCIDENT | NEWS
    severity = Column(String(20))                    # CRITICAL | HIGH | MEDIUM | LOW
    score_weight = Column(Float, default=0.0)        # 0..1 contribution to intel risk component

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
