"""_dialogue_script.py — dialogue-script artifact format + pure helpers (Audio Engine v2).

The per-chapter dialogue script is the autonomous-audio analog of the
chapter+framing pair: a full two-host conversation, written turn by turn,
that an API engine (ElevenLabs v3 text-to-dialogue) renders directly.

ARTIFACT

    BOOK_DIR/_system/dialogue-scripts/EP##-<slug>.script.md

FORMAT (line-oriented, deterministic to parse):

    # EP01-the-lamp-and-the-wick — dialogue script        <- '#' lines are comments
    HOST_A: [warm] Welcome. We're with ...                 <- speaker turn
    HOST_B: And the question the chapter opens with ...
    HOST_A: A continuation line without a speaker prefix
      is appended to the previous turn.

  - Speakers are exactly HOST_A (male scholar voice) and HOST_B (female
    seeker voice) per R-HOST-ROLE-PARITY.
  - Sparse performance tags like [warm] / [thoughtful] ride inside the turn
    text (ElevenLabs v3 audio tags). They are BILLED as characters — the
    authoring prompt keeps them sparse; validators count them.
  - Arabic SCRIPT never appears here at authorship time (scripts are
    phonetic-only, like chapters). Native-script recitation is a
    script-COMPILE-layer feature behind a per-book flag (Step 4 / halt H2).

This module is pure: parsing, serialization, soft character bands, the
deterministic chunker, and hash-derived seeds. No network, no LLM calls.
The renderer (render_dialogue_audio.py) and the gate (_validators_dialogue.py)
both import from here so the format can never drift between them.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

SPEAKERS = ("HOST_A", "HOST_B")
TURN_RE = re.compile(r"^(HOST_A|HOST_B):\s+(\S.*)$")
AUDIO_TAG_RE = re.compile(r"\[[a-z][a-z0-9 _-]{1,30}\]")

# ~chars of dialogue per minute of rendered audio (empirical from the
# elevenlabs-audition experiment: chars // 900 ≈ minutes).
CHARS_PER_AUDIO_MINUTE = 900

# SOFT character bands per length tier — pacing targets that mirror the
# word-count soft bands on the NotebookLM path. CONTENT COMPLETENESS OUTRANKS
# THE BAND: a script over its band is a P2 pacing flag, NEVER a cut.
SOFT_CHAR_BANDS: dict[str, tuple[int, int]] = {
    "brief": (6 * CHARS_PER_AUDIO_MINUTE, 10 * CHARS_PER_AUDIO_MINUTE),
    "default_deep_dive": (12 * CHARS_PER_AUDIO_MINUTE, 15 * CHARS_PER_AUDIO_MINUTE),
    "longer": (22 * CHARS_PER_AUDIO_MINUTE, 40 * CHARS_PER_AUDIO_MINUTE),
    "extended": (50 * CHARS_PER_AUDIO_MINUTE, 60 * CHARS_PER_AUDIO_MINUTE),
}
DEFAULT_LENGTH_TIER = "default_deep_dive"


class DialogueScriptError(ValueError):
    """Raised when a script artifact cannot be parsed into speaker turns."""


@dataclass(frozen=True)
class Turn:
    speaker: str  # "HOST_A" | "HOST_B"
    text: str  # turn text, may carry sparse [tag] cues


def script_path_for(book_dir: Path, episode_id: str) -> Path:
    """Canonical script artifact path for an EP##-<slug> episode id."""
    return Path(book_dir) / "_system" / "dialogue-scripts" / f"{episode_id}.script.md"


def parse_dialogue_script(text: str) -> list[Turn]:
    """Parse script text into an ordered list of Turns.

    Rules: '#' lines and blank lines are ignored; a 'HOST_X: ...' line starts
    a turn; any other non-blank line continues the previous turn (joined with
    a single space). Raises DialogueScriptError when no turns parse or when a
    continuation line appears before the first turn.
    """
    turns: list[tuple[str, list[str]]] = []
    for ln_no, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = TURN_RE.match(line)
        if m:
            turns.append((m.group(1), [m.group(2).strip()]))
            continue
        if not turns:
            raise DialogueScriptError(
                f"line {ln_no}: content before the first speaker turn "
                f"(expected 'HOST_A: ...' or 'HOST_B: ...'): {line.strip()[:80]!r}"
            )
        turns[-1][1].append(line.strip())
    if not turns:
        raise DialogueScriptError("no speaker turns found — script must contain 'HOST_A: ...' / 'HOST_B: ...' lines.")
    return [Turn(speaker=s, text=" ".join(parts)) for s, parts in turns]


