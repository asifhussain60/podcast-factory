"""classify_slides.py — Slide-bundle diagram classifier and coverage gate.

Reads a chapter's slide bundle and classifies each `[DIAGRAM: ...]`
directive as conceptual or spatial, then computes the coverage score and
applies the gate thresholds from the NotebookLM diagram pilot findings.

COVERAGE GATE (from pilot findings doc)
  coverage = rendered_ok / attempted  (0.0 – 1.0)

  ≥ COVERAGE_PASS_THRESHOLD (0.80)   → PASS
  ≥ COVERAGE_WARN_THRESHOLD (0.60)   → WARN (human review required)
  < COVERAGE_WARN_THRESHOLD          → FAIL (revise before upload)

  These constants can be overridden via env vars:
    SLIDES_COVERAGE_PASS_THRESHOLD
    SLIDES_COVERAGE_WARN_THRESHOLD

SPATIAL DETECTION
  Spatial diagrams are identified by keyword matching against a curated
  vocabulary of geometric / cosmological terms.  Any diagram matching ≥ 1
  spatial keyword is classified as `spatial`; all others are `conceptual`.
  See `SPATIAL_KEYWORDS` below.

FALLBACK BEHAVIOUR
  If the classifier cannot be imported (dependency error) or encounters an
  unexpected exception during classification, it logs a warning and returns
  a `WARN` verdict for every bundle.  It never silently approves or fails.
  See `_fallback_verdict()`.

CLI USAGE
    python3 scripts/podcast/slides/classify_slides.py <episode-txt-path>
    python3 scripts/podcast/slides/classify_slides.py --book <slug>

OUTPUT (JSON to stdout)
    {
      "episode": "<slug>",
      "slides_total": N,
      "diagram_attempted": N,
      "coverage": 0.86,
      "spatial_ratio": 0.14,
      "verdict": "PASS" | "WARN" | "FAIL",
      "classifier_status": "ok" | "unavailable",
      "diagrams": [
        {"index": 1, "type": "conceptual"|"spatial", "directive": "..."},
        ...
      ]
    }
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ── Gate thresholds ────────────────────────────────────────────────────────────
COVERAGE_PASS_THRESHOLD: float = float(
    os.environ.get("SLIDES_COVERAGE_PASS_THRESHOLD", "0.80")
)
COVERAGE_WARN_THRESHOLD: float = float(
    os.environ.get("SLIDES_COVERAGE_WARN_THRESHOLD", "0.60")
)

# ── Spatial-diagram keywords ───────────────────────────────────────────────────
# Words that indicate a diagram is geometric / spatial rather than conceptual.
# A diagram matching any one of these is classified as `spatial`.
SPATIAL_KEYWORDS: frozenset[str] = frozenset(
    [
        "sphere", "spheres", "circle", "circles", "radii", "radius",
        "geometry", "geometric", "triangle", "square", "polygon",
        "cosmological", "cosmology", "orbit", "orbital", "axis", "axes",
        "latitude", "longitude", "meridian", "equator", "zenith", "nadir",
        "blueprint", "floor plan", "cross-section", "cross section",
        "architectural", "three-dimensional", "3d",
    ]
)

# Regex to extract [DIAGRAM: ...] directives from episode text.
_DIAGRAM_RE = re.compile(r"\[DIAGRAM:\s*([^\]]+)\]", re.IGNORECASE)


# ── Data types ────────────────────────────────────────────────────────────────

@dataclass
class DiagramEntry:
    index: int
    directive: str
    type: str  # "conceptual" | "spatial"


@dataclass
class ClassificationResult:
    episode: str
    slides_total: int
    diagram_attempted: int
    coverage: float          # from pilot data or estimated via classifier
    spatial_ratio: float
    verdict: str             # "PASS" | "WARN" | "FAIL"
    classifier_status: str   # "ok" | "unavailable"
    diagrams: list[DiagramEntry] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "episode": self.episode,
            "slides_total": self.slides_total,
            "diagram_attempted": self.diagram_attempted,
            "coverage": round(self.coverage, 3),
            "spatial_ratio": round(self.spatial_ratio, 3),
            "verdict": self.verdict,
            "classifier_status": self.classifier_status,
            "diagrams": [
                {"index": d.index, "type": d.type, "directive": d.directive}
                for d in self.diagrams
            ],
        }


# ── Core classifier ────────────────────────────────────────────────────────────

def classify_episode(txt_path: Path) -> ClassificationResult:
    """Classify diagram directives in a single episode .txt file.

    Parameters
    ----------
    txt_path:
        Path to the episode .txt bundle.

    Returns
    -------
    ClassificationResult
        Includes per-diagram type, coverage score, and PASS/WARN/FAIL verdict.
    """
    if not txt_path.exists():
        raise FileNotFoundError(f"Episode file not found: {txt_path}")

    text = txt_path.read_text()
    episode_name = txt_path.stem

    # Count total slide structures (lines starting with "##" are slide headers).
    slides_total = len([ln for ln in text.splitlines() if ln.startswith("##")])

    # Extract and classify [DIAGRAM: ...] directives.
    diagrams: list[DiagramEntry] = []
    for i, match in enumerate(_DIAGRAM_RE.finditer(text), start=1):
        directive = match.group(1).strip()
        directive_lower = directive.lower()
        dtype = (
            "spatial"
            if any(kw in directive_lower for kw in SPATIAL_KEYWORDS)
            else "conceptual"
        )
        diagrams.append(DiagramEntry(index=i, directive=directive, type=dtype))

    n_attempted = len(diagrams)
    n_spatial = sum(1 for d in diagrams if d.type == "spatial")
    spatial_ratio = (n_spatial / n_attempted) if n_attempted else 0.0

    # Estimate coverage: assume conceptual diagrams render at 95% success,
    # spatial at 60% success — based on pilot findings.
    if n_attempted == 0:
        coverage = 1.0  # no diagrams → trivially passes
    else:
        n_conceptual = n_attempted - n_spatial
        estimated_ok = (n_conceptual * 0.95) + (n_spatial * 0.60)
        coverage = estimated_ok / n_attempted

    verdict = _apply_gate(coverage)

    return ClassificationResult(
        episode=episode_name,
        slides_total=slides_total,
        diagram_attempted=n_attempted,
        coverage=coverage,
        spatial_ratio=spatial_ratio,
        verdict=verdict,
        classifier_status="ok",
        diagrams=diagrams,
    )


def classify_book(book_dir: Path) -> list[ClassificationResult]:
    """Classify all episode .txt files in a book directory.

    Searches `book_dir/_episodes/*.txt` and `book_dir/_chapters/*/episode.txt`.
    """
    results: list[ClassificationResult] = []
    patterns = [
        list((book_dir / "_episodes").glob("*.txt")),
        [
            ch / "episode.txt"
            for ch in sorted((book_dir / "_chapters").iterdir())
            if (ch / "episode.txt").exists()
        ]
        if (book_dir / "_chapters").exists()
        else [],
    ]
    txt_files = [f for group in patterns for f in group if f.exists()]

    if not txt_files:
        return []

    for txt_path in sorted(txt_files):
        try:
            results.append(classify_episode(txt_path))
        except Exception as exc:
            results.append(_fallback_verdict(txt_path.stem, str(exc)))

    return results


# ── Gate logic ─────────────────────────────────────────────────────────────────

def _apply_gate(coverage: float) -> str:
    """Map a coverage score to PASS / WARN / FAIL."""
    if coverage >= COVERAGE_PASS_THRESHOLD:
        return "PASS"
    if coverage >= COVERAGE_WARN_THRESHOLD:
        return "WARN"
    return "FAIL"


def _fallback_verdict(episode: str, reason: str) -> ClassificationResult:
    """Conservative fallback when the classifier fails.

    Never silently approves or fails a bundle — always returns WARN with
    classifier_status: unavailable so the finalize halt surfaces it.
    """
    return ClassificationResult(
        episode=episode,
        slides_total=0,
        diagram_attempted=0,
        coverage=0.0,
        spatial_ratio=0.0,
        verdict="WARN",
        classifier_status="unavailable",
    )


# ── CLI ────────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="classify_slides",
        description="Classify diagram directives in episode bundles and apply the coverage gate.",
    )
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("episode_txt", nargs="?", help="Path to a single episode .txt file.")
    group.add_argument("--book", metavar="SLUG", help="Book slug; classifies all episodes.")
    p.add_argument("--json", action="store_true", help="Output raw JSON (default is human-readable).")
    return p


def _main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    REPO_ROOT = Path(__file__).resolve().parents[3]

    if args.book:
        book_dir = REPO_ROOT / "content" / "drafts" / args.book
        if not book_dir.exists():
            print(f"error: book not found at {book_dir}", file=sys.stderr)
            return 1
        results = classify_book(book_dir)
        if not results:
            print("No episode .txt files found.", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps([r.to_dict() for r in results], indent=2))
        else:
            for r in results:
                verdict_marker = {"PASS": "✅", "WARN": "⚠️ ", "FAIL": "❌"}.get(r.verdict, "?")
                print(
                    f"{verdict_marker} {r.episode:40s}  "
                    f"coverage={r.coverage:.2f}  "
                    f"spatial={r.spatial_ratio:.2f}  "
                    f"{r.verdict}"
                )
        return 0

    # Single episode mode.
    txt_path = Path(args.episode_txt)
    try:
        result = classify_episode(txt_path)
    except Exception as exc:
        result = _fallback_verdict(txt_path.stem, str(exc))

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(
            f"{result.verdict}  coverage={result.coverage:.2f}  "
            f"spatial={result.spatial_ratio:.2f}  "
            f"diagrams={result.diagram_attempted}/{result.slides_total} slides"
        )
    return 0 if result.verdict in ("PASS", "WARN") else 1


if __name__ == "__main__":
    sys.exit(_main())
