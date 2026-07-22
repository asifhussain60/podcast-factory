"""_content_types.py — the content-type registry: profile -> bucket, phases, voice.

Extracted verbatim from `_rules.py` (2026-07-19) under DR-005: `_rules.py` was
a grandfathered over-limit module, and the gate's rule is "split, never grow".
This is the registry axis lifted out whole — behaviour is unchanged and every
name is re-exported from `_rules`, so no importer needed touching.

SINGLE SOURCE OF TRUTH for what a content type is. Adding a content type is one
entry in CONTENT_TYPE_REGISTRY plus one entry in BUCKETS; `_paths.resolve_bucket`
and `_branching.branch_name` derive from these and need no edit.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ─── Content-profile system (Wave CP) — declares how a book moves through the pipeline.
# Every book declares `content_profile` in its series-config.yaml; missing field defaults
# to `islamic_scholarly` so all existing books are unaffected. Profiles drive:
#   - assertion gating in build_episode_txt.py (Arabic checks skipped for non-Islamic)
#   - phase 0c phonetics (no-op for non-islamic_scholarly, already handled via CONSUMER_CATEGORIES)
#   - challenger rule selection (only islamic_scholarly gets Arabic name/citation checks)
# ─── Content-type registry (2026-06-04, Wave: content/ type-first layout) ──────
# SINGLE SOURCE OF TRUTH for what a content type is: its canonical profile key
# (stored as `content_profile` in series-config.yaml), the top-level `bucket`
# folder it lives under (content/<bucket>/<slug>/), which pipeline phases it
# skips, and its literary (revoice) voice defaults. Adding a content type = one
# entry here. Two ORTHOGONAL axes used to be conflated:
#   • the legacy `category` (books/lectures/sites/…) — still used for the optional
#     book-vs-lecture metadata tag, and retained in ALLOWED_CATEGORIES for intake.
#   • the content TYPE / profile — what actually drives routing + voice + bucket.
# This registry is the profile axis. _paths.py maps profile→bucket via bucket_for_profile().
@dataclass(frozen=True)
class ContentType:
    profile: str  # canonical content_profile key (series-config.yaml)
    bucket: str  # top-level folder under content/ (type-first layout)
    skip_phonetics: bool  # skip Phase 0c (Arabic phonetic pass)
    skip_enrichment: bool  # skip Phase 0e (doctrinal enrichment)
    skip_ocr: bool  # skip Phase 0a Azure OCR (source already digital English/text)
    literary_voice: dict  # revoice defaults consumed by _literary.py
    # Default audio engine for a NEW book of this profile, stamped into
    # series-config.yaml at intake (intake_launch._write_series_config). NEW-book
    # default ONLY — never applied retroactively, so existing books with no
    # `audio_engine` field keep the notebooklm default and never move off the
    # path their already-rendered audio came from.
    audio_engine: str = "notebooklm"
    # Default ElevenLabs cast (host key -> voice-library name) stamped at intake
    # when the chosen engine is elevenlabs and the operator picked no voices.
    default_voice_cast: dict = field(default_factory=dict)


CONTENT_TYPE_REGISTRY: dict[str, "ContentType"] = {
    "islamic_scholarly": ContentType(
        profile="islamic_scholarly",
        bucket="Islamic",
        skip_phonetics=False,
        skip_enrichment=False,
        skip_ocr=False,
        literary_voice={
            "narrator_voice": "author_first_person",
            "narrator_subject": "the author",
            "addressee": "the reader",
            "scene_source": "text_only",
        },
        # All Islamic books use NotebookLM (Google conversational AI — approved
        # fingerprint from the-master-and-the-disciple, confirmed 2026-06-13).
        # ElevenLabs scripted dialogue was tried for Vol 1 and rejected.
        audio_engine="notebooklm",
        default_voice_cast={"host_a": "Eric", "host_b": "Lily"},
    ),
    "technical": ContentType(
        profile="technical",
        bucket="Technical",
        skip_phonetics=True,
        skip_enrichment=True,
        skip_ocr=True,
        literary_voice={
            "narrator_voice": "peer_expert",
            "narrator_subject": "a senior practitioner",
            "addressee": "a fellow developer",
            "scene_source": "text_only",
        },
    ),
    "fiction": ContentType(
        profile="fiction",
        bucket="Fiction",
        skip_phonetics=True,
        skip_enrichment=True,
        skip_ocr=False,
        literary_voice={
            "narrator_voice": "narrative_voice",
            "narrator_subject": "the narrator",
            "addressee": "the reader",
            "scene_source": "text_only",
        },
    ),
    "consumer_explainer": ContentType(
        profile="consumer_explainer",
        bucket="Guides",
        skip_phonetics=True,
        skip_enrichment=True,
        skip_ocr=True,
        literary_voice={
            "narrator_voice": "contemporary_narrator",
            "narrator_subject": "a guide",
            "addressee": "you",
            "scene_source": "text_only",
        },
    ),
    "general_nonfiction": ContentType(
        profile="general_nonfiction",
        bucket="Guides",
        skip_phonetics=True,
        skip_enrichment=False,
        skip_ocr=False,
        literary_voice={
            "narrator_voice": "scholarly_essayist",
            "narrator_subject": "the author",
            "addressee": "the reader",
            "scene_source": "text_only",
        },
    ),
    # Supplications (du'a / ziyarat / munajat) — a PDF-ONLY sibling lane, not a
    # branch of the podcast pipeline. Registered here purely so the shared
    # bucket/branch/path resolvers (_paths.resolve_bucket, _branching.branch_name)
    # derive `Supplications/<slug>` for free. The podcast phase machinery never
    # runs for this profile: the lane has its own driver (scripts/podcast/
    # supplication/) with its own gates, and produces NO episodes, audio, slides,
    # or video. The skip_* flags are set conservatively and are inert unless a
    # caller mistakenly routes a supplication into the podcast phases.
    # Appended LAST on purpose: CONTENT_PROFILES is derived from insertion order,
    # so adding here leaves every existing profile's position untouched.
    "islamic_supplication": ContentType(
        profile="islamic_supplication",
        bucket="Supplications",
        skip_phonetics=True,
        skip_enrichment=True,
        skip_ocr=False,  # source is a scan; the lane's own OCR step handles it
        literary_voice={
            "narrator_voice": "devotional_voice",
            "narrator_subject": "the supplicant",
            "addressee": "the reader",
            "scene_source": "text_only",
        },
    ),
}

# Ordered top-level bucket folders under content/ (type-first layout, 2026-06-04).
# "Supplications" appended 2026-07-19 (PDF-only facing-column lane).
BUCKETS: tuple[str, ...] = ("Islamic", "Technical", "Fiction", "Guides", "Supplications")

# CONTENT_PROFILES is now DERIVED from the registry (was a hand-maintained tuple
# of 3; technical + fiction are now first-class). Order: registry insertion order.
CONTENT_PROFILES: tuple[str, ...] = tuple(CONTENT_TYPE_REGISTRY)
ISLAMIC_SCHOLARLY_PROFILE = "islamic_scholarly"


def bucket_for_profile(profile: str | None) -> str:
    """Map a content_profile to its top-level bucket folder. Defaults to Islamic.

    The bucket is the type-first folder (content/<bucket>/<slug>/). Unknown or
    absent profiles fall back to Islamic — the historical default that keeps every
    pre-existing book on the full scholarly pipeline.
    """
    ct = CONTENT_TYPE_REGISTRY.get(profile or "")
    return ct.bucket if ct else "Islamic"


def literary_voice_for_profile(profile: str | None) -> dict:
    """Revoice voice defaults for a profile (used by _literary.py). Islamic fallback."""
    ct = CONTENT_TYPE_REGISTRY.get(profile or "") or CONTENT_TYPE_REGISTRY[ISLAMIC_SCHOLARLY_PROFILE]
    return dict(ct.literary_voice)


def phase_capabilities(profile: str | None) -> "ContentType":
    """Return the ContentType (phase-skip capabilities) for a content_profile.

    SINGLE accessor for every phase-skip decision (0a OCR, 0c phonetics, 0e
    enrichment). Reads the CONTENT_TYPE_REGISTRY (single source of truth); unknown
    or absent profiles fall back to islamic_scholarly — the historical default that
    runs the full scholarly pipeline. Mirrors the bucket_for_profile pattern so
    routing logic lives in ONE place instead of scattered `category in {...}` checks.
    """
    return CONTENT_TYPE_REGISTRY.get(profile or "") or CONTENT_TYPE_REGISTRY[ISLAMIC_SCHOLARLY_PROFILE]


def audio_engine_default_for_profile(profile: str | None) -> str:
    """Default audio engine to stamp for a NEW book of this profile.

    NEW-book default only (consumed by intake_launch). Unknown/absent profiles
    fall back to islamic_scholarly's default. This never touches existing books.
    """
    ct = CONTENT_TYPE_REGISTRY.get(profile or "") or CONTENT_TYPE_REGISTRY[ISLAMIC_SCHOLARLY_PROFILE]
    return ct.audio_engine


def default_voice_cast_for_profile(profile: str | None) -> dict:
    """Default ElevenLabs cast (host key -> library name) for a NEW book."""
    ct = CONTENT_TYPE_REGISTRY.get(profile or "") or CONTENT_TYPE_REGISTRY[ISLAMIC_SCHOLARLY_PROFILE]
    return dict(ct.default_voice_cast)
