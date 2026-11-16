"""
Database initialization — creates all tables on startup.
"""
import logging

from sqlalchemy import text

from app.db.base import Base, engine

logger = logging.getLogger(__name__)


async def init_db() -> None:
    """
    Initialize the database by creating all tables.
    Imports all models to ensure they are registered with the Base metadata.
    """
    # Import all models to register them with Base.metadata
    from app.models import shoreline, analysis, forecast, job  # noqa: F401

    try:
        async with engine.begin() as conn:
            # Enable PostGIS extension if available
            try:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
                logger.info("PostGIS extension enabled")
            except Exception as exc:
                logger.warning("Could not enable PostGIS: %s", exc)

            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
    except Exception as exc:
        logger.error("Failed to initialize database: %s", exc)
        raise
