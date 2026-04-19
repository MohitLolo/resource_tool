from __future__ import annotations

from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    REDIS_URL: str = "redis://localhost:6379/0"
    DATA_DIR: str = "data"
    UPLOAD_DIR: str | None = None
    OUTPUT_DIR: str | None = None
    MAX_FILE_SIZE: int = 500 * 1024 * 1024
    CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @model_validator(mode="after")
    def _populate_dirs(self) -> "Settings":
        data_dir = Path(self.DATA_DIR)
        if self.UPLOAD_DIR is None:
            self.UPLOAD_DIR = str(data_dir / "uploads")
        if self.OUTPUT_DIR is None:
            self.OUTPUT_DIR = str(data_dir / "outputs")
        return self

    def ensure_dirs(self) -> None:
        Path(self.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
        Path(self.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)


settings = Settings()
