"""
ShorelineAnalysis ORM model.
"""
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ShorelineAnalysis(Base):
    """Represents a comparison analysis between two shorelines at different times."""
    __tablename__ = "shoreline_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Foreign keys to the two shorelines being compared
    shoreline_from_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("shorelines.id", ondelete="CASCADE"), nullable=False
    )
    shoreline_to_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("shorelines.id", ondelete="CASCADE"), nullable=False
    )

    # EPR: End Point Rate — average shoreline change rate in meters per year
    epr_m_per_year: Mapped[float] = mapped_column(Float, nullable=True)

    # Total displacement along the main transect axis (metres)
    total_change_m: Mapped[float] = mapped_column(Float, nullable=True)

    # Area change statistics
    area_lost_km2: Mapped[float] = mapped_column(Float, nullable=True)
    area_gained_km2: Mapped[float] = mapped_column(Float, nullable=True)

    # GeoJSON array of transect lines with per-transect EPR values
    transects_geojson: Mapped[dict] = mapped_column(JSON, nullable=True)

    # Accuracy metrics
    iou_score: Mapped[float] = mapped_column(Float, nullable=True)
    f1_score: Mapped[float] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    shoreline_from = relationship(
        "Shoreline", foreign_keys=[shoreline_from_id], lazy="selectin"
    )
    shoreline_to = relationship(
        "Shoreline", foreign_keys=[shoreline_to_id], lazy="selectin"
    )

    def __repr__(self) -> str:
        return (
            f"<ShorelineAnalysis id={self.id} "
            f"from={self.shoreline_from_id} to={self.shoreline_to_id} "
            f"epr={self.epr_m_per_year}>"
        )
