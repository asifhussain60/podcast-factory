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
        "narrative_frame": _from_registry(NARRATIVE_FRAMES),
        "autonomy": _from_registry(AUTONOMY_LEVELS),
        "source_medium": [
            _opt(v, _titleize(v), _GLOSS.get(v, "")) for v in (_flags.SOURCE_PRINTED_TEXT, _flags.SOURCE_AUDIO_LECTURE)
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
        out = {
            "vocabularies": get_vocabularies(),
            "defaults": defaults(),
            "profile_narrative_frame": dict(PROFILE_DEFAULT_NARRATIVE_FRAME),
            # The bucket a profile routes to, so the form can show it read-only
            # without keeping a third copy of the map (`_paths.resolve_bucket`
            # and `content-paths.ts` are the other two, and they must agree).
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
