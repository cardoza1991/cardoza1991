from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, SessionLocal
from .models.models import Base
from .routers import fleet, parts, suppliers, risk, agent, intel, impact, scenarios, bom, auth, landing
from .services.seed_data import seed_database
from .services.agent_loop import start_scheduler, run_agent_cycle
from .services.ml_predictor import train_models
from .services.auth import ensure_default_tenant_and_user
from .services.audit import audit_middleware
from .config import settings

app = FastAPI(
    title="AeroRisk AI",
    description="Autonomous Aerospace Supply Chain Risk Intelligence Platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Audit middleware runs AFTER CORS so OPTIONS preflights don't audit.
app.middleware("http")(audit_middleware)

app.include_router(fleet.router)
app.include_router(parts.router)
app.include_router(suppliers.router)
app.include_router(risk.router)
app.include_router(agent.router)
app.include_router(intel.router)
app.include_router(impact.router)
app.include_router(scenarios.router)
app.include_router(bom.router)
app.include_router(auth.router)
app.include_router(landing.router)


@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)
    train_models()
    # Tenancy bootstrap runs unconditionally so login works even when
    # seed_on_startup=false.
    db = SessionLocal()
    try:
        ensure_default_tenant_and_user(db)
    finally:
        db.close()
    if settings.seed_on_startup:
        db = SessionLocal()
        try:
            seed_database(db)
            # Prime the intel + risk pipeline so the first dashboard render
            # already has signals and scores, instead of waiting for the
            # scheduled job 60s later.
            run_agent_cycle(db)
        finally:
            db.close()
    start_scheduler()


@app.get("/")
def root():
    return {"status": "operational", "system": "AeroRisk AI v1.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}
