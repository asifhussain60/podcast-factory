"""_translation_contract.py — translation-edition config readers + contract checks.

Extracted verbatim from ``_translation_edition.py`` (R3 DR-005 split, 2026-07-18).
Owns the cheap, deterministic side of the translation-edition lane: reading
``_system/series-config.yaml``, the ``deliverable_mode`` / ``book_voice``
routing predicates, and the pre-LLM-spend contract gate. Deliberately LIGHT at
import time — ``AuthoringError`` is imported lazily so drivers, validators, and
tests can call these predicates without pulling in the authoring stack
(the same concern that made ``_pipeline_flags`` re-implement its own YAML read).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

TRANSLATION_EDITION_MODE = "translation_edition"
DEFAULT_VISUAL_STYLE = "black_white"


def read_series_config(book_dir: Path) -> dict[str, Any]:
    cfg_path = Path(book_dir) / "_system" / "series-config.yaml"
    if not cfg_path.exists():
        return {}
    try:
        data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def deliverable_mode(book_dir: Path) -> str:
    cfg = read_series_config(book_dir)
    return str(cfg.get("deliverable_mode") or "").strip()


def is_translation_edition(book_dir: Path) -> bool:
    return deliverable_mode(book_dir) == TRANSLATION_EDITION_MODE


def is_faithful_translation_deliverable(book_dir: Path) -> bool:
    """True when the book's DELIVERABLE is a faithful translation edition.

    For SHIP-GATE selection only (B3 translation branch, B4/B5/B6). Covers BOTH
    ``deliverable_mode == translation_edition`` AND the ``book_voice == faithful``
    knob (the faithful base + fluency de-calque, no author re-voice) — which
    produces the same faithful-translation artifact but is selected by the voice
    knob, not by ``deliverable_mode``.

    Deliberately SEPARATE from ``is_translation_edition``: that predicate governs
    compose run-vs-skip (``book_driver``) via ``deliverable_mode``; this one only
    decides which SHIP GATES apply.
    """
    if is_translation_edition(book_dir):
        return True
    try:
        from _pipeline_flags import BOOK_VOICE_FAITHFUL, book_voice
    except ImportError:  # nothing to read the knob with — assume not faithful
        return False
    # A ValueError from `book_voice` is a typo'd knob, and it is deliberately NOT
    # caught: swallowing it returns False, which turns gates B3/B4/B5/B6 into
    # "n/a (not a translation edition)". A config typo that silently disables four
    # ship gates is worse than the fallback this replaced.
    return book_voice(book_dir) == BOOK_VOICE_FAITHFUL


def translation_policy(book_dir: Path) -> dict[str, Any]:
    cfg = read_series_config(book_dir)
    policy = cfg.get("translation_policy") or {}
    return policy if isinstance(policy, dict) else {}


_COLOR_VISUAL_STYLES = {"color", "full_color", "colour", "photographic", "illustrated"}


def requires_monochrome_visuals(book_dir: Path) -> bool:
    """Standardized default (2026-08-07): every slide deck is black-and-white,
    minimal-yet-elegant unless a book explicitly opts into a colour style via
    `visual_style` or `translation_policy.monochrome_visuals: false`."""
    cfg = read_series_config(book_dir)
    policy = translation_policy(book_dir)
    style = str(cfg.get("visual_style") or policy.get("visual_style") or "").strip().lower()
    if policy.get("monochrome_visuals") is False or style in _COLOR_VISUAL_STYLES:
        return False
    return True


def contract_findings(book_dir: Path) -> list[str]:
    """Return contract findings for translation-edition mode.

    Empty means the book is configured safely. The checks are deterministic and
    cheap, so callers can run them before any LLM spend.
    """
    findings: list[str] = []
    cfg = read_series_config(book_dir)
    policy = translation_policy(book_dir)

    if cfg.get("deliverable_mode") != TRANSLATION_EDITION_MODE:
        findings.append("deliverable_mode must be 'translation_edition'")

    augmentation = str(policy.get("augmentation") or "forbidden").strip().lower()
    if augmentation not in {"forbidden", "none", "source_only"}:
        findings.append("translation_policy.augmentation must forbid outside-source augmentation")

    denoise = str(policy.get("denoise") or "teaching_only").strip().lower()
    if denoise not in {"teaching_only", "none", "light"}:
        findings.append("translation_policy.denoise must be teaching_only, light, or none")

    if not bool(policy.get("preserve_arabic_terms", True)):
        findings.append("translation_policy.preserve_arabic_terms must stay true")

    if not requires_monochrome_visuals(book_dir):
        findings.append("visual_style must be black_white/monochrome for this path")

    return findings


def assert_translation_contract(book_dir: Path) -> None:
    findings = contract_findings(book_dir)
    if findings:
        # Lazy import keeps this module cheap for the predicate-only callers.
        from _authoring._core import AuthoringError

        raise AuthoringError(
            phase="translation-edition",
            message="translation-edition contract failed: " + "; ".join(findings),
            manual_fallback=(
                "Set _system/series-config.yaml deliverable_mode=translation_edition "
                "and translation_policy.augmentation=forbidden before running this path."
            ),
        )
