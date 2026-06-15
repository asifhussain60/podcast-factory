#!/usr/bin/env python3
"""transcribe_audio_book.py — bridges the audio source path (source_kind=audio).

A book intaken via `intake_book.py --from-audio` (or any book that has audio
lecture files under <book>/source/*.mp3 and source_kind=audio) lands at
phase=0a-transcribe. This script does the transcription half so the book can
advance to synthesis (reconcile) and the holistic editorial pass.

Mirrors the role `translate_bundle.py` plays for source_kind=bundle, but uses
Gemini 2.5 Pro DIRECT-AUDIO transcription (validated decisively best for
code-switched Urdu/Arabic religious lectures — it preserves doctrine that
Azure-STT + Translator and external ASR both destroy).

What it does (idempotent — skip-if-exists, --force to redo):
1. Reads <book>/source/*.mp3 in filename order.
2. For each: Gemini 2.5 Pro transcribes; if source_language != "en" it also
   translates to English in the same pass (one-pass transcribe+translate).
   Writes a faithful per-lecture transcript + a provenance sidecar. Records
   Gemini spend in _system/cost-ledger.jsonl.
3. Concatenates the lectures into the faithful master
   _system/source/text/raw-extract.md (with <!-- lecture N --> markers) AND a
   denoised SOURCE STREAM at _system/source/multi/denoised/audio-synthesized.md
   so the existing reconcile_book.py multi-source path can fuse it with any
   companion streams (PDF OCR, supplementary text).
4. Advances orchestrator-state: last_completed_phase=0a, phase=0a-synthesize.

The faithful master is NEVER pruned here — denoise/reorganize/enrich happen in
the holistic editorial pass downstream, against this faithful baseline.

Usage:
  python3 scripts/podcast/transcribe_audio_book.py --slug <book-slug>
  python3 scripts/podcast/transcribe_audio_book.py --slug <slug> --language ur
  python3 scripts/podcast/transcribe_audio_book.py --slug <slug> --limit 1 --force
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from _paths import REPO_ROOT, content_dir, find_content  # noqa: E402

GEMINI_MODEL = "gemini-2.5-pro"

# Validated probe prompt — faithful, complete, terminology-preserving.
TRANSCRIBE_PROMPT = """This is an audio recording of an {lang_name}-language Islamic lecture \
(Ismaili/Tayyibi tradition) teaching from the book "{book_title}".

