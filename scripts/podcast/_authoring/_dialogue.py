"""_authoring/_dialogue.py — per-chapter dialogue-script authorship (Audio Engine v2).

Authors the full two-host dialogue script that an API audio engine renders
directly (no NotebookLM). Runs on Claude Max via `claude -p` — no API spend.

The script is authored FROM the same steering stack the NotebookLM framing
encodes — and the framing itself is the per-chapter distillation of that
stack (name discipline, pronunciation plan, governing analogies, spine
thesis, host roles, deny lists). So the prompt hands the model the framing
as the AUTHORITATIVE spec rather than duplicating rule text (per the Step-2
"reuse framing-rendering logic as the script spec" requirement). The framing
must therefore exist before script authorship — the orchestrator runs this
after the per-chapter convergence loop has shipped the framing.

Artifact: BOOK_DIR/_system/dialogue-scripts/EP##-<slug>.script.md
"""
from __future__ import annotations

import re as _re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ._core import (  # noqa: E402
    AuthoringError,
    DEFAULT_TIMEOUT,
    _run_claude_p_with_retry,
    _assert_artifact,
)

DIALOGUE_TIMEOUT = DEFAULT_TIMEOUT  # full-script authorship is the heaviest per-chapter call


def _episode_id_for_chapter(book_dir: Path, chapter_slug: str) -> tuple[str, Path]:
    """Resolve (EP##-<slug>, chapter_file) from the chapter slug.

    Mirrors _framing.author_framing's X7 numbering rule: letter-suffixed
    chapters (ch14b-...) map to the digits-only episode number (EP14-...).
    """
    chapter_files = sorted((book_dir / "chapters").glob(f"ch*-{chapter_slug}.txt"))
    if not chapter_files:
        raise AuthoringError(
            phase=f"dialogue/{chapter_slug}",
            message=f"chapter file missing for slug {chapter_slug} under {book_dir / 'chapters'}",
            manual_fallback="Run Phase 0d to produce the chapter files.",
        )
    chapter_file = chapter_files[0]
    _prefix = chapter_file.stem.split("-", 1)[0]
    _m = _re.match(r"ch(\d+)", _prefix)
    chap_num = _m.group(1) if _m else _prefix[2:]
    return f"EP{chap_num}-{chapter_slug}", chapter_file


def _read_length_tier(book_dir: Path) -> str:
    """length_tier from series-config.yaml (default default_deep_dive)."""
    cfg = book_dir / "_system" / "series-config.yaml"
    if cfg.exists():
        try:
            import yaml
            data = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
            tier = str(data.get("length_tier") or "").strip()
            if tier:
                return tier
        except Exception:  # noqa: BLE001
            pass
    return "default_deep_dive"


