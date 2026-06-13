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
    ENGINE_ELEVENLABS: AudioEngine(
        name=ENGINE_ELEVENLABS,
        render_mode=RENDER_MODE_API,
        supports_arabic_script=True,
        supports_audio_tags=True,
        max_chunk_chars=2000,           # documented reliability limit per request
        credit_rate=1.0,                # eleven_v3: ~1 credit/char (API discounted)
        model_id="eleven_v3",
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


def is_autonomous(engine: AudioEngine | str) -> bool:
    """True when the engine renders audio via API (no manual upload/download)."""
    card = engine if isinstance(engine, AudioEngine) else get_engine(engine)
    return card.render_mode == RENDER_MODE_API


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
