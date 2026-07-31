from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from _arabic_coverage import (
    _ARABIC_COVERAGE_MIN_QUOTES,
    arabic_coverage_hint,
    arabic_coverage_shortfall,
    arabic_ground_truth_block,
    arabic_quote_count,
    arabic_quote_spans,
    arabic_run_spans,
)
from _translation_edition import (
    _iter_source_windows,
    _para_is_echo,
    _trim_seam_overlap,
    contract_findings,
    dedupe_seam_paragraphs,
    duplicate_passage_findings,
    is_faithful_translation_deliverable,
    is_translation_edition,
    monochrome_svg,
    normalize_translation_prose,
    requires_monochrome_visuals,
    source_title_drift_findings,
    translation_output_findings,
)
from phases.book_driver import _book_branch_enabled


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
    v2c = _book(
        tmp_path / "v2c", "book_pipeline_v2: true\nbook_voice: author_companion\nbook_augmentation: source_only\n"
    )
    assert not is_faithful_translation_deliverable(v2c)

    # An Islamic book that declares NOTHING is a faithful deliverable (2026-07-31):
    # the knob default puts it on the faithful voice, and this predicate follows the
    # resolved voice rather than the config text — which is the point of it. So the
    # translation-route ship gates (B3's translation branch, B4/B5/B6) now apply to
    # it, matching the artifact the faithful route actually produces.
    islamic_default = _book(tmp_path / "islamic", "content_profile: islamic_scholarly\n")
    assert is_faithful_translation_deliverable(islamic_default)

    # Neither -> false. A non-Islamic book with nothing declared still defaults to
    # the author-companion voice, so it is not a faithful translation deliverable.
    plain = _book(tmp_path / "plain", "content_profile: fiction\n")
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
        'Since you didn\'t pick an option, I cannot produce "Dress" prose '
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
    prev = "And then the scholar said the counsel of the shaykh is the only right guidance for the seeker on the road."
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


def test_preface_is_composed_and_emitted_before_chapter_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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

    refined = "\n".join(
        [
            "The opening teaching that frames the whole work as thanksgiving.",  # 1
            "Thank the master by obeying him and the knowledge by acting on it.",  # 2
            "",  # 3
            "The traveller who was lost and then guided came to the city.",  # 4
            "He learned the counsel of the guide and carried it home.",  # 5
        ]
    )
    (bd / "_system" / "source" / "text" / "refined-english.md").write_text(refined, encoding="utf-8")

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
    (bd / "book" / "book-toc.json").write_text(json.dumps(toc), encoding="utf-8")

    book_md = te.author_translation_edition_compose(bd, log=lambda *a, **k: None, enforce_contract=False)
    text = book_md.read_text(encoding="utf-8")

    preface_at = text.find("## How to Read a Conversation Made of Doors")
    chapter_at = text.find("## 1. The Traveller Guided")
    assert preface_at != -1, "preface heading missing from book.md"
    assert chapter_at != -1, "chapter heading missing from book.md"
    assert preface_at < chapter_at, "preface must render before chapter one"
    assert "thanksgiving" in text  # the preface teaching survived into the deliverable
    assert (bd / "book" / "_chunks" / "translation" / "preface.md").exists()


