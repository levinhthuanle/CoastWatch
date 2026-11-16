"""
Feature extraction from Sentinel-2 imagery for ML classification.
"""
import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Feature band list
SPECTRAL_BANDS = ["B2", "B3", "B4", "B8", "B11", "B12"]


def compute_spectral_indices(
    b2: np.ndarray,
    b3: np.ndarray,
    b4: np.ndarray,
    b8: np.ndarray,
    b11: np.ndarray,
    b12: np.ndarray,
) -> Dict[str, np.ndarray]:
    """
    Compute spectral indices from Sentinel-2 bands.

    Args:
        b2..b12: 2-D NumPy arrays of reflectance values (0-1)

    Returns:
        Dict of index name → 2-D array
    """
    eps = 1e-10  # avoid division by zero

    ndwi = (b3 - b8) / (b3 + b8 + eps)
    mndwi = (b3 - b11) / (b3 + b11 + eps)
    ndvi = (b8 - b4) / (b8 + b4 + eps)
    ndsi = (b3 - b11) / (b3 + b11 + eps)  # same as MNDWI; alias
    evi = 2.5 * (b8 - b4) / (b8 + 6 * b4 - 7.5 * b2 + 1 + eps)

    return {
        "NDWI": ndwi,
        "MNDWI": mndwi,
        "NDVI": ndvi,
        "NDSI": ndsi,
        "EVI": evi,
    }


def extract_features_from_arrays(
    bands: Dict[str, np.ndarray],
    labels: Optional[np.ndarray] = None,
) -> pd.DataFrame:
    """
    Build a flat feature DataFrame from band arrays.

    Args:
        bands: Dict band_name → 2-D ndarray
        labels: Optional 2-D ndarray with class labels (0=land, 1=water)

    Returns:
        DataFrame with one row per pixel, columns = bands + indices [+ label]
    """
    height, width = next(iter(bands.values())).shape
    n_pixels = height * width

    b2 = bands.get("B2", np.zeros((height, width)))
    b3 = bands.get("B3", np.zeros((height, width)))
    b4 = bands.get("B4", np.zeros((height, width)))
    b8 = bands.get("B8", np.zeros((height, width)))
    b11 = bands.get("B11", np.zeros((height, width)))
    b12 = bands.get("B12", np.zeros((height, width)))

    indices = compute_spectral_indices(b2, b3, b4, b8, b11, b12)

    data: Dict[str, np.ndarray] = {}

    # Raw bands
    for band_name, arr in bands.items():
        data[band_name] = arr.flatten()

    # Derived indices
    for idx_name, arr in indices.items():
        data[idx_name] = arr.flatten()

    df = pd.DataFrame(data)

    if labels is not None:
        df["label"] = labels.flatten()

    return df


def extract_features_from_image(image, bbox: dict, scale: int = 20) -> pd.DataFrame:
    """
    Extract spectral features from a GEE Sentinel-2 image as a DataFrame.

    Uses GEE's sampleRegion to pull pixel values as a table.

    Args:
        image: ee.Image with bands B2, B3, B4, B8, B11, B12
        bbox: Dict with keys west, south, east, north
        scale: Sampling scale in metres (use ≥20 for manageable output)

    Returns:
        DataFrame with one row per sampled pixel
    """
    import ee  # type: ignore

    from app.services.gee.client import initialize_gee
    initialize_gee()

    region = ee.Geometry.Rectangle(
        [bbox["west"], bbox["south"], bbox["east"], bbox["north"]]
    )

    bands = ["B2", "B3", "B4", "B8", "B11", "B12"]
    subset = image.select(bands)

    sample = subset.sample(
        region=region,
        scale=scale,
        numPixels=5000,
        seed=42,
        geometries=False,
    )

    features_list = sample.getInfo()["features"]
    rows = [f["properties"] for f in features_list]
    df = pd.DataFrame(rows)

    if df.empty:
        logger.warning("No features extracted from image for bbox=%s", bbox)
        return df

    # Normalise reflectance if needed (S2 SR bands should already be 0-1 after /10000)
    for band in bands:
        if band in df.columns and df[band].max() > 10:
            df[band] = df[band] / 10000.0

    b2 = df.get("B2", pd.Series(0.0, index=df.index)).values
    b3 = df.get("B3", pd.Series(0.0, index=df.index)).values
    b4 = df.get("B4", pd.Series(0.0, index=df.index)).values
    b8 = df.get("B8", pd.Series(0.0, index=df.index)).values
    b11 = df.get("B11", pd.Series(0.0, index=df.index)).values
    b12 = df.get("B12", pd.Series(0.0, index=df.index)).values

    indices = compute_spectral_indices(b2, b3, b4, b8, b11, b12)
    for idx_name, arr in indices.items():
        df[idx_name] = arr

    return df
