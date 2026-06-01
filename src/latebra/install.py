"""Post-installation setup for latebra.

Downloads browser binaries needed by the browser evasions layers.
Run after ``pip install latebra[all]``:

    python -m latebra install
    # or
    latebra install

Autor: Evandro Fonseca Junior
Licença: MIT
"""

from __future__ import annotations

import importlib
import logging
import sys
from typing import Any

logger = logging.getLogger("latebra.install")


async def run_install() -> None:
    """Run the full post-install setup.

    Steps:
    1. Install Chromium via patchright (if available)
    2. Fetch Camoufox binaries (if available)
    3. Print summary
    """
    print("=" * 55)
    print("  latebra post-install setup")
    print("=" * 55)
    print()

    results: list[dict[str, Any]] = []

    # ── Step 1: patchright install chromium ─────
    results.append(await _install_patchright())

    # ── Step 2: camoufox fetch ──────────────────
    results.append(await _install_camoufox())

    # ── Summary ─────────────────────────────────
    print()
    print("=" * 55)
    print("  Summary")
    print("=" * 55)
    ok = sum(1 for r in results if r["status"] == "ok")
    for r in results:
        icon = "✅" if r["status"] == "ok" else ("⚠️" if r["status"] == "skip" else "❌")
        print(f"  {icon} {r['name']}: {r['message']}")
    print()
    print(f"  {ok}/{len(results)} steps completed successfully.")
    print()
    if ok < len(results):
        print("  Some steps were skipped (optional dependencies not installed).")
        print("  The server will still work, but browser-based features")
        print("  may fall back to the HTTP curl_cffi layer.")
    else:
        print("  All browser binaries installed. Ready to scrape!")
    print()


async def _install_patchright() -> dict[str, Any]:
    """Install Chromium via patchright."""
    result: dict[str, Any] = {
        "name": "Patchright (Chromium)",
        "status": "skip",
        "message": "patchright not installed — install with: pip install latebra[browser]",
    }
    try:
        import patchright  # noqa: F401
    except ImportError:
        return result

    try:
        import subprocess
        import sys

        logger.info("Installing Chromium via patchright...")
        proc = await asyncio_subprocess_run(
            [
                sys.executable,
                "-m",
                "patchright",
                "install",
                "chromium",
            ],
            timeout=300,
        )
        if proc.returncode == 0:
            result["status"] = "ok"
            result["message"] = "Chromium installed"
        else:
            result["status"] = "error"
            result["message"] = f"patchright install failed (exit {proc.returncode})"
    except Exception as e:
        result["status"] = "error"
        result["message"] = f"patchright install error: {e}"

    return result


async def _install_camoufox() -> dict[str, Any]:
    """Fetch Camoufox browser binaries."""
    result: dict[str, Any] = {
        "name": "Camoufox browser",
        "status": "skip",
        "message": "camoufox not installed — install with: pip install latebra[browser]",
    }
    try:
        import camoufox  # noqa: F401
    except ImportError:
        return result

    try:
        import subprocess

        logger.info("Fetching Camoufox binaries...")
        proc = await asyncio_subprocess_run(
            [sys.executable, "-m", "camoufox", "fetch"],
            timeout=300,
        )
        if proc.returncode == 0:
            result["status"] = "ok"
            result["message"] = "Camoufox binaries up to date"
        else:
            result["status"] = "error"
            result["message"] = f"camoufox fetch failed (exit {proc.returncode})"
    except Exception as e:
        result["status"] = "error"
        result["message"] = f"camoufox fetch error: {e}"

    return result


async def asyncio_subprocess_run(
    cmd: list[str],
    timeout: int = 300,
) -> subprocess.CompletedProcess:  # type: ignore[name-defined]
    """Run a subprocess asynchronously."""
    import asyncio

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    await asyncio.wait_for(proc.wait(), timeout=timeout)
    return proc  # type: ignore[return-value]


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_install())
