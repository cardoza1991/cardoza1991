"""Shared fixtures: in-memory SQLite session so tests don't need Postgres."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Make `app` importable when running pytest from the backend dir.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Point the app at SQLite BEFORE importing it.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.models.models import Base, Supplier  # noqa: E402


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def seeded_suppliers(db):
    suppliers = [
        Supplier(
            name="Honeywell Aerospace Tech",
            country="USA",
            reliability_score=0.87,
            avg_lead_time_days=35,
            on_time_delivery_rate=0.91,
            defect_rate=0.012,
            single_source_parts_count=7,
            is_approved=True,
            aliases=json.dumps(["Honeywell International"]),
            keywords=json.dumps(["Honeywell", "Experion PKS"]),
            ticker="HON",
            cik="0000773840",
            hq_country_code="US",
            hq_region="North America",
        ),
        Supplier(
            name="Moog Hydraulic Systems",
            country="USA",
            reliability_score=0.72,
            avg_lead_time_days=60,
            on_time_delivery_rate=0.61,
            defect_rate=0.035,
            single_source_parts_count=4,
            is_approved=True,
            aliases=json.dumps(["Hydraulic Equipment LLC"]),
            keywords=json.dumps(["Moog"]),
            ticker="MOG-A",
            cik="0000067887",
            hq_country_code="US",
            hq_region="North America",
        ),
        Supplier(
            name="Collins Aerospace Solutions",
            country="USA",
            reliability_score=0.95,
            avg_lead_time_days=30,
            on_time_delivery_rate=0.94,
            defect_rate=0.008,
            single_source_parts_count=5,
            is_approved=True,
            aliases=json.dumps(["Collins Aerospace"]),
            keywords=json.dumps(["Collins Aerospace", "ARINC 615A"]),
            ticker="RTX",
            cik="0000101829",
            hq_country_code="US",
            hq_region="North America",
        ),
        Supplier(
            name="Safran Landing Systems",
            country="France",
            reliability_score=0.83,
            avg_lead_time_days=80,
            on_time_delivery_rate=0.79,
            defect_rate=0.022,
            single_source_parts_count=3,
            is_approved=True,
            aliases=json.dumps(["Safran"]),
            keywords=json.dumps(["Safran"]),
            ticker="SAF.PA",
            hq_country_code="FR",
            hq_region="Europe",
        ),
    ]
    for s in suppliers:
        db.add(s)
    db.commit()
    return suppliers
