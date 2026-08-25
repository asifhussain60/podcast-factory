#!/usr/bin/env python3
"""The Book Composer's publish re-records the chapters whose text changed.

Editing a chapter on the compose tab published the new text and left the
chapter's MP3 speaking the words it replaced: `render_reader_narration` was
reachable only from the orchestrator's one-time pipeline run, so every edit made
after a book first shipped left its audio behind, silently. These tests pin the
step that closes that, and — as much as the step itself — the ORDER and the
FAILURE DIRECTIONS around it, which are the parts that are easy to regress and
impossible to notice.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _narration_plan  # noqa: E402
import _progress  # noqa: E402
import reader_narration as rn  # noqa: E402
from phases import reader_narration_driver  # noqa: E402

TWO_CHAPTERS = (
    "# Sample Book\n\n"
    "## 1. Opening\n\n"
    "The first paragraph of the opening.\n\n"
    "## 2. Second\n\n"
    "The first paragraph of the second chapter.\n"
)


def make_book(tmp_path: Path, *, body: str = TWO_CHAPTERS, profile: str = "islamic_scholarly") -> Path:
    book = tmp_path / "content" / "Islamic" / "sample-book"
    (book / "_system").mkdir(parents=True)
    (book / "book").mkdir()
    (book / "_system" / "series-config.yaml").write_text(
        f"content_profile: {profile}\nreader_narration:\n  voice: jenny\n", encoding="utf-8"
    )
    (book / "book" / "book.md").write_text(body, encoding="utf-8")
    return book


def fake_azure(durations=None):
    """Patch out everything that costs money or touches ffmpeg."""
    seq = iter(durations or [1.0] * 200)
    return (
        mock.patch.object(rn, "synthesize_text", side_effect=lambda text, preset: b"AUDIO"),
        mock.patch.object(rn, "audio_duration_seconds", side_effect=lambda _p: next(seq)),
        mock.patch.object(rn, "concat_audio", side_effect=lambda parts, out: out.write_bytes(b"MP3")),
        mock.patch.object(rn, "append_azure_speech_cost"),
    )


def render(book: Path, **kw):
    a, b, c, d = fake_azure()
    with a, b, c, d as cost:
        return rn.render_reader_narration(book, **kw), cost


class Recorder:
    """Stands in for publish_to_production.Reporter, keeping what it was told."""

    def __init__(self) -> None:
        self.steps: list[str] = []
        self.logs: list[str] = []
        self.warns: list[str] = []

    def step(self, name: str) -> None:
        self.steps.append(name)

    def log(self, text: str) -> None:
        self.logs.append(text)

    def warn(self, text: str) -> None:
        self.warns.append(text)

    @property
    def said(self) -> str:
        return "\n".join(self.logs + self.warns)


def args(**kw) -> SimpleNamespace:
    base = {"skip_narration": False, "dry_run": False, "skip_media": False}
    return SimpleNamespace(**{**base, **kw})


# ── sunshine ──────────────────────────────────────────────────────────────────


def test_editing_one_chapter_re_records_only_that_chapter(tmp_path: Path) -> None:
    """THE defect this exists for. An edit must re-record its own chapter, and
    must NOT re-record the chapter next to it — that distinction is the whole
    cost argument for doing this on every publish."""
    book = make_book(tmp_path)
    first, _ = render(book)
    assert sorted(first.rendered) == ["opening", "second"]

    edited = TWO_CHAPTERS.replace("The first paragraph of the opening.", "Completely rewritten opening text.")
    (book / "book" / "book.md").write_text(edited, encoding="utf-8")

    report = Recorder()
    with mock.patch.object(rn, "synthesize_text", side_effect=lambda t, p: b"AUDIO"), mock.patch.object(
        rn, "audio_duration_seconds", return_value=1.0
    ), mock.patch.object(rn, "concat_audio", side_effect=lambda parts, out: out.write_bytes(b"MP3")), mock.patch.object(
        rn, "append_azure_speech_cost"
    ):
        result = _narration_plan.narrate(book, args(), report)

    assert result["rendered"] == 1
    assert "will record: 1. Opening" in report.said
    assert "1 of 1 paragraph(s) changed" in report.said
    manifest = json.loads((book / "book" / "narration" / "manifest.json").read_text())
    assert set(manifest["chapters"]) == {"opening", "second"}


def test_an_unedited_book_costs_nothing(tmp_path: Path) -> None:
    """Re-publishing a book nobody touched must not reach Azure at all — this is
    what makes the step safe to run on every single publish."""
    book = make_book(tmp_path)
    render(book)

    report = Recorder()
    with mock.patch.object(rn, "synthesize_text", side_effect=AssertionError("must not synthesise")):
        result = _narration_plan.narrate(book, args(), report)

    assert result["rendered"] == 0
    assert "nothing to do" in report.said


def test_the_plan_costs_nothing_and_matches_what_the_render_does(tmp_path: Path) -> None:
    """The plan and the render share `plan_chapter`, so what is promised and what
    happens cannot drift. A second copy of that comparison is the bug this guards."""
    book = make_book(tmp_path)
    plan = rn.narration_plan(book)
    assert [c.anchor for c in plan.render] == ["opening", "second"]
    assert plan.current == [] and plan.silent == []

    with mock.patch.object(rn, "synthesize_text", side_effect=AssertionError("planning must not synthesise")):
        rn.narration_plan(book)

    result, _ = render(book)
    assert sorted(result.rendered) == sorted(c.anchor for c in plan.render)


def test_a_missing_mp3_is_re_recorded_even_though_the_text_is_unchanged(tmp_path: Path) -> None:
    """MP3s are gitignored (`content/**/*.mp3`) while the manifest is tracked, so
    a fresh clone has every hash and no audio. The file's absence must win over
    the hash's agreement or that book publishes rows pointing at nothing."""
    book = make_book(tmp_path)
    render(book)
    (book / "book" / "narration" / "opening.mp3").unlink()

    plan = rn.narration_plan(book)
    assert [c.anchor for c in plan.render] == ["opening"]
    assert plan.render[0].reason == "recording is missing from disk"


