"""app/schemas/__init__.py"""
from app.schemas.shoreline import (
    BboxModel,
    ShorelineCreate,
    ShorelineResponse,
    ShorelineListResponse,
    ShorelineExtractRequest,
    ShorelineGeoJSONResponse,
)
from app.schemas.analysis import (
    AnalysisCompareRequest,
    AnalysisResponse,
    AnalysisListResponse,
)
from app.schemas.forecast import (
    ForecastGenerateRequest,
    ForecastResponse,
    ForecastListResponse,
)
from app.schemas.job import JobResponse, JobListResponse
from app.schemas.chat import ChatRequest, ChatResponse

__all__ = [
    "BboxModel",
    "ShorelineCreate",
    "ShorelineResponse",
    "ShorelineListResponse",
    "ShorelineExtractRequest",
    "ShorelineGeoJSONResponse",
    "AnalysisCompareRequest",
    "AnalysisResponse",
    "AnalysisListResponse",
    "ForecastGenerateRequest",
    "ForecastResponse",
    "ForecastListResponse",
    "JobResponse",
    "JobListResponse",
    "ChatRequest",
    "ChatResponse",
]
