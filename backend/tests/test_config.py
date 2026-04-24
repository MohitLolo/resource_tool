from pathlib import Path

from app.config import Settings


def test_settings_builds_derived_directories_and_ensure_dirs(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    settings = Settings(DATA_DIR=str(data_dir))

    assert Path(settings.UPLOAD_DIR) == data_dir / "uploads"
    assert Path(settings.OUTPUT_DIR) == data_dir / "outputs"
    assert Path(settings.U2NET_HOME) == data_dir / "models" / "u2net"

    settings.ensure_dirs()

    assert (data_dir / "uploads").is_dir()
    assert (data_dir / "outputs").is_dir()
    assert (data_dir / "models" / "u2net").is_dir()


def test_default_data_dir_is_absolute_and_stable() -> None:
    settings = Settings()
    data_dir = Path(settings.DATA_DIR)
    assert data_dir.is_absolute()
    assert data_dir.name == "data"
    assert Path(settings.UPLOAD_DIR) == data_dir / "uploads"
    assert Path(settings.OUTPUT_DIR) == data_dir / "outputs"
    assert Path(settings.U2NET_HOME) == data_dir / "models" / "u2net"


def test_relative_overrides_are_resolved_to_absolute_paths() -> None:
    settings = Settings(
        DATA_DIR="custom_data",
        UPLOAD_DIR="custom_uploads",
        OUTPUT_DIR="custom_outputs",
        U2NET_HOME="custom_models/u2net",
    )
    assert Path(settings.DATA_DIR).is_absolute()
    assert Path(settings.UPLOAD_DIR).is_absolute()
    assert Path(settings.OUTPUT_DIR).is_absolute()
    assert Path(settings.U2NET_HOME).is_absolute()
