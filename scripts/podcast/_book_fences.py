"""_book_fences — one place that knows what a machine fence looks like.

The pipeline delimits the spans it owns in ``book.md`` with HTML-comment markers
(``<!-- editorial:begin -->`` … ``<!-- editorial:end -->``, and the same shape for
``bridge``, ``study-summary`` and ``edition-intro``). Those markers are
load-bearing in two directions: the prose passes EXTRACT fenced spans so no model
is ever handed a machine-authored aside as if it were the book's own text, and
the authoring passes use them to REPLACE a prior block rather than stack a second
one beside it.

THE FORM THIS MODULE EXISTS FOR
The Composer's editor cannot carry an HTML comment through a round-trip: TipTap's
schema has no comment node, so its serializer emits the marker back as a BARE TEXT
line — ``editorial:begin`` on a line of its own. ``book-fences.ts`` restores the
comment form on the way in (``preserveFences`` step 1), but that is the site's
guarantee about the site's own save route, not a property of the file. Any body
that reaches Python between the flattening and the restore carries bare markers,
and every fence regex here used to match ``<!-- … -->`` and nothing else.

A pass that cannot see the fence does not fail loudly — it silently treats the
aside as ordinary prose. That is the whole of the-master-and-the-disciple chapter
3, July 2026: an articulation pass was handed a bare-marked chapter, could not
find the span, rewrote the editorial aside into the narrator's own paragraph, and
the next ``0book-augment`` — equally unable to find the fence it had written —
appended a fresh block instead of replacing the old one. The chapter printed the
same editorial note twice, once wearing the narrator's voice.

So the matcher accepts BOTH forms. The bare alternative is anchored to a whole
line (``re.MULTILINE``), exactly as ``markerOf`` in ``book-fences.ts`` matches only
a trimmed full line, so a chapter that happens to MENTION ``editorial:begin`` mid
sentence is prose and stays prose.

Writing is deliberately not offered here. Each owning module keeps its own
``<!-- <kind>:begin -->`` literal, because ``test_fence_kinds_cross_language.py``
discovers the set of live fence kinds by scanning the pipeline for exactly those
literals and checks it against the two renderer lists on the site side. A kind
that existed only as an argument to a function in this file would be invisible to
that scan, and the renderer would print its markers as visible text.
"""

from __future__ import annotations

import re
from functools import lru_cache


def _marker_pattern(kind: str, side: str) -> str:
    """Either form of one marker: the comment the pipeline writes, or the bare
    line an editor round-trip leaves behind."""
    k = re.escape(kind)
    return rf"(?:<!--[ \t]*{k}:{side}[ \t]*-->|^[ \t]*{k}:{side}[ \t]*$)"


@lru_cache(maxsize=None)
def marker_re(kind: str, side: str) -> re.Pattern[str]:
    """Match a single ``begin``/``end`` marker of ``kind``, in either form."""
    return re.compile(_marker_pattern(kind, side), re.MULTILINE)


@lru_cache(maxsize=None)
def span_re(kind: str, *, leading: str = "", trailing: str = "") -> re.Pattern[str]:
    """Match a whole fenced span of ``kind``, markers included.

    ``leading``/``trailing`` are raw regex fragments the caller appends around the
    span — typically ``r"\\n*"`` — so a strip leaves the surrounding blank lines in
    the shape that caller already produced. Non-greedy between the markers, so two
    spans of the same kind never collapse into one match.
    """
    return re.compile(
        leading + _marker_pattern(kind, "begin") + r".*?" + _marker_pattern(kind, "end") + trailing,
        re.DOTALL | re.MULTILINE,
    )


def strip_spans(text: str, kind: str, *, leading: str = "", trailing: str = "") -> str:
    """Remove every fenced span of ``kind`` from ``text``."""
    return span_re(kind, leading=leading, trailing=trailing).sub("", text)


def find_spans(text: str, kind: str, *, leading: str = "", trailing: str = "") -> list[str]:
    """Every fenced span of ``kind`` in ``text``, verbatim and in document order."""
    return span_re(kind, leading=leading, trailing=trailing).findall(text)


def count_markers(text: str, kind: str, side: str) -> int:
    """How many ``begin``/``end`` markers of ``kind`` appear, in either form."""
    return len(marker_re(kind, side).findall(text))
