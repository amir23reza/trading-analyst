from functools import lru_cache

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    app_name: str = Field(..., env="APP_NAME")
    app_version: str = Field(..., env="APP_VERSION")
    db_host: str = Field(..., env="DB_HOST")
    db_port: int = Field(..., env="DB_PORT")
    db_user: str = Field(..., env="DB_USER")
    db_password: str = Field(..., env="DB_PASSWORD")
    db_name: str = Field(..., env="DB_NAME")
    dispatcher_enabled: bool = Field(..., env="DISPATCHER_ENABLED")


@lru_cache
def get_settings() -> Settings:
    """Return a cached instance of Settings."""
    return Settings()

def get_database_url() -> str:
    """Construct the mssql database URL from environment variables."""
    settings = get_settings()
    return f"mssql+pyodbc://{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/{settings.db_name}?driver=ODBC+Driver+18+for+SQL+Server"