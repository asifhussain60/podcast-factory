"""Every fence kind Python AUTHORS is a fence kind the renderers know to hide.

The pipeline delimits spans it owns with comment markers in ``book.md``
(``<!-- editorial:begin -->`` and friends). Each Python module declares only the
one kind it authors: ``_book_frontmatter`` owns ``edition-intro``,
``_self_study`` owns ``study-summary``, and so on. Nothing on the Python side
enumerates the whole set.

The full enumeration lives on the site side, twice — ``FENCE_KINDS`` in
``book-fences.ts`` (the contract, used to restore markers a rich-text edit
flattened) and ``MACHINE_FENCE_KINDS`` in ``book-html.mjs`` (the renderer, used
to SKIP marker lines so they never print as visible text). Those two are pinned
against each other by ``book-html.test.mjs``.

This test closes the remaining gap, and it is the gap that produced a real bug:
``edition-intro`` was added to the contract on 2026-07-21 and the renderer's skip
list was never updated, so the Composer showed ``<!-- edition-intro:begin -->``
as a chapter's first line. A test comparing the two renderer lists to each other
stays GREEN in that situation — both were wrong together at first, and only one
was fixed. Comparing them to what Python actually writes is what catches a kind
added on one side of the language boundary.

Deliberately derived from the source rather than a hardcoded list: a new
``<!-- newkind:begin -->`` in any pipeline module fails this test on the day it
lands, naming the renderer that has not been told.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PODCAST = REPO / "scripts" / "podcast"
SITE = REPO / "plan-dashboard"
BOOK_FENCES_TS = SITE / "src" / "lib" / "reader" / "book-fences.ts"
BOOK_HTML_MJS = SITE / "scripts" / "lib" / "book-html.mjs"

# A fence marker literal as the Python modules write it. Both sides of the pair
# are matched so a module that only ever emits `:end` is still counted.
MARKER_RE = re.compile(r"<!--\s*([a-z][a-z0-9-]*):(?:begin|end)\s*-->")

# Marker-shaped strings that are NOT pipeline fences: `<!-- page N -->` and the
# section markers the source extractor writes are comments the renderers
# deliberately DISPLAY (as .md-comment / .se-section-marker), not hide.
NOT_A_FENCE = {"page", "section"}


def _python_authored_kinds() -> dict[str, set[str]]:
    """Fence kinds each pipeline module writes, keyed by kind -> module names."""
    found: dict[str, set[str]] = {}
    for path in sorted(PODCAST.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        for kind in MARKER_RE.findall(text):
            if kind in NOT_A_FENCE:
                continue
            found.setdefault(kind, set()).add(path.name)
    return found


def _js_array(path: Path, name: str) -> set[str]:
    """Pull a flat string array out of a TS/JS source file."""
    src = path.read_text(encoding="utf-8")
    m = re.search(rf"{re.escape(name)}\s*=\s*\[(.*?)\]", src, re.S)
    assert m, f"{name} not found in {path.name}"
    return set(re.findall(r'"([^"]+)"', m.group(1)))


def test_python_authors_no_fence_kind_the_contract_has_not_declared() -> None:
    """A kind Python writes but `FENCE_KINDS` omits round-trips as bare text.

    `preserveFences` only restores markers for kinds it knows, so an undeclared
    kind is dropped by the first Composer save of that chapter — after which the
    Python phase that owns the span stops matching it.
    """
    authored = _python_authored_kinds()
    declared = _js_array(BOOK_FENCES_TS, "FENCE_KINDS")
    undeclared = {k: sorted(v) for k, v in authored.items() if k not in declared}
    assert not undeclared, (
        f"pipeline modules author fence kinds that book-fences.ts FENCE_KINDS does not declare: {undeclared}"
    )


def test_python_authors_no_fence_kind_the_renderer_would_print() -> None:
    """A kind the renderer's skip list omits renders as escaped `<!-- ... -->`.

    This is the exact 2026-07-21 `edition-intro` regression, in gate form.
    """
    authored = _python_authored_kinds()
    skipped = _js_array(BOOK_HTML_MJS, "MACHINE_FENCE_KINDS")
    unskipped = {k: sorted(v) for k, v in authored.items() if k not in skipped}
    assert not unskipped, (
        f"pipeline modules author fence kinds that book-html.mjs MACHINE_FENCE_KINDS does not skip: {unskipped}"
    )


def test_the_contract_declares_nothing_the_pipeline_never_writes() -> None:
    """The reverse direction, so the lists cannot accumulate dead entries.

    A declared-but-unwritten kind is not dangerous, only misleading — it implies
    a span the pipeline produces when nothing does. Asserted so the enumeration
    stays a description of reality rather than a wish list.
    """
    authored = set(_python_authored_kinds())
    declared = _js_array(BOOK_FENCES_TS, "FENCE_KINDS")
    stale = sorted(declared - authored)
    assert not stale, (
        "book-fences.ts declares fence kinds no pipeline module writes: "
        f"{stale} — retire them, or point this test at the module that owns them"
    )


def test_the_scan_finds_the_kinds_we_know_exist() -> None:
    """Guard the SCAN itself: a regex that silently matched nothing would make
    all three tests above pass vacuously, which is the failure mode a
    derived-from-source test has and a hardcoded one does not."""
    authored = _python_authored_kinds()
    assert len(authored) >= 4, f"scan found only {sorted(authored)}"
    for expected in ("editorial", "study-summary", "bridge", "edition-intro"):
        assert expected in authored, f"{expected} not found by the scan"
