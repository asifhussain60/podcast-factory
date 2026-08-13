#!/usr/bin/env python3
"""`pf-compose-articulator`'s engine: chapter resolution, the fidelity gate,
the Sessions-lane guard, and the install path.

The first real install (done by hand, before this tool existed) got three
things wrong: it trusted the hand-off file's own heading instead of the
book's, it never ran the pipeline's own fidelity gate, and nothing guarded
against a live Composer. These tests pin the fixes for all three.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import _sessions_prose_format as spf  # noqa: E402
import compose_articulate as ca  # noqa: E402
import compose_paste_fix as cpf  # noqa: E402

BOOK = """# A Series

## Introduction to the Book

Apparatus, not a chapter.

## The Stages Of Love

The first level is attachment. It is a small thing, and it grows.

## Linguistic Meaning Of Allah

A different chapter about a different word entirely, unrelated to love.
"""


@pytest.fixture()
def book_dir(tmp_path: Path) -> Path:
    (tmp_path / "book").mkdir()
    (tmp_path / "_system").mkdir()
    (tmp_path / "book" / "book.md").write_text(BOOK, encoding="utf-8")
    (tmp_path / "_system" / "sessions-articulation.json").write_text(json.dumps({"chapters": {}}), encoding="utf-8")
    (tmp_path / "_system" / "series-config.yaml").write_text(
        "content_profile: islamic_session\nnarrative_frame: first_person_expository\n",
        encoding="utf-8",
    )
    return tmp_path


def handoff(tmp_path: Path, text: str, name: str = "handoff.md") -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


# ─── the Sessions-lane guard ──────────────────────────────────────────────


def test_refuses_a_book_with_no_sessions_ledger(tmp_path: Path) -> None:
    (tmp_path / "book").mkdir()
    (tmp_path / "_system").mkdir()
    (tmp_path / "book" / "book.md").write_text(BOOK, encoding="utf-8")
    with pytest.raises(PermissionError, match="Sessions-lane only"):
        ca._require_sessions_lane(tmp_path, "some-translation-edition")


def test_a_sessions_lane_book_is_accepted(book_dir: Path) -> None:
    ca._require_sessions_lane(book_dir, "surah-al-fateha")  # does not raise


# ─── chapter resolution — never the hand-off file's own heading ──────────


def test_resolves_by_exact_key(book_dir: Path) -> None:
    heading = ca.resolve_chapter(book_dir / "book" / "book.md", "the stages of love")
    assert heading == "The Stages Of Love"


def test_resolves_by_fragment(book_dir: Path) -> None:
    heading = ca.resolve_chapter(book_dir / "book" / "book.md", "Stages")
    assert heading == "The Stages Of Love"


def test_no_match_lists_every_chapter(book_dir: Path) -> None:
    with pytest.raises(ValueError, match="no chapter matches") as exc:
        ca.resolve_chapter(book_dir / "book" / "book.md", "nonexistent")
    assert "Linguistic Meaning Of Allah" in str(exc.value)


def test_the_handoff_files_own_heading_is_never_trusted(book_dir: Path, tmp_path: Path) -> None:
    """The exact bug the first manual install hit: the hand-off file said
    'Stages of Love' (lowercase 'of'), the book says 'Stages Of Love'."""
    off = handoff(tmp_path, "## Stages of Love\n\nA small attachment. It is a small thing, and it grows more.\n")
    result = ca.check(book_dir, "the stages of love", off, log=lambda *_: None)
    assert result["heading"] == "The Stages Of Love"  # the book's casing, not the hand-off's


# ─── the fidelity gate ─────────────────────────────────────────────────────


def test_a_faithful_rewrite_is_clean(book_dir: Path, tmp_path: Path) -> None:
    off = handoff(
        tmp_path,
        "## The Stages Of Love\n\nThe first level is attachment. It is a small thing, and it grows.\n",
    )
    result = ca.check(book_dir, "the stages of love", off, log=lambda *_: None)
    assert result["clean"] is True
    assert result["findings"] == []


def test_unrelated_content_is_refused(book_dir: Path, tmp_path: Path) -> None:
    """Installing under the wrong chapter — the content shares nothing with
    the chapter it would replace."""
    off = handoff(tmp_path, "## Linguistic Meaning Of Allah\n\nThe first level is attachment.\n")
    result = ca.check(book_dir, "linguistic meaning of allah", off, log=lambda *_: None)
    assert result["clean"] is False
    assert result["findings"]


def test_sessions_normalizer_merges_split_hadith_card() -> None:
    source = (
        "The Prophet said:\n\n"
        "> قَالَ رَسُولُ اللَّہِ صَلَّی اللَّہُ عَلَیْہِ وَ آلِہِ وَ سَلَّمَ\n\n"
        "> الشِّرکُ فِی أُمَّتِی أَخفٰی مِن سَیرِ النَّمَلِ\n\n"
        "Shirk is more hidden in my nation than the movement of an ant.\n"
    )
    fixed, changes = spf.normalize_sessions_prose(source)
    assert "قَالَ رَسُولُ" not in fixed
    assert (
        "> الشِّرکُ فِی أُمَّتِی أَخفٰی مِن سَیرِ النَّمَلِ\n>\n> Shirk is more hidden in my nation than the movement of an ant."
    ) in fixed
    assert changes[-1]["quote_kind"] == {
        "first_line": "الشِّرکُ فِی أُمَّتِی أَخفٰی مِن سَیرِ النَّمَلِ",
        "kind": "hadith",
    }


def test_sessions_normalizer_drops_named_quran_ref_when_card_can_name_it() -> None:
    source = (
        "Allah says:\n\n"
        "The Criterion [25:43]\n\n"
        "> أَرَءَيْتَ مَنِ ٱتَّخَذَ إِلَهَهُۥ هَوَىٰهُ\n"
        ">\n"
        "> Have you seen the one who takes his own desire as his god?\n"
    )
    fixed, changes = spf.normalize_sessions_prose(source)
    assert "The Criterion [25:43]" not in fixed
    assert "> أَرَءَيْتَ مَنِ ٱتَّخَذَ إِلَهَهُۥ هَوَىٰهُ" in fixed
    assert any(c["kind"] == "named-citation-line-removed" for c in changes)


# ─── install ───────────────────────────────────────────────────────────────


def test_install_refuses_on_a_finding_without_force(book_dir: Path, tmp_path: Path) -> None:
    off = handoff(tmp_path, "## Linguistic Meaning Of Allah\n\nThe first level is attachment.\n")
    result = ca.install(book_dir, "linguistic meaning of allah", off, log=lambda *_: None)
    assert result["installed"] is False
    # book.md must be untouched
    assert "A different chapter about a different word entirely" in (book_dir / "book" / "book.md").read_text()


def test_install_writes_book_md_and_records_the_composer_edit(book_dir: Path, tmp_path: Path) -> None:
    off = handoff(
        tmp_path,
        "## The Stages Of Love\n\nThe first level is attachment. It is a small thing, and it grows.\n",
    )
    result = ca.install(book_dir, "the stages of love", off, log=lambda *_: None)
    assert result["installed"] is True

    text = (book_dir / "book" / "book.md").read_text(encoding="utf-8")
    assert "The first level is attachment" in text
    assert "## Linguistic Meaning Of Allah" in text  # the next chapter survives untouched

    edits = json.loads((book_dir / "_system" / "composer-edits.json").read_text(encoding="utf-8"))
    keys = [e["chapter_key"] for e in edits["edits"]]
    assert "the stages of love" in keys

    ledger = json.loads((book_dir / "_system" / "sessions-articulation.json").read_text(encoding="utf-8"))
    assert ledger["chapters"]["the stages of love"]["status"] == "adapted"

    assert (book_dir / "book" / "book.md.bak").exists()


def test_force_installs_despite_a_finding(book_dir: Path, tmp_path: Path) -> None:
    off = handoff(tmp_path, "## Linguistic Meaning Of Allah\n\nThe first level is attachment.\n")
    result = ca.install(book_dir, "linguistic meaning of allah", off, force=True, log=lambda *_: None)
    assert result["installed"] is True
    assert result["findings"]  # still reported, never silently dropped
    text = (book_dir / "book" / "book.md").read_text(encoding="utf-8")
    assert "The first level is attachment." in text


def test_installing_twice_does_not_duplicate_the_composer_edit(book_dir: Path, tmp_path: Path) -> None:
    off = handoff(
        tmp_path,
        "## The Stages Of Love\n\nThe first level is attachment. It is a small thing, and it grows.\n",
    )
    ca.install(book_dir, "the stages of love", off, log=lambda *_: None)
    ca.install(book_dir, "the stages of love", off, log=lambda *_: None)
    edits = json.loads((book_dir / "_system" / "composer-edits.json").read_text(encoding="utf-8"))
    keys = [e["chapter_key"] for e in edits["edits"]]
    assert keys.count("the stages of love") == 1


# ─── images the hand-off can't carry forward ──────────────────────────────


IMG_A = "images/87/983c2f7d-5f31-4f45-b5bf-27da233a43c0.jpg"
IMG_B = "images/87/1b3198d2-bb3f-48d3-ac49-05f97e515554.jpg"

BOOK_WITH_IMAGES = f"""# A Series

