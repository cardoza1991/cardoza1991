from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, SessionLocal
from .models.models import Base
from .routers import fleet, parts, suppliers, risk, agent
from .services.seed_data import seed_database
from .services.agent_loop import start_scheduler
from .services.ml_predictor import train_models
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

app.include_router(fleet.router)
app.include_router(parts.router)
app.include_router(suppliers.router)
app.include_router(risk.router)
app.include_router(agent.router)


@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)
    train_models()
    if settings.seed_on_startup:
        db = SessionLocal()
        try:
            seed_database(db)
        finally:
            db.close()
    start_scheduler()


@app.get("/")
def root():
    return {"status": "operational", "system": "AeroRisk AI v1.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}