def test_per_chapter_sidecars_never_land_in_the_podcast_lanes_shared_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: this compose route used to write ch<NN>-<slug>.txt straight into
    the top-level chapters/ dir — the SAME namespace the podcast lane uses for one
    file per episode. publish_to_library's ship gate globs chapters/ch*.txt and
    expects every match to pair with an episode; a book-lane sidecar sharing that
    glob shape reads as "a chapter with no episode" and blocks publish. Found live
    on the-master-and-the-disciple 2026-07-19. The sidecar must live under book/,
    alongside book/_chunks and book/_diagrams — never in the shared chapters/ dir,
    even when a real podcast episode already occupies that folder."""
    import _translation_edition as te

    monkeypatch.setattr(
        te,
        "_compose_one",
        lambda title, body, previous_tail, book_dir, label, log, **kw: body.strip(),
    )

    bd = tmp_path / "the-book"
    (bd / "book").mkdir(parents=True)
    (bd / "_system" / "source" / "text").mkdir(parents=True)
    # A real podcast-lane episode chapter already sitting in the shared folder —
    # the fixture that would have collided with the old write path.
    (bd / "chapters").mkdir(parents=True)
    (bd / "chapters" / "ch01a-three-thanks-and-the-persian-awakening.txt").write_text("EP01 source", "utf-8")

    refined = "The traveller who was lost and then guided came to the city."
    (bd / "_system" / "source" / "text" / "refined-english.md").write_text(refined, encoding="utf-8")

    toc = {
        "book_title": "The Book of the Road",
        "voice": "faithful",
        "chapters": [{"bk_index": 1, "title": "The Traveller Guided", "source_line_ranges": [[1, 1]]}],
    }
    (bd / "book" / "book-toc.json").write_text(json.dumps(toc), encoding="utf-8")

    te.author_translation_edition_compose(bd, log=lambda *a, **k: None, enforce_contract=False)

    assert (bd / "book" / "_chapters" / "ch01-the-traveller-guided.txt").exists()
    assert not (bd / "chapters" / "ch01-the-traveller-guided.txt").exists()
    # The pre-existing real episode file is untouched — this book-lane sidecar
    # never even visits the shared folder.
    assert sorted(p.name for p in (bd / "chapters").iterdir()) == ["ch01a-three-thanks-and-the-persian-awakening.txt"]


def test_dedupe_drops_reworded_within_chapter_twin() -> None:
    # A back-to-back reworded twin (survives the verbatim trimmer) inside a chapter.
    text = (
        "# Book\n\n"
        "## 8. Homecoming\n\n"
        'They said, "But we have been taught that whoever stands in this position, one who '
        "neither verifies the truth nor refutes falsehood, is ignorant in his conduct, for he "
        'does not know the truth that he might follow it nor falsehood that he might avoid it."\n\n'
        'They said, "But we have been taught that whoever stands in this position, one who '
        "neither verifies the truth so as to follow it nor refutes falsehood so as to avoid it, "
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

    assert "eyes overflowed with tears" not in out  # the ch3 echo is dropped
    assert "eyes brimmed over with tears" in out  # ch2's rendering survives
    assert "The youth kept the Master" in out  # real ch3 content survives
    assert out.count("## 3. The Boy at the Door") == 1  # heading preserved


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


def test_dedupe_reports_every_paragraph_it_deletes() -> None:
    """It removes source-bearing prose, so it must say what it removed.

    Until 2026-07-21 it deleted silently — no log, no count, no report — so a false
    positive at the ratio floor (a liturgical refrain, a question restated before
    its answer) simply left the book and nothing recorded it had been there.
    """
    text = (
        "# Book\n\n"
        "## 1. The Persian\n\n"
        'They said, "But we have been taught that whoever stands in this position, one who '
        "neither verifies the truth nor refutes falsehood, is ignorant in his conduct, for he "
        'does not know the truth that he might follow it nor falsehood that he might avoid it."\n\n'
        'They said, "But we have been taught that whoever stands in this position, one who '
        "neither verifies the truth so as to follow it nor refutes falsehood so as to avoid it, "
        'is ignorant in his conduct."\n'
    )
    removed: list[dict] = []

    dedupe_seam_paragraphs(text, removed=removed)

    assert len(removed) == 1
    record = removed[0]
    assert record["rule"] == "adjacent-echo"
    assert record["chapter"] == "1. The Persian"
    # The full text is kept, which is what makes an accidental deletion
    # recoverable without a git archaeology session.
    assert "is ignorant in his conduct." in record["removed_text"]
    assert record["words"] > 20


def test_dedupe_reports_nothing_when_it_deletes_nothing() -> None:
    text = "# Book\n\n## 1. The Persian\n\nA first paragraph.\n\nA wholly different second one here.\n"
    removed: list[dict] = []
    dedupe_seam_paragraphs(text, removed=removed)
    assert removed == []


def test_duplicate_passage_findings_reports_a_re_narrated_block() -> None:
    # A window that ran past its own passage: the farewell, the journey, and the
    # counsel are narrated once, then narrated again in different words three
    # paragraphs later. Neither copy is adjacent to its twin, so the seam de-dup
    # rules cannot see it. Modelled on the-master-and-the-disciple ch7.
    text = (
        "# Book\n\n"
        "## 7. The Long Road\n\n"
        "Then the two rose, clasped hands, and embraced, each bidding the other farewell, unable "
        "to hold back his tears and unable to speak except by a sign. Then they parted, and the "
        "Master and the boy set out and travelled on together until they drew near to the boy's "
        "own city, the city in which his father was living all this while.\n\n"
        'The Master said to the boy: "My son, you have heard the charge of the Shaykh, and there '
        "is no right guidance to be found anywhere except in his words. This is your city, and we "
        "have now reached its edge. Sit with me here, apart from the road, for I wish to remind "
        'you of something of my own affair and to counsel you in what you should act upon."\n\n'
        "When they had sat down, the Master said: \"My son, you know your father's state and his "
        "enmity toward the people of this way, and now your going out with me and your absence "
        "from him, without his leave, have come one upon another to weigh upon him and to trouble "
        'his heart against us."\n\n'
        "Then they stood, clasped hands, and embraced, and each gave his friend farewell, unable "
        "to master himself against the weight of the parting, able to speak only by a gesture of "
        "the hand. Then they went their separate ways, and the Master and the boy travelled on "
        "until they came near to the city where the boy's father was living.\n\n"
        'So the Master said to him: "My son, I have grasped the counsel of the Shaykh, and you '
        "have not yet grasped it. There is no right guidance except in his words. This is your "
        "city, and we have reached its edge. Sit with me here, off the road, for I wish to remind "
        'you of certain of my concerns, and to charge you with what you should do."\n\n'
        'When they had sat down, the Master said: "My son, I know your father, and I know his '
        "enmity toward the people of this affair. To that has now been added your going out with "
        "me and your long absence from him, without his leave and without his trust, so that his "
        'heart is troubled against us."\n'
    )

    findings = duplicate_passage_findings(text)

    assert len(findings) == 1
    finding = findings[0]
    assert finding["chapter"] == "7. The Long Road"
    assert finding["paragraphs"] >= 2
    # Both copies are named, so a reader can compare each against the source.
    assert finding["first_copy_paragraphs"][0] < finding["second_copy_paragraphs"][0]
    assert "clasped hands" in finding["first_copy_opens"] or "grasped the counsel" in finding["second_copy_opens"]


def test_duplicate_passage_findings_never_mutates_the_text() -> None:
    # IDENTIFY-ONLY: each copy of a real duplicate can be faithful where the other
    # is wrong, so dropping one automatically would destroy source material.
    text = (
        "# Book\n\n"
        "## 7. The Long Road\n\n"
        + "\n\n".join(
            [
                "Then the two rose and clasped hands and embraced one another, each bidding the "
                "other a long farewell, unable to hold back his tears and unable to speak at all "
                "except by a sign of the hand between them, and then at last they parted.",
                "He walked on for a while beside the river and considered everything that the "
                "Shaykh had said to him about patience and about the trust that had been laid "
                "upon him, and he found that he could not yet see the whole of its meaning.",
                "Then the two stood and clasped hands and embraced one another, each giving his "
                "friend a long farewell, unable to master himself against the weight of that "
                "parting, able to speak only by a gesture of the hand, and then they parted.",
            ]
        )
        + "\n"
    )

    before = text
    duplicate_passage_findings(text)

    assert text == before


def test_duplicate_passage_findings_ignores_legitimate_dialogue() -> None:
    # Alternating speech turns that ask and answer DIFFERENT things. They share a
    # speaker formula and a register, which is what every dialogue chapter in the
    # corpus does; they do not narrate the same events twice.
    text = (
        "# Book\n\n"
        "## 3. The Boy at the Door\n\n"
        'The boy said: "Tell me of the twelve islands that stand in the sea of knowledge, for I '
        "have heard them named and have never once heard what is meant by them, nor by what "
        'reckoning they were counted at twelve and not at some other number."\n\n'
        'The Master said: "Each is a station in which the seeker is questioned, and he does not '
        "pass from one to the next until what was asked of him at the first has been answered in "
        'him and has become part of the way he lives."\n\n'
        'The boy said: "Then what becomes of a man who dies upon the road, having answered some '
        "of what was asked and left the rest unanswered? Is the portion he finished counted for "
        'him, or is it lost with the portion he never reached?"\n\n'
        'The Master said: "Nothing that was truly finished in him is ever lost. What he completed '
        "stands to his account, and what he left is held against no one who was overtaken while "
        'still walking toward it in good faith."\n'
    )

    assert duplicate_passage_findings(text) == []


def test_preface_skipped_when_not_included(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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

    text = te.author_translation_edition_compose(bd, log=lambda *a, **k: None, enforce_contract=False).read_text(
        encoding="utf-8"
    )

    assert "Skip Me" not in text


def test_a_composer_authored_chapter_is_never_re_translated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No model call, and the author's words reach book.md unaltered.

    This is where the money was going: on 2026-07-21 a rebuild re-translated all
    nine chapters of the-master-and-the-disciple and the replay then restored eight
    of them, so the fresh prose was paid for and discarded. The Composer is the
    singular path for PDF-bound chapter changes; composing over it bought nothing.
    """
    import _translation_edition as te
    from _book_edits import record_edit

    composed: list[str] = []

    def spy(title, body, previous_tail, book_dir, label, log, **kw):
        composed.append(title)
        return body.strip()

    monkeypatch.setattr(te, "_compose_one", spy)

    bd = tmp_path / "the-book"
    (bd / "book").mkdir(parents=True)
    (bd / "_system" / "source" / "text").mkdir(parents=True)
    (bd / "_system" / "source" / "text" / "refined-english.md").write_text(
        "The traveller who was lost and then guided came to the city.\nHe learned and returned.",
        encoding="utf-8",
    )
    toc = {
        "book_title": "The Book",
        "chapters": [
            {"bk_index": 1, "title": "The Traveller Guided", "source_line_ranges": [[1, 1]]},
            {"bk_index": 2, "title": "The Return", "source_line_ranges": [[2, 2]]},
        ],
    }
    (bd / "book" / "book-toc.json").write_text(json.dumps(toc), encoding="utf-8")
    record_edit(bd, chapter_key="the traveller guided", body_md="The author's own rendering of this chapter.")

    text = te.author_translation_edition_compose(bd, log=lambda *a, **k: None, enforce_contract=False).read_text(
        encoding="utf-8"
    )

    assert composed == ["The Return"]  # the authored chapter never reached a model
    assert "The author's own rendering of this chapter." in text
    assert "He learned and returned." in text  # the other chapter still composed


