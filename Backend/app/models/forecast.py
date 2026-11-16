"""
ShorelineForecast ORM model.
"""
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ShorelineForecast(Base):
    """Represents a predicted future shoreline position."""
    __tablename__ = "shoreline_forecasts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Target prediction year
    target_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Prediction method used
    method: Mapped[str] = mapped_column(
        String(100), nullable=False, default="linear_regression"
    )

    # Predicted shoreline geometry
    predicted_geometry: Mapped[object] = mapped_column(
        Geometry(geometry_type="LINESTRING", srid=4326), nullable=True
    )

    # Confidence interval geometries (lower and upper bounds)
    confidence_interval_low: Mapped[object] = mapped_column(
        Geometry(geometry_type="LINESTRING", srid=4326), nullable=True
    )
    confidence_interval_high: Mapped[object] = mapped_column(
        Geometry(geometry_type="LINESTRING", srid=4326), nullable=True
    )

    # Model accuracy metrics
    rmse: Mapped[float] = mapped_column(Float, nullable=True)
    r2_score: Mapped[float] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<ShorelineForecast id={self.id} "
            f"target_year={self.target_year} method={self.method!r}>"
        )
