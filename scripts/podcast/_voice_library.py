#!/usr/bin/env python3
"""_voice_library.py — the approved voice-casting pools (data: voice-library.yaml).

Asif-approved pools (2026-06-12): every book renders with ONE male (HOST_A
scholar) and ONE female (HOST_B seeker) drawn from the library. Resolution
order lives in `_audio_engines.voices_for_book`; this module owns the data
access and the deterministic per-slug pick.

Extensibility: adding a voice = one YAML entry. Nothing here enumerates
names; pools are whatever the YAML says.
"""
from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

LIBRARY_PATH = Path(__file__).resolve().parent / "voice-library.yaml"


@lru_cache(maxsize=1)
def load_library() -> dict:
    import yaml
    with LIBRARY_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def male_pool() -> list[dict]:
    return list(load_library().get("males") or [])


def female_pool() -> list[dict]:
    return list(load_library().get("females") or [])


def pools() -> dict[str, list[dict]]:
    """The approved pools as UI-ready entries: {males:[...], females:[...]}.

    Each entry carries name, full_name, voice_id, accent, and sample (the clip
    filename served by the Astro voice picker). The single source for both the
    Python side and the TS reader (plan-dashboard/src/lib/voice-library.ts),
    which parses the same YAML.
    """
    return {"males": male_pool(), "females": female_pool()}


def resolve_name(name: str) -> str | None:
    """Library `name`/`full_name` (case-insensitive) -> voice_id, else None."""
    needle = name.strip().lower()
    for entry in male_pool() + female_pool():
        if needle in (str(entry.get("name", "")).lower(),
                      str(entry.get("full_name", "")).lower()):
            return entry.get("voice_id")
    return None


def pair_for_slug(slug: str) -> dict[str, str]:
    """Deterministic, stable casting pick for a book slug.

    Same slug -> same pair forever (re-renders never recast); different
    slugs rotate through the pools. Offset female index so pairings vary
    rather than tracking the male index in lockstep.
    """
    males, females = male_pool(), female_pool()
    if not males or not females:
        return {}
    h = int(hashlib.sha1(slug.encode("utf-8")).hexdigest(), 16)
    return {
        "host_a": males[h % len(males)]["voice_id"],
        "host_b": females[(h // len(males)) % len(females)]["voice_id"],
    }
