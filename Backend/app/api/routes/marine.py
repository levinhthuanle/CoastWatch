"""
Marine conditions API routes.
Data from Open-Meteo Marine API — free, no API key required.
"""
import logging
from datetime import date, timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, func

from app.services.marine.open_meteo import fetch_current_and_forecast, fetch_historical
from app.services.marine.risk_scorer import score_erosion_risk, classify_wave_energy_7day
from app.db.base import AsyncSessionLocal
from app.models.analysis import ShorelineAnalysis

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/current")
async def get_current_conditions() -> Dict[str, Any]:
    """
    Get current marine conditions + 7-day hourly forecast for Cửa Tùng.
    Includes erosion risk assessment based on current wave energy.
    """
    try:
        data = await fetch_current_and_forecast(forecast_days=7)
    except Exception as e:
        logger.error("Failed to fetch marine data: %s", e)
        raise HTTPException(status_code=502, detail=f"Marine API unavailable: {e}")

    current = data["current"]

    # Fetch latest EPR from DB to inform risk score
    epr = await _get_latest_epr()

    risk = score_erosion_risk(
        wave_height_m=current.get("wave_height_m"),
        swell_wave_height_m=None,
        wind_wave_height_m=None,
        wind_speed_kmh=current.get("wind_speed_kmh"),
        timestamp=current.get("time"),
        historical_epr_m_per_year=epr,
    )

    # 7-day daily risk summary
    daily_risk = classify_wave_energy_7day(data["hourly"])

    return {
        "current": current,
        "risk": risk,
        "daily_forecast": daily_risk["daily"],
        "hourly_forecast": data["hourly"][:72],  # 3 days of hourly = 72 points
        "location": {
            "name": "Cửa Tùng, Quảng Trị",
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
        },
    }


@router.get("/forecast")
async def get_marine_forecast(
    days: int = Query(default=7, ge=1, le=16),
) -> Dict[str, Any]:
    """
    Get extended marine forecast (up to 16 days).
    """
    try:
        data = await fetch_current_and_forecast(forecast_days=days)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Marine API unavailable: {e}")

    daily = classify_wave_energy_7day(data["hourly"])
    return {
        "hourly": data["hourly"],
        "daily": daily["daily"],
    }


@router.get("/historical")
async def get_marine_historical(
    days: int = Query(default=30, ge=7, le=365),
) -> Dict[str, Any]:
    """
    Get historical marine conditions for the past N days.
    Useful for correlating with shoreline change observations.
    """
    end = date.today() - timedelta(days=1)  # archive has 1-day lag
    start = end - timedelta(days=days - 1)
    try:
        data = await fetch_historical(start, end)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Marine archive unavailable: {e}")

    daily = classify_wave_energy_7day(data["hourly"])
    return {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "hourly": data["hourly"],
        "daily": daily["daily"],
    }


@router.get("/risk")
async def get_erosion_risk() -> Dict[str, Any]:
    """
    Current erosion risk assessment combining marine conditions + historical EPR trend.
    """
    try:
        data = await fetch_current_and_forecast(forecast_days=1)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Marine API unavailable: {e}")

    current = data["current"]
    epr = await _get_latest_epr()

    # Find peak swell from next 24h
    next_24h = data["hourly"][:24]
    max_swell = max(
        (r["swell_wave_height_m"] or 0 for r in next_24h), default=0.0
    )
    max_wind_wave = max(
        (r["wind_wave_height_m"] or 0 for r in next_24h), default=0.0
    )

    risk = score_erosion_risk(
        wave_height_m=current.get("wave_height_m"),
        swell_wave_height_m=max_swell,
        wind_wave_height_m=max_wind_wave,
        wind_speed_kmh=current.get("wind_speed_kmh"),
        timestamp=current.get("time"),
        historical_epr_m_per_year=epr,
    )

    return {
        **risk,
        "current_wave_height_m": current.get("wave_height_m"),
        "current_wind_speed_kmh": current.get("wind_speed_kmh"),
        "historical_epr_m_per_year": epr,
        "timestamp": current.get("time"),
    }


async def _get_latest_epr() -> Optional[float]:
    """Fetch the most recent EPR value from the analysis table."""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ShorelineAnalysis.epr_m_per_year)
                .where(ShorelineAnalysis.epr_m_per_year.isnot(None))
                .order_by(ShorelineAnalysis.created_at.desc())
                .limit(1)
            )
            row = result.scalar_one_or_none()
            return float(row) if row is not None else None
    except Exception:
        return None
