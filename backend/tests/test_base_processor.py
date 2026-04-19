from app.core.base import BaseProcessor


class DemoProcessor(BaseProcessor):
    name = "demo.processor"
    label = "Demo"
    category = "image"
    params_schema = {"quality": {"type": "number"}}

    def validate(self, params: dict) -> bool:
        return "quality" in params

    def process(self, input_file, output_dir, params, progress_callback):
        progress_callback(100, "done")
        return ["out.png"]


def test_subclass_exposes_metadata_and_validate() -> None:
    processor = DemoProcessor()
    assert processor.name == "demo.processor"
    assert processor.label == "Demo"
    assert processor.category == "image"
    assert processor.params_schema["quality"]["type"] == "number"
    assert processor.validate({"quality": 90}) is True


def test_process_invokes_progress_callback_and_returns_files() -> None:
    processor = DemoProcessor()
    seen = []

    result = processor.process("in.png", "out", {"quality": 1}, lambda p, m: seen.append((p, m)))

    assert result == ["out.png"]
    assert seen == [(100, "done")]
