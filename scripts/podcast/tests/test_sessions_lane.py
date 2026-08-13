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
from sessions.ingest import SERIES, _heard_text, _title_of, _without_image  # noqa: E402

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
    out, wanted = localise_images(markdown)
    assert out == "![](images/213/66560670-7213-4cba-b2eb-e49a0af49bd3.jpg)"
    assert wanted == [("213", "66560670-7213-4cba-b2eb-e49a0af49bd3.jpg")]


# ---------------------------------------------------------------------------
# Where the picture lives, versus where the editor's browser once fetched it
# ---------------------------------------------------------------------------
#
# 47 of the corpus's image references across the seven ingestable groups carry a
# host in front of the path — 31 the live admin, 16 Asif's own dev server on
# port 786. Every one of them names a file that is sitting in `Resources Images/`
# right now. Reading the host as meaningful cost all 47 of them, and cost them in
# the worst way available: the file was still copied and uploaded, so nothing
# anywhere reported a problem and the page simply showed a broken picture.


@pytest.mark.parametrize(
    "src",
    [
        "Resources/IMAGES/87/21ac5722-564f-4aed-beeb-4f61c600508f.jpg",
        "https://session.kashkole.com/Resources/IMAGES/87/21ac5722-564f-4aed-beeb-4f61c600508f.jpg",
        "http://localhost:786/Resources/IMAGES/87/21ac5722-564f-4aed-beeb-4f61c600508f.jpg",
        "/Resources/IMAGES/87/21ac5722-564f-4aed-beeb-4f61c600508f.jpg",
        "Resources/IMAGES/87/21ac5722-564f-4aed-beeb-4f61c600508f.jpg?v=2",
    ],
)
def test_the_same_picture_localises_the_same_way_however_it_was_referenced(src: str) -> None:
    """The host is where a browser once fetched it, never where the file lives."""
    out, wanted = localise_images(f"![]({src})")
    assert out == "![](images/87/21ac5722-564f-4aed-beeb-4f61c600508f.jpg)"
    assert wanted == [("87", "21ac5722-564f-4aed-beeb-4f61c600508f.jpg")]


def test_a_host_prefixed_reference_is_counted_as_recovered_not_as_unreachable() -> None:
    """It is an ordinary corpus image, and the count is how a regression shows."""
    out = convert(
        "<p><img src='https://session.kashkole.com/Resources/IMAGES/87/21ac5722-564f-4aed-beeb-4f61c600508f.jpg'></p>"
    )
    assert len(out.images) == 1
    assert len(out.hosted_images) == 1
    assert out.external_images == []
    assert out.unmappable_images == []


def test_the_whole_target_is_replaced_so_a_host_cannot_survive_the_rewrite() -> None:
    """Substituting the path fragment alone left the host in place and produced
    `https://session.kashkole.com/images/87/…` — a URL that has never existed on
    that host, pointing away from a file that was correctly in the bucket."""
    out, _ = localise_images(
        "![](https://session.kashkole.com/Resources/IMAGES/87/21ac5722-564f-4aed-beeb-4f61c600508f.jpg)"
    )
    assert "kashkole" not in out
    assert "http" not in out


def test_a_reference_naming_no_corpus_file_is_reported_and_not_rendered() -> None:
    """Seven references in the dump are `Resources/IMAGES/1278/01.jpg` — a real
    folder, a filename that is not a GUID. Emitting one guarantees a broken icon
    on the page and nothing anywhere says why."""
    out = convert("<p><img src='Resources/IMAGES/1278/01.jpg'></p>")
    assert out.unmappable_images == ["Resources/IMAGES/1278/01.jpg"]
    assert out.images == []
    assert "![" not in out.markdown


def test_a_picture_genuinely_on_another_site_is_reported_and_not_rendered() -> None:
    """A gated chapter must not send the reader's browser to a third party, and
    a hotlink breaks the day that site does."""
    out = convert("<p><img src='https://example.com/diagram.png'></p>")
    assert out.external_images == ["https://example.com/diagram.png"]
    assert out.images == []
    assert "![" not in out.markdown


# ---------------------------------------------------------------------------
# Constructs Book 1 was too small to carry
# ---------------------------------------------------------------------------
#
# Love Of The Prophet exercised six sessions and two illustrations, so none of
# the three below ever ran. All three were found by looking at a RENDERED page of
# Book 2 rather than at the markdown, which is the rule step 4b already states:
# four of the five links in the chain were correct when the list markers were
# lost, and the same is true here.


