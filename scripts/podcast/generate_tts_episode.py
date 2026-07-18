#!/usr/bin/env python3
"""
generate_tts_episode.py — Two-host podcast audio via Claude + Azure Neural TTS.

Steps:
  1. Read chapter content + episode framing file
  2. Use `claude -p` to generate a structured two-host conversation script (JSON)
  3. Render each utterance via Azure Neural TTS with two distinct voices
  4. Concatenate all clips into a single mp3 with ffmpeg
  5. Write to <BOOK_DIR>/audio/tts/<EP##-slug>-tts.mp3

Usage:
  python3 scripts/podcast/generate_tts_episode.py <BOOK_DIR> <EP##-slug> <chapter-md> [--minutes N]

Example:
  python3 scripts/podcast/generate_tts_episode.py \\
    content/drafts/sites/healthequity EP01-hsa \\
    content/drafts/sites/healthequity/chapters/ch02-hsa.md --minutes 12

Credentials:
  Reads AZURE_SPEECH_KEY env var, or fetches from Azure CLI if not set.
  `az` must be logged in as asifhussain60@msn.com.
  `claude` must be authenticated via Max subscription (claude login).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import time
import urllib.error
import urllib.request
import xml.sax.saxutils as saxutils
from pathlib import Path

# ── Voice config ─────────────────────────────────────────────────────────────
# Host A — knowledgeable, warm guide
VOICE_A = "en-US-DavisNeural"
# Host B — curious, relatable listener
VOICE_B = "en-US-JennyNeural"

# ── Azure TTS ─────────────────────────────────────────────────────────────────
# Neural TTS requires the region-specific speech endpoint, NOT the generic
# cognitive services host. Pattern: https://<region>.tts.speech.microsoft.com/...
TTS_ENDPOINT = "https://eastus.tts.speech.microsoft.com/cognitiveservices/v1"
TTS_OUTPUT_FORMAT = "audio-24khz-96kbitrate-mono-mp3"


# ── Credential helper ─────────────────────────────────────────────────────────


def get_azure_speech_key() -> str:
    """Fetch Azure Speech key — env var wins, falls back to az CLI."""
    key = os.environ.get("AZURE_SPEECH_KEY", "").strip()
    if key:
        return key
    print("  Fetching Azure Speech key via az CLI...")
    result = subprocess.run(
        [
            "az",
            "cognitiveservices",
            "account",
            "keys",
            "list",
            "--name",
            "journal-speech",
            "--resource-group",
            "rg-journal-ai",
            "--query",
            "key1",
            "-o",
            "tsv",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


# ── TTS ───────────────────────────────────────────────────────────────────────


def _build_ssml(text: str, voice: str) -> bytes:
    escaped = saxutils.escape(text)
    ssml = (
        f"<speak version='1.0' xml:lang='en-US' "
        f"xmlns='http://www.w3.org/2001/10/synthesis'>"
        f"<voice name='{voice}'>"
        f"<prosody rate='-3%'>{escaped}</prosody>"
        f"</voice></speak>"
    )
    return ssml.encode("utf-8")


def synthesize_utterance(text: str, voice: str, key: str, retries: int = 3) -> bytes:
    """Call Azure TTS REST API and return mp3 bytes. Retries on transient errors."""
    from _engine import ENGINE_AZURE, TASK_TTS, engine_guard

    engine_guard(TASK_TTS, ENGINE_AZURE)
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                TTS_ENDPOINT,
                data=_build_ssml(text, voice),
                headers={
                    "Content-Type": "application/ssml+xml",
                    "X-Microsoft-OutputFormat": TTS_OUTPUT_FORMAT,
                    "Ocp-Apim-Subscription-Key": key,
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if attempt == retries:
                raise
            print(f"    HTTP {e.code} — retrying ({attempt}/{retries})...", file=sys.stderr)
            time.sleep(2**attempt)
        except Exception as e:
            if attempt == retries:
                raise
            print(f"    Error: {e} — retrying ({attempt}/{retries})...", file=sys.stderr)
            time.sleep(2**attempt)


# ── Script generation ─────────────────────────────────────────────────────────


def generate_conversation_script(
    chapter_text: str,
    episode_text: str,
    minutes: int,
) -> list[dict]:
    """Use `claude -p` to produce a two-host conversation script as a JSON array."""
    word_target = minutes * 130  # ~130 words/min conversational speech

    prompt = textwrap.dedent(f"""
