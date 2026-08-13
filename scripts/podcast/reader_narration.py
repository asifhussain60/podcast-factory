"""Chapter read-aloud audio for the Podcast Factory Library.

The reading edition remains the source of truth. This module reads
``book/book.md``, renders one MP3 per chapter, and writes timed cues that point
back to the chapter's rendered block indexes so the browser can follow along
without changing the chapter HTML.
"""

from __future__ import annotations

import hashlib
import json
import re
import shlex
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import xml.sax.saxutils as saxutils
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import _azure
import yaml
from _content_profile import is_islamic_scholarly
from _cost_ledger import append_azure_speech_cost
from _engine import ENGINE_AZURE, TASK_TTS, engine_guard
from _listener_book import split_chapters

PHASE = "reader-narration"
MANIFEST_SCHEMA = 1
OUTPUT_FORMAT = "audio-24khz-96kbitrate-mono-mp3"
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

_ARABIC = re.compile(r"[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff\ufb50-\ufdff\ufe70-\ufeff]+")
_ARABIC_PARENS = re.compile(r"\([^)]*[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff\ufb50-\ufdff\ufe70-\ufeff][^)]*\)")
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_IMAGE = re.compile(r"!\[[^\]]*]\([^)]+\)")
_TAG = re.compile(r"<[^>]+>")
_MARKDOWN_EDGE = re.compile(r"^[>*#\-\s]+")


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
    """Return whether chapter narration belongs on this book."""
    cfg = _read_config(book_dir)
    value = cfg.get("reader_narration")
    if isinstance(value, dict) and value.get("enabled") is False:
        return False, "disabled in series-config.yaml"
    if value is False:
        return False, "disabled in series-config.yaml"
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


def chapter_blocks(markdown: str) -> list[tuple[int, str]]:
    blocks: list[tuple[int, str]] = []
    raw_blocks = re.split(r"\n\s*\n", _HTML_COMMENT.sub("", markdown).strip())
    for block_index, raw in enumerate(raw_blocks):
        text = speech_text(raw)
        if text:
            blocks.append((block_index, text))
    return blocks


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
    return text


def _source_hash(chapter_markdown: str, preset: dict[str, str]) -> str:
    payload = {
        "markdown": chapter_markdown,
        "preset": preset,
        "schema": MANIFEST_SCHEMA,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


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
    return float(out)


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


def render_reader_narration(book_dir: Path) -> RenderSummary:
    book_dir = Path(book_dir)
    enabled, reason = narration_enabled(book_dir)
    if not enabled:
        return RenderSummary(outcome="skipped", rendered=[], skipped=[], reason=reason)

    book_md = book_dir / "book" / "book.md"
    if not book_md.exists():
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
    chars = 0
    out_dir = book_dir / "book" / "narration"

    for chapter in chapters:
        digest = _source_hash(chapter.markdown, preset)
        audio = out_dir / f"{chapter.anchor}.mp3"
        existing = manifest["chapters"].get(chapter.anchor, {})
        if (
            isinstance(existing, dict)
            and existing.get("source_hash") == digest
            and existing.get("voice_id") == preset["voice"]
            and audio.exists()
        ):
            skipped.append(chapter.anchor)
            continue

        blocks = chapter_blocks(chapter.markdown)
        if not blocks:
            skipped.append(chapter.anchor)
            continue

        out_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="reader-narration-") as tmp:
            tmp_dir = Path(tmp)
            clips: list[Path] = []
            cues: list[Cue] = []
            cursor = 0.0
            for idx, (block_index, text) in enumerate(blocks):
                clip = tmp_dir / f"{idx:04d}.mp3"
                clip.write_bytes(synthesize_text(text, preset))
                duration = audio_duration_seconds(clip)
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
                chars += len(text)
            concat_audio(clips, audio)

        duration = round(audio_duration_seconds(audio), 3)
        manifest["chapters"][chapter.anchor] = {
            "title": chapter.title,
            "idx": chapter.idx,
            "audio": f"book/narration/{audio.name}",
            "audio_key": f"{book_dir.name}/narration/{audio.name}",
            "duration_s": duration,
            "source_hash": digest,
            "voice": voice_key,
            "voice_id": preset["voice"],
            "style": preset["style"],
            "cues": [asdict(c) for c in cues],
        }
        append_azure_speech_cost(book_dir, phase=PHASE, step=chapter.anchor, char_count=sum(len(c.text) for c in cues))
        rendered.append(chapter.anchor)

    _write_manifest(book_dir, manifest)
    return RenderSummary(outcome="completed", rendered=rendered, skipped=skipped, chars=chars)
