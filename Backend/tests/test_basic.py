"""
Basic smoke tests for CoastWatch backend.
"""
import pytest


def test_config_loads():
    """Settings should load without errors."""
    from app.core.config import settings
    assert settings.APP_NAME == "CoastWatch API"


def test_spectral_indices():
    """Spectral index computations should produce correct shapes."""
    import numpy as np
    from app.services.ml.features import compute_spectral_indices

    shape = (10, 10)
    b2 = np.random.rand(*shape) * 0.3
    b3 = np.random.rand(*shape) * 0.3
    b4 = np.random.rand(*shape) * 0.3
    b8 = np.random.rand(*shape) * 0.5
    b11 = np.random.rand(*shape) * 0.4
    b12 = np.random.rand(*shape) * 0.3

    indices = compute_spectral_indices(b2, b3, b4, b8, b11, b12)
    assert "NDWI" in indices
    assert "MNDWI" in indices
    assert "NDVI" in indices
    assert indices["NDWI"].shape == shape


def test_area_metrics():
    """Area change computation should work correctly."""
    import numpy as np
    from app.services.analysis.metrics import compute_area_change, compute_iou

    mask1 = np.array([[0, 0, 1, 1], [0, 0, 1, 1]])
    mask2 = np.array([[0, 1, 1, 1], [0, 1, 1, 1]])

    changes = compute_area_change(mask1, mask2, pixel_area_m2=100.0)
    assert changes["area_lost_km2"] >= 0
    assert changes["area_gained_km2"] >= 0

    iou = compute_iou(mask1, mask2)
    assert 0.0 <= iou <= 1.0


def test_rf_evaluate():
    """RF evaluate should return expected metric keys."""
    import numpy as np
    from app.services.ml.random_forest import RandomForestModel

    y_true = np.array([0, 1, 1, 0, 1, 0, 0, 1])
    y_pred = np.array([0, 1, 0, 0, 1, 1, 0, 1])

    metrics = RandomForestModel.evaluate(y_true, y_pred)
    assert set(metrics.keys()) == {"iou", "f1", "precision", "recall"}
    assert all(0.0 <= v <= 1.0 for v in metrics.values())


def test_epr_computation():
    """EPR should equal displacement / years."""
    from app.services.analysis.transects import compute_epr

    displacements = [100.0, -50.0, 200.0]
    years = 5.0

    epr = compute_epr(displacements, years)
    assert epr == [20.0, -10.0, 40.0]


def test_rf_train_predict():
    """RF model should train on synthetic data and produce predictions."""
    import numpy as np
    import pandas as pd
    from app.services.ml.random_forest import RandomForestModel

    rng = np.random.default_rng(42)
    n = 300
    df = pd.DataFrame({
        "B2": rng.random(n),
        "B3": rng.random(n),
        "B4": rng.random(n),
        "B8": rng.random(n),
        "B11": rng.random(n),
        "B12": rng.random(n),
        "NDWI": rng.uniform(-1, 1, n),
        "MNDWI": rng.uniform(-1, 1, n),
        "NDVI": rng.uniform(-1, 1, n),
        "EVI": rng.uniform(-1, 1, n),
        "label": rng.integers(0, 2, n),
    })

    model = RandomForestModel(n_estimators=10)
    metrics = model.train(df)

    assert "f1" in metrics
    X = df[["B2", "B3", "B4", "B8", "B11", "B12", "NDWI", "MNDWI", "NDVI", "EVI"]].values
    preds = model.predict(X)
    assert preds.shape == (n,)
    assert set(preds).issubset({0, 1})
