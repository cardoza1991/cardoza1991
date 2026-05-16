from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class AircraftBase(BaseModel):
    tail_number: str
    platform: str
    squadron: str
    base_location: str
    mission_status: str
    flight_hours_total: float


class AircraftOut(AircraftBase):
    id: int
    last_maintenance_date: Optional[datetime]
    next_scheduled_maintenance: Optional[datetime]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class SupplierBase(BaseModel):
    name: str
    country: str
    reliability_score: float
    avg_lead_time_days: int
    on_time_delivery_rate: float
    defect_rate: float
    single_source_parts_count: int
    is_approved: bool


class SupplierOut(SupplierBase):
    id: int
    last_audit_date: Optional[datetime]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class PartBase(BaseModel):
    part_number: str
    name: str
    description: Optional[str]
    platform_compatibility: Optional[str]
    unit_cost: Optional[float]
    lead_time_days: int
    lead_time_variance_days: int
    is_mission_critical: bool
    is_single_source: bool
    category: Optional[str]


class PartOut(PartBase):
    id: int
    supplier_id: Optional[int]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class InventoryOut(BaseModel):
    id: int
    part_id: int
    quantity_on_hand: int
    quantity_on_order: int
    reorder_point: int
    reorder_quantity: int
    warehouse_location: Optional[str]
    avg_monthly_consumption: float
    last_updated: Optional[datetime]

    class Config:
        from_attributes = True


class PurchaseOrderOut(BaseModel):
    id: int
    po_number: str
    part_id: int
    supplier_id: int
    quantity_ordered: int
    unit_price: float
    order_date: Optional[datetime]
    expected_delivery_date: Optional[datetime]
    actual_delivery_date: Optional[datetime]
    status: str
    delay_days: int
    delay_reason: Optional[str]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class MaintenanceEventOut(BaseModel):
    id: int
    aircraft_id: int
    part_id: Optional[int]
    event_type: str
    description: Optional[str]
    scheduled_date: Optional[datetime]
    completed_date: Optional[datetime]
    status: str
    technician: Optional[str]
    requires_part: bool
    part_available: bool
    downtime_hours: float
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class RiskScoreOut(BaseModel):
    id: int
    aircraft_id: Optional[int]
    part_id: Optional[int]
    supplier_id: Optional[int]
    risk_type: str
    score: float
    shortage_probability: float
    lead_time_volatility: float
    supplier_reliability_risk: float
    mission_criticality: float
    historical_failure_rate: float
    confidence_level: float
    days_to_event: Optional[int]
    explanation: Optional[str]
    computed_at: Optional[datetime]

    class Config:
        from_attributes = True


class AgentRecommendationOut(BaseModel):
    id: int
    title: str
    recommendation_type: str
    priority: str
    aircraft_affected: Optional[str]
    part_affected: Optional[str]
    supplier_affected: Optional[str]
    description: Optional[str]
    rationale: Optional[str]
    estimated_impact: Optional[str]
    action_steps: Optional[str]
    status: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class QueryRequest(BaseModel):
    query: str


class AtRiskAircraftDetail(BaseModel):
    tail_number: str
    platform: str
    squadron: str
    mission_status: str
    days_to_nmc: Optional[int]
    risk_score: float
    root_cause: str
    blocking_part: Optional[str]
    supplier: Optional[str]
    po_status: Optional[str]
    mitigation: List[str]


class QueryResponse(BaseModel):
    query: str
    response: dict
