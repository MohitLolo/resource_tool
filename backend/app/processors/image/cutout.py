from __future__ import annotations

import importlib
import os
import sys
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from app.config import settings
from app.core.base import BaseProcessor, ProgressCallback


class CutoutProcessor(BaseProcessor):
    """移除图片背景并输出透明 PNG。"""

    name = "image.cutout"
    label = "智能抠图"
    category = "image"
    params_schema = {
        "alpha_matting": {
            "type": "checkbox",
            "label": "精细边缘",
            "default": False,
        }
    }

    def validate(self, params: dict) -> bool:
        """抠图处理器当前无强约束参数。"""
        return True

    def process(
        self,
        input_file: str,
        output_dir: str,
        params: dict,
        progress_callback: ProgressCallback,
    ) -> list[str]:
        """执行抠图处理。"""
        progress_callback(5, "加载模型")
        self._warmup_rembg()

        progress_callback(10, "读取图片")
        input_bytes = Path(input_file).read_bytes()

        progress_callback(30, "移除背景")
        alpha_matting = bool(params.get("alpha_matting", False))
        result = self._remove_background(input_bytes, alpha_matting=alpha_matting)

        progress_callback(85, "编码 PNG")
        png_bytes = self._ensure_rgba_png_bytes(result)

        output_path = Path(output_dir) / f"{Path(input_file).stem}_cutout.png"
        output_path.write_bytes(png_bytes)

        progress_callback(100, "完成")
        return [str(output_path)]

    def _warmup_rembg(self) -> None:
        """首次调用时预加载模型，后续调用走缓存不耗时。"""
        if not settings.CUTOUT_WARMUP:
            return
        key = self._runtime_key()
        if key in self.__class__._warmup_done:
            return
        try:
            rembg_remove = self._import_rembg_remove()
            # 用 1x1 透明 PNG 触发模型下载和初始化
            dummy = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
            buf = BytesIO()
            dummy.save(buf, format="PNG")
            rembg_remove(
                buf.getvalue(),
                alpha_matting=False,
                session=self._get_or_create_session(),
            )
            self.__class__._warmup_done.add(key)
        except Exception:
            # 预热仅用于降低首次请求延迟，不应阻塞主处理流程。
            return

    _warmup_done: set[tuple[str, tuple[str, ...], str]] = set()
    _sessions: dict[tuple[str, tuple[str, ...], str], Any] = {}

    def _ensure_rgba_png_bytes(self, result: bytes | Image.Image | np.ndarray) -> bytes:
        if isinstance(result, bytes):
            image = Image.open(BytesIO(result)).convert("RGBA")
        elif isinstance(result, Image.Image):
            image = result.convert("RGBA")
        else:
            image = Image.fromarray(result).convert("RGBA")

        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    def _remove_background(
        self,
        input_bytes: bytes,
        alpha_matting: bool,
    ) -> bytes | Image.Image | np.ndarray:
        rembg_remove = self._import_rembg_remove()
        return rembg_remove(
            input_bytes,
            alpha_matting=alpha_matting,
            session=self._get_or_create_session(),
        )

    def _get_or_create_session(self):
        key = self._runtime_key()
        session = self.__class__._sessions.get(key)
        if session is not None:
            return session

        _, rembg_new_session = self._import_rembg_api()
        self.__class__._sessions[key] = rembg_new_session(
            settings.CUTOUT_MODEL,
            providers=list(settings.CUTOUT_PROVIDERS),
        )
        return self.__class__._sessions[key]

    def _import_rembg_remove(self):
        rembg_remove, _ = self._import_rembg_api()
        return rembg_remove

    def _import_rembg_api(self):
        self._apply_runtime_env()
        # 部分环境下 pymatting 会触发 numba 缓存初始化异常，这里降级关闭 JIT 后重试。
        try:
            from rembg import new_session as rembg_new_session
            from rembg import remove as rembg_remove
        except RuntimeError as exc:
            if "cannot cache function" not in str(exc):
                raise
            os.environ["NUMBA_DISABLE_JIT"] = "1"
            self._purge_module_prefixes(["rembg", "pymatting"])
            importlib.invalidate_caches()
            from rembg import new_session as rembg_new_session
            from rembg import remove as rembg_remove

        return rembg_remove, rembg_new_session

    def _apply_runtime_env(self) -> None:
        os.environ["U2NET_HOME"] = self._resolve_u2net_home()
        if settings.CUTOUT_DISABLE_NUMBA_JIT:
            os.environ.setdefault("NUMBA_DISABLE_JIT", "1")

    def _resolve_u2net_home(self) -> str:
        configured_home = Path(settings.U2NET_HOME)
        configured_model = configured_home / "u2net.onnx"
        if configured_model.exists():
            return str(configured_home)

        legacy_home = Path("/root/.u2net")
        legacy_model = legacy_home / "u2net.onnx"
        if legacy_model.exists():
            return str(legacy_home)

        return str(configured_home)

    def _runtime_key(self) -> tuple[str, tuple[str, ...], str]:
        providers = tuple(settings.CUTOUT_PROVIDERS)
        return settings.CUTOUT_MODEL, providers, self._resolve_u2net_home()

    @staticmethod
    def _purge_module_prefixes(prefixes: list[str]) -> None:
        keys = [key for key in sys.modules if any(key == p or key.startswith(f"{p}.") for p in prefixes)]
        for key in keys:
            sys.modules.pop(key, None)
