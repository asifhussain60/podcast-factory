"""_book_compose.py — shared compose helpers for the book lane.

A HELPER MODULE ONLY. The pipeline's 0book-compose phase routes through the
unified ``_book_pipeline_v2.compose_book_v2``; what lives here is the shared
source-slicing / Arabic-page / Quran-anchor machinery that the v2 faithful base
(``_translation_edition``), ``_book_voice`` and ``validate_book_ready`` import.

It also held a second, superseded whole-book composer — ``author_phase_book_compose``
plus a ``main()`` that invoked it from the command line — deleted 2026-07-21. It was
not dead code in the harmless sense: it wrote ``book/book.md`` directly and
repopulated the stale first-person ``book/_chunks/book/`` cache, so running the
module as a script clobbered a good compose with prose from a route the pipeline
retired, in a narrative frame the repo's locked rule forbids. A file that can
destroy the deliverable by being run is worse than a missing feature.
"""

from __future__ import annotations

import re
from pathlib import Path

from _authoring._core import AuthoringError, _run_claude_p, pure_text_call_options
from _literary import _VOICE_INSTRUCTIONS, chapter_craft_block

# Per-chapter wall budgets. 420s proved too tight in practice (2026-06-11:
# a 631-word chapter ran ~16 min on Opus and the whole phase aborted at
# chapter 1); compose calls re-voice full chapters, so give them the same
# order of budget as phase-0d authoring calls.
_COMPOSE_TIMEOUT = 900
_RETRY_TIMEOUT = 1350

_PAGE_MARK = re.compile(r"<!--\s*page\s*(\d+)\s*-->", re.IGNORECASE)


