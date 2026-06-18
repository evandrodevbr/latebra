# [Logging System + Publicação] Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use TDD (test-driven-development) for every code change.

**Goal:** Implementar um sistema de logging que salva warnings e errors em `~/.latebra/logs/` (cross-platform Linux/Windows), e pesquisar os melhores canais de publicação para atrair usuários.

**Architecture:**
1. **Logging core** — `log_utils.py` com `LogManager` que configura file handler com rotação, salva em diretório cross-platform via `appdirs` (ou path manual), e expõe `get_log_path()`
2. **MCP tool** — `latebra_get_log_path` adicionada ao servidor
3. **Integração no startup** — `__main__.py` inicializa file logging

**Tech Stack:** Python 3.12+, logging stdlib, pathlib, platform

---

## Tasks

### Task 1: Criar src/latebra/constants.py

**Files:**
- Create: `src/latebra/constants.py`
- Test: `tests/test_constants.py`

- [ ] **Step 1: Write the failing test**

```python
"""Test latebra constants."""
from latebra.constants import APP_NAME, get_data_dir


def test_app_name() -> None:
    assert APP_NAME == "latebra"


def test_get_data_dir_returns_path() -> None:
    path = get_data_dir()
    assert path.name == "latebra"
    assert path.is_absolute()


def test_get_log_dir_returns_subdir() -> None:
    from latebra.constants import get_log_dir
    log_dir = get_log_dir()
    assert log_dir.name == "logs"
    assert str(log_dir.parent.name) == "latebra"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_constants.py -v`
Expected: ModuleNotFoundError for `latebra.constants`

- [ ] **Step 3: Write minimal implementation**

```python
"""Constants for latebra project."""

from __future__ import annotations

import platform
from pathlib import Path


APP_NAME = "latebra"


def _get_data_dir() -> Path:
    """Return cross-platform data directory."""
    system = platform.system()
    if system == "Windows":
        base = Path.home() / "AppData" / "Local"
    elif system == "Linux":
        base = Path.home() / ".local" / "share"
    elif system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path.home() / ".latebra"
    return base / APP_NAME


_DATA_DIR: Path | None = None


def get_data_dir() -> Path:
    """Get the application data directory (cached)."""
    global _DATA_DIR
    if _DATA_DIR is None:
        _DATA_DIR = _get_data_dir()
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
    return _DATA_DIR


def get_log_dir() -> Path:
    """Get the logs directory (creates if needed)."""
    log_dir = get_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_constants.py -v`
Expected: PASS (3/3)

- [ ] **Step 5: Commit**

```bash
git add src/latebra/constants.py tests/test_constants.py
git commit -m "feat: add cross-platform data/log dir constants"
```

---

### Task 2: Criar src/latebra/log_utils.py

