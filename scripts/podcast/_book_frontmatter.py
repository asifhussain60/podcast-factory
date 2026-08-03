"""_book_frontmatter.py — the retired machine preface, and its removal.

WHAT THIS MODULE USED TO DO, AND WHY IT NO LONGER DOES IT
---------------------------------------------------------
Until 2026-08-03 this module AUTHORED an "edition introduction": three to five
hundred words a model wrote *about* each book — what kind of text it is, who is
attributed with it, what its technical vocabulary is doing — injected above the
source's own opening under a fence, with the source's words demoted beneath a
machine-invented ``### The book's own opening`` subheading.

Asif's direction (2026-08-03): **no book needs a preface; they begin with the
actual content chapters.** Applied honestly that removes what the pipeline wrote
about each book and keeps what each author wrote, folded into chapter 1 by
``_translation_edition``. The authoring path is therefore gone — the brief, the
fact-gathering, the gate, the injector and the cache read.

WHAT SURVIVES, AND WHY
----------------------
``strip_introduction`` and the two marker literals. Five editions carry a fence
written by the retired path, and one of them carries it INSIDE a Composer edit,
so it is replayed into ``book.md`` on every compose from the sidecar. Deleting
the code that writes a fence does not delete the fences already written; only a
cleanup step does that, and it must run AFTER the Composer replay for exactly
that reason. ``_book_apparatus`` wires it in the slot the authoring step used to
occupy.

The ``edition-intro`` marker literals stay here for a second reason beyond the
strip: ``test_fence_kinds_cross_language.py`` discovers live fence kinds by
scanning the pipeline for them, and the renderers on the site side declare the
same set. De-registering the kind while any book still carries a fence would make
those surviving markers render as literal text — the exact 2026-07-21 regression
that test exists to catch, run backwards.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from _book_fences import span_re

INTRO_OPEN = "<!-- edition-intro:begin -->"
INTRO_CLOSE = "<!-- edition-intro:end -->"
# Matches the bare-marker form as well — see `_book_fences`. An introduction whose
# fence a Composer save flattened must still be found here, or the cleanup leaves
# a machine preface on the page and reports success.
_INTRO_SPAN_RE = span_re("edition-intro", leading=r"\n*", trailing=r"\n*")

# The subheading the retired injector wrote to title the source's opening beneath
# the machine preface. It normally lives INSIDE the fence and goes with it, but
# `the-master-and-the-disciple` was split by hand before the fence existed, so the
# label can also appear on its own. It names a distinction the edition no longer
# draws, so it is cleaned up either way.
_OWN_OPENING_HEADING_RE = re.compile(r"(?m)^\s*###\s+The book's own opening\s*$\n?")

# Where the retired path cached its authored text. Nothing reads it any more; the
# constant is kept so `clear_introduction` can retire the file alongside the fence.
CACHE_NAME = "edition-introduction.md"


def strip_introduction(book_md: str) -> str:
    """Remove a previously injected introduction, whitespace normalized."""
    return _OWN_OPENING_HEADING_RE.sub("", _INTRO_SPAN_RE.sub("\n\n", book_md))


def clear_introduction(book_dir: Path, *, log=print) -> dict[str, Any]:
    """Take the machine preface out of ``book/book.md``. Report-shaped.

    Idempotent and free: a book that never had one, or has already been cleaned,
    is left byte-identical and reports ``removed: False``. Runs on every compose
    rather than once, because the fence can come BACK — a Composer edit saved
    while the fence was still being written carries it in the sidecar, and the
    replay puts it back on every run until the edit itself is migrated.
    """
    book_dir = Path(book_dir)
    book_md = book_dir / "book" / "book.md"
    if not book_md.exists():
        return {"removed": False, "reason": "no book.md"}
    before = book_md.read_text(encoding="utf-8")
    after = strip_introduction(before)
    if after == before:
        return {"removed": False}
    book_md.write_text(after, encoding="utf-8")
    words = len(before.split()) - len(after.split())
    log(f"    front-matter: machine preface removed ({words} words)")
    return {"removed": True, "words": words}
