from __future__ import annotations

from pathlib import Path

from PIL import Image

from app.core.base import BaseProcessor, ProgressCallback


class PixelateProcessor(BaseProcessor):
    """将图片转换为像素风格，可选调色板与输出尺寸。"""

    name = "image.pixelate"
    label = "像素风转换"
    category = "image"
    params_schema = {
        "pixel_size": {
            "type": "number",
            "label": "像素块大小 (Pixel Size)",
            "default": 8,
            "min": 2,
            "max": 32,
        },
        "palette_colors": {
            "type": "select",
            "label": "调色板颜色数 (Palette)",
            "default": 0,
            "options": [0, 8, 16, 32, 64, 128, 256],
        },
        "output_size": {
            "type": "select",
            "label": "输出尺寸 (Output Size)",
            "default": "original",
            "options": ["original", "64x64", "128x128", "256x256"],
        },
    }

    _PALETTE_ALLOWED = {0, 8, 16, 32, 64, 128, 256}
    _OUTPUT_ALLOWED = {"original", "64x64", "128x128", "256x256"}

    def validate(self, params: dict) -> bool:
        """校验像素化参数范围。"""
        pixel_size = self._as_int(params.get("pixel_size", 8))
        palette_colors = self._as_int(params.get("palette_colors", 0))
        output_size = str(params.get("output_size", "original")).lower()

        if pixel_size is None or pixel_size < 2 or pixel_size > 32:
            return False
        if palette_colors is None or palette_colors not in self._PALETTE_ALLOWED:
            return False
        if output_size not in self._OUTPUT_ALLOWED:
            return False
        return True

    def process(
        self,
        input_file: str,
        output_dir: str,
        params: dict,
        progress_callback: ProgressCallback,
    ) -> list[str]:
        """执行像素风转换。"""
        if not self.validate(params):
            raise ValueError("Invalid params for image.pixelate")

        pixel_size = int(params.get("pixel_size", 8))
        palette_colors = int(params.get("palette_colors", 0))
        output_size = str(params.get("output_size", "original")).lower()

        progress_callback(10, "读取图片")
        with Image.open(input_file) as source:
            image = source.convert("RGBA") if "A" in source.getbands() else source.convert("RGB")

        progress_callback(45, "像素化处理中")
        image = self._pixelate(image, pixel_size=pixel_size)

        progress_callback(70, "应用调色板")
        image = self._apply_palette_limit(image, palette_colors=palette_colors)

        progress_callback(85, "调整输出尺寸")
        image = self._resize_output(image, output_size=output_size)

        output_path = Path(output_dir) / f"{Path(input_file).stem}_pixelate.png"
        image.save(output_path, format="PNG")

        progress_callback(100, "完成")
        return [str(output_path)]

    def _pixelate(self, image: Image.Image, pixel_size: int) -> Image.Image:
        width, height = image.size
        small_size = (max(1, width // pixel_size), max(1, height // pixel_size))
        small = image.resize(small_size, Image.Resampling.NEAREST)
        return small.resize((width, height), Image.Resampling.NEAREST)

    def _apply_palette_limit(self, image: Image.Image, palette_colors: int) -> Image.Image:
        if palette_colors <= 0:
            return image

        if image.mode == "RGBA":
            alpha = image.getchannel("A")
            rgb = image.convert("RGB")
            quantized = rgb.quantize(colors=palette_colors, method=Image.Quantize.MEDIANCUT)
            merged = quantized.convert("RGBA")
            merged.putalpha(alpha)
            return merged

        return image.quantize(colors=palette_colors, method=Image.Quantize.MEDIANCUT).convert("RGB")

    def _resize_output(self, image: Image.Image, output_size: str) -> Image.Image:
        if output_size == "original":
            return image

        width_str, height_str = output_size.split("x", maxsplit=1)
        width = int(width_str)
        height = int(height_str)
        return image.resize((width, height), Image.Resampling.NEAREST)
