"""
CoastWatch FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import shorelines, analysis, forecast, chat, jobs, tiles, marine
from app.db.init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan handler: startup and shutdown events."""
    # Startup
    await init_db()
    yield
    # Shutdown (cleanup if needed)


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title="CoastWatch API",
        description="API for monitoring coastal shoreline changes using Sentinel-2 satellite imagery",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS middleware — allow all origins for development
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    application.include_router(
        shorelines.router, prefix="/api/shorelines", tags=["Shorelines"]
    )
    application.include_router(
        analysis.router, prefix="/api/analysis", tags=["Analysis"]
    )
    application.include_router(
        forecast.router, prefix="/api/forecast", tags=["Forecast"]
    )
    application.include_router(
        chat.router, prefix="/api/chat", tags=["Chatbot"]
    )
    application.include_router(
        jobs.router, prefix="/api/jobs", tags=["Jobs"]
    )
    application.include_router(
        tiles.router, prefix="/tiles", tags=["Tiles"]
    )
    application.include_router(
        marine.router, prefix="/api/marine", tags=["Marine"]
    )

    @application.get("/health", tags=["Health"])
    async def health_check() -> dict:
        return {"status": "healthy", "service": "CoastWatch API"}

    return application


app = create_application()
