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
        "quality": {
            "type": "select",
            "label": "质量",
            "default": "balanced",
            "options": ["fast", "balanced", "high"],
        },
        "alpha_matting": {
            "type": "checkbox",
            "label": "精细边缘",
            "default": False,
        }
    }

    _QUALITY_SIZE = {"fast": 512, "balanced": 768, "high": 1024}

    def validate(self, params: dict) -> bool:
        """校验质量参数。"""
        quality = str(params.get("quality", "balanced")).lower()
        return quality in self._QUALITY_SIZE

    def process(
        self,
        input_file: str,
        output_dir: str,
        params: dict,
        progress_callback: ProgressCallback,
    ) -> list[str]:
        """执行抠图处理。"""
        if not self.validate(params):
            raise ValueError("参数无效")

        quality = str(params.get("quality", "balanced")).lower()
        max_size = self._QUALITY_SIZE[quality]

        progress_callback(5, "加载模型")
        self._warmup_rembg()

        progress_callback(10, "读取图片")
        image = Image.open(input_file).convert("RGBA")
        original_size = image.size

        # 大图先缩小再推理，避免 CPU 上推理时间过长
        if max(original_size) > max_size:
            progress_callback(15, "缩放图片")
            scale = max_size / max(original_size)
            inference_size = (int(original_size[0] * scale), int(original_size[1] * scale))
            small_image = image.resize(inference_size, Image.Resampling.LANCZOS)
        else:
            inference_size = original_size
            small_image = image

        progress_callback(20, "移除背景")
        buf = BytesIO()
        small_image.save(buf, format="PNG")
        alpha_matting = bool(params.get("alpha_matting", False))
        result = self._remove_background(buf.getvalue(), alpha_matting=alpha_matting)

        progress_callback(80, "处理遮罩")
        mask_image = self._to_mask(result)

        # 缩放回原始尺寸
        if inference_size != original_size:
            mask_image = mask_image.resize(original_size, Image.Resampling.LANCZOS)

        progress_callback(85, "合成输出")
        output = Image.composite(image, Image.new("RGBA", original_size, (0, 0, 0, 0)), mask_image)

        output_path = Path(output_dir) / f"{Path(input_file).stem}_cutout.png"
        output.save(str(output_path), format="PNG")

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

    def _to_mask(self, result: bytes | Image.Image | np.ndarray) -> Image.Image:
        """将 rembg 输出转为灰度遮罩（白色=前景，黑色=背景）。"""
        if isinstance(result, bytes):
            img = Image.open(BytesIO(result)).convert("RGBA")
        elif isinstance(result, Image.Image):
            img = result.convert("RGBA")
        else:
            img = Image.fromarray(result).convert("RGBA")
        return img.split()[3]  # alpha 通道即为遮罩

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

        backend_home = Path(__file__).resolve().parents[3] / "data" / "models" / "u2net"
        backend_model = backend_home / "u2net.onnx"
        if backend_model.exists():
            return str(backend_home)

        return str(configured_home)

    def _runtime_key(self) -> tuple[str, tuple[str, ...], str]:
        providers = tuple(settings.CUTOUT_PROVIDERS)
        return settings.CUTOUT_MODEL, providers, self._resolve_u2net_home()

    @staticmethod
    def _purge_module_prefixes(prefixes: list[str]) -> None:
        keys = [key for key in sys.modules if any(key == p or key.startswith(f"{p}.") for p in prefixes)]
        for key in keys:
            sys.modules.pop(key, None)