# ─── Arabic-coverage gate (deterministic script-preservation net) ──────────────

# A compact stand-in for OCR ground truth: six Quranic verses fenced in the printed
# edition's quotation delimiters (enough to clear _ARABIC_COVERAGE_MIN_QUOTES), plus
# a short variant-reading note that must NOT count as a quotation.
_OCR_GROUND_TRUTH = (
    "<!-- page 22 -->\n"
    "قال عز وجل :\n"
    "((إِلَّا الَّذِينَ آمَنُوا وَعَمِلُوا الصَّالِحَاتِ وَقَلِيلٌ مَا هُمْ))\n"
    "وقال :\n"
    "((وَلَٰكِنَّ أَكْثَرَ النَّاسِ لَا يَعْلَمُونَ))\n"
    "وقال تعالى :\n"
    "«مِنْهُمُ الْمُؤْمِنُونَ وَأَكْثَرُهُمُ الْفَاسِقُونَ»\n"
    "وقال :\n"
    "((وَمَا أَكْثَرُ النَّاسِ وَلَوْ حَرَصْتَ بِمُؤْمِنِينَ))\n"
    "وقال جل ذكره :\n"
    "((فَأَعْرَضَ أَكْثَرُهُمْ فَهُمْ لَا يَسْمَعُونَ))\n"
    "وقال :\n"
    "((قَدْ ضَلُّوا مِنْ قَبْلُ وَأَضَلُّوا كَثِيرًا وَضَلُّوا عَنْ سَوَاءِ السَّبِيلِ))\n"
    "(١) في نسخة (س)\n"
)


