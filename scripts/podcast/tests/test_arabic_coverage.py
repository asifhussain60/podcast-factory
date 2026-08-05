#: Modules that still spell the Arabic range out instead of importing it.
#: A RATCHET, not a clean sheet — the same idiom the bare-term guard uses. The
#: defect fixed on 2026-08-03 was DISAGREEMENT, not duplication: `_gloss_terms`
#: and `_narrative` omitted Arabic Extended-A, so one character was Arabic to the
#: vowelling gate and not Arabic to the bare-term report, while `build_glossary`
#: and `fill_glossary_cross_book` used the base block alone. Those eight now
#: import `_arabic_coverage.ARABIC_BODY`. The rest are honest debt: shrink this
#: list when a module is touched for another reason, never grow it.
_RESPELL_THE_RANGE = frozenset(
    {
        "_annotation_policy.py",
        "_arabic_paragraphs.py",
        "_book_companion.py",
        "_book_compose.py",
        "_book_edits.py",
        "_book_frontmatter.py",
        "_book_inline_arabic.py",
        "_book_opening.py",
        "_book_quran_extent.py",
        "_buckwalter.py",
        "_etymology.py",
        "_self_study.py",
        "_vowelling.py",
        "correct_ocr.py",
        "knowledge/pronunciation_ledger.py",
        "restore_arabic.py",
        "split_synthesis_al_anwaar.py",
        "supplication/llm.py",
        "transcribe_audio_book.py",
        "validate_book_ready.py",
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
    literal = re.compile(r"[\u0600-\u06ff]\s*-\s*[\u0600-\u06ff]")
    found = {
        str(path.relative_to(root))
        for path in sorted(root.rglob("*.py"))
        if path.name not in ("_arabic_coverage.py", "_mushaf.py")
        and "/tests/" not in str(path)
        and literal.search(path.read_text(encoding="utf-8"))
    }
    assert not (found - _RESPELL_THE_RANGE), (
        f"new module(s) respelling the Arabic range: {sorted(found - _RESPELL_THE_RANGE)}"
    )
    assert not (_RESPELL_THE_RANGE - found), (
        f"cured — remove from the ratchet list: {sorted(_RESPELL_THE_RANGE - found)}"
    )
