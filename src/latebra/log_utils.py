"""Logging utilities for latebra — cross-platform file logging with rotation.

Creates two rotating log files in a configurable directory:
- latebra.log:  INFO+ messages (all operational logs)
- errors.log:   WARNING+ messages (dedicated error triage file)

Usage:
    from latebra.log_utils import setup_file_logging, get_log_path
    setup_file_logging()
    logging.getLogger("latebra").error("Something went wrong")

Autor: Evandro Fonseca Junior
Licença: MIT
"""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from latebra.constants import get_log_dir

# ── Module state ─────────────────────────────────
_LOG_DIR: str | None = None


def get_log_path() -> str:
    """Return path to the log directory (absolute string, cross-platform).

    Returns a cached value — only probes the filesystem on first call.
    """
    global _LOG_DIR
    if _LOG_DIR is None:
        _LOG_DIR = str(get_log_dir())
    return _LOG_DIR


def setup_file_logging(
    log_dir: str | None = None,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 3,
) -> None:
    """Configure file logging for latebra.

    Creates two rotating log files:
    - ``latebra.log`` — INFO+ (rotating, max_bytes per file, backup_count backups)
    - ``errors.log``  — WARNING+ (same rotation config)

    Does NOT remove any existing console handlers — those stay active.
    Removes any previously added file handlers to avoid duplicates.

    Args:
        log_dir:  Custom log directory. If None, uses the default data dir.
        max_bytes: Maximum size per log file before rotation starts.
        backup_count: Number of old log files to keep after rotation.
    """
    if log_dir is not None:
        log_path = Path(log_dir)
    else:
        log_path = Path(get_log_path())

    log_path.mkdir(parents=True, exist_ok=True)

    # ── Main log (INFO+) ────────────────────────────────
    main_handler = RotatingFileHandler(
        filename=str(log_path / "latebra.log"),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    main_handler.setLevel(logging.INFO)
    main_handler.setFormatter(_formatter())

    # ── Error log (WARNING+) ────────────────────────────
    error_handler = RotatingFileHandler(
        filename=str(log_path / "errors.log"),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(_formatter(detailed=True))

    # ── Root logger ─────────────────────────────────────
    root = logging.getLogger()
    # Remove any existing file handlers to avoid duplicates
    root.handlers = [
        h for h in root.handlers
        if not isinstance(h, logging.FileHandler)
    ]
    root.addHandler(main_handler)
    root.addHandler(error_handler)
    # Keep root at DEBUG so file handlers can filter up from their level
    root.setLevel(logging.DEBUG)

    # Cache the resolved log directory
    global _LOG_DIR
    _LOG_DIR = str(log_path)


def _formatter(detailed: bool = False) -> logging.Formatter:
    """Create a log formatter.

    Args:
        detailed: If True, includes lineno in the format (for error logs).

    Returns:
        A configured logging.Formatter instance.
    """
    if detailed:
        fmt = "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d | %(message)s"
    else:
        fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    return logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")


def truncate_logs(log_dir: str | None = None, max_files: int = 10) -> int:
    """Remove oldest rotated log files beyond *max_files* per prefix.

    Args:
        log_dir:   Directory to clean. If None, uses the default log dir.
        max_files: Maximum number of files (including the active one) to keep
                   per prefix (``latebra.log``, ``errors.log``).

    Returns:
        Number of deleted files.
    """
    if log_dir is None:
        log_dir = get_log_path()

    log_path = Path(log_dir)
    if not log_path.exists():
        return 0

    deleted = 0
    for prefix in ("latebra.log", "errors.log"):
        files: list[Path] = sorted(
            log_path.glob(f"{prefix}*"),
            key=os.path.getmtime,
        )
        while len(files) > max_files:
            oldest = files.pop(0)
            try:
                oldest.unlink(missing_ok=True)
                deleted += 1
            except OSError:
                pass

    return deleted
