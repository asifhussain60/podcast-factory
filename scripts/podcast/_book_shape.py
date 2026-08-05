"""_book_shape.py — the compose's text-SHAPE sub-phase, in one place.

Two deterministic passes run back to back over the finished prose, and they are
one concern: how the page presents what the model already wrote. Neither reads a
model, neither costs anything, both are idempotent, and both must run AFTER
`5a-arabic` — the Arabic overlay is also the STRIP pass, so each of these reads
the text it leaves rather than the text it is about to change.

  work titles     a cited book prints under the name a reader can read
                  (`_book_work_titles`)
  Arabic blocks   every Arabic display quotation is a blockquote holding its own
                  English rendering (`_book_arabic_blocks`)

The rules, and the failure each one fixes, live in those two module headers. What
lives HERE is only the sequencing and the isolation: a failure in one pass must
not cost the other, because they touch different things and either result is
worth having on its own.

Why a coordinator rather than two steps in `_book_apparatus`: that module is a
single 570-line function sitting at its DR-005 budget, and two more near-identical
try/except blocks would have pushed it over — the gate saying, correctly, that a
new sub-phase belongs in a module rather than as more lines in the sequence.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from _book_arabic_blocks import apply_arabic_blocks
from _book_work_titles import apply_work_titles


def apply_book_shape(book_dir: Path, *, log=lambda _m: None) -> dict[str, Any]:
    """Run both shape passes. Returns what each did, or the error it hit.

    Never raises: a shape pass is never worth a finished book, and the caller
    records ONE skip for the sub-phase. Per-pass failures are reported here so a
    half-run is legible rather than looking like a clean one.
    """
    book_dir = Path(book_dir)
    out: dict[str, Any] = {}
    for name, run in (("work_titles", apply_work_titles), ("arabic_blocks", apply_arabic_blocks)):
        try:
            out[name] = run(book_dir, log=log)
        except Exception as e:
            out[name] = {"error": str(e)}
            log(f"{name.replace('_', '-')}: FAILED — {e}")
    return out
