"""
Cargill Ocean Transportation - FastAPI Backend
==============================================
Wraps existing Python analytics with a REST API.
Pre-computes optimization results on startup for instant responses.
"""

import os
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("cargill.api")

# Load .env file from project root
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)
    logger.info("Loaded env from %s", env_path)
except ImportError:
    logger.info("python-dotenv not installed, using system env vars")

from .services.calculator_service import calculator_service
from .routes import portfolio, voyage, scenario, ml_routes, chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize calculator service on startup."""
    logger.info("=" * 50)
    logger.info("Cargill Ocean Transportation API - Starting")
    logger.info("=" * 50)
    calculator_service.initialize()
    logger.info("API ready at http://localhost:8000")
    logger.info("Docs at http://localhost:8000/docs")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Cargill Ocean Transportation API",
    description="Maritime shipping analytics for vessel-cargo optimization",
    version="1.0.0",
    lifespan=lifespan,
)

# Get CORS origins from environment (for production) or use defaults (for dev)
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
cors_origins_list = [origin.strip() for origin in cors_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(portfolio.router)
app.include_router(voyage.router)
app.include_router(scenario.router)
app.include_router(ml_routes.router)
app.include_router(chat.router)


@app.get("/")
def root():
    return {
        "name": "Cargill Ocean Transportation API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "vessels": "/api/vessels",
            "cargoes": "/api/cargoes",
            "portfolio": "/api/portfolio/optimize",
            "voyages": "/api/portfolio/all-voyages",
            "bunker_scenario": "/api/scenario/bunker",
            "delay_scenario": "/api/scenario/port-delay",
            "ml_delays": "/api/ml/port-delays",
            "model_info": "/api/ml/model-info",
            "chat": "/api/chat",
            "docs": "/docs",
        },
    }


@app.get("/health")
@app.get("/api/health")
def health():
    return {"status": "healthy"}
