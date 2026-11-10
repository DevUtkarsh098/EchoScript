from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    # Fail closed when deployments omit APP_ENV; local demo mode must be explicit.
    app_env: str = "production"
    app_version: str = "0.1.0"
    commit_sha: str = "development"
    deployment_color: str = "local"
    mock_auth: bool = True
    mock_processing: bool = True
    mock_video: bool = True
    public_api_url: str = "http://localhost:8000"
    cors_origins: str = "http://localhost:5173"
    data_dir: Path = Path("./data")
    max_upload_bytes: int = 262_144_000
    cognito_issuer: str = ""
    cognito_client_id: str = ""

    @property
    def allowed_origins(self) -> list[str]:
        return [value.strip() for value in self.cors_origins.split(",") if value.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return settings

