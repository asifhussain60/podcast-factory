from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from _translation_edition import (  # noqa: E402
    contract_findings,
    is_faithful_translation_deliverable,
    is_translation_edition,
    monochrome_svg,
    normalize_translation_prose,
    requires_monochrome_visuals,
    source_title_drift_findings,
    translation_output_findings,
    _iter_source_windows,
    _para_is_echo,
    _trim_seam_overlap,
    dedupe_seam_paragraphs,
)
from phases.book_driver import _book_branch_enabled  # noqa: E402


def _book(tmp_path: Path, config: str) -> Path:
    bd = tmp_path / "book"
    (bd / "_system").mkdir(parents=True)
    (bd / "_system" / "series-config.yaml").write_text(config, encoding="utf-8")
    return bd


def test_translation_edition_contract_passes(tmp_path: Path) -> None:
    bd = _book(
        tmp_path,
        """
content_profile: islamic_scholarly
deliverable_mode: translation_edition
visual_style: black_white
translation_policy:
  augmentation: forbidden
  denoise: teaching_only
  preserve_arabic_terms: true
""",
    )

    assert is_translation_edition(bd)
    assert requires_monochrome_visuals(bd)
    assert contract_findings(bd) == []


def test_translation_edition_contract_rejects_augmentation(tmp_path: Path) -> None:
    bd = _book(
        tmp_path,
        """
deliverable_mode: translation_edition
visual_style: black_white
translation_policy:
  augmentation: outside_sources
""",
    )

    findings = contract_findings(bd)
    assert any("augmentation" in finding for finding in findings)


def test_faithful_deliverable_covers_v2_faithful_and_legacy(tmp_path: Path) -> None:
    # Legacy translation-edition mode -> faithful deliverable.
    legacy = _book(tmp_path / "legacy", "deliverable_mode: translation_edition\n")
    assert is_faithful_translation_deliverable(legacy)

    # v2 route, faithful voice -> faithful deliverable (the gap this closes).
    v2f = _book(tmp_path / "v2f", "book_pipeline_v2: true\nbook_voice: faithful\nbook_augmentation: none\n")
    assert is_faithful_translation_deliverable(v2f)
    assert not is_translation_edition(v2f)  # NOT legacy — routing predicate stays false

    # v2 route, author-companion voice -> NOT a faithful translation deliverable.
    v2c = _book(tmp_path / "v2c", "book_pipeline_v2: true\nbook_voice: author_companion\nbook_augmentation: source_only\n")
    assert not is_faithful_translation_deliverable(v2c)

    # Neither -> false.
    plain = _book(tmp_path / "plain", "content_profile: islamic_scholarly\n")
    assert not is_faithful_translation_deliverable(plain)


def test_translation_edition_enables_book_branch_without_meta_flag(tmp_path: Path) -> None:
    bd = _book(
        tmp_path,
        """
deliverable_mode: translation_edition
visual_style: black_white
translation_policy:
  augmentation: forbidden
""",
    )

    assert _book_branch_enabled(bd)


def test_monochrome_svg_rewrites_theme_colours() -> None:
    svg = '<svg><rect fill="#8b4513" stroke="#d2b48c"/><text fill="#1f1d18">x</text></svg>'

    mono = monochrome_svg(svg)

    assert "#8b4513" not in mono
    assert "#d2b48c" not in mono
    assert 'fill="#000000"' in mono
    assert 'stroke="#d9d9d9"' in mono


def test_source_windows_preserve_line_ranges() -> None:
    lines = []
    for page in range(1, 5):
        lines.append(f"<!-- page {page} -->")
        lines.append(("word " * 20).strip())
        lines.append("")

    windows = _iter_source_windows(lines, [[1, len(lines)]], target_words=35)

    assert len(windows) >= 2
    assert windows[0][1][0][0] == 1
    assert windows[-1][1][-1][-1] == len(lines)


def test_translation_output_findings_rejects_model_commentary() -> None:
    prose = (
        "Since you didn't pick an option, I cannot produce \"Dress\" prose "
        "from a source passage about hunting. Here is the faithful chapter."
    )

    findings = translation_output_findings(prose, expected_title="Dress")

    assert findings
    assert any("option" in f or "refuses" in f for f in findings)


def test_translation_output_findings_rejects_model_owned_headings() -> None:
    prose = "# What We Hunt and What We Slaughter\n\nThe source teaches..."

    findings = translation_output_findings(prose, expected_title="What We Wear")

    assert any("opening heading" in f for f in findings)


