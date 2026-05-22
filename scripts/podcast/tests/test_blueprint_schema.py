#!/usr/bin/env python3
"""Tests for scripts/podcast/_blueprint_schema.py (P24.1 deliverable).

Covers the eight acceptance bullets in P24.1.tests + four scenarios derived
from the locked decisions (2026-05-20):

  (a) valid classification.json round-trips through validate_classification
  (b) missing required field fails loud
  (c) invalid genre_primary enum fails loud
  (d) recommended_model_for_layer_2 enum gates {haiku, sonnet, opus}
  (e) audience_profile enum gates {traditional, modern-secular, clinical-wellness, academic}
  (f) recommended_source_tradition can be null OR tradition-slug; never empty string
  (g) rationale length 50-500 chars; outside range fails loud
  (h) arc_conventions_from_classification projects all locked fields

Also exercises:
  • compute_source_signature determinism
  • write_classification + load_classification round-trip
  • episode-plan frontmatter validation
  • cross-field defaults: GENRE_TO_DEFAULT_PLANNING_MODE / default_model_for_density

Repo style: unittest + sys.path insert; matches test_cost_ledger.py.
"""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _blueprint_schema as bp  # noqa: E402


def _valid_classification_dict() -> dict:
    """A minimal valid classification.json — every locked field populated."""
    return {
        "schema_version": 1,
        "book_slug": "tiny-book",
        "source_signature": "sha256:" + "0" * 64,
        "classified_at": "2026-05-20T12:00:00+00:00",
        "genre_primary": "polemic_tribunal",
        "density_score": 0.82,
        "narrative_mode": "dialectical",
        "structural_units": ["babs", "fasls"],
        "cross_reference_load": "high",
        "vocabulary_contestedness": "high",
        "recommended_model_for_layer_2": "opus",
        "recommended_audience_profile": "academic",
        "recommended_source_tradition": "islamic-classical-ismaili",
        "recommended_episode_planning_mode": "tribunal_arc",
        "rationale": (
            "opens with judicial framing on Bāb 1 — three named accusers "
            "structuring the polemic; cross-reference load high from chained "
            "Quranic + hadith citations; vocabulary contested across Ismaili / "
            "Sunni reception."
        ),
    }


class ClassificationValidationTests(unittest.TestCase):
    def test_valid_round_trip(self):
        d = _valid_classification_dict()
        c = bp.validate_classification(d)
        self.assertEqual(c.book_slug, "tiny-book")
        self.assertEqual(c.genre_primary, "polemic_tribunal")
        self.assertEqual(c.recommended_model_for_layer_2, "opus")
        self.assertEqual(c.structural_units, ("babs", "fasls"))
        # to_dict round-trips
        d2 = c.to_dict()
        self.assertEqual(d2["structural_units"], ["babs", "fasls"])

    def test_to_json_parses(self):
        c = bp.validate_classification(_valid_classification_dict())
        parsed = json.loads(c.to_json())
        self.assertEqual(parsed["book_slug"], "tiny-book")

    def test_missing_required_field_fails_loud(self):
        d = _valid_classification_dict()
        del d["rationale"]
        with self.assertRaises(bp.BlueprintSchemaError) as ctx:
            bp.validate_classification(d)
        self.assertIn("rationale", str(ctx.exception))

    def test_unknown_field_fails_loud(self):
        d = _valid_classification_dict()
        d["unexpected_field"] = "boo"
        with self.assertRaises(bp.BlueprintSchemaError) as ctx:
            bp.validate_classification(d)
        self.assertIn("unknown fields", str(ctx.exception))

    def test_schema_version_mismatch(self):
        d = _valid_classification_dict()
        d["schema_version"] = 2
        with self.assertRaises(bp.BlueprintSchemaError):
            bp.validate_classification(d)


