"""The Python half of the peq-scores <-> _quality mirror pair.

The JS half is `plan-dashboard/scripts/lib/peq-scores.test.mjs`, reading the SAME
fixture file.

This is a TRIPLE, not a pair. `_rules.py` holds R_INTEREST_WEIGHT and the five
R_INTEREST_* pattern lists; `_quality.py` imports them; `peq-scores.ts` re-types them
as literals with no link to the authority. The constant assertions below therefore
check `_rules.py`, not `_quality.py` — otherwise the weight could change upstream,
_quality's sum-to-1.0 assert could still pass if another weight compensated, and the
TypeScript 0.15 would diverge with nothing complaining.

Two real divergences were found and fixed at the root on 2026-07-26 (half-up vs
half-to-even rounding, and ASCII vs Unicode word boundaries). See the fixture's
`_comment` block. Both were latent — measured across all 58 chapter sources in the
repo, zero were affected, so no shipped verdict moved.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PIPELINE = REPO_ROOT / "scripts" / "podcast"
FIXTURES = REPO_ROOT / "plan-dashboard" / "scripts" / "lib" / "peq-scores.fixtures.json"

if str(PIPELINE) not in sys.path:
    sys.path.insert(0, str(PIPELINE))

import _quality as q  # noqa: E402
import _rules as r  # noqa: E402

assert FIXTURES.is_file(), f"shared fixture file missing: {FIXTURES}"
FIX = json.loads(FIXTURES.read_text(encoding="utf-8"))

PATTERN_GROUPS = {
    "hook": r.R_INTEREST_HOOK_PATTERNS,
    "challenge_raise": r.R_INTEREST_CHALLENGE_RAISE_PATTERNS,
    "challenge_resolve": r.R_INTEREST_CHALLENGE_RESOLVE_PATTERNS,
    "relevance": r.R_INTEREST_RELEVANCE_PATTERNS,
    "strawman_deny": r.R_INTEREST_STRAWMAN_DENY,
}


# ── constants, asserted against the real authority ────────────────────────────
def test_constants_match_the_shared_fixtures() -> None:
    c = FIX["constants"]
    assert q.THRESHOLD_PASS == c["threshold_pass"]
    assert q.THRESHOLD_WARN == c["threshold_warn"]
    w = c["weights"]
    assert q.WEIGHT_FIDELITY == w["fidelity"]
    assert q.WEIGHT_VOICE == w["voice"]
    assert q.WEIGHT_STRUCTURE == w["structure"]
    assert q.WEIGHT_ENRICHMENT == w["enrichment"]
    # The interest weight's authority is _rules.py; _quality.py only re-exports it.
    assert r.R_INTEREST_WEIGHT == w["interest"]
    assert q.WEIGHT_INTEREST == r.R_INTEREST_WEIGHT
    assert q._VOICE_SCORER_READY is c["voice_scorer_ready"]


def test_weights_sum_to_one() -> None:
    total = q.WEIGHT_FIDELITY + q.WEIGHT_VOICE + q.WEIGHT_STRUCTURE + q.WEIGHT_ENRICHMENT + q.WEIGHT_INTEREST
    assert abs(total - 1.0) < 1e-9, f"PEQ weights must sum to 1.0, got {total}"


def test_interest_pattern_counts_match_the_shared_fixtures() -> None:
    """Catches a pattern added to one language only — the TS side re-types these by
    hand, so a new rule landing in _rules.py alone is invisible without this."""
    expected = FIX["constants"]["interest_pattern_counts"]
    for name, patterns in PATTERN_GROUPS.items():
        assert len(patterns) == expected[name], f"{name}: {len(patterns)} != {expected[name]}"


def test_hook_patterns_are_unanchored() -> None:
    """Pinned because it is the kind of asymmetry a tidy-up introduces. The hook
    patterns deliberately carry NO word boundary; adding one would silently narrow
    the axis. (I added boundaries to the TS hook list by reflex while fixing the
    boundary divergence, and this assertion is what such a slip should hit.)"""
    if not FIX["constants"]["hook_patterns_are_unanchored"]:
        pytest.skip("fixture says hook patterns are anchored")
    for p in r.R_INTEREST_HOOK_PATTERNS:
        assert r"\b" not in p, f"hook pattern gained a word boundary: {p!r}"


# ── rounding ──────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("case", FIX["rounding_cases"], ids=lambda c: c["why"][:52])
def test_rounding_matches_the_shared_fixtures(case: dict) -> None:
    """Python's built-in round() IS the canonical rule; peq-scores.ts implements it
    explicitly as roundHalfEven() because Math.round is half-UP."""
    assert round(case["value"], case["digits"]) == case["out"]


# ── word boundaries ───────────────────────────────────────────────────────────
@pytest.mark.parametrize("case", FIX["boundary_cases"], ids=lambda c: c["why"][:52])
def test_boundary_behaviour_matches_the_shared_fixtures(case: dict) -> None:
    patterns = PATTERN_GROUPS[case["pattern_group"]]
    hit = any(re.search(p, case["text"], re.I) for p in patterns)
    assert hit is case["expect_match"], f"{case['text']!r} in {case['pattern_group']}"


# ── interest axis ─────────────────────────────────────────────────────────────
@pytest.mark.parametrize("case", FIX["interest_cases"], ids=lambda c: c["why"][:52])
def test_interest_score_matches_the_shared_fixtures(case: dict) -> None:
    assert q._interest_score(case["text"]) == case["expect_interest"]


# ── aggregation + verdict banding ─────────────────────────────────────────────
@pytest.mark.parametrize("case", FIX["aggregation_cases"], ids=lambda c: c["why"][:52])
def test_aggregation_matches_the_shared_fixtures(case: dict) -> None:
    """Pins the voice-redistribution branch, the clamp, and the threshold banding —
    all three re-implemented by hand on the TypeScript side."""
    a = case["axes"]
    assert case["voice_available"] is False, "only the redistribution branch is fixtured today"
    total = (
        (q.WEIGHT_FIDELITY + q.WEIGHT_VOICE) * a["fidelity"]
        + q.WEIGHT_STRUCTURE * a["structure"]
        + q.WEIGHT_ENRICHMENT * a["enrichment"]
        + q.WEIGHT_INTEREST * a["interest"]
    )
    total = round(min(max(total, 0.0), 100.0), 1)
    assert total == case["expect_total"]
    assert q.verdict_from_total(total) == case["expect_verdict"]
