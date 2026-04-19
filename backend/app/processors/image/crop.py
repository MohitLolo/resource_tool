from __future__ import annotations

from pathlib import Path

from PIL import Image

from app.core.base import BaseProcessor


class CropProcessor(BaseProcessor):
    name = "image.crop"
    label = "裁剪/缩放"
    category = "image"
    params_schema = {
        "mode": {
            "type": "select",
            "label": "模式 (Mode)",
            "default": "custom",
            "options": ["custom", "power2", "crop"],
        },
        "width": {"type": "number", "label": "宽度 (Width)", "min": 1},
        "height": {"type": "number", "label": "高度 (Height)", "min": 1},
        "power2_size": {
            "type": "select",
            "label": "幂次尺寸 (Power2)",
            "default": 256,
            "options": [32, 64, 128, 256, 512, 1024],
        },
        "x": {"type": "number", "label": "X", "min": 0},
        "y": {"type": "number", "label": "Y", "min": 0},
        "crop_width": {"type": "number", "label": "裁剪宽 (Crop Width)", "min": 1},
        "crop_height": {"type": "number", "label": "裁剪高 (Crop Height)", "min": 1},
    }

    _POWER2_SIZES = {32, 64, 128, 256, 512, 1024}

    def validate(self, params: dict) -> bool:
        mode = self._mode(params)
        validator = self._validator_map().get(mode)
        if validator is None:
            return False
        return validator(params)

    def process(
        self,
        input_file: str,
        output_dir: str,
        params: dict,
        progress_callback,
    ) -> list[str]:
        mode = self._mode(params)
        if not self.validate(params):
            raise ValueError(f"Invalid params for mode: {mode}")

        handler = self._handler_map()[mode]

        progress_callback(10, "读取图片")
        with Image.open(input_file) as source:
            progress_callback(60, "执行处理")
            output = handler(source, params)

        output_path = Path(output_dir) / f"{Path(input_file).stem}_crop.png"
        output.save(output_path, format="PNG")

        progress_callback(100, "完成")
        return [str(output_path)]

    def _validator_map(self):
        return {
            "custom": self._validate_custom,
            "power2": self._validate_power2,
            "crop": self._validate_crop,
        }

    def _handler_map(self):
        return {
            "custom": self._process_custom,
            "power2": self._process_power2,
            "crop": self._process_crop,
        }

    def _mode(self, params: dict) -> str:
        return str(params.get("mode", "custom")).lower()

    def _param_int(self, params: dict, key: str) -> int | None:
        if key not in params:
            return None
        return self._as_int(params[key])

    def _validate_custom(self, params: dict) -> bool:
        width = self._param_int(params, "width")
        height = self._param_int(params, "height")
        return width is not None and height is not None and width > 0 and height > 0

    def _validate_power2(self, params: dict) -> bool:
        size = self._param_int(params, "power2_size")
        return size in self._POWER2_SIZES

    def _validate_crop(self, params: dict) -> bool:
        x = self._param_int(params, "x")
        y = self._param_int(params, "y")
        crop_width = self._param_int(params, "crop_width")
        crop_height = self._param_int(params, "crop_height")
        if None in {x, y, crop_width, crop_height}:
            return False
        return x >= 0 and y >= 0 and crop_width > 0 and crop_height > 0

    def _process_custom(self, image: Image.Image, params: dict) -> Image.Image:
        width = int(params["width"])
        height = int(params["height"])
        return image.resize((width, height), Image.Resampling.LANCZOS)

    def _process_power2(self, image: Image.Image, params: dict) -> Image.Image:
        size = int(params["power2_size"])
        return image.resize((size, size), Image.Resampling.LANCZOS)

    def _process_crop(self, image: Image.Image, params: dict) -> Image.Image:
        x = int(params["x"])
        y = int(params["y"])
        crop_width = int(params["crop_width"])
        crop_height = int(params["crop_height"])
        return image.crop((x, y, x + crop_width, y + crop_height))
