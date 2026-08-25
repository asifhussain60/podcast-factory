#!/usr/bin/env python3
"""_narration_plan.py — what the read-aloud narration NEEDS, and the publish step.

Extracted from ``reader_narration.py`` (DR-005 gate, 2026-08-25): adding the
planner and the publish-time step pushed that module to 620 lines, past the
600-line limit. Same pattern as ``_runlog.py``'s split from ``_progress.py`` —
extracted verbatim, and every name stays importable from ``reader_narration``
via re-export, so no existing caller or test changes.

The split is along a real seam rather than a convenient line number. Everything
here is a DECISION or a TRACE and touches no network: what a chapter needs, how
its speech text is derived, and how a step is recorded. ``reader_narration``
keeps the part that actually talks to Azure and writes audio. That is why this
module can be imported by anything, including a page load, without cost.

Dependency direction is one-way: ``reader_narration`` imports this, never the
reverse. ``narrate`` is the single exception and resolves it lazily inside the
function body, where it is wrapped anyway.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from _arabic_coverage import ARABIC_BODY
from _runlog import log_event

PHASE = "reader-narration"
MANIFEST_SCHEMA = 1

# `reader_narration` spelled these five ranges out itself and was on the
# `test_arabic_coverage` ratchet as `ESC, FULL` — a full re-declaration of the
# shared definition, which that list names as the cheapest kind to cure because
# it already agrees in value. Extracting this module was the "touched for another
# reason" the ratchet asks for, so it is cured here rather than carried across:
# `[{ARABIC_BODY}]+` is character-for-character the range that was inlined.
_ARABIC = re.compile(f"[{ARABIC_BODY}]+")
_ARABIC_PARENS = re.compile(rf"\([^)]*[{ARABIC_BODY}][^)]*\)")
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_IMAGE = re.compile(r"!\[[^\]]*]\([^)]+\)")
_TAG = re.compile(r"<[^>]+>")
_MARKDOWN_EDGE = re.compile(r"^[>*#\-\s]+")
_SPEAKABLE = re.compile(r"[A-Za-z0-9]")


@dataclass(frozen=True)
class Cue:
    idx: int
    blockIndex: int
    startS: float
    endS: float
    text: str


@dataclass(frozen=True)
class RenderSummary:
    outcome: str
    rendered: list[str]
    skipped: list[str]
    reason: str | None = None
    chars: int = 0
    failed: list[str] = field(default_factory=list)


#: What one chapter needs. `action` is one of:
#:   render  — synthesis is required, and `reason` says what changed
#:   current — the recording on disk matches this text in this voice
#:   silent  — there is nothing speakable here, so there is nothing to record
@dataclass(frozen=True)
class ChapterPlan:
    anchor: str
    title: str
    idx: int
    action: str
    reason: str
    digest: str
    blocks: int = 0
    #: Paragraphs with no cached clip — the ones this render actually buys.
    #: `blocks - stale_blocks` are reused from the paragraph cache for free.
    stale_blocks: int = 0


@dataclass(frozen=True)
class NarrationPlan:
    """What a render WOULD do, worked out without spending anything.

    Exists so a caller can report the cost of a run before committing to it —
    the Book Composer's publish quotes this before touching Azure — and so the
    same question has one answer whether it is being asked or acted on.
    """

    enabled: bool
    reason: str | None
    chapters: list[ChapterPlan] = field(default_factory=list)

    @property
    def render(self) -> list[ChapterPlan]:
        return [c for c in self.chapters if c.action == "render"]

    @property
    def current(self) -> list[ChapterPlan]:
        return [c for c in self.chapters if c.action == "current"]

    @property
    def silent(self) -> list[ChapterPlan]:
        return [c for c in self.chapters if c.action == "silent"]


def speech_text(markdown: str) -> str:
    text = _IMAGE.sub("", markdown)
    text = _LINK.sub(r"\1", text)
    text = _TAG.sub("", text)
    text = _ARABIC_PARENS.sub("", text)
    text = _ARABIC.sub("", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"[*_]{1,3}([^*_]+)[*_]{1,3}", r"\1", text)
    text = "\n".join(_MARKDOWN_EDGE.sub("", line).strip() for line in text.splitlines())
    text = re.sub(r"\s+", " ", text).strip()
    if not _SPEAKABLE.search(text):
        return ""
    return text


def chapter_blocks(markdown: str) -> list[tuple[int, str]]:
    blocks: list[tuple[int, str]] = []
    raw_blocks = re.split(r"\n\s*\n", _HTML_COMMENT.sub("", markdown).strip())
    for block_index, raw in enumerate(raw_blocks):
        text = speech_text(raw)
        if text:
            blocks.append((block_index, text))
    return blocks


def _source_hash(chapter_markdown: str, preset: dict[str, str]) -> str:
    payload = {
        "markdown": chapter_markdown,
        "preset": preset,
        "schema": MANIFEST_SCHEMA,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def block_hash(text: str, preset: dict[str, str]) -> str:
    """The identity of ONE spoken paragraph: its text in this voice.

    This is what makes an edit cost one paragraph instead of one chapter. The
    renderer already synthesised every paragraph as its own clip and then
    concatenated them — the clips were simply thrown away with the temp
    directory, so changing a word at the end of a chapter re-bought every
    paragraph above it. Keyed by content, so the cache needs no invalidation:
    a paragraph that changed asks for a name nothing has stored yet, and one
    that did not asks for the name its audio is already filed under.

    Deliberately NOT position-dependent. Inserting a paragraph must not
    re-record the ones after it, and two identical paragraphs — a repeated
    refrain, a shared formula — are the same audio and are bought once.
    """
    payload = {"text": text, "preset": preset, "schema": MANIFEST_SCHEMA}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:32]


def block_cache_dir(out_dir: Path) -> Path:
    """Where one book's paragraph clips live. Beside its chapter MP3s, so a book
    carries its own cache and `content/**/*.mp3` already keeps it out of git."""
    return Path(out_dir) / "_blocks"


def cached_clip(out_dir: Path, text: str, preset: dict[str, str]) -> Path:
    """The clip for this paragraph — the file's NAME is its content hash, so its
    existence is the entire cache lookup and there is nothing to invalidate."""
    return block_cache_dir(out_dir) / f"{block_hash(text, preset)}.mp3"


def plan_chapter(
    chapter: Any,
    *,
    manifest_chapters: dict[str, Any],
    preset: dict[str, str],
    out_dir: Path,
) -> ChapterPlan:
    """Decide what this chapter needs. THE single decision site.

    Both the planner and the renderer call this, so "does this chapter need
    re-recording" has exactly one answer. A second copy of this comparison —
    one to report and one to act on — is how a plan starts promising work the
    render does not do.

    The order below is load-bearing and preserved from the original inline
    check: an existing recording counts only when the text, the voice AND the
    file on disk all agree, and speakability gates every render path because
    the synthesiser cannot concatenate zero clips.
    """
    digest = _source_hash(chapter.markdown, preset)
    entry = manifest_chapters.get(chapter.anchor)
    entry = entry if isinstance(entry, dict) else {}
    audio = out_dir / f"{chapter.anchor}.mp3"
    common = {"anchor": chapter.anchor, "title": chapter.title, "idx": chapter.idx, "digest": digest}

    if entry.get("source_hash") == digest and entry.get("voice_id") == preset["voice"] and audio.exists():
        return ChapterPlan(action="current", reason="unchanged since it was recorded", **common)

    blocks = chapter_blocks(chapter.markdown)
    if not blocks:
        return ChapterPlan(action="silent", reason="no speakable text", **common)

    # How much of this chapter this render actually BUYS. A chapter is rebuilt
    # whole — the MP3 is one file — but only the paragraphs with no cached clip
    # reach Azure, so this, not `blocks`, is what the run costs.
    stale = sum(1 for _i, text in blocks if not cached_clip(out_dir, text, preset).exists())

    if not entry:
        why = "never recorded"
    elif entry.get("voice_id") != preset["voice"]:
        why = f"voice changed to {preset['voice']}"
    elif entry.get("source_hash") != digest:
        why = (
            f"{stale} of {len(blocks)} paragraph(s) changed"
            if stale
            else "text changed since it was recorded (every paragraph is cached)"
        )
    else:
        why = "recording is missing from disk"
    return ChapterPlan(action="render", reason=why, blocks=len(blocks), stale_blocks=stale, **common)


def _trace(event: str, *, book_dir: Path, log: Any, level: str = "info", msg: str = "", **fields: Any) -> None:
    """One narration step, to the caller's console AND the run timeline.

    Both from a single call, so a step cannot be traceable in one and invisible
    in the other. `log_event` never raises by contract; the console callback is
    wrapped for the same reason — a caller's logger must not be able to fail a
    render that was otherwise going to succeed.
    """
    if log is not None and msg:
        try:
            log(msg)
        except Exception:
            pass
    log_event(event, book_dir=book_dir, phase=PHASE, level=level, msg=msg, **fields)


def narrate(book_dir: Path, args: Any, report: Any) -> dict:
    """Re-record the chapters whose text changed. Never fatal. The publish step.

    THIS IS WHAT MAKES THE PUBLISH BUTTON HONEST. Editing a chapter on the
    compose tab lights the button and publishes the new text; until this step
    existed the chapter's MP3 went on speaking the words that had been replaced,
    and nothing anywhere reported the divergence. `render_reader_narration` was
    reachable only from the orchestrator's one-time pipeline run, so every edit
    made after a book first shipped left its audio behind.

    Called BEFORE the content push and outside the per-target loop, for two
    reasons that are both load-bearing:

      * `publish_to_listener` reads `book/narration/manifest.json` off disk, so a
        recording written after the push cannot be carried by it; and
      * the re-recorded MP3 has a new sha256, which is what resets that asset's
        `uploaded_at` to NULL in the media_asset upsert, which is in turn the only
        reason `upload_listener_media` (which selects `uploaded_at IS NULL`) picks
        it up. Regenerate after the push and the new audio never reaches R2.

    Cost is bounded by the same hash the renderer records: only chapters whose
    text or voice actually moved reach Azure, so re-publishing an unedited book
    is free. The plan is reported BEFORE anything is spent.

    NON-FATAL, like the transcripts step above it, and unlike the orchestrator's
    driver which halts on the same failure. The two callers face different ways
    on purpose: the pipeline is unattended and should stop rather than ship a
    half-narrated book, whereas this run is a person who has already approved
    this text going live. A speech outage should not hold back the words; the
    chapter keeps the recording it had, the failure is named, and because the
    manifest entry is dropped the next publish retries exactly that chapter.
    """
    report.step("Read-aloud narration")
    outcome: dict = {"attempted": False}

    if getattr(args, "skip_narration", False):
        report.log("skipped, as asked — chapters keep the recordings they have")
        return {**outcome, "skipped": "asked"}

    try:
        from reader_narration import narration_plan, render_reader_narration
    except Exception as error:
        report.warn(f"narration is unavailable, continuing without it: {error}")
        return {**outcome, "skipped": "unavailable"}

    try:
        plan = narration_plan(book_dir)
    except Exception as error:
        report.warn(f"could not work out what needs re-recording, continuing: {error}")
        return {**outcome, "skipped": "unplannable"}

    if not plan.enabled:
        report.log(f"not narrated: {plan.reason}")
        return {**outcome, "skipped": plan.reason}

    stale = sum(c.stale_blocks for c in plan.render)
    total = sum(c.blocks for c in plan.render)
    report.log(
        f"{len(plan.render)} chapter(s) to re-record, {len(plan.current)} already current"
        + (f", {len(plan.silent)} with nothing speakable" if plan.silent else "")
    )
    if plan.render:
        report.log(f"{stale} of {total} paragraph(s) need synthesis — the rest are reused from the paragraph cache")
    for chapter in plan.render:
        report.log(f"  will record: {chapter.title} — {chapter.reason}")

    if not plan.render:
        report.log("every chapter's recording matches its text — nothing to do")
        return {**outcome, "rendered": 0}

    if getattr(args, "dry_run", False):
        report.log("dry run — no audio was synthesised")
        return {**outcome, "dryRun": True, "planned": len(plan.render)}

    try:
        result = render_reader_narration(book_dir, log=report.log)
    except Exception as error:
        report.warn(f"narration failed, continuing — chapters keep their existing audio: {error}")
        return {**outcome, "attempted": True, "error": str(error)}

    for anchor in result.failed:
        report.warn(f"could not record '{anchor}' — it keeps its previous audio and will be retried next publish")
    report.log(f"recorded {len(result.rendered)} chapter(s), {result.chars} characters synthesised")

    # A re-recorded chapter reaches readers only once its file is in the bucket.
    # `--skip-media` is a legitimate thing to ask for, but combined with new audio
    # it leaves the database describing a recording R2 does not yet hold, and that
    # is worth saying out loud rather than discovering as a chapter that reads new
    # and sounds old.
    if result.rendered and getattr(args, "skip_media", False):
        report.warn(
            f"{len(result.rendered)} chapter(s) were re-recorded but --skip-media means they were NOT uploaded — "
            "run again without --skip-media to put the new audio in the bucket"
        )

    return {**outcome, "attempted": True, "rendered": len(result.rendered), "failed": result.failed}
