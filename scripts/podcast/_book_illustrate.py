"""_book_illustrate.py — Phase 0book-illustrate: inject teaching diagrams into book.md.

Reads book/book.md, splits into H2 sections, calls claude -p per section to identify
1-3 philosophical concepts that genuinely benefit from a teaching diagram, generates
Mermaid DSL for each, renders to SVG via render-mermaid.mjs --book-dir, reads the SVG
inline, and produces book/book-illustrated.md with <figure class="book-diagram"> blocks
inserted after the anchor sentences identified by the LLM.

Idempotent: if book-illustrated.md exists, manifest.json is complete, and all SVG files
are present, the LLM + render steps are skipped. Pass force=True to regenerate.

Standalone:
  python3 _book_illustrate.py <BOOK_DIR> [--force]
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _authoring._core import AuthoringError, _run_claude_p  # noqa: E402
from _paths import REPO_ROOT  # noqa: E402

_TIMEOUT = 180  # per section
_DASHBOARD = REPO_ROOT / "plan-dashboard"
_RENDER_SCRIPT = _DASHBOARD / "scripts" / "render-mermaid.mjs"

# Minimum word count for a section to be worth analysing.
_MIN_SECTION_WORDS = 200

_DIAGRAM_TASK_TEMPLATE = """\
Analyse the following passage from a scholarly Islamic philosophy reading edition and output a JSON \
object identifying 0-3 philosophical or metaphysical concepts that warrant a teaching diagram.

OUTPUT REQUIREMENT: Return ONLY valid JSON — no preamble, no explanation, no markdown fences, \
no commentary. The entire response must be parseable by json.loads():
{{"diagrams": [{{"anchor_text": "...", "diagram_type": "...", "mermaid_dsl": "...", "caption": "..."}}]}}
Return {{"diagrams": []}} if no diagram is warranted. Maximum 3 diagrams.

WHEN to propose a diagram — only when ALL of these hold:
1. The concept has internal structure (taxonomy, process, multi-part relationship) that prose must describe sequentially
2. A diagram reveals that structure at a glance in a way prose cannot
3. A reader encountering this section cold would be measurably helped by seeing the structure

DO NOT propose a diagram for:
- Simple binary contrasts already clear in prose
- Narrative passages, hadith/verse quotations, or supplications
- Short illustrative anecdotes without structural content

DIAGRAM TYPES — match the structural shape:
- "flowchart": causal chains, sequential stages, conditional branches
- "mindmap": central concept radiating into attributes, sub-types, or examples
- "graph": bidirectional relationships between concepts of equal weight

MERMAID DSL HARD CONSTRAINTS (violations cause render failure):
- ALL node labels in double quotes: A["Label text"]
- Node IDs: letters + digits + underscores only — no spaces, no hyphens
- Labels: max 6 words, no apostrophes, no parentheses inside quotes
- flowchart: first line must be `flowchart TD` or `flowchart LR`
- mindmap: root uses `root(("Topic"))`, branches indented 2 spaces, NO arrows
- graph: `graph LR` or `graph TD`, `-->` for directional, `---` for undirected

JSON FIELD DEFINITIONS:
- anchor_text: verbatim 20-70 character substring from the passage (must appear EXACTLY in the text below)
- diagram_type: one of "flowchart", "mindmap", "graph"
- mermaid_dsl: complete valid Mermaid DSL string
- caption: one sentence (present tense) explaining what structure the diagram shows

SECTION TITLE: {section_title}

