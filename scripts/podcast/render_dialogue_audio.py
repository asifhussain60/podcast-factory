#!/usr/bin/env python3
"""render_dialogue_audio.py — production ElevenLabs renderer (render once, cache forever).

Step 5 of Audio Engine v2. Renders a gated dialogue script into the SAME
canonical audio layout the NotebookLM path produces, so every downstream
consumer (postprod-review, stitch_video, the Astro site, publish gates)
works identically for both engines:

    m4a/ch<NN><s>-<slug>.m4a
    m4a/transcripts/ch<NN><s>-<slug>.transcript.txt    (script text, speaker-labeled)
    transcripts/EP<NN>-<slug>.transcript.txt           (byte-identical copy)

No fingerprint matching, no Azure STT spend on this path — the transcript
IS the script.

DETERMINISM CONTRACT (input-determinism + ledger; neural TTS itself is
best-effort reproducible):
  - pure chunker at turn boundaries, <= engine.max_chunk_chars per request
  - per-chunk seed derived from the chunk content hash
  - model id, voice ids, settings, dictionary version all pinned
  - render ledger (_system/render-ledger.jsonl): input-hash -> output-hash
  - chunk cache (_system/render-cache/<EP>/<input-hash>.mp3): an unchanged
    chunk is NEVER re-rendered — revisions re-spend only on changed chunks.

QUALITY GATES:
  - REFUSES to render any episode whose convergence verdict is not
    SHIP-READY / SHIP-WITH-CAUTION (the Step-3 gate owns content quality;
    nothing renders before a passing verdict).
  - free post-render sanity: chars-per-second band per chunk (catches
    truncation = cps too high, runaway = cps too low).
  - --deep-verify (optional, Azure spend): STT the final m4a and report
    token containment against the script.

SPEND: only here, only after gates, only with explicit approval (the
orchestrator's H1 halt, or --confirm on the CLI). Exact credits metered
from the subscription meter (start/end delta) into cost-ledger.jsonl.

Usage:
    python3 scripts/podcast/render_dialogue_audio.py <slug> --dry-run
    python3 scripts/podcast/render_dialogue_audio.py <slug> --confirm
    python3 scripts/podcast/render_dialogue_audio.py <slug> --episode EP01-... --confirm
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _audio_engines import (  # noqa: E402
    audio_engine_for_book, voices_for_book, credit_estimate, is_autonomous,
    engine_for_episode, ENGINE_NOTEBOOKLM,
)
from _dialogue_script import (  # noqa: E402
    parse_dialogue_script, script_path_for, script_char_count,
    chunk_turns, chunk_content_hash, chunk_seed, Turn,
)
from _dialogue_convergence import read_verdict  # noqa: E402

RENDER_LEDGER = "render-ledger.jsonl"
RENDER_CACHE_DIR = "render-cache"
SHIPPABLE_VERDICTS = ("SHIP-READY", "SHIP-WITH-CAUTION")

# Pinned synthesis settings (the proven experiment configuration).
DIALOGUE_SETTINGS: dict = {"stability": 0.0}
OUTPUT_FORMAT = "mp3_44100_128"

# Free post-render sanity band: spoken English runs ~12-18 chars/sec; a chunk
# far outside the band signals truncation (high) or runaway/silence (low).
CPS_MIN = 6.0
CPS_MAX = 28.0

EP_RE = re.compile(r"^EP(\d{2,})([a-z]?)-([a-z0-9][a-z0-9-]*)$")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class ChunkRender:
    index: int
    input_hash: str
    chars: int
    cached: bool
    output_sha256: str = ""
    duration_s: float | None = None
    cps: float | None = None
    sanity_ok: bool = True


@dataclass
class RenderResult:
    episode_id: str
    ch_stem: str
    verdict: str
    rendered: bool = False
    m4a_path: Path | None = None
    transcript_paths: list[Path] = field(default_factory=list)
    chunks: list[ChunkRender] = field(default_factory=list)
    chars_total: int = 0
    credits_estimated: int = 0
    credits_metered: int | None = None
    notes: list[str] = field(default_factory=list)
    # Post-render style gate (None when the gate did not run).
    style_score: float | None = None
    style_passed: bool | None = None

    @property
    def cache_hits(self) -> int:
        return sum(1 for c in self.chunks if c.cached)

    @property
    def sanity_failures(self) -> list[ChunkRender]:
        return [c for c in self.chunks if not c.sanity_ok]


# ─── canonical naming ─────────────────────────────────────────────────────────


def chapter_stem_for_episode(book_dir: Path, episode_id: str) -> str:
    """EP##-<slug> -> the canonical ch-stem (prefers the real chapters/ file

    so letter-suffixed chapters keep their suffix in the audio name)."""
    m = EP_RE.match(episode_id)
    if not m:
        raise ValueError(f"episode id {episode_id!r} does not match EP##-<slug>")
    num, slug = int(m.group(1)), m.group(3)
    for p in sorted((Path(book_dir) / "chapters").glob(f"ch*-{slug}.txt")):
        sm = re.match(r"^ch(\d{2})([a-z]?)-", p.stem)
        if sm and int(sm.group(1)) == num:
            return p.stem
    return f"ch{num:02d}-{slug}"


# ─── ffmpeg helpers (injectable for tests) ───────────────────────────────────


def _concat_to_m4a(chunk_files: list[Path], out_path: Path) -> None:
    """Concat the rendered mp3 chunks into one canonical .m4a (AAC)."""
    list_file = out_path.parent / f".{out_path.stem}.concat.txt"
    list_file.write_text(
        "".join(f"file '{p.resolve()}'\n" for p in chunk_files), encoding="utf-8")
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
             "-i", str(list_file), "-c:a", "aac", "-b:a", "128k", str(out_path)],
            check=True, capture_output=True)
    finally:
        list_file.unlink(missing_ok=True)


def _audio_duration_s(path: Path) -> float | None:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, check=True).stdout.strip()
        return float(out)
    except Exception:  # noqa: BLE001 — ffprobe absent => sanity check skipped
        return None


# ─── render ledger ────────────────────────────────────────────────────────────


def _append_render_ledger(book_dir: Path, rows: list[dict]) -> None:
    ledger = Path(book_dir) / "_system" / RENDER_LEDGER
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")


# ─── the renderer ─────────────────────────────────────────────────────────────


def render_episode(
    book_dir: Path,
    episode_id: str,
    *,
    client=None,
    approved: bool = False,
    deep_verify: bool = False,
    style_gate: bool = False,
    style_retake_budget: int = 1,
    concat=_concat_to_m4a,
    duration_probe=_audio_duration_s,
    meter_settle_s: float = 5.0,
    log=print,
) -> RenderResult:
    """Render one episode's gated script to canonical audio + transcripts.

    Refuses without a shippable gate verdict; refuses paid synthesis without
    *approved* (the H1 contract). Cache hits cost nothing and need no
    approval — a fully-cached episode re-assembles for free.

    *style_gate* (default OFF): after assembly, fingerprint the audio against
    the genre gold standard (content/_shared/audio-style/<profile>.json). When
    it scores below threshold and *style_retake_budget* > 0 AND spend is
    approved, render ONE alternate take (salted seed) and keep the better one.
    A residual sub-threshold score surfaces via result.style_passed/notes — it
    is a quality FLAG, never a hard block. Default-off keeps every existing
    caller and test byte-identical.
    """
    book_dir = Path(book_dir)
    engine = audio_engine_for_book(book_dir)
    if not is_autonomous(engine):
        raise RuntimeError(
            f"book {book_dir.name!r} uses audio_engine={engine.name!r} "
            f"(render_mode={engine.render_mode}) — nothing to render via API.")
    # Defense-in-depth: an episode flipped to NotebookLM via
    # episode_engine_overrides is rendered manually, never here — refuse even a
    # direct --episode CLI call so a flipped episode can't be rendered by mistake.
    if engine_for_episode(book_dir, episode_id) == ENGINE_NOTEBOOKLM:
        raise RuntimeError(
            f"REFUSED: episode {episode_id} is overridden to notebooklm "
            f"(episode_engine_overrides) — generate it in NotebookLM and drop the "
            f"m4a into m4a/; it is never API-rendered.")

    verdict = read_verdict(book_dir, episode_id)
    result = RenderResult(episode_id=episode_id,
                          ch_stem=chapter_stem_for_episode(book_dir, episode_id),
                          verdict=verdict or "(none)")
    if verdict not in SHIPPABLE_VERDICTS:
        raise RuntimeError(
            f"REFUSED: episode {episode_id} has gate verdict {verdict!r} — "
            f"nothing renders before a passing verdict "
            f"(run the dialogue convergence loop first).")

    script = script_path_for(book_dir, episode_id)
    turns = parse_dialogue_script(script.read_text(encoding="utf-8"))

    # Script-compile layer: Arabic-recitation scaffold (identity until H2).
    from pronunciation_compiler import compile_turns_for_render, ensure_dictionary
    turns = compile_turns_for_render(book_dir, turns)

    voices = voices_for_book(book_dir)
    chunks = chunk_turns(turns, engine.max_chunk_chars)
    result.chars_total = script_char_count(turns)
    result.credits_estimated = credit_estimate(engine, result.chars_total)

    if client is None:
        from _elevenlabs import ElevenLabsClient
        client = ElevenLabsClient()

    # Pronunciation dictionary: compile + pin (upload only on glossary change).
    locator = ensure_dictionary(book_dir, client, log=log)
    dictionary_version = locator["version_id"] if locator else ""
    locators = [locator] if locator else None

    cache_dir = book_dir / "_system" / RENDER_CACHE_DIR / episode_id
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Plan: which chunks are cache hits vs paid renders?
    plan: list[tuple[int, list[Turn], str, Path]] = []
    to_render = 0
    for i, chunk in enumerate(chunks):
        ihash = chunk_content_hash(
            chunk, model_id=engine.model_id, voices=voices,
            dictionary_version=dictionary_version)
        cpath = cache_dir / f"{ihash}.mp3"
        plan.append((i, chunk, ihash, cpath))
        if not cpath.exists():
            to_render += 1

    if to_render and not approved:
        raise RuntimeError(
            f"REFUSED: {to_render}/{len(chunks)} chunk(s) need PAID synthesis "
            f"(estimate {result.credits_estimated:,} credits for the full "
            f"script) and spend is not approved. Pass approved=True "
            f"(orchestrator H1) or --confirm (CLI).")

    meter_start: int | None = None
    if to_render:
        try:
            meter_start = int(client.subscription().get("character_count"))
        except Exception as e:  # noqa: BLE001 — meter probe is best-effort
            log(f"  [render] WARN subscription meter probe failed: {e}")

    ledger_rows: list[dict] = []
    chunk_files: list[Path] = []
    for i, chunk, ihash, cpath in plan:
        chars = sum(len(t.text) for t in chunk)
        cr = ChunkRender(index=i, input_hash=ihash, chars=chars,
                         cached=cpath.exists())
        if not cr.cached:
            seed = chunk_seed(ihash)
            log(f"  [render] chunk {i + 1}/{len(chunks)}: {len(chunk)} turns, "
                f"{chars:,} chars, seed={seed}")
            audio = client.text_to_dialogue(
                [{"text": t.text, "voice_id": voices[t.speaker.lower()]}
                 for t in chunk],
                model_id=engine.model_id,
                seed=seed,
                settings=DIALOGUE_SETTINGS,
                pronunciation_dictionary_locators=locators,
                output_format=OUTPUT_FORMAT)
            cpath.write_bytes(audio)
        else:
            log(f"  [render] chunk {i + 1}/{len(chunks)}: cache hit ({ihash[:12]})")
        data = cpath.read_bytes()
        cr.output_sha256 = hashlib.sha256(data).hexdigest()
        cr.duration_s = duration_probe(cpath)
        if cr.duration_s and cr.duration_s > 0:
            cr.cps = round(chars / cr.duration_s, 2)
            cr.sanity_ok = CPS_MIN <= cr.cps <= CPS_MAX
            if not cr.sanity_ok:
                result.notes.append(
                    f"chunk {i}: {cr.cps} chars/sec outside [{CPS_MIN}, {CPS_MAX}] "
                    f"— possible {'truncation' if cr.cps > CPS_MAX else 'runaway/silence'}")
        result.chunks.append(cr)
        chunk_files.append(cpath)
        ledger_rows.append({
            "ts": _utc_now(), "episode_id": episode_id, "chunk_index": i,
            "input_hash": ihash, "output_sha256": cr.output_sha256,
            "chars": chars, "cached": cr.cached,
            "seed": chunk_seed(ihash), "model_id": engine.model_id,
            "voices": voices, "dictionary_version": dictionary_version,
            "settings": DIALOGUE_SETTINGS,
            "duration_s": cr.duration_s, "cps": cr.cps, "sanity_ok": cr.sanity_ok,
        })
    _append_render_ledger(book_dir, ledger_rows)

    # Exact credit metering (subscription delta — the experiment's pattern).
    if to_render and meter_start is not None:
        try:
            time.sleep(meter_settle_s)  # let the usage meter settle
            meter_end = int(client.subscription().get("character_count"))
            result.credits_metered = meter_end - meter_start
            from _cost_ledger import append_elevenlabs_cost
            append_elevenlabs_cost(
                book_dir, phase="audio-render", step=episode_id,
                credits=result.credits_metered, char_count=result.chars_total)
            log(f"  [render] credits this render: {result.credits_metered:,} "
                f"(estimate was {result.credits_estimated:,})")
        except Exception as e:  # noqa: BLE001
            result.notes.append(f"credit metering failed: {e}")

    # Assemble canonical outputs.
    m4a_dir = book_dir / "m4a"
    m4a_dir.mkdir(parents=True, exist_ok=True)
    out_m4a = m4a_dir / f"{result.ch_stem}.m4a"
    concat(chunk_files, out_m4a)
    result.m4a_path = out_m4a

    transcript_text = "\n\n".join(f"{t.speaker}: {t.text}" for t in turns) + "\n"
    tx1 = m4a_dir / "transcripts" / f"{result.ch_stem}.transcript.txt"
    tx1.parent.mkdir(parents=True, exist_ok=True)
    tx1.write_text(transcript_text, encoding="utf-8")
    tx2 = book_dir / "transcripts" / f"{episode_id}.transcript.txt"
    tx2.parent.mkdir(parents=True, exist_ok=True)
    tx2.write_text(transcript_text, encoding="utf-8")
    result.transcript_paths = [tx1, tx2]
    result.rendered = True

    # ── Post-render style gate (default off) ─────────────────────────────────
    if style_gate:
        _apply_style_gate(
            book_dir, episode_id, result, out_m4a, transcript_text,
            chunks=chunks, voices=voices, engine=engine, locators=locators,
            dictionary_version=dictionary_version, cache_dir=cache_dir,
            m4a_dir=m4a_dir, concat=concat, client=client, approved=approved,
            style_retake_budget=style_retake_budget,
            meter_settle_s=meter_settle_s, log=log)

    if deep_verify:
        _deep_verify(book_dir, result, transcript_text, log=log)

    log(f"  [render] {episode_id}: wrote {out_m4a.name} "
        f"({len(chunks)} chunks, {result.cache_hits} cached, "
        f"{len(result.sanity_failures)} sanity flags)")
    return result


def _render_salted_take(client, chunks, voices, engine, locators,
                        dictionary_version, cache_dir, take_salt, log) -> list[Path]:
    """Render an ALTERNATE take of every chunk (salted seed -> distinct delivery).

    Cache-keyed by the salted hash so a repeat call is free; only un-cached
    salted chunks hit the paid API. Returns the chunk file paths to assemble.
    """
    files: list[Path] = []
    for i, chunk in enumerate(chunks):
        ihash = chunk_content_hash(
            chunk, model_id=engine.model_id, voices=voices,
            dictionary_version=dictionary_version, take_salt=take_salt)
        cpath = cache_dir / f"{ihash}.mp3"
        if not cpath.exists():
            audio = client.text_to_dialogue(
                [{"text": t.text, "voice_id": voices[t.speaker.lower()]}
                 for t in chunk],
                model_id=engine.model_id, seed=chunk_seed(ihash),
                settings=DIALOGUE_SETTINGS,
                pronunciation_dictionary_locators=locators,
                output_format=OUTPUT_FORMAT)
            cpath.write_bytes(audio)
            log(f"  [style] retake chunk {i + 1}/{len(chunks)}: {ihash[:12]}")
        files.append(cpath)
    return files


def _apply_style_gate(book_dir, episode_id, result, out_m4a, transcript_text, *,
                      chunks, voices, engine, locators, dictionary_version,
                      cache_dir, m4a_dir, concat, client, approved,
                      style_retake_budget, meter_settle_s, log) -> None:
    """Fingerprint the assembled audio vs the gold standard; one bounded retake.

    A quality FLAG, never a block: keeps the better-scoring take and records a
    residual sub-threshold score on the result for the review channel. The
    retake re-spends, so it runs ONLY when spend is approved (inside the H1
    scope) and is logged to the cost ledger.
    """
    from _content_profile import resolve_content_profile
    from _audio_fingerprint import fingerprint_m4a, score_against_profile, word_count

    profile = resolve_content_profile(book_dir)
    words = word_count(transcript_text)
    base = score_against_profile(fingerprint_m4a(out_m4a, words=words), profile)
    result.style_score = base.get("score")
    result.style_passed = base.get("passed", True)
    if base.get("score") is None:
        log(f"  [style] {episode_id}: no gold standard for profile {profile!r} — skipped")
        return
    log(f"  [style] {episode_id}: score {base['score']} "
        f"(threshold {base['threshold']}, passed={base['passed']})")

    if base.get("passed") or style_retake_budget <= 0 or not approved:
        if not base.get("passed"):
            result.notes.append(
                f"style score {base['score']} below threshold "
                f"{base['threshold']} (no retake: budget/approval)")
        return

    log(f"  [style] {episode_id}: below threshold — rendering ONE retake (salted seed)")
    try:
        r_start = int(client.subscription().get("character_count"))
    except Exception:  # noqa: BLE001
        r_start = None
    cand_files = _render_salted_take(
        client, chunks, voices, engine, locators, dictionary_version,
        cache_dir, "retake1", log)
    cand_m4a = m4a_dir / f".{result.ch_stem}.retake.m4a"
    concat(cand_files, cand_m4a)
    cand = score_against_profile(fingerprint_m4a(cand_m4a, words=words), profile)

    if r_start is not None:
        try:
            time.sleep(meter_settle_s)
            retake_credits = int(client.subscription().get("character_count")) - r_start
            result.credits_metered = (result.credits_metered or 0) + retake_credits
            from _cost_ledger import append_elevenlabs_cost
            append_elevenlabs_cost(
                book_dir, phase="audio-render", step=f"{episode_id}/style-retake",
                credits=retake_credits, char_count=result.chars_total)
            log(f"  [style] retake credits: {retake_credits:,}")
        except Exception as e:  # noqa: BLE001
            result.notes.append(f"style retake metering failed: {e}")

    if (cand.get("score") or 0) > (base.get("score") or 0):
        cand_m4a.replace(out_m4a)
        result.style_score = cand["score"]
        result.style_passed = cand.get("passed", False)
        result.notes.append(
            f"style retake kept ({base['score']} -> {cand['score']})")
        log(f"  [style] retake WON: {base['score']} -> {cand['score']}")
    else:
        cand_m4a.unlink(missing_ok=True)
        result.notes.append(
            f"style retake discarded (base {base['score']} >= retake {cand.get('score')})")
        log(f"  [style] retake kept base ({base['score']} >= {cand.get('score')})")
    if not result.style_passed:
        result.notes.append(
            f"style score {result.style_score} still below threshold "
            f"{base['threshold']} after retake — review before publish")


def _deep_verify(book_dir: Path, result: RenderResult, script_text: str,
                 *, log=print) -> None:
    """Optional Azure STT verification: transcribe the final m4a and report

    token containment vs the script. Writes the report under m4a/_review/;
    never overwrites the canonical (script-derived) transcripts."""
    try:
        import _azure
        from _engine import engine_guard, TASK_TRANSCRIBE, ENGINE_AZURE
        engine_guard(TASK_TRANSCRIBE, ENGINE_AZURE)
        creds = _azure.load_speech_creds()
        stt = _azure.transcribe_audio(
            creds, result.m4a_path.read_bytes(), result.m4a_path.name)
        script_tokens = {w for w in re.split(r"[^a-z0-9']+", script_text.lower())
                         if len(w) > 3}
        stt_tokens = {w for w in re.split(r"[^a-z0-9']+", stt.lower()) if len(w) > 3}
        containment = (len(script_tokens & stt_tokens) / len(script_tokens)
                       if script_tokens else 0.0)
        review = book_dir / "m4a" / "_review"
        review.mkdir(parents=True, exist_ok=True)
        report = review / f"{result.ch_stem}.deep-verify.json"
        report.write_text(json.dumps({
            "ts": _utc_now(), "episode_id": result.episode_id,
            "token_containment": round(containment, 3),
            "script_tokens": len(script_tokens), "stt_tokens": len(stt_tokens),
        }, indent=2) + "\n", encoding="utf-8")
        result.notes.append(f"deep-verify token containment: {containment:.1%}")
        try:
            from _cost_ledger import append_azure_stt_cost
            dur = _audio_duration_s(result.m4a_path) or 0.0
            append_azure_stt_cost(book_dir, phase="audio-render",
                                  step=f"deep-verify/{result.ch_stem}",
                                  duration_seconds=dur)
        except Exception:  # noqa: BLE001
            pass
        log(f"  [deep-verify] containment {containment:.1%} -> {report.name}")
    except Exception as e:  # noqa: BLE001 — verification is optional, never fatal
        result.notes.append(f"deep-verify failed: {e}")
        log(f"  [deep-verify] WARN: {e}")


def episodes_with_scripts(book_dir: Path) -> list[str]:
    """Episode ids that have a script artifact, in order."""
    d = Path(book_dir) / "_system" / "dialogue-scripts"
    if not d.is_dir():
        return []
    return sorted(p.name.removesuffix(".script.md")
                  for p in d.glob("EP*.script.md"))


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Render gated dialogue scripts via ElevenLabs into the canonical m4a layout.")
    ap.add_argument("slug", help="book slug (any bucket)")
    ap.add_argument("--episode", help="single EP##-<slug> (default: all gated scripts)")
    ap.add_argument("--confirm", action="store_true",
                    help="approve PAID synthesis (H1 spend approval)")
    ap.add_argument("--deep-verify", action="store_true",
                    help="STT-verify the rendered audio via Azure (extra spend)")
    ap.add_argument("--dry-run", action="store_true",
                    help="show the render plan + credit estimate, render nothing")
    args = ap.parse_args()

    from _paths import find_content
    found = find_content(args.slug)
    if not found:
        print(f"ERROR: no content directory matches slug {args.slug!r}", file=sys.stderr)
        return 2
    book_dir = found[2]

    targets = [args.episode] if args.episode else episodes_with_scripts(book_dir)
    if not targets:
        print("no dialogue scripts found — author + gate them first.", file=sys.stderr)
        return 1

    if args.dry_run:
        engine = audio_engine_for_book(book_dir)
        total = 0
        for ep in targets:
            sp = script_path_for(book_dir, ep)
            if not sp.exists():
                print(f"  {ep}: NO SCRIPT")
                continue
            turns = parse_dialogue_script(sp.read_text(encoding="utf-8"))
            chars = script_char_count(turns)
            est = credit_estimate(engine, chars)
            total += est
            print(f"  {ep}: verdict={read_verdict(book_dir, ep) or '(none)'} "
                  f"chars={chars:,} est={est:,} credits")
        print(f"\nTOTAL estimate: {total:,} credits")
        return 0

    failures = 0
    for ep in targets:
        try:
            render_episode(book_dir, ep, approved=args.confirm,
                           deep_verify=args.deep_verify)
        except Exception as e:  # noqa: BLE001
            failures += 1
            print(f"ERROR [{ep}]: {e}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
