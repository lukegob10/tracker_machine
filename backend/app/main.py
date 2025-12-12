from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .db import SessionLocal, init_db
from .routes import api_router
from .seed import seed_phases
from .sample_seed import seed_sample_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with SessionLocal() as session:
        seed_phases(session)
        seed_sample_data(session)
    yield


app = FastAPI(title="Jira-lite API", version="0.1.0", lifespan=lifespan)

# API under /api to avoid collisions with static frontend
app.include_router(api_router, prefix="/api")

# Serve frontend from repo root /frontend
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
