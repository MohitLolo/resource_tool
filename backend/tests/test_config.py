from pathlib import Path

from app.config import Settings


def test_settings_builds_derived_directories_and_ensure_dirs(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    settings = Settings(DATA_DIR=str(data_dir))

    assert Path(settings.UPLOAD_DIR) == data_dir / "uploads"
    assert Path(settings.OUTPUT_DIR) == data_dir / "outputs"

    settings.ensure_dirs()

    assert (data_dir / "uploads").is_dir()
    assert (data_dir / "outputs").is_dir()
