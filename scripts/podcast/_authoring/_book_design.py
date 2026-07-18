"""_book_design.py — Phase 0book-design: book-craft re-segmentation.

Re-segments a book's refined source into the chapter structure of a polished
modern reading edition — its OWN chapter count / boundaries / titles + a preface,
INDEPENDENT of the podcast episode cuts (PDF path, not podcast path). Emits
BOOK_DIR/book/book-toc.json.

One Opus pass via `claude -p` (flat-rate Max). Idempotent: skips if book-toc.json
already exists unless force=True.

Standalone:
  python3 -m _authoring._book_design <BOOK_DIR> [--force]
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from ._core import AuthoringError, _run_claude_p_with_retry

_DESIGN_TIMEOUT = 600


def _numbered(text: str) -> str:
    return "\n".join(f"{i:>4} | {ln}" for i, ln in enumerate(text.split("\n"), 1))


def _extract_json(stdout: str) -> dict:
    s = stdout.strip()
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", s, re.S)
    if m:
        s = m.group(1)
    else:
        i, j = s.find("{"), s.rfind("}")
        if i != -1 and j != -1:
            s = s[i : j + 1]
    return json.loads(s)


def _resolve_source(book_dir: Path) -> str:
    """Refined English is the design input; fall back to the concatenation of the
    enriched chapters for books authored outside the orchestrator (no refined file)."""
    refined = book_dir / "_system" / "source" / "text" / "refined-english.md"
    if refined.exists():
        return refined.read_text(encoding="utf-8")
    chapters = sorted((book_dir / "chapters").glob("ch*.txt"))
    if chapters:
        return "\n\n".join(c.read_text(encoding="utf-8") for c in chapters)
    raise AuthoringError(
        phase="0book-design",
        message=f"no design input: neither {refined} nor chapters/ch*.txt exist.",
        manual_fallback="Run the earlier refine/enrich phases, or place a refined-english.md.",
    )


_PROMPT = """You are an experienced book editor preparing a modern reading edition of a \
classical work. Below is the full refined-English source of a short classical book, \
with every line numbered (`NNNN | text`).

YOUR TASK
Re-segment this source into the chapter structure of a polished professional BOOK, by \
modern nonfiction book-craft — NOT by copying the source's own table of contents, and \
NOT for audio. Decide the chapter count and boundaries yourself.

RULES
1. DROP front-matter from chapter coverage: the title page, the source's own table of \
contents, the translator's note, and any `<!-- PAGE n -->` markers are NOT chapters. \
Real content begins at the book's introduction / the author's reply.
2. Group the material into chapters that each make a satisfying, thematically coherent \
read. For a work of this length modern book-craft typically yields roughly 6-9 chapters \
plus a short preface — but YOU decide what serves the reader; explain each choice.
3. Every instructive line of the source (every teaching, argument, example, named person, \
citation) MUST be covered by exactly one chapter's ranges — no teaching may fall in a gap. \
Ranges are INCLUSIVE 1-based line numbers into the numbered source. A chapter may use \
multiple non-contiguous ranges if book-craft merges scattered material.
4. Add a PREFACE: a short modern orientation (you write its prose later; here decide \
whether to include it, give it a title, and optionally point to the source lines it draws on).
5. Give each chapter a real, evocative modern chapter TITLE (not the source's clause \
headings) and a one-sentence rationale naming the thematic seam.
6. Ground every title in its OWN assigned source ranges. Before finalizing, compare \
each chapter title/rationale against the first and last substantive lines inside that \
chapter's ranges. Do not shift a neighboring theme onto the wrong range. If the range \
is about hunting, slaughter, marriage, sales, inheritance, retaliation, or another \
explicit source heading, the title/rationale must reflect that same material.
7. Never ask the later writer to resolve a title/source conflict. If a proposed title \
does not match the assigned source lines, change either the title or the ranges now.

OUTPUT
Return ONLY a JSON object, no prose around it, in exactly this shape:

{
  "book_title": "<the book's title>",
  "voice": "modern author first-person",
  "preface": { "include": true, "title": "<preface title>", "source_line_ranges": [[a, b]] },
  "chapters": [
    { "bk_index": 1, "title": "<modern chapter title>", "source_line_ranges": [[a, b]],
      "theme": "<2-4 word theme>", "rationale": "<one sentence: the thematic seam>" }
  ]
}

SOURCE (numbered)
{SOURCE}"""


def author_phase_book_design(book_dir: Path, *, log=print, force: bool = False) -> Path:
    book_dir = Path(book_dir).resolve()
    out_dir = book_dir / "book"
    out_path = out_dir / "book-toc.json"
    if out_path.exists() and not force:
        log(f"    0book-design: {out_path.name} exists — skip (use --force to redo)")
        return out_path

    source = _resolve_source(book_dir)
    n_lines = len(source.split("\n"))
    prompt = _PROMPT.replace("{SOURCE}", _numbered(source))
    log(f"    0book-design: {book_dir.name}: {n_lines} source lines -> Opus segmentation")

    rc, stdout, stderr = _run_claude_p_with_retry(
        prompt, timeout=_DESIGN_TIMEOUT, book_dir=book_dir, phase="0book-design", step="segment", log=log
    )
    if rc != 0:
        raise AuthoringError(
            phase="0book-design",
            message=f"claude -p exited rc={rc}.\n{stderr[:400]}",
            manual_fallback="Re-run the phase, or author book-toc.json by hand.",
        )
    try:
        toc = _extract_json(stdout)
    except Exception as e:
        raise AuthoringError(
            phase="0book-design",
            message=f"could not parse book-toc.json from model output: {e}\n{stdout[:800]}",
            manual_fallback="Re-run the phase.",
        ) from e

    chapters = toc.get("chapters") or []
    if not chapters:
        raise AuthoringError(
            phase="0book-design", message="book-toc.json has no chapters[].", manual_fallback="Re-run the phase."
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(toc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    log(
        f"    0book-design: wrote {out_path.name} — {len(chapters)} chapters + "
        f"preface={toc.get('preface', {}).get('include')}"
    )
    return out_path


def main() -> int:
    import sys

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print("usage: python3 -m _authoring._book_design <BOOK_DIR> [--force]", file=__import__("sys").stderr)
        return 2
    try:
        author_phase_book_design(Path(args[0]), force="--force" in sys.argv[1:])
        return 0
    except AuthoringError as e:
        print(f"ERROR [{e.phase}]: {e}", file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
