"""
Application configuration using Pydantic Settings.
Reads values from environment variables / .env file.
"""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    APP_NAME: str = "CoastWatch API"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://coastwatch:password@localhost:5432/coastwatch_db"

    # Security
    SECRET_KEY: str = "change-me-in-production"

    # Google Earth Engine
    GEE_SERVICE_ACCOUNT: Optional[str] = None
    GEE_PRIVATE_KEY_FILE: Optional[str] = None

    # SAP AI Core
    LLM_API_CONFIG: Optional[str] = None
    AICORE_RESOURCE_GROUP: str = "default"
    AICORE_LLM_MODEL: str = "gpt-4o"

    # Study area defaults (Cua Tung, Quang Tri, Vietnam)
    DEFAULT_BBOX_WEST: float = 107.02
    DEFAULT_BBOX_SOUTH: float = 17.00
    DEFAULT_BBOX_EAST: float = 107.06
    DEFAULT_BBOX_NORTH: float = 17.04


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()


settings = get_settings()
