"""Chapter read-aloud audio for the Podcast Factory Library.

The reading edition remains the source of truth. This module reads
``book/book.md``, renders one MP3 per chapter, and writes timed cues that point
back to the chapter's rendered block indexes so the browser can follow along
without changing the chapter HTML.
"""

from __future__ import annotations

import json
import re
import shlex
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import xml.sax.saxutils as saxutils
from dataclasses import asdict
from pathlib import Path
from typing import Any

import _azure
import yaml
from _content_profile import is_islamic_scholarly
from _cost_ledger import append_azure_speech_cost
from _engine import ENGINE_AZURE, TASK_TTS, engine_guard
from _listener_book import split_chapters

# Extracted to _narration_plan.py (DR-005, 2026-08-25) and re-exported here so
# every existing caller and test keeps importing these from `reader_narration`.
# Split along a real seam: everything there is a DECISION or a TRACE and touches
# no network, which is what lets a page load ask for a plan for free. What stays
# here is the part that actually talks to Azure and writes audio.
from _narration_plan import (  # noqa: F401
    MANIFEST_SCHEMA,
    PHASE,
    ChapterPlan,
    Cue,
    NarrationPlan,
    RenderSummary,
    _source_hash,
    _trace,
    block_cache_dir,
    block_hash,
    cached_clip,
    chapter_blocks,
    plan_chapter,
    speech_text,
)

OUTPUT_FORMAT = "audio-24khz-96kbitrate-mono-mp3"
MAX_SEGMENT_ATTEMPTS = 3
VOICE_PRESETS: dict[str, dict[str, str]] = {
    "aria": {
        "voice": "en-US-AriaNeural",
        "style": "newscast-casual",
        "rate": "-6%",
        "pitch": "-2%",
    },
    "jenny": {
        "voice": "en-US-JennyNeural",
        "style": "friendly",
        "rate": "-5%",
        "pitch": "-1%",
    },
}


def _read_config(book_dir: Path) -> dict[str, Any]:
    path = book_dir / "_system" / "series-config.yaml"
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def narration_enabled(book_dir: Path) -> tuple[bool, str | None]:
    """Return whether chapter narration belongs on this book.

    The profile and lane checks below are a DEFAULT — a guess about which books
    are worth reading aloud, made from what kind of book it is. An explicit
    `reader_narration.enabled` in series-config.yaml is a decision a person
    made about THIS book, so it wins in both directions: `false` refuses a book
    the default would have taken, and `true` takes one the default would have
    refused. Without the `true` half there was no way to say yes at all, and a
    lecture-session book could only be narrated by editing this function
    (Asif, 2026-08-15, for love-of-the-prophet and surah-al-fateha).
    """
    cfg = _read_config(book_dir)
    value = cfg.get("reader_narration")
    if isinstance(value, dict) and value.get("enabled") is False:
        return False, "disabled in series-config.yaml"
    if value is False:
        return False, "disabled in series-config.yaml"
    if isinstance(value, dict) and value.get("enabled") is True:
        return True, None
    if value is True:
        return True, None
    if not is_islamic_scholarly(book_dir):
        return False, "not an Islamic source book"
    if "Sessions" in Path(book_dir).parts:
        return False, "KSESSIONS/Sessions lane is excluded"
    return True, None


def selected_voice(book_dir: Path) -> tuple[str, dict[str, str]]:
    cfg = _read_config(book_dir)
    value = cfg.get("reader_narration")
    requested = ""
    if isinstance(value, dict):
        requested = str(value.get("voice") or "").strip().lower()
    if not requested:
        requested = str(cfg.get("reader_narration_voice") or "").strip().lower()
    key = requested if requested in VOICE_PRESETS else "aria"
    return key, VOICE_PRESETS[key]


def _manifest_path(book_dir: Path) -> Path:
    return book_dir / "book" / "narration" / "manifest.json"


def _read_manifest(book_dir: Path) -> dict[str, Any]:
    path = _manifest_path(book_dir)
    if not path.exists():
        return {"schema": MANIFEST_SCHEMA, "chapters": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"schema": MANIFEST_SCHEMA, "chapters": {}}
    return data if isinstance(data, dict) else {"schema": MANIFEST_SCHEMA, "chapters": {}}