def test_changing_the_voice_re_records_the_whole_book(tmp_path: Path) -> None:
    book = make_book(tmp_path)
    render(book)
    cfg = book / "_system" / "series-config.yaml"
    cfg.write_text(cfg.read_text().replace("voice: jenny", "voice: aria"), encoding="utf-8")

    plan = rn.narration_plan(book)
    assert [c.anchor for c in plan.render] == ["opening", "second"]
    assert all("voice changed" in c.reason for c in plan.render)


def test_every_step_is_traced_to_the_run_timeline(tmp_path: Path) -> None:
    """The trace is the point of the logging: a publish that ran unattended has to
    be explicable afterwards with no console to scroll back to."""
    book = make_book(tmp_path)
    events: list[tuple] = []
    with mock.patch.object(_narration_plan, "log_event", side_effect=lambda e, **k: events.append((e, k))):
        render(book)

    names = [e for e, _ in events]
    assert names[0] == "narration.plan"
    assert names.count("narration.chapter.start") == 2
    assert names.count("narration.chapter.done") == 2
    assert names[-1] == "narration.done"
    assert all(k.get("phase") == "reader-narration" for _, k in events)

    plan_event = next(k for e, k in events if e == "narration.plan")
    assert sorted(plan_event["to_render"]) == ["opening", "second"]
    done = next(k for e, k in events if e == "narration.done")
    assert sorted(done["rendered"]) == ["opening", "second"] and done["failed"] == []


def test_the_console_log_receives_each_step_too(tmp_path: Path) -> None:
    book = make_book(tmp_path)
    seen: list[str] = []
    a, b, c, d = fake_azure()
    with a, b, c, d:
        rn.render_reader_narration(book, log=seen.append)

    joined = "\n".join(seen)
    assert "2 chapter(s) to record" in joined
    # The ordinal is part of `Chapter.title` and deliberately not part of
    # `anchor` — the log names chapters the way the book prints them.
    assert "recording 1. Opening" in joined and "recording 2. Second" in joined
    assert "recorded 1. Opening" in joined
    assert "narration finished: 2 recorded" in joined


# ── paragraph-level reuse ─────────────────────────────────────────────────────

FOUR_PARAS = (
    "# Sample Book\n\n"
    "## 1. Opening\n\n"
    "Paragraph one of the opening.\n\n"
    "Paragraph two of the opening.\n\n"
    "Paragraph three of the opening.\n\n"
    "Paragraph four of the opening.\n"
)


