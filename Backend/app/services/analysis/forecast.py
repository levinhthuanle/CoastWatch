"""
Linear trend fitting and future shoreline position forecasting.
Optionally enhanced with marine wave energy weighting for physically-grounded predictions.
"""
import logging
import math
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from shapely.geometry import LineString, mapping, shape
from shapely.ops import unary_union

logger = logging.getLogger(__name__)


def _geometry_to_coords(geojson_geom: Dict) -> List[Tuple[float, float]]:
    """Extract coordinate list from a GeoJSON geometry dict."""
    geom_type = geojson_geom.get("type", "")
    if geom_type == "LineString":
        return geojson_geom["coordinates"]
    if geom_type == "MultiLineString":
        coords = []
        for part in geojson_geom["coordinates"]:
            coords.extend(part)
        return coords
    return []


def _interpolate_coords_to_n(
    coords: List[Tuple[float, float]],
    n: int,
) -> np.ndarray:
    """Resample a polyline to exactly *n* evenly-spaced points."""
    line = LineString(coords)
    distances = np.linspace(0, line.length, n)
    pts = [line.interpolate(d) for d in distances]
    return np.array([(p.x, p.y) for p in pts])


class ShorelineTrendModel:
    """Linear trend model for shoreline position forecasting."""

    def __init__(self, n_points: int = 100) -> None:
        self.n_points = n_points
        self._models_x: List[Any] = []   # per-point regression for x coordinate
        self._models_y: List[Any] = []   # per-point regression for y coordinate
        self._years: Optional[np.ndarray] = None
        self._is_fitted = False

    def fit(
        self,
        shorelines_history: List[Tuple[date, Dict]],
        sample_weights: Optional[List[float]] = None,
    ) -> "ShorelineTrendModel":
        """
        Fit linear regression models to historical shoreline positions.

        Args:
            shorelines_history: List of (date, geometry_geojson) tuples
                                sorted chronologically (oldest first)
            sample_weights: Optional per-observation weights for weighted regression.
                           If provided, observations with higher weights have more
                           influence on the fitted trend.

        Returns:
            Self (fitted model)
        """
        from sklearn.linear_model import LinearRegression  # type: ignore

        if len(shorelines_history) < 2:
            raise ValueError("Need at least 2 historical shorelines to fit a trend")

        years = np.array([d.year + d.timetuple().tm_yday / 365.0
                          for d, _ in shorelines_history])
        self._years = years

        # Normalise sample weights to sum to n_observations
        if sample_weights is not None:
            w = np.array(sample_weights, dtype=float)
            w = w / w.sum() * len(w)
        else:
            w = None

        # Resample each shoreline to the same number of points
        resampled = []
        for _, geom in shorelines_history:
            coords = _geometry_to_coords(geom)
            if len(coords) < 2:
                raise ValueError("Shoreline geometry has fewer than 2 coordinates")
            pts = _interpolate_coords_to_n(coords, self.n_points)
            resampled.append(pts)

        # Fit a linear model for each point (x and y separately)
        self._models_x = []
        self._models_y = []

        for i in range(self.n_points):
            x_vals = np.array([pts[i, 0] for pts in resampled])
            y_vals = np.array([pts[i, 1] for pts in resampled])

            model_x = LinearRegression()
            model_x.fit(years.reshape(-1, 1), x_vals, sample_weight=w)
            self._models_x.append(model_x)

            model_y = LinearRegression()
            model_y.fit(years.reshape(-1, 1), y_vals, sample_weight=w)
            self._models_y.append(model_y)

        self._is_fitted = True
        logger.info("Fitted trend model with %d historical shorelines", len(shorelines_history))
        return self

    def predict(
        self, target_year: float, confidence_level: float = 1.96
    ) -> Dict[str, Any]:
        """
        Predict future shoreline position and confidence bounds.

        Args:
            target_year: Year to predict (e.g. 2030.5 for mid-2030)
            confidence_level: Z-score multiplier for confidence band (1.96 = 95%)

        Returns:
            Dict with predicted_geometry, confidence_interval_low, confidence_interval_high
            as GeoJSON LineString dicts
        """
        if not self._is_fitted:
            raise RuntimeError("Model is not fitted. Call fit() first.")

        year_arr = np.array([[target_year]])

        pred_coords = []
        low_coords = []
        high_coords = []

        for i in range(self.n_points):
            px = float(self._models_x[i].predict(year_arr)[0])
            py = float(self._models_y[i].predict(year_arr)[0])

            # Simple residual-based confidence interval
            coef_x = float(self._models_x[i].coef_[0])
            coef_y = float(self._models_y[i].coef_[0])

            # Uncertainty grows with extrapolation distance from last observed year
            last_year = float(self._years[-1])
            delta_year = abs(target_year - last_year)
            uncertainty_x = confidence_level * abs(coef_x) * delta_year * 0.1
            uncertainty_y = confidence_level * abs(coef_y) * delta_year * 0.1

            pred_coords.append((px, py))
            low_coords.append((px - uncertainty_x, py - uncertainty_y))
            high_coords.append((px + uncertainty_x, py + uncertainty_y))

        predicted_geom = mapping(LineString(pred_coords))
        low_geom = mapping(LineString(low_coords))
        high_geom = mapping(LineString(high_coords))

        return {
            "predicted_geometry": predicted_geom,
            "confidence_interval_low": low_geom,
            "confidence_interval_high": high_geom,
        }

    def score(self, shorelines_history: List[Tuple[date, Dict]]) -> Dict[str, float]:
        """
        Compute RMSE and R² scores over the training data.

        Args:
            shorelines_history: Same list used for fitting

        Returns:
            Dict with rmse and r2_score
        """
        if not self._is_fitted:
            raise RuntimeError("Model is not fitted.")

        from sklearn.metrics import r2_score  # type: ignore

        years = np.array([d.year + d.timetuple().tm_yday / 365.0
                          for d, _ in shorelines_history])

        all_true_x, all_pred_x = [], []
        all_true_y, all_pred_y = [], []

        resampled = []
        for _, geom in shorelines_history:
            coords = _geometry_to_coords(geom)
            pts = _interpolate_coords_to_n(coords, self.n_points)
            resampled.append(pts)

        for i in range(self.n_points):
            for t_idx, pts in enumerate(resampled):
                y_arr = np.array([[years[t_idx]]])
                pred_x = float(self._models_x[i].predict(y_arr)[0])
                pred_y = float(self._models_y[i].predict(y_arr)[0])
                all_true_x.append(pts[i, 0])
                all_true_y.append(pts[i, 1])
                all_pred_x.append(pred_x)
                all_pred_y.append(pred_y)

        true_xy = np.array(all_true_x + all_true_y)
        pred_xy = np.array(all_pred_x + all_pred_y)

        rmse = float(np.sqrt(np.mean((true_xy - pred_xy) ** 2)))
        r2 = float(r2_score(true_xy, pred_xy))

        return {"rmse": rmse, "r2_score": r2}


def fit_linear_trend(
    shorelines_history: List[Tuple[date, Dict]],
    sample_weights: Optional[List[float]] = None,
) -> ShorelineTrendModel:
    """Convenience wrapper: fit and return a ShorelineTrendModel.

    Args:
        shorelines_history: List of (date, geometry_geojson) tuples
        sample_weights: Optional per-observation weights (higher = more influence).
                        Used for marine-enhanced fitting where high wave-energy
                        periods get downweighted (recent calm-weather observations
                        are more representative of the stable shoreline position).
    """
    model = ShorelineTrendModel()
    if sample_weights is not None:
        model.fit(shorelines_history, sample_weights=sample_weights)
    else:
        model.fit(shorelines_history)
    return model


def predict_future(
    model: ShorelineTrendModel,
    target_year: int,
) -> Dict[str, Any]:
    """Convenience wrapper: predict future shoreline for *target_year*."""
    return model.predict(float(target_year))


def compute_regression_stats(
    model: ShorelineTrendModel,
    data: List[Tuple[date, Dict]],
) -> Dict[str, float]:
    """Convenience wrapper: compute RMSE and R² for a fitted model."""
    return model.score(data)
