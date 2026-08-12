from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _book_voice_prompts import _articulation_prompt  # noqa: E402


def test_articulation_prompt_requires_copy_edit_and_list_shape() -> None:
    prompt = _articulation_prompt(
        "A Chapter",
        "The path rests on three matters: knowledge; sincerity; steadfast action.",
    )

    assert "MANDATORY COPY-EDIT (REQ-BA-112)" in prompt
    assert "spelling, grammar, punctuation, and copy-edit pass" in prompt
    assert "LIST SHAPE (REQ-BA-115)" in prompt
    assert "`1.` lists only for true sequence" in prompt
    assert "`-` bullets for parallel unordered items" in prompt
    assert "source section or paragraph numbering" in prompt


def test_articulation_prompt_sets_a_numeric_window_word_budget() -> None:
    base = " ".join(f"word{i}" for i in range(100))
    prompt = _articulation_prompt("A Chapter", base)

    assert "OUTPUT WORD BUDGET (mechanical" in prompt
    assert "This source window has about 100 words" in prompt
    assert "must never exceed 220 words" in prompt
    assert "Stop when the\nsource window stops" in prompt
