"""Deterministic fidelity gates for a re-voiced chapter window.

Split out of `_book_voice.py` on 2026-08-12 (DR-005). `revoice_gates` and its
one local dependency, `narrative_opening_findings`, are the whole "may this
rewrite replace the base text" contract for `_book_voice.py`,
`_translation_edition.py`, and `rearticulate_chapter.py` alike — self-contained
enough to live on their own, and the natural place to grow when the next gate
that catches a "how could that possibly have shipped" defect gets added.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from _book_articulation_notes import leaked_marker_findings
from _book_compose import _arabic_run_count
from _doctrinal import run_doctrinal_checks
from _literary import teaching_loss_findings
from _narrative import frame_findings

_ASSEMBLED_DETAIL_FLOOR = 0.80
_ASSEMBLED_RUNAWAY_CEILING = 2.50

# Narrator "announcing the telling" openings — a chapter must begin as a chapter,
# not with the narrator framing the act of narration itself (found live 2026-07-19:
# "Let me set down, as faithfully as I can, how my Master opened the matter...",
# 6 instances in one book alone). Searched only within the chapter's own opening
# window (first ~200 chars) — this voice is intentionally first-person and warm
# by design (see REGISTER above), so a broad first-person match would revert
# legitimate prose; only the specific "I am now going to narrate" framing move
# is forbidden, and it can land a few words into the opening sentence (e.g. "I
# held this book back... and I want to tell you why"), not only at position 0.
_NARRATIVE_OPENING_RE = re.compile(
    r"\b("
    r"let me (tell|set down|speak|recount|say)\b"
    r"|i want to tell you\b"
    r"|i shall (now )?(tell|recount|set down)\b"
    r"|before i (tell|set down|begin)\b"
    r"|allow me to (tell|recount|set down)\b"
    r")",
    re.IGNORECASE,
)


def narrative_opening_findings(text: str, base_text: str | None = None) -> list[str]:
    """Flag a chapter that opens by announcing the act of narration instead of
    starting as a chapter does. Checked only against the chapter's own opening.

    DIFFERENTIAL when ``base_text`` is given: the finding is reported only if the
    re-voice INTRODUCED the announcement. Every other gate in ``revoice_gates``
    already reads this way — abridgement measures against the base's word count,
    teaching-loss and the frame guards take both texts, dropped Arabic runs
    compares run counts, and new doctrinal P0s subtract the base's own. This one
    did not, and the asymmetry cost real work: *Ayyuhal Walad* chapter 2 opens
    "Let me tell you of a man among the Children of Israel" in al-Ghazali's own
    letter, so the model preserving that opening — exactly what faithfulness
    demands — was reverted as though it had invented it, and the chapter shipped
    un-articulated. A source that announces its own telling can otherwise never
    pass articulation at all.

    ``base_text=None`` keeps the older single-argument contract for unit tests
    that exercise the phrase-matching in isolation.
    """
    opening = text.strip()[:200]
    if not _NARRATIVE_OPENING_RE.search(opening):
        return []
    # The author already opened this way — preserving it is fidelity, not drift.
    if base_text is not None and _NARRATIVE_OPENING_RE.search(base_text.strip()[:200]):
        return []
    return [f"narrative-announcement opening: {opening[:120]!r}"]


def revoice_gates(
    base_text: str,
    revoiced: str,
    *,
    check_opening: bool = True,
    frame: str | None = None,
    narrator_subject: str = "",
) -> list[str]:
    """Deterministic fidelity gates. Empty list => the re-voice may be kept.

    ``check_opening`` is False for continuation windows of a split chapter — the
    narrative-opening rule is about how a CHAPTER opens, and a mid-chapter window
    that legitimately says "let me tell you" must not be reverted for it.

    ``frame`` adds the narrative guards from ``_narrative``: grammatical person,
    speech-tag integrity, Arabic-script retention, supplied diacritics, and
    enumeration survival. Passed by both routes; omitted only by unit tests that
    exercise the older gates in isolation.
    """
    findings: list[str] = []
    if not revoiced.strip():
        return ["empty re-voice output"]
    base_words = len(base_text.split())
    revoiced_words = len(revoiced.split())
    # Anti-abridgement: a re-voice must be about the same length, never a summary.
    if base_words >= 8 and revoiced_words < 0.6 * base_words:
        findings.append(f"abridged re-voice ({revoiced_words}<{round(0.6 * base_words)} words)")
    # The symmetric case (2026-08-12): a 2,663-word window came back at 39,945
    # words. Nothing here checked for TOO LONG, only too short, so it reached the
    # expensive checks below on a quarter-million-character string and something
    # there threw, uncaught — one window's failure reported as the whole chapter
    # "failed". Returned FIRST, before anything downstream sees the text. 3x
    # leaves headroom for ordinary expansion while catching an order-of-magnitude
    # runaway.
    if base_words >= 8 and revoiced_words > 3 * base_words:
        return [
            f"runaway re-voice ({revoiced_words}>{3 * base_words} words — {round(revoiced_words / base_words, 1)}x source)"
        ]
    findings.extend(teaching_loss_findings(base_text, revoiced))
    if check_opening:
        findings.extend(narrative_opening_findings(revoiced, base_text))
    if _arabic_run_count(revoiced) < _arabic_run_count(base_text):
        findings.append(f"Arabic runs dropped ({_arabic_run_count(revoiced)}<{_arabic_run_count(base_text)})")
    base_p0 = {f.signature for f in run_doctrinal_checks(base_text) if f.severity == "P0"}
    new_p0 = [f for f in run_doctrinal_checks(revoiced) if f.severity == "P0" and f.signature not in base_p0]
    if new_p0:
        findings.append("new doctrinal P0: " + "; ".join(f"{f.check_id}:{f.signature}" for f in new_p0[:3]))
    if frame:
        findings.extend(frame_findings(base_text, revoiced, frame=frame, narrator_subject=narrator_subject))
    findings.extend(leaked_marker_findings(revoiced))
    return findings


def _norm_for_assembly(text: str) -> str:
    return " ".join((text or "").lower().split())


def _adjacent_similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, _norm_for_assembly(left), _norm_for_assembly(right)).ratio()


def assembled_chapter_gates(base_text: str, assembled: str) -> list[str]:
    """Final quality gates after windowed prose has been pieced back together.

    Per-window gates protect fidelity inside each model call. This protects the
    chapter that will actually ship: a set of individually legal windows can
    still assemble into a chapter that is too compressed overall, inflated
    overall, or visibly duplicated at a join.
    """
    findings: list[str] = []
    if not assembled.strip():
        return ["assembled chapter is empty"]

    base_words = len(base_text.split())
    output_words = len(assembled.split())
    if base_words >= 120 and output_words < _ASSEMBLED_DETAIL_FLOOR * base_words:
        findings.append(
            "assembled chapter below detail floor "
            f"({output_words}<{round(_ASSEMBLED_DETAIL_FLOOR * base_words)} words; "
            f"{round(output_words / max(base_words, 1), 2)}x source)"
        )
    if base_words >= 120 and output_words > _ASSEMBLED_RUNAWAY_CEILING * base_words:
        findings.append(
            "assembled chapter expanded too far "
            f"({output_words}>{round(_ASSEMBLED_RUNAWAY_CEILING * base_words)} words; "
            f"{round(output_words / max(base_words, 1), 2)}x source)"
        )

    base_paragraphs = [p for p in re.split(r"\n\s*\n", base_text.strip()) if p.strip()]
    paragraphs = [p for p in re.split(r"\n\s*\n", assembled.strip()) if p.strip()]
    for idx, (left, right) in enumerate(zip(paragraphs, paragraphs[1:]), start=1):
        left_norm = _norm_for_assembly(left)
        right_norm = _norm_for_assembly(right)
        if min(len(left_norm.split()), len(right_norm.split())) < 24:
            continue
        if _adjacent_similarity(left, right) < 0.92:
            continue
        base_idx = idx - 1
        if (
            base_idx + 1 < len(base_paragraphs)
            and _adjacent_similarity(base_paragraphs[base_idx], base_paragraphs[base_idx + 1]) >= 0.92
        ):
            continue
        else:
            findings.append(f"duplicated adjacent paragraphs near assembly join {idx}/{idx + 1}")
            break

    return findings
