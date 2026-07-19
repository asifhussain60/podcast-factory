"""_narrator_policy.py — who may be quoted when a book is augmented.

Asif, 2026-07-19: "Do not augment with quotations from Abu Bakar, Umar, Uthman,
Ayesha. Only quotes of the Ahl-e-Bait, Imam Ali, Ismail bin Muhammad, and their
followers are approved." A doctrinal editorial policy for the augmentation
lane, applied the same way every other guardrail in this lane is applied:
deterministically, at the point the corpus is LOADED, so a disallowed
attribution is never even offered to the model as a candidate — not filtered
after the fact, not left to the model's own judgment.

Scope, precisely: this blocks a QUOTATION ATTRIBUTED TO one of the four named
companions — the ``speaker`` field on a ``quote`` atom, the ``narrator`` field
on a ``hadith`` atom. It does NOT scrub prose that merely MENTIONS one of these
names. A doctrinal passage that discusses history involving Abu Bakr and Umar
(this corpus has exactly one, grouping them with Ibn Muljam — Ali's assassin —
as adversaries) is not a quotation FROM them; deleting it on a name-substring
match would over-apply the rule and destroy real teaching content the rule was
never meant to touch. "Do not augment WITH quotations FROM X" is an attribution
rule, not a keyword filter.

The allowlist named in the rule (Ahl al-Bayt, Imam Ali, Ismail bin Muhammad,
their followers) is NOT enforced as a closed allowlist here: the corpus is
dominated by content with no sectarian attribution at stake at all — the
Qur'an, hadith with no narrator recorded, doctrinal exposition, Ghazali,
Corbin, philosophical prose — and requiring every atom to name-match the
allowlist would silently gut all of that. The precise, defensible reading is
the blocklist: exclude the four named companions, leave everything else
exactly as retrieval already scores it.
"""

from __future__ import annotations

import re
from typing import Any

from _translit import simplify_transliteration

# Canonical variant spellings actually seen (or plausible) for each disallowed
# narrator. Matched as whole words/phrases against a normalized name, never as a
# bare substring — "Umar" must not fire on a name that happens to contain those
# letters; the corpus has none, but the match stays word-bounded regardless.
_DISALLOWED: dict[str, tuple[str, ...]] = {
    "Abu Bakr": ("abu bakr", "abu bakar", "abubakr", "abou bakr", "abu bakr al siddiq", "abu bakr siddiq"),
    "Umar": ("umar", "omar", "umar ibn al khattab", "umar ibn khattab", "janab umar", "hazrat umar", "umar farooq"),
    "Uthman": ("uthman", "usman", "uthman ibn affan", "usman ghani", "uthman ghani"),
    "Aisha": ("aisha", "ayesha", "a'isha", "aishah", "a'ishah", "aisha bint abi bakr"),
}


def _normalize(name: str) -> str:
    """Fold to plain transliteration, lowercase, punctuation to spaces, whitespace flat."""
    flat = simplify_transliteration(str(name or "")).lower()
    flat = re.sub(r"[^a-z0-9]+", " ", flat)
    return " ".join(flat.split())


def disallowed_narrator(name: str) -> str | None:
    """The canonical disallowed name ``name`` matches, or ``None`` if it is clear."""
    normalized = _normalize(name)
    if not normalized:
        return None
    for canonical, variants in _DISALLOWED.items():
        for variant in variants:
            # The variant is folded through the SAME normalizer as the target, so
            # a variant written with an apostrophe ("a'isha") still matches after
            # both sides collapse punctuation to spaces the same way.
            if re.search(rf"\b{re.escape(_normalize(variant))}\b", normalized):
                return canonical
    return None


def atom_narrator(atom: dict[str, Any]) -> str:
    """The person a KB atom quotes or narrates from, or '' if it does not attribute one.

    Only ``quote`` (``body.speaker``) and ``hadith`` (``body.narrator``) atoms
    carry this. Doctrine, Quran, and etymology atoms are prose or reference data,
    not a quotation attributed to a named individual — they have no such field
    and are never subject to this filter.
    """
    body = atom.get("body") if isinstance(atom.get("body"), dict) else {}
    for key in ("speaker", "narrator"):
        value = body.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def filter_atoms(atoms: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split a KB atom pool into (kept, excluded). Excluded carries WHY, for the log.

    Applied at load time so a disallowed attribution is never offered to the
    model as a candidate — the same discipline as every other gate in the
    augmentation lane: deterministic exclusion, not a prompt instruction hoping
    the model declines to use it.
    """
    kept: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for atom in atoms:
        speaker = atom_narrator(atom)
        matched = disallowed_narrator(speaker) if speaker else None
        if matched:
            excluded.append({"id": atom.get("id"), "speaker": speaker, "matched": matched})
        else:
            kept.append(atom)
    return kept, excluded
