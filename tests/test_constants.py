"""Test latebra constants."""

from __future__ import annotations

import platform


def test_app_name() -> None:
    from latebra.constants import APP_NAME

    assert APP_NAME == "latebra"


def test_get_data_dir_returns_absolute() -> None:
    from latebra.constants import get_data_dir

    path = get_data_dir()
    assert path.name == "latebra"
    assert path.is_absolute()
    assert path.exists()


def test_get_log_dir_returns_subdir() -> None:
    from latebra.constants import get_log_dir

    log_dir = get_log_dir()
    assert log_dir.name == "logs"
    assert log_dir.parent.name == "latebra"
    assert log_dir.exists()


def test_data_dir_cross_platform() -> None:
    from latebra.constants import _get_data_dir

    path = _get_data_dir()
    system = platform.system()
    if system == "Linux":
        assert ".local/share/latebra" in str(path)
    elif system == "Windows":
        assert "AppData\\Local\\latebra" in str(path)
    elif system == "Darwin":
        assert "Library/Application Support/latebra" in str(path)