**Files:**
- Create: `src/latebra/log_utils.py`
- Test: `tests/test_log_utils.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Test latebra log utilities."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest


def test_setup_file_logging_creates_log_dir() -> None:
    from latebra.log_utils import setup_file_logging, get_log_path
    log_dir = Path(get_log_path())
    assert log_dir.exists()


def test_setup_file_logging_writes_error_log() -> None:
    from latebra.log_utils import setup_file_logging, get_log_path
    log_path = Path(get_log_path())
    # Configure with explicit dir
    test_log_dir = log_path.parent / "test_logs"
    setup_file_logging(log_dir=str(test_log_dir))

    logger = logging.getLogger("latebra_test")
    logger.error("Test error message")

    # Force flush handler
    for h in logger.handlers:
        h.flush()

    error_log = test_log_dir / "errors.log"
    assert error_log.exists()
    content = error_log.read_text()
    assert "Test error message" in content


def test_setup_file_logging_writes_info_log() -> None:
    from latebra.log_utils import setup_file_logging
    test_log_dir = Path(get_log_path()).parent / "test_logs_info"
    setup_file_logging(log_dir=str(test_log_dir))

    logger = logging.getLogger("latebra_test_info")
    logger.info("Test info message")

    for h in logger.handlers:
        h.flush()

    main_log = test_log_dir / "latebra.log"
    assert main_log.exists()
    content = main_log.read_text()
    assert "Test info message" in content


def test_setup_file_logging_does_not_capture_debug() -> None:
    from latebra.log_utils import setup_file_logging
    test_log_dir = Path(get_log_path()).parent / "test_logs_debug"
    setup_file_logging(log_dir=str(test_log_dir))

    logger = logging.getLogger("latebra_test_debug")
    logger.debug("Test debug message")

    for h in logger.handlers:
        h.flush()

    main_log = test_log_dir / "latebra.log"
    if main_log.exists():
        content = main_log.read_text()
        assert "Test debug message" not in content


def test_log_path_returns_absolute_string() -> None:
    from latebra.log_utils import get_log_path
    path = get_log_path()
    assert isinstance(path, str)
    assert path.endswith("logs")
    assert path.startswith("/") or ":" in path  # absolute on both OSes


def test_log_truncate_does_not_raise() -> None:
    from latebra.log_utils import truncate_logs
    # Should not raise even with missing dir
    truncate_logs("/tmp/nonexistent_latebra_test", max_files=5)
    truncate_logs(None, max_files=5)
```

Note: I need `get_log_path` to be accessible. Let me use the actual `get_log_dir` from constants.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_log_utils.py -v`
Expected: ModuleNotFoundError for `latebra.log_utils`

- [ ] **Step 3: Write minimal implementation**

```python
"""Logging utilities for latebra — cross-platform file logging."""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from latebra.constants import get_log_dir


_LOG_DIR: str | None = None


def get_log_path() -> str:
    """Return path to the log directory (absolute string, cross-platform)."""
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

    Creates two log files in the specified (or default) directory:
    - latebra.log: INFO+ messages (rotating, 5MB per file, 3 backups)
    - errors.log:  WARNING+ messages (separate file for error triage)

    Args:
        log_dir: Path to log directory. If None, uses ~/.latebra/logs/.
        max_bytes: Maximum size per log file before rotation.
        backup_count: Number of rotated backups to keep.
    """
    if log_dir is not None:
        log_path = Path(log_dir)
    else:
        log_path = Path(get_log_path())

    log_path.mkdir(parents=True, exist_ok=True)

    # ── Main log (INFO+) ───────────────────────────────────────────
    main_handler = RotatingFileHandler(
        filename=str(log_path / "latebra.log"),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    main_handler.setLevel(logging.INFO)
    main_handler.setFormatter(_formatter())

    # ── Error log (WARNING+) ────────────────────────────────────────
    error_handler = RotatingFileHandler(
        filename=str(log_path / "errors.log"),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(_formatter(detailed=True))

    # ── Root logger ────────────────────────────────────────────────
    root = logging.getLogger()
    # Remove existing file handlers (keep console handlers intact)
    root.handlers = [h for h in root.handlers if not isinstance(h, logging.FileHandler)]
    root.addHandler(main_handler)
    root.addHandler(error_handler)

    # Avoid propagation issues
    root.setLevel(logging.DEBUG)

    global _LOG_DIR
    _LOG_DIR = str(log_path)


def _formatter(detailed: bool = False) -> logging.Formatter:
    """Create log formatter."""
    if detailed:
        fmt = "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d | %(message)s"
    else:
        fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    return logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")


def truncate_logs(log_dir: str | None = None, max_files: int = 10) -> int:
    """Remove oldest rotated logs beyond max_files count.

    Args:
        log_dir: Directory to clean. If None, uses default.
        max_files: Maximum .log files to keep per prefix.

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
        files = sorted(log_path.glob(f"{prefix}*"), key=os.path.getmtime)
        while len(files) > max_files:
            oldest = files.pop(0)
            oldest.unlink(missing_ok=True)
            deleted += 1

    return deleted
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_log_utils.py -v`
Expected: 6/6 PASS

- [ ] **Step 5: Commit**

```bash
git add src/latebra/log_utils.py tests/test_log_utils.py
git commit -m "feat: add cross-platform file logging with rotation"
```

---

### Task 3: Integrar file logging no __main__.py

**Files:**
- Modify: `src/latebra/__main__.py`

- [ ] **Step 1: Add file logging initialization**

```python
# In __main__.py, after logging.basicConfig:
from latebra.log_utils import setup_file_logging, get_log_path

