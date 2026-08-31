"""What has to be true before a paragraph is allowed to light up.

The gate this replaces asked one question — what share of transcript cues could
support their own placement — and answered it with a threshold of 0.55. That
number falls as cues get SHORTER relative to paragraphs, which is a fact about
subtitle granularity and not about whether the pairing is right. It worked while
every session book was one chapter per recording; `purification-of-the-heart` is
twenty-four chapters across two ten-hour recordings, and every chapter scored
0.22-0.52 while being placed in perfect order with 94-100% of paragraphs timed.

So half of these cases are about the conditions catching a real mis-pairing, and
half are about them NOT refusing work that is demonstrably correct.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _cue_gate import CONDITIONS, MIN_COVERAGE, Timing, verdict  # noqa: E402


def _cues(*spans: tuple[float, float]) -> list[dict]:
    return [{"idx": i, "blockIndex": i, "startS": a, "endS": b, "text": "x"} for i, (a, b) in enumerate(spans)]


def _timing(**kw) -> Timing:
    base = dict(paragraphs=3, cues=_cues((0, 5), (5, 10), (10, 15)), monotonic=True, recording_s=100.0)
    base.update(kw)
    return Timing(**base)


# ── a clean chapter publishes ────────────────────────────────────────────────
def test_a_correctly_timed_chapter_passes():
    call = verdict(_timing())
    assert call.ok
    assert call.failures == []


def test_every_condition_is_asked_even_on_a_pass():
    """A pass has to be as legible as a refusal — otherwise nobody can tell
    whether a condition ran or was skipped."""
    assert verdict(_timing()).checked == [name for name, _q, _c in CONDITIONS]


# ── the mistake the gate exists for ──────────────────────────────────────────
def test_a_paragraph_timed_before_the_one_above_it_is_refused():
    """The whole failure: a paragraph lit while a different one is spoken."""
    call = verdict(_timing(cues=_cues((0, 5), (30, 35), (10, 15))))
    assert not call.ok
    assert any("paragraphs-in-order" in f for f in call.failures)


def test_an_alignment_that_ran_backwards_is_refused():
    call = verdict(_timing(monotonic=False))
    assert not call.ok
    assert any("alignment-held" in f for f in call.failures)


def test_a_paragraph_that_ends_before_it_begins_is_refused():
    call = verdict(_timing(cues=_cues((0, 5), (20, 10), (25, 30))))
    assert any("spans-run-forward" in f for f in call.failures)


def test_a_chapter_timed_past_the_end_of_its_recording_is_refused():
    call = verdict(_timing(recording_s=12.0))
    assert any("within-the-recording" in f for f in call.failures)


def test_a_chapter_that_begins_inside_the_one_before_it_is_refused():
    call = verdict(_timing(before_end_s=60.0))
    assert any("clear-of-neighbours" in f for f in call.failures)


def test_a_chapter_that_runs_into_the_one_after_it_is_refused():
    call = verdict(_timing(after_start_s=2.0))
    assert any("clear-of-neighbours" in f for f in call.failures)


def test_a_chapter_with_no_timings_at_all_is_refused():
    call = verdict(_timing(cues=[]))
    assert not call.ok
    assert any("has-timings" in f for f in call.failures)


def test_a_half_timed_chapter_is_refused():
    """Highlighting that stops for half the chapter is worse than none."""
    call = verdict(_timing(paragraphs=10))
    assert any("coverage" in f for f in call.failures)


# ── what must NOT be refused ─────────────────────────────────────────────────
def test_the_cue_score_is_not_a_condition():
    """The number that refused all twenty-four correct chapters is no longer
    part of the decision — it is a diagnostic the manifest still records."""
    assert not any("score" in name or "confidence" in name for name, _q, _c in CONDITIONS)


def test_a_chapter_at_exactly_the_coverage_floor_passes():
    call = verdict(_timing(paragraphs=int(3 / MIN_COVERAGE)))
    assert call.ok


def test_touching_neighbours_is_not_an_overlap():
    """The recordings run continuously; the seam between two chapters is a
    sentence, not a cut. A strict inequality would refuse correct work for
    sharing a second."""
    assert verdict(_timing(before_end_s=1.0, after_start_s=15.5)).ok


def test_a_chapter_with_no_neighbours_is_not_penalised_for_it():
    assert verdict(_timing(before_end_s=None, after_start_s=None)).ok


def test_an_unknown_recording_length_makes_no_claim():
    """Duration is read off the audio file; when that fails it must not become
    evidence that the timings are wrong."""
    assert verdict(_timing(recording_s=0.0)).ok


def test_every_failure_names_its_condition():
    """A chapter published without highlighting has to say which property
    failed — a percentage is not something anyone can act on."""
    call = verdict(_timing(monotonic=False, cues=_cues((0, 5), (30, 35), (10, 15))))
    assert len(call.failures) >= 2
    for failure in call.failures:
        assert failure.split(":")[0] in {name for name, _q, _c in CONDITIONS}


# ── the books already published this way ─────────────────────────────────────
def test_the_session_books_already_shipped_still_pass_the_new_conditions():
    """`surah-al-fateha` and `love-of-the-prophet` were timed and published under
    the cue-score gate. Replacing that gate must not make their existing timings
    unpublishable — a new rule that refuses shipped, correct work is a
    regression however well it reads."""
    import json

    content = Path(__file__).resolve().parents[3] / "content" / "Sessions"
    seen = 0
    for slug in ("surah-al-fateha", "love-of-the-prophet"):
        path = content / slug / "book" / "narration" / "manifest.json"
        if not path.is_file():
            continue
        for chapter in json.loads(path.read_text(encoding="utf-8")).get("chapters", {}).values():
            cues = chapter.get("cues") or []
            if not cues:
                continue
            seen += 1
            call = verdict(
                Timing(
                    paragraphs=len(cues),
                    cues=cues,
                    monotonic=True,
                    recording_s=chapter.get("duration_s") or 0.0,
                )
            )
            assert call.ok, f"{slug}/{chapter.get('title')}: {call.reason}"
    assert seen, "no published session timings were found to check"


# ── the condition the first real run needed ──────────────────────────────────
def test_a_paragraph_holding_unmatched_audio_is_refused():
    """The aligner must place every cue somewhere, so audio matching nothing in
    the book piles onto the nearest paragraph — usually the first. On the real
    run, paragraph one of "Love of the World" spanned 137 minutes against a
    median of one, and every other condition passed it: it looks like a timing
    and behaves as a bucket, leaving one paragraph lit for two hours."""
    swallowed = _cues((0, 8220), (8220, 8280), (8280, 8340), (8340, 8400))
    call = verdict(_timing(paragraphs=4, cues=swallowed, recording_s=9000.0))
    assert not call.ok
    assert any("no-paragraph-swallows-the-chapter" in f for f in call.failures)


def test_an_ordinarily_long_paragraph_is_not_refused():
    """A paragraph several times the median is normal speech. The condition
    catches the absurd, not the long — measured chapters run to 4-5x."""
    spans = _cues((0, 60), (60, 120), (120, 400), (400, 460), (460, 520))
    call = verdict(_timing(paragraphs=5, cues=spans, recording_s=600.0))
    assert call.ok


def test_a_chapter_too_short_to_have_a_typical_paragraph_makes_no_claim():
    """With two paragraphs there is no median to be disproportionate to."""
    assert verdict(_timing(paragraphs=2, cues=_cues((0, 5), (5, 4000)), recording_s=9000.0)).ok
