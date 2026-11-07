from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MediFlow API"
    app_env: str = "development"
    enable_dev_auth: bool = False
    api_v1_prefix: str = "/api/v1"
    database_url: str
    frontend_origins: str = "http://localhost:5173"

    # JWT authentication settings
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Gemini AI configuration
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.frontend_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()