"""Proofread a transcription without rewriting it, and put its Arabic back.

Extracted from `sessions/read_along.py` (2026-08-30) when phase 0d needed the
same two operations for a book that must never be rewritten but ISN'T going
through the Sessions lane — it keeps 0d's own chapter-boundary intelligence,
which that lane deliberately does not have (see `sessions/ingest.py`: "the
audio map is written out, not inferred").

Living HERE rather than staying in `sessions/read_along.py` and being imported
from there: `_chapter_design.py` is core pipeline code every book runs through,
and `sessions/` is one lane among several. The core pipeline reaching INTO a
lane module for two functions is backwards — importing `sessions.read_along`
also pulls in `sessions.series.SERIES` (a hand-curated per-book audio-mapping
registry) and `sessions.ingest` at module load, neither of which a phase-0d
chapter has anything to do with. A shared, dependency-free module is the
correct shape; `sessions/read_along.py` now imports FROM here instead of
defining these itself, so the Sessions lane's own behaviour is unchanged.

Two operations, meant to be used together, in order:

  correct        PROOFREADING, not writing. Fixes spelling, punctuation,
                 paragraph breaks, and words the transcriber dropped
                 mid-sentence. Gated per-window on how much of the speaker's
                 own vocabulary survives (`_RETENTION_FLOOR`) and on how much
                 the window's length moved (`_LENGTH_BAND`) — a window that
                 fails either is REVERTED to the raw transcription rather than
                 kept, so a corrector that starts improving instead of fixing
                 produces a no-op, never a loss.

  restore_script Puts phonetically-written Arabic back into Arabic script,
                 through the same romanization ladder the rest of the repo
                 uses, with the canonical mushaf's own wording winning over
                 any reconstruction for a run that is actually Qur'an.

`phase` is a required keyword on every call that talks to the model, so the
cost and step ledgers attribute the spend to whichever phase is actually
calling — `sessions-read-along` for the Sessions lane, `0d` for phase-0d
chapter authoring — rather than silently mislabeling one as the other.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from _authoring._claude_runtime import pure_json_call_options, pure_text_call_options
from _authoring._core import _run_claude_p_with_retry

#: The share of the transcription's own words a corrected window must still
#: carry. Punctuation, capitalisation and paragraph breaks move freely under
#: this; a rewritten sentence does not survive it.
_RETENTION_FLOOR = 0.90
#: How much longer or shorter a corrected window may be. Restoring dropped words
#: makes a window slightly longer; summarising makes it much shorter.
_LENGTH_BAND = (0.92, 1.12)

_CORRECT_TIMEOUT = 300
_DETECT_TIMEOUT = 240

#: Words of transcription handed to the corrector at once. Small, because the
#: instruction is "change almost nothing" and a long window invites a model to
#: start improving instead — the same reason the articulation pass windows, at
#: the opposite end of the scale.
_WINDOW_WORDS = 700

_WORD_RE = re.compile(r"[a-z0-9']+")

_CORRECT_PROMPT = """Below is a verbatim transcription of a recorded lecture. It will be
printed as a chapter of a book, and the printed paragraphs are matched against the
recording so a reader can follow the speaker's own voice through them.

YOUR JOB IS PROOFREADING, NOT WRITING. Return the same lecture with these fixes:

- Spelling, including names and places the transcriber misheard.
- Punctuation and capitalisation.
- Paragraph breaks, where the speaker clearly moved to a new point. Blank line between
  paragraphs.
- Words the transcriber plainly dropped mid-sentence, where the missing word is obvious
  from the sentence around it.
- Filler that carries nothing: a stray "um", a stammer, an immediately repeated word.

YOU MUST NOT:
- Reword a sentence, however awkward it reads. Spoken grammar stays spoken grammar.
- Reorder, summarise, expand, or explain anything.
- Change first person to third, or otherwise alter who is speaking.
- Translate, transliterate differently, or "correct" any Arabic. Leave every Arabic
  word exactly as it is spelled here.
- Add a heading, a note, a preamble, or a closing remark.

Output the corrected lecture text ALONE.

TRANSCRIPTION:
{window}"""

_DETECT_PROMPT = """Below is a passage from a transcribed Islamic lecture. The transcriber
wrote every Arabic word phonetically, in English letters.

List every run of Arabic that appears in it — Qur'anic recitation, hadith, invocations,
devotional formulas, and single Arabic terms alike.

Return JSON only: {{"runs": ["...", "..."]}}
Each entry must be copied EXACTLY as it appears in the passage, character for character,
so it can be found by a string search. Do not translate, do not correct, do not merge two
separate runs, and do not include the English around them.
If there is no Arabic, return {{"runs": []}}.

