"""
Area change and accuracy metrics for shoreline comparison.
"""
import logging
from typing import Dict, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


def compute_area_change(
    mask_t1: np.ndarray,
    mask_t2: np.ndarray,
    pixel_area_m2: float = 100.0,
) -> Dict[str, float]:
    """
    Compute land-lost and land-gained areas between two binary water masks.

    Args:
        mask_t1: 2-D binary array at time 1 (1 = water, 0 = land)
        mask_t2: 2-D binary array at time 2 (1 = water, 0 = land)
        pixel_area_m2: Area of each pixel in square metres (default 10x10 m = 100 m²)

    Returns:
        Dict with area_lost_km2 (land that became water) and area_gained_km2 (water → land)
    """
    if mask_t1.shape != mask_t2.shape:
        raise ValueError(
            f"Masks must have the same shape: {mask_t1.shape} vs {mask_t2.shape}"
        )

    # Pixels that were land (0) at t1 but water (1) at t2 → land lost
    land_to_water = ((mask_t1 == 0) & (mask_t2 == 1)).sum()

    # Pixels that were water (1) at t1 but land (0) at t2 → land gained
    water_to_land = ((mask_t1 == 1) & (mask_t2 == 0)).sum()

    area_lost_km2 = float(land_to_water * pixel_area_m2 / 1e6)
    area_gained_km2 = float(water_to_land * pixel_area_m2 / 1e6)

    return {
        "area_lost_km2": area_lost_km2,
        "area_gained_km2": area_gained_km2,
    }


def compute_iou(
    mask1: np.ndarray,
    mask2: np.ndarray,
    class_value: int = 1,
) -> float:
    """
    Compute Intersection over Union (IoU / Jaccard index) for a given class.

    Args:
        mask1: First binary mask
        mask2: Second binary mask
        class_value: Class to evaluate (default 1 = water)

    Returns:
        IoU score in range [0, 1]
    """
    m1 = mask1 == class_value
    m2 = mask2 == class_value

    intersection = np.logical_and(m1, m2).sum()
    union = np.logical_or(m1, m2).sum()

    if union == 0:
        return 1.0  # Both masks are empty → perfect match

    return float(intersection / union)


def compute_f1(
    mask_pred: np.ndarray,
    mask_true: np.ndarray,
    class_value: int = 1,
) -> float:
    """
    Compute F1 score for the given class.

    Args:
        mask_pred: Predicted binary mask
        mask_true: Ground-truth binary mask
        class_value: Class to evaluate

    Returns:
        F1 score in range [0, 1]
    """
    pred = mask_pred == class_value
    true = mask_true == class_value

    tp = np.logical_and(pred, true).sum()
    fp = np.logical_and(pred, ~true).sum()
    fn = np.logical_and(~pred, true).sum()

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

    if precision + recall == 0:
        return 0.0

    f1 = 2 * precision * recall / (precision + recall)
    return float(f1)
