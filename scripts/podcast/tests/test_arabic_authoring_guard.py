"""Chapter authoring may not invent Arabic.

R-ARABIC-INTEGRITY: the only sanctioned way Arabic script enters a chapter is (1) it was in the
SOURCE, or (2) canonical injection from the mushaf/verified atoms/curated glossary. Phase 0d's
per-chapter prompt told the model to *preserve* script the source supplies but never forbade writing
it from memory, so on isaf-al-talib the model added Qur'anic phrases as `⟪ar:…⟫` (ch20: three spans).
Finalize gate G14 caught them and a person removed them by hand (b593cf34). Every translation edition
would hit this. Two layers now: the prompt forbids it, and this deterministic backstop removes anything
unsanctioned right after the model writes — recorded, never silent.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _arabic_authoring_guard as guard  # noqa: E402
import arabic_integrity as ai  # noqa: E402

VERSE = "وَمِمَّا رَزَقْنَاهُمْ يُنفِقُونَ"  # 2:3 — genuine Qur'an, but written by the model, not the source
TERM = "مواد"


def _h(s: str) -> str:
    return ai._hash(ai.normalize_arabic_span(s))


def test_the_ch20_case_arabic_is_removed_and_the_english_quotation_survives():
    text = f'He is one of those Allah described in the verse: ⟪ar:{VERSE}⟫, "and who spend out of what We provided."'
    out, removed = guard.scrub_chapter_text(text, sanctioned=set())
    assert out == 'He is one of those Allah described in the verse: "and who spend out of what We provided."'
    assert removed == [VERSE]


def test_a_span_the_source_supplied_is_kept_untouched():
    text = f"the verse ⟪ar:{VERSE}⟫ is recited"
    out, removed = guard.scrub_chapter_text(text, sanctioned={_h(VERSE)})
    assert out == text and removed == []


def test_an_empty_parenthetical_left_behind_is_tidied():
    out, removed = guard.scrub_chapter_text(f"the substance (⟪ar:{TERM}⟫) of it", sanctioned=set())
    assert out == "the substance of it" and removed == [TERM]


def test_bare_unmarked_invented_arabic_is_removed_too():
    out, removed = guard.scrub_chapter_text(f"He said {VERSE} and left.", sanctioned=set())
    assert VERSE not in out and removed == [VERSE]
    assert "  " not in out


def test_text_with_no_arabic_is_byte_identical_including_markdown_hard_breaks():
    text = "Line one with a hard break  \nLine two ()\n\n> a quote\n"
    out, removed = guard.scrub_chapter_text(text, sanctioned=set())
    assert out == text and removed == []


def test_a_marker_at_the_start_of_a_line_leaves_no_stray_space():
    out, _ = guard.scrub_chapter_text(f"⟪ar:{TERM}⟫ means the thing.", sanctioned=set())
    assert out == "means the thing."


def test_only_the_unsanctioned_span_goes_when_two_share_a_paragraph():
    text = f"first ⟪ar:{VERSE}⟫ and second ⟪ar:{TERM}⟫ here"
    out, removed = guard.scrub_chapter_text(text, sanctioned={_h(VERSE)})
    assert VERSE in out and TERM not in out and removed == [TERM]


def _book(tmp_path: Path) -> Path:
    d = tmp_path / "book"
    (d / "_system").mkdir(parents=True)
    (d / "chapters").mkdir()
    return d


def test_the_file_pass_rewrites_only_changed_chapters_and_records_what_it_removed(tmp_path, monkeypatch):
    monkeypatch.setattr(ai, "build_allowlist", lambda _d: {"added": set(), "dropped": set()})
    d = _book(tmp_path)
    bad = d / "chapters" / "ch20-zakat.txt"
    ok = d / "chapters" / "ch21-fasting.txt"
    bad.write_text(f'verse: ⟪ar:{VERSE}⟫, "and who spend."\n', encoding="utf-8")
    ok.write_text("plain English only\n", encoding="utf-8")
    before = ok.stat().st_mtime_ns

    total = guard.scrub_authored_chapters(d, [bad, ok], source_text="no arabic in the source", log=lambda *_: None)

    assert total == 1
    assert VERSE not in bad.read_text(encoding="utf-8")
    assert ok.stat().st_mtime_ns == before, "an unchanged chapter must not be rewritten"
    report = json.loads((d / "_system" / "arabic-authoring-scrub.json").read_text(encoding="utf-8"))
    assert report["chapters"]["ch20-zakat.txt"] == [VERSE]
    assert "ch21-fasting.txt" not in report["chapters"]


def test_the_file_pass_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(ai, "build_allowlist", lambda _d: {"added": set(), "dropped": set()})
    d = _book(tmp_path)
    f = d / "chapters" / "ch1-a.txt"
    f.write_text(f"x ⟪ar:{TERM}⟫ y\n", encoding="utf-8")
    guard.scrub_authored_chapters(d, [f], source_text="", log=lambda *_: None)
    assert guard.scrub_authored_chapters(d, [f], source_text="", log=lambda *_: None) == 0


def test_glossary_and_atom_arabic_counts_as_sanctioned(tmp_path, monkeypatch):
    monkeypatch.setattr(ai, "build_allowlist", lambda _d: {"added": {_h(TERM)}, "dropped": set()})
    d = _book(tmp_path)
    f = d / "chapters" / "ch1-a.txt"
    f.write_text(f"x ⟪ar:{TERM}⟫ y\n", encoding="utf-8")
    assert guard.scrub_authored_chapters(d, [f], source_text="", log=lambda *_: None) == 0
    assert TERM in f.read_text(encoding="utf-8")


CHAPTER_DESIGN = Path(__file__).resolve().parents[1] / "_authoring" / "_chapter_design.py"


def test_the_authoring_prompt_forbids_writing_arabic_from_memory():
    text = CHAPTER_DESIGN.read_text(encoding="utf-8")
    assert "R-ARABIC-INTEGRITY (never invent Arabic)" in text
    assert "from memory" in text and "Anything you add is removed and recorded" in text


def test_the_scrub_runs_on_every_authored_chapter_before_the_density_gate():
    text = CHAPTER_DESIGN.read_text(encoding="utf-8")
    assert "scrub_authored_chapters(" in text
    assert text.index("scrub_authored_chapters(") < text.index("R-MAX-CONCEPTS post-write gate")
