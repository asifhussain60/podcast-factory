"""Canonical phase-name constants for the podcast orchestrator.

Single source of truth for the 14-step orchestrator phase names. Other
modules import `Phase` and `PHASE_ORDER` instead of using literal phase
strings. The plan's P8.6 will land the bulk find/replace that consumes
this module.

Single execution path: NO LEGACY_ALIAS, NO `resolve()` indirection.
Callers do `Phase(name)` directly; unknown names raise `ValueError`.
This is per `_workspace/plan/podcast-plan.yaml` P5.4.
"""
from __future__ import annotations

import sys
if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
    # Polyfill for Python <3.11 (StrEnum landed in 3.11). Air ships 3.9.6.
    from enum import Enum
    class StrEnum(str, Enum):
        pass


class Phase(StrEnum):
    PREFLIGHT       = "01-preflight"
    BRANCH          = "02-branch"
    SCAFFOLD        = "03-scaffold"
    OCR_TRANSLATE   = "04-ocr-translate"
    REFINE_ENG      = "05-refine-english"
    PHONETICS       = "06-phonetics"
    CHAPTER_DESIGN  = "07-chapter-design"
    ENRICHMENT      = "08-enrichment"
    SERIES_PLAN     = "09-series-plan"
    REGISTER_SERIES = "10-register-series"
    PER_CHAPTER     = "11-per-chapter"
    SLIDE_DECKS     = "11b-slide-decks"   # optional; gated by series.enable_slide_decks (default false). Slot between PER_CHAPTER and TRAINER so trainer's substrate scan can absorb slide-deck findings.
    TRAINER         = "12-trainer"
    MERGE           = "13-merge"
    DONE            = "14-done"


# Canonical execution order. The orchestrator advances strictly forward
# through this tuple; resume picks up at whatever phase state.json names.
PHASE_ORDER: tuple[Phase, ...] = tuple(Phase)
