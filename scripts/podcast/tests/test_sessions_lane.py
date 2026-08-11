#!/usr/bin/env python3
"""What the Sessions lane must keep doing, pinned against real defects.

Every case here is a bug that was actually made and then fixed while Love Of The
Prophet was being ingested, or a decision that would be silently reversible. The
lane reads a 29 MB UTF-16 SQL dump and years-old hand-authored HTML, so almost
nothing about it is provable by inspection — the parser looked right and lost a
third of the Arabic, the audio map looked right and dropped two of five
lectures.

No dump is read here beyond one hand-built fragment, and no Drive mount is
touched: every case is either pure text or a temporary content root.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import pytest  # noqa: E402
from sessions.convert import convert, localise_images  # noqa: E402
from sessions.dump import INGESTABLE_GROUPS, Session, duplicate_transcripts, load_sessions, strip_markup  # noqa: E402
from sessions.ingest import SERIES, _heard_text, _title_of  # noqa: E402

# ---------------------------------------------------------------------------
# The dump's allow-list
# ---------------------------------------------------------------------------


def test_a_group_outside_the_allow_list_is_refused_not_returned() -> None:
    """The exclusions are enforced where the dump is READ, not per caller.

    G5 (MABDA MA'AD) belongs in the al-anwaar reading edition and G7/G12/G18
    already shipped as books. A lane that selected "every group with usable
    transcripts" would drag all four back in, and every caller would have to
    remember not to.
    """
    with pytest.raises(ValueError) as raised:
        load_sessions(5)
    assert "al-anwaar" in str(raised.value)

    for excluded in (5, 7, 12, 18):
        assert excluded not in INGESTABLE_GROUPS


def test_the_allow_list_covers_exactly_the_series_the_plan_named() -> None:
    assert set(INGESTABLE_GROUPS.values()) == {
        "is-quran-a-miracle",
        "islam-vs-iman",
        "wise-reminder",
        "quran-comprehension",
        "surah-al-fateha",
        "mindful-prayers",
        "love-of-the-prophet",
    }


def test_a_null_transcript_is_not_a_short_one() -> None:
    """The dump writes SQL NULL as a bare token, which is not falsy as a string."""
    assert strip_markup("ULL") == ""
    assert strip_markup("") == ""
    assert strip_markup("<p>Real teaching.</p>") == "Real teaching."


def _session(session_id: int, html: str) -> Session:
    return Session(
        session_id=session_id,
        group_id=14,
        sequence=session_id,
        name=f"Session {session_id}",
        description="",
        date=None,
        media_guid=None,
        transcript_html=html,
    )


def test_a_copy_pasted_transcript_is_reported_rather_than_repaired() -> None:
    """Session 211 holds a 99.96% copy of 215 — publishing it verbatim would put
    a different lecture under its title. The lane names the pair; the decision
    about which text to trust is the series definition's, not the parser's."""
    body = "<p>" + ("The prophet taught his companions patience. " * 40) + "</p>"
    sessions = [_session(1, body), _session(2, body + "<p>One extra line.</p>")]
    assert duplicate_transcripts(sessions) == [(1, 2)]


def test_two_genuinely_different_transcripts_are_not_reported() -> None:
    sessions = [
        _session(1, "<p>" + ("Love is a seed that must be nurtured. " * 40) + "</p>"),
        _session(2, "<p>" + ("Success is measured against the hereafter. " * 40) + "</p>"),
    ]
    assert duplicate_transcripts(sessions) == []


# ---------------------------------------------------------------------------
# The HTML the admin actually stored
# ---------------------------------------------------------------------------


def test_the_editors_own_buttons_are_dropped_whole() -> None:
    html = (
        "<div class='hadees-widget'><p>He said this.</p>"
        "<button class='delete-hadees-btn froala-only-btn'>Delete</button></div>"
    )
    out = convert(html)
    assert "Delete" not in out.markdown
    assert out.dropped_chrome == 1


def test_a_verse_card_becomes_a_plain_blockquote_carrying_both_parts() -> None:
    """The renderer decides what KIND of quotation a block is — scripture, a
    tradition, verse, a saying. Emitting our own class here would be a second
    opinion about the same paragraph, which is the one thing the reader contract
    exists to prevent."""
    html = (
        "<div class='ayah-card'>"
        "<p class='ayah-arabic'>قُلْ هُوَ اللَّهُ أَحَدٌ</p>"
        "<p class='ayah-translation'>Say: He is Allah, the One.</p>"
        "</div>"
    )
    out = convert(html)
    lines = [line for line in out.markdown.splitlines() if line.strip()]

    assert out.quotes == 1
    assert all(line.startswith(">") for line in lines)
    assert "قُلْ هُوَ اللَّهُ أَحَدٌ" in out.markdown
    assert "Say: He is Allah, the One." in out.markdown
    # The Arabic leads and the English follows, which is the shape every
    # quotation in this library takes.
    assert out.markdown.index("قُلْ") < out.markdown.index("Say:")
    assert "class=" not in out.markdown


def test_a_heading_inside_a_quotation_does_not_stay_a_heading() -> None:
    """Several hadith widgets open with an <h3> naming the speaker, and `> ###`
    renders as a heading floating inside a quotation."""
    html = "<div class='hadees-widget'><h3><strong>Imam Ali</strong></h3><p>He said this.</p></div>"
    out = convert(html)
    assert "###" not in out.markdown
    assert "Imam Ali" in out.markdown


def test_froalas_crossed_tags_cannot_leave_emphasis_open() -> None:
    """`<h3><strong>x</h3>` appears in the stored HTML, so a `**` can open inside
    a quoted block and never close — which italicises the rest of the chapter."""
    html = "<div class='hadees-widget'><h3><strong>Unclosed</h3><p>Body text.</p></div>"
    out = convert(html)
    assert out.markdown.count("**") % 2 == 0


def test_class_matching_folds_case() -> None:
    """`inlineArabic` in one session, `InlineArabic` in two others, authored by
    hand years apart. Matching exactly loses a third of the Arabic in Love Of
    The Prophet alone."""
    for spelling in ("inlineArabic", "InlineArabic", "INLINEARABIC"):
        out = convert(f"<p>He said <span class='{spelling}'>الحمد</span> often.</p>")
        assert "الحمد" in out.markdown


def test_third_party_verse_badges_are_dropped_and_counted() -> None:
    """Sixty-two of the sixty-four images in Love Of The Prophet are decorative
    numerals hotlinked from someone else's bucket. Keeping them would make an
    offline page depend on another site staying up."""
    html = (
        "<p><img src='https://myislam.sfo3.digitaloceanspaces.com/ayat/ayah-255.png'></p>"
        "<p><img src='Resources/IMAGES/213/66560670-7213-4cba-b2eb-e49a0af49bd3.jpg'></p>"
    )
    out = convert(html)
    assert out.dropped_badges == 1
    assert len(out.images) == 1


def test_an_image_is_rewritten_to_the_books_own_path_and_asked_for_by_name() -> None:
    markdown = "![](Resources/IMAGES/213/66560670-7213-4CBA-B2EB-E49A0AF49BD3.JPG)"
    out, wanted = localise_images(markdown, "love-of-the-prophet")
    assert out == "![](images/213/66560670-7213-4cba-b2eb-e49a0af49bd3.jpg)"
    assert wanted == [("213", "66560670-7213-4cba-b2eb-e49a0af49bd3.jpg")]


def test_an_empty_transcript_converts_to_nothing_rather_than_to_whitespace() -> None:
    assert convert("").markdown == ""
    assert convert("   ").markdown == ""


# ---------------------------------------------------------------------------
# The series definition
# ---------------------------------------------------------------------------


def test_every_audio_map_pairs_each_file_with_a_distinct_session() -> None:
    """Position alone puts Love Of The Prophet off by one — five recordings
    against six sessions, and the one without a recording is the opener. A
    duplicated sequence would silently publish one lecture twice."""
    for slug, series in SERIES.items():
        sequences = list(series.audio_map.values())
        assert len(set(sequences)) == len(sequences), f"{slug} maps two files to one session"


def test_a_title_fix_repairs_the_stored_name_and_nothing_else() -> None:
    stored = Session(
        session_id=212,
        group_id=14,
        sequence=3,
        name="eed For Messengers",
        description="",
        date=None,
        media_guid=None,
        transcript_html="",
    )
    series = SERIES["love-of-the-prophet"]
    assert _title_of(series, stored) == "Need For Messengers"

    untouched = Session(**{**stored.__dict__, "sequence": 1, "name": "Personal Intro"})
    assert _title_of(series, untouched) == "Personal Intro"


def test_the_title_fixes_are_corrections_not_retitlings() -> None:
    """Renaming a lecture Asif delivered is his call. Every fix must still be
    recognisably the stored name — a dropped letter restored, a case corrected —
    which is testable as: the words survive, ignoring case and spacing."""
    for series in SERIES.values():
        for fixed in series.title_fixes.values():
            assert fixed == fixed.strip()
            assert len(fixed.split()) >= 2


# ---------------------------------------------------------------------------
# Reading text taken from the recording
# ---------------------------------------------------------------------------


VTT = """WEBVTT

1
00:00:00.000 --> 00:00:02.000
<v Speaker 1>One.

2
00:00:02.000 --> 00:00:04.000
<v Speaker 1>Two.
"""


def test_the_recordings_words_are_grouped_into_paragraphs_not_one_line_per_breath(tmp_path) -> None:
    """A VTT cue is a breath, not a sentence. One line per cue reads as a
    subtitle file rather than as a chapter."""
    (tmp_path / "transcripts").mkdir()
    (tmp_path / "transcripts" / "ep01.vtt").write_text(VTT, encoding="utf-8")

    text = _heard_text(tmp_path, 1)
    assert text == "One. Two."
    assert "\n" not in text


def test_no_transcript_yields_no_text_rather_than_an_error(tmp_path) -> None:
    """A chapter with no stored text AND no transcription must be REPORTED, not
    crash the ingest — the run has five other chapters to lay down."""
    assert _heard_text(tmp_path, 1) == ""
    assert _heard_text(tmp_path, None) == ""


# ---------------------------------------------------------------------------
# The episode-to-chapter bridge
# ---------------------------------------------------------------------------


def test_the_bridge_shipped_with_the_book_names_only_chapters_that_exist() -> None:
    """`read_bridge` prints a warning and drops a pairing whose chapter it cannot
    find, so a drifted bridge fails SILENTLY on the site — the Read and Listen
    tabs simply stop pointing at each other. This asserts over the real book."""
    book = Path(__file__).resolve().parents[3] / "content/Sessions/love-of-the-prophet"
    bridge_path = book / "_system/listener-episode-chapters.json"
    if not bridge_path.exists():  # the book is ingested on demand, not in CI
        pytest.skip("love-of-the-prophet is not laid down in this checkout")

    bridge = json.loads(bridge_path.read_text(encoding="utf-8"))
    headings = {
        line[3:].strip()
        for line in (book / "book/book.md").read_text(encoding="utf-8").splitlines()
        if line.startswith("## ")
    }

    assert bridge, "a series with recordings must ship a bridge"
    for number, titles in bridge.items():
        assert int(number) >= 1
        for title in titles:
            assert title in headings, f"episode {number} names a chapter that is not in the book"
