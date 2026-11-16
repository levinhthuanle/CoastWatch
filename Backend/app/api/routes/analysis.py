"""
Analysis API routes.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.models.analysis import ShorelineAnalysis
from app.models.shoreline import Shoreline
from app.schemas.analysis import (
    AnalysisCompareRequest,
    AnalysisListResponse,
    AnalysisResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# Cửa Tùng AOI — clip shorelines to this before transect analysis
_CUA_TUNG_BBOX = (106.9, 16.9, 107.2, 17.1)  # (min_lon, min_lat, max_lon, max_lat)


def _clip_geojson_to_bbox(geojson: dict, bbox: tuple) -> dict | None:
    """Return the intersection of a GeoJSON geometry with a bounding box.

    Returns None if there's no intersection or shapely is unavailable.
    """
    try:
        from shapely.geometry import box, mapping, shape  # type: ignore

        aoi = box(*bbox)
        geom = shape(geojson)
        clipped = geom.intersection(aoi)
        if clipped.is_empty:
            return None
        return mapping(clipped)
    except Exception as exc:
        logger.debug("Could not clip geometry: %s", exc)
        return geojson


def _analysis_to_response(analysis: ShorelineAnalysis) -> AnalysisResponse:
    return AnalysisResponse(
        id=analysis.id,
        shoreline_from_id=analysis.shoreline_from_id,
        shoreline_to_id=analysis.shoreline_to_id,
        epr_m_per_year=analysis.epr_m_per_year,
        total_change_m=analysis.total_change_m,
        area_lost_km2=analysis.area_lost_km2,
        area_gained_km2=analysis.area_gained_km2,
        transects_geojson=analysis.transects_geojson,
        iou_score=analysis.iou_score,
        f1_score=analysis.f1_score,
        created_at=analysis.created_at,
    )


@router.get("", response_model=AnalysisListResponse)
async def list_analyses(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> AnalysisListResponse:
    """Return a paginated list of all shoreline analyses."""
    query = select(ShorelineAnalysis).order_by(ShorelineAnalysis.created_at.desc())

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    analyses = result.scalars().all()

    return AnalysisListResponse(
        total=total,
        items=[_analysis_to_response(a) for a in analyses],
    )


@router.get("/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(
    analysis_id: int,
    db: AsyncSession = Depends(get_db),
) -> AnalysisResponse:
    """Return details for a single analysis including transect data."""
    result = await db.execute(
        select(ShorelineAnalysis).where(ShorelineAnalysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()

    if analysis is None:
        raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found")

    return _analysis_to_response(analysis)


@router.post("/compare", response_model=AnalysisResponse, status_code=201)
async def compare_shorelines(
    request: AnalysisCompareRequest,
    db: AsyncSession = Depends(get_db),
) -> AnalysisResponse:
    """
    Compare two shorelines and compute EPR, area change, and transect metrics.
    """
    # Load both shorelines
    r1 = await db.execute(
        select(Shoreline).where(Shoreline.id == request.shoreline_from_id)
    )
    sl_from = r1.scalar_one_or_none()
    if sl_from is None:
        raise HTTPException(
            status_code=404,
            detail=f"Shoreline {request.shoreline_from_id} not found",
        )

    r2 = await db.execute(
        select(Shoreline).where(Shoreline.id == request.shoreline_to_id)
    )
    sl_to = r2.scalar_one_or_none()
    if sl_to is None:
        raise HTTPException(
            status_code=404,
            detail=f"Shoreline {request.shoreline_to_id} not found",
        )

    # Ensure chronological order
    date_from = sl_from.date
    date_to = sl_to.date

    if date_from >= date_to:
        raise HTTPException(
            status_code=400,
            detail="shoreline_from must be earlier than shoreline_to",
        )

    years_elapsed = (date_to - date_from).days / 365.25

    # Convert geometries to GeoJSON
    def _geom_to_geojson(geom):
        if geom is None:
            return None
        try:
            from geoalchemy2.shape import to_shape  # type: ignore
            from shapely.geometry import mapping  # type: ignore
            return mapping(to_shape(geom))
        except Exception:
            return None

    geom_from_geojson = _geom_to_geojson(sl_from.geometry)
    geom_to_geojson = _geom_to_geojson(sl_to.geometry)

    # Clip to AOI to avoid running transects on global coastline data
    if geom_from_geojson:
        geom_from_geojson = _clip_geojson_to_bbox(geom_from_geojson, _CUA_TUNG_BBOX) or geom_from_geojson
    if geom_to_geojson:
        geom_to_geojson = _clip_geojson_to_bbox(geom_to_geojson, _CUA_TUNG_BBOX) or geom_to_geojson

    # Generate transects and compute displacement
    epr_m_per_year = None
    total_change_m = None
    transects_geojson = None

    if geom_from_geojson and geom_to_geojson:
        try:
            from app.services.analysis.transects import (
                generate_transects,
                measure_displacement,
                compute_epr,
            )

            transects = generate_transects(geom_from_geojson)
            displacements = measure_displacement(transects, geom_from_geojson, geom_to_geojson)
            epr_values = compute_epr(displacements, years_elapsed)

            # Annotate transects with EPR values
            for i, transect in enumerate(transects):
                transect["properties"]["epr_m_per_year"] = (
                    epr_values[i] if i < len(epr_values) else None
                )
                transect["properties"]["displacement_m"] = (
                    displacements[i] if i < len(displacements) else None
                )

            transects_geojson = {"type": "FeatureCollection", "features": transects}

            import statistics
            epr_m_per_year = statistics.mean(epr_values) if epr_values else None
            total_change_m = statistics.mean(displacements) if displacements else None

        except Exception as exc:
            logger.warning("Could not compute transect metrics: %s", exc)

    # Create and persist analysis record
    analysis = ShorelineAnalysis(
        shoreline_from_id=sl_from.id,
        shoreline_to_id=sl_to.id,
        epr_m_per_year=epr_m_per_year,
        total_change_m=total_change_m,
        transects_geojson=transects_geojson,
    )
    db.add(analysis)
    await db.flush()
    await db.refresh(analysis)

    return _analysis_to_response(analysis)


@router.post("/auto-compare", status_code=200)
async def auto_compare_all(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    So sánh tất cả cặp shoreline liền kề theo năm (2020→2021, 2021→2022, ...).
    Bỏ qua cặp đã có analysis. Trả về số cặp đã xử lý.
    """
    result = await db.execute(
        select(Shoreline).order_by(Shoreline.year.asc())
    )
    shorelines = result.scalars().all()

    if len(shorelines) < 2:
        return {"processed": 0, "skipped": 0, "message": "Cần ít nhất 2 đường bờ biển"}

    # Tìm các cặp đã có analysis
    existing = await db.execute(
        select(ShorelineAnalysis.shoreline_from_id, ShorelineAnalysis.shoreline_to_id)
    )
    existing_pairs = {(r[0], r[1]) for r in existing.all()}

    processed = 0
    skipped = 0
    errors = []

    for i in range(len(shorelines) - 1):
        sl_from = shorelines[i]
        sl_to = shorelines[i + 1]

        if (sl_from.id, sl_to.id) in existing_pairs:
            skipped += 1
            continue

        if sl_from.date >= sl_to.date:
            skipped += 1
            continue

        years_elapsed = (sl_to.date - sl_from.date).days / 365.25

        def _geom_to_geojson(geom):
            if geom is None:
                return None
            try:
                from geoalchemy2.shape import to_shape
                from shapely.geometry import mapping
                return mapping(to_shape(geom))
            except Exception:
                return None

        geom_from = _geom_to_geojson(sl_from.geometry)
        geom_to = _geom_to_geojson(sl_to.geometry)

        # Clip to AOI before transect analysis
        if geom_from:
            geom_from = _clip_geojson_to_bbox(geom_from, _CUA_TUNG_BBOX) or geom_from
        if geom_to:
            geom_to = _clip_geojson_to_bbox(geom_to, _CUA_TUNG_BBOX) or geom_to

        epr_m_per_year = None
        total_change_m = None
        transects_geojson = None

        if geom_from and geom_to:
            try:
                from app.services.analysis.transects import (
                    generate_transects,
                    measure_displacement,
                    compute_epr,
                )
                import statistics

                transects = generate_transects(geom_from)
                displacements = measure_displacement(transects, geom_from, geom_to)
                epr_values = compute_epr(displacements, years_elapsed)

                for j, transect in enumerate(transects):
                    transect["properties"]["epr_m_per_year"] = epr_values[j] if j < len(epr_values) else None
                    transect["properties"]["displacement_m"] = displacements[j] if j < len(displacements) else None

                transects_geojson = {"type": "FeatureCollection", "features": transects}
                epr_m_per_year = statistics.mean(epr_values) if epr_values else None
                total_change_m = statistics.mean(displacements) if displacements else None

            except Exception as exc:
                errors.append(f"{sl_from.year}→{sl_to.year}: {exc}")
                logger.warning("auto-compare %s→%s failed: %s", sl_from.year, sl_to.year, exc)

        analysis = ShorelineAnalysis(
            shoreline_from_id=sl_from.id,
            shoreline_to_id=sl_to.id,
            epr_m_per_year=epr_m_per_year,
            total_change_m=total_change_m,
            transects_geojson=transects_geojson,
        )
        db.add(analysis)
        processed += 1

    await db.commit()

    return {
        "processed": processed,
        "skipped": skipped,
        "errors": errors,
        "message": f"Đã tạo {processed} phân tích, bỏ qua {skipped} cặp đã có hoặc không hợp lệ",
    }