You are writing a two-host podcast conversation script for HealthEquity's "Benefits Unlocked" podcast.

HOST A is the knowledgeable guide — warm, direct, uses concrete numbers, works at HealthEquity.
HOST B is the relatable everyday listener — curious, occasionally surprised, asks natural follow-up questions.

TARGET LENGTH: approximately {word_target} words of dialogue (targeting {minutes} minutes of audio at normal conversational pace).

─── EPISODE FRAMING ───────────────────────────────────────────────
Use this to structure the episode — welcome block, beats, closing CTA, tone rules, and do-nots all apply.

{episode_text}

─── SOURCE CONTENT ────────────────────────────────────────────────
All facts, numbers, and specific examples MUST come from here verbatim. Do not invent or round any figures.

{chapter_text}

─── OUTPUT FORMAT ─────────────────────────────────────────────────
Return ONLY a valid JSON array. No markdown, no explanation, no text outside the array.

[
  {{"speaker": "A", "text": "Welcome to Benefits Unlocked, brought to you by HealthEquity..."}},
  {{"speaker": "B", "text": "..."}},
  ...
]

─── HARD RULES ────────────────────────────────────────────────────
1. Start with the Welcome block from the episode framing — Host A speaks it verbatim as written.
2. Follow the three-beat structure from the episode framing.
3. Repeat the central thesis VERBATIM at the three moments specified in the framing.
4. End with the Closing call to action from the episode framing — Host A speaks it verbatim.
5. Host B delivers a single warm closing line to end the episode.
6. Every number (dollar amounts, limits, percentages, dates) must match the source content exactly.
7. Keep each utterance to 1–4 sentences. Natural back-and-forth rhythm, not monologues.
8. Forbidden words: wow, game-changer, revolutionary, buckle up, let's dive in, mind blown, fascinating world of, what a journey, right? (as filler).
9. Do NOT include any text outside the JSON array.
""").strip()

    print("  Calling Claude to generate conversation script...")
    result = subprocess.run(
        ["claude", "-p", prompt],
        capture_output=True,
        text=True,
        timeout=180,
    )
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        raise SystemExit(f"Claude exited {result.returncode}")

    raw = result.stdout.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:])
        if raw.endswith("```"):
            raw = raw[: raw.rfind("```")].strip()

    # Trim any trailing prose after the closing ]
    bracket_end = raw.rfind("]")
    if bracket_end != -1:
        raw = raw[: bracket_end + 1]

    return json.loads(raw)


# ── Audio concatenation ───────────────────────────────────────────────────────


def concat_clips(clip_paths: list[Path], output: Path) -> None:
    """Concatenate mp3 clips using ffmpeg."""
    list_content = "\n".join(f"file '{p}'" for p in clip_paths) + "\n"
    list_file = output.parent / "_concat_list.txt"
    list_file.write_text(list_content, encoding="utf-8")
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_file),
                "-c",
                "copy",
                str(output),
            ],
            check=True,
            capture_output=True,
        )
    finally:
        list_file.unlink(missing_ok=True)


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("book_dir", type=Path, help="e.g. content/drafts/sites/healthequity")
    parser.add_argument("episode_id", help="e.g. EP01-hsa")
    parser.add_argument("chapter_md", type=Path, help="Path to the chapter .md file")
    parser.add_argument("--minutes", type=int, default=12, help="Target runtime in minutes (default: 12)")
    parser.add_argument(
        "--use-script",
        type=Path,
        default=None,
        help="Skip Claude generation and load an existing JSON script file instead",
    )
    args = parser.parse_args()

    book_dir: Path = args.book_dir.resolve()
    chapter_md: Path = args.chapter_md.resolve()

    if not book_dir.is_dir():
        raise SystemExit(f"BOOK_DIR not found: {book_dir}")
    if not chapter_md.is_file():
        raise SystemExit(f"Chapter file not found: {chapter_md}")

    # Locate episode framing file
    ep_file = book_dir / "episodes" / f"{args.episode_id}.txt"
    if not ep_file.is_file():
        candidates = list((book_dir / "episodes").glob(f"{args.episode_id[:4]}*.txt"))
        if not candidates:
            raise SystemExit(f"No episode file found for {args.episode_id} in {book_dir / 'episodes'}")
        ep_file = candidates[0]

    chapter_text = chapter_md.read_text(encoding="utf-8")
    episode_text = ep_file.read_text(encoding="utf-8")

    out_dir = book_dir / "audio" / "tts"
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── Step 1: Generate or load conversation script ──────────────────────────
    print(f"\n{'─' * 60}")
    print(f"Episode: {args.episode_id}  |  Target: {args.minutes} min")
    print(f"{'─' * 60}")

    script_path = out_dir / f"{args.episode_id}-script.json"

    if args.use_script:
        src = args.use_script.resolve()
        print(f"  Loading existing script: {src}")
        script = json.loads(src.read_text(encoding="utf-8"))
    else:
        script = generate_conversation_script(chapter_text, episode_text, args.minutes)
        script_path.write_text(json.dumps(script, indent=2, ensure_ascii=False))
        print(f"  Script saved → {script_path.relative_to(Path.cwd())}")

    total_words = sum(len(u["text"].split()) for u in script)
    print(f"  {len(script)} utterances / ~{total_words:,} words")

    # ── Step 2: Render via Azure TTS ──────────────────────────────────────────
    print("\nFetching Azure Speech credentials...")
    key = get_azure_speech_key()
    print(f"  Voices: A={VOICE_A}  B={VOICE_B}")
    print(f"\nRendering {len(script)} utterances via Azure Neural TTS...")

    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str)
        clip_paths: list[Path] = []

        for i, utt in enumerate(script):
            speaker = utt.get("speaker", "A")
            text = utt.get("text", "").strip()
            if not text:
                continue
            voice = VOICE_A if speaker == "A" else VOICE_B
            preview = text[:70].replace("\n", " ")
            print(f"  [{i + 1:03d}/{len(script)}] Host {speaker}: {preview}...")

            audio = synthesize_utterance(text, voice, key)
            clip = tmp / f"{i:04d}.mp3"
            clip.write_bytes(audio)
            clip_paths.append(clip)

            # Pace requests: brief pause every 15 utterances
            if (i + 1) % 15 == 0:
                time.sleep(0.8)

        if not clip_paths:
            raise SystemExit("No audio clips generated.")

        # ── Step 3: Concatenate ───────────────────────────────────────────────
        out_audio = out_dir / f"{args.episode_id}-tts.mp3"
        print(f"\nConcatenating {len(clip_paths)} clips → {out_audio.name}")
        concat_clips(clip_paths, out_audio)

    size_mb = out_audio.stat().st_size / (1024 * 1024)
    est_min = size_mb * 8 / (96 / 8 * 60 / 1024)  # 96kbps mp3
    print(f"\n{'─' * 60}")
    print(f"  Output : {out_audio}")
    print(f"  Size   : {size_mb:.1f} MB")
    print(f"  Est.   : ~{est_min:.0f} min at 96 kbps")
    print(f"  Script : {script_path}")
    print(f"\n  Play   : open '{out_audio}'")
    print(f"{'─' * 60}\n")


if __name__ == "__main__":
    main()
