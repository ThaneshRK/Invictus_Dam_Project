from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import PostgresDsn, computed_field
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
    )
    
    PROJECT_NAME: str = "Flood Simulation & HADR Framework"
    API_V1_STR: str = "/api/v1"
    
    # Postgres
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "flood_hadr_db"
    POSTGRES_PORT: int = 5432
    
    LOG_LEVEL: str = "INFO"
    
    # Simulation Limits
    SPH_MAX_PARTICLES: int = 50000

    # Government Data
    GOVERNMENT_DATA_DIR: str = "../datasets"

    # Delft3D Engine Configuration
    DELFT3D_ENABLED: bool = True
    DELFT3D_EXECUTION_MODE: str = "host" # options: "host", "docker"
    DELFT3D_INSTALL_DIR: str = "/home/agent001/Downloads/Delft3D/build_dflowfm_release/install"
    DELFT3D_DFLOWFM_EXECUTABLE: str = "dflowfm"
    DELFT3D_CONTAINER_IMAGE: str = "delft3d:dflowfm"
    DELFT3D_WORKSPACE_ROOT: str = "/tmp/delft3d_workspaces"
    DELFT3D_TIMEOUT_SECONDS: int = 3600
    DELFT3D_LD_LIBRARY_PATH: str = "/home/agent001/Downloads/Delft3D/build_dflowfm_release/install/lib:/opt/intel/oneapi/2026.1/lib"

    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=f"{self.POSTGRES_DB}",
        )

settings = Settings()