def _slice_source(lines: list[str], ranges: list[list[int]]) -> str:
    out: list[str] = []
    for a, b in ranges:
        out.extend(lines[a - 1 : b])  # 1-based inclusive
    text = "\n".join(out)
    text = _PAGE_MARK.sub("", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _line_pages(lines: list[str]) -> list[int]:
    """Source page carried by each line of the line-numbered design input.

    Lines before the first ``<!-- page N -->`` marker belong to page 1."""
    pages: list[int] = []
    cur = 1
    for ln in lines:
        m = _PAGE_MARK.search(ln)
        if m:
            cur = int(m.group(1))
        pages.append(cur)
    return pages


def _pages_for_ranges(line_pages: list[int], ranges: list[list[int]]) -> list[int]:
    out: set[int] = set()
    for a, b in ranges:
        lo, hi = max(1, a), min(len(line_pages), b)
        out.update(line_pages[lo - 1 : hi])
    return sorted(out)


def _load_arabic_pages(book_dir: Path) -> dict[int, str] | None:
    """Per-page Arabic OCR ground truth from Phase 0a, when the source was Arabic script.

    Returns None for books without an Arabic OCR extract (fiction, technical, English
    sources) — composition then behaves exactly as before."""
    from _vowelled_source import resolve_arabic_source

    src = book_dir / "_system" / "source" / "ocr" / "raw-extract.md"
    if not src.exists():
        return None
    # Prefer the vowelled copy of this exact OCR when `vowel_source` has made one:
    # the ground truth handed to the compose prompt then carries its marks, so a
    # quoted verse arrives vowelled instead of being re-derived at the end. Falls
    # back to the raw extract whenever no sibling exists or the OCR has since been
    # re-run — see `_vowelled_source` for why staleness is fingerprinted.
    src = resolve_arabic_source(src)
    text = src.read_text(encoding="utf-8")
    if _arabic_run_count(text) < 50:
        return None
    pages: dict[int, str] = {}
    cur: int | None = None
    buf: list[str] = []
    for ln in text.split("\n"):
        m = _PAGE_MARK.search(ln)
        if m:
            if cur is not None:
                pages[cur] = "\n".join(buf).strip()
            cur, buf = int(m.group(1)), []
        elif cur is not None:
            buf.append(ln)
    if cur is not None:
        pages[cur] = "\n".join(buf).strip()
    return pages or None


def _translit_quote_count(text: str) -> int:
    """How many italicized transliteration quotes the SOURCE carries (for reporting)."""
    return len(re.findall(r'\*"[^"]{8,}"\*', text) + re.findall(r"\*'[^']{8,}'\*", text))


def _arabic_run_count(text: str) -> int:
    return len(re.findall(r"[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]{2,}", text))


# Quran citation in the source/transliteration, e.g. "(Qur'an 2:255)", "Quran 7:56",
# "Sura 18:110", "Q 53:39", "(5:13)". Surah 1-114, ayah up to 286 (longest sura).
# Three forms, captured consistently:
#   - spelled prefix (Qur'an/Quran/Sura/Surah) accepts colon OR dot separator
#     (groups 1,2). Word-boundary anchored so it won't match mid-word.
#   - bare "Q" prefix requires a COLON separator (groups 3,4) — this excludes
#     financial-quarter notation like "Q1.20" / "Q3.2025" that the dot form would
#     otherwise misread as a verse and pollute the anchor-coverage metric.
#   - a WORDLESS reference in parentheses (groups 5,6), added 2026-08-01. Five of
#     `degrees-of-excellence`'s 23 citations are written this way, and because
#     none of them matched, the verses they name were never anchored into the
#     compose prompt and reached the page with no Arabic at all. Safe for the same
#     reason the `Q` form is: the enclosing parentheses AND a colon are both
#     required, so neither a fiscal quarter nor a bare ratio in running prose can
#     reach it.
_QURAN_CITE_RE = re.compile(
    r"\b(?:Qur(?:['’ʾ]?)?an|Qur['’]ān|S[uū]rah?|Sura)\.?\s*(\d{1,3})\s*[:.]\s*(\d{1,3})"
    r"|\bQ\.?\s*(\d{1,3})\s*:\s*(\d{1,3})"
    r"|\(\s*(\d{1,3})\s*:\s*(\d{1,3})\s*\)",
    re.IGNORECASE,
)


def _detect_quran_refs(text: str) -> list[tuple[int, int]]:
    """Distinct (surah, ayat) citations in order of first appearance, range-validated."""
    refs: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for m in _QURAN_CITE_RE.finditer(text or ""):
        s = int(m.group(1) or m.group(3) or m.group(5))
        a = int(m.group(2) or m.group(4) or m.group(6))
        if 1 <= s <= 114 and 1 <= a <= 286 and (s, a) not in seen:
            seen.add((s, a))
            refs.append((s, a))
    return refs


def _quran_anchor_block(text: str) -> tuple[str, dict]:
    """Build an authoritative CANONICAL QURAN block from mirror.db for every verse
    cited in the chapter, so the composer reproduces the exact mushaf text instead
    of reconstructing it from memory. Deterministic: a stored DB lookup keyed by
    surah:ayat (no LLM, no fuzzy match). Returns (block, stats). Empty block when
    nothing is cited or the mirror is unavailable — composition degrades to the
    prior best-attempt behavior, never worse."""
    refs = _detect_quran_refs(text)
    stats = {"cited": len(refs), "anchored": 0}
    if not refs:
        return "", stats
    try:
        from source_library_mirror import quran_ayat_lookup
    except Exception:
        return "", stats
    entries: list[str] = []
    for s, a in refs:
        try:
            row = quran_ayat_lookup(s, a)
        except Exception:
            row = None
        arabic = ((row or {}).get("arabic") or "").strip()
        if arabic:
            stats["anchored"] += 1
            entries.append(f"Qur'an {s}:{a} — reproduce this EXACT canonical text:\n{arabic}")
    if not entries:
        return "", stats
    block = (
        "\nCANONICAL QURAN — VERBATIM (authoritative; overrides memory)\n"
        "For each Quranic verse cited in this chapter, the EXACT canonical mushaf "
        "Arabic is given below, drawn from the verified Quran database. When you "
        "render one of these verses in Arabic script, you MUST reproduce its text "
        "below CHARACTER-FOR-CHARACTER — do not re-spell, re-vowel, paraphrase, or "
        "rely on memory. Place the English translation beneath as usual.\n\n" + "\n\n".join(entries) + "\n"
    )
    return block, stats


def _arabic_ground_truth_block(arabic_src: str) -> str:
    if not arabic_src:
        return ""
    return f"""
ARABIC SOURCE — GROUND TRUTH (the original pages this chapter is drawn from)
The original ARABIC of this chapter's source pages is reproduced below, from a machine OCR of the printed \
book — it may carry stray footnote digits, broken letters, or misplaced marks. When rendering quotations, \
poetry, sermons, and reported sayings in Arabic script, TRANSCRIBE them from this source rather than from \
memory — silently correct obvious OCR artifacts and add full vowelling. EXCEPTION: Quranic verses must \
still use the precise canonical mushaf text. If a passage you need is not present in this source, fall \
back to the rule above (best faithful attempt, no invented reference).

{arabic_src}
"""


def _compose_prompt(
    title: str, body: str, cfg: dict, voice_card: str, prev_tail: str, arabic_src: str = "", quran_anchor: str = ""
) -> str:
    """SUPERSEDED. The live compose route is ``_translation_prompts._compose_prompt``.

    Now reachable from NOTHING in the pipeline: the two callers that could reach it
    (``author_phase_book_compose`` and this module's ``main``) were deleted on
    2026-07-21 because running them clobbered a good compose. Kept only because one
    test exercises the Quran anchor block through it. Do not add a caller.

    Two hazards were removed from its text on 2026-07-20 rather than left sitting in a
    live-looking template: it instructed the model to supply full tashkīl and to
    "render your best faithful attempt" when unsure, which is the origin of the
    fabricated-vowelling problem the Arabic audit now exists to catch; and it
    hardcoded a first-person register, which contradicts the locked rule that
    narrative frame is a SOURCE property. Do not revive this route without making it
    frame-aware through ``_narrative``.
    """
    voice_key = cfg.get("narrator_voice", "author_first_person")
    narrator = cfg.get("narrator_subject", "the author")
    addressee = cfg.get("addressee", "the reader")
    voice_instr = _VOICE_INSTRUCTIONS.get(voice_key, _VOICE_INSTRUCTIONS["author_first_person"]).format(
        narrator_subject=narrator, addressee=addressee
    )
    craft = chapter_craft_block(cfg.get("content_profile"))
    anchor = (
        (
            f"\nVOICE ANCHOR (match this exact register and rhythm — it is your own voice "
            f"established earlier in the book):\n{voice_card}\n"
        )
        if voice_card
        else ""
    )
    cont = (
        (
            f'\nCONTINUITY: the previous chapter ended with —\n"…{prev_tail}"\nOpen THIS chapter so '
            f"it flows naturally onward. Do not repeat those lines or recap them.\n"
        )
        if prev_tail
        else ""
    )

    return f"""You are {narrator}, preparing a modern reading edition of your letter. Write ONE chapter, \
titled "{title}".

NARRATOR VOICE
{voice_instr}

FAITHFULNESS (absolute)
Preserve every teaching, argument, example, named person, and citation in the source below. \
Do NOT summarize, condense, omit, or shorten. The chapter must be approximately the SAME LENGTH as \
the source material — never shorter. You may modernize the connective prose, but every quotation's \
substance and reference must survive.

ARABIC QUOTATIONS (important — this is a printed book, not audio)
The source gives Arabic quotations (Quranic verses, hadith, reported sayings, poetry) in Latin-letter \
TRANSLITERATION. In your output you MUST replace each transliteration with the actual ARABIC SCRIPT, \
fully vowelled (tashkīl), and place the English translation on the line(s) directly below it. Render \
each quotation as a blockquote — Arabic first, English beneath — like this:

> أَعُوذُ بِاللَّهِ مِنْ عِلْمٍ لَا يَنْفَعُ
>
> "I seek refuge in God from knowledge that does not benefit."

Use the EXACT canonical Arabic: for Quranic verses, the precise mushaf text; for hadith and reported \
sayings, their well-attested Arabic wording; for Arabic poetry, the Arabic lines. Keep any source \
attribution or reference. Do NOT keep the Latin-letter transliteration. If you are not confident of the \
exact canonical Arabic for a quotation, LEAVE THE TRANSLITERATION AS IT STANDS and do not supply script \
or vowels from memory — an unconverted transliteration is a visible gap a human can fix, while invented \
vowelling reads as authoritative and is found only by auditing every run against the scan.
{quran_anchor}{_arabic_ground_truth_block(arabic_src)}
CHAPTER CRAFT
Write this as a single flowing book chapter under its title. Avoid sub-headings unless the material \
genuinely demands one. No meta-commentary; write the thing, not about it.
{craft}

REGISTER
Contemporary literary English. No archaic diction. Keep the grammatical person the source uses;
do not move a third-person report into first person.
{anchor}{cont}
OUTPUT
Return ONLY the chapter prose. Do NOT print the title line (it is added separately). No preamble, no \
code fences, no trailing commentary.

SOURCE MATERIAL (this chapter)
{body}"""


def _compose_one(
    title: str,
    body: str,
    cfg: dict,
    voice_card: str,
    prev_tail: str,
    book_dir: Path,
    label: str,
    log,
    arabic_src: str = "",
    quran_anchor: str = "",
) -> str:
    prompt = _compose_prompt(title, body, cfg, voice_card, prev_tail, arabic_src=arabic_src, quran_anchor=quran_anchor)
    rc, out, err = _run_claude_p(
        prompt,
        timeout=_COMPOSE_TIMEOUT,
        book_dir=book_dir,
        phase="0book-compose",
        step=label,
        **pure_text_call_options(),
    )
    out = (out or "").strip()
    if rc != 0:
        raise AuthoringError(
            phase="0book-compose",
            message=f"{label}: claude -p rc={rc}: {err[:300]}",
            manual_fallback="Re-run the phase to resume from the last completed chapter.",
        )
    sw = len(body.split())
    if sw >= 200 and len(out.split()) < 0.7 * sw:
        log(f"      {label}: short ({len(out.split())}/{sw}w) — retry (anti-abridge)")
        rc2, out2, _ = _run_claude_p(
            prompt + "\n\nYOUR PREVIOUS ATTEMPT WAS TOO SHORT — it summarized. Re-voice the FULL "
            "material; omit nothing; output about the same length as the source.",
            timeout=_RETRY_TIMEOUT,
            book_dir=book_dir,
            phase="0book-compose",
            step=f"{label}-retry",
            **pure_text_call_options(),
        )
        if rc2 == 0 and len(out2.split()) > len(out.split()):
            out = out2.strip()
    return out
