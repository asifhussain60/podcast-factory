#: The Arabic-script blocks `_arabic_coverage.ARABIC_BODY` is assembled from.
#: An escaped range counts as respelling the Arabic range only when BOTH of its
#: endpoints land in one of these — `A-Z` is Latin and none of this
#: test's business, while `؀-ۿ` is the base block spelled the long way.
_ARABIC_BLOCKS = (
    (0x0600, 0x06FF),  # Arabic
    (0x0750, 0x077F),  # Arabic Supplement
    (0x08A0, 0x08FF),  # Arabic Extended-A
    (0xFB50, 0xFDFF),  # Presentation Forms-A
    (0xFE70, 0xFEFF),  # Presentation Forms-B
)


def _in_arabic_block(codepoint: int) -> bool:
    return any(low <= codepoint <= high for low, high in _ARABIC_BLOCKS)


#: Modules that still spell the Arabic range out instead of importing it.
#: A RATCHET, not a clean sheet — the same idiom the bare-term guard uses. The
#: defect fixed on 2026-08-03 was DISAGREEMENT, not duplication: `_gloss_terms`
#: and `_narrative` omitted Arabic Extended-A, so one character was Arabic to the
#: vowelling gate and not Arabic to the bare-term report, while `build_glossary`
#: and `fill_glossary_cross_book` used the base block alone. Those eight now
#: import `_arabic_coverage.ARABIC_BODY`. The rest are honest debt: shrink this
#: list when a module is touched for another reason, never grow it.
#:
#: The ten entries marked ESC were invisible until 2026-08-15 — they spell their
#: range in `\uXXXX` escapes, which the detector did not read. Five of them (marked
#: FULL) re-declare the ENTIRE shared definition and are the cheapest to cure: they
#: already agree with it in value, so importing `ARABIC_BODY` changes no behaviour
#: at all. The rest are narrower classes — letters, digits, vowel marks — that
#: happen to be written as Arabic ranges; curing those means naming the concept,
#: not just swapping the constant.
_RESPELL_THE_RANGE = frozenset(
    {
        "_annotation_policy.py",
        "_arabic_paragraphs.py",
        "_book_companion.py",
        "_book_compose.py",
        "_book_defects.py",  # ESC
        "_book_edits.py",
        "_book_frontmatter.py",
        "_book_inline_arabic.py",
        "_book_mirror.py",  # ESC
        "_book_opening.py",
        "_book_quran_extent.py",
        "_buckwalter.py",
        "_etymology.py",
        "_self_study.py",
        "_sessions_prose_format.py",  # ESC
        "_translit_skeleton.py",  # ESC
        "_vowelling.py",
        "compose_paste_fix.py",  # ESC, FULL
        "correct_ocr.py",
        "inject_chapter_arabic.py",  # ESC, FULL
        "intelligence/augmenter.py",  # ESC, FULL
        "knowledge/pronunciation_ledger.py",
        "phases/noise_router.py",  # ESC, FULL
        "reader_narration.py",  # ESC, FULL
        "restore_arabic.py",
        "split_synthesis_al_anwaar.py",
        "supplication/llm.py",
        "transcribe_audio_book.py",
        "validate_book_ready.py",
        "vowel_book.py",  # ESC — its letter/digit classes; the token class is cured
    }
)


def test_no_new_module_respells_the_arabic_range() -> None:
    """One definition of what "Arabic" means, or the checks disagree about it.

    `_gloss_terms` and `_narrative` omitted Arabic Extended-A and
    `build_glossary` used the base block alone, so the same character counted as
    Arabic in one gate and not another. Import `_arabic_coverage.ARABIC_BODY`
    (to interpolate) or `ARABIC_RE` (to match one character) — that module pulls
    in nothing but `re`, so it is free to import from anywhere.
    """
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    # No whitespace around the dash: a character-class range is written tight
    # (`[\u0600-\u06ff]`), while Arabic PROSE that happens to contain a hyphen is spaced
    # (a Persian binder title, `\u063a\u0632\u0627\u0644\u06cc - \u06a9\u06cc\u0645\u06cc\u0627\u0626\u06cc \u0627\u0644\u0633\u0639\u0627\u062f\u06c3`). Allowing `\s*` here
    # read that title as a range literal and held this ratchet red from
    # 2026-08-14, which masks the violations it exists to catch.
    literal = re.compile(r"[\u0600-\u06ff]-[\u0600-\u06ff]")
    # The SAME range written `\u0600-\u06ff` is the same duplication, and until
    # 2026-08-15 this test could not see it at all: eleven modules spell one that
    # way, five of them re-declaring the whole shared definition, and TWO of those
    # landed on 12 and 13 August \u2014 after this ratchet went in on the 3rd, without
    # tripping it. A guard that watches one of the two ways a thing is written
    # reports "no new violations" while they accumulate beside it.
    escaped = re.compile(r"\\u([0-9a-fA-F]{4})-\\u([0-9a-fA-F]{4})")

    def _respells(text: str) -> bool:
        if literal.search(text):
            return True
        return any(
            _in_arabic_block(int(m.group(1), 16)) and _in_arabic_block(int(m.group(2), 16))
            for m in escaped.finditer(text)
        )

    found = {
        str(path.relative_to(root))
        for path in sorted(root.rglob("*.py"))
        if path.name not in ("_arabic_coverage.py", "_mushaf.py")
        and "/tests/" not in str(path)
        and _respells(path.read_text(encoding="utf-8"))
    }
    assert not (found - _RESPELL_THE_RANGE), (
        f"new module(s) respelling the Arabic range: {sorted(found - _RESPELL_THE_RANGE)}"
    )
    assert not (_RESPELL_THE_RANGE - found), (
        f"cured — remove from the ratchet list: {sorted(_RESPELL_THE_RANGE - found)}"
    )