PASSAGE:
{section_text}"""


def _sections_from_md(md: str) -> list[tuple[str, str]]:
    """Split book.md into [(heading, body)] pairs by H2 headings."""
    parts = re.split(r'^(## .+)$', md, flags=re.MULTILINE)
    result: list[tuple[str, str]] = []
    i = 1
    while i < len(parts) - 1:
        heading = parts[i].lstrip('#').strip()
        body = parts[i + 1].strip()
        if body:
            result.append((heading, body))
        i += 2
    return result


def _call_illustrate(section_title: str, section_text: str, *, book_dir: Path) -> list[dict]:
    """Call claude -p with the illustration prompt. Returns validated diagram specs."""
    text = section_text[:6000] if len(section_text) > 6000 else section_text
    prompt = _DIAGRAM_TASK_TEMPLATE.format(
        section_title=section_title,
        section_text=text,
    )

    rc, stdout, stderr = _run_claude_p(
        prompt,
        book_dir=book_dir,
        phase="0book-illustrate",
        step=section_title[:40],
        timeout=_TIMEOUT,
    )
    if rc != 0:
        sys.stderr.write(f"  [illustrate] claude -p rc={rc}: {stderr[:200]}\n")
        return []

    raw = re.sub(r'^```(?:json)?\s*\n?', '', stdout.strip())
    raw = re.sub(r'\n?```\s*$', '', raw)

    try:
        data = json.loads(raw)
        diagrams = data.get("diagrams", [])
    except (json.JSONDecodeError, AttributeError):
        sys.stderr.write(f"  [illustrate] JSON parse failed for {section_title!r}: {raw[:200]}\n")
        return []

    valid: list[dict] = []
    for d in diagrams:
        if not all(k in d for k in ("anchor_text", "diagram_type", "mermaid_dsl", "caption")):
            continue
        if d["diagram_type"] not in ("flowchart", "mindmap", "graph"):
            continue
        valid.append(d)
    return valid[:3]


def _render_diagrams(book_dir: Path, *, log=print) -> None:
    """Render all .mmd files in book/_diagrams/ to .svg via render-mermaid.mjs --book-dir."""
    diagram_dir = book_dir / "book" / "_diagrams"
    if not diagram_dir.exists() or not list(diagram_dir.glob("*.mmd")):
        return
    if not _RENDER_SCRIPT.exists():
        raise AuthoringError(
            phase="0book-illustrate",
            message=f"render-mermaid.mjs not found at {_RENDER_SCRIPT}",
            manual_fallback="Ensure plan-dashboard/scripts/ is present.")

    log(f"    0book-illustrate: rendering Mermaid diagrams via Playwright")
    proc = subprocess.run(
        ["node", str(_RENDER_SCRIPT), f"--book-dir={book_dir}"],
        cwd=str(_DASHBOARD),
        capture_output=True,
        text=True,
        timeout=300,
    )
    if proc.returncode == 3:
        log("    0book-illustrate: chromium unavailable — diagrams will be absent from PDF")
        log("      Install with: npx playwright install chromium  (in plan-dashboard/)")
    elif proc.returncode != 0:
        raise AuthoringError(
            phase="0book-illustrate",
            message=f"render-mermaid.mjs failed rc={proc.returncode}.\n{proc.stderr[:400]}",
            manual_fallback="Run `npx playwright install chromium` in plan-dashboard/ then retry.")
    else:
        for line in proc.stdout.strip().splitlines():
            log(f"    {line}")


def _inject_figures(book_md: str, manifest: list[dict]) -> str:
    """Insert <figure class="book-diagram"> blocks after anchor paragraphs in book_md."""
    result = book_md
    insertions: list[tuple[int, str]] = []

    for entry in manifest:
        anchor = entry.get("anchor_text", "").strip()
        svg_path_str = entry.get("svg_path", "")
        caption = entry.get("caption", "")

        if not anchor or not svg_path_str:
            continue

        svg_file = Path(svg_path_str)
        if not svg_file.exists():
            sys.stderr.write(f"  [illustrate] SVG missing: {svg_path_str}, skipping\n")
            continue

        svg_content = svg_file.read_text(encoding="utf-8").strip()
        pos = result.find(anchor)
        if pos == -1:
            sys.stderr.write(f"  [illustrate] anchor not found: {repr(anchor[:60])}, skipping\n")
            continue

        # Insert after the paragraph containing the anchor (next blank line boundary)
        end_of_para = result.find('\n\n', pos + len(anchor))
        insert_at = (end_of_para + 2) if end_of_para != -1 else len(result)

        figure_block = (
            f'<figure class="book-diagram">\n'
            f'{svg_content}\n'
            f'<figcaption>{caption}</figcaption>\n'
            f'</figure>\n\n'
        )
        insertions.append((insert_at, figure_block))

    # Apply in reverse order so earlier insertions don't shift later offsets
    insertions.sort(key=lambda x: x[0], reverse=True)
    for pos, block in insertions:
        result = result[:pos] + block + result[pos:]

    return result


def author_phase_book_illustrate(book_dir: Path, *, log=print, force: bool = False) -> Path:
    """Main entry point for 0book-illustrate. Returns path to book/book-illustrated.md."""
    book_dir = Path(book_dir).resolve()
    book_md_path = book_dir / "book" / "book.md"
    illustrated_path = book_dir / "book" / "book-illustrated.md"
    diagram_dir = book_dir / "book" / "_diagrams"
    manifest_path = diagram_dir / "manifest.json"

    if not book_md_path.exists():
        raise AuthoringError(
            phase="0book-illustrate",
            message=f"book.md not found at {book_md_path} — run 0book-compose first.",
            manual_fallback="python3 _book_compose.py <BOOK_DIR>")

    # Idempotency: skip if all outputs are present and not forcing
    if not force and illustrated_path.exists() and manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if all((diagram_dir / Path(e["svg_path"]).name).exists()
                   for e in manifest if e.get("svg_path")):
                log(f"    0book-illustrate: {book_dir.name}: "
                    f"already complete ({len(manifest)} diagrams) — skipping")
                return illustrated_path
        except Exception:
            pass  # fall through to re-run

    diagram_dir.mkdir(parents=True, exist_ok=True)

    book_md = book_md_path.read_text(encoding="utf-8")
    sections = _sections_from_md(book_md)
    log(f"    0book-illustrate: {book_dir.name}: "
        f"analysing {len(sections)} sections for diagram opportunities")

    manifest: list[dict] = []

    for heading, body in sections:
        word_count = len(body.split())
        if word_count < _MIN_SECTION_WORDS:
            log(f"    0book-illustrate: skip short section ({word_count}w): {heading[:50]!r}")
            continue

        log(f"    0book-illustrate: {heading[:60]!r} — requesting diagram spec")
        specs = _call_illustrate(heading, body, book_dir=book_dir)

        if not specs:
            log(f"    0book-illustrate: {heading[:60]!r} — no diagrams warranted")
            continue

        log(f"    0book-illustrate: {heading[:60]!r} — {len(specs)} diagram(s) identified")
        section_slug = re.sub(r'[^a-z0-9]+', '-', heading.lower())[:40].strip('-')

        for i, spec in enumerate(specs, 1):
            diagram_id = f"{section_slug}-{i}"
            mmd_path = diagram_dir / f"{diagram_id}.mmd"
            svg_path = diagram_dir / f"{diagram_id}.svg"
            mmd_path.write_text(spec["mermaid_dsl"], encoding="utf-8")

            manifest.append({
                "diagram_id": diagram_id,
                "section": heading,
                "anchor_text": spec["anchor_text"],
                "diagram_type": spec["diagram_type"],
                "caption": spec["caption"],
                "mmd_path": str(mmd_path),
                "svg_path": str(svg_path),
            })

    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"    0book-illustrate: manifest written — {len(manifest)} total diagram(s)")

    _render_diagrams(book_dir, log=log)

    log(f"    0book-illustrate: assembling book-illustrated.md")
    illustrated_md = _inject_figures(book_md, manifest)
    illustrated_path.write_text(illustrated_md, encoding="utf-8")
    log(f"    0book-illustrate: wrote {illustrated_path.name} "
        f"({illustrated_path.stat().st_size // 1024} KB)")

    return illustrated_path


def main() -> int:
    args = sys.argv[1:]
    force = "--force" in args
    paths = [a for a in args if not a.startswith("--")]
    if not paths:
        print("usage: _book_illustrate.py <BOOK_DIR> [--force]", file=sys.stderr)
        return 2
    try:
        out = author_phase_book_illustrate(Path(paths[0]), force=force)
        print(f"done: {out}")
        return 0
    except AuthoringError as e:
        print(f"ERROR [{e.phase}]: {e}\n  → {e.manual_fallback}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
