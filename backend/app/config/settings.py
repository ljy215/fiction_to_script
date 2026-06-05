from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "AI Novel To Script API"
    app_version: str = "0.1.0"

    bailian_api_key: str = Field(..., min_length=1)
    bailian_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    bailian_model: str = "qwen-plus"

    jwt_secret: str = Field(..., min_length=16)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    database_url: str = "sqlite:///./storage/data/app.sqlite3"
    file_storage_dir: Path = Path("./storage/files")
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(
        env_file=(".env.example", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, value: str) -> str:
        origins = [origin.strip() for origin in value.split(",") if origin.strip()]
        if not origins:
            raise ValueError("CORS_ORIGINS must contain at least one origin")
        return ",".join(origins)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def sqlite_database_path(self) -> Path | None:
        if not self.database_url.startswith("sqlite:///"):
            return None

        raw_path = self.database_url.removeprefix("sqlite:///")
        return Path(raw_path)

    def ensure_local_directories(self) -> None:
        self.file_storage_dir.mkdir(parents=True, exist_ok=True)

        sqlite_path = self.sqlite_database_path
        if sqlite_path is not None:
            sqlite_path.parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
