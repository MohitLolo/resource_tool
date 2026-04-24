from __future__ import annotations

from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    REDIS_URL: str = "redis://localhost:6379/0"
    DATA_DIR: str = "data"
    UPLOAD_DIR: str | None = None
    OUTPUT_DIR: str | None = None
    U2NET_HOME: str | None = None
    MAX_FILE_SIZE: int = 500 * 1024 * 1024
    CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    CUTOUT_MODEL: str = "u2net"
    CUTOUT_PROVIDERS: list[str] = Field(default_factory=lambda: ["CPUExecutionProvider"])
    CUTOUT_WARMUP: bool = True
    CUTOUT_DISABLE_NUMBA_JIT: bool = True
    TASK_IDEMPOTENCY_TTL_SECONDS: int = 24 * 60 * 60

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @model_validator(mode="after")
    def _populate_dirs(self) -> "Settings":
        data_dir = self._resolve_path(self.DATA_DIR)
        self.DATA_DIR = str(data_dir)
        if self.UPLOAD_DIR is None:
            self.UPLOAD_DIR = str(data_dir / "uploads")
        else:
            self.UPLOAD_DIR = str(self._resolve_path(self.UPLOAD_DIR))
        if self.OUTPUT_DIR is None:
            self.OUTPUT_DIR = str(data_dir / "outputs")
        else:
            self.OUTPUT_DIR = str(self._resolve_path(self.OUTPUT_DIR))
        if self.U2NET_HOME is None:
            self.U2NET_HOME = str(data_dir / "models" / "u2net")
        else:
            self.U2NET_HOME = str(self._resolve_path(self.U2NET_HOME))
        return self

    @staticmethod
    def _resolve_path(value: str) -> Path:
        path = Path(value)
        if path.is_absolute():
            return path
        return (PROJECT_ROOT / path).resolve()

    def ensure_dirs(self) -> None:
        Path(self.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
        Path(self.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        Path(self.U2NET_HOME).mkdir(parents=True, exist_ok=True)


settings = Settings()
