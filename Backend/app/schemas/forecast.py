"""
Pydantic schemas for ShorelineForecast requests and responses.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ForecastGenerateRequest(BaseModel):
    """Request to generate a shoreline forecast."""
    target_year: int = Field(..., ge=2020, le=2100, description="Target prediction year")
    method: str = Field("linear_regression", description="Forecasting method")


class ForecastBase(BaseModel):
    """Shared forecast fields."""
    target_year: int
    method: str
    rmse: Optional[float] = None
    r2_score: Optional[float] = None


class ForecastResponse(ForecastBase):
    """Schema for returning a forecast record."""
    id: int
    predicted_geometry: Optional[Dict[str, Any]] = Field(
        None, description="GeoJSON LineString of predicted shoreline"
    )
    confidence_interval_low: Optional[Dict[str, Any]] = Field(
        None, description="GeoJSON LineString of lower confidence bound"
    )
    confidence_interval_high: Optional[Dict[str, Any]] = Field(
        None, description="GeoJSON LineString of upper confidence bound"
    )
    created_at: datetime

    model_config = {"from_attributes": True}


class ForecastListResponse(BaseModel):
    """Paginated list of forecasts."""
    total: int
    items: List[ForecastResponse]
