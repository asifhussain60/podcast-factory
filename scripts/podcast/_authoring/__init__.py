"""_authoring — LLM-shellout helpers for orchestrate_book.py (A4 split package).

Public API is identical to the old _authoring.py flat module.
All callers that do `from _authoring import X` continue to work unchanged.
"""
from __future__ import annotations

from ._core import (  # noqa: F401
    AuthoringError,
    DEFAULT_MODEL_LABEL,
    CLAUDE_CMD,
    DEFAULT_TIMEOUT,
    FRAMING_TIMEOUT,
    CHALLENGER_TIMEOUT,
    FIXER_TIMEOUT,
    TRAINER_TIMEOUT,
    PHASE_0B_WINDOW_WORDS,
    PHASE_0B_OVERLAP_WORDS,
    PHASE_0B_WINDOW_TIMEOUT,
    PHASE_0C_WINDOW_WORDS,
    PHASE_0C_OVERLAP_WORDS,
    PHASE_0C_WINDOW_TIMEOUT,
    PHASE_0D_TOC_TIMEOUT,
    PHASE_0D_SC_TIMEOUT,
    PHASE_0E_CHAPTER_TIMEOUT,
    PHASE_0D_SC_TIMEOUT_MIN,
    PHASE_0D_SC_TIMEOUT_MAX,
    PHASE_0D_SC_TIMEOUT_RATE,
    PHASE_0D_SC_TIMEOUT_BASELINE,
    _run_claude_p,
    _run_claude_p_with_retry,
    _assert_artifact,
    _compute_sc_timeout,
)
from ._refine import (  # noqa: F401
    build_phase_0b_window_prompt,
    author_phase_0b,
    author_phase_0c,
)
from ._chapter_design import author_phase_0d  # noqa: F401
from ._enrichment import author_phase_0e  # noqa: F401
from ._framing import author_framing  # noqa: F401
from ._convergence import (  # noqa: F401
    invoke_challenger,
    invoke_fixer,
    invoke_trainer,
)
