#!/usr/bin/env python3
"""The deterministic tail has ONE definition and two callers.

`_book_apparatus.apply_book_apparatus` is the tail of a compose — replay, house
style, Arabic apparatus, audits, bridges, honorifics, alignment. `compose_book_v2`
runs it after its model passes; `apply_book_apparatus.py` runs it standalone over
a book already on disk, so an existing edition's Arabic can be brought up to
current rules without re-running a model over its prose.

The value of that split is entirely in the two paths being the SAME code. If
compose ever grows its own copy of a step, a standalone run stops meaning what it
says, and the books brought current through it quietly diverge from the books
composed fresh. These tests pin the delegation.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import _book_apparatus  # noqa: E402
import _book_pipeline_v2  # noqa: E402

_PIPELINE_SRC = (SCRIPT_DIR / "_book_pipeline_v2.py").read_text(encoding="utf-8")
_CLI_SRC = (SCRIPT_DIR / "apply_book_apparatus.py").read_text(encoding="utf-8")

# Every module that hosts apparatus step call sites, concatenated. Read from
# `_apparatus_steps.APPARATUS_MODULES` rather than naming `_book_apparatus.py` alone:
# when the report-only steps moved to `_book_reports` on 2026-08-08 this test, and two
# others like it, silently stopped seeing three of the steps they exist to pin.
from _apparatus_steps import APPARATUS_MODULES  # noqa: E402

_APPARATUS_SRC = "\n".join((SCRIPT_DIR / name).read_text(encoding="utf-8") for name in APPARATUS_MODULES)


def test_compose_delegates_the_tail_rather_than_owning_it():
    assert "from _book_apparatus import apply_book_apparatus" in _PIPELINE_SRC
    assert "return apply_book_apparatus(" in _PIPELINE_SRC


def test_the_cli_calls_the_same_function():
    assert "from _book_apparatus import apply_book_apparatus" in _CLI_SRC
    assert "apply_book_apparatus(book_dir" in _CLI_SRC


def test_compose_keeps_no_copy_of_any_apparatus_step():
    """Not one `_record_skip` call site may remain on the compose side.

    That is the cheap, exact signal: every apparatus step is wrapped in one, so a
    step re-appearing in compose means a second copy of the sequence exists.
    """
    assert not re.search(r'_record_skip\(book_dir,\s*"', _PIPELINE_SRC), (
        "an apparatus step has reappeared in _book_pipeline_v2 — there must be only one copy"
    )


def test_every_apparatus_step_lives_in_the_apparatus():
    labels = set(re.findall(r'_record_skip\(book_dir,\s*"([^"]+)"', _APPARATUS_SRC))
    # The full sequence as of the 2026-08-02 split. A change here is a real change
    # to what a compose does and should be a deliberate edit, not a surprise.
    assert labels == {
        "composer-edits",
        "report-reconcile",
        "translit",
        "arabic-substitution",
        "quran-arabic",
        "citation-names",
        "glossary-harvest",
        "annotation-policy",
        "etymology",
        "glossary-vowelling",
        "inline-arabic",
        "text-shape",
        "vowelling",
        "spelling",
        "front-matter",
        "opening-fold",
        "introduction",
        "arabic-audit",
        "duplication",
        "visual-policy",
        # Added 2026-08-09. Scans the FINISHED page for the five defects Asif found by
        # eye; called after step 11 rather than with the three report steps above,
        # because the honorific convention and the paragraph mirror both run between.
        "defect-scan",
        "bridges",
        "honorifics",
        "arabic-alignment",
        "paragraph-mirror",
        "substitution-restamp",
    }, sorted(labels)


def test_the_model_passes_stayed_on_the_compose_side():
    """The tail must not acquire a model prose pass — that is what makes it safe."""
    for model_pass in ("apply_fluency_adapt", "apply_author_companion_voice", "author_phase_book_augment"):
        assert model_pass in _PIPELINE_SRC, f"{model_pass} should still be in compose"
        assert model_pass not in _APPARATUS_SRC, (
            f"{model_pass} reached the apparatus — a standalone run would rewrite prose, "
            "which is exactly what the split exists to prevent"
        )


def test_the_apparatus_accepts_no_stages_and_does_not_crash_on_it():
    """A standalone run has no model stages to report; that must be a valid call."""
    import inspect

    sig = inspect.signature(_book_apparatus.apply_book_apparatus)
    assert sig.parameters["stages"].default is None
    assert sig.parameters["force"].default is False


def test_compose_still_exports_its_entry_point():
    assert callable(_book_pipeline_v2.compose_book_v2)