## A Chapter With Slides

The first level is attachment. It is a small thing, and it grows.

A vs THE

![]({IMG_A})

What matters is the difference between a thing and the thing.

ILAH vs AL-ILAH

![]({IMG_B})

The distinction carries all the way through.

## Next Chapter

Unrelated content entirely.
"""


@pytest.fixture()
def book_dir_with_images(tmp_path: Path) -> Path:
    (tmp_path / "book").mkdir()
    (tmp_path / "_system").mkdir()
    (tmp_path / "book" / "book.md").write_text(BOOK_WITH_IMAGES, encoding="utf-8")
    (tmp_path / "_system" / "sessions-articulation.json").write_text(json.dumps({"chapters": {}}), encoding="utf-8")
    (tmp_path / "_system" / "series-config.yaml").write_text(
        "content_profile: islamic_session\nnarrative_frame: first_person_expository\n",
        encoding="utf-8",
    )
    return tmp_path


def test_no_restoration_needed_when_the_base_chapter_has_no_images(book_dir: Path) -> None:
    base_body, _, _ = ca._chapter_body(book_dir / "book" / "book.md", "The Stages Of Love")
    new_body, restored = ca._restore_images(base_body, "A rewritten body with no images at all.")
    assert restored == []
    assert new_body == "A rewritten body with no images at all."


def test_an_image_is_reinserted_after_its_surviving_caption(book_dir_with_images: Path, tmp_path: Path) -> None:
    off = handoff(
        tmp_path,
        "## A Chapter With Slides\n\n"
        "Attachment is where love begins; it is small, but it grows.\n\n"
        "A vs THE\n\n"
        "There is a real difference between a thing and the thing.\n\n"
        "ILAH vs AL-ILAH\n\n"
        "That same distinction runs through everything that follows.\n",
    )
    result = ca.check(book_dir_with_images, "A Chapter With Slides", off, log=lambda *_: None)
    assert IMG_A in result["body"]
    assert IMG_B in result["body"]
    assert [r["placement"] for r in result["images_restored"]] == ["anchored", "anchored"]
    # each image lands directly after the caption line it followed in the source
    lines = result["body"].split("\n")
    a_idx = next(i for i, ln in enumerate(lines) if IMG_A in ln)
    assert lines[a_idx - 2].strip().lower() == "### a vs the"


def test_an_image_whose_caption_was_paraphrased_away_still_lands_somewhere(
    book_dir_with_images: Path, tmp_path: Path
) -> None:
    off = handoff(
        tmp_path,
        "## A Chapter With Slides\n\n"
        "Attachment is where love begins.\n\n"
        "There is a real difference between something generic and something specific.\n\n"
        "That same distinction runs through everything that follows.\n",
    )
    result = ca.check(book_dir_with_images, "A Chapter With Slides", off, log=lambda *_: None)
    assert IMG_A in result["body"]
    assert IMG_B in result["body"]
    assert all(r["placement"] == "proportional" for r in result["images_restored"])


def test_an_image_the_handoff_already_includes_is_not_duplicated(book_dir_with_images: Path, tmp_path: Path) -> None:
    off = handoff(
        tmp_path,
        f"## A Chapter With Slides\n\nAttachment grows.\n\n![]({IMG_A})\n\nDistinction carries through.\n\n"
        f"![]({IMG_B})\n\nEverything follows from it.\n",
    )
    result = ca.check(book_dir_with_images, "A Chapter With Slides", off, log=lambda *_: None)
    assert result["body"].count(IMG_A) == 1
    assert result["body"].count(IMG_B) == 1
    assert result["images_restored"] == []


def test_check_normalizes_heading_and_citation_house_style(book_dir: Path, tmp_path: Path) -> None:
    off = handoff(
        tmp_path,
        "## The Stages Of Love\n\n"
        "### Trustworthy Friend ولیجۃ\n\nWALEEJA\n\n"
        "The first level is attachment. It is a small thing, and it grows.\n",
    )
    result = ca.check(book_dir, "the stages of love", off, log=lambda *_: None)
    assert "### Trustworthy Friend (ولیجۃ)" in result["body"]
    assert "WALEEJA" not in result["body"]
    assert result["format_changes"]


# ─── pasted paragraph repair + Scholar continuity ──────────────────────────


def test_split_sentence_fragments_are_joined_before_gating(book_dir: Path, tmp_path: Path) -> None:
    off = handoff(
        tmp_path,
        "## The Stages Of Love\n\nThe first level is attachment. It is a small thing\n\nand it grows.\n",
    )
    result = ca.check(book_dir, "the stages of love", off, log=lambda *_: None)
    assert "It is a small thing and it grows." in result["body"]
    assert [c["kind"] for c in result["paragraph_changes"]] == ["split-sentence-join"]


def test_paragraph_repair_preserves_images_and_blockquotes() -> None:
    body = (
        "This line was broken\ninside one pasted paragraph.\n\n"
        "> Arabic quotation stays apart.\n\n"
        "![](images/87/a.jpg)\n\n"
        "A sentence was split\n\n"
        "across a blank line."
    )
    repaired, changes = ca.repair_split_paragraphs(body)
    assert "This line was broken inside one pasted paragraph." in repaired
    assert "A sentence was split across a blank line." in repaired
    assert "> Arabic quotation stays apart.\n\n![](images/87/a.jpg)" in repaired
    assert [c["kind"] for c in changes] == ["soft-line-join", "split-sentence-join"]


def test_standalone_section_titles_are_promoted_without_touching_citations() -> None:
    body = (
        "ILAH\n\n"
        "A vs. THE\n\n"
        "Meanings of the Word ILAH\n\n"
        "Allah as the One I Lean Upon\n\n"
        "The Criterion [25:43]\n\n"
        "قَالَ رَسُولُ اللَّہِ صَلَّی اللَّہُ عَلَیْہِ وَ آلِہِ وَ سَلَّمَ\n\n"
        "This remains a sentence."
    )
    repaired, changes = ca.promote_standalone_headings(body)
    assert "### ILAH" in repaired
    assert "### A vs. THE" in repaired
    assert "### Meanings of the Word ILAH" in repaired
    assert "### Allah as the One I Lean Upon" in repaired
    assert "### The Criterion" not in repaired
    assert "### قَالَ" not in repaired
    assert [c["kind"] for c in changes] == [
        "heading-promoted",
        "heading-promoted",
        "heading-promoted",
        "heading-promoted",
    ]


def test_scholar_continuity_adapter_can_improve_the_fixed_body(book_dir: Path, tmp_path: Path) -> None:
    off = handoff(
        tmp_path,
        "## The Stages Of Love\n\nThe first level is attachment. It is a small thing, and it grows.\n",
    )

    def adapter(book_dir: Path, heading: str, base_body: str, repaired_body: str, *, log=print):
        assert heading == "The Stages Of Love"
        assert "The first level is attachment" in base_body
        return (
            repaired_body + "\n\nThis added bridge stays inside the same teaching instead of opening a new one.",
            [{"kind": "scholar-continuity", "status": "kept", "grounded": 1, "morphology": False}],
        )

    result = ca.check(
        book_dir,
        "the stages of love",
        off,
        log=lambda *_: None,
        scholar_continuity=True,
        continuity_adapter=adapter,
    )
    assert "This added bridge" in result["body"]
    assert result["continuity_changes"][0]["status"] == "kept"


def test_student_readability_adapter_reports_questions_without_editing_body(book_dir: Path, tmp_path: Path) -> None:
    off = handoff(
        tmp_path,
        "## The Stages Of Love\n\nThe first level is attachment. It is a small thing, and it grows.\n",
    )

    def adapter(book_dir: Path, heading: str, body: str, *, log=print):
        assert heading == "The Stages Of Love"
        assert "attachment" in body
        return {
            "status": "checked",
            "budget": 2,
            "proposed": 1,
            "gated_out": [],
            "questions": [
                {
                    "defect": "undefined-term",
                    "question": "What does attachment mean in this chapter?",
                    "quote": "The first level is attachment.",
                }
            ],
        }

    result = ca.check(
        book_dir,
        "the stages of love",
        off,
        log=lambda *_: None,
        student_readability=True,
        readability_adapter=adapter,
    )
    assert "The first level is attachment." in result["body"]
    assert result["readability_review"]["status"] == "checked"
    assert result["readability_review"]["questions"][0]["defect"] == "undefined-term"


def test_student_readability_review_prepares_companion_note_payload(
    book_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = "The first level is attachment. It is a small thing, and it grows."

    monkeypatch.setattr(
        cpf,
        "_run_claude_p_with_retry",
        lambda *_args, **_kwargs: (
            0,
            json.dumps(
                [
                    {
                        "defect": "undefined-term",
                        "quote": "The first level is attachment.",
                        "question": "What does attachment mean in this chapter?",
                    }
                ]
            ),
            "",
        ),
    )

    def scholar_adapter(finding, chapter, _book_dir, book_title, _log):
        assert chapter["key"] == "the-stages-of-love"
        assert chapter["prose"] == body
        assert book_title == book_dir.name
        return {
            "note": {
                "id": "student:1234567890abcdef",
                "kind": "explanation",
                "body": "Attachment means the first form of love named here.",
                "anchor": "The first level is attachment.",
                "quote": finding["quote"],
                "review": "proposed",
                "source": {
                    "provider": "scholar",
                    "label": "Ismaili Scholar",
                    "ref": finding["defect"],
                },
            },
            "question": finding["question"],
            "grounded": 1,
            "tightened": False,
        }

    review = cpf.student_readability_review(
        book_dir,
        "The Stages Of Love",
        body,
        log=lambda *_: None,
        scholar_adapter=scholar_adapter,
    )

    assert review["status"] == "checked"
    assert review["questions"][0]["question"] == "What does attachment mean in this chapter?"
    assert review["companion_notes"][0]["id"] == "student:1234567890abcdef"
    assert review["companion_notes"][0]["review"] == "proposed"


def test_scholar_continuity_is_reverted_when_it_drops_images(
    book_dir_with_images: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    off = handoff(
        tmp_path,
        f"## A Chapter With Slides\n\n"
        f"Attachment grows.\n\n![]({IMG_A})\n\n"
        f"Distinction carries through.\n\n![]({IMG_B})\n",
    )

    monkeypatch.setattr(
        cpf,
        "scholar_prepare",
        lambda **_kwargs: {"ok": True, "user": "grounding", "grounded": 1, "morphology": False},
    )
    monkeypatch.setattr(
        cpf,
        "_run_claude_p_with_retry",
        lambda *_args, **_kwargs: (0, "Attachment grows. Distinction carries through.", ""),
    )

    result = ca.check(
        book_dir_with_images,
        "A Chapter With Slides",
        off,
        log=lambda *_: None,
        scholar_continuity=True,
    )
    assert IMG_A in result["body"]
    assert IMG_B in result["body"]
    assert result["continuity_changes"][0]["status"] == "reverted"
    assert "image markdown dropped" in result["continuity_changes"][0]["findings"][-1]


# ─── retrofit_book ──────────────────────────────────────────────────────────


ARABIC_HEADING_BOOK = """# A Series

