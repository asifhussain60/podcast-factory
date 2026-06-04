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
from _paths import REPO_ROOT
from typing import Any

DEFAULT_FIXTURES_DIR = REPO_ROOT / "content/podcast/.skill/_learning/fixtures"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _rules import (
    MODERNIZE_DENY,
    SURPRISE_DENY,
    HONORIFICS as HONORIFICS_RAW,
    AI_CLICHE_DENY,
    DEEP_DIVE_SELF_REFERENCE_PATTERNS,
    ESSENTIALISM_STEM_PATTERNS,
    FAUX_PROFUNDITY_OPENING_PATTERNS,
    PREMATURE_CLOSURE_PATTERNS,
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


def detect_j2_bold_header(text: str) -> list[str]:
    """J2 (bold-header surface form) — markdown bold/header carrying a known
    long ceremonial name AFTER its first plain-text mention.

    Detector strategy: find every `**<phrase>**` where <phrase> is 4+ tokens
    AND begins with one of the long-name tokens from the name-alias policy
    (kept as a compact prefix list here to keep the fixture deterministic).
    Each match is one hit; first-mention exemption is not modeled (fixtures
    assume the long name has appeared earlier as plain text).
    """
    long_name_prefixes = [
        "Abu Hatim Ahmad ibn Hamdan al-Razi",
        "Abu Ya'qub Ishaq al-Sijistani",
        "Hamid al-Din Ahmad ibn Abdullah al-Kirmani",
        "Muhammad ibn Ahmad al-Nasafi",
    ]
    hits = []
    for m in re.finditer(r"\*\*([^*\n]+)\*\*", text):
        phrase = m.group(1).strip()
        for prefix in long_name_prefixes:
            if phrase.startswith(prefix):
                ln = text[: m.start()].count("\n") + 1
                hits.append(f"L{ln}:{prefix}")
                break
    return sorted(set(hits))


def detect_surprise_positive_companion(text: str) -> list[str]:
    """R-NOSURPRISE positive-companion presence check.

    The framing's `## Do not` block must carry BOTH the DENY clause AND the
    positive directive promoted on 2026-05-18. The detector returns hits
    only when the positive paragraph is MISSING — its presence is the
    intended state, so a clean framing produces zero hits.
    """
    required_phrase = "name what is new in ONE short clause"
    if required_phrase in text:
        return []
    return ["MISSING:surprise-positive-companion"]


def _norm(text: str) -> str:
    """Normalize text for phrase/pattern matching: lowercase, straight apostrophes."""
    return (
        text.lower()
        .replace("\u2019", "'")  # right single quotation mark → straight
        .replace("\u2018", "'")  # left single quotation mark → straight
        .replace("\n", " ")
    )


def detect_ai_cliche(text: str) -> list[str]:
    """R-NO-AI-CLICHE — banned podcast/AI stock phrases."""
    tl = _norm(text)
    matched: list[str] = []
    for phrase in AI_CLICHE_DENY:
        p = phrase.lower().replace("\u2019", "'").replace("\u2018", "'")
        if p in tl:
            matched.append(p)
    # Dedup: if phrase A is a strict prefix of phrase B and both matched, keep A only.
    deduped: list[str] = []
    for phrase in matched:
        dominated = any(
            other != phrase and phrase.startswith(other)
            for other in matched
        )
        if not dominated:
            deduped.append(phrase)
    return sorted(set(deduped))


def detect_deep_dive_self_reference(text: str) -> list[str]:
    """R-NO-DEEP-DIVE-SELF-REFERENCE — self-referential episode framing."""
    tl = _norm(text)
    hits: list[str] = []
    for pat in DEEP_DIVE_SELF_REFERENCE_PATTERNS:
        for m in re.finditer(pat, tl, re.IGNORECASE):
            hits.append(m.group(0).strip())
    return sorted(set(hits))


def detect_essentialism(text: str) -> list[str]:
    """R-NO-ESSENTIALISM-EXTERNAL — blanket tradition claims."""
    hits: list[str] = []
    for pat in ESSENTIALISM_STEM_PATTERNS:
        for m in re.finditer(pat, text, re.IGNORECASE):
            hit = m.group(0).strip()
            # Pattern 8 matches "the [tradition] view …"; strip the leading article.
            if re.match(r"^the\s+", hit, re.IGNORECASE):
                hit = re.sub(r"^the\s+", "", hit, count=1, flags=re.IGNORECASE)
            # No-True-Scotsman pattern ends at "would/don't/…"; extend to include
            # "never" when it is the very next word in the source text.
            if re.search(r"\bwould$", hit, re.IGNORECASE):
                tail = text[m.end():]
                extra = re.match(r"[ \t]+never\b", tail, re.IGNORECASE)
                if extra:
                    hit = hit + " never"
            hits.append(hit.strip())
    return sorted(set(hits))


def detect_faux_profundity(text: str) -> list[str]:
    """R-NO-FAUX-PROFUNDITY-OPENING — rhetorical opening gestures."""
    tl = _norm(text)
    hits: list[str] = []
    for pat in FAUX_PROFUNDITY_OPENING_PATTERNS:
        for m in re.finditer(pat, tl, re.IGNORECASE):
            hits.append(m.group(0).strip())
    return sorted(set(hits))


def detect_premature_closure(text: str) -> list[str]:
    """R-NO-PREMATURE-CLOSURE — closing sections that falsely resolve hard questions."""
    tl = _norm(text)
    hits: list[str] = []
    for pat in PREMATURE_CLOSURE_PATTERNS:
        for m in re.finditer(pat, tl, re.IGNORECASE):
            hits.append(m.group(0).strip())
    return sorted(set(hits))


DETECTORS = {
    "em_dash": detect_em_dash,
    "honorific_repeat": detect_honorific_repeat,
    "inline_phonetic": detect_inline_phonetic,
    "modernize": detect_modernize,
    "formal_transition": detect_formal_transition,
    "abbreviation": detect_abbreviation,
    "surprise": detect_surprise,
    "j2_bold_header": detect_j2_bold_header,
    "surprise_positive_companion": detect_surprise_positive_companion,
    "ai_cliche": detect_ai_cliche,
    "deep_dive_self_reference": detect_deep_dive_self_reference,
    "essentialism": detect_essentialism,
    "faux_profundity": detect_faux_profundity,
    "premature_closure": detect_premature_closure,
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
