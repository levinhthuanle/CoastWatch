"""
ProcessingJob ORM model for async task tracking.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class JobType(str, enum.Enum):
    """Type of background processing job."""
    EXTRACT_SHORELINE = "extract_shoreline"
    ANALYZE = "analyze"
    FORECAST = "forecast"


class JobStatus(str, enum.Enum):
    """Current status of a processing job."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingJob(Base):
    """Tracks the status and result of asynchronous processing jobs."""
    __tablename__ = "processing_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    type: Mapped[JobType] = mapped_column(
        Enum(JobType), nullable=False
    )

    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus), nullable=False, default=JobStatus.PENDING, index=True
    )

    # JSON parameters passed when the job was created
    params: Mapped[dict] = mapped_column(JSON, nullable=True)

    # JSON result payload once completed
    result: Mapped[dict] = mapped_column(JSON, nullable=True)

    # Error message if status is FAILED
    error: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<ProcessingJob id={self.id} type={self.type} status={self.status}>"
