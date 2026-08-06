"""_book_visual_policy.py — who is allowed to put a figure in the reading edition.

A companion edition is a TEXT deliverable: prose, citations, verses, and the
Arabic they carry. Its visuals are chosen by a human in the Book Composer, one
placement at a time, and written to ``book/visual-layout.json``. The pipeline's
job is to never pre-empt that choice.

Two halves, matching the two ways a figure could reach a page:

  * POLICY — under ``book_visuals: manual_only`` the generating phases
    (0book-illustrate, 0book-slide-import) do not run at all, so no candidate
    asset is ever produced behind the curator's back.
  * PROOF — a deterministic scan of the composed ``book.md`` plus the layout
    contract, asserting the edition really is text-only. Policy states intent;
    this measures the artifact, because a figure could also arrive by a model
    emitting image markup mid-prose, which no phase toggle would catch.

Pure and side-effect-free apart from writing its own report. Never mutates
``book.md`` — an unexpected figure is surfaced for a human, not silently deleted
from a book someone may have meant to illustrate.

THE RULE, stated once (Asif, 2026-08-06 — cite this, do not re-copy it):

  A diagram NEVER enters a chapter by pipeline action. 0book-illustrate and
  0book-slide-import may GENERATE and OFFER — each asset is registered as a
  candidate in ``book/visuals/index.json`` — and placement is a human act in the
  Astro Book Composer, which writes ``book/visual-layout.json``, the renderer's
  only placement source. ``book.md`` stays diagram-free and IS the render input
  on every route (``build_book_pdf._pick_book_md``).

  An empty ``visual-layout.json`` is therefore the CORRECT resting state of a
  book nobody has curated yet, and must never be reported as an unfinished job.
  Generated assets sitting unplaced are a palette waiting on a person, not debris.

  There is no second copy of the book. ``book-illustrated.md`` and
  ``book-slides.md`` were the v1 injected variants; the illustrate passthroughs
  went on writing the first as a plain copy long after the renderer stopped
  reading it, and the deck injector went on PREFERRING it — so on a book carrying
  a stale one, deck anchors were validated against prose weeks out of date. Four
  leftovers were deleted 2026-08-06, one of them nine weeks stale and missing a
  whole chapter of a published book. ``injected_variants`` below reports any that
  reappear, because a scan of ``book.md`` cannot see a file beside it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from _pipeline_flags import BOOK_VISUALS_MANUAL_ONLY, book_visuals

# Every way a figure can enter the rendered page from the markdown itself. The
# renderer passes raw <figure> blocks through, resolves <img>, and inlines SVG, so
# each of these is a real path to a picture — not a stylistic preference.
_VISUAL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("markdown-image", re.compile(r"!\[[^\]]*\]\([^)]*\)")),
    ("html-img", re.compile(r"<img\b", re.I)),
    ("inline-svg", re.compile(r"<svg\b", re.I)),
    ("figure-block", re.compile(r"<figure\b", re.I)),
    ("picture-block", re.compile(r"<picture\b", re.I)),
    ("embed-or-object", re.compile(r"<(?:embed|object|iframe|canvas|video)\b", re.I)),
    ("mermaid-fence", re.compile(r"(?m)^```\s*mermaid\b", re.I)),
)

_CHAPTER_HEADING_RE = re.compile(r"(?m)^##\s+(.+?)\s*$")

#: Book variants the pipeline used to write by INJECTING figures into the prose.
#: Nothing produces these any more and nothing renders them — the renderer reads
#: book.md on every route. One on disk means either a retired artifact nobody
#: cleaned up, or a phase that has started injecting again; both are worth a
#: human's attention, and neither is visible by scanning book.md alone.
INJECTED_VARIANTS: tuple[str, ...] = ("book-illustrated.md", "book-slides.md")


def injected_variants(book_dir: Path) -> list[str]:
    """Which retired injected-variant files exist beside book.md. Usually none."""
    book = Path(book_dir) / "book"
    return [name for name in INJECTED_VARIANTS if (book / name).exists()]


def scan_markdown(book_md: str) -> list[dict[str, Any]]:
    """Every visual-bearing construct in the markdown, with its chapter and line."""
    lines = book_md.split("\n")
    chapter = "(front matter)"
    findings: list[dict[str, Any]] = []
    for n, line in enumerate(lines, start=1):
        heading = _CHAPTER_HEADING_RE.match(line)
        if heading:
            chapter = heading.group(1).strip()
            continue
        for kind, pattern in _VISUAL_PATTERNS:
            if pattern.search(line):
                findings.append({"kind": kind, "chapter": chapter, "line": n, "text": line.strip()[:120]})
                break
    return findings


def layout_placements(book_dir: Path) -> int:
    """How many figures the human's curated contract will place. Absent file = 0."""
    path = Path(book_dir) / "book" / "visual-layout.json"
    if not path.exists():
        return 0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return 0
    if isinstance(data, dict):
        for key in ("placements", "figures", "items"):
            value = data.get(key)
            if isinstance(value, list):
                return len(value)
        return 0
    return len(data) if isinstance(data, list) else 0


def check_text_only(book_dir: Path, *, log=print) -> dict[str, Any]:
    """Assert the composed edition is text-only under ``manual_only``. Report-only.

    ``curated_placements`` is reported but never a violation: a figure the human
    placed in the Composer is exactly what this policy exists to protect.
    """
    book_dir = Path(book_dir).resolve()
    book_md = book_dir / "book" / "book.md"
    policy = book_visuals(book_dir)
    findings = scan_markdown(book_md.read_text(encoding="utf-8")) if book_md.exists() else []
    curated = layout_placements(book_dir)
    variants = injected_variants(book_dir)
    violations = findings if policy == BOOK_VISUALS_MANUAL_ONLY else []
    report = {
        "schema": "book.visual-policy/v1",
        "policy": policy,
        "text_only": not violations,
        "pipeline_inserted": findings,
        "curated_placements": curated,
        "injected_variants": variants,
    }
    out = book_dir / "_system" / "book-visual-policy.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if policy != BOOK_VISUALS_MANUAL_ONLY:
        log(f"    visual-policy: {policy} — pipeline visuals allowed for this book")
    elif violations:
        log(f"    visual-policy: {len(violations)} pipeline-inserted visual(s) in a text-only edition:")
        for f in violations[:5]:
            log(f"      ! {f['chapter']} line {f['line']}: {f['kind']}")
    else:
        log(f"    visual-policy: text-only confirmed · {curated} human-curated figure(s) from the Composer")
    if variants:
        # Not folded into `violations`: book.md itself is clean, so calling the
        # edition not-text-only would be false. It is a separate fact and is
        # reported as one.
        log(f"    visual-policy: retired injected variant(s) on disk — {', '.join(variants)}")
    return report


if __name__ == "__main__":  # pragma: no cover - thin CLI
    import sys

    if len(sys.argv) != 2:
        print("usage: _book_visual_policy.py <BOOK_DIR>", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(0 if check_text_only(Path(sys.argv[1]))["text_only"] else 1)
