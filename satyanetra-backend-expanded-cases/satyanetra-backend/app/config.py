import os
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "SatyaNetra API"
    environment: str = "development"
    database_url: str = "sqlite:///./satyanetra.db"
    jwt_secret: SecretStr = SecretStr("CHANGE_THIS_TO_A_RANDOM_SECRET_OF_AT_LEAST_32_CHARS")
    access_token_minutes: int = 60
    cors_origins: str = "http://localhost:5500,http://127.0.0.1:5500"
    upload_dir: str = "./private_uploads"
    max_upload_mb: int = 8
    ai_provider: str = "mock"
    watsonx_api_key: SecretStr | None = None
    watsonx_url: str | None = None
    watsonx_project_id: str | None = None
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

settings = Settings()
