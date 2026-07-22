"""_authoring — LLM-shellout helpers for orchestrate_book.py (A4 split package).

Public API is identical to the old _authoring.py flat module.
All callers that do `from _authoring import X` continue to work unchanged.
"""

from __future__ import annotations

from ._agent_invocations import (
    invoke_challenger,
    invoke_fixer,
    invoke_trainer,
)
from ._book_intelligence import author_phase_0ci
from ._chapter_design import author_phase_0d
from ._core import (
    CHALLENGER_TIMEOUT,
    CLAUDE_CMD,
    DEFAULT_MODEL_LABEL,
    DEFAULT_TIMEOUT,
    FICTION_CONTENT_PROFILES,
    FIXER_TIMEOUT,
    FRAMING_TIMEOUT,
    PHASE_0B_OVERLAP_WORDS,
    PHASE_0B_WINDOW_TIMEOUT,
    PHASE_0B_WINDOW_WORDS,
    PHASE_0C_OVERLAP_WORDS,
    PHASE_0C_WINDOW_TIMEOUT,
    PHASE_0C_WINDOW_WORDS,
    PHASE_0D_SC_TIMEOUT,
    PHASE_0D_SC_TIMEOUT_BASELINE,
    PHASE_0D_SC_TIMEOUT_MAX,
    PHASE_0D_SC_TIMEOUT_MIN,
    PHASE_0D_SC_TIMEOUT_RATE,
    PHASE_0D_TOC_TIMEOUT,
    PHASE_0E_CHAPTER_TIMEOUT,
    TRAINER_TIMEOUT,
    AuthoringError,
    AuthoringHalt,
    _assert_artifact,
    _compute_sc_timeout,
    _read_content_profile,
    _run_claude_p,
    _run_claude_p_with_retry,
)
from ._enrichment import author_phase_0e
from ._framing import author_framing
from ._refine import (
    author_phase_0b,
    author_phase_0c,
    build_phase_0b_window_prompt,
)
