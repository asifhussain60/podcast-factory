"""_book_mirror.py — one Arabic paragraph, one English paragraph.

WHY (Asif, 2026-07-30). The articulation pass splits a long Arabic paragraph into
several readable English ones, and it splits a speech tag off from the speech: the
Arabic prints `قال الغلام: قلة العذر روعتني…` as ONE paragraph and the English
printed "The boy said:" on a line of its own with the quotation beneath it. Asif
asked for the English paragraphing to mirror the source's, everywhere — 43 speech
tags and, book-wide, 162 paragraphs that merge back into the 534 Arabic ones they
came from.

The edition is a translation edition. Its paragraphing is not the translator's to
choose, and a reader comparing the two columns should never have to work out which
English answers which Arabic. After this pass every group is 1:1 and the reveal
panel's "the N paragraphs below" label has nothing left to say.

WHAT IT MERGES, AND WHAT IT WILL NOT TOUCH:

  * Only PROSE blocks, and only runs of them that are ADJACENT in the raw block
    list. A blockquote, heading or figure between two paragraphs of one source
    paragraph ends the run — merging across it would carry prose over a verse.
  * Only when the alignment still describes THIS text. Every block's fingerprint is
    checked against the pair that claims it (`_para_blocks.para_fingerprint`); one
    mismatch and the whole chapter is left alone, because a stale alignment merging
    paragraphs is how you would silently join two unrelated passages.
  * Never a chapter the human has authored through the Composer. That chapter is
    the author's, per the singular-path rule, and its paragraphing is a choice.

THE CONTINUATION QUOTE. English sets a speech that runs over several paragraphs by
opening each one with a quotation mark and closing only the last. Merge two of
those naively and an orphan `"` lands mid-sentence. So a leading quote is dropped
when the text so far is still INSIDE a quotation — tracked by parity for the
straight `"` this book mostly uses, and by open-minus-close for the curly pair.

THE ALIGNMENT IS REWRITTEN, not re-derived by a model. Merging changes what a
paragraph IS, so every fingerprint downstream of it would miss. The new pairing is
already known exactly — the merged paragraph's source is the group's source — so
this pass emits it directly, and `align_arabic_paragraphs` has nothing to redo.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from _para_blocks import para_fingerprint

_SPLIT_RE = re.compile(r"\n\s*\n")
_NOT_PROSE_RE = re.compile(r"^\s*[>#<]")

# The opening marks a continued speech re-opens with. The straight quote is
# ambiguous (it both opens and closes), so it is judged by PARITY of the text so
# far; the curly pair is judged by how many are still unclosed.
_STRAIGHT = '"'
_CURLY_OPEN = "“"
_CURLY_CLOSE = "”"


def raw_blocks(body: str) -> list[str]:
    """Every block of a chapter body, prose or not, in order and unstripped-of-order."""
    return [b for b in _SPLIT_RE.split(body or "") if b.strip()]


def is_prose(block: str) -> bool:
    """The same test `_para_blocks.prose_blocks` applies, on one block."""
    return not _NOT_PROSE_RE.match(block)


def inside_quotation(text: str) -> bool:
    """Is the accumulated text still inside an open quotation?"""
    curly = text.count(_CURLY_OPEN) - text.count(_CURLY_CLOSE)
    if curly > 0:
        return True
    if curly < 0:
        return False
    return text.count(_STRAIGHT) % 2 == 1


def join_blocks(blocks: list[str]) -> str:
    """Merge prose blocks into one paragraph, dropping continuation quotes."""
    out = blocks[0].strip()
    for block in blocks[1:]:
        nxt = block.strip()
        if inside_quotation(out) and nxt[:1] in (_STRAIGHT, _CURLY_OPEN):
            nxt = nxt[1:].lstrip()
        out = f"{out} {nxt}"
    return out


# A paragraph that is nothing but "X said:" — the speech tag, alone on its line.
_TAG_RE = re.compile(
    r"^[\"“]?[A-Z][^.!?]{0,60}\s"
    r"(?:said|replied|answered|asked|continued|spoke|went on|resumed)"
    r"[^.!?]{0,30}:$"
)


def adopt_tag_sources(blocks: list[str], pairs: list[dict]) -> list[dict]:
    """Let a lone speech tag take the source of the speech it introduces.

    `قال الغلام:` is never a paragraph of its own in the Arabic — it OPENS one. But
    the aligner sometimes pairs the English tag with a span straddling two source
    paragraphs (`[33, 34]`) while the speech that follows is pinned to one (`[34]`),
    and two different signatures never group. Three tags survived the first sweep
    that way.

    So a tag-only block adopts its follower's source, which is where the Arabic
    actually puts it, and the ordinary grouping does the rest — including refusing
    to merge when a blockquote sits between the two. That refusal is why the third
    of those three is still on its own line, and rightly: it introduces a DISPLAYED
    verse, and "The boy said:" belongs above a block quotation exactly as it stands.
    """
    out = [dict(p) for p in pairs]
    for i, block in enumerate(blocks[:-1]):
        if _TAG_RE.match(block.strip()):
            out[i]["source_paras"] = list(out[i + 1].get("source_paras") or [])
    return out


def _groups(pairs: list[dict]) -> list[list[int]]:
    """Indices of the prose blocks that share a source paragraph, consecutively."""
    out: list[list[int]] = []
    prev: str | None = None
    for i, p in enumerate(pairs):
        sig = ",".join(str(n) for n in p.get("source_paras") or [])
        if prev is not None and sig == prev and out:
            out[-1].append(i)
        else:
            out.append([i])
        prev = sig
    return out


def mirror_chapter(body: str, pairs: list[dict]) -> tuple[str, list[dict]] | None:
    """Merge one chapter's prose to the Arabic's paragraphing.

    Returns ``(body, pairs)`` or None when the alignment does not describe this
    text and nothing may safely be merged.
    """
    blocks = raw_blocks(body)
    prose_at = [i for i, b in enumerate(blocks) if is_prose(b)]
    if len(prose_at) != len(pairs):
        return None
    for slot, pair in zip(prose_at, pairs):
        if para_fingerprint(blocks[slot].strip()) != pair.get("fp"):
            return None

    pairs = adopt_tag_sources([blocks[s].strip() for s in prose_at], pairs)
    merged_blocks = list(blocks)
    new_pairs: list[dict] = []
    drop: set[int] = set()
    for group in _groups(pairs):
        slots = [prose_at[i] for i in group]
        # Adjacent in the RAW list, or a blockquote sits between them and the run
        # must stop there rather than carry prose across it.
        runs: list[list[int]] = [[slots[0]]]
        for slot in slots[1:]:
            if slot == runs[-1][-1] + 1:
                runs[-1].append(slot)
            else:
                runs.append([slot])
        idx = 0
        for run in runs:
            text = join_blocks([blocks[s].strip() for s in run])
            merged_blocks[run[0]] = text
            drop.update(run[1:])
            source = pairs[group[idx]]
            confidence = (
                "bracketed"
                if any(pairs[i].get("confidence") == "bracketed" for i in group)
                else source.get("confidence", "verified")
            )
            new_pairs.append(
                {
                    "fp": para_fingerprint(text),
                    "source_paras": source.get("source_paras") or [],
                    "confidence": confidence,
                }
            )
            idx += len(run)

    kept = [b for i, b in enumerate(merged_blocks) if i not in drop]
    return "\n\n".join(b.strip() for b in kept) + "\n", new_pairs


def load_alignment(book_dir: Path) -> dict | None:
    path = book_dir / "_system" / "arabic-alignment.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


__all__ = [
    "inside_quotation",
    "is_prose",
    "join_blocks",
    "load_alignment",
    "mirror_chapter",
    "raw_blocks",
]
