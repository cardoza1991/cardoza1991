from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..models.models import (
    Aircraft, Supplier, Part, Inventory, PurchaseOrder,
    MaintenanceEvent, FlightSchedule, RiskScore, AgentRecommendation
)
import json


def seed_database(db: Session):
    """Seed the database with realistic aerospace demo data if tables are empty."""
    if db.query(Aircraft).count() > 0:
        return

    now = datetime.utcnow()

    # -------------------------------------------------------------------------
    # SUPPLIERS
    # -------------------------------------------------------------------------
    suppliers_data = [
        {
            "name": "Lockheed Defense Systems",
            "country": "USA",
            "reliability_score": 0.92,
            "avg_lead_time_days": 45,
            "on_time_delivery_rate": 0.89,
            "defect_rate": 0.01,
            "single_source_parts_count": 8,
            "is_approved": True,
            "last_audit_date": now - timedelta(days=90),
            "aliases": json.dumps(["Lockheed Martin", "LMCO"]),
            "domain": "lockheedmartin.com",
            "keywords": json.dumps(["Lockheed", "Lockheed Martin"]),
        },
        {
            "name": "Raytheon Avionics Corp",
            "country": "USA",
            "reliability_score": 0.88,
            "avg_lead_time_days": 60,
            "on_time_delivery_rate": 0.82,
            "defect_rate": 0.02,
            "single_source_parts_count": 12,
            "is_approved": True,
            "last_audit_date": now - timedelta(days=120),
            "aliases": json.dumps(["Raytheon Technologies", "RTX"]),
            "domain": "rtx.com",
            "keywords": json.dumps(["Raytheon", "RTX"]),
        },
        {
            "name": "Collins Aerospace Solutions",
            "country": "USA",
            "reliability_score": 0.95,
            "avg_lead_time_days": 30,
            "on_time_delivery_rate": 0.94,
            "defect_rate": 0.008,
            "single_source_parts_count": 5,
            "is_approved": True,
            "last_audit_date": now - timedelta(days=60),
            "aliases": json.dumps(["Collins Aerospace", "Rockwell Collins"]),
            "domain": "collinsaerospace.com",
            "keywords": json.dumps(["Collins Aerospace", "ARINC 615A"]),
        },
        {
            "name": "GE Aviation Components",
            "country": "USA",
            "reliability_score": 0.91,
            "avg_lead_time_days": 90,
            "on_time_delivery_rate": 0.88,
            "defect_rate": 0.015,
            "single_source_parts_count": 6,
            "is_approved": True,
            "last_audit_date": now - timedelta(days=180),
            "aliases": json.dumps(["GE Aerospace", "General Electric Aviation"]),
            "domain": "geaerospace.com",
            "keywords": json.dumps(["GE", "GE Aviation", "Aviation Engine Diagnostic"]),
        },
        {
            "name": "Moog Hydraulic Systems",
            "country": "USA",
            "reliability_score": 0.72,
            "avg_lead_time_days": 60,
            "on_time_delivery_rate": 0.61,
            "defect_rate": 0.035,
            "single_source_parts_count": 4,
            "is_approved": True,
            "last_audit_date": now - timedelta(days=240),
            "aliases": json.dumps(["Moog Inc", "Hydraulic Equipment LLC"]),
            "domain": "moog.com",
            "keywords": json.dumps(["Moog", "DS2020 Servo Drive"]),
        },
        {
            "name": "Honeywell Aerospace Tech",
            "country": "USA",
            "reliability_score": 0.87,
            "avg_lead_time_days": 35,
            "on_time_delivery_rate": 0.91,
            "defect_rate": 0.012,
            "single_source_parts_count": 7,
            "is_approved": True,
            "last_audit_date": now - timedelta(days=45),
            "aliases": json.dumps(["Honeywell International", "Honeywell"]),
            "domain": "honeywell.com",
            "keywords": json.dumps(["Honeywell", "Experion PKS"]),
        },
        {
            "name": "TransDigm Precision Parts",
            "country": "USA",
            "reliability_score": 0.78,
            "avg_lead_time_days": 75,
            "on_time_delivery_rate": 0.74,
            "defect_rate": 0.028,
            "single_source_parts_count": 9,
            "is_approved": True,
            "last_audit_date": now - timedelta(days=300),
            "aliases": json.dumps(["TransDigm Group", "Pacific Rim Avionics Trading"]),
            "domain": "transdigm.com",
            "keywords": json.dumps(["TransDigm"]),
        },
        {
            "name": "Safran Landing Systems",
            "country": "France",
            "reliability_score": 0.83,
            "avg_lead_time_days": 80,
            "on_time_delivery_rate": 0.79,
            "defect_rate": 0.022,
            "single_source_parts_count": 3,
            "is_approved": True,
            "last_audit_date": now - timedelta(days=150),
            "aliases": json.dumps(["Safran", "Safran Group"]),
            "domain": "safran-group.com",
            "keywords": json.dumps(["Safran", "Landing Gear Maintenance Tool"]),
        },
    ]

    suppliers = []
    for s_data in suppliers_data:
        s = Supplier(**s_data)
        db.add(s)
        suppliers.append(s)
    db.flush()

    # -------------------------------------------------------------------------
    # PARTS  (35 parts across categories)
    # -------------------------------------------------------------------------
    parts_data = [
        # --- Avionics ---
        {
            "part_number": "LRU-F35-001",
            "name": "F-35A Mission Computer LRU",
            "description": "Line Replaceable Unit — primary mission computer for F-35A avionics suite",
            "platform_compatibility": "F-35A",
            "supplier_id": suppliers[1].id,   # Raytheon — high lead time, low on-time
            "unit_cost": 245000.0,
            "lead_time_days": 45,
            "lead_time_variance_days": 18,
            "is_mission_critical": True,
            "is_single_source": True,
            "category": "Avionics",
        },
        {
            "part_number": "ANT-F35-002",
            "name": "F-35A AN/APG-81 AESA Radar Module",
            "description": "Active electronically scanned array radar replacement module",
            "platform_compatibility": "F-35A",
            "supplier_id": suppliers[1].id,
            "unit_cost": 380000.0,
            "lead_time_days": 90,
            "lead_time_variance_days": 20,
            "is_mission_critical": True,
            "is_single_source": True,
            "category": "Avionics",
        },
        {
            "part_number": "IFF-MULTI-003",
            "name": "AN/APX-123 IFF Transponder",
            "description": "Identification Friend or Foe transponder, multi-platform",
            "platform_compatibility": "F-35A,F/A-18E,F/A-18F",
            "supplier_id": suppliers[0].id,
            "unit_cost": 42000.0,
            "lead_time_days": 30,
            "lead_time_variance_days": 7,
            "is_mission_critical": True,
            "is_single_source": False,
            "category": "Avionics",
        },
        {
            "part_number": "RWR-F18-004",
            "name": "AN/ALR-67(V)3 Radar Warning Receiver",
            "description": "Radar warning receiver for threat detection",
            "platform_compatibility": "F/A-18E,F/A-18F",
            "supplier_id": suppliers[5].id,
            "unit_cost": 89000.0,
            "lead_time_days": 35,
            "lead_time_variance_days": 8,
            "is_mission_critical": True,
            "is_single_source": False,
            "category": "Avionics",
        },
        {
            "part_number": "HUD-F18-005",
            "name": "F/A-18 Head-Up Display Assembly",
            "description": "HUD optical combiner and display processor assembly",
            "platform_compatibility": "F/A-18E,F/A-18F",
            "supplier_id": suppliers[2].id,
            "unit_cost": 65000.0,
            "lead_time_days": 28,
            "lead_time_variance_days": 5,
            "is_mission_critical": False,
            "is_single_source": False,
            "category": "Avionics",
        },
        # --- Engine ---
        {
            "part_number": "ENG-C130-006",
            "name": "C-130J Rolls-Royce AE2100D3 Turboprop Power Section",
            "description": "Complete power turbine section assembly for C-130J propulsion",
            "platform_compatibility": "C-130J",
            "supplier_id": suppliers[3].id,   # GE Aviation — long lead time
            "unit_cost": 1850000.0,
            "lead_time_days": 120,
            "lead_time_variance_days": 30,
            "is_mission_critical": True,
            "is_single_source": True,
            "category": "Engine",
        },
        {
            "part_number": "ENG-C130-007",
            "name": "C-130J Propeller Gearbox Assembly",
            "description": "Reduction gearbox connecting turboprop to 6-blade propeller",
            "platform_compatibility": "C-130J",
            "supplier_id": suppliers[3].id,
            "unit_cost": 420000.0,
            "lead_time_days": 90,
            "lead_time_variance_days": 21,
            "is_mission_critical": True,
            "is_single_source": False,
            "category": "Engine",
        },
        {
            "part_number": "HPT-F35-008",
            "name": "F135 High-Pressure Turbine Blade Set",
            "description": "Pratt & Whitney F135 HPT blade set, 48-blade configuration",
            "platform_compatibility": "F-35A",
            "supplier_id": suppliers[0].id,
            "unit_cost": 320000.0,
            "lead_time_days": 60,
            "lead_time_variance_days": 14,
            "is_mission_critical": True,
            "is_single_source": False,
            "category": "Engine",
        },
        {
            "part_number": "FADEC-F18-009",
            "name": "F/A-18 FADEC Control Unit",
            "description": "Full Authority Digital Engine Control — GE F414 engine",
            "platform_compatibility": "F/A-18E,F/A-18F",
            "supplier_id": suppliers[5].id,
            "unit_cost": 175000.0,
            "lead_time_days": 40,
            "lead_time_variance_days": 10,
            "is_mission_critical": True,
            "is_single_source": False,
            "category": "Engine",
        },
        {
            "part_number": "ENG-MH60-010",
            "name": "MH-60R T700-GE-401C Engine Module",
            "description": "GE T700 turboshaft engine hot-section module",
            "platform_compatibility": "MH-60R",
            "supplier_id": suppliers[3].id,
            "unit_cost": 980000.0,
            "lead_time_days": 100,
            "lead_time_variance_days": 25,
            "is_mission_critical": True,
            "is_single_source": False,
            "category": "Engine",
        },
        # --- Hydraulics ---
        {
            "part_number": "HYD-F18-011",
            "name": "F/A-18E Flight Control Hydraulic Actuator",
            "description": "Primary flight control surface actuator — port wing",
            "platform_compatibility": "F/A-18E,F/A-18F",
            "supplier_id": suppliers[4].id,   # Moog — low reliability, poor on-time
            "unit_cost": 58000.0,
            "lead_time_days": 60,
            "lead_time_variance_days": 22,
            "is_mission_critical": True,
            "is_single_source": False,
            "category": "Hydraulics",
        },
        {
            "part_number": "HYD-F35-012",
            "name": "F-35A EHA Electro-Hydraulic Actuator",
            "description": "Electro-hydrostatic actuator for F-35 flight controls",
            "platform_compatibility": "F-35A",
            "supplier_id": suppliers[4].id,
            "unit_cost": 95000.0,
            "lead_time_days": 55,
            "lead_time_variance_days": 15,
            "is_mission_critical": True,
            "is_single_source": True,
            "category": "Hydraulics",
        },
        {
            "part_number": "HYD-C130-013",
            "name": "C-130J Landing Gear Hydraulic Pump",
            "description": "Engine-driven hydraulic pump for landing gear system",
            "platform_compatibility": "C-130J",
            "supplier_id": suppliers[4].id,
            "unit_cost": 34000.0,
            "lead_time_days": 45,
            "lead_time_variance_days": 12,
            "is_mission_critical": False,
            "is_single_source": False,
            "category": "Hydraulics",
        },
        {
            "part_number": "HYD-MH60-014",
            "name": "MH-60R Tail Rotor Servo Actuator",
            "description": "Hydraulic servo actuator for anti-torque tail rotor",
            "platform_compatibility": "MH-60R",
            "supplier_id": suppliers[6].id,
            "unit_cost": 28000.0,
            "lead_time_days": 75,
            "lead_time_variance_days": 20,
            "is_mission_critical": True,
            "is_single_source": False,
            "category": "Hydraulics",
        },
        {
            "part_number": "HYD-MULTI-015",
            "name": "29SI Hydraulic Fluid Reservoir Assembly",
            "description": "High-pressure hydraulic reservoir, multi-platform compatible",
            "platform_compatibility": "F/A-18E,F/A-18F,C-130J",
            "supplier_id": suppliers[2].id,
            "unit_cost": 8500.0,
            "lead_time_days": 21,
            "lead_time_variance_days": 5,
            "is_mission_critical": False,
            "is_single_source": False,
            "category": "Hydraulics",
        },
        # --- Landing Gear ---
        {
            "part_number": "LG-F35-016",
            "name": "F-35A Main Landing Gear Strut Assembly",
            "description": "Oleo-pneumatic main gear strut with carbon-ceramic brake",
            "platform_compatibility": "F-35A",
            "supplier_id": suppliers[7].id,
            "unit_cost": 185000.0,
            "lead_time_days": 80,
            "lead_time_variance_days": 20,
            "is_mission_critical": False,
            "is_single_source": False,
            "category": "Landing Gear",
        },
        {
            "part_number": "LG-F18-017",
            "name": "F/A-18E Nose Gear Steering Unit",
            "description": "Electrohydraulic nose wheel steering control unit",
            "platform_compatibility": "F/A-18E,F/A-18F",
            "supplier_id": suppliers[7].id,
            "unit_cost": 47000.0,
            "lead_time_days": 60,
            "lead_time_variance_days": 15,
            "is_mission_critical": False,
            "is_single_source": False,
            "category": "Landing Gear",
        },
        {
            "part_number": "BRAKE-F35-018",
            "name": "F-35A Carbon-Ceramic Brake Assembly",
            "description": "Carbon-ceramic composite brake disc and caliper assembly",
            "platform_compatibility": "F-35A",
            "supplier_id": suppliers[6].id,
            "unit_cost": 32000.0,
            "lead_time_days": 45,
            "lead_time_variance_days": 10,
            "is_mission_critical": False,
            "is_single_source": False,
            "category": "Landing Gear",
        },
        {
            "part_number": "TIRE-MULTI-019",
            "name": "Aircraft Tire 40x14 Type VII",
            "description": "High-performance aircraft tire for fighter/attack platforms",
            "platform_compatibility": "F-35A,F/A-18E,F/A-18F",
            "supplier_id": suppliers[2].id,
            "unit_cost": 2800.0,
            "lead_time_days": 14,
            "lead_time_variance_days": 3,
            "is_mission_critical": False,
            "is_single_source": False,
            "category": "Landing Gear",
        },
        # --- ECS (Environmental Control System) ---
        {
            "part_number": "ECS-F35-020",
            "name": "F-35A Integrated Power Package",
            "description": "Combined APU, ECS and power generation package",
            "platform_compatibility": "F-35A",
            "supplier_id": suppliers[5].id,
            "unit_cost": 320000.0,
            "lead_time_days": 70,
            "lead_time_variance_days": 18,
            "is_mission_critical": True,
            "is_single_source": True,
            "category": "ECS",
        },
        {
            "part_number": "ECS-F18-021",
            "name": "F/A-18E Environmental Control System Pack",
            "description": "Air cycle machine and heat exchanger assembly",
            "platform_compatibility": "F/A-18E,F/A-18F",
            "supplier_id": suppliers[5].id,
            "unit_cost": 78000.0,
            "lead_time_days": 35,
            "lead_time_variance_days": 8,
            "is_mission_critical": False,
            "is_single_source": False,
            "category": "ECS",
        },
        {
            "part_number": "ECS-C130-022",
            "name": "C-130J Pressurization Control Valve",
            "description": "Outflow valve for cabin pressurization system",
            "platform_compatibility": "C-130J",
            "supplier_id": suppliers[2].id,
            "unit_cost": 12500.0,
            "lead_time_days": 25,
            "lead_time_variance_days": 5,
            "is_mission_critical": False,
            "is_single_source": False,
            "category": "ECS",
        },
        {
            "part_number": "OBOGS-MULTI-023",
            "name": "On-Board Oxygen Generating System Concentrator",
            "description": "OBOGS concentrator assembly for pilot life support",
            "platform_compatibility": "F-35A,F/A-18E,F/A-18F",
            "supplier_id": suppliers[5].id,
            "unit_cost": 18500.0,
            "lead_time_days": 30,
            "lead_time_variance_days": 7,
            "is_mission_critical": True,
            "is_single_source": False,
            "category": "ECS",
        },
        # --- Structural ---
        {
            "part_number": "STR-F35-024",
            "name": "F-35A Composite Wing Access Panel",
            "description": "Carbon-fiber reinforced polymer lower wing access panel",
            "platform_compatibility": "F-35A",
            "supplier_id": suppliers[0].id,
            "unit_cost": 24000.0,
            "lead_time_days": 30,
            "lead_time_variance_days": 7,
            "is_mission_critical": False,
            "is_single_source": False,
            "category": "Structural",
        },
        {
            "part_number": "STR-MH60-025",
            "name": "MH-60R Main Rotor Head Assembly",
            "description": "Elastomeric bearing main rotor head with folding mechanism",
            "platform_compatibility": "MH-60R",
            "supplier_id": suppliers[6].id,
            "unit_cost": 650000.0,
            "lead_time_days": 90,
            "lead_time_variance_days": 25,
            "is_mission_critical": True,
            "is_single_source": True,
            "category": "Structural",
        },
        # --- Electrical / Power ---
        {
            "part_number": "ELEC-F35-026",
            "name": "F-35A Integrated Drive Generator",
            "description": "270V DC variable-speed constant frequency IDG",
            "platform_compatibility": "F-35A",
            "supplier_id": suppliers[5].id,
            "unit_cost": 145000.0,
            "lead_time_days": 50,
            "lead_time_variance_days": 12,
            "is_mission_critical": True,
            "is_single_source": False,
            "category": "Electrical",
        },
        {
            "part_number": "ELEC-C130-027",
            "name": "C-130J AC Power Distribution Panel",
            "description": "115V 400Hz AC power distribution panel assembly",
            "platform_compatibility": "C-130J",
            "supplier_id": suppliers[2].id,
            "unit_cost": 35000.0,
            "lead_time_days": 28,
            "lead_time_variance_days": 6,
            "is_mission_critical": False,
            "is_single_source": False,
            "category": "Electrical",
        },
        {
            "part_number": "ELEC-MH60-028",
            "name": "MH-60R AN/APS-153 Radar Processor",
            "description": "Multimode radar signal processor for maritime search",
            "platform_compatibility": "MH-60R",
            "supplier_id": suppliers[1].id,
            "unit_cost": 225000.0,
            "lead_time_days": 65,
            "lead_time_variance_days": 18,
            "is_mission_critical": True,
            "is_single_source": True,
            "category": "Avionics",
        },
        # --- Fuel System ---
        {
            "part_number": "FUEL-F18-029",
            "name": "F/A-18E In-Flight Refueling Probe",
            "description": "Fixed-probe in-flight refueling assembly",
            "platform_compatibility": "F/A-18E",
            "supplier_id": suppliers[2].id,
            "unit_cost": 28000.0,
            "lead_time_days": 25,
            "lead_time_variance_days": 5,
            "is_mission_critical": False,
            "is_single_source": False,
            "category": "Fuel System",
        },
        {
            "part_number": "FUEL-C130-030",
            "name": "C-130J Wing Fuel Boost Pump",
            "description": "Submerged centrifugal fuel boost pump",
            "platform_compatibility": "C-130J",
            "supplier_id": suppliers[2].id,
            "unit_cost": 9800.0,
            "lead_time_days": 20,
            "lead_time_variance_days": 4,
            "is_mission_critical": False,
            "is_single_source": False,
            "category": "Fuel System",
        },
        # --- Communications ---
        {
            "part_number": "COM-MULTI-031",
            "name": "AN/ARC-210 Multiband Radio",
            "description": "30-400 MHz multiband airborne communications radio",
            "platform_compatibility": "F-35A,F/A-18E,F/A-18F,C-130J,MH-60R",
            "supplier_id": suppliers[5].id,
            "unit_cost": 55000.0,
            "lead_time_days": 30,
            "lead_time_variance_days": 7,
            "is_mission_critical": True,
            "is_single_source": False,
            "category": "Communications",
        },
        {
            "part_number": "COM-F35-032",
            "name": "F-35A CNI System Processor",
            "description": "Communications, Navigation and Identification integrated processor",
            "platform_compatibility": "F-35A",
            "supplier_id": suppliers[1].id,
            "unit_cost": 195000.0,
            "lead_time_days": 55,
            "lead_time_variance_days": 15,
            "is_mission_critical": True,
            "is_single_source": True,
            "category": "Communications",
        },
        # --- Weapons/Stores ---
        {
            "part_number": "WPNS-F35-033",
            "name": "F-35A Internal Weapons Bay Door Actuator",
            "description": "High-speed rotary actuator for internal bay doors",
            "platform_compatibility": "F-35A",
            "supplier_id": suppliers[6].id,
            "unit_cost": 42000.0,
            "lead_time_days": 50,
            "lead_time_variance_days": 12,
            "is_mission_critical": False,
            "is_single_source": False,
            "category": "Weapons/Stores",
        },
        {
            "part_number": "WPNS-F18-034",
            "name": "F/A-18 BRU-32 Bomb Rack Unit",
            "description": "Multiple ejector rack for stores management",
            "platform_compatibility": "F/A-18E,F/A-18F",
            "supplier_id": suppliers[0].id,
            "unit_cost": 18500.0,
            "lead_time_days": 25,
            "lead_time_variance_days": 5,
            "is_mission_critical": False,
            "is_single_source": False,
            "category": "Weapons/Stores",
        },
        {
            "part_number": "SENSOR-MH60-035",
            "name": "MH-60R AAS-44C FLIR/Laser Turret",
            "description": "Forward-looking infrared and laser designator turret",
            "platform_compatibility": "MH-60R",
            "supplier_id": suppliers[1].id,
            "unit_cost": 875000.0,
            "lead_time_days": 120,
            "lead_time_variance_days": 30,
            "is_mission_critical": True,
            "is_single_source": True,
            "category": "Sensors",
        },
    ]

    parts = []
    for p_data in parts_data:
        p = Part(**p_data)
        db.add(p)
        parts.append(p)
    db.flush()

    # Create part lookup by part_number
    part_by_num = {p.part_number: p for p in parts}

    # -------------------------------------------------------------------------
    # INVENTORY  (some critically low)
    # -------------------------------------------------------------------------
    inventory_data = [
        # LRU-F35-001 — CRITICALLY LOW (1 unit), reorder point 3 — DEMO SCENARIO 1
        {"part_id": part_by_num["LRU-F35-001"].id, "quantity_on_hand": 1, "quantity_on_order": 2,
         "reorder_point": 3, "reorder_quantity": 5, "warehouse_location": "BLDG-A-01", "avg_monthly_consumption": 0.8},
        # ANT-F35-002
        {"part_id": part_by_num["ANT-F35-002"].id, "quantity_on_hand": 3, "quantity_on_order": 1,
         "reorder_point": 2, "reorder_quantity": 3, "warehouse_location": "BLDG-A-02", "avg_monthly_consumption": 0.3},
        # IFF-MULTI-003
        {"part_id": part_by_num["IFF-MULTI-003"].id, "quantity_on_hand": 8, "quantity_on_order": 0,
         "reorder_point": 4, "reorder_quantity": 6, "warehouse_location": "BLDG-A-03", "avg_monthly_consumption": 1.2},
        # RWR-F18-004
        {"part_id": part_by_num["RWR-F18-004"].id, "quantity_on_hand": 5, "quantity_on_order": 0,
         "reorder_point": 3, "reorder_quantity": 4, "warehouse_location": "BLDG-B-01", "avg_monthly_consumption": 0.9},
        # HUD-F18-005
        {"part_id": part_by_num["HUD-F18-005"].id, "quantity_on_hand": 6, "quantity_on_order": 0,
         "reorder_point": 3, "reorder_quantity": 4, "warehouse_location": "BLDG-B-02", "avg_monthly_consumption": 0.6},
        # ENG-C130-006 — CRITICALLY LOW (2 units), reorder point 3 — DEMO SCENARIO 3
        {"part_id": part_by_num["ENG-C130-006"].id, "quantity_on_hand": 2, "quantity_on_order": 1,
         "reorder_point": 3, "reorder_quantity": 4, "warehouse_location": "BLDG-C-01", "avg_monthly_consumption": 0.6},
        # ENG-C130-007
        {"part_id": part_by_num["ENG-C130-007"].id, "quantity_on_hand": 4, "quantity_on_order": 2,
         "reorder_point": 3, "reorder_quantity": 4, "warehouse_location": "BLDG-C-02", "avg_monthly_consumption": 0.5},
        # HPT-F35-008
        {"part_id": part_by_num["HPT-F35-008"].id, "quantity_on_hand": 6, "quantity_on_order": 0,
         "reorder_point": 4, "reorder_quantity": 6, "warehouse_location": "BLDG-C-03", "avg_monthly_consumption": 0.7},
        # FADEC-F18-009
        {"part_id": part_by_num["FADEC-F18-009"].id, "quantity_on_hand": 4, "quantity_on_order": 2,
         "reorder_point": 3, "reorder_quantity": 4, "warehouse_location": "BLDG-C-04", "avg_monthly_consumption": 0.5},
        # ENG-MH60-010
        {"part_id": part_by_num["ENG-MH60-010"].id, "quantity_on_hand": 3, "quantity_on_order": 0,
         "reorder_point": 2, "reorder_quantity": 3, "warehouse_location": "BLDG-C-05", "avg_monthly_consumption": 0.4},
        # HYD-F18-011 — ZERO STOCK — DEMO SCENARIO 2
        {"part_id": part_by_num["HYD-F18-011"].id, "quantity_on_hand": 0, "quantity_on_order": 3,
         "reorder_point": 2, "reorder_quantity": 4, "warehouse_location": "BLDG-D-01", "avg_monthly_consumption": 1.1},
        # HYD-F35-012
        {"part_id": part_by_num["HYD-F35-012"].id, "quantity_on_hand": 3, "quantity_on_order": 0,
         "reorder_point": 2, "reorder_quantity": 3, "warehouse_location": "BLDG-D-02", "avg_monthly_consumption": 0.6},
        # HYD-C130-013
        {"part_id": part_by_num["HYD-C130-013"].id, "quantity_on_hand": 5, "quantity_on_order": 0,
         "reorder_point": 3, "reorder_quantity": 4, "warehouse_location": "BLDG-D-03", "avg_monthly_consumption": 0.7},
        # HYD-MH60-014
        {"part_id": part_by_num["HYD-MH60-014"].id, "quantity_on_hand": 4, "quantity_on_order": 0,
         "reorder_point": 2, "reorder_quantity": 3, "warehouse_location": "BLDG-D-04", "avg_monthly_consumption": 0.5},
        # HYD-MULTI-015
        {"part_id": part_by_num["HYD-MULTI-015"].id, "quantity_on_hand": 12, "quantity_on_order": 0,
         "reorder_point": 5, "reorder_quantity": 8, "warehouse_location": "BLDG-D-05", "avg_monthly_consumption": 1.5},
        # LG-F35-016
        {"part_id": part_by_num["LG-F35-016"].id, "quantity_on_hand": 2, "quantity_on_order": 1,
         "reorder_point": 2, "reorder_quantity": 3, "warehouse_location": "BLDG-E-01", "avg_monthly_consumption": 0.3},
        # LG-F18-017
        {"part_id": part_by_num["LG-F18-017"].id, "quantity_on_hand": 4, "quantity_on_order": 0,
         "reorder_point": 2, "reorder_quantity": 3, "warehouse_location": "BLDG-E-02", "avg_monthly_consumption": 0.4},
        # BRAKE-F35-018
        {"part_id": part_by_num["BRAKE-F35-018"].id, "quantity_on_hand": 8, "quantity_on_order": 0,
         "reorder_point": 4, "reorder_quantity": 6, "warehouse_location": "BLDG-E-03", "avg_monthly_consumption": 1.8},
        # TIRE-MULTI-019
        {"part_id": part_by_num["TIRE-MULTI-019"].id, "quantity_on_hand": 24, "quantity_on_order": 0,
         "reorder_point": 8, "reorder_quantity": 12, "warehouse_location": "BLDG-E-04", "avg_monthly_consumption": 3.2},
        # ECS-F35-020
        {"part_id": part_by_num["ECS-F35-020"].id, "quantity_on_hand": 2, "quantity_on_order": 1,
         "reorder_point": 2, "reorder_quantity": 3, "warehouse_location": "BLDG-F-01", "avg_monthly_consumption": 0.4},
        # ECS-F18-021
        {"part_id": part_by_num["ECS-F18-021"].id, "quantity_on_hand": 5, "quantity_on_order": 0,
         "reorder_point": 3, "reorder_quantity": 4, "warehouse_location": "BLDG-F-02", "avg_monthly_consumption": 0.7},
        # ECS-C130-022
        {"part_id": part_by_num["ECS-C130-022"].id, "quantity_on_hand": 6, "quantity_on_order": 0,
         "reorder_point": 3, "reorder_quantity": 4, "warehouse_location": "BLDG-F-03", "avg_monthly_consumption": 0.8},
        # OBOGS-MULTI-023
        {"part_id": part_by_num["OBOGS-MULTI-023"].id, "quantity_on_hand": 10, "quantity_on_order": 0,
         "reorder_point": 5, "reorder_quantity": 8, "warehouse_location": "BLDG-F-04", "avg_monthly_consumption": 1.3},
        # STR-F35-024
        {"part_id": part_by_num["STR-F35-024"].id, "quantity_on_hand": 7, "quantity_on_order": 0,
         "reorder_point": 3, "reorder_quantity": 5, "warehouse_location": "BLDG-G-01", "avg_monthly_consumption": 0.9},
        # STR-MH60-025
        {"part_id": part_by_num["STR-MH60-025"].id, "quantity_on_hand": 1, "quantity_on_order": 1,
         "reorder_point": 2, "reorder_quantity": 2, "warehouse_location": "BLDG-G-02", "avg_monthly_consumption": 0.2},
        # ELEC-F35-026
        {"part_id": part_by_num["ELEC-F35-026"].id, "quantity_on_hand": 4, "quantity_on_order": 0,
         "reorder_point": 2, "reorder_quantity": 3, "warehouse_location": "BLDG-H-01", "avg_monthly_consumption": 0.5},
        # ELEC-C130-027
        {"part_id": part_by_num["ELEC-C130-027"].id, "quantity_on_hand": 5, "quantity_on_order": 0,
         "reorder_point": 3, "reorder_quantity": 4, "warehouse_location": "BLDG-H-02", "avg_monthly_consumption": 0.6},
        # ELEC-MH60-028
        {"part_id": part_by_num["ELEC-MH60-028"].id, "quantity_on_hand": 2, "quantity_on_order": 0,
         "reorder_point": 2, "reorder_quantity": 3, "warehouse_location": "BLDG-H-03", "avg_monthly_consumption": 0.3},
        # FUEL-F18-029
        {"part_id": part_by_num["FUEL-F18-029"].id, "quantity_on_hand": 6, "quantity_on_order": 0,
         "reorder_point": 3, "reorder_quantity": 4, "warehouse_location": "BLDG-I-01", "avg_monthly_consumption": 0.7},
        # FUEL-C130-030
        {"part_id": part_by_num["FUEL-C130-030"].id, "quantity_on_hand": 8, "quantity_on_order": 0,
         "reorder_point": 4, "reorder_quantity": 6, "warehouse_location": "BLDG-I-02", "avg_monthly_consumption": 1.1},
        # COM-MULTI-031
        {"part_id": part_by_num["COM-MULTI-031"].id, "quantity_on_hand": 12, "quantity_on_order": 0,
         "reorder_point": 5, "reorder_quantity": 8, "warehouse_location": "BLDG-J-01", "avg_monthly_consumption": 1.4},
        # COM-F35-032
        {"part_id": part_by_num["COM-F35-032"].id, "quantity_on_hand": 2, "quantity_on_order": 1,
         "reorder_point": 2, "reorder_quantity": 3, "warehouse_location": "BLDG-J-02", "avg_monthly_consumption": 0.3},
        # WPNS-F35-033
        {"part_id": part_by_num["WPNS-F35-033"].id, "quantity_on_hand": 6, "quantity_on_order": 0,
         "reorder_point": 3, "reorder_quantity": 4, "warehouse_location": "BLDG-K-01", "avg_monthly_consumption": 0.8},
        # WPNS-F18-034
        {"part_id": part_by_num["WPNS-F18-034"].id, "quantity_on_hand": 14, "quantity_on_order": 0,
         "reorder_point": 6, "reorder_quantity": 8, "warehouse_location": "BLDG-K-02", "avg_monthly_consumption": 1.9},
        # SENSOR-MH60-035
        {"part_id": part_by_num["SENSOR-MH60-035"].id, "quantity_on_hand": 1, "quantity_on_order": 0,
         "reorder_point": 2, "reorder_quantity": 2, "warehouse_location": "BLDG-L-01", "avg_monthly_consumption": 0.2},
    ]

    for inv_data in inventory_data:
        inv = Inventory(**inv_data)
        db.add(inv)
    db.flush()

    # -------------------------------------------------------------------------
    # AIRCRAFT (12 aircraft)
    # -------------------------------------------------------------------------
    aircraft_data = [
        # F-35A wing — DEMO SCENARIO 1: AT_RISK due to LRU shortage
        {"tail_number": "AF-21-001", "platform": "F-35A", "squadron": "VFA-147 Argonauts",
         "base_location": "NAS Lemoore, CA", "mission_status": "AT_RISK",
         "flight_hours_total": 1847.3, "last_maintenance_date": now - timedelta(days=12),
         "next_scheduled_maintenance": now + timedelta(days=18)},
        {"tail_number": "AF-21-002", "platform": "F-35A", "squadron": "VFA-147 Argonauts",
         "base_location": "NAS Lemoore, CA", "mission_status": "FMC",
         "flight_hours_total": 2103.7, "last_maintenance_date": now - timedelta(days=5),
         "next_scheduled_maintenance": now + timedelta(days=55)},
        {"tail_number": "AF-21-003", "platform": "F-35A", "squadron": "VFA-147 Argonauts",
         "base_location": "NAS Lemoore, CA", "mission_status": "PMC",
         "flight_hours_total": 1620.8, "last_maintenance_date": now - timedelta(days=3),
         "next_scheduled_maintenance": now + timedelta(days=42)},
        # F/A-18E wing — DEMO SCENARIO 2: NMC due to hydraulic actuator (zero stock)
        {"tail_number": "NA-19-101", "platform": "F/A-18E", "squadron": "VFA-195 Dambusters",
         "base_location": "NAF Atsugi, Japan", "mission_status": "NMC",
         "flight_hours_total": 3284.1, "last_maintenance_date": now - timedelta(days=2),
         "next_scheduled_maintenance": now + timedelta(days=7)},
        {"tail_number": "NA-19-102", "platform": "F/A-18E", "squadron": "VFA-195 Dambusters",
         "base_location": "NAF Atsugi, Japan", "mission_status": "FMC",
         "flight_hours_total": 2891.5, "last_maintenance_date": now - timedelta(days=8),
         "next_scheduled_maintenance": now + timedelta(days=32)},
        {"tail_number": "NA-19-103", "platform": "F/A-18F", "squadron": "VFA-11 Red Rippers",
         "base_location": "NAS Oceana, VA", "mission_status": "FMC",
         "flight_hours_total": 1958.2, "last_maintenance_date": now - timedelta(days=15),
         "next_scheduled_maintenance": now + timedelta(days=45)},
        {"tail_number": "NA-19-104", "platform": "F/A-18F", "squadron": "VFA-11 Red Rippers",
         "base_location": "NAS Oceana, VA", "mission_status": "PMC",
         "flight_hours_total": 2214.9, "last_maintenance_date": now - timedelta(days=7),
         "next_scheduled_maintenance": now + timedelta(days=21)},
        # C-130J wing — DEMO SCENARIO 3: AT_RISK due to engine component
        {"tail_number": "AC-20-401", "platform": "C-130J", "squadron": "VR-64 Condors",
         "base_location": "JRB Fort Worth, TX", "mission_status": "AT_RISK",
         "flight_hours_total": 8741.2, "last_maintenance_date": now - timedelta(days=20),
         "next_scheduled_maintenance": now + timedelta(days=10)},
        {"tail_number": "AC-20-402", "platform": "C-130J", "squadron": "VR-64 Condors",
         "base_location": "JRB Fort Worth, TX", "mission_status": "FMC",
         "flight_hours_total": 7234.6, "last_maintenance_date": now - timedelta(days=30),
         "next_scheduled_maintenance": now + timedelta(days=60)},
        # MH-60R wing
        {"tail_number": "MH-22-601", "platform": "MH-60R", "squadron": "HSM-78 Blue Hawks",
         "base_location": "NAS North Island, CA", "mission_status": "FMC",
         "flight_hours_total": 1234.7, "last_maintenance_date": now - timedelta(days=6),
         "next_scheduled_maintenance": now + timedelta(days=24)},
        {"tail_number": "MH-22-602", "platform": "MH-60R", "squadron": "HSM-78 Blue Hawks",
         "base_location": "NAS North Island, CA", "mission_status": "PMC",
         "flight_hours_total": 980.3, "last_maintenance_date": now - timedelta(days=4),
         "next_scheduled_maintenance": now + timedelta(days=36)},
        {"tail_number": "MH-22-603", "platform": "MH-60R", "squadron": "HSM-35 Magicians",
         "base_location": "NAS North Island, CA", "mission_status": "FMC",
         "flight_hours_total": 1456.8, "last_maintenance_date": now - timedelta(days=10),
         "next_scheduled_maintenance": now + timedelta(days=50)},
    ]

    aircraft = []
    for a_data in aircraft_data:
        a = Aircraft(**a_data)
        db.add(a)
        aircraft.append(a)
    db.flush()

    aircraft_by_tail = {a.tail_number: a for a in aircraft}

    # -------------------------------------------------------------------------
    # PURCHASE ORDERS (15 POs)
    # -------------------------------------------------------------------------
    pos_data = [
        # DEMO SCENARIO 1: LRU-F35-001 PO — DELAYED 18 days
        {"po_number": "PO-2024-0891", "part_id": part_by_num["LRU-F35-001"].id,
         "supplier_id": suppliers[1].id, "quantity_ordered": 2, "unit_price": 245000.0,
         "order_date": now - timedelta(days=40), "expected_delivery_date": now + timedelta(days=5),
         "actual_delivery_date": None, "status": "DELAYED", "delay_days": 18,
         "delay_reason": "Supplier component shortage — FPGA procurement delay from Taiwan fab"},
        # DEMO SCENARIO 2: HYD-F18-011 PO — IN_TRANSIT but supplier unreliable
        {"po_number": "PO-2024-0923", "part_id": part_by_num["HYD-F18-011"].id,
         "supplier_id": suppliers[4].id, "quantity_ordered": 3, "unit_price": 58000.0,
         "order_date": now - timedelta(days=25), "expected_delivery_date": now + timedelta(days=35),
         "actual_delivery_date": None, "status": "IN_TRANSIT", "delay_days": 0,
         "delay_reason": None},
        # DEMO SCENARIO 3: ENG-C130-006 PO — IN_TRANSIT
        {"po_number": "PO-2024-0756", "part_id": part_by_num["ENG-C130-006"].id,
         "supplier_id": suppliers[3].id, "quantity_ordered": 1, "unit_price": 1850000.0,
         "order_date": now - timedelta(days=60), "expected_delivery_date": now + timedelta(days=60),
         "actual_delivery_date": None, "status": "IN_TRANSIT", "delay_days": 0,
         "delay_reason": None},
        # ANT-F35-002
        {"po_number": "PO-2024-0812", "part_id": part_by_num["ANT-F35-002"].id,
         "supplier_id": suppliers[1].id, "quantity_ordered": 1, "unit_price": 380000.0,
         "order_date": now - timedelta(days=55), "expected_delivery_date": now + timedelta(days=35),
         "actual_delivery_date": None, "status": "IN_TRANSIT", "delay_days": 0,
         "delay_reason": None},
        # HPT-F35-008
        {"po_number": "PO-2024-0834", "part_id": part_by_num["HPT-F35-008"].id,
         "supplier_id": suppliers[0].id, "quantity_ordered": 2, "unit_price": 320000.0,
         "order_date": now - timedelta(days=30), "expected_delivery_date": now + timedelta(days=30),
         "actual_delivery_date": None, "status": "PENDING", "delay_days": 0,
         "delay_reason": None},
        # FADEC-F18-009
        {"po_number": "PO-2024-0867", "part_id": part_by_num["FADEC-F18-009"].id,
         "supplier_id": suppliers[5].id, "quantity_ordered": 2, "unit_price": 175000.0,
         "order_date": now - timedelta(days=20), "expected_delivery_date": now + timedelta(days=20),
         "actual_delivery_date": None, "status": "PENDING", "delay_days": 0,
         "delay_reason": None},
        # ENG-C130-007 — DELAYED
        {"po_number": "PO-2024-0798", "part_id": part_by_num["ENG-C130-007"].id,
         "supplier_id": suppliers[3].id, "quantity_ordered": 2, "unit_price": 420000.0,
         "order_date": now - timedelta(days=75), "expected_delivery_date": now - timedelta(days=5),
         "actual_delivery_date": None, "status": "DELAYED", "delay_days": 12,
         "delay_reason": "Manufacturing quality hold — non-conformance report pending disposition"},
        # STR-MH60-025 — PENDING
        {"po_number": "PO-2024-0901", "part_id": part_by_num["STR-MH60-025"].id,
         "supplier_id": suppliers[6].id, "quantity_ordered": 1, "unit_price": 650000.0,
         "order_date": now - timedelta(days=15), "expected_delivery_date": now + timedelta(days=75),
         "actual_delivery_date": None, "status": "PENDING", "delay_days": 0,
         "delay_reason": None},
        # COM-F35-032 — PENDING
        {"po_number": "PO-2024-0913", "part_id": part_by_num["COM-F35-032"].id,
         "supplier_id": suppliers[1].id, "quantity_ordered": 1, "unit_price": 195000.0,
         "order_date": now - timedelta(days=10), "expected_delivery_date": now + timedelta(days=45),
         "actual_delivery_date": None, "status": "PENDING", "delay_days": 0,
         "delay_reason": None},
        # OBOGS-MULTI-023 — DELIVERED
        {"po_number": "PO-2024-0702", "part_id": part_by_num["OBOGS-MULTI-023"].id,
         "supplier_id": suppliers[5].id, "quantity_ordered": 5, "unit_price": 18500.0,
         "order_date": now - timedelta(days=45), "expected_delivery_date": now - timedelta(days=15),
         "actual_delivery_date": now - timedelta(days=14), "status": "DELIVERED", "delay_days": 0,
         "delay_reason": None},
        # TIRE-MULTI-019 — DELIVERED
        {"po_number": "PO-2024-0721", "part_id": part_by_num["TIRE-MULTI-019"].id,
         "supplier_id": suppliers[2].id, "quantity_ordered": 12, "unit_price": 2800.0,
         "order_date": now - timedelta(days=30), "expected_delivery_date": now - timedelta(days=16),
         "actual_delivery_date": now - timedelta(days=17), "status": "DELIVERED", "delay_days": 0,
         "delay_reason": None},
        # ELEC-MH60-028 — DELAYED
        {"po_number": "PO-2024-0878", "part_id": part_by_num["ELEC-MH60-028"].id,
         "supplier_id": suppliers[1].id, "quantity_ordered": 2, "unit_price": 225000.0,
         "order_date": now - timedelta(days=50), "expected_delivery_date": now + timedelta(days=15),
         "actual_delivery_date": None, "status": "DELAYED", "delay_days": 8,
         "delay_reason": "Export control documentation — ITAR license renewal pending"},
        # HYD-F35-012 — DELIVERED
        {"po_number": "PO-2024-0733", "part_id": part_by_num["HYD-F35-012"].id,
         "supplier_id": suppliers[4].id, "quantity_ordered": 3, "unit_price": 95000.0,
         "order_date": now - timedelta(days=65), "expected_delivery_date": now - timedelta(days=10),
         "actual_delivery_date": now - timedelta(days=7), "status": "DELIVERED", "delay_days": 3,
         "delay_reason": None},
        # ECS-F35-020 — IN_TRANSIT
        {"po_number": "PO-2024-0889", "part_id": part_by_num["ECS-F35-020"].id,
         "supplier_id": suppliers[5].id, "quantity_ordered": 1, "unit_price": 320000.0,
         "order_date": now - timedelta(days=35), "expected_delivery_date": now + timedelta(days=35),
         "actual_delivery_date": None, "status": "IN_TRANSIT", "delay_days": 0,
         "delay_reason": None},
        # SENSOR-MH60-035 — CANCELLED
        {"po_number": "PO-2024-0644", "part_id": part_by_num["SENSOR-MH60-035"].id,
         "supplier_id": suppliers[1].id, "quantity_ordered": 1, "unit_price": 875000.0,
         "order_date": now - timedelta(days=120), "expected_delivery_date": now - timedelta(days=10),
         "actual_delivery_date": None, "status": "CANCELLED", "delay_days": 0,
         "delay_reason": "Budget hold — FY reallocation pending congressional approval"},
    ]

    for po_data in pos_data:
        po = PurchaseOrder(**po_data)
        db.add(po)
    db.flush()

    # -------------------------------------------------------------------------
    # MAINTENANCE EVENTS (20 events)
    # -------------------------------------------------------------------------
    maint_data = [
        # DEMO SCENARIO 1: AF-21-001 needs LRU — part NOT available
        {"aircraft_id": aircraft_by_tail["AF-21-001"].id, "part_id": part_by_num["LRU-F35-001"].id,
         "event_type": "UNSCHEDULED", "description": "Mission computer LRU failure detected — BIT fault code MC-0x4F2",
         "scheduled_date": now + timedelta(days=3), "status": "SCHEDULED",
         "technician": "SSgt Rodriguez, M.", "requires_part": True, "part_available": False, "downtime_hours": 0.0},
        # AF-21-001 also needs scheduled inspection
        {"aircraft_id": aircraft_by_tail["AF-21-001"].id, "part_id": None,
         "event_type": "INSPECTION", "description": "Phase inspection — 200-hour TBO check",
         "scheduled_date": now + timedelta(days=18), "status": "SCHEDULED",
         "technician": "MSgt Williams, K.", "requires_part": False, "part_available": True, "downtime_hours": 0.0},
        # DEMO SCENARIO 2: NA-19-101 needs hydraulic actuator — zero stock, part NOT available
        {"aircraft_id": aircraft_by_tail["NA-19-101"].id, "part_id": part_by_num["HYD-F18-011"].id,
         "event_type": "UNSCHEDULED", "description": "Port wing flaperon actuator failed — hydraulic leak detected, grounded",
         "scheduled_date": now + timedelta(days=1), "status": "IN_PROGRESS",
         "technician": "TSgt Martinez, J.", "requires_part": True, "part_available": False, "downtime_hours": 48.0},
        # DEMO SCENARIO 3: AC-20-401 C-130J engine component — low stock
        {"aircraft_id": aircraft_by_tail["AC-20-401"].id, "part_id": part_by_num["ENG-C130-006"].id,
         "event_type": "SCHEDULED", "description": "Turboprop power section — phase 4 depot-level inspection, power section swap required",
         "scheduled_date": now + timedelta(days=10), "status": "SCHEDULED",
         "technician": "MSgt Thompson, D.", "requires_part": True, "part_available": True, "downtime_hours": 0.0},
        # AF-21-003 — PMC, ECS issue
        {"aircraft_id": aircraft_by_tail["AF-21-003"].id, "part_id": part_by_num["ECS-F35-020"].id,
         "event_type": "REPAIR", "description": "Integrated power package degraded performance — partial ECS failure",
         "scheduled_date": now + timedelta(days=7), "status": "SCHEDULED",
         "technician": "TSgt Garcia, L.", "requires_part": True, "part_available": True, "downtime_hours": 0.0},
        # NA-19-104 — PMC
        {"aircraft_id": aircraft_by_tail["NA-19-104"].id, "part_id": part_by_num["FADEC-F18-009"].id,
         "event_type": "SCHEDULED", "description": "FADEC software update and functional check",
         "scheduled_date": now + timedelta(days=14), "status": "SCHEDULED",
         "technician": "SSgt Chen, W.", "requires_part": True, "part_available": True, "downtime_hours": 0.0},
        # MH-22-602 — PMC, radar issue
        {"aircraft_id": aircraft_by_tail["MH-22-602"].id, "part_id": part_by_num["ELEC-MH60-028"].id,
         "event_type": "REPAIR", "description": "APS-153 radar intermittent failure — BITE indicates processor fault",
         "scheduled_date": now + timedelta(days=5), "status": "SCHEDULED",
         "technician": "AT1 Johnson, R.", "requires_part": True, "part_available": False, "downtime_hours": 0.0},
        # NA-19-102 scheduled maintenance
        {"aircraft_id": aircraft_by_tail["NA-19-102"].id, "part_id": None,
         "event_type": "SCHEDULED", "description": "300-hour phase inspection",
         "scheduled_date": now + timedelta(days=32), "status": "SCHEDULED",
         "technician": "TSgt Park, S.", "requires_part": False, "part_available": True, "downtime_hours": 0.0},
        # AC-20-402 routine
        {"aircraft_id": aircraft_by_tail["AC-20-402"].id, "part_id": None,
         "event_type": "SCHEDULED", "description": "Annual isochronal inspection — airframe and systems",
         "scheduled_date": now + timedelta(days=60), "status": "SCHEDULED",
         "technician": "MSgt Davis, P.", "requires_part": False, "part_available": True, "downtime_hours": 0.0},
        # AF-21-002 brake replacement
        {"aircraft_id": aircraft_by_tail["AF-21-002"].id, "part_id": part_by_num["BRAKE-F35-018"].id,
         "event_type": "SCHEDULED", "description": "Carbon-ceramic brake assembly replacement at 500-cycle TBO",
         "scheduled_date": now + timedelta(days=21), "status": "SCHEDULED",
         "technician": "SSgt Lee, T.", "requires_part": True, "part_available": True, "downtime_hours": 0.0},
        # MH-22-601 routine
        {"aircraft_id": aircraft_by_tail["MH-22-601"].id, "part_id": None,
         "event_type": "INSPECTION", "description": "150-hour rotor head inspection",
         "scheduled_date": now + timedelta(days=10), "status": "SCHEDULED",
         "technician": "AE2 White, C.", "requires_part": False, "part_available": True, "downtime_hours": 0.0},
        # NA-19-103 IFF
        {"aircraft_id": aircraft_by_tail["NA-19-103"].id, "part_id": part_by_num["IFF-MULTI-003"].id,
         "event_type": "REPAIR", "description": "IFF transponder Mode S failure — replacement required",
         "scheduled_date": now + timedelta(days=9), "status": "SCHEDULED",
         "technician": "AT2 Brown, J.", "requires_part": True, "part_available": True, "downtime_hours": 0.0},
        # AC-20-401 fuel pump
        {"aircraft_id": aircraft_by_tail["AC-20-401"].id, "part_id": part_by_num["FUEL-C130-030"].id,
         "event_type": "SCHEDULED", "description": "Fuel boost pump TBO replacement",
         "scheduled_date": now + timedelta(days=25), "status": "SCHEDULED",
         "technician": "MSgt Thompson, D.", "requires_part": True, "part_available": True, "downtime_hours": 0.0},
        # Completed events
        {"aircraft_id": aircraft_by_tail["AF-21-002"].id, "part_id": part_by_num["TIRE-MULTI-019"].id,
         "event_type": "SCHEDULED", "description": "Main gear tire replacement at 300-landing cycle",
         "scheduled_date": now - timedelta(days=5), "completed_date": now - timedelta(days=5),
         "status": "COMPLETED", "technician": "SSgt Lee, T.", "requires_part": True, "part_available": True, "downtime_hours": 4.0},
        {"aircraft_id": aircraft_by_tail["NA-19-102"].id, "part_id": None,
         "event_type": "INSPECTION", "description": "100-hour phase inspection — all systems checked",
         "scheduled_date": now - timedelta(days=8), "completed_date": now - timedelta(days=8),
         "status": "COMPLETED", "technician": "TSgt Park, S.", "requires_part": False, "part_available": True, "downtime_hours": 12.0},
        {"aircraft_id": aircraft_by_tail["MH-22-603"].id, "part_id": None,
         "event_type": "SCHEDULED", "description": "100-hour phase inspection",
         "scheduled_date": now - timedelta(days=10), "completed_date": now - timedelta(days=10),
         "status": "COMPLETED", "technician": "AE1 Wilson, M.", "requires_part": False, "part_available": True, "downtime_hours": 8.0},
        {"aircraft_id": aircraft_by_tail["NA-19-104"].id, "part_id": part_by_num["HYD-MULTI-015"].id,
         "event_type": "REPAIR", "description": "Hydraulic reservoir replacement — system leak",
         "scheduled_date": now - timedelta(days=7), "completed_date": now - timedelta(days=7),
         "status": "COMPLETED", "technician": "SSgt Chen, W.", "requires_part": True, "part_available": True, "downtime_hours": 6.0},
        {"aircraft_id": aircraft_by_tail["AC-20-402"].id, "part_id": part_by_num["ELEC-C130-027"].id,
         "event_type": "REPAIR", "description": "AC power distribution panel relay failure — panel swap",
         "scheduled_date": now - timedelta(days=30), "completed_date": now - timedelta(days=29),
         "status": "COMPLETED", "technician": "MSgt Davis, P.", "requires_part": True, "part_available": True, "downtime_hours": 18.0},
        {"aircraft_id": aircraft_by_tail["AF-21-001"].id, "part_id": part_by_num["OBOGS-MULTI-023"].id,
         "event_type": "REPAIR", "description": "OBOGS concentrator replacement — O2 purity degraded",
         "scheduled_date": now - timedelta(days=12), "completed_date": now - timedelta(days=12),
         "status": "COMPLETED", "technician": "SSgt Rodriguez, M.", "requires_part": True, "part_available": True, "downtime_hours": 3.0},
        {"aircraft_id": aircraft_by_tail["MH-22-601"].id, "part_id": None,
         "event_type": "INSPECTION", "description": "Airframe corrosion inspection — cleared",
         "scheduled_date": now - timedelta(days=6), "completed_date": now - timedelta(days=6),
         "status": "COMPLETED", "technician": "AE2 White, C.", "requires_part": False, "part_available": True, "downtime_hours": 6.0},
    ]

    for m_data in maint_data:
        if "completed_date" not in m_data:
            m_data["completed_date"] = None
        m = MaintenanceEvent(**m_data)
        db.add(m)
    db.flush()

    # -------------------------------------------------------------------------
    # FLIGHT SCHEDULE (10 entries)
    # -------------------------------------------------------------------------
    flights_data = [
        {"aircraft_id": aircraft_by_tail["AF-21-002"].id, "mission_name": "STRIKE EAGLE 01",
         "mission_type": "COMBAT", "scheduled_date": now + timedelta(days=2),
         "duration_hours": 4.5, "priority": "HIGH", "status": "SCHEDULED"},
        {"aircraft_id": aircraft_by_tail["AF-21-001"].id, "mission_name": "STRIKE EAGLE 02",
         "mission_type": "COMBAT", "scheduled_date": now + timedelta(days=4),
         "duration_hours": 3.8, "priority": "CRITICAL", "status": "AT_RISK"},
        {"aircraft_id": aircraft_by_tail["NA-19-102"].id, "mission_name": "BLUE FLAG 12",
         "mission_type": "TRAINING", "scheduled_date": now + timedelta(days=5),
         "duration_hours": 2.5, "priority": "ROUTINE", "status": "SCHEDULED"},
        {"aircraft_id": aircraft_by_tail["NA-19-101"].id, "mission_name": "BLUE FLAG 13",
         "mission_type": "TRAINING", "scheduled_date": now + timedelta(days=3),
         "duration_hours": 2.0, "priority": "HIGH", "status": "CANCELLED"},
        {"aircraft_id": aircraft_by_tail["AC-20-401"].id, "mission_name": "LOGAIR 441",
         "mission_type": "TRANSPORT", "scheduled_date": now + timedelta(days=8),
         "duration_hours": 6.0, "priority": "HIGH", "status": "AT_RISK"},
        {"aircraft_id": aircraft_by_tail["AC-20-402"].id, "mission_name": "LOGAIR 442",
         "mission_type": "TRANSPORT", "scheduled_date": now + timedelta(days=10),
         "duration_hours": 5.5, "priority": "ROUTINE", "status": "SCHEDULED"},
        {"aircraft_id": aircraft_by_tail["MH-22-601"].id, "mission_name": "SAR ALPHA",
         "mission_type": "RECON", "scheduled_date": now + timedelta(days=3),
         "duration_hours": 3.0, "priority": "HIGH", "status": "SCHEDULED"},
        {"aircraft_id": aircraft_by_tail["MH-22-603"].id, "mission_name": "SAR BRAVO",
         "mission_type": "RECON", "scheduled_date": now + timedelta(days=6),
         "duration_hours": 2.5, "priority": "ROUTINE", "status": "SCHEDULED"},
        {"aircraft_id": aircraft_by_tail["NA-19-103"].id, "mission_name": "TOP GUN 07",
         "mission_type": "TRAINING", "scheduled_date": now + timedelta(days=7),
         "duration_hours": 1.8, "priority": "ROUTINE", "status": "SCHEDULED"},
        {"aircraft_id": aircraft_by_tail["AF-21-003"].id, "mission_name": "RED FLAG 22",
         "mission_type": "TRAINING", "scheduled_date": now + timedelta(days=12),
         "duration_hours": 3.2, "priority": "HIGH", "status": "SCHEDULED"},
    ]

    for f_data in flights_data:
        f = FlightSchedule(**f_data)
        db.add(f)
    db.flush()

    # -------------------------------------------------------------------------
    # PRE-COMPUTED RISK SCORES
    # -------------------------------------------------------------------------
    risk_scores_data = [
        # Aircraft risk scores
        {"aircraft_id": aircraft_by_tail["AF-21-001"].id, "risk_type": "MISSION_READINESS",
         "score": 87.4, "shortage_probability": 0.92, "lead_time_volatility": 0.85,
         "supplier_reliability_risk": 0.78, "mission_criticality": 0.95, "historical_failure_rate": 0.65,
         "confidence_level": 0.88, "days_to_event": 18,
         "explanation": "F-35A AF-21-001 is AT_RISK. Mission computer LRU (LRU-F35-001) has only 1 unit on hand against a reorder point of 3. Active PO PO-2024-0891 is delayed 18 days due to FPGA procurement issues. Raytheon Avionics Corp has only 82% on-time delivery. Next maintenance requires this LRU in 3 days."},
        {"aircraft_id": aircraft_by_tail["NA-19-101"].id, "risk_type": "MISSION_READINESS",
         "score": 94.1, "shortage_probability": 1.0, "lead_time_volatility": 0.88,
         "supplier_reliability_risk": 0.90, "mission_criticality": 1.0, "historical_failure_rate": 0.72,
         "confidence_level": 0.95, "days_to_event": 1,
         "explanation": "F/A-18E NA-19-101 is NMC. Aircraft is grounded due to flight control hydraulic actuator (HYD-F18-011) failure with zero units in stock. Moog Hydraulic Systems has a 61% on-time delivery rate and 60-day lead time. Active PO in transit — expected delivery 35 days out. Aircraft cannot fly until part arrives."},
        {"aircraft_id": aircraft_by_tail["AC-20-401"].id, "risk_type": "MISSION_READINESS",
         "score": 76.8, "shortage_probability": 0.78, "lead_time_volatility": 0.72,
         "supplier_reliability_risk": 0.65, "mission_criticality": 0.88, "historical_failure_rate": 0.82,
         "confidence_level": 0.84, "days_to_event": 10,
         "explanation": "C-130J AC-20-401 is AT_RISK. Phase 4 engine inspection requires turboprop power section (ENG-C130-006) with only 2 units remaining (below reorder of 3). 120-day lead time from GE Aviation. If current spare is consumed in scheduled maintenance, next aircraft requiring this component has no backup available for 4+ months."},
        {"aircraft_id": aircraft_by_tail["AF-21-003"].id, "risk_type": "MISSION_READINESS",
         "score": 52.3, "shortage_probability": 0.45, "lead_time_volatility": 0.55,
         "supplier_reliability_risk": 0.48, "mission_criticality": 0.72, "historical_failure_rate": 0.40,
         "confidence_level": 0.75, "days_to_event": 42,
         "explanation": "F-35A AF-21-003 (PMC) has degraded ECS. Integrated power package on order — delivery expected 35 days. Low immediate risk but trending toward NMC if repair is deferred past 42 days."},
        {"aircraft_id": aircraft_by_tail["MH-22-602"].id, "risk_type": "MISSION_READINESS",
         "score": 48.9, "shortage_probability": 0.42, "lead_time_volatility": 0.58,
         "supplier_reliability_risk": 0.62, "mission_criticality": 0.65, "historical_failure_rate": 0.35,
         "confidence_level": 0.70, "days_to_event": 21,
         "explanation": "MH-60R MH-22-602 (PMC) radar processor PO delayed 8 days — ITAR paperwork. Risk is manageable but trending upward."},
        # Part risk scores
        {"part_id": part_by_num["LRU-F35-001"].id, "risk_type": "SHORTAGE",
         "score": 89.2, "shortage_probability": 0.94, "lead_time_volatility": 0.87,
         "supplier_reliability_risk": 0.80, "mission_criticality": 0.95, "historical_failure_rate": 0.68,
         "confidence_level": 0.91, "days_to_event": 21,
         "explanation": "LRU-F35-001: 1 unit on hand, reorder point 3, PO delayed 18 days. Single-source from Raytheon with 82% OTD. Expected stockout in 21 days if current unit fails."},
        {"part_id": part_by_num["HYD-F18-011"].id, "risk_type": "SHORTAGE",
         "score": 96.5, "shortage_probability": 1.0, "lead_time_volatility": 0.92,
         "supplier_reliability_risk": 0.90, "mission_criticality": 0.95, "historical_failure_rate": 0.78,
         "confidence_level": 0.96, "days_to_event": 0,
         "explanation": "HYD-F18-011: ZERO stock. Aircraft grounded. Moog Hydraulic Systems 61% OTD, 60-day lead time. 3 units on order, in transit."},
        {"part_id": part_by_num["ENG-C130-006"].id, "risk_type": "SHORTAGE",
         "score": 78.4, "shortage_probability": 0.80, "lead_time_volatility": 0.75,
         "supplier_reliability_risk": 0.68, "mission_criticality": 0.88, "historical_failure_rate": 0.82,
         "confidence_level": 0.86, "days_to_event": 10,
         "explanation": "ENG-C130-006: 2 units remaining, below reorder point of 3. 120-day lead time. Single-source from GE Aviation. High historical failure rate at this flight-hour interval."},
        {"part_id": part_by_num["STR-MH60-025"].id, "risk_type": "SHORTAGE",
         "score": 64.7, "shortage_probability": 0.62, "lead_time_volatility": 0.68,
         "supplier_reliability_risk": 0.72, "mission_criticality": 0.78, "historical_failure_rate": 0.45,
         "confidence_level": 0.74, "days_to_event": 45,
         "explanation": "STR-MH60-025: 1 unit on hand, PO pending (90-day lead time). Single-source, if consumed no backup for 90+ days."},
        {"part_id": part_by_num["SENSOR-MH60-035"].id, "risk_type": "SHORTAGE",
         "score": 61.2, "shortage_probability": 0.55, "lead_time_volatility": 0.72,
         "supplier_reliability_risk": 0.75, "mission_criticality": 0.80, "historical_failure_rate": 0.38,
         "confidence_level": 0.68, "days_to_event": 60,
         "explanation": "SENSOR-MH60-035: 1 unit on hand, last PO cancelled due to budget hold. 120-day lead time. Mission-critical for maritime ISR."},
        # Supplier risk scores
        {"supplier_id": suppliers[4].id, "risk_type": "SUPPLIER_DELAY",
         "score": 82.5, "shortage_probability": 0.80, "lead_time_volatility": 0.85,
         "supplier_reliability_risk": 0.88, "mission_criticality": 0.75, "historical_failure_rate": 0.65,
         "confidence_level": 0.88, "days_to_event": None,
         "explanation": "Moog Hydraulic Systems: 61% on-time delivery, 3.5% defect rate. Supplies 4 single-source parts including HYD-F18-011 (zero stock, aircraft grounded). Immediate risk to fleet readiness."},
        {"supplier_id": suppliers[1].id, "risk_type": "SUPPLIER_DELAY",
         "score": 68.4, "shortage_probability": 0.65, "lead_time_volatility": 0.72,
         "supplier_reliability_risk": 0.70, "mission_criticality": 0.78, "historical_failure_rate": 0.52,
         "confidence_level": 0.80, "days_to_event": None,
         "explanation": "Raytheon Avionics Corp: 82% on-time delivery, 60-day avg lead time, 12 single-source parts. PO-2024-0891 delayed 18 days. Multiple critical avionics systems at risk."},
        {"supplier_id": suppliers[6].id, "risk_type": "SUPPLIER_DELAY",
         "score": 62.8, "shortage_probability": 0.60, "lead_time_volatility": 0.65,
         "supplier_reliability_risk": 0.72, "mission_criticality": 0.72, "historical_failure_rate": 0.48,
         "confidence_level": 0.72, "days_to_event": None,
         "explanation": "TransDigm Precision Parts: 74% on-time delivery, 75-day lead time, 9 single-source parts. Last audit 300 days ago — overdue. High risk for parts shortages."},
    ]

    for rs_data in risk_scores_data:
        rs = RiskScore(**rs_data)
        db.add(rs)
    db.flush()

    # -------------------------------------------------------------------------
    # AGENT RECOMMENDATIONS (pre-seeded)
    # -------------------------------------------------------------------------
    recs_data = [
        {
            "title": "CRITICAL: Expedite PO-2024-0891 — F-35A Mission Computer LRU shortage threatens NMC in 18 days",
            "recommendation_type": "EXPEDITE_ORDER",
            "priority": "CRITICAL",
            "aircraft_affected": "AF-21-001",
            "part_affected": "LRU-F35-001",
            "supplier_affected": "Raytheon Avionics Corp",
            "description": "Aircraft AF-21-001 (F-35A) will become Non-Mission-Capable in approximately 18 days. Mission computer LRU has only 1 unit remaining and scheduled maintenance requiring this part is in 3 days. PO-2024-0891 is delayed 18 days due to FPGA procurement issues at the supplier.",
            "rationale": "With 1 unit on hand and a pending maintenance event in 3 days, this part will be consumed leaving zero buffer. The delayed PO (18 days overdue) will not arrive before the aircraft is grounded. Raytheon's 82% OTD rate and 45-day lead time make this a critical supply chain vulnerability.",
            "estimated_impact": "AF-21-001 grounded for 21-45 days. STRIKE EAGLE 02 mission (CRITICAL priority) at risk. Estimated operational cost: $2.4M per day aircraft is NMC.",
            "action_steps": json.dumps([
                "Contact Raytheon Avionics Corp program manager immediately — escalate to VP level",
                "Request expedited delivery on PO-2024-0891, authorize premium shipping",
                "Survey sister squadrons (VFA-25, VFA-113) for available LRU-F35-001 loan",
                "Coordinate with F-35 JPO for emergency requisition from depot stock",
                "Reschedule STRIKE EAGLE 02 mission to AF-21-002 as contingency"
            ]),
            "status": "OPEN",
        },
        {
            "title": "CRITICAL: NA-19-101 NMC — Hydraulic actuator zero stock, Moog Hydraulic Systems high-risk supplier",
            "recommendation_type": "EXPEDITE_ORDER",
            "priority": "CRITICAL",
            "aircraft_affected": "NA-19-101",
            "part_affected": "HYD-F18-011",
            "supplier_affected": "Moog Hydraulic Systems",
            "description": "F/A-18E NA-19-101 is currently Non-Mission-Capable due to flight control hydraulic actuator failure with zero units in stock. Moog Hydraulic Systems (supplier) has a 61% on-time delivery rate. Active PO (PO-2024-0923) shows 35 days estimated delivery. Aircraft is grounded and BLUE FLAG 13 mission has been cancelled.",
            "rationale": "Zero inventory with an unreliable supplier is the highest-risk scenario. Moog's 61% OTD rate means there is a 39% probability this PO will be further delayed. The 60-day lead time for new orders means no recovery option if this PO slips.",
            "estimated_impact": "NA-19-101 grounded indefinitely until delivery. Blue Flag 13 cancelled. Estimated 35-65 day NMC period. Squadron operational readiness rate drops to 67%.",
            "action_steps": json.dumps([
                "Immediately contact Moog Hydraulic Systems — escalate PO-2024-0923 to priority delivery",
                "Survey NAVAIR depot (NADEP Jacksonville) for available actuator loan/exchange",
                "Evaluate alternative actuator sources — Parker Hannifin and Eaton Aerospace",
                "Submit NMCS (Non-Mission-Capable Supply) status report up chain of command",
                "Issue formal supplier corrective action request to Moog for delivery performance"
            ]),
            "status": "OPEN",
        },
        {
            "title": "HIGH: Expedite ENG-C130-006 reorder — C-130J engine component below reorder point, 120-day lead time",
            "recommendation_type": "EXPEDITE_ORDER",
            "priority": "HIGH",
            "aircraft_affected": "AC-20-401",
            "part_affected": "ENG-C130-006",
            "supplier_affected": "GE Aviation Components",
            "description": "C-130J AC-20-401 has scheduled Phase 4 engine inspection in 10 days requiring turboprop power section. Only 2 units remain (reorder point: 3). If AC-20-401 consumes one unit, only 1 will remain with a 120-day lead time for replenishment. A second C-130J requiring this part would face extended grounding.",
            "rationale": "With 2 units and a 120-day lead time, the fleet is vulnerable. Historical failure rate for this component at 8,000+ flight hours is elevated. AC-20-401 is at 8,741 hours — prime failure window.",
            "estimated_impact": "If both remaining units are consumed, next C-130J requiring this part faces 4+ month grounding. LOGAIR 441 mission (HIGH priority) at risk.",
            "action_steps": json.dumps([
                "Place immediate emergency order for 4 units of ENG-C130-006 with GE Aviation",
                "Request depot-level inspection to determine if current units can be extended",
                "Contact AMC logistics for cross-base inventory sharing",
                "Review predictive maintenance data to defer AC-20-401 maintenance if engine health permits",
                "Initiate supplier qualification for alternative turboprop component source"
            ]),
            "status": "OPEN",
        },
        {
            "title": "HIGH: Qualify alternative supplier for hydraulic actuators — Moog performance unacceptable",
            "recommendation_type": "FIND_ALT_SUPPLIER",
            "priority": "HIGH",
            "aircraft_affected": "NA-19-101, NA-19-104",
            "part_affected": "HYD-F18-011, HYD-F35-012",
            "supplier_affected": "Moog Hydraulic Systems",
            "description": "Moog Hydraulic Systems' 61% on-time delivery rate and 3.5% defect rate are below threshold. This supplier provides hydraulic actuators for both F/A-18 and F-35 platforms. Current performance is directly causing NMC status on NA-19-101.",
            "rationale": "Supplier reliability below 70% constitutes high risk per DoD supply chain standards. With 4 single-source parts from Moog and declining performance trend (last audit 240 days ago), alternative qualification is mandatory.",
            "estimated_impact": "Qualifying Parker Hannifin as alternative source reduces hydraulic actuator shortage risk by estimated 65%.",
            "action_steps": json.dumps([
                "Initiate First Article Test (FAT) with Parker Hannifin for HYD-F18-011 equivalent",
                "Issue formal CPAR (Corrective/Preventive Action Request) to Moog",
                "Schedule emergency supplier audit within 30 days",
                "Brief NAVAIR PMA-265 on actuator supply chain risk",
                "Review contract terms for performance penalties"
            ]),
            "status": "OPEN",
        },
        {
            "title": "MEDIUM: Raytheon Avionics Corp — multiple delayed POs create systemic F-35A avionics risk",
            "recommendation_type": "FIND_ALT_SUPPLIER",
            "priority": "MEDIUM",
            "aircraft_affected": "AF-21-001, AF-21-003",
            "part_affected": "LRU-F35-001, COM-F35-032",
            "supplier_affected": "Raytheon Avionics Corp",
            "description": "Raytheon Avionics Corp has 3 open POs with 2 showing delays. Combined with 60-day average lead time and 12 single-source parts, this creates systemic risk to F-35A avionics readiness.",
            "rationale": "Multiple concurrent delays suggest systemic supplier issues rather than isolated incidents. F-35A avionics are all single-source, making this risk extremely difficult to mitigate.",
            "estimated_impact": "Current trajectory: 2 of 3 F-35A aircraft at medium-high risk within 45 days.",
            "action_steps": json.dumps([
                "Request formal Root Cause Analysis from Raytheon for PO delays",
                "Escalate to F-35 Joint Program Office (JPO) for contractor performance review",
                "Review Defense Contract Management Agency (DCMA) oversight records",
                "Assess feasibility of stockpiling 90-day safety stock for critical LRUs",
                "Schedule program management review within 15 days"
            ]),
            "status": "OPEN",
        },
    ]

    for rec_data in recs_data:
        rec = AgentRecommendation(**rec_data)
        db.add(rec)

    db.commit()
