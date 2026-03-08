"""
Wealthmancer Backend - FastAPI Application Entry Point.

Financial document consolidation app for Indonesian financial statements.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import UPLOAD_DIR
from app.db.database import create_tables

# Import routers
from app.api.dashboard import router as dashboard_router
from app.api.portfolio import router as portfolio_router
from app.api.settings import router as settings_router
from app.api.transactions import router as transactions_router
from app.api.upload import router as upload_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler - runs on startup and shutdown."""
    # Startup
    logger.info("Creating database tables...")
    # Import all models so their tables get created
    from app.models.settings import AppSetting  # noqa: F401

    create_tables()
    logger.info("Database tables created successfully.")
    yield
    # Shutdown
    logger.info("Application shutting down.")


app = FastAPI(
    title="Wealthmancer API",
    description="Financial document consolidation backend for Indonesian financial statements.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware - allow frontend at localhost:3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(upload_router, prefix="/api", tags=["Upload"])
app.include_router(portfolio_router, prefix="/api", tags=["Portfolio"])
app.include_router(transactions_router, prefix="/api", tags=["Transactions"])
app.include_router(dashboard_router, prefix="/api", tags=["Dashboard"])
app.include_router(settings_router, prefix="/api", tags=["Settings"])

# Serve uploaded files as static
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "wealthmancer-api"}