def _write_manifest(book_dir: Path, manifest: dict[str, Any]) -> None:
    path = _manifest_path(book_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def narration_object_name(anchor: str) -> str:
    safe = re.sub(r"[^a-z0-9]+", "-", anchor.lower()).strip("-")
    return f"{safe or 'chapter'}.mp3"


def _tts_endpoint(region: str) -> str:
    return f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"


def _ssml(text: str, preset: dict[str, str]) -> bytes:
    escaped = saxutils.escape(text)
    style = saxutils.escape(preset["style"])
    voice = saxutils.escape(preset["voice"])
    rate = saxutils.escape(preset["rate"])
    pitch = saxutils.escape(preset["pitch"])
    return (
        "<speak version='1.0' xml:lang='en-US' "
        "xmlns='http://www.w3.org/2001/10/synthesis' "
        "xmlns:mstts='https://www.w3.org/2001/mstts'>"
        f"<voice name='{voice}'><mstts:express-as style='{style}'>"
        f"<prosody rate='{rate}' pitch='{pitch}'>{escaped}</prosody>"
        "</mstts:express-as></voice></speak>"
    ).encode("utf-8")


def synthesize_text(text: str, preset: dict[str, str], *, retries: int = 3) -> bytes:
    engine_guard(TASK_TTS, ENGINE_AZURE)
    creds = _azure.load_speech_creds()
    for attempt in range(1, retries + 1):
        req = urllib.request.Request(
            _tts_endpoint(creds.region),
            data=_ssml(text, preset),
            headers={
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": OUTPUT_FORMAT,
                "Ocp-Apim-Subscription-Key": creds.key,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                return response.read()
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            if attempt == retries:
                raise
            time.sleep(2**attempt)
    raise RuntimeError("Azure Speech synthesis exhausted retries")


def audio_duration_seconds(path: Path) -> float:
    out = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    ).stdout.strip()
    duration = float(out)
    if duration <= 0:
        raise RuntimeError(f"Audio segment has non-positive duration: {path}")
    return duration


def synthesize_clip(text: str, preset: dict[str, str], clip: Path) -> float:
    last_error: Exception | None = None
    for attempt in range(1, MAX_SEGMENT_ATTEMPTS + 1):
        clip.write_bytes(synthesize_text(text, preset))
        try:
            return audio_duration_seconds(clip)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError, RuntimeError) as exc:
            last_error = exc
            clip.unlink(missing_ok=True)
            if attempt < MAX_SEGMENT_ATTEMPTS:
                time.sleep(2**attempt)
    raise RuntimeError(f"Azure Speech returned invalid audio after {MAX_SEGMENT_ATTEMPTS} attempts") from last_error


def concat_audio(parts: list[Path], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as handle:
        list_path = Path(handle.name)
        for part in parts:
            handle.write(f"file {shlex.quote(str(part))}\n")
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_path),
                "-c",
                "copy",
                str(out_path),
            ],
            check=True,
            timeout=300,
        )
    finally:
        list_path.unlink(missing_ok=True)


def narration_plan(book_dir: Path) -> NarrationPlan:
    """What a render would do, costing nothing: no network, no synthesis.

    Reads the reading edition and the manifest and compares them. Safe to call
    on every page load, which is what the Book Composer does.
    """
    book_dir = Path(book_dir)
    enabled, reason = narration_enabled(book_dir)
    if not enabled:
        return NarrationPlan(enabled=False, reason=reason)

    book_md = book_dir / "book" / "book.md"
    if not book_md.exists():
        return NarrationPlan(enabled=False, reason="no reading edition")

    _voice_key, preset = selected_voice(book_dir)
    manifest = _read_manifest(book_dir)
    chapters = manifest.get("chapters")
    chapters = chapters if isinstance(chapters, dict) else {}
    out_dir = book_dir / "book" / "narration"
    return NarrationPlan(
        enabled=True,
        reason=None,
        chapters=[
            plan_chapter(c, manifest_chapters=chapters, preset=preset, out_dir=out_dir)
            for c in split_chapters(book_md.read_text(encoding="utf-8"))
        ],
    )


