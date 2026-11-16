"""
Seed script: creates sample shoreline data for Cua Tung, Quang Tri, Vietnam.

Generates fake but realistic shoreline LineString geometries spanning 2018-2023
so the frontend can be tested without running actual GEE extractions.

Usage:
    cd /Users/I779979/Documents/Personal/CoastWatch/Backend
    DATABASE_URL=postgresql+asyncpg://... python scripts/seed_data.py
"""
import asyncio
import logging
import os
import sys
from datetime import date
from pathlib import Path

# Ensure the repo root is on sys.path so 'app' is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Cua Tung bbox
BBOX_WEST = 107.02
BBOX_SOUTH = 17.00
BBOX_EAST = 107.06
BBOX_NORTH = 17.04

# Central latitude for the shoreline (approx coastline latitude)
SHORE_LAT = 17.02

# Number of sample shorelines to create (one per year 2018-2023)
SAMPLE_YEARS = [2018, 2019, 2020, 2021, 2022, 2023]


def _make_shoreline_coords(year: int, drift_per_year_deg: float = -0.0002):
    """
    Generate a simple west-to-east LineString along the Cua Tung coast.

    Simulates gradual erosion by shifting the shoreline landward (north) over time.
    """
    base_year = 2018
    lat_offset = (year - base_year) * drift_per_year_deg

    # 10 points from west to east along the coast
    lons = [BBOX_WEST + i * (BBOX_EAST - BBOX_WEST) / 9 for i in range(10)]
    lats = [SHORE_LAT + lat_offset + 0.001 * ((-1) ** i) for i in range(10)]

    return list(zip(lons, lats))


def _coords_to_wkt(coords):
    pts = ", ".join(f"{lon} {lat}" for lon, lat in coords)
    return f"LINESTRING({pts})"


async def seed():
    """Main seed function."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from sqlalchemy import text

    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://coastwatch:password@localhost:5432/coastwatch_db",
    )

    engine = create_async_engine(database_url, echo=False)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Import models AFTER setting up sys.path
    from app.models.shoreline import Shoreline, ShorelineMethod
    from app.db.base import Base

    async with engine.begin() as conn:
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        except Exception:
            pass
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        # Check if seed data already exists
        from sqlalchemy import select, func
        count = (await session.execute(select(func.count()).select_from(Shoreline))).scalar_one()

        if count >= len(SAMPLE_YEARS):
            logger.info("Seed data already present (%d shorelines). Skipping.", count)
            return

        logger.info("Creating %d sample shorelines for Cua Tung...", len(SAMPLE_YEARS))

        for year in SAMPLE_YEARS:
            coords = _make_shoreline_coords(year)
            wkt = _coords_to_wkt(coords)

            # Use PostGIS ST_GeomFromText to create geometry
            result = await session.execute(
                text("SELECT ST_GeomFromText(:wkt, 4326)"),
                {"wkt": wkt},
            )
            geom_wkb = result.scalar_one()

            sl = Shoreline(
                name=f"Cua Tung Shoreline {year}",
                date=date(year, 7, 15),  # Mid-year
                year=year,
                method=ShorelineMethod.NDWI,
                geometry=geom_wkb,
                area_water_km2=round(2.5 + (year - 2018) * 0.05, 3),
                area_land_km2=round(14.2 - (year - 2018) * 0.05, 3),
                cloud_cover=round(5.0 + (year % 3) * 3, 1),
                source_image_id=f"COPERNICUS/S2_SR/20{year}0715T030631_{year}",
            )
            session.add(sl)
            logger.info("  Added shoreline: %s", sl.name)

        await session.commit()
        logger.info("Seed complete. %d shorelines created.", len(SAMPLE_YEARS))

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
