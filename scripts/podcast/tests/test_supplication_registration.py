#!/usr/bin/env python3
"""Tranche 1 pins — the Supplications bucket + islamic_supplication profile.

The registration is deliberately *additive*: the shared resolvers
(``_paths.resolve_bucket`` / ``content_dir`` and ``_branching.branch_name``)
derive everything from ``BUCKETS`` + ``CONTENT_TYPE_REGISTRY``, so registering
the content type is the ONLY shared-code change the lane needs.

These tests pin both halves of that claim:
  - the new bucket/profile resolve, branch, and route correctly;
  - and every pre-existing bucket/profile resolves EXACTLY as before (the
    regression firewall — a new bucket must not perturb the old ones).
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_PODCAST))

import _branching
import _paths
from _rules import BUCKETS, CONTENT_TYPE_REGISTRY, bucket_for_profile, phase_capabilities

SUP_PROFILE = "islamic_supplication"
SUP_BUCKET = "Supplications"


class TestRegistration:
    def test_bucket_is_registered(self):
        assert SUP_BUCKET in BUCKETS

    def test_profile_is_registered_and_maps_to_bucket(self):
        assert SUP_PROFILE in CONTENT_TYPE_REGISTRY
        assert bucket_for_profile(SUP_PROFILE) == SUP_BUCKET

    def test_bucket_validates_in_paths(self):
        # _paths._validate_bucket raises for unknown buckets; bucket_dir goes
        # through it, so this is the assertion that the two lists agree.
        assert _paths.bucket_dir(SUP_BUCKET).name == SUP_BUCKET

    def test_capabilities_skip_phonetics_and_enrichment(self):
        caps = phase_capabilities(SUP_PROFILE)
        assert caps.skip_phonetics is True
        assert caps.skip_enrichment is True


class TestDerivedResolvers:
    """Nothing in _paths / _branching needed editing — prove it."""

    def test_content_dir_routes_to_the_new_bucket(self):
        d = _paths.content_dir("dua-kumayl", profile=SUP_PROFILE)
        assert d.parent.name == SUP_BUCKET
        assert d.name == "dua-kumayl"

    def test_branch_name_is_bucket_grouped(self):
        assert _branching.branch_name(None, "dua-kumayl", profile=SUP_PROFILE) == "Supplications/dua-kumayl"

    def test_resolve_bucket_prefers_profile_over_legacy_category(self):
        # A supplication tagged with the legacy `books` category must still land
        # in Supplications, not Islamic.
        assert _paths.resolve_bucket(bucket=None, profile=SUP_PROFILE, category="books") == SUP_BUCKET


class TestNoRegressionOnExistingProfiles:
    def test_every_pre_existing_profile_keeps_its_bucket(self):
        for profile, bucket in (
            ("islamic_scholarly", "Islamic"),
            ("technical", "Technical"),
            ("fiction", "Fiction"),
            ("consumer_explainer", "Guides"),
            ("general_nonfiction", "Guides"),
        ):
            assert bucket_for_profile(profile) == bucket

    def test_unknown_and_absent_profiles_still_default_to_islamic(self):
        # The new bucket must NOT become a catch-all — the historical default
        # that keeps every legacy book on the scholarly pipeline is unchanged.
        assert bucket_for_profile(None) == "Islamic"
        assert bucket_for_profile("nonsense") == "Islamic"

    def test_existing_buckets_keep_their_order(self):
        # CONTENT_PROFILES / BUCKETS order feeds the intake form; the new entry
        # is appended so existing positions are untouched.
        assert BUCKETS[:4] == ("Islamic", "Technical", "Fiction", "Guides")
