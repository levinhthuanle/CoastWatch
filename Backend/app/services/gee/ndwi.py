"""
NDWI / MNDWI computation and shoreline extraction from Sentinel-2 imagery.
"""
import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def compute_ndwi(image):
    """
    Compute Normalized Difference Water Index (NDWI).

    NDWI = (Green - NIR) / (Green + NIR)
         = (B3 - B8) / (B3 + B8)

    Positive values indicate water, negative indicate land.

    Args:
        image: ee.Image with B3 (Green) and B8 (NIR) bands

    Returns:
        ee.Image single-band NDWI image
    """
    import ee  # type: ignore

    ndwi = image.normalizedDifference(["B3", "B8"]).rename("NDWI")
    return ndwi


def compute_mndwi(image):
    """
    Compute Modified Normalized Difference Water Index (MNDWI).

    MNDWI = (Green - SWIR1) / (Green + SWIR1)
           = (B3 - B11) / (B3 + B11)

    Better at suppressing built-up area noise than NDWI.

    Args:
        image: ee.Image with B3 (Green) and B11 (SWIR1) bands

    Returns:
        ee.Image single-band MNDWI image
    """
    import ee  # type: ignore

    mndwi = image.normalizedDifference(["B3", "B11"]).rename("MNDWI")
    return mndwi


def compute_water_mask(image, threshold: float = 0.0, use_mndwi: bool = True):
    """
    Create a binary water/land mask from a Sentinel-2 image.

    Args:
        image: ee.Image with relevant spectral bands
        threshold: Index threshold separating water (>= threshold) from land
        use_mndwi: If True, use MNDWI; otherwise NDWI

    Returns:
        ee.Image binary mask (1 = water, 0 = land)
    """
    import ee  # type: ignore

    if use_mndwi:
        index = compute_mndwi(image)
    else:
        index = compute_ndwi(image)

    water_mask = index.gte(threshold).rename("water_mask")
    return water_mask


def extract_shoreline(
    image,
    bbox: Dict,
    threshold: float = 0.0,
    scale: int = 10,
) -> Dict[str, Any]:
    """
    Extract shoreline as a GeoJSON LineString from a Sentinel-2 image.

    The approach:
    1. Compute MNDWI water mask
    2. Convert binary mask to vector polygons
    3. Extract the outer boundary as LineString(s)

    Args:
        image: ee.Image with relevant spectral bands
        bbox: Dict with keys west, south, east, north
        threshold: Index threshold for water/land separation
        scale: Pixel scale in meters (10m for Sentinel-2)

    Returns:
        GeoJSON FeatureCollection dict with shoreline LineString geometry
    """
    import ee  # type: ignore

    region = ee.Geometry.Rectangle(
        [bbox["west"], bbox["south"], bbox["east"], bbox["north"]]
    )

    water_mask = compute_water_mask(image, threshold=threshold)

    # Convert water pixels to vector polygons
    vectors = water_mask.selfMask().reduceToVectors(
        geometry=region,
        scale=scale,
        geometryType="polygon",
        eightConnected=True,
        labelProperty="water",
        reducer=ee.Reducer.countEvery(),
    )

    # Extract boundary as lines
    boundaries = vectors.map(lambda f: f.set(
        "geometry", f.geometry().boundary(1)
    ))

    geojson_str = boundaries.getInfo()
    return geojson_str


def get_water_area_km2(image, bbox: Dict, scale: int = 10) -> Dict[str, float]:
    """
    Compute water and land areas in km² within a bounding box.

    Args:
        image: ee.Image with relevant spectral bands
        bbox: Dict with keys west, south, east, north
        scale: Pixel scale in metres

    Returns:
        Dict with keys area_water_km2 and area_land_km2
    """
    import ee  # type: ignore

    region = ee.Geometry.Rectangle(
        [bbox["west"], bbox["south"], bbox["east"], bbox["north"]]
    )

    water_mask = compute_water_mask(image)

    pixel_area = ee.Image.pixelArea()
    water_area = water_mask.multiply(pixel_area).reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=region,
        scale=scale,
        maxPixels=1e10,
    )

    area_m2 = water_area.getInfo().get("water_mask", 0)
    total_area_m2 = (
        pixel_area.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=region,
            scale=scale,
            maxPixels=1e10,
        ).getInfo().get("area", 0)
    )

    area_water_km2 = area_m2 / 1e6
    area_land_km2 = (total_area_m2 - area_m2) / 1e6

    return {"area_water_km2": area_water_km2, "area_land_km2": area_land_km2}
