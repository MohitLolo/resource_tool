from app.core.base import BaseProcessor
from app.core.registry import ProcessorRegistry


class TestProcessor(BaseProcessor):
    name = "image.test"
    label = "Image Test"
    category = "image"
    params_schema = {"enabled": {"type": "checkbox"}}

    def validate(self, params: dict) -> bool:
        return True

    def process(self, input_file, output_dir, params, progress_callback):
        return []


class AudioProcessor(BaseProcessor):
    name = "audio.test"
    label = "Audio Test"
    category = "audio"
    params_schema = {}

    def validate(self, params: dict) -> bool:
        return True

    def process(self, input_file, output_dir, params, progress_callback):
        return []


def setup_function() -> None:
    ProcessorRegistry.clear()


def test_register_get_and_list() -> None:
    ProcessorRegistry.register(TestProcessor)
    ProcessorRegistry.register(AudioProcessor)

    instance = ProcessorRegistry.get("image.test")
    assert isinstance(instance, TestProcessor)

    all_items = ProcessorRegistry.list_all()
    assert {item["name"] for item in all_items} == {"image.test", "audio.test"}

    image_items = ProcessorRegistry.list_by_category("image")
    assert len(image_items) == 1
    assert image_items[0]["label"] == "Image Test"


def test_auto_discover_registers_processors_from_package() -> None:
    ProcessorRegistry.auto_discover("app.processors")
    items = ProcessorRegistry.list_all()
    assert any(item["name"] == "image.watermark" for item in items)
