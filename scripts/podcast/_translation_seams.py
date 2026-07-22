"""Seam and duplication analysis for composed book text.

Split out of ``_translation_text.py`` (DR-005 line-count gate, 2026-07-20). Every
name here answers one question: has a passage of the book been rendered twice?

Three rules, in the order they were needed, each blind to what the next one sees:

  ``_trim_seam_overlap``        verbatim echo at a window join, trimmed at compose
  ``dedupe_seam_paragraphs``    reworded twin sitting NEXT to its original
  ``duplicate_passage_findings`` reworded twin several paragraphs away — reported,
                                never deleted, because on 2026-07-20 each copy of
                                one turned out faithful where the other was wrong

``_translation_text`` re-exports all of them, so existing importers are unaffected.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

_SEAM_LOOKBACK = 3
_SEAM_MIN_WORDS = 6
_SEAM_RATIO = 0.80
_SEAM_RUN = 12


def _overlap_tokens(text: str) -> list[str]:
    """Normalize a passage to comparable tokens: casefold, drop punctuation."""
    folded = re.sub(r"[^\w\s]", " ", (text or "").casefold())
    return re.sub(r"\s+", " ", folded).strip().split()


def _split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", (text or "").strip()) if p.strip()]


def _para_is_echo(candidate: str, prior: str) -> bool:
    """True when ``candidate`` is a chunk-seam echo of ``prior``.

    Deliberately conservative — fires only on whole-paragraph near-identity or a
    long verbatim token run that covers most of the candidate — so genuinely
    distinct adjacent paragraphs (a real narrative continuation) are never
    trimmed. This catches the ``compose_book_v2`` seam double-render where a
    boundary passage is composed into two adjacent windows/chapters.
    """
    cand = _overlap_tokens(candidate)
    prev = _overlap_tokens(prior)
    if len(cand) < _SEAM_MIN_WORDS or not prev:
        return False
    matcher = SequenceMatcher(None, cand, prev, autojunk=False)
    if matcher.ratio() >= _SEAM_RATIO:
        return True
    block = matcher.find_longest_match(0, len(cand), 0, len(prev))
    return block.size >= _SEAM_RUN and block.size >= 0.6 * len(cand)


def _trim_seam_overlap(prev_prose: str, next_prose: str) -> str:
    """Drop leading paragraphs of ``next_prose`` that echo the tail of
    ``prev_prose``. Whole-paragraph drops only; the surviving text is never
    edited. Returns ``next_prose`` unchanged when nothing echoes."""
    if not (prev_prose or "").strip() or not (next_prose or "").strip():
        return next_prose
    prev_tail = _split_paragraphs(prev_prose)[-_SEAM_LOOKBACK:]
    if not prev_tail:
        return next_prose
    next_paras = _split_paragraphs(next_prose)
    drop = 0
    for para in next_paras[:_SEAM_LOOKBACK]:
        if any(_para_is_echo(para, tail) for tail in prev_tail):
            drop += 1
        else:
            break
    if not drop:
        return next_prose
    return "\n\n".join(next_paras[drop:]).strip()


# Similarity-based seam de-dup — catches reworded twin renders the verbatim
# _trim_seam_overlap cannot see (the fluency de-calque pass rewords each copy of a
# seam double-render differently, so exact-match trimming misses them). Two rules,
# each calibrated on real content with a wide safety margin to the nearest
# legitimate pair (within-chapter next-legit ~0.56 ratio; boundary next-legit ~0.26
# containment):
_ADJ_DEDUP_RATIO = 0.62  # within a chapter: paragraph vs immediate predecessor
_BOUNDARY_DEDUP_CONTAINMENT = 0.42  # chapter open vs previous chapter's last paragraph
_BOUNDARY_DEDUP_MIN_RUN = 5
_NUMBERED_CHAPTER_RE = re.compile(r"^##\s+\d+\.")


def _adjacent_echo(cur: str, prev: str) -> bool:
    a, b = _overlap_tokens(cur), _overlap_tokens(prev)
    if len(a) < _SEAM_MIN_WORDS or len(b) < _SEAM_MIN_WORDS:
        return False
    return SequenceMatcher(None, a, b, autojunk=False).ratio() >= _ADJ_DEDUP_RATIO


def _boundary_echo(cur: str, prev: str) -> bool:
    a, b = _overlap_tokens(cur), _overlap_tokens(prev)
    if len(a) < _SEAM_MIN_WORDS or len(b) < _SEAM_MIN_WORDS:
        return False
    matcher = SequenceMatcher(None, a, b, autojunk=False)
    matched = sum(block.size for block in matcher.get_matching_blocks())
    containment = matched / min(len(a), len(b))
    if containment < _BOUNDARY_DEDUP_CONTAINMENT:
        return False
    return matcher.find_longest_match(0, len(a), 0, len(b)).size >= _BOUNDARY_DEDUP_MIN_RUN


def record_seam_removals(book_dir: Path, pass_name: str, removed: list[dict], log) -> None:
    """Persist every paragraph ``dedupe_seam_paragraphs`` deleted, and say so.

    The de-dup runs twice per compose (once inside the base assembly, once over
    the fully re-voiced text) and each run can delete a paragraph on a similarity
    judgment. A false positive is a passage that leaves the book forever, so the
    removals are appended — not overwritten — and the full text of each is kept,
    which is what makes an accidental deletion recoverable without a git
    archaeology session. ``compose_book_v2`` clears the file at the start of a run,
    so it describes THIS compose rather than every compose the book has had.
    """
    path = Path(book_dir) / "_system" / "book-seam-dedup.json"
    try:
        existing: list[dict] = []
        if path.exists():
            try:
                existing = json.loads(path.read_text(encoding="utf-8")).get("removed", [])
            except Exception:
                existing = []
        existing.extend({"pass": pass_name, **record} for record in removed)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"schema": "book.seam-dedup/v1", "removed": existing}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except Exception:  # a recorder must never become the failure it records
        pass
    if removed:
        log(f"    seam-dedup ({pass_name}): {len(removed)} paragraph(s) DELETED — see _system/book-seam-dedup.json")
        for record in removed[:3]:
            log(f"      {record['rule']} · {record['chapter'][:40]} · {record['words']} words")


def dedupe_seam_paragraphs(text: str, *, removed: list[dict] | None = None) -> str:
    """Drop reworded seam double-renders that survive the verbatim trimmer.

    Runs LAST, on the fully-assembled (and, in v2, de-calqued) book text, because
    the rewording that hides these twins from exact matching happens after compose.
    Two conservative, whole-paragraph-only rules:
      - within a chapter, a paragraph that echoes its IMMEDIATE predecessor
        (token ratio >= 0.62) is a model/window self-repeat — drop the second copy;
      - a chapter's FIRST paragraph that echoes the previous chapter's LAST
        paragraph (containment >= 0.42, with a real shared run) is a boundary
        over-run — drop the echo so the chapter opens on its own content.
    Never edits surviving text; comparisons are immediate-neighbour only, so a
    distant legitimate refrain is untouched.

    Pass ``removed`` to receive one record per deleted paragraph. This function
    DELETES SOURCE-BEARING PROSE, and until 2026-07-21 it did so with no log, no
    count and no report — a false positive at the ratio floor (a liturgical
    refrain, a question restated before its answer) simply left the book and
    nothing recorded that it had ever been there. Its sibling
    ``duplicate_passage_findings`` is deliberately report-only for exactly this
    reason; this one still deletes, so the least it can do is say what it took.
    """
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    out: list[str] = []
    prev_para: str | None = None  # last kept paragraph (within-chapter adjacency)
    prev_chapter_last: str | None = None
    at_chapter_open = False  # first paragraph after a numbered chapter heading
    chapter = ""

    def _record(rule: str, block: str, against: str) -> None:
        if removed is None:
            return
        removed.append(
            {
                "rule": rule,
                "chapter": chapter,
                "words": len(block.split()),
                "removed_text": block,
                "kept_neighbour_head": " ".join(against.split()[:30]),
            }
        )

    for block in blocks:
        if block.startswith("#"):
            if _NUMBERED_CHAPTER_RE.match(block):
                prev_chapter_last = prev_para
                at_chapter_open = True
                chapter = block.lstrip("# ").strip()
            out.append(block)
            prev_para = None  # adjacency does not cross a heading
            continue
        if at_chapter_open and prev_chapter_last and _boundary_echo(block, prev_chapter_last):
            at_chapter_open = False
            _record("boundary-echo", block, prev_chapter_last)
            continue  # drop the chapter-opening echo
        if not at_chapter_open and prev_para is not None and _adjacent_echo(block, prev_para):
            _record("adjacent-echo", block, prev_para)
            continue  # drop the adjacent within-chapter echo
        at_chapter_open = False
        out.append(block)
        prev_para = block
    return "\n\n".join(out).strip() + "\n"


# Block re-narration — the seam defect BOTH rules above are blind to. When a
# windowed chapter's window N runs past its own passage and narrates the beats
# that belong to window N+1, N+1 then renders them properly and the book prints
# the whole scene twice, in different words, several paragraphs apart. Neither
# copy is adjacent to its twin (they are separated by the length of the block),
# so `_adjacent_echo` never sees them, and neither sits at a chapter boundary,
# so `_boundary_echo` never sees them either. What IS visible is the shape: two
# or more CONSECUTIVE paragraphs each echoing a paragraph at the same distance
# back. A legitimate refrain repeats once; a re-narrated block repeats in
# formation.
#
# Calibrated on the four books with a composed `book/book.md` as of 2026-07-20.
# Three true positives (the-master-and-the-disciple ch7, mukhtasar-ul-asar-1 ch8
# and ch9 — all verified by reading both copies), zero false positives. Single
# pairs are deliberately NOT reported: the highest-scoring legitimate pair in the
# corpus (0.63, a dialogue exchange whose two halves share a formula) outranks the
# weakest pair inside a real duplicate run, so pair score alone cannot separate
# them and only the run does.
_DUP_LAG_MAX = 6  # how far back a twin may sit; a window seam puts it 2-5 apart
_DUP_RATIO = 0.45  # token-sequence similarity of one pair
_DUP_SHARED_RARE = 6  # distinctive content words the pair must share
_DUP_RARE_MAX_DF = 25  # a word this common book-wide is not distinctive
_DUP_MIN_TOKENS = 40  # short paragraphs (a one-line speech tag) are never judged
_DUP_MIN_RUN = 2  # consecutive same-lag pairs required to report


def _rare_words(paragraph: str, doc_freq: Counter) -> set[str]:
    return {w for w in set(_overlap_tokens(paragraph)) if len(w) > 3 and doc_freq[w] <= _DUP_RARE_MAX_DF}


def _dup_pair_score(cur: str, prior: str, doc_freq: Counter) -> tuple[float, int]:
    """``(sequence ratio, shared distinctive words)`` for one candidate twin pair."""
    a, b = _overlap_tokens(cur), _overlap_tokens(prior)
    if len(a) < _DUP_MIN_TOKENS or len(b) < _DUP_MIN_TOKENS:
        return 0.0, 0
    ratio = SequenceMatcher(None, a, b, autojunk=False).ratio()
    shared = len(_rare_words(cur, doc_freq) & _rare_words(prior, doc_freq))
    return ratio, shared


def duplicate_passage_findings(text: str) -> list[dict]:
    """Report passages the book narrates twice. IDENTIFY-ONLY — never mutates.

    Returns one record per duplicated block, each naming both copies by chapter
    and paragraph index so a reader can compare them against the source.

    This deliberately does NOT delete the second copy the way the seam de-dup
    rules above do, and the reason is the incident that produced it. On
    2026-07-20 a duplicated scene in `the-master-and-the-disciple` ch7 looked
    like a clean case of "keep the later telling, drop the earlier". Read clause
    by clause against the Arabic scan, EACH telling was faithful where the other
    was wrong — and two sentences of the source were missing from BOTH, so the
    duplication had been masking an omission. An automatic drop of either copy
    would have destroyed source material and left the omission invisible. A
    duplicate is therefore evidence that a passage needs human comparison against
    the source, not an instruction the machine can carry out.

    Known limitation: a text that reuses long sentence frames across consecutive
    turns — a catechism whose every answer opens "They are the likenesses of…" —
    can score like a re-narration. Zero such cases exist in the corpus this was
    calibrated on, and the consequence of one is a passage a human looks at and
    clears, not a passage the pipeline deletes. Tuned in that direction on
    purpose: a missed duplicate ships a scene twice, a false one costs a glance.
    """
    findings: list[dict] = []
    doc_freq = Counter(_overlap_tokens(text))
    blocks = [b.strip() for b in re.split(r"\n\s*\n", (text or "").strip()) if b.strip()]
    chapter = ""
    paragraphs: list[str] = []

    def sweep() -> None:
        for lag in range(1, _DUP_LAG_MAX + 1):
            run: list[tuple[int, float, int]] = []
            for i in range(lag, len(paragraphs)):
                ratio, shared = _dup_pair_score(paragraphs[i], paragraphs[i - lag], doc_freq)
                if ratio >= _DUP_RATIO and shared >= _DUP_SHARED_RARE:
                    run.append((i, ratio, shared))
                    continue
                _emit(lag, run)
                run = []
            _emit(lag, run)

    def _emit(lag: int, run: list[tuple[int, float, int]]) -> None:
        if len(run) < _DUP_MIN_RUN:
            return
        first, last = run[0][0], run[-1][0]
        findings.append(
            {
                "chapter": chapter,
                "lag": lag,
                "first_copy_paragraphs": [first - lag, last - lag],
                "second_copy_paragraphs": [first, last],
                "paragraphs": len(run),
                "min_ratio": round(min(r for _, r, _ in run), 3),
                "min_shared_words": min(s for _, _, s in run),
                "first_copy_opens": paragraphs[first - lag][:160],
                "second_copy_opens": paragraphs[first][:160],
            }
        )

    for block in blocks:
        if block.startswith("#"):
            sweep()
            chapter = re.sub(r"^#{1,6}\s+", "", block).strip()
            paragraphs = []
            continue
        paragraphs.append(block)
    sweep()
    return findings
