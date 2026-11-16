"""
Processing Jobs API routes.
"""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.models.job import ProcessingJob
from app.schemas.job import JobListResponse, JobResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("", response_model=JobListResponse)
async def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> JobListResponse:
    """Return a list of recent processing jobs."""
    query = select(ProcessingJob).order_by(ProcessingJob.created_at.desc())

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    jobs = result.scalars().all()

    return JobListResponse(
        total=total,
        items=[JobResponse.model_validate(j) for j in jobs],
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """
    Poll the status of a processing job.

    Returns the job's current status, and the result or error when complete.
    """
    result = await db.execute(
        select(ProcessingJob).where(ProcessingJob.id == job_id)
    )
    job = result.scalar_one_or_none()

    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return JobResponse.model_validate(job)
