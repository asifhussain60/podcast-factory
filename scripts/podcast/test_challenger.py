#!/usr/bin/env python3
"""test_challenger.py — Regression harness for the deterministic auto-fix layer.

PURPOSE

  Stage 4 of the podcast-skill learning pipeline (sense → aggregate → propose
  → TEST → promote). The `podcast-challenger` agent is an LLM-driven semantic
  reviewer; its auto-fix layer is deterministic (regex + substring matching
  against canonical lists in `_rules.py` and `build_episode_txt.py`).

  This harness pins that deterministic layer with frozen fixtures:

    _learning/fixtures/<check-id>/
      ├── input.txt        — minimal artifact exhibiting the failure
      └── expected.json    — {"check_id":"...","detector":"...","hits":[...]}

  Each fixture declares its detector. The harness runs the detector against
  input.txt and asserts the produced hits set equals the expected hits set.
  Any mismatch fails the test (non-zero exit) and the offending check is
  reported.

  When a normative rule list changes (a new entry added to MODERNIZE_DENY,
  a new INLINE_PHONETIC_PATTERNS regex, etc.), `python3 test_challenger.py`
  must still exit 0. If it doesn't, the change has regressed a prior fixture
  and needs adjusting — either the fixture has stale expectations (rare;
  intentional rule rewrite) or the rule change broke a real prior fix.

USAGE

  python3 scripts/podcast/test_challenger.py

  Optional flags:
    --fixtures <dir>     Use a non-default fixtures directory.
    --update-golden      Rewrite expected.json from actual detector output for
                         every fixture. USE WITH CAUTION — disables regression
                         signal. Intended for first-time fixture authoring or
                         intentional rule shifts.
    --verbose            Print every fixture result.

EXIT CODES

  0  — all fixtures green.
  1  — at least one fixture regressed.
  2  — fixtures directory empty or invalid.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURES_DIR = REPO_ROOT / "content/podcast/.skill/_learning/fixtures"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _rules import (
    MODERNIZE_DENY,
    SURPRISE_DENY,
    HONORIFICS as HONORIFICS_RAW,
)

# Pull canonical regex sets from build_episode_txt without triggering its CLI
# (the module has top-level side-effect-free constants only).
from build_episode_txt import (  # noqa: E402
    INLINE_PHONETIC_PATTERNS,
    FORBIDDEN_ABBREVIATIONS,
    HONORIFIC_PHRASES,
)

# Custom detectors below mirror the auto-fix detection logic the challenger
# uses. Each takes (text: str) and returns list[str] of hit signatures.
# Keep signatures stable across runs so expected.json comparisons are
# byte-deterministic.


def detect_em_dash(text: str) -> list[str]:
    """B5 — em-dashes in chapter prose. Auto-fix: replace with ', '."""
    hits = []
    for i, line in enumerate(text.splitlines(), start=1):
        for m in re.finditer(r"—", line):
            hits.append(f"L{i}:col{m.start() + 1}")
    return hits


def detect_honorific_repeat(text: str) -> list[str]:
    """O1 / C3 — honorific expansions appearing > 1× in the same text."""
    hits = []
    for pat in HONORIFIC_PHRASES:
        matches = list(pat.finditer(text))
        if len(matches) > 1:
            for extra in matches[1:]:
                ln = text[: extra.start()].count("\n") + 1
                hits.append(f"{pat.pattern}@L{ln}")
    return hits


def detect_inline_phonetic(text: str) -> list[str]:
    """N1 — chapter carries inline phonetic parens."""
    hits = []
    for pat in INLINE_PHONETIC_PATTERNS:
        for m in pat.finditer(text):
            ln = text[: m.start()].count("\n") + 1
            hits.append(f"L{ln}:{m.group(0)[:30]}")
    return hits


def detect_modernize(text: str) -> list[str]:
    """M1 / M3 — modernization-DENY phrase in framing or transcript."""
    hits = []
    for phrase in MODERNIZE_DENY:
        if phrase in text:
            hits.append(phrase.strip())
    return sorted(set(hits))


def detect_formal_transition(text: str) -> list[str]:
    """R4 / R6 — formal-essay transitions banned by R-NOFORMAL."""
    formal_transitions = [
        "Firstly", "Secondly", "Furthermore",
        "In conclusion", "Moving on to", "To summarize", "Lastly",
    ]
    hits = []
    for phrase in formal_transitions:
        if re.search(rf"\b{re.escape(phrase)}\b", text):
            hits.append(phrase)
    return sorted(set(hits))


def detect_abbreviation(text: str) -> list[str]:
    """O2 — abbreviated work titles per FORBIDDEN_ABBREVIATIONS."""
    hits = []
    for pat in FORBIDDEN_ABBREVIATIONS:
        if re.search(pat, text):
            hits.append(pat)
    return sorted(set(hits))


def detect_surprise(text: str) -> list[str]:
    """M2 / M4 — surprise-DENY phrase in framing or transcript."""
    hits = []
    for phrase in SURPRISE_DENY:
        if phrase in text:
            hits.append(phrase.strip())
    return sorted(set(hits))


DETECTORS = {
    "em_dash": detect_em_dash,
    "honorific_repeat": detect_honorific_repeat,
    "inline_phonetic": detect_inline_phonetic,
    "modernize": detect_modernize,
    "formal_transition": detect_formal_transition,
    "abbreviation": detect_abbreviation,
    "surprise": detect_surprise,
}


def run_fixture(fixture_dir: Path, update_golden: bool, verbose: bool) -> tuple[bool, str]:
    input_path = fixture_dir / "input.txt"
    expected_path = fixture_dir / "expected.json"
    if not input_path.exists():
        return False, f"{fixture_dir.name}: missing input.txt"
    if not expected_path.exists() and not update_golden:
        return False, f"{fixture_dir.name}: missing expected.json (run --update-golden to bootstrap)"

    input_text = input_path.read_text(encoding="utf-8")

    if expected_path.exists():
        try:
            expected = json.loads(expected_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            return False, f"{fixture_dir.name}: expected.json malformed — {e}"
        detector_name = expected.get("detector")
    else:
        detector_name = fixture_dir.name
        expected = {"detector": detector_name, "hits": []}

    if detector_name not in DETECTORS:
        return False, f"{fixture_dir.name}: unknown detector '{detector_name}'"

    actual_hits = DETECTORS[detector_name](input_text)
    expected_hits = expected.get("hits", [])

    if update_golden:
        new_expected = {
            "check_id": expected.get("check_id", fixture_dir.name),
            "detector": detector_name,
            "hits": actual_hits,
        }
        expected_path.write_text(
            json.dumps(new_expected, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return True, f"{fixture_dir.name}: GOLDEN updated → {len(actual_hits)} hits"

    if sorted(actual_hits) == sorted(expected_hits):
        if verbose:
            return True, f"{fixture_dir.name}: PASS ({len(actual_hits)} hits)"
        return True, ""
    return False, (
        f"{fixture_dir.name}: REGRESSION\n"
        f"    detector  : {detector_name}\n"
        f"    expected  : {sorted(expected_hits)}\n"
        f"    actual    : {sorted(actual_hits)}\n"
        f"    missing   : {sorted(set(expected_hits) - set(actual_hits))}\n"
        f"    new       : {sorted(set(actual_hits) - set(expected_hits))}"
    )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES_DIR)
    p.add_argument("--update-golden", action="store_true")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    if not args.fixtures.is_dir():
        print(f"ERROR: fixtures directory not found: {args.fixtures}", file=sys.stderr)
        return 2

    fixture_dirs = sorted([d for d in args.fixtures.iterdir() if d.is_dir()])
    if not fixture_dirs:
        print(f"ERROR: no fixtures in {args.fixtures}", file=sys.stderr)
        return 2

    passes = []
    fails = []
    for fdir in fixture_dirs:
        ok, msg = run_fixture(fdir, args.update_golden, args.verbose)
        if ok:
            passes.append(fdir.name)
            if msg:
                print(msg)
        else:
            fails.append((fdir.name, msg))
            print(msg, file=sys.stderr)

    print(f"\ntest_challenger summary: {len(passes)} passed, {len(fails)} failed")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
