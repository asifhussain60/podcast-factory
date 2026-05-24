#!/usr/bin/env python3
"""Schema models + validators for podcast-blueprint (P24.1).

Three artifacts the blueprint agent emits at slot 05.5-blueprint:

  • Classification   — Layer 1 output. Schema-locked by 2026-05-20 design.
                       This file IS the canonical schema (Python dataclasses
                       + frozenset enum validators). The earlier separate
                       JSON Schema file at content/podcast/.skill/handbook/
                       _schemas/classification.schema.json was retired in
                       the 2026-05-23 restructure and not restored.
  • EpisodePlan      — Layer 2 output. Frontmatter dataclass; body is freeform
                       markdown that Layer 2 emits as prose.
  • ArcConventions   — Layer 3 output. Frontmatter dataclass; body is built
                       from the template inlined in _blueprint.py Layer-3
                       prompt builder (formerly at content/podcast/.skill/
                       handbook/_templates/arc-conventions.template.md,
                       retired 2026-05-23).

The four locked design decisions (2026-05-20) are reflected here:
  1. Name = "podcast-blueprint"     → AGENT_NAME constant
  2. Slot = 05.5-blueprint          → PHASE_SLUG constant
  3. Layer-1 model recommendation   → Classification.recommended_model_for_layer_2
                                       enum = {haiku, sonnet, opus}
  4. arc-conventions.md lifecycle   → ArcConventions has no in-place mutators;
                                       Layer 3 creates-only-if-absent (enforced
                                       at _blueprint.py call site)

Repo style: @dataclass(frozen=True) + hand-rolled enum validation, no pydantic,
no jsonschema. Matches _cost_ledger.py.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Locked constants — names, slugs, slot order
# ---------------------------------------------------------------------------

AGENT_NAME = "podcast-blueprint"
PHASE_SLUG = "05.5-blueprint"
SCHEMA_VERSION = 1

# Locked enums. (The earlier external mirror at content/podcast/.skill/
# handbook/_schemas/classification.schema.json was retired 2026-05-23; the
# Python frozensets below are the sole source-of-truth now.)
GENRE_PRIMARY_ENUM = frozenset({
    "polemic_tribunal",
    "memoir",
    "self_help",
    "essay_collection",
    "didactic_dialogue",
    "exegesis",
    "epistle",
})

NARRATIVE_MODE_ENUM = frozenset({
    "first_person",
    "third_person_omniscient",
    "dialectical",
    "epistolary",
    "vignette",
})

LOAD_LEVEL_ENUM = frozenset({"low", "medium", "high"})

MODEL_RECOMMENDATION_ENUM = frozenset({"haiku", "sonnet", "opus"})

AUDIENCE_PROFILE_ENUM = frozenset({
    "traditional",
    "modern-secular",
    "clinical-wellness",
    "academic",
})

EPISODE_PLANNING_MODE_ENUM = frozenset({
    "tribunal_arc",
    "chronological",
    "problem_solution",
    "vignette_grid",
    "dialectical_pairs",
})

# Genre → default planning mode. Layer 1 may override per source signals; this
# is the fallback used by schema-validation tests for the cross-field
# coherence check.
GENRE_TO_DEFAULT_PLANNING_MODE: dict[str, str] = {
    "polemic_tribunal": "tribunal_arc",
    "memoir": "chronological",
    "self_help": "problem_solution",
    "essay_collection": "vignette_grid",
    "didactic_dialogue": "dialectical_pairs",
    "exegesis": "chronological",      # default; vignette_grid for non-linear
    "epistle": "chronological",        # default; vignette_grid for non-linear
}

# Density-score → default model recommendation. Layer 1 may upgrade further
# based on cross_reference_load or vocabulary_contestedness.
def default_model_for_density(density: float) -> str:
    if density < 0.34:
        return "haiku"
    if density < 0.67:
        return "sonnet"
    return "opus"


BOOK_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
TRADITION_SLUG_RE = re.compile(r"^[a-z][a-z0-9-]*[a-z0-9]$")
STRUCTURAL_UNIT_RE = re.compile(r"^[a-z][a-z_]*[a-z]$")
SOURCE_SIGNATURE_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class BlueprintSchemaError(ValueError):
    """Raised when an artifact fails schema validation. Fails LOUD per P24.1."""


# ---------------------------------------------------------------------------
# Layer 1 — Classification
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Classification:
    schema_version: int
    book_slug: str
    source_signature: str
    classified_at: str
    genre_primary: str
    density_score: float
    narrative_mode: str
    structural_units: tuple[str, ...]
    cross_reference_load: str
    vocabulary_contestedness: str
    recommended_model_for_layer_2: str
    recommended_audience_profile: str
    recommended_source_tradition: str | None
    recommended_episode_planning_mode: str
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["structural_units"] = list(self.structural_units)
        return d

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


def validate_classification(data: dict[str, Any]) -> Classification:
    """Parse + validate a classification.json dict. Returns frozen dataclass.

    Raises BlueprintSchemaError on any conformance failure. Fails LOUD — never
    coerces, never warns, never silently drops fields.
    """
    required = {
        "schema_version", "book_slug", "source_signature", "classified_at",
        "genre_primary", "density_score", "narrative_mode", "structural_units",
        "cross_reference_load", "vocabulary_contestedness",
        "recommended_model_for_layer_2", "recommended_audience_profile",
        "recommended_source_tradition", "recommended_episode_planning_mode",
        "rationale",
    }
    missing = required - set(data.keys())
    if missing:
        raise BlueprintSchemaError(
            f"classification.json missing required fields: {sorted(missing)}"
        )

    extra = set(data.keys()) - required
    if extra:
        raise BlueprintSchemaError(
            f"classification.json has unknown fields: {sorted(extra)} "
            f"(schema_version={SCHEMA_VERSION} additionalProperties=false)"
        )

    if data["schema_version"] != SCHEMA_VERSION:
        raise BlueprintSchemaError(
            f"classification.json schema_version={data['schema_version']!r} "
            f"!= {SCHEMA_VERSION} — refusing"
        )

    book_slug = data["book_slug"]
    if not isinstance(book_slug, str) or not BOOK_SLUG_RE.match(book_slug):
        raise BlueprintSchemaError(f"invalid book_slug: {book_slug!r}")

    sig = data["source_signature"]
    if not isinstance(sig, str) or not SOURCE_SIGNATURE_RE.match(sig):
        raise BlueprintSchemaError(f"invalid source_signature: {sig!r}")

    classified_at = data["classified_at"]
    if not isinstance(classified_at, str):
        raise BlueprintSchemaError("classified_at must be ISO-8601 string")
    try:
        _dt.datetime.fromisoformat(classified_at.replace("Z", "+00:00"))
    except ValueError as e:
        raise BlueprintSchemaError(f"classified_at not parseable ISO-8601: {e}") from e

    genre = data["genre_primary"]
    if genre not in GENRE_PRIMARY_ENUM:
        raise BlueprintSchemaError(
            f"genre_primary={genre!r} not in {sorted(GENRE_PRIMARY_ENUM)}"
        )

    density = data["density_score"]
    if not isinstance(density, (int, float)) or isinstance(density, bool):
        raise BlueprintSchemaError(f"density_score must be number; got {type(density).__name__}")
    density = float(density)
    if not (0.0 <= density <= 1.0):
        raise BlueprintSchemaError(f"density_score={density} out of [0.0, 1.0]")

    mode = data["narrative_mode"]
    if mode not in NARRATIVE_MODE_ENUM:
        raise BlueprintSchemaError(
            f"narrative_mode={mode!r} not in {sorted(NARRATIVE_MODE_ENUM)}"
        )

    units = data["structural_units"]
    if not isinstance(units, list) or not 1 <= len(units) <= 6:
        raise BlueprintSchemaError(
            f"structural_units must be 1-6 element list; got {units!r}"
        )
    for u in units:
        if not isinstance(u, str) or not STRUCTURAL_UNIT_RE.match(u):
            raise BlueprintSchemaError(f"invalid structural_unit: {u!r}")

    crl = data["cross_reference_load"]
    if crl not in LOAD_LEVEL_ENUM:
        raise BlueprintSchemaError(
            f"cross_reference_load={crl!r} not in {sorted(LOAD_LEVEL_ENUM)}"
        )

    vc = data["vocabulary_contestedness"]
    if vc not in LOAD_LEVEL_ENUM:
        raise BlueprintSchemaError(
            f"vocabulary_contestedness={vc!r} not in {sorted(LOAD_LEVEL_ENUM)}"
        )

    rec_model = data["recommended_model_for_layer_2"]
    if rec_model not in MODEL_RECOMMENDATION_ENUM:
        raise BlueprintSchemaError(
            f"recommended_model_for_layer_2={rec_model!r} not in "
            f"{sorted(MODEL_RECOMMENDATION_ENUM)} "
            f"(locked decision 3 — 2026-05-20)"
        )

    rec_profile = data["recommended_audience_profile"]
    if rec_profile not in AUDIENCE_PROFILE_ENUM:
        raise BlueprintSchemaError(
            f"recommended_audience_profile={rec_profile!r} not in "
            f"{sorted(AUDIENCE_PROFILE_ENUM)}"
        )

    rec_tradition = data["recommended_source_tradition"]
    if rec_tradition is not None:
        if not isinstance(rec_tradition, str) or not TRADITION_SLUG_RE.match(rec_tradition):
            raise BlueprintSchemaError(
                f"recommended_source_tradition={rec_tradition!r} must be "
                f"tradition-slug or null"
            )

    rec_mode = data["recommended_episode_planning_mode"]
    if rec_mode not in EPISODE_PLANNING_MODE_ENUM:
        raise BlueprintSchemaError(
            f"recommended_episode_planning_mode={rec_mode!r} not in "
            f"{sorted(EPISODE_PLANNING_MODE_ENUM)}"
        )

    rationale = data["rationale"]
    if not isinstance(rationale, str) or not 50 <= len(rationale) <= 500:
        raise BlueprintSchemaError(
            f"rationale must be 50-500 chars; got {len(rationale) if isinstance(rationale, str) else 'non-string'}"
        )

    return Classification(
        schema_version=SCHEMA_VERSION,
        book_slug=book_slug,
        source_signature=sig,
        classified_at=classified_at,
        genre_primary=genre,
        density_score=density,
        narrative_mode=mode,
        structural_units=tuple(units),
        cross_reference_load=crl,
        vocabulary_contestedness=vc,
        recommended_model_for_layer_2=rec_model,
        recommended_audience_profile=rec_profile,
        recommended_source_tradition=rec_tradition,
        recommended_episode_planning_mode=rec_mode,
        rationale=rationale,
    )


def load_classification(path: Path) -> Classification:
    with open(path, encoding="utf-8") as f:
        return validate_classification(json.load(f))


def write_classification(path: Path, c: Classification) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(c.to_json() + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Layer 2 — EpisodePlan (frontmatter only; body is freeform markdown)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EpisodePlanFrontmatter:
    schema_version: int
    book_slug: str
    classification_source_signature: str   # SHA-256 of the classification.json that drove this plan
    planned_at: str
    episode_count: int
    planning_mode: str
    audience_profile: str
    model_used: str                         # the actual model invoked
    model_recommended: str                  # what Layer 1 recommended
    model_overridden_by_operator: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_episode_plan_frontmatter(data: dict[str, Any]) -> EpisodePlanFrontmatter:
    required = {
        "schema_version", "book_slug", "classification_source_signature",
        "planned_at", "episode_count", "planning_mode", "audience_profile",
        "model_used", "model_recommended", "model_overridden_by_operator",
    }
    missing = required - set(data.keys())
    if missing:
        raise BlueprintSchemaError(f"episode-plan frontmatter missing: {sorted(missing)}")
    extra = set(data.keys()) - required
    if extra:
        raise BlueprintSchemaError(f"episode-plan frontmatter unknown fields: {sorted(extra)}")

    if data["schema_version"] != SCHEMA_VERSION:
        raise BlueprintSchemaError(
            f"episode-plan schema_version={data['schema_version']!r} != {SCHEMA_VERSION}"
        )

    book_slug = data["book_slug"]
    if not isinstance(book_slug, str) or not BOOK_SLUG_RE.match(book_slug):
        raise BlueprintSchemaError(f"invalid book_slug: {book_slug!r}")

    sig = data["classification_source_signature"]
    if not isinstance(sig, str) or not SOURCE_SIGNATURE_RE.match(sig):
        raise BlueprintSchemaError(f"invalid classification_source_signature: {sig!r}")

    ec = data["episode_count"]
    if not isinstance(ec, int) or isinstance(ec, bool) or not 1 <= ec <= 200:
        raise BlueprintSchemaError(f"episode_count must be int in [1, 200]; got {ec!r}")

    pm = data["planning_mode"]
    if pm not in EPISODE_PLANNING_MODE_ENUM:
        raise BlueprintSchemaError(
            f"planning_mode={pm!r} not in {sorted(EPISODE_PLANNING_MODE_ENUM)}"
        )

    ap = data["audience_profile"]
    if ap not in AUDIENCE_PROFILE_ENUM:
        raise BlueprintSchemaError(
            f"audience_profile={ap!r} not in {sorted(AUDIENCE_PROFILE_ENUM)}"
        )

    # model_used is freeform (matches whatever was returned by claude -p, e.g.
    # "claude-haiku-4-5-20251001"); model_recommended is the LAYER-1 enum.
    mr = data["model_recommended"]
    if mr not in MODEL_RECOMMENDATION_ENUM:
        raise BlueprintSchemaError(
            f"model_recommended={mr!r} not in {sorted(MODEL_RECOMMENDATION_ENUM)}"
        )

    if not isinstance(data["model_used"], str) or not data["model_used"].strip():
        raise BlueprintSchemaError("model_used must be non-empty string")

    if not isinstance(data["model_overridden_by_operator"], bool):
        raise BlueprintSchemaError("model_overridden_by_operator must be bool")

    return EpisodePlanFrontmatter(
        schema_version=SCHEMA_VERSION,
        book_slug=book_slug,
        classification_source_signature=sig,
        planned_at=data["planned_at"],
        episode_count=ec,
        planning_mode=pm,
        audience_profile=ap,
        model_used=data["model_used"],
        model_recommended=mr,
        model_overridden_by_operator=data["model_overridden_by_operator"],
    )


# ---------------------------------------------------------------------------
# Layer 3 — ArcConventions (frontmatter dataclass; body is template-rendered)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ArcConventionsFrontmatter:
    schema_version: int
    book_slug: str
    seeded_at: str
    seeded_by: str
    source_signature: str
    # Inherited classification slice
    genre_primary: str
    narrative_mode: str
    structural_units: tuple[str, ...]
    density_score: float
    cross_reference_load: str
    vocabulary_contestedness: str
    # Operator-confirmable slice (gets merged into series-config.yaml)
    audience_profile: str
    source_tradition: str | None
    episode_planning_mode: str

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["structural_units"] = list(self.structural_units)
        return d


def arc_conventions_from_classification(
    c: Classification,
    *,
    seeded_by: str = AGENT_NAME + " Layer 3",
    seeded_at: str | None = None,
) -> ArcConventionsFrontmatter:
    """Project a Classification into an ArcConventionsFrontmatter seed.

    Used by Layer 3's first-run path. After this returns, the caller validates
    file-absence at <book>/arc-conventions.md before writing (enforced at
    _blueprint.py call site — Layer 3 NEVER overwrites).
    """
    return ArcConventionsFrontmatter(
        schema_version=SCHEMA_VERSION,
        book_slug=c.book_slug,
        seeded_at=seeded_at or _dt.datetime.now(_dt.UTC).isoformat(),
        seeded_by=seeded_by,
        source_signature=c.source_signature,
        genre_primary=c.genre_primary,
        narrative_mode=c.narrative_mode,
        structural_units=c.structural_units,
        density_score=c.density_score,
        cross_reference_load=c.cross_reference_load,
        vocabulary_contestedness=c.vocabulary_contestedness,
        audience_profile=c.recommended_audience_profile,
        source_tradition=c.recommended_source_tradition,
        episode_planning_mode=c.recommended_episode_planning_mode,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def compute_source_signature(text: str | bytes) -> str:
    """Canonical SHA-256 source-signature format used across all three layers."""
    if isinstance(text, str):
        text = text.encode("utf-8")
    return "sha256:" + hashlib.sha256(text).hexdigest()


def now_iso8601() -> str:
    return _dt.datetime.now(_dt.UTC).isoformat()


__all__ = [
    "AGENT_NAME",
    "PHASE_SLUG",
    "SCHEMA_VERSION",
    "GENRE_PRIMARY_ENUM",
    "NARRATIVE_MODE_ENUM",
    "LOAD_LEVEL_ENUM",
    "MODEL_RECOMMENDATION_ENUM",
    "AUDIENCE_PROFILE_ENUM",
    "EPISODE_PLANNING_MODE_ENUM",
    "GENRE_TO_DEFAULT_PLANNING_MODE",
    "default_model_for_density",
    "BlueprintSchemaError",
    "Classification",
    "validate_classification",
    "load_classification",
    "write_classification",
    "EpisodePlanFrontmatter",
    "validate_episode_plan_frontmatter",
    "ArcConventionsFrontmatter",
    "arc_conventions_from_classification",
    "compute_source_signature",
    "now_iso8601",
]
