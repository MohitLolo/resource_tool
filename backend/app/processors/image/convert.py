from __future__ import annotations

from pathlib import Path

from PIL import Image

from app.core.base import BaseProcessor, ProgressCallback


class ConvertProcessor(BaseProcessor):
    """转换图片输出格式，支持 png/jpg/webp。"""

    name = "image.convert"
    label = "格式转换"
    category = "image"
    params_schema = {
        "format": {
            "type": "select",
            "label": "输出格式",
            "default": "png",
            "options": ["png", "jpg", "webp"],
        },
        "quality": {
            "type": "number",
            "label": "质量",
            "default": 90,
            "min": 1,
            "max": 100,
        },
    }

    _FORMAT_ALLOWED = {"png", "jpg", "webp"}

    def validate(self, params: dict) -> bool:
        """校验输出格式和质量参数。"""
        target_format = str(params.get("format", "png")).lower()
        quality = self._as_int(params.get("quality", 90))
        if target_format not in self._FORMAT_ALLOWED:
            return False
        if quality is None or quality < 1 or quality > 100:
            return False
        return True

    def process(
        self,
        input_file: str,
        output_dir: str,
        params: dict,
        progress_callback: ProgressCallback,
    ) -> list[str]:
        """执行格式转换。"""
        if not self.validate(params):
            raise ValueError("Invalid params for image.convert")

        target_format = str(params.get("format", "png")).lower()
        quality = int(params.get("quality", 90))

        progress_callback(10, "读取图片")
        with Image.open(input_file) as source:
            image = source.copy()

        progress_callback(60, "转换格式")
        output_image = self._prepare_for_format(image, target_format)

        output_ext = "jpg" if target_format == "jpg" else target_format
        output_path = Path(output_dir) / f"{Path(input_file).stem}_convert.{output_ext}"

        save_kwargs = {}
        if target_format in {"jpg", "webp"}:
            save_kwargs["quality"] = quality

        output_image.save(output_path, format=self._pil_format(target_format), **save_kwargs)

        progress_callback(100, "完成")
        return [str(output_path)]

    def _prepare_for_format(self, image: Image.Image, target_format: str) -> Image.Image:
        if target_format == "jpg":
            return self._flatten_alpha_to_white(image)
        if target_format == "png":
            return image.convert("RGBA") if "A" in image.getbands() else image.convert("RGB")
        if target_format == "webp":
            return image.convert("RGBA") if "A" in image.getbands() else image.convert("RGB")
        return image

    def _flatten_alpha_to_white(self, image: Image.Image) -> Image.Image:
        if "A" not in image.getbands():
            return image.convert("RGB")

        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background

    def _pil_format(self, target_format: str) -> str:
        if target_format == "jpg":
            return "JPEG"
        if target_format == "webp":
            return "WEBP"
        return "PNG"
