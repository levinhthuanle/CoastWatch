"""
Shoreline API routes.
"""
import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.models.job import JobStatus, JobType, ProcessingJob
from app.models.shoreline import Shoreline, ShorelineMethod
from app.schemas.job import JobResponse
from app.schemas.shoreline import (
    ShorelineExtractRequest,
    ShorelineGeoJSONResponse,
    ShorelineListResponse,
    ShorelineResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def _shoreline_to_response(sl: Shoreline) -> ShorelineResponse:
    """Convert a Shoreline ORM object to a response schema."""
    geojson_geom = None
    if sl.geometry is not None:
        try:
            from geoalchemy2.shape import to_shape  # type: ignore
            from shapely.geometry import mapping  # type: ignore
            geojson_geom = mapping(to_shape(sl.geometry))
        except Exception:
            pass

    return ShorelineResponse(
        id=sl.id,
        name=sl.name,
        date=sl.date,
        year=sl.year,
        method=sl.method,
        area_water_km2=sl.area_water_km2,
        area_land_km2=sl.area_land_km2,
        cloud_cover=sl.cloud_cover,
        source_image_id=sl.source_image_id,
        created_at=sl.created_at,
        geometry_geojson=geojson_geom,
    )


@router.get("", response_model=ShorelineListResponse)
async def list_shorelines(
    year: Optional[int] = Query(None, description="Filter by exact year"),
    year_from: Optional[int] = Query(None, description="Filter year >= value"),
    year_to: Optional[int] = Query(None, description="Filter year <= value"),
    method: Optional[ShorelineMethod] = Query(None, description="Filter by extraction method"),
    skip: int = Query(0, ge=0),
    limit: int = Query(5000, ge=1, le=10000),
    db: AsyncSession = Depends(get_db),
) -> ShorelineListResponse:
    """Return a paginated list of all shorelines with optional filters."""
    query = select(Shoreline)

    if year is not None:
        query = query.where(Shoreline.year == year)
    if year_from is not None:
        query = query.where(Shoreline.year >= year_from)
    if year_to is not None:
        query = query.where(Shoreline.year <= year_to)
    if method is not None:
        query = query.where(Shoreline.method == method)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    query = query.order_by(Shoreline.date.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    shorelines = result.scalars().all()

    return ShorelineListResponse(
        total=total,
        items=[_shoreline_to_response(sl) for sl in shorelines],
    )


@router.get("/{shoreline_id}", response_model=ShorelineResponse)
async def get_shoreline(
    shoreline_id: int,
    db: AsyncSession = Depends(get_db),
) -> ShorelineResponse:
    """Return details for a single shoreline including its GeoJSON geometry."""
    result = await db.execute(
        select(Shoreline).where(Shoreline.id == shoreline_id)
    )
    sl = result.scalar_one_or_none()

    if sl is None:
        raise HTTPException(status_code=404, detail=f"Shoreline {shoreline_id} not found")

    return _shoreline_to_response(sl)


@router.get("/{shoreline_id}/geojson", response_model=ShorelineGeoJSONResponse)
async def get_shoreline_geojson(
    shoreline_id: int,
    db: AsyncSession = Depends(get_db),
) -> ShorelineGeoJSONResponse:
    """Export a shoreline as a GeoJSON FeatureCollection."""
    result = await db.execute(
        select(Shoreline).where(Shoreline.id == shoreline_id)
    )
    sl = result.scalar_one_or_none()

    if sl is None:
        raise HTTPException(status_code=404, detail=f"Shoreline {shoreline_id} not found")

    geojson_geom = None
    if sl.geometry is not None:
        try:
            from geoalchemy2.shape import to_shape  # type: ignore
            from shapely.geometry import mapping  # type: ignore
            geojson_geom = mapping(to_shape(sl.geometry))
        except Exception:
            pass

    feature = {
        "type": "Feature",
        "geometry": geojson_geom,
        "properties": {
            "id": sl.id,
            "name": sl.name,
            "date": str(sl.date),
            "year": sl.year,
            "method": sl.method.value if sl.method else None,
            "area_water_km2": sl.area_water_km2,
            "area_land_km2": sl.area_land_km2,
            "cloud_cover": sl.cloud_cover,
        },
    }

    return ShorelineGeoJSONResponse(features=[feature])


@router.post("/extract", response_model=JobResponse, status_code=202)
async def extract_shoreline(
    request: ShorelineExtractRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """
    Trigger an asynchronous GEE shoreline extraction job.

    Returns a job ID that can be polled via GET /api/jobs/{id}.
    """
    job = ProcessingJob(
        type=JobType.EXTRACT_SHORELINE,
        status=JobStatus.PENDING,
        params={
            "bbox": request.bbox.model_dump(),
            "date": request.date,
            "method": request.method.value,
            "year": request.year,
            "max_cloud": request.max_cloud,
        },
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)
    job_id = job.id

    background_tasks.add_task(
        _run_extraction_job,
        job_id=job_id,
        params=job.params,
    )

    return JobResponse(
        id=job.id,
        type=job.type,
        status=job.status,
        params=job.params,
        result=None,
        error=None,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


async def _run_extraction_job(job_id: uuid.UUID, params: dict) -> None:
    """Background task: run GEE extraction and persist result."""
    from app.db.base import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ProcessingJob).where(ProcessingJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        if job is None:
            return

        job.status = JobStatus.RUNNING
        await session.commit()

        try:
            bbox = params["bbox"]
            date_str = params["date"]
            method = params.get("method", "ndwi")
            year = params["year"]
            max_cloud = params.get("max_cloud", 20.0)

            # Run GEE operations in a thread pool to avoid blocking event loop
            loop = asyncio.get_event_loop()

            if method == "random_forest":
                shoreline_geojson = await loop.run_in_executor(
                    None,
                    _extract_with_rf,
                    bbox,
                    date_str,
                    max_cloud,
                )
            else:
                shoreline_geojson = await loop.run_in_executor(
                    None,
                    _extract_with_ndwi,
                    bbox,
                    date_str,
                    max_cloud,
                )

            # Persist shoreline record
            from app.models.shoreline import ShorelineMethod as SM
            from geoalchemy2.shape import from_shape  # type: ignore
            from shapely.geometry import shape  # type: ignore

            try:
                geom_shape = shape(shoreline_geojson) if shoreline_geojson else None
                geom_wkb = from_shape(geom_shape, srid=4326) if geom_shape else None
            except Exception:
                geom_wkb = None

            sl_method = SM(method) if method in SM._value2member_map_ else SM.NDWI

            shoreline = Shoreline(
                name=f"Shoreline {date_str} ({method})",
                date=datetime.strptime(date_str, "%Y-%m-%d").date(),
                year=year,
                method=sl_method,
                geometry=geom_wkb,
                source_image_id=f"S2_{date_str}_{bbox}",
            )
            session.add(shoreline)
            await session.flush()

            job.status = JobStatus.COMPLETED
            job.result = {
                "shoreline_id": shoreline.id,
                "message": "Shoreline extracted successfully",
            }

        except Exception as exc:
            logger.error("Extraction job %s failed: %s", job_id, exc, exc_info=True)
            job.status = JobStatus.FAILED
            job.error = str(exc)

        await session.commit()


def _extract_with_ndwi(bbox: dict, date_str: str, max_cloud: float):
    """Synchronous GEE NDWI extraction (runs in thread pool)."""
    from app.services.gee.sentinel2 import fetch_image
    from app.services.gee.ndwi import extract_shoreline

    image = fetch_image(bbox, date_str, max_cloud=max_cloud)
    geojson = extract_shoreline(image, bbox)

    # Return first feature geometry if FeatureCollection
    if geojson and geojson.get("type") == "FeatureCollection":
        features = geojson.get("features", [])
        if features:
            return features[0]["geometry"]
    return geojson


def _extract_with_rf(bbox: dict, date_str: str, max_cloud: float):
    """Synchronous GEE + RandomForest extraction (runs in thread pool)."""
    from app.services.gee.sentinel2 import fetch_image
    from app.services.ml.features import extract_features_from_image

    image = fetch_image(bbox, date_str, max_cloud=max_cloud)

    # For RF, we fall back to NDWI extraction until a trained model is available
    from app.services.gee.ndwi import extract_shoreline
    geojson = extract_shoreline(image, bbox)

    if geojson and geojson.get("type") == "FeatureCollection":
        features = geojson.get("features", [])
        if features:
            return features[0]["geometry"]
    return geojson