class EnumGateTests(unittest.TestCase):
    def test_invalid_genre_primary_fails_loud(self):
        d = _valid_classification_dict()
        d["genre_primary"] = "treatise"
        with self.assertRaises(bp.BlueprintSchemaError) as ctx:
            bp.validate_classification(d)
        self.assertIn("genre_primary", str(ctx.exception))

    def test_model_recommendation_enum_locked(self):
        """Locked decision 3 (2026-05-20): {haiku, sonnet, opus} only."""
        for ok in ("haiku", "sonnet", "opus"):
            d = _valid_classification_dict()
            d["recommended_model_for_layer_2"] = ok
            bp.validate_classification(d)  # passes
        for bad in ("claude-opus-4-7", "opus-4", "gpt-4", "claude-haiku-4-5-20251001"):
            d = _valid_classification_dict()
            d["recommended_model_for_layer_2"] = bad
            with self.assertRaises(bp.BlueprintSchemaError):
                bp.validate_classification(d)

    def test_audience_profile_enum(self):
        valid = ("traditional", "modern-secular", "clinical-wellness", "academic")
        for v in valid:
            d = _valid_classification_dict()
            d["recommended_audience_profile"] = v
            bp.validate_classification(d)
        for bad in ("popular", "scholarly", "general"):
            d = _valid_classification_dict()
            d["recommended_audience_profile"] = bad
            with self.assertRaises(bp.BlueprintSchemaError):
                bp.validate_classification(d)

    def test_planning_mode_enum(self):
        valid = ("tribunal_arc", "chronological", "problem_solution",
                 "vignette_grid", "dialectical_pairs")
        for v in valid:
            d = _valid_classification_dict()
            d["recommended_episode_planning_mode"] = v
            bp.validate_classification(d)
        for bad in ("episodic", "narrative_arc", "hero_journey"):
            d = _valid_classification_dict()
            d["recommended_episode_planning_mode"] = bad
            with self.assertRaises(bp.BlueprintSchemaError):
                bp.validate_classification(d)

    def test_narrative_mode_enum(self):
        for bad in ("third_person_limited", "second_person", "omniscient"):
            d = _valid_classification_dict()
            d["narrative_mode"] = bad
            with self.assertRaises(bp.BlueprintSchemaError):
                bp.validate_classification(d)

    def test_load_levels(self):
        for bad in ("very-high", "extreme", "minimal"):
            d = _valid_classification_dict()
            d["cross_reference_load"] = bad
            with self.assertRaises(bp.BlueprintSchemaError):
                bp.validate_classification(d)


class FieldSemanticsTests(unittest.TestCase):
    def test_source_tradition_null_allowed(self):
        d = _valid_classification_dict()
        d["recommended_source_tradition"] = None
        c = bp.validate_classification(d)
        self.assertIsNone(c.recommended_source_tradition)

    def test_source_tradition_empty_string_refused(self):
        d = _valid_classification_dict()
        d["recommended_source_tradition"] = ""
        with self.assertRaises(bp.BlueprintSchemaError):
            bp.validate_classification(d)

    def test_density_score_bounds(self):
        for ok in (0.0, 0.5, 1.0):
            d = _valid_classification_dict()
            d["density_score"] = ok
            bp.validate_classification(d)
        for bad in (-0.01, 1.01, 2.0):
            d = _valid_classification_dict()
            d["density_score"] = bad
            with self.assertRaises(bp.BlueprintSchemaError):
                bp.validate_classification(d)

    def test_rationale_length_50_to_500(self):
        d = _valid_classification_dict()
        d["rationale"] = "too short"
        with self.assertRaises(bp.BlueprintSchemaError):
            bp.validate_classification(d)
        d["rationale"] = "x" * 501
        with self.assertRaises(bp.BlueprintSchemaError):
            bp.validate_classification(d)

    def test_source_signature_format(self):
        d = _valid_classification_dict()
        for bad in ("sha256:tooshort", "md5:" + "0" * 32, "0" * 64, "sha256:" + "g" * 64):
            d["source_signature"] = bad
            with self.assertRaises(bp.BlueprintSchemaError):
                bp.validate_classification(d)

    def test_book_slug_format(self):
        d = _valid_classification_dict()
        for bad in ("UPPER", "with_underscore", "-leading", "trailing-", "a"):
            d["book_slug"] = bad
            with self.assertRaises(bp.BlueprintSchemaError):
                bp.validate_classification(d)


class FileRoundTripTests(unittest.TestCase):
    def test_write_and_load(self):
        c = bp.validate_classification(_valid_classification_dict())
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "classification.json"
            bp.write_classification(path, c)
            c2 = bp.load_classification(path)
            self.assertEqual(c, c2)