def test_normalize_translation_prose_compacts_long_salutations() -> None:
    prose = (
        "The Messenger of Allah, may Allah's peace and blessings be upon him and his family, said this. "
        "The Imams, may Allah's prayers be upon them all, preserved it. "
        "Ali, may Allah be pleased with him, narrated it."
    )

    normalized = normalize_translation_prose(prose)

    assert "(ع)" in normalized
    assert "(عليهم السلام)" in normalized
    assert "(رض)" in normalized
    assert "peace and blessings" not in normalized.lower()


def test_source_title_drift_detects_dress_title_on_hunting_source() -> None:
    findings = source_title_drift_findings(
        "What We Wear: Dress, Adornment, and Fragrance",
        "A discussion of hunting, game, slaughter, sacrifice, prey, and the knife.",
    )

    assert findings


# --- seam-overlap trimming (chunk-seam double-render root fix) ---------------

def test_trim_seam_drops_verbatim_boundary_echo() -> None:
    # The composer double-renders the parting passage across a chunk seam.
    prev = (
        "So the scholar and the boy went out together and drew near to the boy's "
        "city, and the scholar said: My son, you have learned the counsel of the "
        "Shaykh, and there is no right guidance but in his word."
    )
    nxt = (
        "So the scholar and the boy went out together and drew near to the boy's "
        "city, and the scholar said: My son, you have learned the counsel of the "
        "Shaykh, and there is no right guidance but in his word.\n\n"
        "Then a new road opened before them, and they spoke of the five shares."
    )

    trimmed = _trim_seam_overlap(prev, nxt)

    assert trimmed.startswith("Then a new road opened")
    assert "you have learned the counsel" not in trimmed


def test_trim_seam_keeps_distinct_chapter_opening() -> None:
    # A genuinely new chapter opening must never be trimmed as an echo.
    prev = "The chapter closes on the marketplace and the ethics of honest trade."
    nxt = (
        "A wholly different discussion now opens on divorce, the waiting period, "
        "and the rites of mourning.\n\nThe teaching continues from there."
    )

    assert _trim_seam_overlap(prev, nxt) == nxt


def test_trim_seam_drops_long_verbatim_run_in_reworded_echo() -> None:
    # A long verbatim run (>=12 tokens) inside an otherwise-reworded opening is
    # still a seam echo and is trimmed.
    prev = (
        "And then the scholar said the counsel of the shaykh is the only right "
        "guidance for the seeker on the road."
    )
    nxt = (
        "Truly, the counsel of the shaykh is the only right guidance for the "
        "seeker on the road, he said to them again.\n\n"
        "After this the debate turned to the foundations of justice."
    )

    trimmed = _trim_seam_overlap(prev, nxt)

    assert trimmed.startswith("After this the debate")


def test_trim_seam_keeps_short_reworded_overlap_by_design() -> None:
    # The trimmer is deliberately conservative: a short (<12-token) reworded
    # overlap is NOT trimmed — sequential window continuity prevents these, and
    # trimming so aggressively would risk removing legitimately similar prose.
    prev = "He said that lying is the worst of wares in the market of the soul."
    nxt = (
        "Indeed lying is the worst of wares, he repeated to them plainly.\n\n"
        "After this the debate turned to the foundations of justice."
    )

    assert _trim_seam_overlap(prev, nxt) == nxt


def test_para_is_echo_ignores_short_fragments() -> None:
    assert _para_is_echo("He said.", "He said that lying is the worst of wares.") is False


def test_trim_seam_noops_on_empty_inputs() -> None:
    assert _trim_seam_overlap("", "Opening paragraph.") == "Opening paragraph."
    assert _trim_seam_overlap("Prior tail.", "") == ""


# --- preface emission (P0: planned preface silently dropped at assembly) -----

def test_preface_is_composed_and_emitted_before_chapter_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import _translation_edition as te

    # Stub the LLM compose to echo the source faithfully (deterministic).
    monkeypatch.setattr(
        te,
        "_compose_one",
        lambda title, body, previous_tail, book_dir, label, log, **kw: body.strip(),
    )

    bd = tmp_path / "the-book"
    (bd / "book").mkdir(parents=True)
    (bd / "_system" / "source" / "text").mkdir(parents=True)

    refined = "\n".join([
        "The opening teaching that frames the whole work as thanksgiving.",  # 1
        "Thank the master by obeying him and the knowledge by acting on it.",  # 2
        "",                                                                   # 3
        "The traveller who was lost and then guided came to the city.",       # 4
        "He learned the counsel of the guide and carried it home.",           # 5
    ])
    (bd / "_system" / "source" / "text" / "refined-english.md").write_text(
        refined, encoding="utf-8"
    )

    toc = {
        "book_title": "The Book of the Road",
        "voice": "faithful",
        "preface": {
            "include": True,
            "title": "How to Read a Conversation Made of Doors",
            "source_line_ranges": [[1, 2]],
        },
        "chapters": [
            {"bk_index": 1, "title": "The Traveller Guided", "source_line_ranges": [[4, 5]]},
        ],
    }
    (bd / "book" / "book-toc.json").write_text(
        json.dumps(toc), encoding="utf-8"
    )

    book_md = te.author_translation_edition_compose(bd, log=lambda *a, **k: None, enforce_contract=False)
    text = book_md.read_text(encoding="utf-8")

    preface_at = text.find("## How to Read a Conversation Made of Doors")
    chapter_at = text.find("## 1. The Traveller Guided")
    assert preface_at != -1, "preface heading missing from book.md"
    assert chapter_at != -1, "chapter heading missing from book.md"
    assert preface_at < chapter_at, "preface must render before chapter one"
    assert "thanksgiving" in text  # the preface teaching survived into the deliverable
    assert (bd / "book" / "_chunks" / "translation" / "preface.md").exists()