def serialize_dialogue_script(turns: list[Turn], episode_id: str, engine_name: str) -> str:
    """Render turns back to the canonical on-disk format (round-trip stable)."""
    lines = [
        f"# {episode_id} — dialogue script",
        f"# engine: {engine_name}",
        "# format: HOST_A / HOST_B speaker turns; sparse [tag] cues allowed.",
        "",
    ]
    for t in turns:
        lines.append(f"{t.speaker}: {t.text}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def script_char_count(turns: list[Turn]) -> int:
    """Billable character count: the sum of turn-text lengths (tags included —

    ElevenLabs bills audio tags as characters)."""
    return sum(len(t.text) for t in turns)


def audio_tag_count(turns: list[Turn]) -> int:
    """Number of [tag] performance cues across the script (sparseness check)."""
    return sum(len(AUDIO_TAG_RE.findall(t.text)) for t in turns)


def soft_char_band(length_tier: str | None) -> tuple[int, int]:
    """The SOFT pacing band for a length tier (unknown tiers -> default)."""
    return SOFT_CHAR_BANDS.get(length_tier or "", SOFT_CHAR_BANDS[DEFAULT_LENGTH_TIER])


def estimated_minutes(char_count: int) -> float:
    """Rough rendered-audio duration for a script of *char_count* characters."""
    return round(char_count / CHARS_PER_AUDIO_MINUTE, 1)


# ─── Deterministic chunker (render requests) ─────────────────────────────────

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _split_long_turn(turn: Turn, max_chars: int) -> list[Turn]:
    """Split one over-long turn at sentence boundaries into same-speaker parts.

    Deterministic: greedy sentence packing. A single sentence longer than
    max_chars is split at the last space before the limit (degenerate case;
    never expected from real authorship but must not crash the renderer).
    """
    if len(turn.text) <= max_chars:
        return [turn]
    sentences = _SENTENCE_SPLIT_RE.split(turn.text)
    parts: list[str] = []
    cur = ""
    for s in sentences:
        while len(s) > max_chars:  # degenerate: one sentence over the limit
            if cur:
                parts.append(cur)
                cur = ""
            cut = s.rfind(" ", 0, max_chars)
            cut = cut if cut > 0 else max_chars
            parts.append(s[:cut].strip())
            s = s[cut:].strip()
        candidate = f"{cur} {s}".strip() if cur else s
        if len(candidate) > max_chars and cur:
            parts.append(cur)
            cur = s
        else:
            cur = candidate
    if cur:
        parts.append(cur)
    return [Turn(speaker=turn.speaker, text=p) for p in parts if p]


def chunk_turns(turns: list[Turn], max_chars: int) -> list[list[Turn]]:
    """Pack turns into render-request chunks of <= max_chars total text.

    Pure function of (turns, max_chars): same input -> same chunks, always.
    Chunk boundaries fall at turn boundaries; a single turn longer than
    max_chars is first split at sentence boundaries (same speaker).
    """
    if max_chars <= 0:
        raise ValueError(f"max_chars must be positive (got {max_chars})")
    flat: list[Turn] = []
    for t in turns:
        flat.extend(_split_long_turn(t, max_chars))
    chunks: list[list[Turn]] = []
    cur: list[Turn] = []
    cur_len = 0
    for t in flat:
        if cur and cur_len + len(t.text) > max_chars:
            chunks.append(cur)
            cur, cur_len = [], 0
        cur.append(t)
        cur_len += len(t.text)
    if cur:
        chunks.append(cur)
    return chunks


def chunk_content_hash(
    chunk: list[Turn],
    *,
    model_id: str = "",
    voices: dict[str, str] | None = None,
    dictionary_version: str = "",
    take_salt: str = "",
) -> str:
    """Stable content hash for a chunk + its pinned render settings.

    The render ledger keys on this: same text + same speaker sequence + same
    pinned model/voices/dictionary-version -> same hash -> cache hit (never
    re-render, never re-spend).

    *take_salt* (default "") seeds an ALTERNATE take for the style-gate retake:
    a non-empty salt yields a distinct hash (hence a distinct seed + cache file)
    so the retake renders a different delivery instead of returning the cached
    canonical take. The empty default keeps every existing hash and cache entry
    byte-identical — the canonical take is never salted.
    """
    h = hashlib.sha256()
    for t in chunk:
        h.update(t.speaker.encode("utf-8"))
        h.update(b"\x00")
        h.update(t.text.encode("utf-8"))
        h.update(b"\x01")
    h.update(model_id.encode("utf-8"))
    h.update(b"\x02")
    for k in sorted(voices or {}):
        h.update(f"{k}={voices[k]}".encode("utf-8"))
        h.update(b"\x03")
    h.update(dictionary_version.encode("utf-8"))
    if take_salt:
        h.update(b"\x04")
        h.update(take_salt.encode("utf-8"))
    return h.hexdigest()


def chunk_seed(content_hash: str) -> int:
    """Best-effort determinism seed derived from the chunk content hash.

    ElevenLabs accepts seed in [0, 4294967295]; vendor states determinism is
    best-effort only — the pipeline's real determinism contract is the input
    hash + render ledger, this seed just nudges the synthesis toward
    reproducibility.
    """
    return int(content_hash[:8], 16)  # first 4 bytes of the sha256 -> 0..2^32-1