def test_arabic_quote_spans_extracts_verses_and_skips_apparatus() -> None:
    spans = arabic_quote_spans(_OCR_GROUND_TRUTH)
    assert len(spans) == 6
    assert any("الصَّالِحَاتِ" in s for s in spans)
    # The short "(١) في نسخة (س)" variant note is below the length floor — excluded.
    assert not any("نسخة" in s for s in spans)


def test_arabic_quote_count_matches_spans() -> None:
    assert arabic_quote_count(_OCR_GROUND_TRUTH) == 6
    assert arabic_quote_count("") == 0
    assert arabic_quote_count("plain english, no arabic at all") == 0


def test_arabic_run_spans_counts_output_quotations() -> None:
    # An English chapter that preserved two of the verses in Arabic script.
    out = (
        'He said: "Except those who believed" (إِلَّا الَّذِينَ آمَنُوا وَعَمِلُوا الصَّالِحَاتِ).\n'
        'And He said: "But most people do not know" (وَلَٰكِنَّ أَكْثَرَ النَّاسِ لَا يَعْلَمُونَ).\n'
    )
    assert len(arabic_run_spans(out)) == 2
    # English-only output carries no Arabic runs.
    assert arabic_run_spans("He said: Except those who believed. And He said: most people.") == []


def test_arabic_coverage_shortfall_fires_on_catastrophic_drop() -> None:
    # English-only output (0 Arabic runs) against a 6-quote source -> retry suffix.
    suffix = arabic_coverage_shortfall(
        "He said: Except those who believed, and how few they are. And most do not know.",
        _OCR_GROUND_TRUTH,
    )
    assert suffix != ""
    assert "MUST appear in its Arabic script" in suffix
    # The suffix names the specific dropped spans as evidence.
    assert "الصَّالِحَاتِ" in suffix


