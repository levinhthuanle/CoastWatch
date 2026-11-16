"""
Pydantic schemas for ProcessingJob requests and responses.
"""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from app.models.job import JobStatus, JobType


class JobResponse(BaseModel):
    """Schema for returning a job status record."""
    id: uuid.UUID
    type: JobType
    status: JobStatus
    params: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    """Paginated list of jobs."""
    total: int
    items: List[JobResponse]