def prune_block_cache(book_dir: Path, chapters: list, preset: dict[str, str]) -> int:
    """Drop paragraph clips no chapter refers to any more. Returns how many went.

    Keyed on EVERY chapter of the current edition, not just the ones this run
    recorded: an untouched chapter's paragraphs must stay cached, or editing it
    later would re-buy the whole thing — which is the cost this cache exists to
    avoid. Only clips belonging to text that no longer appears anywhere in the
    book are removed.

    Best-effort by design. A cache that cannot be tidied is a disk-space
    question; a render that fails because tidying failed is a broken publish.
    """
    directory = block_cache_dir(book_dir / "book" / "narration")
    if not directory.is_dir():
        return 0
    try:
        live = {block_hash(text, preset) for chapter in chapters for _idx, text in chapter_blocks(chapter.markdown)}
        gone = 0
        for path in directory.glob("*.mp3"):
            if path.stem not in live:
                path.unlink(missing_ok=True)
                gone += 1
        return gone
    except OSError:
        return 0


def render_reader_narration(book_dir: Path, *, log: Any = None) -> RenderSummary:
    """Record every chapter whose text or voice has changed.

    `log` is an optional one-argument callable receiving human-readable progress
    lines. Every line it gets is also appended to the run timeline, so a publish
    that ran unattended can be traced afterwards from
    `_workspace/runs/<slug>/<run_id>.jsonl` with no console to scroll back to.
    """
    book_dir = Path(book_dir)
    enabled, reason = narration_enabled(book_dir)
    if not enabled:
        _trace("narration.skipped", book_dir=book_dir, log=log, msg=f"narration skipped: {reason}", reason=reason)
        return RenderSummary(outcome="skipped", rendered=[], skipped=[], reason=reason)

    book_md = book_dir / "book" / "book.md"
    if not book_md.exists():
        _trace(
            "narration.skipped",
            book_dir=book_dir,
            log=log,
            msg="narration skipped: no reading edition",
            reason="no reading edition",
        )
        return RenderSummary(outcome="skipped", rendered=[], skipped=[], reason="no reading edition")

    voice_key, preset = selected_voice(book_dir)
    chapters = split_chapters(book_md.read_text(encoding="utf-8"))
    manifest = _read_manifest(book_dir)
    manifest.update(
        {
            "schema": MANIFEST_SCHEMA,
            "engine": "azure-speech-neural-tts",
            "voice": voice_key,
            "voice_id": preset["voice"],
            "style": preset["style"],
            "chapters": manifest.get("chapters") if isinstance(manifest.get("chapters"), dict) else {},
        }
    )

    rendered: list[str] = []
    skipped: list[str] = []
    failed: list[str] = []
    chars = 0
    out_dir = book_dir / "book" / "narration"

    plans = [plan_chapter(c, manifest_chapters=manifest["chapters"], preset=preset, out_dir=out_dir) for c in chapters]
    todo = [p for p in plans if p.action == "render"]
    _trace(
        "narration.plan",
        book_dir=book_dir,
        log=log,
        msg=(
            f"narration: {len(todo)} chapter(s) to record, "
            f"{sum(1 for p in plans if p.action == 'current')} already current, "
            f"{sum(1 for p in plans if p.action == 'silent')} with nothing speakable"
            + (
                f" — {sum(p.stale_blocks for p in todo)} of {sum(p.blocks for p in todo)} "
                "paragraph(s) actually need synthesis"
                if todo
                else ""
            )
        ),
        voice=voice_key,
        voice_id=preset["voice"],
        to_render=[p.anchor for p in todo],
        reasons={p.anchor: p.reason for p in todo},
        paragraphs_stale=sum(p.stale_blocks for p in todo),
        paragraphs_total=sum(p.blocks for p in todo),
    )

    by_anchor = {c.anchor: c for c in chapters}
    for plan in plans:
        chapter = by_anchor[plan.anchor]
        if plan.action != "render":
            skipped.append(plan.anchor)
            _trace(
                "narration.chapter.skipped",
                book_dir=book_dir,
                log=log,
                level="debug",
                chapter=plan.anchor,
                msg=f"  {plan.title}: {plan.reason}",
                action=plan.action,
                reason=plan.reason,
            )
            continue

        digest = plan.digest
        audio = out_dir / f"{chapter.anchor}.mp3"
        blocks = chapter_blocks(chapter.markdown)
        started = time.monotonic()
        _trace(
            "narration.chapter.start",
            book_dir=book_dir,
            log=log,
            chapter=plan.anchor,
            msg=f"  recording {plan.title} ({len(blocks)} paragraph(s)) — {plan.reason}",
            blocks=len(blocks),
            reason=plan.reason,
        )

        out_dir.mkdir(parents=True, exist_ok=True)
        # One chapter's failure is ISOLATED to that chapter. A book part-way
        # through a re-record must not lose the chapters already done — they are
        # on disk with their manifest entries written, and the next run picks up
        # exactly the ones that did not finish. The caller decides whether a
        # failure is fatal; the renderer's job is to leave a resumable state.
        try:
            block_cache_dir(out_dir).mkdir(parents=True, exist_ok=True)
            clips: list[Path] = []
            cues: list[Cue] = []
            cursor = 0.0
            bought = 0
            spoken = 0
            for idx, (block_index, text) in enumerate(blocks):
                # PARAGRAPH-LEVEL REUSE. The clip's name is the hash of its text
                # in this voice, so a paragraph nobody touched is already on disk
                # under the name this asks for and costs nothing but an ffprobe.
                # Only genuinely new wording reaches Azure — editing one
                # paragraph of a forty-paragraph chapter buys one paragraph.
                clip = cached_clip(out_dir, text, preset)
                duration = None
                if clip.exists():
                    # A cached clip that will not probe is a truncated or
                    # half-written file, not a reason to fail the chapter: throw
                    # it away and buy the paragraph again. Trusting it instead
                    # would publish a chapter with a paragraph of silence in it.
                    try:
                        duration = audio_duration_seconds(clip)
                    except Exception:
                        clip.unlink(missing_ok=True)
                        duration = None
                if duration is None:
                    duration = synthesize_clip(text, preset, clip)
                    bought += 1
                    spoken += len(text)
                    chars += len(text)
                clips.append(clip)
                cues.append(
                    Cue(
                        idx=idx,
                        blockIndex=block_index,
                        startS=round(cursor, 3),
                        endS=round(cursor + duration, 3),
                        text=text,
                    )
                )
                cursor += duration
            concat_audio(clips, audio)
            duration = round(audio_duration_seconds(audio), 3)
        except Exception as exc:
            failed.append(plan.anchor)
            # The half-written file goes: a truncated MP3 on disk would satisfy
            # the `audio.exists()` half of the freshness check on the next run
            # and be published as if it were the whole chapter.
            audio.unlink(missing_ok=True)
            manifest["chapters"].pop(plan.anchor, None)
            _write_manifest(book_dir, manifest)
            _trace(
                "narration.chapter.failed",
                book_dir=book_dir,
                log=log,
                level="error",
                chapter=plan.anchor,
                msg=f"  FAILED {plan.title}: {exc}",
                error=str(exc),
            )
            continue

        manifest["chapters"][chapter.anchor] = {
            "title": chapter.title,
            "idx": chapter.idx,
            "audio": f"book/narration/{audio.name}",
            "audio_key": f"{book_dir.name}/narration/{narration_object_name(chapter.anchor)}",
            "duration_s": duration,
            "source_hash": digest,
            "voice": voice_key,
            "voice_id": preset["voice"],
            "style": preset["style"],
            "cues": [asdict(c) for c in cues],
        }
        _write_manifest(book_dir, manifest)
        # Bill ONLY what was synthesised. Charging for the whole chapter here
        # would report a paragraph edit at the price of a full re-record and
        # make the ledger disagree with the invoice.
        append_azure_speech_cost(book_dir, phase=PHASE, step=chapter.anchor, char_count=spoken)
        rendered.append(chapter.anchor)
        reused = len(blocks) - bought
        _trace(
            "narration.chapter.done",
            book_dir=book_dir,
            log=log,
            chapter=plan.anchor,
            msg=(
                f"  recorded {plan.title} — {duration}s of audio; "
                f"{bought} paragraph(s) synthesised ({spoken} characters), {reused} reused from cache"
            ),
            duration_s=duration,
            chars=spoken,
            blocks_synthesised=bought,
            blocks_reused=reused,
            elapsed_ms=int((time.monotonic() - started) * 1000),
        )

    _write_manifest(book_dir, manifest)
    pruned = prune_block_cache(book_dir, chapters, preset)
    _trace(
        "narration.done",
        book_dir=book_dir,
        log=log,
        level="error" if failed else "info",
        msg=(
            f"narration finished: {len(rendered)} recorded, {len(skipped)} unchanged"
            + (f", {len(failed)} FAILED" if failed else "")
            + (f"; {pruned} stale paragraph clip(s) pruned" if pruned else "")
        ),
        blocks_pruned=pruned,
        rendered=rendered,
        skipped=skipped,
        failed=failed,
        chars=chars,
    )
    return RenderSummary(outcome="completed", rendered=rendered, skipped=skipped, chars=chars, failed=failed)