def test_arabic_coverage_shortfall_passes_when_arabic_preserved() -> None:
    # All six verses preserved in Arabic -> at/above floor -> no retry (empty suffix).
    full = " ".join(f"({s})" for s in arabic_quote_spans(_OCR_GROUND_TRUTH))
    assert arabic_coverage_shortfall(full, _OCR_GROUND_TRUTH) == ""


def test_arabic_coverage_shortfall_skips_short_source_and_empty() -> None:
    # No Arabic ground truth -> never fires (English / fiction path).
    assert arabic_coverage_shortfall("anything", "") == ""
    # A source below the min-quote cluster -> not gated even if output has no Arabic.
    tiny = "((إِلَّا الَّذِينَ آمَنُوا وَعَمِلُوا الصَّالِحَاتِ))\n"
    assert arabic_quote_count(tiny) < _ARABIC_COVERAGE_MIN_QUOTES
    assert arabic_coverage_shortfall("english only", tiny) == ""


def test_arabic_ground_truth_block_is_empty_without_source() -> None:
    # English / fiction books have no OCR ground truth — the prompt must be unchanged.
    assert arabic_ground_truth_block("") == ""
    block = arabic_ground_truth_block(_OCR_GROUND_TRUTH)
    assert "MUST be rendered in its Arabic script" in block


def test_arabic_coverage_hint_lists_source_spans() -> None:
    hint = arabic_coverage_hint(_OCR_GROUND_TRUTH)
    assert hint.count("\n- ") + hint.count("- ", 0, 2) >= 1  # bullet list
    assert "الصَّالِحَاتِ" in hint