setup_file_logging()
logger.info("File logging initialized. Logs: %s", get_log_path())
```

Wait, I need to be careful. The `basicConfig` is called with `stream=sys.stderr`. If I add file logging after, the handlers from basicConfig stay (console) and I add file handlers on top. That's fine — console + file is the desired behavior.

But `basicConfig` only takes effect if no handlers exist. Since `setup_file_logging` adds handlers to the root logger, subsequent `basicConfig` calls won't work. But in `__main__.py`, `basicConfig` is called FIRST, then `setup_file_logging` adds file handlers. That works.

Let me look at the current __main__.py again:

```python
def main() -> None:
    parser = argparse.ArgumentParser(prog="latebra", ...)
    parser.add_argument("command", nargs="?", default="run")
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    if args.command == "run":
        from latebra.server import serve
        asyncio.run(serve())
```

I need to add `setup_file_logging()` after `basicConfig()`. Also add `sys.excepthook` to capture uncaught exceptions.

Actually, Python already logs uncaught exceptions via `logging` if you use `logging.exception()` in except blocks. But a global `sys.excepthook` would catch crashes too.

Let me keep it simple: add `setup_file_logging()` call and `sys.excepthook`.

- [ ] **Step 2: Verify it works**

Run: `python -m latebra run --verbose & sleep 2 && kill %1`
Check: `ls ~/.latebra/logs/` contains `latebra.log` and `errors.log`

- [ ] **Step 3: Commit**

```bash
git add src/latebra/__main__.py
git commit -m "feat: initialize file logging on startup"
```

---

### Task 4: Adicionar MCP tool latebra_get_log_path

**Files:**
- Modify: `src/latebra/server.py`
- Test: `tests/test_server.py` (if exists, check or add)

- [ ] **Step 1: Add tool definition to server.py**

Add to `tool_definitions` property:

```python
{
    "name": "latebra_get_log_path",
    "description": "Returns the path to the log directory. "
                   "Use this to locate logs when reporting issues.",
    "inputSchema": {
        "type": "object",
        "properties": {},
    },
},
```

Add handler method:

```python
async def _handle_get_log_path(self, args: dict[str, Any]) -> dict[str, Any]:
    from latebra.log_utils import get_log_path
    return {"log_path": get_log_path()}
```

Add to dispatch dict:

```python
"latebra_get_log_path": self._handle_get_log_path,
```

- [ ] **Step 2: Test the tool**

```bash
cd /home/evandro/latebra && /home/evandro/.hermes/venvs/latebra/bin/python -c "
import asyncio
from latebra.server import LatebraServer
async def t():
    s = LatebraServer()
    r = await s._handle_get_log_path({})
    print(r)
asyncio.run(t())
"
```
Expected: `{'log_path': '/home/evandro/.local/share/latebra/logs'}` (or equivalent)

- [ ] **Step 3: Commit**

```bash
git add src/latebra/server.py
git commit -m "feat: add latebra_get_log_path MCP tool"
```

---

### Task 5: Pesquisar melhores lugares para publicar

- [ ] **Step 1: Web search for best open-source project launch channels**

Search queries:
- "best places to launch open source project 2026"
- "where to promote github project reddit hacker news"
- "open source project marketing channels"

- [ ] **Step 2: Compile ranked list with pros/cons**

Categorize:
1. Communities for devs (HN, Reddit, Lobsters)
2. Launch platforms (Product Hunt, BetaList)
3. Content (Dev.to, Medium, YouTube)
4. Directories (Awesome lists, GitHub topics)
5. Social (X/Twitter, LinkedIn)