class EpisodePlanFrontmatterTests(unittest.TestCase):
    def _valid(self):
        return {
            "schema_version": 1,
            "book_slug": "tiny-book",
            "classification_source_signature": "sha256:" + "0" * 64,
            "planned_at": "2026-05-20T13:00:00+00:00",
            "episode_count": 7,
            "planning_mode": "tribunal_arc",
            "audience_profile": "academic",
            "model_used": "claude-opus-4-7",
            "model_recommended": "opus",
            "model_overridden_by_operator": False,
        }

    def test_valid(self):
        fm = bp.validate_episode_plan_frontmatter(self._valid())
        self.assertEqual(fm.episode_count, 7)
        self.assertEqual(fm.model_recommended, "opus")

    def test_planning_mode_must_match_enum(self):
        d = self._valid()
        d["planning_mode"] = "tribunal-arc"  # hyphen vs underscore — typo
        with self.assertRaises(bp.BlueprintSchemaError):
            bp.validate_episode_plan_frontmatter(d)

    def test_model_recommended_must_be_short_enum(self):
        d = self._valid()
        d["model_recommended"] = "claude-opus-4-7"
        with self.assertRaises(bp.BlueprintSchemaError):
            bp.validate_episode_plan_frontmatter(d)


class ArcConventionsProjectionTests(unittest.TestCase):
    def test_projection_preserves_locked_fields(self):
        c = bp.validate_classification(_valid_classification_dict())
        ac = bp.arc_conventions_from_classification(c, seeded_at="2026-05-20T14:00:00+00:00")
        self.assertEqual(ac.book_slug, c.book_slug)
        self.assertEqual(ac.genre_primary, c.genre_primary)
        self.assertEqual(ac.narrative_mode, c.narrative_mode)
        self.assertEqual(ac.structural_units, c.structural_units)
        self.assertEqual(ac.audience_profile, c.recommended_audience_profile)
        self.assertEqual(ac.source_tradition, c.recommended_source_tradition)
        self.assertEqual(ac.episode_planning_mode, c.recommended_episode_planning_mode)
        self.assertEqual(ac.seeded_by, bp.AGENT_NAME + " Layer 3")


class HelperTests(unittest.TestCase):
    def test_source_signature_deterministic(self):
        sig1 = bp.compute_source_signature("hello world")
        sig2 = bp.compute_source_signature("hello world")
        self.assertEqual(sig1, sig2)
        self.assertTrue(sig1.startswith("sha256:"))
        self.assertEqual(len(sig1), len("sha256:") + 64)

    def test_default_model_for_density(self):
        self.assertEqual(bp.default_model_for_density(0.0), "haiku")
        self.assertEqual(bp.default_model_for_density(0.33), "haiku")
        self.assertEqual(bp.default_model_for_density(0.5), "sonnet")
        self.assertEqual(bp.default_model_for_density(0.66), "sonnet")
        self.assertEqual(bp.default_model_for_density(0.67), "opus")
        self.assertEqual(bp.default_model_for_density(1.0), "opus")

    def test_genre_to_default_planning_mode_complete(self):
        # every genre in the enum must have a default planning mode
        for g in bp.GENRE_PRIMARY_ENUM:
            self.assertIn(g, bp.GENRE_TO_DEFAULT_PLANNING_MODE)
            self.assertIn(bp.GENRE_TO_DEFAULT_PLANNING_MODE[g], bp.EPISODE_PLANNING_MODE_ENUM)


class LockedDecisionsTests(unittest.TestCase):
    """Sanity checks on the four LOCKED decisions (2026-05-20)."""

    def test_agent_name(self):
        self.assertEqual(bp.AGENT_NAME, "podcast-blueprint")
        self.assertNotEqual(bp.AGENT_NAME, "podcast-arc")

    def test_phase_slug(self):
        self.assertEqual(bp.PHASE_SLUG, "05.5-blueprint")

    def test_model_recommendation_enum_size(self):
        self.assertEqual(bp.MODEL_RECOMMENDATION_ENUM, frozenset({"haiku", "sonnet", "opus"}))


if __name__ == "__main__":
    unittest.main()
