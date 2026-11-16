"""
Google Earth Engine client initialization.
"""
import logging
import os
from typing import List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

_gee_initialized = False


def initialize_gee() -> None:
    """
    Initialize Google Earth Engine authentication.

    Priority:
    1. Service account credentials if GEE_PRIVATE_KEY_FILE is set and exists
    2. Application Default Credentials (ADC) as fallback
    """
    global _gee_initialized

    if _gee_initialized:
        return

    try:
        import ee  # type: ignore

        key_file = settings.GEE_PRIVATE_KEY_FILE
        service_account = settings.GEE_SERVICE_ACCOUNT

        if key_file and os.path.isfile(key_file) and service_account:
            # Use service account credentials
            credentials = ee.ServiceAccountCredentials(
                email=service_account,
                key_file=key_file,
            )
            ee.Initialize(credentials)
            logger.info("GEE initialized with service account: %s", service_account)
        else:
            # Fallback to Application Default Credentials
            ee.Initialize()
            logger.info("GEE initialized with Application Default Credentials")

        _gee_initialized = True

    except Exception as exc:
        logger.error("Failed to initialize Google Earth Engine: %s", exc)
        raise RuntimeError(f"GEE initialization failed: {exc}") from exc


def get_sentinel2_collection(
    bbox: dict,
    start_date: str,
    end_date: str,
    max_cloud: float = 20.0,
):
    """
    Retrieve a Sentinel-2 SR image collection for the given bounding box and date range.

    Args:
        bbox: Dict with keys west, south, east, north (EPSG:4326)
        start_date: Start date string 'YYYY-MM-DD'
        end_date: End date string 'YYYY-MM-DD'
        max_cloud: Maximum cloud cover percentage (0-100)

    Returns:
        ee.ImageCollection filtered by bounds, date, and cloud cover
    """
    import ee  # type: ignore

    initialize_gee()

    region = ee.Geometry.Rectangle(
        [bbox["west"], bbox["south"], bbox["east"], bbox["north"]]
    )

    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(region)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", max_cloud))
    )

    return collection