def test_dedupe_drops_reworded_within_chapter_twin() -> None:
    # A back-to-back reworded twin (survives the verbatim trimmer) inside a chapter.
    text = (
        "# Book\n\n"
        "## 8. Homecoming\n\n"
        'They said, "But we have been taught that whoever stands in this position, one who '
        'neither verifies the truth nor refutes falsehood, is ignorant in his conduct, for he '
        'does not know the truth that he might follow it nor falsehood that he might avoid it."\n\n'
        'They said, "But we have been taught that whoever stands in this position, one who '
        'neither verifies the truth so as to follow it nor refutes falsehood so as to avoid it, '
        'is ignorant in his conduct."\n\n'
        'Abu Malik said, "What you have related, you have believed."\n'
    )

    out = dedupe_seam_paragraphs(text)

    assert out.count("we have been taught that whoever stands in this position") == 1
    assert "What you have related, you have believed" in out


def test_dedupe_drops_chapter_boundary_echo() -> None:
    # A chapter that opens by re-rendering the previous chapter's closing passage.
    text = (
        "# Book\n\n"
        "## 2. A Stranger\n\n"
        "Then his eyes brimmed over with tears, and he broke off his words and took his leave of "
        "the people weeping, and the people wept too and longed to rise and go with him, but good "
        "manners held them back and so they returned to their homes.\n\n"
        "## 3. The Boy at the Door\n\n"
        "His eyes overflowed with tears, and at that he broke off his speech and took his leave of "
        "the people, and the people wept and longed to follow him, yet out of courtesy they held "
        "back and turned back to their houses.\n\n"
        "The youth kept the Master's company until the end of the journey.\n"
    )

    out = dedupe_seam_paragraphs(text)

    assert "eyes overflowed with tears" not in out       # the ch3 echo is dropped
    assert "eyes brimmed over with tears" in out         # ch2's rendering survives
    assert "The youth kept the Master" in out            # real ch3 content survives
    assert out.count("## 3. The Boy at the Door") == 1   # heading preserved


def test_dedupe_keeps_legitimate_dialogue_and_openings() -> None:
    # Distinct Q&A turns share structure but are not echoes — must be untouched.
    text = (
        "# Book\n\n"
        "## 1. The Persian\n\n"
        'The boy said: "What is the likeness of the twelve islands in the sea of knowledge?"\n\n'
        'The scholar said: "They are the likenesses of the twelve arguments set for the seeker."\n\n'
        "## 2. A Stranger\n\n"
        "A wholly new discussion opens now upon the making of the world and its first cause.\n"
    )

    assert dedupe_seam_paragraphs(text) == text.strip() + "\n"


def test_preface_skipped_when_not_included(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import _translation_edition as te

    monkeypatch.setattr(
        te,
        "_compose_one",
        lambda title, body, previous_tail, book_dir, label, log, **kw: body.strip(),
    )

    bd = tmp_path / "the-book"
    (bd / "book").mkdir(parents=True)
    (bd / "_system" / "source" / "text").mkdir(parents=True)
    (bd / "_system" / "source" / "text" / "refined-english.md").write_text(
        "The traveller who was lost and then guided came to the city.\nHe learned and returned.",
        encoding="utf-8",
    )
    toc = {
        "book_title": "The Book",
        "preface": {"include": False, "title": "Skip Me", "source_line_ranges": [[1, 1]]},
        "chapters": [
            {"bk_index": 1, "title": "The Traveller Guided", "source_line_ranges": [[1, 2]]},
        ],
    }
    (bd / "book" / "book-toc.json").write_text(json.dumps(toc), encoding="utf-8")

    text = te.author_translation_edition_compose(
        bd, log=lambda *a, **k: None, enforce_contract=False
    ).read_text(encoding="utf-8")

    assert "Skip Me" not in text
