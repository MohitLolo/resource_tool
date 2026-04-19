from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable


ProgressCallback = Callable[[int, str], None]


class BaseProcessor(ABC):
    name: str = ""
    label: str = ""
    category: str = ""
    params_schema: dict = {}

    def _as_int(self, value, default: int | None = None) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _as_float(self, value, default: float | None = None) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @abstractmethod
    def validate(self, params: dict) -> bool:
        """Validate processor params."""

    @abstractmethod
    def process(
        self,
        input_file: str,
        output_dir: str,
        params: dict,
        progress_callback: ProgressCallback,
    ) -> list[str]:
        """Process an input file and return generated file paths."""
