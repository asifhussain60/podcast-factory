"""_spike_book_design.py — STAGE 1 SPIKE (throwaway; do not productionize as-is).

Re-segments a book's refined-english.md into a polished modern BOOK by book-craft
best practices: its OWN chapter count / boundaries / titles + a preface, INDEPENDENT
of the podcast episode cuts. Emits book/book-toc.json.

One Opus pass via `claude -p` (flat-rate Max). No phase registration, no driver.

Usage:
  python3 scripts/podcast/_spike_book_design.py content/Islamic/ayyuhal-walad/
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

_PODCAST = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_PODCAST))

from _authoring._core import _run_claude_p  # noqa: E402


def _numbered(text: str) -> str:
    return "\n".join(f"{i:>4} | {ln}" for i, ln in enumerate(text.split("\n"), 1))


def _extract_json(stdout: str) -> dict:
    s = stdout.strip()
    # strip ```json ... ``` fences if present
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", s, re.S)
    if m:
        s = m.group(1)
    else:
        # else take the outermost {...}
        i, j = s.find("{"), s.rfind("}")
        if i != -1 and j != -1:
            s = s[i : j + 1]
    return json.loads(s)


_PROMPT = """You are an experienced book editor preparing a modern reading edition of a \
classical work. Below is the full refined-English source of a short classical book, \
with every line numbered (`NNNN | text`).

YOUR TASK
Re-segment this source into the chapter structure of a polished professional BOOK, by \
modern nonfiction book-craft — NOT by copying the source's own table of contents, and \
NOT for audio. Decide the chapter count and boundaries yourself.

RULES
1. DROP front-matter from chapter coverage: the title page, the source's own table of \
contents, the translator's note, and the `<!-- PAGE n -->` markers are NOT chapters. \
Real content begins at the book's introduction / the author's reply.
2. Group the material into chapters that each make a satisfying, thematically coherent \
read. For a work of this length (~15,000 words) modern book-craft typically yields \
roughly 6-9 chapters plus a short preface — but YOU decide what serves the reader; \
explain each choice.
3. Every instructive line of the source (every teaching, argument, example, named \
person, citation) MUST be covered by exactly one chapter's ranges — no teaching may \
fall in a gap. Ranges are INCLUSIVE 1-based line numbers into the numbered source. A \
chapter may use multiple non-contiguous ranges if book-craft merges scattered material.
4. Add a PREFACE: a short modern orientation for the reader (you will write its prose \
later; here just decide whether to include it, give it a title, and optionally point to \
the source lines — e.g. the introduction — it draws on).
5. Give each chapter a real, evocative modern chapter TITLE (not the source's clause \
headings) and a one-sentence rationale naming the thematic seam.

OUTPUT
Return ONLY a JSON object, no prose around it, in exactly this shape:

{
  "book_title": "<the book's title>",
  "voice": "modern author first-person",
  "preface": { "include": true, "title": "<preface title>", "source_line_ranges": [[a, b]] },
  "chapters": [
    {
      "bk_index": 1,
      "title": "<modern chapter title>",
      "source_line_ranges": [[a, b]],
      "theme": "<2-4 word theme>",
      "rationale": "<one sentence: the thematic seam this chapter captures>"
    }
  ]
}

SOURCE (numbered)
{SOURCE}"""


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: _spike_book_design.py <BOOK_DIR>", file=sys.stderr)
        return 2
    book_dir = pathlib.Path(sys.argv[1]).resolve()
    refined = book_dir / "_system" / "source" / "text" / "refined-english.md"
    if not refined.exists():
        print(f"ERROR: no refined-english.md at {refined}", file=sys.stderr)
        return 1

    source = refined.read_text(encoding="utf-8")
    n_lines = len(source.split("\n"))
    prompt = _PROMPT.replace("{SOURCE}", _numbered(source))

    print(f"[spike-design] {book_dir.name}: {n_lines} source lines → Opus segmentation…")
    rc, stdout, stderr = _run_claude_p(prompt, timeout=600, book_dir=book_dir,
                                       phase="0book-design(spike)", step="segment")
    if rc != 0:
        print(f"ERROR: claude -p rc={rc}\n{stderr}", file=sys.stderr)
        print(f"--- stdout ---\n{stdout[:2000]}", file=sys.stderr)
        return 1

    try:
        toc = _extract_json(stdout)
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: could not parse JSON: {e}", file=sys.stderr)
        print(f"--- raw stdout ---\n{stdout[:4000]}", file=sys.stderr)
        return 1

    out_dir = book_dir / "book"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "book-toc.json"
    out_path.write_text(json.dumps(toc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    chapters = toc.get("chapters", [])
    print(f"[spike-design] wrote {out_path.relative_to(book_dir.parent.parent.parent)}")
    print(f"[spike-design] book: {toc.get('book_title')!r} · {len(chapters)} chapters + "
          f"preface={toc.get('preface', {}).get('include')}")
    for ch in chapters:
        rngs = ch.get("source_line_ranges", [])
        span = sum((b - a + 1) for a, b in rngs) if rngs else 0
        print(f"   {ch.get('bk_index'):>2}. {ch.get('title')}  ({span} src lines) — {ch.get('theme')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
