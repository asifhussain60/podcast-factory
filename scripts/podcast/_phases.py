"""Canonical phase registry — thin re-export of the single source of truth.

The single source of truth for the orchestrator phase sequence is
``_progress.PHASES``. This module re-exposes it as ``PHASE_ORDER`` for callers
that want a phase-list import without pulling in the rest of ``_progress``.

History: this file used to declare an independent ``Phase`` StrEnum with
display-style names (``01-preflight`` … ``14-done``) — a P5.4 deliverable that
P8.6 was meant to adopt via a bulk find/replace. That adoption never happened:
the runtime uses the machine names in ``_progress.PHASES`` everywhere, and the
enum drifted from both reality and its own test. It is now a re-export so there
is exactly ONE phase list in the codebase. (Machine names like ``0a`` / ``06a``
are not valid Python identifiers, so a StrEnum view is intentionally not offered.)
"""
from __future__ import annotations

from _progress import PHASES as PHASE_ORDER  # noqa: F401  (re-export)

__all__ = ["PHASE_ORDER"]
