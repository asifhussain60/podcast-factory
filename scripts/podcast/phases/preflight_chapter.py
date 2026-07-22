"""phases/preflight_chapter.py — $0 deterministic smoke gate for a chapter.

Fail-fast discipline (Phase E, C2): catch the broad *deterministic* failure
class — missing chapter file, missing/malformed contract, out-of-band word
count — BEFORE any paid/long step (author_framing LLM call, convergence loop)
or the real-money Azure/Gemini phases. No LLM, no subprocess, no side effects.

Used in two places:
  - Pre-loop in chapter_driver: run on EVERY chapter before the per-chapter loop
    spends a cent, so a deterministic bug in chapter N halts at $0 before
    chapter 1's framing is authored.
  - Inside per_chapter_pass, after extract and BEFORE author_framing, as
    defense-in-depth so a structurally-broken chapter never pays for a framing
    call.

This does NOT replace the deep content validators (doctrinal, phonetics, framing
structure) that run at build time — those need the authored framing and are
content judgments, not the systemic/deterministic class this gate guards.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _contract_validation import validate_contract_full  # FIX 14: one validator, four gates
from _validator_constants import CHAPTER_WORD_MAX_HARD, CHAPTER_WORD_MIN_HARD

try:
    import yaml
except Exception:  # pragma: no cover - PyYAML is a hard dep elsewhere
    yaml = None


def _chapter_file(book_dir: Path, slug: str) -> Path | None:
    return next((book_dir / "chapters").glob(f"ch*-{slug}.txt"), None)


def smoke_check_chapter(book_dir: Path, slug: str) -> tuple[bool, str]:
    """Return (ok, reason). ok=True means the chapter is safe to spend on.

    Deterministic, $0, no side effects. ``reason`` is a one-line human-readable
    cause when ok is False (and the empty string when ok is True).
    """
    # 1. Chapter file present.
    chapter_file = _chapter_file(book_dir, slug)
    if chapter_file is None:
        return False, f"chapter file missing (expected chapters/ch*-{slug}.txt)"

    # 2. Contract present, parses, and carries the keys the pipeline relies on.
    contract_file = book_dir / "chapter-contracts" / f"{slug}.yml"
    if not contract_file.is_file():
        return False, f"contract missing (expected chapter-contracts/{slug}.yml)"
    if yaml is not None:
        try:
            contract = yaml.safe_load(contract_file.read_text(encoding="utf-8"))
        except Exception as e:
            return False, f"contract parse error: {str(e).splitlines()[0][:160]}"
        if not isinstance(contract, dict):
            return False, "contract is not a YAML mapping"
        if not str(contract.get("slug") or "").strip():
            return False, "contract missing required `slug`"
        if not (contract.get("episode_number") or str(contract.get("title") or "").strip()):
            return False, "contract missing both `episode_number` and `title`"

        # 2b. FIX 14 — FULL contract validation (the same single validator
        # extract and pipeline_lint enforce), so the $0 pre-loop gate now
        # catches everything those later, more expensive layers would refuse:
        # debate-with-no-block, slug/chapter-file rename mismatch, and
        # R-HOST-ROLE-PARITY role enums included.
        findings = validate_contract_full(
            contract,
            chapter_file,
            book_dir,
            contract_path=contract_file,
        )
        if findings:
            return False, (f"contract validation ({len(findings)} finding(s)): " + " | ".join(findings))

    # 3. Chapter word count inside the hard band (catches empty / truncated / huge).
    try:
        n = len(chapter_file.read_text(encoding="utf-8").split())
    except Exception as e:
        return False, f"chapter unreadable: {str(e).splitlines()[0][:160]}"
    if n < CHAPTER_WORD_MIN_HARD or n > CHAPTER_WORD_MAX_HARD:
        return False, (f"chapter word count {n} outside hard band [{CHAPTER_WORD_MIN_HARD}, {CHAPTER_WORD_MAX_HARD}]")

    # 4. Density gate (R-MAX-CONCEPTS, 2026-06-10) — OPT-IN via
    #    `density_standard: 2` in series-config.yaml. Halts the per-chapter
    #    loop at $0 before any framing/convergence spend on an over-dense
    #    chapter. Legacy books (no flag) are never blocked here — 26 of the
    #    pre-standard chapters would otherwise dead-halt on every retry.
    try:
        from _content_profile import density_standard_active

        if density_standard_active(book_dir):
            from chapter_density_audit import audit_chapter

            density = audit_chapter(chapter_file, book_dir.name, "")
            if density.status == "FAIL":
                return False, (
                    f"density gate: {density.concept_count} concept sections "
                    f"(max {density.max_concepts}) — split required before "
                    f"authoring; see docs/standards/chapter-density.md"
                )
    except ImportError:
        pass  # density tooling unavailable — never block the smoke gate on it

    return True, ""


def smoke_check_book(book_dir: Path, chapter_slugs: list[str]) -> list[tuple[str, str]]:
    """Run smoke_check on every chapter. Return [(slug, reason), ...] for FAILURES.

    An empty list means every chapter passed the $0 gate and the per-chapter loop
    is safe to spend on.
    """
    failures: list[tuple[str, str]] = []
    for slug in chapter_slugs:
        ok, reason = smoke_check_chapter(book_dir, slug)
        if not ok:
            failures.append((slug, reason))
    return failures
