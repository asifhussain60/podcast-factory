"""Book-pipeline phase drivers (book_driver, chapter_driver, audio_driver, etc.).

The wave-execution engine that formerly shared this package (run_wave.py,
the p*/pw* phase runners, the REGISTRY/wave_phases dispatch) was deleted
2026-07-18 — waves 1-6 were fully shipped and it had no live callers. See
_workspace/plan/refactor/plan.md R5 and _workspace/plan/operations/wave-acceptance-checklist.md
for the historical record of what it delivered.
"""

from __future__ import annotations