PASSAGE:
{window}"""


def _words(text: str) -> list[str]:
    return _WORD_RE.findall((text or "").lower())


def retention(base: str, candidate: str) -> float:
    """Share of the transcription's words the corrected text still contains.

    A multiset comparison rather than a diff: the corrector is allowed to move a
    word across a paragraph break and to drop a stammer, and neither should read
    as a rewrite. What it cannot do is replace the vocabulary.
    """
    base_words = _words(base)
    if not base_words:
        return 1.0
    remaining: dict[str, int] = {}
    for word in _words(candidate):
        remaining[word] = remaining.get(word, 0) + 1
    kept = 0
    for word in base_words:
        if remaining.get(word):
            remaining[word] -= 1
            kept += 1
    return kept / len(base_words)


def _windows(paragraphs: list[str]) -> list[list[str]]:
    out: list[list[str]] = []
    current: list[str] = []
    count = 0
    for para in paragraphs:
        current.append(para)
        count += len(para.split())
        if count >= _WINDOW_WORDS:
            out.append(current)
            current, count = [], 0
    if current:
        out.append(current)
    return out


def correct(book_dir: Path, base: str, *, phase: str, label: str, log=print) -> tuple[str, list[str]]:
    """Proofread the transcription. Returns the text and what was refused."""
    warnings: list[str] = []
    paragraphs = [p.strip() for p in base.split("\n\n") if p.strip()]
    corrected: list[str] = []

    for index, window in enumerate(_windows(paragraphs), start=1):
        source = "\n\n".join(window)
        step = f"{label}-window-{index:02d}"
        rc, out, err = _run_claude_p_with_retry(
            _CORRECT_PROMPT.format(window=source),
            timeout=_CORRECT_TIMEOUT,
            book_dir=book_dir,
            phase=phase,
            step=step,
            log=log,
            **pure_text_call_options(),
        )
        candidate = (out or "").strip()
        if rc != 0 or not candidate:
            warnings.append(f"{step}: no usable reply, kept the transcription")
            corrected.append(source)
            continue

        kept = retention(source, candidate)
        ratio = len(candidate.split()) / max(1, len(source.split()))
        if kept < _RETENTION_FLOOR:
            warnings.append(f"{step}: reverted, only {kept:.0%} of the spoken words survived")
            corrected.append(source)
            continue
        if not (_LENGTH_BAND[0] <= ratio <= _LENGTH_BAND[1]):
            warnings.append(f"{step}: reverted, length moved to {ratio:.0%} of the transcription")
            corrected.append(source)
            continue
        corrected.append(candidate)

    return "\n\n".join(corrected), warnings


def detect_runs(book_dir: Path, text: str, *, phase: str, label: str, log=print) -> list[str]:
    """The phonetically-written Arabic in a chapter, longest first.

    Longest first so a substitution cannot eat the opening of a longer run it is
    part of — replacing `Bismillah` before `Bismillahir Rahmanir Rahim` would
    leave the tail of the longer run stranded in English letters.
    """
    found: list[str] = []
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    for index, window in enumerate(_windows(paragraphs), start=1):
        source = "\n\n".join(window)
        rc, out, _ = _run_claude_p_with_retry(
            _DETECT_PROMPT.format(window=source),
            timeout=_DETECT_TIMEOUT,
            book_dir=book_dir,
            phase=phase,
            step=f"{label}-arabic-{index:02d}",
            log=log,
            **pure_json_call_options(),
        )
        if rc != 0 or not out:
            continue
        try:
            payload = json.loads(re.sub(r"^```(?:json)?|```$", "", out.strip(), flags=re.M).strip())
        except ValueError:
            continue
        for run in payload.get("runs") or []:
            run = str(run).strip()
            # Only a run the passage actually contains: a model paraphrase of one
            # cannot be substituted, and pretending otherwise would edit text
            # that is not there.
            if run and run in source and run not in found:
                found.append(run)
    return sorted(found, key=len, reverse=True)


def _mushaf_wording(arabic: str):
    """The canonical mushaf's own wording for a run that is Qur'an, else None.

    THE RECONSTRUCTION MUST NOT STAND FOR A VERSE. Rung 3 of the romanization
    ladder renders the letters the transliteration spells, which for scripture is
    close but not the text: the reconstruction of Fussilat 53 came back
    `آيَاتِنَا ... فِي الْآفَاقِ` where the mushaf reads `آيَتِنَا ... فِى ٱلْءَافَاقِ`.
    Close enough to look right on the page, and not the verse.

    The ladder's own library rung cannot catch this — it searches by skeleton
    overlap, and an imperfect reconstruction is exactly the input that search
    misses (3 hits in 83 runs, measured). `_mushaf.is_quranic` recognises the
    same text immediately, because it is asking a different question. So the
    verse is identified here, after the ladder has spoken, and the mushaf's
    wording replaces the reconstruction.
    """
    from _mushaf import is_quranic, mushaf_vocalisation

    if not is_quranic(arabic):
        return None
    return mushaf_vocalisation(arabic)


def restore_script(book_dir: Path, text: str, *, phase: str, label: str, book_title: str = "", log=print):
    """Put every phonetically-written Arabic run back into Arabic script.

    Resolution is `_book_romanization.resolve`, unchanged: the book's own Arabic
    and the library first, a reconstruction from the transliteration when the
    library cannot answer. The metered research rung is off — a transcript
    carries hundreds of runs, and this lane is not the place to buy a search for
    each one.

    On top of the ladder, one rule that outranks all of it: anything the
    canonical mushaf recognises is set from the mushaf. See `_mushaf_wording`.

    Every run records which rung answered it, and a reconstruction is never
    recorded as a citation.
    """
    from _book_romanization import LIBRARY, resolve

    resolutions = []
    seen: set[str] = set()
    for run in detect_runs(book_dir, text, phase=phase, label=label, log=log):
        if run in seen:
            continue
        seen.add(run)
        resolution = resolve(
            run,
            book_dir=book_dir,
            context=book_title,
            book_title=book_title,
            allow_research=False,
            log=log,
        )
        if resolution.ok:
            canonical = _mushaf_wording(resolution.arabic)
            if canonical:
                resolution.arabic = canonical
                resolution.provenance = LIBRARY
                resolution.detail = "canonical mushaf"
        resolutions.append(resolution)
        if resolution.ok:
            text = text.replace(run, resolution.arabic)
    return text, resolutions
