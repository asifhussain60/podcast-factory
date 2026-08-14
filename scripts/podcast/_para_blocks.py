"""_para_blocks.py — the prose blocks of a chapter, and a stable name for each.

PYTHON HALF OF A MIRROR PAIR. The JavaScript half is
``plan-dashboard/scripts/lib/para-blocks.mjs``. Both are pinned to the SAME
fixtures at ``plan-dashboard/scripts/lib/para-blocks.fixtures.json``, so a change
to either that is not matched in the other fails a test rather than letting the
aligner and the Composer disagree about which blocks a chapter HAS or what each
one is called. A silent disagreement here does not degrade the Arabic reveal — it
puts the wrong Arabic above the wrong paragraph, which is worse than showing none.

WHY FINGERPRINT THE RAW MARKDOWN, and not the rendered text. Both sides read the
same `book/book.md` body, so the raw block is a shared, byte-identical input.
Fingerprinting rendered text would drag in `passage-match.foldText`, which exists
to reconcile two DIFFERENT renderings of one sentence (the Composer keeps
scholarly transliteration where the live reader folds it) and is a much heavier
NFD/combining-mark fold — a real drift risk to port for no gain here.

WHY NOT A POSITIONAL INDEX. Composition is not stable: articulation turned 61
source paragraphs into 133 in one chapter, and any Composer edit that splits a
paragraph shifts every index after it. An index would then place confidently
wrong Arabic above everything downstream, with nothing to signal it. A
fingerprint fails CLOSED — a rewritten paragraph simply has no entry, and the
reveal falls back to the bracket its neighbours pin.
"""

from __future__ import annotations

import hashlib
import re

# A chapter body is split on blank lines; a block is PROSE unless it opens as a
# blockquote, a heading, or a raw HTML block. This mirrors the `paras` count in
# `plan-dashboard/src/lib/reader/composer.ts`, which in turn mirrors what
# `visual-layout.mjs` counts as a paragraph when it places figures — so the three
# agree on what "paragraph 4 of this chapter" means.
_NOT_PROSE_RE = re.compile(r"^\s*[>#<]")
_SPLIT_RE = re.compile(r"\n\s*\n")

# A block that is NOTHING BUT a standalone `![alt](src)` line — see
# para-blocks.mjs's own docstring on this constant for the full history: an
# image line renders as a `chapterImage` editor node the Composer's alignment
# system deliberately does not count as an alignable paragraph, so counting it
# here too disagreed with that count by one per image and disabled every
# alignment button in the chapter.
_IMAGE_ONLY_RE = re.compile(r"^!\[[^\]]*\]\([^)\s]+\)$")


def prose_blocks(body: str) -> list[str]:
    """The chapter's prose blocks, in order, stripped."""
    out = []
    for block in _SPLIT_RE.split(body or ""):
        stripped = block.strip()
        if not stripped:
            continue
        if _NOT_PROSE_RE.match(block):
            continue
        if _IMAGE_ONLY_RE.match(stripped):
            continue
        out.append(stripped)
    return out


def para_fingerprint(block: str) -> str:
    """A stable short name for one prose block.

    Whitespace-collapsed and lowercased before hashing, so a re-wrap or a change
    of indentation does not rename a paragraph that a reader would call the same
    one. Anything more aggressive would start merging paragraphs that genuinely
    differ.
    """
    norm = re.sub(r"\s+", " ", block or "").strip().lower()
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]


def fingerprints(body: str) -> list[str]:
    """`para_fingerprint` of every prose block, in order."""
    return [para_fingerprint(b) for b in prose_blocks(body)]


def blocks_fingerprint(body: str) -> str:
    """One name for a chapter's WHOLE ordered block list.

    The incremental key: when this is unchanged the chapter's prose has not moved,
    so its stored alignment is still valid and re-composing costs nothing.
    """
    joined = "\n".join(fingerprints(body))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]
