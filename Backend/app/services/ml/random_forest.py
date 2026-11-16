"""
Random Forest classifier for water/land pixel classification.
"""
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    f1_score,
    jaccard_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

# Feature columns used for training / inference
FEATURE_COLS = [
    "B2", "B3", "B4", "B8", "B11", "B12",
    "NDWI", "MNDWI", "NDVI", "EVI",
]

DEFAULT_MODEL_PATH = Path("/app/models/rf_coastwatch.joblib")


class RandomForestModel:
    """Random Forest wrapper for water/land classification."""

    def __init__(
        self,
        n_estimators: int = 200,
        max_depth: Optional[int] = None,
        random_state: int = 42,
    ) -> None:
        self.clf = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=random_state,
            n_jobs=-1,
            class_weight="balanced",
        )
        self.scaler = StandardScaler()
        self.feature_cols = FEATURE_COLS
        self._is_trained = False

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(self, features_df: pd.DataFrame) -> Dict[str, float]:
        """
        Train the classifier on labelled pixel features.

        Args:
            features_df: DataFrame with feature columns + 'label' column
                         (0 = land, 1 = water)

        Returns:
            Dict with training metrics (accuracy, f1, etc.)
        """
        if "label" not in features_df.columns:
            raise ValueError("features_df must contain a 'label' column")

        available_cols = [c for c in self.feature_cols if c in features_df.columns]
        if not available_cols:
            raise ValueError(
                f"No expected feature columns found. Expected: {self.feature_cols}"
            )

        X = features_df[available_cols].fillna(0).values
        y = features_df["label"].values

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        self.clf.fit(X_train_scaled, y_train)
        self._is_trained = True
        self.feature_cols = available_cols

        y_pred = self.clf.predict(X_test_scaled)
        metrics = self.evaluate(y_test, y_pred)

        logger.info("Model trained — test metrics: %s", metrics)
        return metrics

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    def predict(self, image_array: np.ndarray) -> np.ndarray:
        """
        Classify image pixels as water (1) or land (0).

        Args:
            image_array: 3-D array (bands, height, width) or 2-D (n_pixels, bands)

        Returns:
            1-D array of class labels (0 or 1) per pixel
        """
        if not self._is_trained:
            raise RuntimeError("Model is not trained. Call train() or load() first.")

        if image_array.ndim == 3:
            n_bands, height, width = image_array.shape
            X = image_array.reshape(n_bands, -1).T  # (n_pixels, n_bands)
        else:
            X = image_array

        X_scaled = self.scaler.transform(X)
        predictions = self.clf.predict(X_scaled)
        return predictions

    def predict_proba(self, image_array: np.ndarray) -> np.ndarray:
        """Return class probability for water class."""
        if not self._is_trained:
            raise RuntimeError("Model is not trained.")

        if image_array.ndim == 3:
            n_bands, height, width = image_array.shape
            X = image_array.reshape(n_bands, -1).T
        else:
            X = image_array

        X_scaled = self.scaler.transform(X)
        return self.clf.predict_proba(X_scaled)[:, 1]

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    @staticmethod
    def evaluate(
        y_true: np.ndarray,
        y_pred: np.ndarray,
    ) -> Dict[str, float]:
        """
        Compute classification metrics.

        Returns:
            Dict with iou, f1, precision, recall
        """
        iou = float(jaccard_score(y_true, y_pred, zero_division=0))
        f1 = float(f1_score(y_true, y_pred, zero_division=0))
        precision = float(precision_score(y_true, y_pred, zero_division=0))
        recall = float(recall_score(y_true, y_pred, zero_division=0))

        return {
            "iou": iou,
            "f1": f1,
            "precision": precision,
            "recall": recall,
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: Optional[Path] = None) -> str:
        """Serialize the model to disk using joblib."""
        save_path = path or DEFAULT_MODEL_PATH
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        joblib.dump(
            {"clf": self.clf, "scaler": self.scaler, "feature_cols": self.feature_cols},
            save_path,
        )
        logger.info("Model saved to %s", save_path)
        return str(save_path)

    def load(self, path: Optional[Path] = None) -> None:
        """Load a previously serialized model from disk."""
        load_path = path or DEFAULT_MODEL_PATH
        load_path = Path(load_path)

        if not load_path.exists():
            raise FileNotFoundError(f"Model file not found: {load_path}")

        payload = joblib.load(load_path)
        self.clf = payload["clf"]
        self.scaler = payload["scaler"]
        self.feature_cols = payload.get("feature_cols", FEATURE_COLS)
        self._is_trained = True
        logger.info("Model loaded from %s", load_path)