def spy_render(book: Path, **kw):
    """Render while recording exactly which paragraph texts reached Azure."""
    spoken: list[str] = []

    def synth(text, preset):
        spoken.append(text)
        return b"AUDIO"

    with mock.patch.object(rn, "synthesize_text", side_effect=synth), mock.patch.object(
        rn, "audio_duration_seconds", return_value=1.0
    ), mock.patch.object(rn, "concat_audio", side_effect=lambda p, out: out.write_bytes(b"MP3")), mock.patch.object(
        rn, "append_azure_speech_cost"
    ) as cost:
        result = rn.render_reader_narration(book, **kw)
    return result, spoken, cost


def test_editing_one_paragraph_re_synthesises_only_that_paragraph(tmp_path: Path) -> None:
    """THE efficiency requirement. A chapter is rebuilt whole because its MP3 is
    one file, but only the changed paragraph may be BOUGHT."""
    book = make_book(tmp_path, body=FOUR_PARAS)
    _first, spoken, _ = spy_render(book)
    assert len(spoken) == 4, "the first render buys every paragraph"

    edited = FOUR_PARAS.replace("Paragraph three of the opening.", "A completely new third paragraph.")
    (book / "book" / "book.md").write_text(edited, encoding="utf-8")

    result, spoken, cost = spy_render(book)

    assert spoken == ["A completely new third paragraph."], "only the edited paragraph may reach Azure"
    assert result.rendered == ["opening"], "the chapter is still rebuilt as one file"
    assert result.chars == len("A completely new third paragraph.")
    # The ledger must bill the paragraph, not the chapter.
    assert cost.call_args.kwargs["char_count"] == len("A completely new third paragraph.")


def test_the_rebuilt_chapter_still_covers_every_paragraph_in_order(tmp_path: Path) -> None:
    """Reuse must not cost coverage: the cues still describe the whole chapter,
    and the concat still receives one clip per paragraph, in reading order."""
    book = make_book(tmp_path, body=FOUR_PARAS)
    spy_render(book)
    edited = FOUR_PARAS.replace("Paragraph two of the opening.", "Replacement second paragraph.")
    (book / "book" / "book.md").write_text(edited, encoding="utf-8")

    joined: list[list[Path]] = []
    with mock.patch.object(rn, "synthesize_text", side_effect=lambda t, p: b"AUDIO"), mock.patch.object(
        rn, "audio_duration_seconds", return_value=1.0
    ), mock.patch.object(
        rn, "concat_audio", side_effect=lambda parts, out: (joined.append(list(parts)), out.write_bytes(b"MP3"))[1]
    ), mock.patch.object(rn, "append_azure_speech_cost"):
        rn.render_reader_narration(book)

    manifest = json.loads((book / "book" / "narration" / "manifest.json").read_text())
    cues = manifest["chapters"]["opening"]["cues"]
    assert [c["text"] for c in cues] == [
        "Paragraph one of the opening.",
        "Replacement second paragraph.",
        "Paragraph three of the opening.",
        "Paragraph four of the opening.",
    ]
    assert [c["startS"] for c in cues] == [0.0, 1.0, 2.0, 3.0]
    assert len(joined[0]) == 4, "every paragraph, reused or bought, is concatenated"


def test_inserting_a_paragraph_does_not_re_buy_the_ones_after_it(tmp_path: Path) -> None:
    """The clip name is content, never position — otherwise inserting near the
    top of a chapter would re-buy everything below it."""
    book = make_book(tmp_path, body=FOUR_PARAS)
    spy_render(book)

    edited = FOUR_PARAS.replace(
        "Paragraph one of the opening.", "Paragraph one of the opening.\n\nA brand new inserted paragraph."
    )
    (book / "book" / "book.md").write_text(edited, encoding="utf-8")
    _result, spoken, _ = spy_render(book)

    assert spoken == ["A brand new inserted paragraph."]


def test_a_repeated_paragraph_is_bought_once(tmp_path: Path) -> None:
    body = "# B\n\n## 1. Opening\n\nA repeated refrain.\n\nSomething else.\n\nA repeated refrain.\n"
    book = make_book(tmp_path, body=body)
    _result, spoken, _ = spy_render(book)

    assert sorted(spoken) == ["A repeated refrain.", "Something else."]


