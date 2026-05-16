from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
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

    parts = relationship("Part", back_populates="supplier")
    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")


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
