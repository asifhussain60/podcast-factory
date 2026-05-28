"""tests/test_anti_cliche.py — Tests for scripts/podcast/intelligence/_anti_cliche.py"""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts" / "podcast"
sys.path.insert(0, str(SCRIPTS_DIR))

from intelligence._anti_cliche import (  # noqa: E402
    AUGMENTER_PRIOR_TREATMENT_DENY,
    CAPSTONE_DENY,
    SELF_HELP_DENY,
    TIER_2_DENY,
)


# ---------------------------------------------------------------------------
# Type and size invariants
# ---------------------------------------------------------------------------

def test_all_lists_are_frozensets():
    assert isinstance(CAPSTONE_DENY, frozenset)
    assert isinstance(SELF_HELP_DENY, frozenset)
    assert isinstance(TIER_2_DENY, frozenset)
    assert isinstance(AUGMENTER_PRIOR_TREATMENT_DENY, frozenset)


def test_all_lists_non_empty():
    assert len(CAPSTONE_DENY) >= 10
    assert len(SELF_HELP_DENY) >= 15
    assert len(TIER_2_DENY) >= 15
    assert len(AUGMENTER_PRIOR_TREATMENT_DENY) >= 15


def test_all_entries_are_lowercase():
    for deny_list in (CAPSTONE_DENY, SELF_HELP_DENY, TIER_2_DENY, AUGMENTER_PRIOR_TREATMENT_DENY):
        for entry in deny_list:
            assert entry == entry.lower(), f"Entry not lowercase: {entry!r}"


# ---------------------------------------------------------------------------
# No cross-list duplicates (each list serves a distinct purpose)
# ---------------------------------------------------------------------------

def test_no_overlap_capstone_self_help():
    overlap = CAPSTONE_DENY & SELF_HELP_DENY
    assert overlap == frozenset(), f"Unexpected overlap: {overlap}"


def test_no_overlap_tier2_augmenter():
    overlap = TIER_2_DENY & AUGMENTER_PRIOR_TREATMENT_DENY
    assert overlap == frozenset(), f"Unexpected overlap: {overlap}"


# ---------------------------------------------------------------------------
# Spot checks — canonical entries that must always be present
# ---------------------------------------------------------------------------

def test_capstone_deny_contains_key_phrases():
    assert "key takeaways" in CAPSTONE_DENY
    assert "in conclusion" in CAPSTONE_DENY
    assert "lessons learned" in CAPSTONE_DENY


def test_self_help_deny_contains_key_phrases():
    assert "actionable" in SELF_HELP_DENY
    assert "personal growth" in SELF_HELP_DENY
    assert "growth mindset" in SELF_HELP_DENY


def test_tier2_deny_contains_casual_markers():
    assert "basically" in TIER_2_DENY
    assert "kind of" in TIER_2_DENY
    assert "obviously" in TIER_2_DENY


def test_augmenter_deny_contains_biographical_filler():
    assert "born in" in AUGMENTER_PRIOR_TREATMENT_DENY
    assert "studied under" in AUGMENTER_PRIOR_TREATMENT_DENY
    assert "it is important to note" in AUGMENTER_PRIOR_TREATMENT_DENY


# ---------------------------------------------------------------------------
# Matching semantics — case-insensitive substring is the documented contract
# ---------------------------------------------------------------------------

def test_capstone_match_is_case_insensitive():
    text = "In Summary, we have covered the key points."
    assert any(phrase in text.lower() for phrase in CAPSTONE_DENY)


def test_self_help_match_finds_embedded_phrase():
    text = "This is incredibly actionable wisdom for our personal growth journey."
    assert any(phrase in text.lower() for phrase in SELF_HELP_DENY)
