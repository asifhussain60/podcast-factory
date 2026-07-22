"""_subprocess.py — ONE shared subprocess + logging surface for the pipeline.

Phase 4 de-patch: 13+ phase modules each defined a byte-identical ``_run`` /
``_err`` / ``_info`` triplet. They now import from here so the behaviour lives in
ONE place. Call sites are unchanged — modules alias the imports back to the
private names they already use (``from _subprocess import run as _run, …``).

Behaviour is preserved exactly:
  - ``run(cmd, cwd=None, timeout=None)`` → ``(returncode, stdout, stderr)``,
    captured + text-decoded (timeout=None means no timeout, as before).
  - ``info(msg)`` → ``print(msg)`` (stdout).
  - ``err(msg)``  → ``print(f"ERROR: {msg}")`` to stderr.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], *, cwd: "Path | None" = None, timeout: "float | None" = None) -> tuple[int, str, str]:
    """Run ``cmd``, capturing output; return ``(returncode, stdout, stderr)``."""
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return proc.returncode, proc.stdout, proc.stderr


def info(msg: str) -> None:
    """Log an informational line to stdout."""
    print(msg)


def err(msg: str) -> None:
    """Log an error line to stderr (prefixed ``ERROR:``)."""
    print(f"ERROR: {msg}", file=sys.stderr)
