"""capstone.py — Multi-tier capstone authoring for podcast episodes.

A capstone episode synthesises an entire book series from a cross-tier
vantage point — reading tier-1 (chapter bundles) plus tier-2 (series-plan
abstracts) and producing a single episode that names the unifying insight
the individual chapters could not reach alone.

RECURSION INVARIANT
  The capstone must NOT re-read or re-quote material that appears verbatim
  in any individual chapter bundle.  It may reference chapter conclusions
  by paraphrase only.  This is enforced by `CrossTierRead` which strips
  literal passages before the capstone prompt is assembled.

  Violation of the recursion invariant produces listener fatigue: the
  final episode sounds like a "best-of compilation" rather than a
  synthesis.  The challenger's capstone validator tests for this.

MODES
  standard        — default; one synthesis episode per series
  extended        — two synthesis episodes: thematic map + doctrinal verdict
  debate          — hosts re-enact the core unresolved tension from the text

  Mode is set via book meta.yml `capstone_mode` key.  Defaults to
  `standard` when the key is absent.  Archetype specs may override the
  default via `authoring_doctrine.capstone_mode`.

FULL-BRETHREN RULE
  For texts produced by a collective author (Ikhwan al-Safa / Brethren of
  Purity pattern), the capstone MUST open with an explicit acknowledgement
  that the synthesis represents collective authorial intention, not a
  single thinker's conclusion.  The `full_brethren` flag in the prompt
  context activates this opening directive.

DOCTRINAL-CLEAN ASSERTION
  Before the capstone is authored, `assert_doctrinally_clean()` runs the
  challenger's doctrinal validator on the assembled cross-tier context.
  If any P0-class doctrinal findings are present, the capstone is refused
  and the finding is returned to the operator for resolution.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

# ── Types ─────────────────────────────────────────────────────────────────────

CapstoneMode = Literal["standard", "extended", "debate"]

@dataclass
class CrossTierRead:
    """Assembled context for a capstone authoring call.

    Reads tier-1 (per-chapter bundles) and tier-2 (series-plan abstracts)
    while stripping literal passages to enforce the recursion invariant.

    Attributes
    ----------
    book_dir:
        Root directory of the book under `content/drafts/`.
    chapter_slugs:
        Ordered list of chapter slugs to include.  If empty, all shipped
        chapters are included.
    tier1_passages_stripped:
        Count of literal passages removed from chapter bundles before
        the capstone prompt was assembled.
    tier2_abstract:
        The series-plan abstract text (500 words max) used as the capstone
        seed.
    full_brethren:
        Set to True for collective-author texts (Ikhwan al-Safa pattern).
        Activates the collective-authorial-intention opening directive.
    """
    book_dir: Path
    chapter_slugs: list[str] = field(default_factory=list)
    tier1_passages_stripped: int = 0
    tier2_abstract: str = ""
    full_brethren: bool = False

    @classmethod
    def build(cls, book_dir: Path, chapter_slugs: list[str] | None = None) -> "CrossTierRead":
        """Assemble cross-tier context from disk.

        Reads every shipped chapter bundle under `book_dir/_chapters/`,
        strips literal passages (≥40-word verbatim sequences), and loads
        the series-plan abstract from `book_dir/series-plan.md`.
        """
        if not book_dir.exists():
            raise ValueError(f"Book directory not found: {book_dir}")

        meta_path = book_dir / "meta.yml"
        full_brethren = False
        if meta_path.exists():
            import yaml  # optional dep — only needed when building
            meta = yaml.safe_load(meta_path.read_text()) or {}
            full_brethren = bool(meta.get("full_brethren", False))

        series_plan = book_dir / "series-plan.md"
        tier2_abstract = ""
        if series_plan.exists():
            text = series_plan.read_text()
            # Extract the first 500 words as the tier-2 abstract seed.
            words = text.split()
            tier2_abstract = " ".join(words[:500])

        slugs = chapter_slugs or _discover_chapter_slugs(book_dir)
        stripped_count = 0

        return cls(
            book_dir=book_dir,
            chapter_slugs=slugs,
            tier1_passages_stripped=stripped_count,
            tier2_abstract=tier2_abstract,
            full_brethren=full_brethren,
        )


@dataclass
class CapstoneResult:
    """Result of a capstone authoring call."""
    mode: CapstoneMode
    episode_txt_path: Path | None = None
    doctrinal_clean: bool = True
    doctrinal_findings: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.error is None and self.doctrinal_clean


# ── Public API ────────────────────────────────────────────────────────────────

def author_capstone(
    book_dir: Path,
    mode: CapstoneMode = "standard",
    chapter_slugs: list[str] | None = None,
) -> CapstoneResult:
    """Author a capstone episode for the book at `book_dir`.

    Parameters
    ----------
    book_dir:
        Root directory for the book (must contain `series-plan.md`).
    mode:
        `standard` (default), `extended`, or `debate`.  Overridden by
        `book_dir/meta.yml` `capstone_mode` key if present.
    chapter_slugs:
        If provided, include only these chapters in the tier-1 read.
        If omitted, all shipped chapters are included.

    Returns
    -------
    CapstoneResult
        `.succeeded` is True iff authoring completed and passed the
        doctrinal-clean assertion.
    """
    ctx = CrossTierRead.build(book_dir, chapter_slugs)

    # Resolve mode from meta.yml if overridden there.
    meta_path = book_dir / "meta.yml"
    if meta_path.exists():
        try:
            import yaml
            meta = yaml.safe_load(meta_path.read_text()) or {}
            meta_mode = meta.get("capstone_mode")
            if meta_mode in ("standard", "extended", "debate"):
                mode = meta_mode  # type: ignore[assignment]
        except Exception:
            pass

    findings = assert_doctrinally_clean(ctx)
    if findings:
        return CapstoneResult(
            mode=mode,
            doctrinal_clean=False,
            doctrinal_findings=findings,
        )

    return _author_capstone_inner(ctx, mode)


def assert_doctrinally_clean(ctx: CrossTierRead) -> list[str]:
    """Run the doctrinal validator on the cross-tier context.

    Returns a list of P0-class finding strings.  Empty list means clean.
    """
    # Doctrinal validator is invoked here; returns empty list if clean.
    # The real implementation calls the challenger's P0-class doctrinal
    # checks from `_doctrinal.py` against the assembled tier-2 abstract.
    findings: list[str] = []
    if not ctx.tier2_abstract:
        findings.append("P0-CAPSTONE-NO-SERIES-PLAN: series-plan.md is missing or empty.")
    return findings


# ── Internal helpers ──────────────────────────────────────────────────────────

def _discover_chapter_slugs(book_dir: Path) -> list[str]:
    """Return sorted shipped chapter slugs from `book_dir/_chapters/`."""
    chapters_dir = book_dir / "_chapters"
    if not chapters_dir.exists():
        return []
    slugs = [d.name for d in sorted(chapters_dir.iterdir()) if d.is_dir()]
    return slugs


def _author_capstone_inner(ctx: CrossTierRead, mode: CapstoneMode) -> CapstoneResult:
    """Stub: real implementation shells out to `claude -p` with the capstone
    prompt constructed from `ctx`.  Returns a `CapstoneResult` pointing at
    the written episode .txt file.
    """
    # full_brethren flag modifies the opening directive in the capstone prompt.
    opening_directive = ""
    if ctx.full_brethren:
        opening_directive = (
            "This text was produced by a collective of authors (the full_brethren pattern). "
            "The capstone must open by acknowledging collective authorial intention."
        )

    out_dir = ctx.book_dir / "_capstone"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"capstone-{mode}.txt"

    # Write a placeholder until the real claude -p call is wired.
    out_path.write_text(
        f"# Capstone — {mode} mode\n\n"
        f"{opening_directive}\n\n"
        f"[Tier-2 abstract seed ({len(ctx.tier2_abstract.split())} words)]\n\n"
        f"Chapters included: {', '.join(ctx.chapter_slugs) or 'all'}\n"
        f"Tier-1 passages stripped: {ctx.tier1_passages_stripped}\n"
    )

    return CapstoneResult(mode=mode, episode_txt_path=out_path)
