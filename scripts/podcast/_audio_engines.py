"""_audio_engines.py — pluggable audio-engine registry (Audio Engine v2, 2026-06-12).

SINGLE SOURCE OF TRUTH for which audio engine renders a book's episodes and
what each engine can do. Mirrors the CONTENT_TYPE_REGISTRY pattern in
_rules.py and the task-policy pattern in _engine.py: adding an engine is ONE
entry here (extensibility-first rule) — validators, the cost estimator, the
orchestrator, and the Astro site all read capabilities from this registry,
never from hardcoded engine conditionals.

A book declares its engine in `_system/series-config.yaml`:

    audio_engine: notebooklm   # default — manual NotebookLM upload/download
    audio_engine: elevenlabs   # autonomous ElevenLabs v3 text-to-dialogue

A missing field means `notebooklm` — every pre-existing book behaves
byte-identically to before this module existed (golden-fixture test:
tests/test_audio_engines.py). An explicitly UNKNOWN value raises ValueError
so a typo can never silently fall back to the wrong render path (same
philosophy as _engine.select_engine).

Engine facts (verified against ElevenLabs docs 2026-06-12):
  - All FINAL renders use `eleven_v3` via POST /v1/text-to-dialogue
    (~1 credit/char). Flash v2.5 is auditions-only, never finals.
  - <= 2,000 characters per dialogue request (documented reliability limit).
  - v3 supports Arabic script and mixed-language text; audio tags such as
    [warm] are billed as characters — keep sparse.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

ENGINE_NOTEBOOKLM = "notebooklm"
ENGINE_ELEVENLABS = "elevenlabs"

DEFAULT_AUDIO_ENGINE = ENGINE_NOTEBOOKLM

RENDER_MODE_MANUAL = "manual"   # human uploads source + framing, downloads m4a
RENDER_MODE_API = "api"         # pipeline renders audio autonomously

# Notional USD per ElevenLabs credit for the cost ledger's usd column.
# Creator plan list price ($22 / 100k credits). Credits are the REAL meter;
# the usd figure is a convenience estimate surfaced next to it, never instead
# of it. Update if the subscription tier changes.
ELEVENLABS_USD_PER_CREDIT = 22.0 / 100_000


@dataclass(frozen=True)
class AudioEngine:
    """Capability card for one audio engine. All consumers read THESE flags."""
    name: str
    render_mode: str              # RENDER_MODE_MANUAL | RENDER_MODE_API
    supports_arabic_script: bool  # may engine-specific artifacts carry Arabic Unicode?
    supports_audio_tags: bool     # [warm]-style performance tags allowed in scripts?
    max_chunk_chars: int          # per render-request character ceiling (0 = n/a)
    credit_rate: float            # synthesis credits per character (0.0 = unmetered)
    model_id: str                 # pinned synthesis model id ("" = n/a)
    # Tag-budget: the deterministic gate flags more than one [tag] per this many
    # turns. v3 WANTS expressive reaction tags, so its budget is looser than the
    # old flat 1-per-6 cap (which produced flat audio). Registry-driven so the
    # ceiling lives with the engine capability, not hardcoded in the validator.
    tag_budget_per_turns: int = 6
    # Default voice casting (host key -> vendor voice id). Per R-HOST-ROLE-PARITY
    # Host A is the male scholar voice, Host B the female seeker voice.
    # Per-book override: series-config.yaml `elevenlabs_voices: {host_a: .., host_b: ..}`.
    default_voices: dict = field(default_factory=dict)


AUDIO_ENGINE_REGISTRY: dict[str, AudioEngine] = {
    ENGINE_NOTEBOOKLM: AudioEngine(
        name=ENGINE_NOTEBOOKLM,
        render_mode=RENDER_MODE_MANUAL,
        supports_arabic_script=False,   # R-PHONETICS-OUT: TTS path is phonetic-only
        supports_audio_tags=False,
        max_chunk_chars=0,
        credit_rate=0.0,
        model_id="",
        default_voices={},
    ),
    # ── QUARANTINED / DORMANT (2026-06-14) ──────────────────────────────────
    # NO book currently uses this engine: every content profile defaults to
    # `notebooklm` (_rules.audio_engine_default_for_profile), and Islamic
    # scholarly content was confirmed on NotebookLM 2026-06-13. ElevenLabs is
    # RETAINED, not deleted, on purpose: it is the only autonomous (API) engine,
    # so keeping this registry entry preserves the one-engine-among-many seam
    # (extensibility-first rule) and the path to fully hands-off audio for a
    # future fiction/technical book. NotebookLM books never execute its render
    # code — the audio-script / audio-render phases skip it via is_autonomous().
    # To reactivate: set `audio_engine: elevenlabs` in a book's series-config.yaml.
    ENGINE_ELEVENLABS: AudioEngine(
        name=ENGINE_ELEVENLABS,
        render_mode=RENDER_MODE_API,
        supports_arabic_script=True,
        supports_audio_tags=True,
        max_chunk_chars=2000,           # documented reliability limit per request
        credit_rate=1.0,                # eleven_v3: ~1 credit/char (API discounted)
        model_id="eleven_v3",
        tag_budget_per_turns=3,         # v3 wants reaction tags — looser than the default
        default_voices={
            # Daniel — measured male, broadcast (scholar / Host A).
            "host_a": "onwK4e9ZLuTAKqWW03F9",
            # Sarah — warm female, narrative (seeker / Host B).
            "host_b": "EXAVITQu4vr4xnSDxMaL",
        },
    ),
}

AUDIO_ENGINES: tuple[str, ...] = tuple(AUDIO_ENGINE_REGISTRY)


def get_engine(name: str) -> AudioEngine:
    """Return the AudioEngine card for *name*. Raises ValueError on unknown names

    so a typo never silently routes a book down the wrong render path.
    """
    try:
        return AUDIO_ENGINE_REGISTRY[name]
    except KeyError:
        raise ValueError(
            f"unknown audio_engine {name!r}. Known engines: {sorted(AUDIO_ENGINE_REGISTRY)}. "
            f"Add new engines to AUDIO_ENGINE_REGISTRY in _audio_engines.py — "
            f"engine choice must never be implicit."
        ) from None


def resolve_audio_engine(book_dir: Path) -> str:
    """Return the audio_engine name declared in *book_dir*/_system/series-config.yaml.

    Missing file / missing field -> DEFAULT_AUDIO_ENGINE (notebooklm), so every
    book that predates this module behaves exactly as before. An explicit but
    unrecognized value raises ValueError (loud failure beats a silent fallback
    that would strand an autonomous book at a manual halt, or vice versa).
    """
    cfg_path = Path(book_dir) / "_system" / "series-config.yaml"
    if not cfg_path.exists():
        return DEFAULT_AUDIO_ENGINE
    try:
        import yaml
        with cfg_path.open() as f:
            cfg = yaml.safe_load(f) or {}
    except Exception:
        return DEFAULT_AUDIO_ENGINE
    raw = cfg.get("audio_engine")
    if raw is None or str(raw).strip() == "":
        return DEFAULT_AUDIO_ENGINE
    name = str(raw).strip().lower()
    get_engine(name)  # raises ValueError on unknown
    return name


def audio_engine_for_book(book_dir: Path) -> AudioEngine:
    """Convenience: the resolved AudioEngine card for a book directory."""
    return get_engine(resolve_audio_engine(book_dir))


def episode_engine_overrides(book_dir: Path) -> dict[str, str]:
    """Per-episode engine overrides from series-config.yaml, validated.

    A book may flip individual episodes to a different engine than its book
    default (e.g. an ElevenLabs-default book that wants one delicate chapter
    rendered in NotebookLM):

        audio_engine: elevenlabs
        episode_engine_overrides:
          EP07-the-conspiracy-formula: notebooklm

    Returns a {episode_id: engine_name} map. Every value is validated through
    get_engine() so a typo raises ValueError loudly (same philosophy as
    resolve_audio_engine — engine choice is never implicit). An empty/missing
    map returns {}, which keeps every pre-existing book byte-identical: callers
    that gate on "are there any overrides?" treat {} as "no per-episode logic".
    Unknown episode-id keys are tolerated (forward-compatible with edits/renames).
    """
    cfg_path = Path(book_dir) / "_system" / "series-config.yaml"
    if not cfg_path.exists():
        return {}
    try:
        import yaml
        with cfg_path.open() as f:
            cfg = yaml.safe_load(f) or {}
    except Exception:  # noqa: BLE001
        return {}
    raw = cfg.get("episode_engine_overrides") or {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for ep, eng in raw.items():
        if eng is None or str(eng).strip() == "":
            continue
        name = str(eng).strip().lower()
        get_engine(name)  # raises ValueError on unknown — never silent
        out[str(ep).strip()] = name
    return out


def engine_for_episode(book_dir: Path, episode_id: str) -> str:
    """The engine that renders a single episode: its override else the book default.

    This is the SINGLE decision point for per-episode routing — the script
    loop, the render plan, the bundle emitter, and the finalize halt all funnel
    through it so no engine conditional is ever duplicated.
    """
    overrides = episode_engine_overrides(book_dir)
    if episode_id in overrides:
        return overrides[episode_id]
    return resolve_audio_engine(book_dir)


def audio_engine_card_for_episode(book_dir: Path, episode_id: str) -> AudioEngine:
    """Convenience: the resolved AudioEngine card for a single episode."""
    return get_engine(engine_for_episode(book_dir, episode_id))


def is_autonomous(engine: AudioEngine | str) -> bool:
    """True when the engine renders audio via API (no manual upload/download)."""
    card = engine if isinstance(engine, AudioEngine) else get_engine(engine)
    return card.render_mode == RENDER_MODE_API


def notebooklm_episode_filter(
    book_dir: Path, all_episode_ids: list[str] | None = None
) -> set[str] | None:
    """The set of episodes that render on NotebookLM (manual upload/download).

    SINGLE source of truth for "which episodes need the NotebookLM ritual",
    shared by the finalize halt (which prints the upload table + worklist) and
    the audio-ingest phase (which normalizes + transcribes the dropped audio) so
    the two can never disagree about the episode set.

    Returns:
      - ``None``  — a pure-NotebookLM book (no per-episode overrides, manual
        engine). Means "ALL episodes" and renders byte-identically to the
        pre-override behavior (the golden-table latch).
      - empty set — a pure-autonomous book (e.g. ElevenLabs): no NotebookLM
        ritual at all; the audio-ingest phase is a no-op skip.
      - non-empty set — a mixed-engine book: exactly the episode ids overridden
        to NotebookLM.

    ``all_episode_ids`` is only consulted for the mixed-engine case; callers
    always pass it (from the episode mapping) so the override subset can be
    computed. Failures fall back to ``None`` (the safe manual ritual).
    """
    try:
        overrides = episode_engine_overrides(book_dir)
        if not overrides:
            return None if not is_autonomous(audio_engine_for_book(book_dir)) else set()
        eps = all_episode_ids or []
        return {ep for ep in eps
                if engine_for_episode(book_dir, ep) == ENGINE_NOTEBOOKLM}
    except Exception:  # noqa: BLE001 — fall back to the manual ritual
        return None


def credit_estimate(engine: AudioEngine | str, char_count: int) -> int:
    """Deterministic synthesis-credit estimate for *char_count* characters.

    chars x registry credit_rate, rounded up to a whole credit. 0 for
    unmetered engines (notebooklm). This is the figure the pre-synthesis
    gate report and the H1 spend halt surface.
    """
    card = engine if isinstance(engine, AudioEngine) else get_engine(engine)
    if card.credit_rate <= 0 or char_count <= 0:
        return 0
    import math
    return math.ceil(char_count * card.credit_rate)


def credits_to_usd(credits: int | float) -> float:
    """Notional USD for a credit count (ledger convenience column)."""
    return round(float(credits) * ELEVENLABS_USD_PER_CREDIT, 6)


def voices_for_book(book_dir: Path) -> dict[str, str]:
    """Voice casting for a book. Resolution order (lowest to highest):

    1. engine-card `default_voices` (legacy fallback)
    2. voice library deterministic per-slug pair (`_voice_library.pair_for_slug`
       over the Asif-approved pools in voice-library.yaml — stable per slug)
    3. series-config `voice_cast: {host_a/host_b: <library name>}` (names)
    4. series-config `elevenlabs_voices: {host_a/host_b: <voice id>}` (IDs)

    Returns {} for engines without voice casting (notebooklm).
    """
    card = audio_engine_for_book(book_dir)
    voices = dict(card.default_voices)
    if not voices:
        return voices
    try:
        from _voice_library import pair_for_slug, resolve_name
        voices.update(pair_for_slug(Path(book_dir).name))
    except Exception:  # noqa: BLE001 — library damage must not block casting
        resolve_name = None
    cfg_path = Path(book_dir) / "_system" / "series-config.yaml"
    if cfg_path.exists():
        try:
            import yaml
            with cfg_path.open() as f:
                cfg = yaml.safe_load(f) or {}
            named = cfg.get("voice_cast") or {}
            if isinstance(named, dict) and resolve_name is not None:
                for k, v in named.items():
                    vid = resolve_name(str(v)) if isinstance(v, str) else None
                    if vid:
                        voices[str(k)] = vid
            override = cfg.get("elevenlabs_voices") or {}
            if isinstance(override, dict):
                for k, v in override.items():
                    if isinstance(v, str) and v.strip():
                        voices[str(k)] = v.strip()
        except Exception:
            pass
    return voices
