"""_playwright_diag.py — say what is actually wrong when Playwright cannot launch Chromium.

Playwright words "no browser installed" and "a different build is installed" identically ("Executable
doesn't exist at …/chromium_headless_shell-1223/…"). isaf-al-talib, 2026-09-18: the render reported the
browser as not installed while it was — build 1243 was cached and Playwright 1.60 wanted 1223, because
another project's newer Playwright shares the cache. The message sent a person to install what they
had, and they worked around it with two symlinks. This reads the wanted build out of the error and
compares it with what the cache holds, so the message names the real cause and the real remedy.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

_WANTED = re.compile(r"(chromium(?:_headless_shell)?)-(\d+)")
INSTALL = "cd plan-dashboard && npx playwright install chromium"


def default_cache_dir() -> Path:
    override = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if override and override != "0":
        return Path(override)
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "ms-playwright"
    if sys.platform.startswith("win"):
        return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "ms-playwright"
    return Path.home() / ".cache" / "ms-playwright"


def _installed_builds(cache_dir: Path) -> set[str]:
    if not cache_dir.is_dir():
        return set()
    return {m.group(2) for p in cache_dir.iterdir() if (m := _WANTED.fullmatch(p.name))}


def diagnose_launch_failure(stderr: str, *, cache_dir: Path | None = None) -> str:
    """One accurate sentence (plus the remedy) for a failed `chromium.launch()`."""
    first = next((ln.strip() for ln in stderr.splitlines() if ln.strip()), "no error text")
    wanted = _WANTED.search(stderr)
    if not wanted:
        return f"Chromium could not be launched: {first[:240]}"
    build = wanted.group(2)
    installed = _installed_builds(cache_dir if cache_dir is not None else default_cache_dir())
    if build in installed:
        return (
            f"Chromium build {build} IS installed but could not be launched, so this is not an install problem. "
            f"Detail: {first[:240]}"
        )
    if installed:
        have = ", ".join(sorted(installed))
        return (
            f"Chromium revision mismatch: this project's Playwright needs build {build} but the shared cache only has "
            f"{have} (another project's newer Playwright installed those and evicted {build}). Fix: {INSTALL} — it "
            f"downloads {build} alongside and keeps {have} for the other project. Don't symlink {build} to {have}: "
            "it appears to work, but it hides the mismatch."
        )
    return f"Chromium is not installed (Playwright wants build {build}). Fix: {INSTALL}"