def test_the_plan_prices_the_edit_in_paragraphs_before_spending(tmp_path: Path) -> None:
    """The publish panel quotes this before touching Azure, so it has to be the
    real number rather than the chapter's paragraph count."""
    book = make_book(tmp_path, body=FOUR_PARAS)
    spy_render(book)
    edited = FOUR_PARAS.replace("Paragraph four of the opening.", "Rewritten fourth paragraph.")
    (book / "book" / "book.md").write_text(edited, encoding="utf-8")

    plan = rn.narration_plan(book)
    chapter = plan.render[0]
    assert (chapter.blocks, chapter.stale_blocks) == (4, 1)
    assert chapter.reason == "1 of 4 paragraph(s) changed"

    report = Recorder()
    with mock.patch.object(rn, "synthesize_text", side_effect=AssertionError("must not synthesise")):
        _narration_plan.narrate(book, args(dry_run=True), report)
    assert "1 of 4 paragraph(s) need synthesis" in report.said


def test_paragraph_clips_for_deleted_text_are_pruned(tmp_path: Path) -> None:
    """The cache must not grow without bound across a book's editing life."""
    book = make_book(tmp_path, body=FOUR_PARAS)
    spy_render(book)
    cache = rn.block_cache_dir(book / "book" / "narration")
    assert len(list(cache.glob("*.mp3"))) == 4

    shorter = FOUR_PARAS.replace("Paragraph three of the opening.\n\n", "").replace(
        "Paragraph four of the opening.\n", ""
    )
    (book / "book" / "book.md").write_text(shorter, encoding="utf-8")
    spy_render(book)

    assert len(list(cache.glob("*.mp3"))) == 2, "clips for deleted paragraphs go"


def test_pruning_keeps_the_clips_of_chapters_this_run_did_not_touch(tmp_path: Path) -> None:
    """An untouched chapter's paragraphs must survive, or editing it later would
    re-buy the whole thing — the exact cost this cache exists to avoid."""
    book = make_book(tmp_path)  # two chapters, one paragraph each
    spy_render(book)
    cache = rn.block_cache_dir(book / "book" / "narration")
    assert len(list(cache.glob("*.mp3"))) == 2

    edited = TWO_CHAPTERS.replace("The first paragraph of the opening.", "Rewritten opening.")
    (book / "book" / "book.md").write_text(edited, encoding="utf-8")
    spy_render(book)

    # The untouched second chapter's clip is still cached, so it is free later.
    assert len(list(cache.glob("*.mp3"))) == 2
    _result, spoken, _ = spy_render(book)
    assert spoken == [], "nothing changed, so nothing is bought"


def test_the_paragraph_cache_is_never_uploaded_to_the_bucket(tmp_path: Path) -> None:
    """The cache is a local working file, not a deliverable. A broad glob over
    `book/narration/` would quietly start shipping hundreds of paragraph clips to
    R2 alongside each chapter — pinned here because nothing else would notice."""
    from _listener_book import Book, split_chapters
    from _listener_media import collect_media

    book = make_book(tmp_path, body=FOUR_PARAS)
    spy_render(book)
    assert len(list(rn.block_cache_dir(book / "book" / "narration").glob("*.mp3"))) == 4

    blank = dict.fromkeys(("bucket", "title_arabic", "title_language", "study_track", "blurb", "edition_note"), "")
    inventory = Book(
        slug="sample-book",
        directory=book,
        title="Sample",
        chapters=split_chapters((book / "book" / "book.md").read_text(encoding="utf-8")),
        **blank,
    )
    collect_media(inventory)

    keys = [a.key for a in inventory.assets]
    assert keys == ["sample-book/narration/opening.mp3"], keys
    assert not any("_blocks" in k for k in keys)


