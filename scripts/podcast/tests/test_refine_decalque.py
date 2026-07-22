from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from _authoring._refine import build_phase_0b_window_prompt


def _prompt(de_calque: bool) -> str:
    return build_phase_0b_window_prompt(
        "slug",
        1,
        3,
        Path("in.md"),
        Path("out.md"),
        de_calque=de_calque,
    )


def test_de_calque_absent_by_default() -> None:
    # Flag OFF: the scholarly 0b prompt is byte-for-byte the legacy prompt.
    assert "de-calque" not in _prompt(False).lower()
    assert "Book Pipeline v2" not in _prompt(False)


def test_de_calque_appended_when_enabled() -> None:
    p = _prompt(True)
    assert "de-calque" in p.lower()
    assert "fluent" in p.lower()
    # Still preserves fidelity language (not a loosening of the source contract).
    assert "MUST survive unchanged" in p


def test_de_calque_is_pure_suffix() -> None:
    # Enabling only APPENDS — the legacy prompt is a prefix of the v2 prompt.
    assert _prompt(True).startswith(_prompt(False))
