"""
Sentinel-2 image fetching and cloud masking utilities.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Sentinel-2 bands of interest
S2_BANDS = ["B2", "B3", "B4", "B8", "B11", "B12"]
S2_BAND_NAMES = ["Blue", "Green", "Red", "NIR", "SWIR1", "SWIR2"]


def mask_s2_clouds(image):
    """
    Apply cloud masking using Sentinel-2 QA60 bitmask band.

    Bit 10 = Opaque clouds
    Bit 11 = Cirrus clouds

    Args:
        image: ee.Image with QA60 band

    Returns:
        Cloud-masked ee.Image
    """
    import ee  # type: ignore

    qa = image.select("QA60")

    # Bits 10 and 11 are clouds and cirrus
    cloud_bit_mask = 1 << 10
    cirrus_bit_mask = 1 << 11

    mask = (
        qa.bitwiseAnd(cloud_bit_mask).eq(0)
        .And(qa.bitwiseAnd(cirrus_bit_mask).eq(0))
    )

    return image.updateMask(mask).divide(10000).copyProperties(
        image, ["system:time_start"]
    )


def fetch_image(
    bbox: Dict,
    date_str: str,
    max_cloud: float = 20.0,
    window_days: int = 30,
):
    """
    Fetch a median-composite Sentinel-2 image for the given area and date.

    Searches within a ±window_days window around date_str, applies cloud masking,
    and returns the median composite clipped to the bounding box.

    Args:
        bbox: Dict with keys west, south, east, north (EPSG:4326)
        date_str: Target date string 'YYYY-MM-DD'
        max_cloud: Maximum cloud cover percentage
        window_days: Number of days before/after date_str to search

    Returns:
        ee.Image with bands B2, B3, B4, B8, B11, B12 (reflectance 0-1)
    """
    import ee  # type: ignore

    from app.services.gee.client import initialize_gee
    initialize_gee()

    region = ee.Geometry.Rectangle(
        [bbox["west"], bbox["south"], bbox["east"], bbox["north"]]
    )

    target_date = datetime.strptime(date_str, "%Y-%m-%d")
    start_date = (target_date - timedelta(days=window_days)).strftime("%Y-%m-%d")
    end_date = (target_date + timedelta(days=window_days)).strftime("%Y-%m-%d")

    logger.info(
        "Fetching Sentinel-2 image for bbox=%s date=%s window=±%d days",
        bbox, date_str, window_days,
    )

    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(region)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", max_cloud))
        .map(mask_s2_clouds)
        .select(S2_BANDS)
    )

    count = collection.size().getInfo()
    logger.info("Found %d Sentinel-2 scenes", count)

    if count == 0:
        raise ValueError(
            f"No Sentinel-2 images found for bbox={bbox} date={date_str} "
            f"max_cloud={max_cloud}%"
        )

    median_image = collection.median().clip(region)
    return median_image


def get_image_metadata(image) -> Dict:
    """
    Extract metadata from a Sentinel-2 image collection item.

    Returns:
        Dict with image_id, date, cloud_cover
    """
    import ee  # type: ignore

    props = image.getInfo().get("properties", {})
    return {
        "image_id": props.get("system:index", ""),
        "cloud_cover": props.get("CLOUDY_PIXEL_PERCENTAGE", 0.0),
    }
