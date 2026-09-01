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
    # Who narrates a book of this type when it declares no `narrative_frame` of
    # its own. A property of the content type, so it is declared here beside the
    # bucket rather than in a second hand-maintained table; `_rules.py` derives
    # PROFILE_DEFAULT_NARRATIVE_FRAME from these. None means "no type-level
    # default" and falls through to _rules.DEFAULT_NARRATIVE_FRAME.
    narrative_frame: str | None = None
    # Default audio engine for a NEW book of this profile, stamped into
    # series-config.yaml at intake (intake_launch._write_series_config). NEW-book
    # default ONLY — never applied retroactively, so existing books with no
    # `audio_engine` field keep the notebooklm default and never move off the
    # path their already-rendered audio came from.
    audio_engine: str = "notebooklm"
    # Default ElevenLabs cast (host key -> voice-library name) stamped at intake
    # when the chosen engine is elevenlabs and the operator picked no voices.
    default_voice_cast: dict = field(default_factory=dict)
    # Skip the per-chapter PODCAST lane entirely — the NotebookLM episode loop,
    # its convergence passes, and the audio phases after it. Not a performance
    # switch: for a recorded session the audio ALREADY EXISTS and is the
    # lecture, so there is no episode to build and nothing for a challenger to
    # converge. Defaults False, so every existing profile is untouched.
    skip_per_chapter: bool = False


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
        narrative_frame="transmitted_report",
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
        narrative_frame="first_person_author",
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
        narrative_frame="external_narrator",
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
        narrative_frame="transmitted_report",
    ),
    # Delivered lecture sessions — Asif's own recordings, with transcripts already
    # written by hand in KSESSIONS_DEV. A sibling lane like islamic_supplication:
    # registered here purely so the shared resolvers (_paths.resolve_bucket,
    # _branching.branch_name) derive `Sessions/<slug>` for free. The podcast phase
    # machinery never runs for this profile — the lane has its own driver
    # (scripts/podcast/sessions/) and produces no NotebookLM episodes, because the
    # audio already exists and is the lecture itself.
    #
    # Every skip is load-bearing, not conservative padding:
    #   skip_ocr        source is HTML out of a database, already digital text
    #   skip_phonetics  0c exists so NotebookLM says Arabic terms correctly; nothing
    #                   here is spoken by a model, so it has nothing to correct
    #   skip_enrichment 0e injects outside doctrinal material, which would put words
    #                   into a lecture Asif already delivered
    #
    # Appended LAST on purpose: CONTENT_PROFILES is derived from insertion order,
    # so adding here leaves every existing profile's position untouched.
    "islamic_session": ContentType(
        profile="islamic_session",
        bucket="Sessions",
        skip_phonetics=True,
        skip_enrichment=True,
        skip_ocr=True,
        # Added 2026-08-31 after `purification-of-the-heart` finished phase 0d
        # and walked straight into the podcast lane, where a smoke gate written
        # for authored episodes rejected three chapters for being the length the
        # speaker actually spoke. The docstring above already said "produces no
        # NotebookLM episodes, because the audio already exists and is the
        # lecture itself" — it was true of the lane's own driver and not of the
        # orchestrated route, which had no way to express it.
        skip_per_chapter=True,
        literary_voice={
            "narrator_voice": "author_first_person",
            "narrator_subject": "the speaker",
            "addressee": "the reader",
            "scene_source": "text_only",
        },
        narrative_frame="first_person_author",
    ),
    # Published audiobooks — someone else's book, read aloud by a narrator. The
    # SECOND profile to run the spoken lane (`pipeline_mode: sessions_lane`),
    # which is why that lane's scaffolding was lifted out of `sessions/ingest.py`
    # into `spoken_lane/scaffold.py`: the lane is the route, KSESSIONS is one
    # source adapter into it, and a lane defined by whichever ingest you copied
    # is not a lane.
    #
    # The bucket is a FORMAT, not a subject — exactly as `Sessions` is. What the
    # book is ABOUT is carried by `study_track` on the card (Dostoyevsky ships as
    # `philosophy`), so an Islamic audiobook and a Russian novel can share the
    # shelf without either one's subject being misfiled.
    #
    # Every skip is load-bearing, the same reasoning as `islamic_session`:
    #   skip_ocr        the source is a recording; there is nothing to scan
    #   skip_phonetics  0c exists so NotebookLM says Arabic terms correctly, and
    #                   nothing here is spoken by a model
    #   skip_enrichment 0e injects outside doctrinal material, which would put
    #                   words into a book its author finished writing
    #   skip_per_chapter the audio ALREADY EXISTS and is the book, so there is no
    #                   episode to generate and nothing for a challenger to converge
    #
    # NOT skipped, deliberately: the Arabic apparatus. Asif, 2026-09-01 — the
    # shelf "would still preserve and replace arabic". A book with none records a
    # `noop`; one with Arabic gets the same restoration ladder every other book
    # gets, which is what makes an Islamic audiobook work on day one.
    #
    # `external_narrator`: a novel read aloud is still narrated in the third
    # person by its own narrator. The reader is not the frame.
    #
    # Appended LAST on purpose: CONTENT_PROFILES is derived from insertion order,
    # so adding here leaves every existing profile's position untouched.
    "audiobook": ContentType(
        profile="audiobook",
        bucket="Audiobook",
        skip_phonetics=True,
        skip_enrichment=True,
        skip_ocr=True,
        skip_per_chapter=True,
        literary_voice={
            "narrator_voice": "narrative_voice",
            "narrator_subject": "the narrator",
            "addressee": "the reader",
            "scene_source": "text_only",
        },
        narrative_frame="external_narrator",
    ),
}

# Ordered top-level bucket folders under content/ (type-first layout, 2026-06-04).
# "Supplications" appended 2026-07-19 (PDF-only facing-column lane).
# "Sessions" appended 2026-08-11 (delivered-lecture lane).
# "Audiobook" appended 2026-09-01 (published books read aloud; spoken lane).
BUCKETS: tuple[str, ...] = (
    "Islamic",
    "Technical",
    "Fiction",
    "Guides",
    "Supplications",
    "Sessions",
    "Audiobook",
)

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