def test_a_corrupt_cached_clip_is_re_bought_rather_than_failing_the_chapter(tmp_path: Path) -> None:
    """A truncated clip must not be trusted (that publishes silence) and must not
    fail the publish either.

    The cache is only consulted while REBUILDING a chapter — a chapter whose own
    MP3 is current never looks at it — so the corruption is staged alongside an
    edit, which is the only way a reader could ever meet it.
    """
    book = make_book(tmp_path, body=FOUR_PARAS)
    spy_render(book)

    cache = rn.block_cache_dir(book / "book" / "narration")
    unchanged = rn.cached_clip(book / "book" / "narration", "Paragraph one of the opening.", rn.VOICE_PRESETS["jenny"])
    assert unchanged.exists()
    unchanged.write_bytes(b"")  # truncated on disk

    edited = FOUR_PARAS.replace("Paragraph four of the opening.", "A rewritten fourth paragraph.")
    (book / "book" / "book.md").write_text(edited, encoding="utf-8")

    def probe(path: Path) -> float:
        if path == unchanged and path.read_bytes() == b"":
            raise RuntimeError("moov atom not found")
        return 1.0

    spoken: list[str] = []
    with mock.patch.object(
        rn, "synthesize_text", side_effect=lambda t, p: (spoken.append(t), b"AUDIO")[1]
    ), mock.patch.object(rn, "audio_duration_seconds", side_effect=probe), mock.patch.object(
        rn, "concat_audio", side_effect=lambda p, out: out.write_bytes(b"MP3")
    ), mock.patch.object(rn, "append_azure_speech_cost"):
        result = rn.render_reader_narration(book)

    assert result.rendered == ["opening"] and result.failed == []
    # The edited paragraph AND the corrupt one — and nothing else.
    assert sorted(spoken) == ["A rewritten fourth paragraph.", "Paragraph one of the opening."]
    assert len(list(cache.glob("*.mp3"))) == 4


# ── rainy ─────────────────────────────────────────────────────────────────────


def test_a_speech_failure_is_isolated_and_the_other_chapters_survive(tmp_path: Path) -> None:
    """One chapter failing must not cost the chapters already recorded, and must
    not leave a truncated MP3 that the next run would mistake for a finished one."""
    book = make_book(tmp_path)

    def flaky(text, preset):
        if "second chapter" in text:
            raise RuntimeError("Azure said no")
        return b"AUDIO"

    with mock.patch.object(rn, "synthesize_text", side_effect=flaky), mock.patch.object(
        rn, "audio_duration_seconds", return_value=1.0
    ), mock.patch.object(rn, "concat_audio", side_effect=lambda p, out: out.write_bytes(b"MP3")), mock.patch.object(
        rn, "append_azure_speech_cost"
    ):
        result = rn.render_reader_narration(book)

    assert result.rendered == ["opening"]
    assert result.failed == ["second"]
    assert (book / "book" / "narration" / "opening.mp3").exists()
    assert not (book / "book" / "narration" / "second.mp3").exists()
    manifest = json.loads((book / "book" / "narration" / "manifest.json").read_text())
    assert "second" not in manifest["chapters"], "a failed chapter must not keep a manifest entry"


def test_the_failed_chapter_is_retried_on_the_next_run(tmp_path: Path) -> None:
    """Dropping the manifest entry is what makes the retry automatic rather than
    something a person has to remember."""
    book = make_book(tmp_path)
    calls = {"n": 0}

    def flaky(text, preset):
        if "second chapter" in text:
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("transient")
        return b"AUDIO"

    for _ in range(2):
        with mock.patch.object(rn, "synthesize_text", side_effect=flaky), mock.patch.object(
            rn, "audio_duration_seconds", return_value=1.0
        ), mock.patch.object(rn, "concat_audio", side_effect=lambda p, out: out.write_bytes(b"MP3")), mock.patch.object(
            rn, "append_azure_speech_cost"
        ):
            result = rn.render_reader_narration(book)

    assert result.rendered == ["second"] and result.failed == []


def test_the_publish_treats_a_narration_failure_as_non_fatal(tmp_path: Path) -> None:
    """A person has already approved this text going live; a speech outage must
    not hold the words back. The opposite call from the orchestrator, on purpose."""
    book = make_book(tmp_path)
    report = Recorder()
    with mock.patch.object(rn, "render_reader_narration", side_effect=RuntimeError("Azure is down")):
        result = _narration_plan.narrate(book, args(), report)

    assert result["error"] == "Azure is down"
    assert "continuing" in report.said
    assert report.warns, "a swallowed failure must still be reported"


