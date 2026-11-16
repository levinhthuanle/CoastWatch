"""
Pydantic schemas for ShorelineAnalysis requests and responses.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AnalysisCompareRequest(BaseModel):
    """Request to compare two shorelines."""
    shoreline_from_id: int = Field(..., description="ID of the earlier shoreline")
    shoreline_to_id: int = Field(..., description="ID of the later shoreline")


class TransectFeature(BaseModel):
    """GeoJSON Feature representing a single transect with EPR."""
    type: str = "Feature"
    geometry: Dict[str, Any]
    properties: Dict[str, Any]


class AnalysisBase(BaseModel):
    """Shared analysis fields."""
    shoreline_from_id: int
    shoreline_to_id: int
    epr_m_per_year: Optional[float] = None
    total_change_m: Optional[float] = None
    area_lost_km2: Optional[float] = None
    area_gained_km2: Optional[float] = None
    iou_score: Optional[float] = None
    f1_score: Optional[float] = None


class AnalysisResponse(AnalysisBase):
    """Schema for returning an analysis record."""
    id: int
    transects_geojson: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalysisListResponse(BaseModel):
    """Paginated list of analyses."""
    total: int
    items: List[AnalysisResponse]