def author_dialogue_script(book_dir: Path, chapter_slug: str,
                           timeout: int = DIALOGUE_TIMEOUT) -> str:
    """Author the dialogue script for one chapter. Returns claude -p stdout.

    Reads:  BOOK_DIR/chapters/ch##-<slug>.txt           (the teaching content)
            BOOK_DIR/chapter-contracts/<slug>.yml        (tensions, format, anchors)
            BOOK_DIR/_system/episode-drafts/EP##-<slug>/00-framing.md
                                                         (the per-chapter steering spec)
    Writes: BOOK_DIR/_system/dialogue-scripts/EP##-<slug>.script.md
    """
    from _audio_engines import audio_engine_for_book
    from _dialogue_script import (
        script_path_for, soft_char_band, CHARS_PER_AUDIO_MINUTE,
    )

    engine = audio_engine_for_book(book_dir)
    episode_id, chapter_file = _episode_id_for_chapter(book_dir, chapter_slug)

    contract = book_dir / "chapter-contracts" / f"{chapter_slug}.yml"
    if not contract.exists():
        raise AuthoringError(
            phase=f"dialogue/{chapter_slug}",
            message=f"chapter contract missing: {contract}",
            manual_fallback="Run Phase 0d first to produce the contracts.",
        )
    framing = book_dir / "_system" / "episode-drafts" / episode_id / "00-framing.md"
    if not framing.exists():
        raise AuthoringError(
            phase=f"dialogue/{chapter_slug}",
            message=(
                f"framing missing: {framing} — the dialogue script is authored "
                f"AGAINST the framing (it is the per-chapter steering spec)."
            ),
            manual_fallback=(
                "Run the per-chapter loop first so the framing exists, then "
                "re-run dialogue authorship."
            ),
        )

    script_path = script_path_for(book_dir, episode_id)
    tier = _read_length_tier(book_dir)
    lo, hi = soft_char_band(tier)

    # Tag discipline — encodes the ear-locked lesson (2026-06-12): TONAL tags on
    # the scholar recolor his approved timbre; reaction tags belong to the seeker.
    if engine.supports_audio_tags:
        tags_note = (
            "Performance [tag] cues — REACTION tags go on the SEEKER (HOST_B) "
            "ONLY: [curious], [interrupting], [thoughtful], [quiet], [skeptical]. "
            "NEVER put a TONAL tag on the SCHOLAR (HOST_A) — tags like [warm], "
            "[smiling], [lowering voice] recolor his approved voice; at most a "
            "bare [pause] on HOST_A. Use a tag only where it carries a genuine "
            "reaction (not decoration); each tag is billed as audio characters."
        )
    else:
        tags_note = ("Do NOT use [tag] performance cues — this engine does not "
                     "support them.")

    # Script-language discipline. The author writes ASCII ONLY and NEVER types
    # Arabic script — even on engines that can pronounce it. Arabic is injected
    # downstream at the render-compile layer from VERIFIED sources (the wisdom
    # corpus KQur for verses; the per-book glossary for key terms), so the same
    # citation always recites the same canonical verse. A model typing Quran
    # Arabic from memory is a faithfulness risk and is forbidden.
    if engine.supports_arabic_script:
        script_lang_clause = (
            "  - ASCII only — do NOT type any Arabic script yourself, not even "
            "for verses. Write Arabic terms in plain transliteration exactly as "
            "the chapter carries them. Cite every Quran verse in LONG-FORM prose "
            "— 'the chapter of Abraham, verse seven' (named surah + verse number) "
            "— and quote its English meaning; the pipeline splices the verbatim "
            "Arabic recitation in from the corpus at render time, and pronounces "
            "key terms correctly from the glossary. Your job is the English words "
            "+ the precise citation, never the Arabic.\n\n"
        )
    else:
        script_lang_clause = (
            "  - ASCII only. NO Arabic script — Arabic terms appear in plain "
            "phonetic transliteration exactly as the chapter carries them "
            "(pronunciation is handled at synthesis by a pronunciation "
            "dictionary; do not respell terms).\n\n"
        )

    prompt = (
        f"You are writing the COMPLETE two-host dialogue script for episode "
        f"`{episode_id}` of book `{book_dir.name}` — the exact words the hosts "
        f"will speak. A text-to-dialogue engine renders this script verbatim; "
        f"there is no improvising host downstream. Every teaching must be IN the "
        f"script or it never reaches the listener.\n\n"
        f"INPUT (read all three):\n"
        f"  1. `{framing}` — the AUTHORITATIVE steering spec for this episode.\n"
        f"     Obey every section: Opening directive (including the verbatim spine "
        f"     thesis and its three placements), Name discipline (stable labels, "
        f"     honorifics exactly once at first mention), Pronunciation (each term "
        f"     spoken ONCE in its phonetic form; never term + respelling "
        f"     back-to-back), Three-part focus / beats, Host dynamic (including "
        f"     the sample friction lines), Tone constraints (ONLY the governing "
        f"     analogies named there), Landing, and the full Do-not list.\n"
        f"  2. `{chapter_file}` — the chapter. THIS IS THE CONTENT. The script "
        f"     must surface every teaching, every tension, every quoted passage, "
        f"     every concept this chapter carries. Quote the source verbatim "
        f"     where the framing or contract calls for it.\n"
        f"  3. `{contract}` — the chapter contract. Every entry in "
        f"     `key_tensions` and every concept the contract declares MUST be "
        f"     surfaced by name in the dialogue (a deterministic coverage gate "
        f"     checks this; a missing tension is a hard failure).\n\n"
        f"OUTPUT: `{script_path}`\n\n"
        f"FORMAT (line-oriented; a deterministic parser reads it):\n"
        f"  - Lines starting with `#` are comments. Start the file with:\n"
        f"      # {episode_id} — dialogue script\n"
        f"      # engine: {engine.name}\n"
        f"  - Every turn is ONE line: `HOST_A: <text>` or `HOST_B: <text>`.\n"
        f"  - HOST_A is the male scholar/teacher voice; HOST_B is the female "
        f"    seeker/questioner voice (R-HOST-ROLE-PARITY — roles never swap).\n"
        f"  - Blank lines between turns. No other prose, no headings, no stage "
        f"    directions outside turns.\n"
        f"  - {tags_note}\n"
        f"{script_lang_clause}"
        f"LENGTH (SOFT pacing band — content completeness OUTRANKS the band):\n"
        f"  Target {lo:,}-{hi:,} characters of spoken turn text "
        f"(~{lo // CHARS_PER_AUDIO_MINUTE}-{hi // CHARS_PER_AUDIO_MINUTE} minutes "
        f"of audio; length tier `{tier}`). NEVER cut a teaching, a tension, a "
        f"contracted concept, or a verbatim quotation to fit the band — if the "
        f"chapter needs more room, exceed the band; the gate flags pacing as P2 "
        f"(advisory), while a missing teaching is a hard failure. Do not pad "
        f"either: no filler, no recap loops, no invented material.\n\n"
        f"CONVERSATION CRAFT — the NotebookLM interactive style (every move must "
        f"appear; these are what make the audio feel like two people thinking, "
        f"not a lecture):\n"
        f"  1. COLD-OPEN HOOK: the very first turn poses THIS chapter's question "
        f"     straight to the listener — no 'welcome to the show' framing. Land "
        f"     the framing's spine thesis verbatim here.\n"
        f"  2. INTERRUPTION ECHOES: the seeker cuts in mid-exposition to echo a "
        f"     strange term back as a question ('Wait — the etiquette of asking?').\n"
        f"  3. TWO PUSHBACK-AND-CONCEDE ARCS: the seeker objects with real stakes "
        f"     ('I don't buy that yet — that sounds like wordplay'); the scholar "
        f"     answers with the source's OWN analogy; the seeker concedes "
        f"     explicitly ('All right — you have me there'). Use the framing's "
        f"     sample-friction lines as the model; concede only as it allows.\n"
        f"  4. SHORT REACTIVE BEATS: scatter 1-5 word turns at the narrative "
        f"     peaks ('And?' / 'Just sand.' / 'Nothing again.').\n"
        f"  5. MID-THOUGHT HANDOFFS: now and then one host completes the other's "
        f"     sentence ('You cannot thank a road with a word.' / 'You thank it "
        f"     by walking it.').\n"
        f"  6. RECURRING REFRAIN: the spine line lands ~3 times — teased at open, "
        f"     re-armed at the pivot, closed on.\n"
        f"  7. DIRECT-TO-LISTENER CLOSE: the final exchange turns the question "
        f"     back on the listener and ends on the chapter's unresolved image — "
        f"     the framing's Landing, NEVER a tidy summary.\n"
        f"  - Develop each beat fully before moving on; no topic-jumping. The "
        f"    scholar (HOST_A) leads exposition; the seeker (HOST_B) drives the "
        f"    friction. Everything in the framing's Do-not list is forbidden in "
        f"    the spoken text.\n\n"
        f"FAITHFULNESS (hard rule): do not invent doctrine, attributions, "
        f"quotations, or facts not present in the chapter file. The hosts may "
        f"rephrase and connect, but every claim traces to the source.\n\n"
        f"Do NOT modify any file other than `{script_path}`.\n"
        f"Exit when `{script_path}` is written."
    )

    rc, stdout, stderr = _run_claude_p_with_retry(
        prompt, timeout=timeout,
        book_dir=book_dir, phase="audio-script", step=f"dialogue/{chapter_slug}",
    )
    _assert_artifact(
        phase=f"dialogue/{chapter_slug}",
        path=script_path,
        rc=rc,
        stdout=stdout,
        stderr=stderr,
        manual_fallback=(
            f"1. /podcast — author the dialogue script for `{chapter_slug}` manually\n"
            f"   at {script_path} (HOST_A:/HOST_B: turn lines).\n"
            f"2. Re-invoke orchestrate-book --resume."
        ),
    )

    # Deterministic post-author sanity: the artifact must PARSE. Format errors
    # are systemic (prompt/template bugs), not content — fail loudly here.
    from _dialogue_script import parse_dialogue_script, DialogueScriptError
    try:
        parse_dialogue_script(script_path.read_text(encoding="utf-8"))
    except DialogueScriptError as e:
        raise AuthoringError(
            phase=f"dialogue/{chapter_slug}",
            message=f"authored script does not parse: {e}",
            manual_fallback=(
                f"Fix the format of {script_path} (HOST_A:/HOST_B: turn lines, "
                f"'#' comments only), then re-run."
            ),
        ) from e
    return stdout
