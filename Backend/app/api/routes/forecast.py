"""
Forecast API routes.
"""
import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.models.forecast import ShorelineForecast
from app.models.shoreline import Shoreline
from app.schemas.forecast import (
    ForecastGenerateRequest,
    ForecastListResponse,
    ForecastResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)


async def _compute_marine_weights(shorelines: list) -> list:
    """
    Per-observation weights based on seasonal wave energy.
    SW monsoon (calm) → higher weight; NE monsoon peak → lower weight.
    """
    from app.services.marine.risk_scorer import _monsoon_multiplier  # type: ignore
    weights = []
    for sl in shorelines:
        monsoon_factor = _monsoon_multiplier(sl.date.month)
        w = 1.0 / max(monsoon_factor, 0.5)
        weights.append(w)
    return weights


def _geom_to_geojson(geom):
    """Convert a GeoAlchemy2 geometry to a GeoJSON dict."""
    if geom is None:
        return None
    try:
        from geoalchemy2.shape import to_shape  # type: ignore
        from shapely.geometry import mapping  # type: ignore
        return mapping(to_shape(geom))
    except Exception:
        return None


def _forecast_to_response(fc: ShorelineForecast) -> ForecastResponse:
    return ForecastResponse(
        id=fc.id,
        target_year=fc.target_year,
        method=fc.method,
        predicted_geometry=_geom_to_geojson(fc.predicted_geometry),
        confidence_interval_low=_geom_to_geojson(fc.confidence_interval_low),
        confidence_interval_high=_geom_to_geojson(fc.confidence_interval_high),
        rmse=fc.rmse,
        r2_score=fc.r2_score,
        created_at=fc.created_at,
    )


@router.get("", response_model=ForecastListResponse)
async def list_forecasts(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> ForecastListResponse:
    """Return a paginated list of all shoreline forecasts."""
    query = select(ShorelineForecast).order_by(ShorelineForecast.created_at.desc())

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    forecasts = result.scalars().all()

    return ForecastListResponse(
        total=total,
        items=[_forecast_to_response(fc) for fc in forecasts],
    )


@router.get("/{forecast_id}", response_model=ForecastResponse)
async def get_forecast(
    forecast_id: int,
    db: AsyncSession = Depends(get_db),
) -> ForecastResponse:
    """Return details for a single forecast including predicted geometry."""
    result = await db.execute(
        select(ShorelineForecast).where(ShorelineForecast.id == forecast_id)
    )
    fc = result.scalar_one_or_none()

    if fc is None:
        raise HTTPException(status_code=404, detail=f"Forecast {forecast_id} not found")

    return _forecast_to_response(fc)


@router.post("/generate", response_model=ForecastResponse, status_code=201)
async def generate_forecast(
    request: ForecastGenerateRequest,
    db: AsyncSession = Depends(get_db),
) -> ForecastResponse:
    """
    Generate a future shoreline forecast using historical shoreline data.

    Requires at least 2 shorelines with valid geometries in the database.
    """
    # Load all shorelines with geometries, sorted chronologically
    result = await db.execute(
        select(Shoreline)
        .where(Shoreline.geometry.isnot(None))
        .order_by(Shoreline.date.asc())
    )
    shorelines = result.scalars().all()

    if len(shorelines) < 2:
        raise HTTPException(
            status_code=422,
            detail="At least 2 shorelines with valid geometries are required for forecasting",
        )

    # Build history list for the forecast model
    from geoalchemy2.shape import to_shape  # type: ignore
    from shapely.geometry import mapping  # type: ignore

    history = []
    for sl in shorelines:
        try:
            geom = mapping(to_shape(sl.geometry))
            history.append((sl.date, geom))
        except Exception:
            continue

    if len(history) < 2:
        raise HTTPException(
            status_code=422,
            detail="Could not parse geometries from shoreline records",
        )

    # Fit trend model and predict
    try:
        from app.services.analysis.forecast import (
            fit_linear_trend,
            predict_future,
            compute_regression_stats,
        )
        from geoalchemy2.shape import from_shape  # type: ignore
        from shapely.geometry import shape  # type: ignore

        # Marine-enhanced: weight by inverse monsoon intensity
        use_marine = request.method in ("marine_enhanced", "linear_marine")
        sample_weights = None
        if use_marine:
            sample_weights = await _compute_marine_weights(shorelines)
            logger.info("Using marine-enhanced weights: %s", sample_weights)

        model = fit_linear_trend(history, sample_weights=sample_weights)
        prediction = predict_future(model, request.target_year)
        stats = compute_regression_stats(model, history)

        def _geojson_to_geom(geojson_dict):
            if geojson_dict is None:
                return None
            try:
                return from_shape(shape(geojson_dict), srid=4326)
            except Exception:
                return None

        fc = ShorelineForecast(
            target_year=request.target_year,
            method=request.method,
            predicted_geometry=_geojson_to_geom(prediction.get("predicted_geometry")),
            confidence_interval_low=_geojson_to_geom(prediction.get("confidence_interval_low")),
            confidence_interval_high=_geojson_to_geom(prediction.get("confidence_interval_high")),
            rmse=stats.get("rmse"),
            r2_score=stats.get("r2_score"),
        )

    except Exception as exc:
        logger.error("Forecast generation failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Forecast generation failed: {exc}",
        )

    db.add(fc)
    await db.flush()
    await db.refresh(fc)

    return _forecast_to_response(fc)
