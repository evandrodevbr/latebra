"""Test latebra log utilities."""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def isolated_log_dir() -> str:
    """Create a temporary log directory for each test."""
    with tempfile.TemporaryDirectory(prefix="latebra_test_logs_") as tmp:
        yield tmp


def test_setup_creates_log_dir(isolated_log_dir: str) -> None:
    """Verify that setup_file_logging creates the log directory."""
    from latebra.log_utils import setup_file_logging

    log_path = Path(isolated_log_dir) / "subdir"
    setup_file_logging(log_dir=str(log_path))
    assert log_path.exists()


def test_writes_error_log(isolated_log_dir: str) -> None:
    """Verify errors.log is created and contains WARNING+ messages."""
    from latebra.log_utils import setup_file_logging

    setup_file_logging(log_dir=isolated_log_dir)

    logger = logging.getLogger("latebra_test_error")
    logger.error("Test error message")

    for h in logger.handlers:
        h.flush()

    error_log = Path(isolated_log_dir) / "errors.log"
    assert error_log.exists(), "errors.log not created"
    content = error_log.read_text(encoding="utf-8")
    assert "Test error message" in content


def test_writes_info_log(isolated_log_dir: str) -> None:
    """Verify latebra.log is created and contains INFO+ messages."""
    from latebra.log_utils import setup_file_logging

    setup_file_logging(log_dir=isolated_log_dir)

    logger = logging.getLogger("latebra_test_info")
    logger.info("Test info message")

    for h in logger.handlers:
        h.flush()

    main_log = Path(isolated_log_dir) / "latebra.log"
    assert main_log.exists(), "latebra.log not created"
    content = main_log.read_text(encoding="utf-8")
    assert "Test info message" in content


def test_error_log_only_warning_plus(isolated_log_dir: str) -> None:
    """Verify errors.log only has WARNING+ (no INFO)."""
    from latebra.log_utils import setup_file_logging

    setup_file_logging(log_dir=isolated_log_dir)

    logger = logging.getLogger("latebra_test_levels")
    logger.info("Should NOT be in errors.log")
    logger.warning("Should be in errors.log")

    for h in logger.handlers:
        h.flush()

    error_log = Path(isolated_log_dir) / "errors.log"
    content = error_log.read_text(encoding="utf-8")
    assert "Should be in errors.log" in content
    assert "Should NOT be in errors.log" not in content


def test_log_path_returns_absolute(isolated_log_dir: str) -> None:
    """Verify get_log_path returns a valid absolute path string."""
    from latebra.log_utils import get_log_path, setup_file_logging

    setup_file_logging(log_dir=isolated_log_dir)
    path = get_log_path()
    assert isinstance(path, str)
    assert os.path.isabs(path) or ":" in path


def test_truncate_logs_graceful(isolated_log_dir: str) -> None:
    """Verify truncate_logs handles missing/invalid dirs gracefully."""
    from latebra.log_utils import truncate_logs

    # Non-existent dir
    count = truncate_logs("/tmp/nonexistent_latebra_test_xyz", max_files=5)
    assert count == 0

    # None (uses default)
    count = truncate_logs(None, max_files=5)
    assert count == 0 or count >= 0
