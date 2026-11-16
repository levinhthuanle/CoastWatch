"""
Shoreline ORM model.
"""
import enum
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import (
    DateTime,
    Date,
    Enum,
    Float,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ShorelineMethod(str, enum.Enum):
    """Method used to extract the shoreline."""
    NDWI = "ndwi"
    RANDOM_FOREST = "random_forest"
    OPEN_SOURCE = "open_source"


class Shoreline(Base):
    """Represents a detected shoreline at a specific date."""
    __tablename__ = "shorelines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    method: Mapped[ShorelineMethod] = mapped_column(
        Enum(ShorelineMethod), nullable=False, default=ShorelineMethod.NDWI
    )
    geometry: Mapped[object] = mapped_column(
        Geometry(geometry_type="GEOMETRY", srid=4326),
        nullable=True,
    )
    area_water_km2: Mapped[float] = mapped_column(Float, nullable=True)
    area_land_km2: Mapped[float] = mapped_column(Float, nullable=True)
    cloud_cover: Mapped[float] = mapped_column(Float, nullable=True)
    source_image_id: Mapped[str] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Shoreline id={self.id} name={self.name!r} date={self.date} method={self.method}>"
