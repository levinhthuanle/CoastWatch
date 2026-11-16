"""Initial schema: shorelines, analyses, forecasts, jobs

Revision ID: 001_initial
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
import geoalchemy2
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable PostGIS extension
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # Enum types
    shoreline_method = postgresql.ENUM(
        "ndwi", "random_forest", "open_source",
        name="shorelinemethod",
        create_type=True,
    )
    shoreline_method.create(op.get_bind(), checkfirst=True)

    job_type = postgresql.ENUM(
        "extract_shoreline", "analyze", "forecast",
        name="jobtype",
        create_type=True,
    )
    job_type.create(op.get_bind(), checkfirst=True)

    job_status = postgresql.ENUM(
        "pending", "running", "completed", "failed",
        name="jobstatus",
        create_type=True,
    )
    job_status.create(op.get_bind(), checkfirst=True)

    # Shorelines table
    op.create_table(
        "shorelines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("method", sa.Enum("ndwi", "random_forest", "open_source", name="shorelinemethod"), nullable=False),
        sa.Column(
            "geometry",
            geoalchemy2.types.Geometry(geometry_type="LINESTRING", srid=4326),
            nullable=True,
        ),
        sa.Column("area_water_km2", sa.Float(), nullable=True),
        sa.Column("area_land_km2", sa.Float(), nullable=True),
        sa.Column("cloud_cover", sa.Float(), nullable=True),
        sa.Column("source_image_id", sa.String(512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shorelines_id", "shorelines", ["id"])
    op.create_index("ix_shorelines_date", "shorelines", ["date"])
    op.create_index("ix_shorelines_year", "shorelines", ["year"])

    # Shoreline analyses table
    op.create_table(
        "shoreline_analyses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("shoreline_from_id", sa.Integer(), nullable=False),
        sa.Column("shoreline_to_id", sa.Integer(), nullable=False),
        sa.Column("epr_m_per_year", sa.Float(), nullable=True),
        sa.Column("total_change_m", sa.Float(), nullable=True),
        sa.Column("area_lost_km2", sa.Float(), nullable=True),
        sa.Column("area_gained_km2", sa.Float(), nullable=True),
        sa.Column("transects_geojson", sa.JSON(), nullable=True),
        sa.Column("iou_score", sa.Float(), nullable=True),
        sa.Column("f1_score", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["shoreline_from_id"], ["shorelines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shoreline_to_id"], ["shorelines.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shoreline_analyses_id", "shoreline_analyses", ["id"])

    # Shoreline forecasts table
    op.create_table(
        "shoreline_forecasts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("target_year", sa.Integer(), nullable=False),
        sa.Column("method", sa.String(100), nullable=False),
        sa.Column(
            "predicted_geometry",
            geoalchemy2.types.Geometry(geometry_type="LINESTRING", srid=4326),
            nullable=True,
        ),
        sa.Column(
            "confidence_interval_low",
            geoalchemy2.types.Geometry(geometry_type="LINESTRING", srid=4326),
            nullable=True,
        ),
        sa.Column(
            "confidence_interval_high",
            geoalchemy2.types.Geometry(geometry_type="LINESTRING", srid=4326),
            nullable=True,
        ),
        sa.Column("rmse", sa.Float(), nullable=True),
        sa.Column("r2_score", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shoreline_forecasts_id", "shoreline_forecasts", ["id"])
    op.create_index("ix_shoreline_forecasts_target_year", "shoreline_forecasts", ["target_year"])

    # Processing jobs table
    op.create_table(
        "processing_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.Enum("extract_shoreline", "analyze", "forecast", name="jobtype"), nullable=False),
        sa.Column("status", sa.Enum("pending", "running", "completed", "failed", name="jobstatus"), nullable=False),
        sa.Column("params", sa.JSON(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_processing_jobs_id", "processing_jobs", ["id"])
    op.create_index("ix_processing_jobs_status", "processing_jobs", ["status"])


def downgrade() -> None:
    op.drop_table("processing_jobs")
    op.drop_table("shoreline_forecasts")
    op.drop_table("shoreline_analyses")
    op.drop_table("shorelines")

    op.execute("DROP TYPE IF EXISTS jobstatus")
    op.execute("DROP TYPE IF EXISTS jobtype")
    op.execute("DROP TYPE IF EXISTS shorelinemethod")
