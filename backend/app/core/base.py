from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable


ProgressCallback = Callable[[int, str], None]


class BaseProcessor(ABC):
    """处理器基类，定义统一元数据与处理接口。"""

    name: str = ""
    label: str = ""
    category: str = ""
    params_schema: dict = {}

    def _as_int(self, value, default: int | None = None) -> int | None:
        """将输入转换为整数，失败时返回默认值。"""
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _as_float(self, value, default: float | None = None) -> float | None:
        """将输入转换为浮点数，失败时返回默认值。"""
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @abstractmethod
    def validate(self, params: dict) -> bool:
        """校验处理器参数是否合法。"""

    @abstractmethod
    def process(
        self,
        input_file: str,
        output_dir: str,
        params: dict,
        progress_callback: ProgressCallback,
    ) -> list[str]:
        """执行处理并返回输出文件路径列表。"""
