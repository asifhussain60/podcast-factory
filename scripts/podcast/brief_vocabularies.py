"""brief_vocabularies.py — the vocabularies the Intake commissioning form offers.

The Intake wizard (``/intake`` on the Podcast Factory Astro Site) asks for every
decision the pipeline reads, not just the seven ``intake_form_options.py``
already serves. This module supplies the REST — the source-property and
product-route knobs that used to be hand-written into ``_system/series-config.yaml``
and ``meta.yml`` after the fact.

The contract is the same one ``intake_form_options.py`` keeps, and it is the
whole point of the module: every value here is IMPORTED from the registry that
owns it, never restated. A narrative frame added to ``_narrative_frames.py``
appears in the form the same day, and a value the form offers cannot be one the
pipeline rejects.

Each option carries a plain-English ``label`` and ``description`` so the form can
explain a choice to someone who does not speak pipeline. Where the owning
registry already writes that prose (``NARRATIVE_FRAMES``, ``AUTONOMY_LEVELS``),
it is quoted from there rather than re-authored — two descriptions of one knob
would eventually disagree.

Read-only: this module has no setter and no override file. The seven fields with
user-editable option lists stay with ``intake_form_options.py``; nothing here is
served by both.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _archetypes
import _pipeline_flags as _flags
from _autonomy import AUTONOMY_LEVELS, DEFAULT_AUTONOMY
from _content_types import CONTENT_TYPE_REGISTRY
from _listener_book import STUDY_TRACKS
from _narrative_frames import (
    DEFAULT_NARRATIVE_FRAME,
    NARRATIVE_FRAMES,
    PROFILE_DEFAULT_NARRATIVE_FRAME,
)
from _rules import ALLOWED_CATEGORIES, CONTENT_LEVEL_LADDER, EPISODE_FORMAT_ALLOWED
from _translation_contract import TRANSLATION_EDITION_MODE

# ── Families: one plain question instead of seven pipeline profile names ──────
#
# The Intake form asks WHAT KIND of content this is, then WHERE IT CAME FROM,
# and resolves the pipeline's `content_profile` from the pair. That is how the
# two Islamic profiles stop being a choice a person has to understand: a
# scholarly book and a recorded session are both "Islamic", and the medium
# already distinguishes them (Asif, 2026-08-30).
#
# Grouping is a PRESENTATION concern, so it lives here rather than in the
# content-type registry -- but it may not silently fall out of step with it, so
# `_assert_families_cover_registry` fails loudly the day a profile is added
# without a home. The registry stays the authority on what exists.
FAMILIES: tuple[tuple[str, str, str], ...] = (
    (
        "islamic",
        "Islamic",
        "Scholarly works, treatises and recorded religious sessions.",
    ),
    ("technical", "Technical or how-to", "Documentation, training, engineering material."),
    ("fiction", "Fiction", "Novels and narrative storytelling."),
    ("explainer", "Explainer or guide", "Onboarding, product and consumer explainers."),
    ("general", "General non-fiction", "Everything else written to inform."),
    ("supplication", "Supplication", "Prayers and devotional recitation."),
    (
        "audiobook",
        "Audiobook",
        "A published book read aloud — someone else's text, narrated.",
    ),
)

#: family -> {source_medium -> content_profile}. A family whose two media resolve
#: to the SAME profile simply does not vary by medium; only Islamic does today.
FAMILY_PROFILES: dict[str, dict[str, str]] = {
    "islamic": {
        _flags.SOURCE_PRINTED_TEXT: "islamic_scholarly",
        _flags.SOURCE_AUDIO_LECTURE: "islamic_session",
    },
    "technical": {
        _flags.SOURCE_PRINTED_TEXT: "technical",
        _flags.SOURCE_AUDIO_LECTURE: "technical",
    },
    "fiction": {
        _flags.SOURCE_PRINTED_TEXT: "fiction",
        _flags.SOURCE_AUDIO_LECTURE: "fiction",
    },
    "explainer": {
        _flags.SOURCE_PRINTED_TEXT: "consumer_explainer",
        _flags.SOURCE_AUDIO_LECTURE: "consumer_explainer",
    },
    "general": {
        _flags.SOURCE_PRINTED_TEXT: "general_nonfiction",
        _flags.SOURCE_AUDIO_LECTURE: "general_nonfiction",
    },
    "supplication": {
        _flags.SOURCE_PRINTED_TEXT: "islamic_supplication",
        _flags.SOURCE_AUDIO_LECTURE: "islamic_supplication",
    },
    # An audiobook is audio by definition, so the medium answer cannot change
    # what it is -- both entries resolve to the same profile, exactly as every
    # non-Islamic family above does. `audio_lecture` is the answer that fits, and
    # picking it is what reveals the three fields this route actually needs on
    # the form (arabic_restoration, source_fidelity, chapter_segmentation); a
    # third `source_medium` value would have meant touching every `showIf` gate
    # and adding a column to all seven families to express nothing new.
    "audiobook": {
        _flags.SOURCE_PRINTED_TEXT: "audiobook",
        _flags.SOURCE_AUDIO_LECTURE: "audiobook",
    },
}

#: The legacy `category` tag each profile defaults to. It is no longer asked on
#: the form's surface -- `_branching` states outright that category "does NOT
#: reliably determine the bucket" and `content_profile` supersedes it -- but it
#: is still read by _paths, _contract_validation and the explainer slide route,
#: so it is derived here and left overridable rather than dropped.
PROFILE_CATEGORY: dict[str, str] = {
    "islamic_scholarly": "books",
    "islamic_session": "lectures",
    "islamic_supplication": "books",
    "fiction": "books",
    "technical": "explainers",
    "consumer_explainer": "explainers",
    "general_nonfiction": "books",
    "audiobook": "books",
}


#: What each medium actually DOES, said only where the two differ. Derived from
#: FAMILY_PROFILES rather than written out, so a family that starts varying by
#: medium gets the sentence automatically and one that stops varying loses it.
_ROUTE_GLOSS: dict[str, str] = {
    "printed_text": (
        " Chapters are written from the text and episodes are generated for them, "
        "and the reading edition is composed as its own deliverable."
    ),
    "audio_lecture": (
        " The recording IS the chapter: it is proofread but never rewritten, no "
        "podcast episodes are generated, and the text can follow the speaker's own "
        "voice as it plays."
    ),
}


def _route_gloss(medium: str) -> str:
    """The route sentence, only for media that actually lead somewhere different.

    A family whose two media resolve to the SAME content profile does not fork,
    and telling its operator that one answer skips the podcast would be false.
    Only `islamic` forks today; this asks the map rather than assuming that.
    """
    forks = any(len(set(media.values())) > 1 for media in FAMILY_PROFILES.values())
    return _ROUTE_GLOSS.get(medium, "") if forks else ""


def _assert_families_cover_registry() -> None:
    """Every profile the pipeline knows must be reachable from some family."""
    reachable = {p for media in FAMILY_PROFILES.values() for p in media.values()}
    missing = set(CONTENT_TYPE_REGISTRY) - reachable
    if missing:
        raise ValueError(
            "content profiles unreachable from any Intake family: "
            f"{sorted(missing)} -- add them to FAMILY_PROFILES in brief_vocabularies.py"
        )
    unknown = reachable - set(CONTENT_TYPE_REGISTRY)
    if unknown:
        raise ValueError(f"FAMILY_PROFILES names profiles that do not exist: {sorted(unknown)}")
    uncategorised = reachable - set(PROFILE_CATEGORY)
    if uncategorised:
        raise ValueError(f"profiles with no default category: {sorted(uncategorised)}")


def _opt(value: str, label: str, description: str = "") -> dict[str, str]:
    return {"value": value, "label": label, "description": description}


def _from_registry(registry: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    """Options for a registry that already documents itself (frames, autonomy)."""
    return [
        _opt(key, str(entry.get("label") or key), str(entry.get("description") or ""))
        for key, entry in registry.items()
    ]


# Prose for the closed sets whose owning modules define them as bare string
# constants with the explanation in a comment rather than a field. Keyed by
# value so a rename in the owner surfaces here as a missing gloss, not as a
# wrong one.
_GLOSS: dict[str, str] = {
    _flags.SOURCE_PRINTED_TEXT: "The book was set in type and read off a page.",
    _flags.SOURCE_AUDIO_LECTURE: (
        "The book is a talk that was delivered aloud and transcribed. The speaker's "
        "voice is kept; the room he spoke it in is not."
    ),
    _flags.BOOK_VOICE_FAITHFUL: ("Render the source as it stands. The default for an Islamic reading edition."),
    _flags.BOOK_VOICE_AUTHOR_COMPANION: ("Write alongside the source as a companion to it, in a voice of our own."),
    _flags.BOOK_AUGMENTATION_NONE: "Nothing is added that the source does not say.",
    _flags.BOOK_AUGMENTATION_SOURCE_ONLY: ("May draw on the source's own other passages, and nothing from outside it."),
    _flags.BOOK_VISUALS_MANUAL_ONLY: ("Figures are curated by hand in the Book Composer. The standing default."),
    _flags.BOOK_VISUALS_PIPELINE: "The pipeline may place figures on its own.",
}

_STUDY_TRACK_GLOSS: dict[str, str] = {
    "theology": "Belief, the divine, and the nature of faith.",
    "history": "Events, lives, and the record of what happened.",
    "shariah": "Law, practice, and what is required.",
    "esoteric": "Inner meaning beneath the plain sense of the text.",
    "reality": "Metaphysics — origin, return, and the structure of being.",
    "philosophy": "Reasoned enquiry into meaning, morals, and the human condition.",
}

_CONTENT_LEVEL_GLOSS: dict[str, str] = {
    "general": "Narrative and historical accounts.",
    "advanced": "Advanced scholarship, legal analysis, formal commentary.",
    "taveel": "Allegorical and esoteric interpretation.",
    "mamsool": "Parables and exemplars — the esoteric taught through analogy.",
    "mabda_maad": "Origin and return: cosmological doctrine.",
    "haqaiq": "Essential realities — the deepest metaphysical truths.",
}


def _titleize(value: str) -> str:
    words = value.replace("_", " ").replace("-", " ").strip()
    return words[:1].upper() + words[1:]


def get_vocabularies() -> dict[str, list[dict[str, str]]]:
    """Every option list the Intake wizard renders, straight from the registries."""
    archetypes: list[dict[str, str]] = []
    for slug in _archetypes.list_archetypes():
        try:
            arch = _archetypes.load_archetype(slug)
            archetypes.append(_opt(slug, arch.display_name, ", ".join(arch.genre_tags)))
        except Exception:
            # A malformed archetype folder must not take the whole form down.
            archetypes.append(_opt(slug, _titleize(slug)))

    return {
        "content_family": [_opt(v, label, desc) for v, label, desc in FAMILIES],
        "narrative_frame": _from_registry(NARRATIVE_FRAMES),
        "autonomy": _from_registry(AUTONOMY_LEVELS),
        # Worded as the thing itself rather than as the pipeline token: this is
        # half of what decides the content profile, so it has to read plainly.
        #
        # The LABEL now names the road as well as the source (Asif, 2026-08-31:
        # "use values that make it clear where you're asking me to select
        # Book/Content vs Sessions Path"). Both options described only what the
        # material was, and nothing on the form said that this one answer sends
        # the work down a wholly different pipeline — no podcast on one side, no
        # rewriting on the other. `_route_gloss` appends that consequence, and
        # ONLY on the family where it is true: for Technical, Fiction, Explainer,
        # General and Supplication both media resolve to the same profile, so a
        # route promise there would be a sentence the form cannot keep.
        "source_medium": [
            _opt(
                _flags.SOURCE_PRINTED_TEXT,
                "A printed book or manuscript — the Book route",
                _GLOSS[_flags.SOURCE_PRINTED_TEXT] + _route_gloss(_flags.SOURCE_PRINTED_TEXT),
            ),
            _opt(
                _flags.SOURCE_AUDIO_LECTURE,
                "A recorded talk or session — the Sessions route",
                _GLOSS[_flags.SOURCE_AUDIO_LECTURE] + _route_gloss(_flags.SOURCE_AUDIO_LECTURE),
            ),
        ],
        "book_voice": [
            _opt(v, _titleize(v), _GLOSS.get(v, ""))
            for v in (_flags.BOOK_VOICE_FAITHFUL, _flags.BOOK_VOICE_AUTHOR_COMPANION)
        ],
        "book_augmentation": [
            _opt(v, _titleize(v), _GLOSS.get(v, ""))
            for v in (
                _flags.BOOK_AUGMENTATION_NONE,
                _flags.BOOK_AUGMENTATION_SOURCE_ONLY,
            )
        ],
        "book_visuals": [
            _opt(v, _titleize(v), _GLOSS.get(v, ""))
            for v in (_flags.BOOK_VISUALS_MANUAL_ONLY, _flags.BOOK_VISUALS_PIPELINE)
        ],
        "deliverable_mode": [
            _opt(
                "",
                "Standard edition",
                "The usual route. Leave this unless the book is a translation edition.",
            ),
            _opt(
                TRANSLATION_EDITION_MODE,
                "Translation edition",
                "Everything must trace to the source; no augmentation is permitted.",
            ),
        ],
        "slide_deck_mode": [
            _opt("per-chapter", "Per chapter", "One deck for each chapter. The default."),
            _opt("book", "One for the book", "A single deck covering the whole book."),
        ],
        # HOW a recorded series becomes chapters. Asked rather than derived
        # because both answers are right for different series: a course of
        # weekly lectures is one chapter per recording, while a single long
        # sitting that moves through several distinct topics reads better cut
        # at those topic boundaries. Nothing in a file listing can tell the two
        # apart, and guessing wrong reshapes the whole edition.
        "chapter_segmentation": [
            _opt(
                "one_per_recording",
                "One chapter per recording",
                "Each audio file becomes exactly one chapter. The default: a recording IS a session.",
            ),
            _opt(
                "from_source_toc",
                "Follow the book's own chapter list",
                "The sessions teach through a published work chapter by chapter. Cut the chapters where the book does and keep the book's own chapter names.",
            ),
            _opt(
                "from_transcript",
                "Work the chapters out from the transcript",
                "No chapter list exists to follow: read the transcript for topic boundaries and cut chapters there.",
            ),
        ],
        # Arabic that the transcriber wrote out phonetically ("Bismillahir
        # Rahmanir Rahim") has to go back into script before the edition is
        # printed. Qur'anic runs are always resolved against the canonical
        # mushaf; this decides what happens to everything else.
        "arabic_restoration": [
            _opt(
                "audio_grounded",
                "Check the recording",
                "Where the text alone is ambiguous, listen to that moment of the recording to settle what was actually said. Slower, and the most accurate.",
            ),
            _opt(
                "text_only",
                "From the transcript alone",
                "Resolve from the written transcript and the canonical sources only. Faster; a garbled phrase stays unresolved rather than being checked.",
            ),
        ],
        "source_fidelity": [
            _opt("verbatim", "Verbatim", "The transcript is word for word."),
            _opt("edited", "Edited", "The transcript has been tidied."),
            _opt("summary", "Summary", "The transcript condenses rather than records."),
        ],
        "study_track": [_opt(v, _titleize(v), _STUDY_TRACK_GLOSS.get(v, "")) for v in sorted(STUDY_TRACKS)],
        "content_level": [_opt(v, _titleize(v), _CONTENT_LEVEL_GLOSS.get(v, "")) for v in CONTENT_LEVEL_LADDER],
        "category": [_opt(v, _titleize(v)) for v in ALLOWED_CATEGORIES],
        "episode_format": [_opt(v, _titleize(v)) for v in EPISODE_FORMAT_ALLOWED],
        "archetype": archetypes,
        "density": [
            _opt("shallow", "Shallow"),
            _opt("medium", "Medium"),
            _opt("deep", "Deep"),
        ],
    }


def defaults() -> dict[str, str]:
    """The value each vocabulary starts on when the book says nothing."""
    return {
        "narrative_frame": DEFAULT_NARRATIVE_FRAME,
        "autonomy": DEFAULT_AUTONOMY,
        "source_medium": _flags.SOURCE_PRINTED_TEXT,
        "book_voice": _flags.BOOK_VOICE_FAITHFUL,
        "book_augmentation": _flags.BOOK_AUGMENTATION_NONE,
        "book_visuals": _flags.BOOK_VISUALS_MANUAL_ONLY,
        "deliverable_mode": "",
        "slide_deck_mode": "per-chapter",
        "chapter_segmentation": "one_per_recording",
        "arabic_restoration": "audio_grounded",
        "source_fidelity": "verbatim",
        "category": "books",
        "density": "medium",
    }


# ── CLI (the JSON contract the Astro brief endpoints shell out to) ───────────
def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    p = argparse.ArgumentParser(description="Intake commissioning-form vocabularies")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("get")
    # Parsed for validation only: 'get' is the sole subcommand and carries no
    # options, so an unknown argument must still be rejected rather than ignored.
    p.parse_args(argv)
    try:
        _assert_families_cover_registry()
        out = {
            "vocabularies": get_vocabularies(),
            "defaults": defaults(),
            "profile_narrative_frame": dict(PROFILE_DEFAULT_NARRATIVE_FRAME),
            # The bucket a profile routes to, so the form can show it read-only
            # without keeping a third copy of the map (`_paths.resolve_bucket`
            # and `content-paths.ts` are the other two, and they must agree).
            "family_profiles": {f: dict(m) for f, m in FAMILY_PROFILES.items()},
            "profile_category": dict(PROFILE_CATEGORY),
            "profile_bucket": {profile: ct.bucket for profile, ct in CONTENT_TYPE_REGISTRY.items()},
            # The engine each profile actually uses. Served because the shared
            # voice picker still defaults to ElevenLabs, which was retired in
            # 2026-08: a brief must not tell a session to use a dead engine, and
            # the registry is the only thing that knows which one is live.
            "profile_audio_engine": {
                profile: (ct.audio_engine or "notebooklm") for profile, ct in CONTENT_TYPE_REGISTRY.items()
            },
            "profile_voice_cast": {
                profile: dict(ct.default_voice_cast or {}) for profile, ct in CONTENT_TYPE_REGISTRY.items()
            },
        }
    except Exception as e:  # pragma: no cover — surfaced to the UI as an error
        print(json.dumps({"ok": False, "error": str(e)}))
        return 2
    print(json.dumps({"ok": True, **out}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
