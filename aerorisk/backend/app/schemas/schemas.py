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
    last_maintenance_date: Optional[datetime] = None
    next_scheduled_maintenance: Optional[datetime] = None


class AircraftOut(AircraftBase):
    id: int
    created_at: Optional[datetime] = None
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None

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
    last_audit_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    risk_score: Optional[float] = None
    intel_signal_count: Optional[int] = 0
    intel_contribution: Optional[float] = 0.0

    class Config:
        from_attributes = True


class SupplierIntelSignalOut(BaseModel):
    id: int
    supplier_id: Optional[int] = None
    source: str
    source_ref: str
    signal_type: str
    severity: str
    title: str
    body: Optional[str] = None
    link: Optional[str] = None
    observed_at: Optional[datetime] = None
    fetched_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: bool = True
    match_confidence: float = 0.0
    matched_on: Optional[str] = None
    score_weight: float = 0.0
    supplier_name: Optional[str] = None

    class Config:
        from_attributes = True


class IntelCycleSummary(BaseModel):
    fetched: int
    matched: int
    new_signals: int
    updated_signals: int
    unmatched: int
    by_source: dict
    new_critical_signal_ids: list[int]


class InventoryOut(BaseModel):
    id: int
    part_id: int
    quantity_on_hand: int
    quantity_on_order: int
    reorder_point: int
    reorder_quantity: int
    warehouse_location: Optional[str] = None
    avg_monthly_consumption: float
    last_updated: Optional[datetime] = None

    class Config:
        from_attributes = True


class PartBase(BaseModel):
    part_number: str
    name: str
    description: Optional[str] = None
    platform_compatibility: Optional[str] = None
    unit_cost: Optional[float] = None
    lead_time_days: int
    lead_time_variance_days: int
    is_mission_critical: bool
    is_single_source: bool
    category: str


class PartOut(PartBase):
    id: int
    supplier_id: Optional[int] = None
    created_at: Optional[datetime] = None
    inventory: Optional[InventoryOut] = None
    risk_score: Optional[float] = None
    stockout_days: Optional[int] = None
    supplier_name: Optional[str] = None

    class Config:
        from_attributes = True


class PurchaseOrderOut(BaseModel):
    id: int
    po_number: str
    part_id: int
    supplier_id: int
    quantity_ordered: int
    unit_price: float
    order_date: Optional[datetime] = None
    expected_delivery_date: Optional[datetime] = None
    actual_delivery_date: Optional[datetime] = None
    status: str
    delay_days: int
    delay_reason: Optional[str] = None
    part_number: Optional[str] = None
    part_name: Optional[str] = None
    supplier_name: Optional[str] = None

    class Config:
        from_attributes = True


class MaintenanceEventOut(BaseModel):
    id: int
    aircraft_id: int
    part_id: Optional[int] = None
    event_type: str
    description: str
    scheduled_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    status: str
    technician: str
    requires_part: bool
    part_available: bool
    downtime_hours: float
    part_number: Optional[str] = None
    part_name: Optional[str] = None

    class Config:
        from_attributes = True


class RiskScoreOut(BaseModel):
    id: int
    aircraft_id: Optional[int] = None
    part_id: Optional[int] = None
    supplier_id: Optional[int] = None
    risk_type: str
    score: float
    shortage_probability: float
    lead_time_volatility: float
    supplier_reliability_risk: float
    mission_criticality: float
    historical_failure_rate: float
    confidence_level: float
    days_to_event: Optional[int] = None
    explanation: Optional[str] = None
    computed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AgentRecommendationOut(BaseModel):
    id: int
    title: str
    recommendation_type: str
    priority: str
    aircraft_affected: Optional[str] = None
    part_affected: Optional[str] = None
    supplier_affected: Optional[str] = None
    description: str
    rationale: Optional[str] = None
    estimated_impact: Optional[str] = None
    action_steps: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AgentQueryRequest(BaseModel):
    query: str


class NMCForecastItem(BaseModel):
    tail_number: str
    platform: str
    squadron: str
    current_status: str
    days_to_nmc: int
    risk_score: float
    root_cause: str
    blocking_part: Optional[str] = None
    supplier: Optional[str] = None
    po_status: Optional[str] = None
    mitigation: List[str] = []


class AgentQueryResponse(BaseModel):
    query: str
    response: dict


class ReadinessSummary(BaseModel):
    total: int
    fmc: int
    pmc: int
    nmc: int
    at_risk: int
    readiness_percentage: float
