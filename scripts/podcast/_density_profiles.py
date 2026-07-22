#!/usr/bin/env python3
"""_density_profiles.py -- Pluggable NotebookLM density-profile registry (2026-06-11).

One place to define how much material a NotebookLM generation mode can carry
per content profile, and how the density planner (density_planner.py) should
bias its grouping decisions. Extensibility-first: adding a content profile or
a generation mode is ONE registry entry here -- never a search-and-replace.

Profiles are keyed (content_profile, mode). Lookup falls back to the "*"
content profile so unknown profiles degrade to the narrative defaults rather
than crashing. Per-book overrides live in _system/series-config.yaml:

    density_planner: on            # opt-in gate for Slice-2 injections
    density_profiles:              # optional field-level overrides
      default_deep_dive:
        max_words_soft: 3000

Threshold lineage (NOT invented here -- aligned with existing constants):
  - default_deep_dive band tracks the Phase 0d tier band 1,800-2,800 plus the
    empirical finding (2026-06-11) that dense doctrinal chapters up to ~3,200
    words still carry a Default generation well.
  - longer max_words_soft == EPISODE_DENSITY_CEILING_DENSE (6,000) for the
    scholarly profile so the planner can never recommend a group the Phase 0d
    over-cramming brake would reject.
  - max_major_concepts for default tracks EPISODE_MAX_CONCEPTS (3).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, fields, replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _validator_constants import (
    EPISODE_DENSITY_CEILING_DENSE,
    EPISODE_DENSITY_CEILING_NARRATIVE,
    EPISODE_MAX_CONCEPTS,
)

# NotebookLM generation modes the planner can assign.
MODE_DEFAULT = "default_deep_dive"
MODE_LONGER = "longer"
MODE_BRIEF = "brief"

# The NotebookLM "Length" setting each mode maps to in the upload table.
MODE_TO_LENGTH = {
    MODE_DEFAULT: "Default",
    MODE_LONGER: "Long",
    MODE_BRIEF: "Default",
}


@dataclass(frozen=True)
class DensityProfile:
    """Budget + bias envelope for one (content_profile, mode) pair.

    All *_soft bounds are quality targets, NOT NotebookLM technical limits --
    the planner optimizes for usable source density well below the hard
    source-size ceilings.
    """

    mode: str
    min_words_soft: int  # below this a solo chapter is "thin"
    max_words_soft: int  # above this the mode starts compressing
    max_major_concepts: int  # concept sections one generation can honor
    max_compression_risk: float  # 0..1; above this -> flag / pacing directive
    combine_bias: float  # 0..1; reward for combining thin neighbours
    split_bias: float  # 0..1; reward for splitting over-dense files


# ---------------------------------------------------------------------------
# Registry. Key: (content_profile, mode). "*" = fallback content profile.
# ---------------------------------------------------------------------------
DENSITY_PROFILE_REGISTRY: dict[tuple[str, str], DensityProfile] = {
    # -- Islamic scholarly / doctrinal (dense): tight envelopes ---------------
    ("islamic_scholarly", MODE_DEFAULT): DensityProfile(
        mode=MODE_DEFAULT,
        min_words_soft=1800,
        max_words_soft=3200,
        max_major_concepts=EPISODE_MAX_CONCEPTS,
        max_compression_risk=0.55,
        combine_bias=0.2,
        split_bias=0.5,
    ),
    ("islamic_scholarly", MODE_LONGER): DensityProfile(
        mode=MODE_LONGER,
        min_words_soft=3800,
        max_words_soft=EPISODE_DENSITY_CEILING_DENSE,  # 6,000
        max_major_concepts=EPISODE_MAX_CONCEPTS * 2,  # coherent pair budget
        max_compression_risk=0.50,
        combine_bias=0.6,
        split_bias=0.2,
    ),
    ("islamic_scholarly", MODE_BRIEF): DensityProfile(
        mode=MODE_BRIEF,
        min_words_soft=600,
        max_words_soft=2000,
        max_major_concepts=2,
        max_compression_risk=0.75,
        combine_bias=0.0,
        split_bias=0.0,
    ),
    # -- Fallback (narrative / consumer): looser envelopes --------------------
    ("*", MODE_DEFAULT): DensityProfile(
        mode=MODE_DEFAULT,
        min_words_soft=1800,
        max_words_soft=3500,
        max_major_concepts=EPISODE_MAX_CONCEPTS,
        max_compression_risk=0.65,
        combine_bias=0.4,
        split_bias=0.3,
    ),
    ("*", MODE_LONGER): DensityProfile(
        mode=MODE_LONGER,
        min_words_soft=3500,
        max_words_soft=EPISODE_DENSITY_CEILING_NARRATIVE,  # 9,500
        max_major_concepts=EPISODE_MAX_CONCEPTS * 2,
        max_compression_risk=0.60,
        combine_bias=0.7,
        split_bias=0.2,
    ),
    ("*", MODE_BRIEF): DensityProfile(
        mode=MODE_BRIEF,
        min_words_soft=600,
        max_words_soft=2200,
        max_major_concepts=2,
        max_compression_risk=0.80,
        combine_bias=0.0,
        split_bias=0.0,
    ),
}

_PROFILE_FIELD_NAMES = {f.name for f in fields(DensityProfile)}


def _load_series_config(book_dir: Path | None) -> dict:
    if book_dir is None:
        return {}
    cfg_path = Path(book_dir) / "_system" / "series-config.yaml"
    if not cfg_path.exists():
        return {}
    try:
        import yaml

        return yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def get_profile(content_profile: str | None, mode: str, book_dir: Path | None = None) -> DensityProfile:
    """Resolve the DensityProfile for (content_profile, mode).

    Resolution order: exact registry entry -> "*" fallback entry -> then
    field-level overrides from the book's series-config.yaml
    `density_profiles.<mode>` mapping (unknown fields ignored).
    """
    cp = (content_profile or "").strip() or "*"
    prof = DENSITY_PROFILE_REGISTRY.get((cp, mode)) or DENSITY_PROFILE_REGISTRY.get(("*", mode))
    if prof is None:
        raise KeyError(f"Unknown density mode {mode!r}")
    overrides = _load_series_config(book_dir).get("density_profiles") or {}
    mode_overrides = overrides.get(mode) or {}
    clean = {k: v for k, v in mode_overrides.items() if k in _PROFILE_FIELD_NAMES and k != "mode"}
    return replace(prof, **clean) if clean else prof


def planner_enabled(book_dir: Path) -> bool:
    """Slice-2 opt-in gate: `density_planner: on` in series-config.yaml.

    Gates the pacing-directive injection (build_episode_txt) and the Phase 0d
    advisory block (_chapter_design). Running density_planner.py itself and
    the upload-table Length lookup are NOT gated -- the plan artifact's
    presence is their opt-in.
    """
    raw = _load_series_config(book_dir).get("density_planner")
    if raw is None:
        return False
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() in ("on", "true", "yes", "1")