Produce a FAITHFUL, COMPLETE {output_clause} of the full spoken content. Requirements:
1. Preserve all Arabic/Islamic technical terms, proper names, and honorifics in standard \
transliteration (e.g., Bismillah al-Rahman al-Rahim, Ahl al-Bayt, 'isma/'ismah, du'at, Sayyidna, Imam).
2. Render Quranic verses and Arabic quotations in transliteration, followed by a short English \
gloss in parentheses.
3. Transcribe the full continuous speech IN ORDER — do NOT summarize, condense, or reorder.
4. Output ONLY the prose. No headings, no notes, no preamble.
5. Where the audio is genuinely unclear, write [unclear] rather than guessing.
Do NOT drop side-discussion yet — faithfulness first; cleanup happens in a later step."""

_LANG_NAMES = {"ur": "Urdu", "en": "English", "ar": "Arabic", "fa": "Persian"}


def _die(msg: str) -> int:
    print(f"transcribe_audio_book: {msg}", file=sys.stderr)
    return 2


def _info(msg: str) -> None:
    print(msg)


def _resolve_book_dir(slug: str) -> Path | None:
    hit = find_content(slug)
    if hit:
        return hit[2]
    # Fall back to the category-derived path (book may not be registered yet).
    cand = content_dir(slug)
    return cand if cand.exists() else None


def _read_book_title(book_dir: Path) -> str:
    meta = book_dir / "meta.yml"
    if meta.exists():
        for line in meta.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("title:"):
                return line.split(":", 1)[1].strip().strip("\"'")
    return book_dir.name


# Gemini occasionally enters a repetition loop on long/uniform audio, emitting the
# same sentences dozens of times. We detect that deterministically (duplicate-sentence
# ratio) and recover by re-transcribing the audio in chunks, which breaks the loop.
DUP_RATIO_LOOP_THRESHOLD = 0.25


def _dup_ratio(text: str) -> float:
    """Fraction of (>30-char) sentences that are exact duplicates. ~0 for clean
    speech; >0.8 for a runaway repetition loop."""
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 30]
    if not sents:
        return 0.0
    return (len(sents) - len(set(sents))) / len(sents)


def _gen_from_file(client, path: str, prompt: str) -> str:
    f = client.files.upload(file=path)
    for _ in range(120):
        f = client.files.get(name=f.name)
        st = str(f.state)
        if "ACTIVE" in st:
            break
        if "FAIL" in st.upper():
            raise RuntimeError(f"Gemini upload failed for {path}: {f.state}")
        time.sleep(2)
    resp = client.models.generate_content(model=GEMINI_MODEL, contents=[f, prompt])
    return (resp.text or "").strip()


def _transcribe_chunked(client, mp3_bytes: bytes, prompt: str, *, max_bytes: int, log=_info) -> str:
    """Re-transcribe by splitting the audio into chunks (breaks Gemini loops)."""
    from _mp3_chunk import chunk_mp3_bytes  # noqa: E402
    chunks = chunk_mp3_bytes(mp3_bytes, max_bytes=max_bytes)
    log(f"        ↻ chunked into {len(chunks)} pieces to break repetition loop")
    parts = []
    for j, ch in enumerate(chunks, 1):
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tf:
            tf.write(ch)
            tp = tf.name
        parts.append(_gen_from_file(client, tp, prompt))
    return "\n\n".join(p for p in parts if p)


def _transcribe_one(client, mp3: Path, *, language: str, book_title: str, log=_info) -> tuple[str, str]:
    """Transcribe one MP3. Returns (text, method). Auto-recovers from repetition
    loops by re-transcribing in audio chunks."""
    lang_name = _LANG_NAMES.get(language, language)
    output_clause = "ENGLISH TRANSLATION" if language != "en" else "ENGLISH TRANSCRIPTION"
    prompt = TRANSCRIBE_PROMPT.format(
        lang_name=lang_name, book_title=book_title, output_clause=output_clause
    )
    text = _gen_from_file(client, str(mp3), prompt)
    method = "whole-file"
    dup = _dup_ratio(text)
    if dup > DUP_RATIO_LOOP_THRESHOLD:
        log(f"        ⚠ repetition loop detected ({dup:.0%} duplicate sentences) — re-chunking")
        chunked = _transcribe_chunked(client, mp3.read_bytes(), prompt, max_bytes=3_400_000, log=log)
        if _dup_ratio(chunked) < dup:
            text, method = chunked, "chunked-recovery"
        if _dup_ratio(text) > DUP_RATIO_LOOP_THRESHOLD:
            log(f"        ⚠ STILL looping after re-chunk ({_dup_ratio(text):.0%}) — flagged in provenance")
            method = "chunked-recovery-FLAGGED"
    return text, method


def transcribe_audio_book(
    slug: str, *, language: str | None = None, force: bool = False, limit: int | None = None
) -> int:
    book_dir = _resolve_book_dir(slug)
    if book_dir is None:
        return _die(f"book workspace not found for slug {slug!r}")

    state_path = book_dir / "_system" / "orchestrator-state.json"
    state = {}
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state.get("source_kind") not in (None, "audio"):
            return _die(
                f"source_kind is {state.get('source_kind')!r}, not 'audio'. "
                f"This bridge is only for audio-sourced books."
            )

    language = language or state.get("source_language") or "ur"
    book_title = _read_book_title(book_dir)

    src_dir = book_dir / "source"
    mp3s = sorted(p for p in src_dir.glob("*.mp3")) if src_dir.is_dir() else []
    if not mp3s:
        return _die(f"no .mp3 files found in {src_dir}")
    if limit:
        mp3s = mp3s[:limit]

    lectures_dir = book_dir / "_system" / "source" / "lectures"
    lectures_dir.mkdir(parents=True, exist_ok=True)

    _info(f"==> Transcribing {len(mp3s)} lecture(s) for {slug!r}")
    _info(f"    language: {language} ({_LANG_NAMES.get(language, language)})  model: {GEMINI_MODEL}")

    # Lazy imports so --help works without creds/SDK.
    from _secrets import get_gemini_key  # noqa: E402
    from google import genai  # noqa: E402
    try:
        from _cost_ledger import append_gemini_cost  # noqa: E402
    except Exception:
        append_gemini_cost = None

    client = genai.Client(api_key=get_gemini_key())

    transcripts: list[tuple[int, str]] = []
    t0 = time.monotonic()
    for i, mp3 in enumerate(mp3s, 1):
        out_txt = lectures_dir / f"lec{i:02d}.txt"
        prov = lectures_dir / f"lec{i:02d}.provenance.json"
        if out_txt.exists() and not force:
            _info(f"    [{i}/{len(mp3s)}] skip (exists): {out_txt.name}")
            transcripts.append((i, out_txt.read_text(encoding="utf-8")))
            continue
        _info(f"    [{i}/{len(mp3s)}] {mp3.name} ...")
        ts = time.monotonic()
        text, method = _transcribe_one(client, mp3, language=language, book_title=book_title)
        elapsed = time.monotonic() - ts
        dup = _dup_ratio(text)
        out_txt.write_text(text + "\n", encoding="utf-8")
        prov.write_text(json.dumps({
            "lecture": i,
            "source_audio": mp3.name,
            "source_bytes": mp3.stat().st_size,
            "source_kind": "audio",
            "source_language": language,
            "transcription_engine": f"gemini/{GEMINI_MODEL}",
            "transcription_method": method,
            "dup_sentence_ratio": round(dup, 3),
            "loop_flagged": method.endswith("FLAGGED"),
            "translated": language != "en",
            "char_count": len(text),
            "word_count": len(text.split()),
            "elapsed_seconds": round(elapsed, 1),
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }, indent=2) + "\n", encoding="utf-8")
        if append_gemini_cost:
            try:
                append_gemini_cost(
                    book_dir, phase="0a", step=f"transcribe/lec{i:02d}",
                    model=GEMINI_MODEL,
                    in_chars=int(mp3.stat().st_size / 1000),  # rough audio-input proxy
                    out_chars=len(text),
                )
            except Exception as e:
                _info(f"        WARN cost-ledger: {e}")
        _info(f"        -> {len(text):,} chars ({len(text.split())} words, {elapsed:.0f}s)")
        transcripts.append((i, text))

    # Assemble faithful master (never pruned) + denoised source stream.
    transcripts.sort(key=lambda t: t[0])
    parts = [f"<!-- lecture {i} -->\n\n{txt.strip()}" for i, txt in transcripts]
    master = "\n\n".join(parts) + "\n"

    text_dir = book_dir / "_system" / "source" / "text"
    text_dir.mkdir(parents=True, exist_ok=True)
    (text_dir / "raw-extract.md").write_text(master, encoding="utf-8")

    multi_dir = book_dir / "_system" / "source" / "multi" / "denoised"
    multi_dir.mkdir(parents=True, exist_ok=True)
    (multi_dir / "audio-synthesized.md").write_text(master, encoding="utf-8")

    total_words = sum(len(t.split()) for _, t in transcripts)
    _info(f"==> Assembled {len(transcripts)} lectures → raw-extract.md "
          f"({total_words:,} words) in {time.monotonic()-t0:.0f}s")
    _info(f"    stream: _system/source/multi/denoised/audio-synthesized.md")

    # Advance state.
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    state.setdefault("schema_version", 1)
    state["book_slug"] = slug
    state["source_kind"] = "audio"
    state["source_language"] = language
    state["last_completed_phase"] = "0a"
    state["phase"] = "0a-synthesize"
    state["phase_status"] = "pending"
    state["last_error"] = None
    state.setdefault("category", state.get("category", "lectures"))
    state.setdefault("status", "draft")
    state["updated"] = now
    state.setdefault("phases", {})["0a"] = {
        "completed_via": "transcribe_audio_book.py (gemini direct-audio)",
        "completed_at": now,
        "lectures": len(transcripts),
        "engine": f"gemini/{GEMINI_MODEL}",
        "source_language": language,
    }
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    _info(f"    state.json: phase=0a-synthesize, last_completed_phase=0a")
    _info("")
    _info("==> DONE. Next: synthesize (reconcile) + holistic editorial pass.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--slug", required=True, help="Book slug")
    ap.add_argument("--language", default=None, help="Source language (ur|en|ar|fa); "
                    "defaults to state.source_language or 'ur'")
    ap.add_argument("--force", action="store_true", help="Re-transcribe even if a lecture txt exists")
    ap.add_argument("--limit", type=int, default=None, help="Only process the first N lectures (testing)")
    args = ap.parse_args()
    return transcribe_audio_book(args.slug, language=args.language, force=args.force, limit=args.limit)


if __name__ == "__main__":
    sys.exit(main())