## Quranic Friendship

### Trustworthy Friend ولیجۃ

WALEEJA

The next word the Quran uses for a friend is ولیجۃ.

## The Stages Of Love

The first level is attachment. It is a small thing, and it grows.
"""


@pytest.fixture()
def book_dir_with_arabic_headings(tmp_path: Path) -> Path:
    (tmp_path / "book").mkdir()
    (tmp_path / "_system").mkdir()
    (tmp_path / "book" / "book.md").write_text(ARABIC_HEADING_BOOK, encoding="utf-8")
    (tmp_path / "_system" / "sessions-articulation.json").write_text(json.dumps({"chapters": {}}), encoding="utf-8")
    (tmp_path / "_system" / "series-config.yaml").write_text(
        "content_profile: islamic_session\nnarrative_frame: first_person_expository\n",
        encoding="utf-8",
    )
    return tmp_path


def test_retrofit_fixes_the_one_chapter_that_needs_it(book_dir_with_arabic_headings: Path) -> None:
    result = ca.retrofit_book(book_dir_with_arabic_headings, log=lambda *_: None)
    assert result["chapters_changed"] == 1
    assert result["detail"][0]["heading"] == "Quranic Friendship"

    text = (book_dir_with_arabic_headings / "book" / "book.md").read_text(encoding="utf-8")
    assert "### Trustworthy Friend (ولیجۃ)" in text
    assert "WALEEJA" not in text
    assert "## The Stages Of Love" in text  # untouched chapter survives
    assert "The first level is attachment. It is a small thing, and it grows." in text


def test_retrofit_records_a_composer_edit_for_the_changed_chapter(book_dir_with_arabic_headings: Path) -> None:
    ca.retrofit_book(book_dir_with_arabic_headings, log=lambda *_: None)
    edits = json.loads((book_dir_with_arabic_headings / "_system" / "composer-edits.json").read_text())
    keys = [e["chapter_key"] for e in edits["edits"]]
    assert "quranic friendship" in keys


def test_retrofit_is_a_no_op_on_a_book_with_no_formatting_defects(book_dir: Path) -> None:
    result = ca.retrofit_book(book_dir, log=lambda *_: None)
    assert result["chapters_changed"] == 0
    assert not (book_dir / "_system" / "composer-edits.json").exists()


def test_retrofit_twice_does_not_duplicate_the_composer_edit(book_dir_with_arabic_headings: Path) -> None:
    ca.retrofit_book(book_dir_with_arabic_headings, log=lambda *_: None)
    ca.retrofit_book(book_dir_with_arabic_headings, log=lambda *_: None)  # idempotent: nothing left to change
    edits = json.loads((book_dir_with_arabic_headings / "_system" / "composer-edits.json").read_text())
    keys = [e["chapter_key"] for e in edits["edits"]]
    assert keys.count("quranic friendship") == 1


def test_install_writes_the_restored_images_to_book_md(book_dir_with_images: Path, tmp_path: Path) -> None:
    off = handoff(
        tmp_path,
        "## A Chapter With Slides\n\n"
        "Attachment is where love begins; it is small, but it grows.\n\n"
        "A vs THE\n\n"
        "There is a real difference between a thing and the thing.\n\n"
        "ILAH vs AL-ILAH\n\n"
        "That same distinction runs through everything that follows.\n",
    )
    result = ca.install(book_dir_with_images, "A Chapter With Slides", off, log=lambda *_: None)
    assert result["installed"] is True
    text = (book_dir_with_images / "book" / "book.md").read_text(encoding="utf-8")
    assert IMG_A in text
    assert IMG_B in text
    assert "## Next Chapter" in text  # untouched


# ─── CLI --json exit code: a finding is data, not a script failure ─────────


def test_json_check_exits_zero_even_with_findings() -> None:
    """The Compose tab's Paste & Fix action shells out to this CLI over stdin
    and reads `clean`/`findings` from the JSON body it asked for. Before this
    fix, a finding made the process exit nonzero — indistinguishable, to a
    caller that only checks the exit code, from the check itself crashing —
    and a perfectly good report was discarded as an error. --json must exit 0
    whenever it successfully printed one; the human/non-JSON exit code still
    reflects clean vs not, unchanged, for shell/script use.

    A real subprocess against the real surah-al-fateha book already in this
    repo, not an isolated tmp_path fixture: main()'s slug resolver goes
    through find_content(), and revoice_gates reads the shared doctrinal data
    tree (content/_shared/islam/) — both only ever resolve against a real
    content root, which an isolated fake repo would have to fully replicate.
    """
    import subprocess

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_DIR / "compose_articulate.py"),
            "surah-al-fateha",
            "The Stages Of Love",
            "--json",
            "--stdin",
        ],
        input=b"Something else entirely, unfaithful to the source.",
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr.decode()
    report = json.loads(result.stdout)
    assert report["clean"] is False
    assert report["findings"]