def test_the_orchestrator_treats_the_same_failure_as_fatal(tmp_path: Path) -> None:
    """The unattended pipeline must HALT rather than ship a half-narrated book.
    Pinned because per-chapter isolation could easily have made it silent."""
    book = make_book(tmp_path)
    _progress.write_state(book, _progress.initial_state("sample-book", "books"))
    summary = rn.RenderSummary(outcome="completed", rendered=["opening"], skipped=[], failed=["second"])

    with mock.patch.object(reader_narration_driver, "render_reader_narration", return_value=summary), mock.patch.object(
        reader_narration_driver, "phase_git_commit"
    ) as commit:
        outcome, rc = reader_narration_driver.drive_reader_narration(book)

    assert (outcome, rc) == ("failed", 2)
    state = _progress.read_state(book)
    assert state["phases"]["reader-narration"]["status"] == "failed"
    assert "second" in state["last_error"]["message"]
    commit.assert_not_called()


def test_a_dry_run_spends_nothing_but_still_says_what_it_would_do(tmp_path: Path) -> None:
    book = make_book(tmp_path)
    report = Recorder()
    with mock.patch.object(rn, "synthesize_text", side_effect=AssertionError("dry run must not synthesise")):
        result = _narration_plan.narrate(book, args(dry_run=True), report)

    assert result["dryRun"] is True and result["planned"] == 2
    assert "will record" in report.said
    assert not (book / "book" / "narration").exists()


def test_skip_narration_leaves_the_audio_alone(tmp_path: Path) -> None:
    book = make_book(tmp_path)
    report = Recorder()
    with mock.patch.object(rn, "synthesize_text", side_effect=AssertionError("must not synthesise")):
        result = _narration_plan.narrate(book, args(skip_narration=True), report)

    assert result["skipped"] == "asked"


def test_a_book_that_is_not_narrated_is_skipped_cleanly(tmp_path: Path) -> None:
    book = make_book(tmp_path, profile="technical")
    report = Recorder()
    with mock.patch.object(rn, "synthesize_text", side_effect=AssertionError("must not synthesise")):
        result = _narration_plan.narrate(book, args(), report)

    assert "not an Islamic source book" in str(result["skipped"])
    assert "not narrated" in report.said


def test_a_corrupt_manifest_re_records_rather_than_crashing(tmp_path: Path) -> None:
    """The failure direction matters: an unreadable manifest must mean "record
    again", never "assume it is current" and never a traceback mid-publish."""
    book = make_book(tmp_path)
    render(book)
    (book / "book" / "narration" / "manifest.json").write_text("{not json", encoding="utf-8")

    plan = rn.narration_plan(book)
    assert [c.anchor for c in plan.render] == ["opening", "second"]
    assert all(c.reason == "never recorded" for c in plan.render)


def test_skip_media_with_new_audio_is_called_out(tmp_path: Path) -> None:
    """New audio on disk that never reached the bucket leaves the database
    describing a recording R2 does not hold — worth saying, not discovering."""
    book = make_book(tmp_path)
    report = Recorder()
    a, b, c, d = fake_azure()
    with a, b, c, d:
        _narration_plan.narrate(book, args(skip_media=True), report)

    assert any("NOT uploaded" in w for w in report.warns)


def test_a_chapter_with_nothing_speakable_is_never_sent_to_azure(tmp_path: Path) -> None:
    """`concat_audio` cannot join zero clips, so speakability has to gate every
    render path — including the one reached when the MP3 is missing."""
    body = "# B\n\n## 1. Silent\n\n(الإمامة)\n\n## 2. Real\n\nActual words here.\n"
    book = make_book(tmp_path, body=body)

    plan = rn.narration_plan(book)
    assert [c.anchor for c in plan.silent] == ["silent"]
    assert [c.anchor for c in plan.render] == ["real"]

    result, _ = render(book)
    assert result.rendered == ["real"] and "silent" in result.skipped


def test_a_broken_console_logger_cannot_fail_the_render(tmp_path: Path) -> None:
    """Observability must never turn a working render into a failed one."""
    book = make_book(tmp_path)

    def explode(_msg):
        raise RuntimeError("the panel went away")

    a, b, c, d = fake_azure()
    with a, b, c, d:
        result = rn.render_reader_narration(book, log=explode)

    assert sorted(result.rendered) == ["opening", "second"] and result.failed == []


def test_a_book_with_no_reading_edition_is_skipped(tmp_path: Path) -> None:
    book = make_book(tmp_path)
    (book / "book" / "book.md").unlink()

    plan = rn.narration_plan(book)
    assert plan.enabled is False and plan.reason == "no reading edition"

    result, _ = render(book)
    assert result.outcome == "skipped" and result.reason == "no reading edition"
