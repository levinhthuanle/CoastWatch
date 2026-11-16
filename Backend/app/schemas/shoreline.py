"""
Pydantic schemas for Shoreline requests and responses.
"""
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from geojson_pydantic import LineString
from pydantic import BaseModel, Field

from app.models.shoreline import ShorelineMethod


class BboxModel(BaseModel):
    """Bounding box for spatial queries."""
    west: float = Field(..., ge=-180, le=180, description="Western longitude")
    south: float = Field(..., ge=-90, le=90, description="Southern latitude")
    east: float = Field(..., ge=-180, le=180, description="Eastern longitude")
    north: float = Field(..., ge=-90, le=90, description="Northern latitude")


class ShorelineBase(BaseModel):
    """Shared Shoreline fields."""
    name: str = Field(..., max_length=255)
    date: date
    year: int
    method: ShorelineMethod = ShorelineMethod.NDWI
    area_water_km2: Optional[float] = None
    area_land_km2: Optional[float] = None
    cloud_cover: Optional[float] = None
    source_image_id: Optional[str] = None


class ShorelineCreate(ShorelineBase):
    """Schema for creating a shoreline record."""
    geometry_geojson: Optional[Dict[str, Any]] = Field(
        None, description="GeoJSON LineString geometry"
    )


class ShorelineResponse(ShorelineBase):
    """Schema for returning a shoreline record."""
    id: int
    created_at: datetime
    geometry_geojson: Optional[Dict[str, Any]] = Field(
        None, description="GeoJSON geometry"
    )

    model_config = {"from_attributes": True}


class ShorelineListResponse(BaseModel):
    """Paginated list of shorelines."""
    total: int
    items: List[ShorelineResponse]


class ShorelineExtractRequest(BaseModel):
    """Request to trigger a GEE shoreline extraction job."""
    bbox: BboxModel = Field(
        default_factory=lambda: BboxModel(
            west=107.02, south=17.00, east=107.06, north=17.04
        )
    )
    date: str = Field(..., description="Target date in YYYY-MM-DD format")
    method: ShorelineMethod = ShorelineMethod.NDWI
    year: int = Field(..., ge=2015, le=2030)
    max_cloud: float = Field(20.0, ge=0, le=100)


class ShorelineGeoJSONResponse(BaseModel):
    """GeoJSON FeatureCollection for a single shoreline."""
    type: str = "FeatureCollection"
    features: List[Dict[str, Any]]
