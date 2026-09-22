import pytest
from app.core.config import settings

def test_settings_loaded():
    assert settings.PROJECT_NAME == "Flood Simulation & HADR Framework"
    assert settings.API_V1_STR == "/api/v1"
    assert settings.POSTGRES_USER is not None
    assert settings.POSTGRES_PASSWORD is not None
    assert settings.POSTGRES_DB is not None

def test_database_uri_format():
    uri = str(settings.SQLALCHEMY_DATABASE_URI)
    assert uri.startswith("postgresql+asyncpg://")
    assert settings.POSTGRES_USER in uri
    assert settings.POSTGRES_DB in uri
