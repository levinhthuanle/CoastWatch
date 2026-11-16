"""
Open-Meteo Marine + Weather API client.
Free, no API key required, 15-min resolution current + 7-day forecast + historical.
Marine API: https://marine-api.open-meteo.com
Weather API: https://api.open-meteo.com
"""
import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

_LAT = 17.02
_LON = 107.04
_TZ = "Asia/Ho_Chi_Minh"

_MARINE_BASE = "https://marine-api.open-meteo.com/v1/marine"
_WEATHER_BASE = "https://api.open-meteo.com/v1/forecast"
_WEATHER_ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"

_MARINE_HOURLY = "wave_height,wave_direction,wave_period,swell_wave_height,wind_wave_height,ocean_current_velocity,ocean_current_direction,sea_surface_temperature,sea_level_height_msl"
_MARINE_CURRENT = "wave_height,wave_direction,wave_period,sea_surface_temperature,sea_level_height_msl"
_WEATHER_HOURLY = "wind_speed_10m,wind_direction_10m,precipitation"
_WEATHER_CURRENT = "wind_speed_10m,wind_direction_10m"

# Lazily-created per-call client avoids module-level event loop issues
def _make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=15)


async def fetch_current_and_forecast(forecast_days: int = 7) -> Dict[str, Any]:
    """
    Fetch current marine conditions + multi-day hourly forecast.
    Returns merged marine + weather data.
    """
    marine_resp, weather_resp = await _parallel_get(
        _MARINE_BASE,
        {
            "latitude": _LAT,
            "longitude": _LON,
            "hourly": _MARINE_HOURLY,
            "current": _MARINE_CURRENT,
            "forecast_days": forecast_days,
            "timezone": _TZ,
        },
        _WEATHER_BASE,
        {
            "latitude": _LAT,
            "longitude": _LON,
            "hourly": _WEATHER_HOURLY,
            "current": _WEATHER_CURRENT,
            "forecast_days": forecast_days,
            "timezone": _TZ,
        },
    )

    return _merge_marine_weather(marine_resp, weather_resp)


async def fetch_historical(start: date, end: date) -> Dict[str, Any]:
    """
    Fetch hourly historical marine data for a date range.
    Marine archive goes back to 1940; weather archive to 1940 via ERA5.
    """
    start_str = start.isoformat()
    end_str = end.isoformat()

    marine_resp, weather_resp = await _parallel_get(
        _MARINE_BASE,
        {
            "latitude": _LAT,
            "longitude": _LON,
            "hourly": _MARINE_HOURLY,
            "start_date": start_str,
            "end_date": end_str,
            "timezone": _TZ,
        },
        _WEATHER_ARCHIVE,
        {
            "latitude": _LAT,
            "longitude": _LON,
            "hourly": _WEATHER_HOURLY,
            "start_date": start_str,
            "end_date": end_str,
            "timezone": _TZ,
        },
    )

    return _merge_marine_weather(marine_resp, weather_resp)


async def _parallel_get(
    url1: str, params1: Dict, url2: str, params2: Dict
) -> tuple:
    """Fire two GET requests in parallel."""
    import asyncio

    async def _get(url: str, params: Dict) -> Dict:
        async with _make_client() as c:
            r = await c.get(url, params=params)
            r.raise_for_status()
            return r.json()

    r1, r2 = await asyncio.gather(_get(url1, params1), _get(url2, params2))
    return r1, r2


def _merge_marine_weather(marine: Dict, weather: Dict) -> Dict[str, Any]:
    """Merge marine and weather hourly data on a shared time axis."""
    # Build weather lookup by timestamp
    w_hourly = weather.get("hourly", {})
    w_times = w_hourly.get("time", [])
    w_wind_speed = w_hourly.get("wind_speed_10m", [])
    w_wind_dir = w_hourly.get("wind_direction_10m", [])
    w_precip = w_hourly.get("precipitation", [])
    weather_map = {
        t: {
            "wind_speed_kmh": w_wind_speed[i] if i < len(w_wind_speed) else None,
            "wind_direction_deg": w_wind_dir[i] if i < len(w_wind_dir) else None,
            "precipitation_mm": w_precip[i] if i < len(w_precip) else None,
        }
        for i, t in enumerate(w_times)
    }

    m_hourly = marine.get("hourly", {})
    m_times = m_hourly.get("time", [])

    hourly_merged: List[Dict] = []
    for i, t in enumerate(m_times):
        w = weather_map.get(t, {})
        row: Dict[str, Any] = {
            "time": t,
            "wave_height_m": _safe(m_hourly.get("wave_height", []), i),
            "wave_direction_deg": _safe(m_hourly.get("wave_direction", []), i),
            "wave_period_s": _safe(m_hourly.get("wave_period", []), i),
            "swell_wave_height_m": _safe(m_hourly.get("swell_wave_height", []), i),
            "wind_wave_height_m": _safe(m_hourly.get("wind_wave_height", []), i),
            "ocean_current_velocity_kmh": _safe(m_hourly.get("ocean_current_velocity", []), i),
            "ocean_current_direction_deg": _safe(m_hourly.get("ocean_current_direction", []), i),
            "sea_surface_temp_c": _safe(m_hourly.get("sea_surface_temperature", []), i),
            "sea_level_height_m": _safe(m_hourly.get("sea_level_height_msl", []), i),
            "wind_speed_kmh": w.get("wind_speed_kmh"),
            "wind_direction_deg": w.get("wind_direction_deg"),
            "precipitation_mm": w.get("precipitation_mm"),
        }
        hourly_merged.append(row)

    # Current conditions
    current_marine = marine.get("current", {})
    current_weather = weather.get("current", {})
    current = {
        "time": current_marine.get("time"),
        "wave_height_m": current_marine.get("wave_height"),
        "wave_direction_deg": current_marine.get("wave_direction"),
        "wave_period_s": current_marine.get("wave_period"),
        "sea_surface_temp_c": current_marine.get("sea_surface_temperature"),
        "sea_level_height_m": current_marine.get("sea_level_height_msl"),
        "wind_speed_kmh": current_weather.get("wind_speed_10m"),
        "wind_direction_deg": current_weather.get("wind_direction_10m"),
    }

    return {
        "current": current,
        "hourly": hourly_merged,
        "latitude": marine.get("latitude"),
        "longitude": marine.get("longitude"),
        "timezone": marine.get("timezone"),
    }


def _safe(lst: List, i: int) -> Optional[float]:
    try:
        return lst[i]
    except (IndexError, TypeError):
        return None