def test_a_font_awesome_icon_is_not_emphasis() -> None:
    """Font Awesome's tag of choice is `<i>`, which is also markdown emphasis.

    508 icons in the corpus, every one EMPTY, so each emitted `*` open and `*`
    close with nothing between: 133 pairs of literal asterisks printed in Surah
    Al-Fateha's prose and 16 in Love Of The Prophet, which is live on the site.
    """
    out = convert("<p>Before <i class='fa fa-ban text-danger fa-2x' aria-hidden='true'></i> after.</p>")
    assert "*" not in out.markdown
    assert "Before" in out.markdown and "after." in out.markdown


def test_a_real_italic_is_still_emphasis() -> None:
    """The icon rule keys on the CLASS, not on the tag — an `<i>` with no Font
    Awesome class is what the author meant it to be."""
    out = convert("<p>He called it <i>ilm</i>.</p>")
    assert "*ilm*" in out.markdown


def test_a_quran_widget_becomes_a_quotation_with_its_translation_beneath() -> None:
    """370 of these in the corpus, and the reason it matters most on a book about
    a surah: unlisted, the verse, its number and its English fell out as three
    loose paragraphs and the page set scripture like ordinary prose."""
    html = (
        "<div class='hq-container quranWidget'>"
        "<div class='quran-surah inlineArabic'><div class='quran-english-name'>The Cow</div></div>"
        "<div><div class='quran-ayats'><span>ٱللَّهُ وَلِىُّ ٱلَّذِينَ آمَنُوا۟</span></div>"
        "<div class='quran-ayat-translation'><span>Allah is the protector of those who believe.</span></div>"
        "</div></div>"
    )
    out = convert(html)
    lines = [line for line in out.markdown.splitlines() if line.strip()]

    assert out.quotes == 1
    assert all(line.startswith(">") for line in lines)
    assert out.markdown.index("ٱللَّهُ") < out.markdown.index("Allah is the protector")


def test_the_translation_is_asked_about_before_the_arabic() -> None:
    """`quran-ayat-translation` CONTAINS `quran-ayat`. Asking about the Arabic
    first files every English gloss as Arabic and the card comes out with the
    translation stacked inside the verse."""
    html = (
        "<div class='quranWidget'>"
        "<div class='quran-ayats-single'>ٱلْحَمْدُ لِلَّهِ</div>"
        "<div class='quran-ayat-translation-single'>All praise is due to Allah.</div>"
        "</div>"
    )
    out = convert(html)
    assert out.markdown.index("ٱلْحَمْدُ") < out.markdown.index("All praise")


def test_the_guide_chips_letter_goes_and_its_caption_and_diagram_stay() -> None:
    """This is the correction, and it cost a run to find.

    Dropping the whole chip read as obviously right — it is the admin's own
    index furniture — and took 36 of Surah Al-Fateha's 63 illustrations with it,
    because the description span holds the label AND the diagram it labels.
    """
    html = (
        "<div class='box box2 shadow2 box-hub'><div class='box-inner'>"
        "<span class='sessionGuide-letter'>W</span>"
        "<span class='sessionGuide-desc'>A vs THE"
        "<img src='Resources/IMAGES/87/21ac5722-564f-4aed-beeb-4f61c600508f.jpg'>"
        "</span></div></div>"
    )
    out = convert(html)

    assert "WA vs THE" not in out.markdown  # the badge ran into the label
    assert "A vs THE" in out.markdown
    assert len(out.images) == 1


# ---------------------------------------------------------------------------
# A picture the corpus has lost
# ---------------------------------------------------------------------------
#
# Four references across the seven groups name a GUID that is not in
# `Resources Images/` — two in Surah Al-Fateha, two in Wise Reminder. The file
# was lost years before this repo existed. The only decision left is whether the
# reader meets a broken icon or the sentence that surrounded it; the name goes in
# the report either way, which is what makes the removal the opposite of silent.


def test_a_lost_picture_is_lifted_out_and_the_prose_closes_over_it() -> None:
    body = "He drew this on the board.\n\n![](images/159/81ac3f0e-8abb-46bf-a82c-2e0023146ef2.jpg)\n\nThen he explained it."
    out = _without_image(body, "images/159/81ac3f0e-8abb-46bf-a82c-2e0023146ef2.jpg")
    assert out == "He drew this on the board.\n\nThen he explained it."


def test_lifting_one_picture_leaves_every_other_where_it_was() -> None:
    """A chapter carries up to nine of these. Removing the one that is missing
    must not disturb the eight that are present."""
    body = "![](images/87/a.jpg)\n\ntext\n\n![](images/87/b.jpg)"
    assert _without_image(body, "images/87/a.jpg") == "text\n\n![](images/87/b.jpg)"


def test_lifting_a_picture_keeps_its_alt_text_from_leaking_into_the_prose() -> None:
    """The alt is inside the construct being removed, not beside it."""
    body = "before\n\n![the seven heavens](images/87/a.jpg)\n\nafter"
    out = _without_image(body, "images/87/a.jpg")
    assert "seven heavens" not in out


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
