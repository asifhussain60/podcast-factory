"""_book_illustrate.py — Phase 0book-illustrate: OFFER teaching diagrams for the book.

It never places a figure, never writes a second copy of the book, and is off by
default; every route returns book.md. Rule stated once in _book_visual_policy.py.

Two-stage, content-profile-aware SVG generation:

  Stage 1 — Structural classification (one LLM call per section)
    Identifies 0-3 concepts in the section and classifies each into a structure
    type from a content-profile-specific vocabulary.  Returns structured JSON with
    the type name and typed parameters.

  Stage 2 — Generation (no additional LLM call)
    Mermaid-routed types  (mermaid-flowchart, mermaid-mindmap, mermaid-graph):
      Write a .mmd file; render to SVG via render-mermaid.mjs (Playwright).
    SVG-pattern types  (concentric-layers, cosmic-pair, quadrant-map,
                        hierarchy-tree, cascade-chain):
      Call _svg_patterns.render_pattern() directly — pure Python, no Playwright.

Islamic-scholarly vocabulary includes all five SVG pattern types because
Mermaid's grammar cannot express concentric cosmological layers, cosmic-pair
polarity columns, 2×2 quadrant maps, 4-tier ranked hierarchies, or transmission
cascade chains with the visual fidelity these structures deserve.

Idempotent: if manifest.json is complete and all its SVG files are present, the
LLM + render steps are skipped.  Pass force=True to regenerate.

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
from _authoring._core import AuthoringError, _run_claude_p, pure_json_call_options
from _illustrate_resume import failed_entry, resume_state
from _paths import REPO_ROOT

# Per-section classifier budget. 180s proved too tight under real Opus
# latency (2026-06-11: every section timed out and was skipped, yielding a
# diagram-less book) — same failure class as the compose 420s/300s budgets.
_TIMEOUT = 600  # per section
_DASHBOARD = REPO_ROOT / "plan-dashboard"
_RENDER_SCRIPT = _DASHBOARD / "scripts" / "render-mermaid.mjs"
# Minimum word count for a section to be worth analysing.
_MIN_SECTION_WORDS = 200

# ---------------------------------------------------------------------------
# Classification templates — one per content_profile family.
# Each template asks for BOTH the structure type AND its parameters in one call.
# For mermaid-* types the parameters include the full DSL so no second call
# is required.  For SVG-pattern types the parameters are the typed data for
# _svg_patterns.render_pattern().
# ---------------------------------------------------------------------------

_CLASSIFY_HEADER = """\
Analyse the passage below and identify 0-3 structural concepts that genuinely \
benefit from a teaching diagram.  Return ONLY valid JSON, no preamble, no fences:
{{"concepts": [{{"structure_type": "...", "anchor_text": "...", "caption": "...", \
"parameters": {{...}}}}]}}
Return {{"concepts": []}} if nothing warrants a diagram.  Maximum 3 diagrams.

WHEN to propose a diagram — ALL must hold:
1. The concept has internal structure (ranked tiers, nested levels, sequential \
stages, 2-axis states) that prose must describe word-by-word.
2. A diagram reveals that structure simultaneously, in a way prose cannot.
3. A reader encountering this section cold would be measurably helped.

DO NOT propose a diagram for:
- Simple binary contrasts already clear in a single sentence
- Narrative passages, hadith/verse quotations, or supplications
- Short anecdotes without structural content
- Any concept that one sentence describes completely

JSON FIELD DEFINITIONS (apply to all types):
- structure_type: one of the types listed below
- anchor_text: verbatim 20-70 character substring that appears EXACTLY in the passage
- caption: one sentence (present tense) explaining what the diagram shows
- parameters: type-specific object (see schemas below)

"""

_CLASSIFY_TEMPLATE_ISLAMIC = (
    _CLASSIFY_HEADER
    + """\
STRUCTURE TYPES FOR ISLAMIC PHILOSOPHICAL CONTENT:

1. "concentric-layers"
   Use when: the text describes nested degrees of the SAME reality (outer form / inner \
meaning / secret of secrets, or any "the outer of X contains an inner which contains \
an innermost").
   Islamic examples: Zahir/Batin/Batin al-Batin; Shell/White/Yolk (egg metaphor).
   Parameters schema:
     {{"title": "<diagram title>",
       "layers": [{{"label": "<ring label>", "description": "<optional brief note>"}}]}}
   layers list runs from OUTERMOST to INNERMOST (most esoteric last).

2. "cosmic-pair"
   Use when: the text pairs two phenomena repeatedly as higher/lower, manifest/hidden, \
active/passive — and gives MULTIPLE examples of the same pairing principle.
   Islamic examples: Sun/Moon, Sky/Earth, Salty/Fresh — all expressing Zahir/Batin.
   Convention: left column = higher rank / manifest; right column = lower rank / hidden.
   Parameters schema:
     {{"title": "<diagram title>",
       "left_label": "<header for higher-rank column>",
       "right_label": "<header for lower-rank column>",
       "rows": [{{"left": "<item>", "right": "<item>"}}],
       "principle": "<optional: the unifying principle in one phrase>"}}

3. "hierarchy-tree"
   Use when: the text describes a chain of RANKED authority or proximity to the source \
with 2 or more tiers below the apex.
   Islamic examples: Natiq → Wasi/Imam → Hujja (×12) → Duʿāt.
   Parameters schema:
     {{"title": "<diagram title>",
       "root": "<apex node label>",
       "levels": [["<tier-1 node>", ...], ["<tier-2 node>", ...]]}}
   levels[0] is the tier immediately below root; levels[-1] is the lowest tier.
   For large tiers use concise labels like "Hujja × 12".

4. "cascade-chain"
   Use when: the text describes HOW something (knowledge, authority, divine speech) \
passes from origin to receiver through intermediaries, each stage TRANSFORMING or \
adapting the substance.
   Islamic examples: Creator's pure speech → Imam transforms into body-and-form → \
Bab condenses → Duʿāt distributes.
   Parameters schema:
     {{"title": "<diagram title>",
       "nodes": [{{"role": "<transformation label>", "label": "<entity name>"}}]}}
   role is what this stage DOES (e.g. "Transforms into Form", "Condenses").
   First node role can be "Source" or "Origin".

5. "quadrant-map"
   Use when: the text describes FOUR distinct states produced by two independent \
binary qualities.
   Islamic examples: Outer knowledge (yes/no) × Inner knowledge (yes/no) → \
Mu'min / Fasiq / Beast / Dead.
   Parameters schema:
     {{"title": "<diagram title>",
       "x_axis": {{"label": "<axis name>", "pos_label": "<right col label>", \
"neg_label": "<left col label>"}},
       "y_axis": {{"label": "<axis name>", "pos_label": "<top row label>", \
"neg_label": "<bottom row label>"}},
       "quadrants": [
         {{"label": "<top-left state>",    "note": "<optional>", "impossible": false}},
         {{"label": "<top-right state>",   "note": "<optional>", "impossible": false}},
         {{"label": "<bottom-left state>", "note": "<optional>", "impossible": false}},
         {{"label": "<bottom-right state>","note": "<optional>", "impossible": false}}
       ]}}
   Set "impossible": true for any quadrant the source says cannot exist.
   The top-right quadrant (pos x + pos y) is rendered as the ideal/synthesis state.

--- Simpler structures handled by Mermaid ---

6. "mermaid-flowchart"
   Use when: 3-6 sequential or causal stages, each causing the next.
   Parameters: {{"mermaid_dsl": "flowchart TD\\nA[\\"Step\\"] --> B[\\"Step\\"]"}}

7. "mermaid-mindmap"
   Use when: one central concept radiates into sub-types or attributes (NO ranked order).
   Parameters: {{"mermaid_dsl": "mindmap\\n  root((\\"Topic\\"))\\n    Branch1\\n    Branch2"}}
   The root sits at 2-space indent; EVERY branch is indented DEEPER (4 spaces) so it \
nests UNDER the root.  Branches at the SAME indent as the root parse as separate roots \
and Mermaid rejects the diagram with a "multiple roots" error.

8. "mermaid-graph"
   Use when: bidirectional relationships between 3-5 concepts of roughly equal weight.
   Parameters: {{"mermaid_dsl": "graph LR\\nA[\\"Concept\\"] --- B[\\"Concept\\"]"}}

MERMAID DSL HARD CONSTRAINTS (violations cause render failure):
- ALL node labels in double quotes: A["Label text"]
- Node IDs: letters + digits + underscores only (no spaces, no hyphens)
- Labels: max 6 words, no apostrophes or parentheses inside quotes
- flowchart: first line MUST be `flowchart TD` or `flowchart LR`
- mindmap: root uses `root(("Topic"))` at 2-space indent; branches indented DEEPER \
(4 spaces) so they nest under root — branches at the same indent as root cause a \
"multiple roots" render failure; NO arrows
- graph: `graph LR` or `graph TD`; `-->` directional; `---` undirected

SECTION TITLE: {section_title}

PASSAGE:
{section_text}"""
)


_CLASSIFY_TEMPLATE_TECHNICAL = (
    _CLASSIFY_HEADER
    + """\
STRUCTURE TYPES FOR TECHNICAL CONTENT:

1. "hierarchy-tree" — system component hierarchies, module dependency trees.
   Parameters: {{"title": str, "root": str, "levels": [[str, ...], ...]}}

2. "cascade-chain" — data pipelines, request/response flows, build stages.
   Parameters: {{"title": str, "nodes": [{{"role": str, "label": str}}]}}

3. "mermaid-flowchart" — decision trees, conditional logic, sequential processes.
   Parameters: {{"mermaid_dsl": "flowchart TD\\n..."}}

4. "mermaid-graph" — dependency graphs, bidirectional component relationships.
   Parameters: {{"mermaid_dsl": "graph LR\\n..."}}

5. "mermaid-mindmap" — feature decompositions, option spaces.
   Parameters: {{"mermaid_dsl": "mindmap\\n  root((\\"Topic\\"))\\n    Branch1\\n    Branch2"}}
   Root at 2-space indent; EVERY branch indented DEEPER (4 spaces) so it nests under root.

MERMAID DSL HARD CONSTRAINTS:
- ALL node labels in double quotes: A["Label text"]
- Node IDs: letters + digits + underscores only
- Labels: max 6 words, no apostrophes or parentheses inside quotes
- flowchart: first line MUST be `flowchart TD` or `flowchart LR`
- mindmap: root uses `root(("Topic"))` at 2-space indent; branches indented DEEPER \
(4 spaces) so they nest under root — branches at the same indent as root cause a \
"multiple roots" render failure; NO arrows

SECTION TITLE: {section_title}

PASSAGE:
{section_text}"""
)


_CLASSIFY_TEMPLATE_DEFAULT = (
    _CLASSIFY_HEADER
    + """\
STRUCTURE TYPES:

1. "mermaid-flowchart" — sequential/causal stages (3-6 steps).
   Parameters: {{"mermaid_dsl": "flowchart TD\\n..."}}

2. "mermaid-mindmap" — one central concept with radiating attributes.
   Parameters: {{"mermaid_dsl": "mindmap\\n  root((\\"Topic\\"))\\n    Branch1\\n    Branch2"}}
   Root at 2-space indent; EVERY branch indented DEEPER (4 spaces) so it nests under root.

3. "mermaid-graph" — bidirectional relationships (3-5 concepts).
   Parameters: {{"mermaid_dsl": "graph LR\\n..."}}

4. "hierarchy-tree" — ranked tiers descending in authority.
   Parameters: {{"title": str, "root": str, "levels": [[str, ...], ...]}}

5. "cascade-chain" — sequential transmission stages.
   Parameters: {{"title": str, "nodes": [{{"role": str, "label": str}}]}}

MERMAID DSL HARD CONSTRAINTS:
- ALL node labels in double quotes: A["Label text"]
- Node IDs: letters + digits + underscores only
- Labels: max 6 words, no apostrophes or parentheses inside quotes
- flowchart: first line MUST be `flowchart TD` or `flowchart LR`
- mindmap: root uses `root(("Topic"))` at 2-space indent; branches indented DEEPER \
(4 spaces) so they nest under root — branches at the same indent as root cause a \
"multiple roots" render failure; NO arrows

SECTION TITLE: {section_title}

PASSAGE:
{section_text}"""
)

_SVG_PATTERN_TYPES = frozenset(
    {
        "concentric-layers",
        "cosmic-pair",
        "quadrant-map",
        "hierarchy-tree",
        "cascade-chain",
    }
)
_MERMAID_TYPES = frozenset({"mermaid-flowchart", "mermaid-mindmap", "mermaid-graph"})
_ALL_TYPES = _SVG_PATTERN_TYPES | _MERMAID_TYPES


def _sections_from_md(md: str) -> list[tuple[str, str]]:
    """Split book.md into [(heading, body)] pairs by H2 headings."""
    parts = re.split(r"^(## .+)$", md, flags=re.MULTILINE)
    result: list[tuple[str, str]] = []
    i = 1
    while i < len(parts) - 1:
        heading = parts[i].lstrip("#").strip()
        body = parts[i + 1].strip()
        if body:
            result.append((heading, body))
        i += 2
    return result


def _select_classify_template(content_profile: str) -> str:
    """Return the right classification template for a given content profile."""
    if content_profile == "islamic_scholarly":
        return _CLASSIFY_TEMPLATE_ISLAMIC
    if content_profile == "technical":
        return _CLASSIFY_TEMPLATE_TECHNICAL
    return _CLASSIFY_TEMPLATE_DEFAULT


def _classify_section(
    section_title: str, section_text: str, content_profile: str, *, book_dir: Path, model_flag: str | None = None
) -> list[dict]:
    """Stage-1 classification.  Returns validated concept specs (max 3) for the section."""
    template = _select_classify_template(content_profile)
    text = section_text[:6000] if len(section_text) > 6000 else section_text
    prompt = template.format(section_title=section_title, section_text=text)

    rc, stdout, stderr = _run_claude_p(
        prompt,
        book_dir=book_dir,
        phase="0book-illustrate",
        step=section_title[:40],
        timeout=_TIMEOUT,
        model_flag=model_flag,
        **pure_json_call_options(),
    )
    if rc != 0:
        sys.stderr.write(f"  [illustrate] claude -p rc={rc}: {stderr[:200]}\n")
        return []

    raw = re.sub(r"^```(?:json)?\s*\n?", "", stdout.strip())
    raw = re.sub(r"\n?```\s*$", "", raw)

    try:
        data = json.loads(raw)
        concepts = data.get("concepts", [])
    except (json.JSONDecodeError, AttributeError):
        sys.stderr.write(f"  [illustrate] JSON parse failed for {section_title!r}: {raw[:200]}\n")
        return []

    return _validate_concepts(concepts)


def _validate_concepts(raw_concepts: list) -> list[dict]:
    """Validate structure type, required fields, and parameter schema of raw concepts."""
    valid: list[dict] = []
    for c in raw_concepts:
        if not isinstance(c, dict):
            continue
        stype = c.get("structure_type", "")
        if stype not in _ALL_TYPES:
            continue
        if not c.get("anchor_text") or not c.get("caption"):
            continue
        params = c.get("parameters", {})
        if not isinstance(params, dict):
            continue

        if stype in _MERMAID_TYPES:
            dsl = params.get("mermaid_dsl", "")
            if not isinstance(dsl, str) or not dsl.strip():
                continue  # no DSL → skip
        else:
            # SVG pattern types require at least a 'title' in parameters
            if not params.get("title"):
                continue

        valid.append(c)
    return valid[:3]  # hard cap at 3 per section


def _generate_pattern_svg_file(
    spec: dict, diagram_id: str, diagram_dir: Path, book_dir: Path | None = None
) -> str | None:
    """Stage-2 generation for SVG-pattern types.

    Calls _svg_patterns.render_pattern() and writes the SVG file directly.
    Returns the svg_path string, or None on failure.
    """
    from _svg_patterns import render_pattern  # local import: avoids circular deps

    stype = spec["structure_type"]
    params = dict(spec.get("parameters", {}))

    # Ensure a title exists (fall back to a cleaned diagram_id)
    if not params.get("title"):
        params["title"] = diagram_id.replace("-", " ").title()

    svg_str = render_pattern(stype, params)
    if not svg_str:
        sys.stderr.write(f"  [illustrate] render_pattern returned None for {diagram_id} ({stype})\n")
        return None

    if book_dir is not None:
        try:
            from _translation_edition import monochrome_svg, requires_monochrome_visuals

            if requires_monochrome_visuals(book_dir):
                svg_str = monochrome_svg(svg_str)
        except Exception:
            pass

    # Geometry gate (2026-06-11): auto-expand the viewBox over escaping text;
    # surface any remaining overlap/min-type findings in the phase log.
    from _svg_geometry import gate_svg

    svg_str = gate_svg(svg_str, diagram_id, log=lambda m: sys.stderr.write(f"  {m.strip()}\n"))

    svg_path = diagram_dir / f"{diagram_id}.svg"
    try:
        svg_path.write_text(svg_str, encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(f"  [illustrate] write failed for {svg_path}: {exc}\n")
        return None
    return str(svg_path)


def _normalize_mindmap_dsl(dsl: str) -> str:
    """Guarantee a single-root Mermaid mindmap regardless of LLM indentation.

    Mermaid mindmaps express hierarchy purely through indentation: the first
    node is the root and every other node must be indented DEEPER than it.  If
    the model emits branches at the SAME (or shallower) indent as the root, each
    top-level item is parsed as its own root and the render fails with a
    "multiple roots" error.  This normalizer re-indents any such branch to nest
    under the root while preserving the relative nesting among branches.

    Non-mindmap DSL (flowchart/graph) is returned unchanged.
    """
    lines = dsl.splitlines()
    # Locate the `mindmap` declaration line.
    decl_idx = next((i for i, ln in enumerate(lines) if ln.strip().lower() == "mindmap"), None)
    if decl_idx is None:
        return dsl  # not a mindmap — leave untouched

    def indent_of(ln: str) -> int:
        return len(ln) - len(ln.lstrip(" "))

    # First non-blank line after the declaration is the root node.
    root_idx = next((i for i in range(decl_idx + 1, len(lines)) if lines[i].strip()), None)
    if root_idx is None:
        return dsl  # nothing but a declaration

    root_indent = indent_of(lines[root_idx])

    # Branch lines = every non-blank line after the root.
    branch_idxs = [i for i in range(root_idx + 1, len(lines)) if lines[i].strip()]
    if not branch_idxs:
        return dsl  # root only — nothing to nest

    min_branch_indent = min(indent_of(lines[i]) for i in branch_idxs)
    if min_branch_indent > root_indent:
        return dsl  # already correctly nested

    # Shift every branch deeper so the shallowest branch sits one level (2 spaces)
    # below the root; relative indentation among branches is preserved.
    shift = (root_indent + 2) - min_branch_indent
    for i in branch_idxs:
        lines[i] = (" " * (indent_of(lines[i]) + shift)) + lines[i].lstrip(" ")
    return "\n".join(lines)


def _render_diagrams(book_dir: Path, *, log=print) -> None:
    """Render all .mmd files in book/_diagrams/ to .svg via render-mermaid.mjs --book-dir."""
    diagram_dir = book_dir / "book" / "_diagrams"
    if not diagram_dir.exists() or not list(diagram_dir.glob("*.mmd")):
        return
    if not _RENDER_SCRIPT.exists():
        raise AuthoringError(
            phase="0book-illustrate",
            message=f"render-mermaid.mjs not found at {_RENDER_SCRIPT}",
            manual_fallback="Ensure plan-dashboard/scripts/ is present.",
        )

    log("    0book-illustrate: rendering Mermaid diagrams via Playwright")
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
            manual_fallback="Run `npx playwright install chromium` in plan-dashboard/ then retry.",
        )
    else:
        for line in proc.stdout.strip().splitlines():
            log(f"    {line}")
        # Geometry gate over the freshly rendered .svg files (same contract
        # as the pattern path: auto-expand G1, surface the rest in the log).
        from _svg_geometry import gate_svg

        for mmd in sorted(diagram_dir.glob("*.mmd")):
            svgf = mmd.with_suffix(".svg")
            if not svgf.exists():
                continue
            src = svgf.read_text(encoding="utf-8")
            fixed = gate_svg(src, svgf.name, log=log)
            try:
                from _translation_edition import monochrome_svg, requires_monochrome_visuals

                if requires_monochrome_visuals(book_dir):
                    fixed = monochrome_svg(fixed)
            except Exception:
                pass
            if fixed != src:
                svgf.write_text(fixed, encoding="utf-8")


def author_phase_book_illustrate(
    book_dir: Path, *, log=print, force: bool = False, model_flag: str | None = None
) -> Path:
    """Main entry point for 0book-illustrate. ALWAYS returns book/book.md.

    model_flag overrides the default model (Opus) for the diagram-classification
    LLM call — a mechanical structure-triage task, not translation-fidelity-
    critical, so callers may safely pass a lighter model (e.g. translation-edition
    passes Sonnet). None preserves the prior default for all other callers.
    """
    book_dir = Path(book_dir).resolve()
    book_md_path = book_dir / "book" / "book.md"
    diagram_dir = book_dir / "book" / "_diagrams"
    manifest_path = diagram_dir / "manifest.json"

    if not book_md_path.exists():
        raise AuthoringError(
            phase="0book-illustrate",
            message=f"book.md not found at {book_md_path} — run 0book-compose first.",
            manual_fallback="python3 scripts/podcast/orchestrate_book.py --resume <slug>",
        )

    # Resolve content_profile once: used for both the fiction gate and template selection.
    from _content_profile import resolve_content_profile  # local import: avoid circularity

    content_profile = resolve_content_profile(book_dir)

    # Fiction passthrough: novels use scenic raster illustrations (separate path),
    # not teaching diagrams.
    if content_profile == "fiction":
        log(
            f"    0book-illustrate: {book_dir.name}: content_profile='fiction' — "
            f"skipping teaching-diagram injection (novels use scenic illustration)"
        )
        diagram_dir.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text("[]\n", encoding="utf-8")
        return book_md_path

    # book_augmentation=none passthrough: a diagram is model-added interpretive
    # content (it does not exist in the source text), which is augmentation by
    # definition — so it is forbidden for the same books that forbid textual
    # augmentation. This is the ONLY gate on illustration; every caller
    # (phases/book_driver.py and any direct invocation) inherits it
    # automatically via the `book_augmentation` knob, which resolves to "none"
    # for deliverable_mode == translation_edition.
    from _pipeline_flags import BOOK_AUGMENTATION_NONE, book_augmentation

    if book_augmentation(book_dir) == BOOK_AUGMENTATION_NONE:
        log(
            f"    0book-illustrate: {book_dir.name}: book_augmentation='none' — "
            f"skipping diagram generation (faithful/translation edition forbids "
            f"added visual content)"
        )
        diagram_dir.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text("[]\n", encoding="utf-8")
        return book_md_path

    # Idempotency: keyed on the manifest + its SVGs, the real outputs. Keying it
    # on book-illustrated.md (no longer written) would re-pay for every diagram.
    done: list[dict] = []  # drawn by an earlier run and still on disk: carried, never re-bought
    if not force and manifest_path.exists():
        done, complete = resume_state(manifest_path, diagram_dir)
        if complete:
            log(f"    0book-illustrate: {book_dir.name}: already complete ({len(done)} diagrams) — skipping")
            return book_md_path

    diagram_dir.mkdir(parents=True, exist_ok=True)

    book_md = book_md_path.read_text(encoding="utf-8")
    sections = _sections_from_md(book_md)
    log(
        f"    0book-illustrate: {book_dir.name}: profile={content_profile!r} — "
        f"analysing {len(sections)} sections for diagram opportunities"
    )

    manifest, kept = list(done), {e.get("section") for e in done}

    for heading, body in sections:
        word_count = len(body.split())
        if word_count < _MIN_SECTION_WORDS:
            log(f"    0book-illustrate: skip short section ({word_count}w): {heading[:50]!r}")
            continue
        if heading in kept:
            continue  # its diagram is on disk from an earlier run; only what is missing is asked for

        try:
            log(f"    0book-illustrate: {heading[:60]!r} — classifying structure")
            specs = _classify_section(heading, body, content_profile, book_dir=book_dir, model_flag=model_flag)

            if not specs:
                log(f"    0book-illustrate: {heading[:60]!r} — no diagrams warranted")
                continue

            log(
                f"    0book-illustrate: {heading[:60]!r} — "
                f"{len(specs)} diagram(s): " + ", ".join(s["structure_type"] for s in specs)
            )
            section_slug = re.sub(r"[^a-z0-9]+", "-", heading.lower())[:40].strip("-")

            for i, spec in enumerate(specs, 1):
                stype = spec["structure_type"]
                diagram_id = f"{section_slug}-{i}"

                if stype in _MERMAID_TYPES:
                    # ── Mermaid path ──
                    # DSL is in parameters.mermaid_dsl; render-mermaid.mjs converts
                    # .mmd → .svg in _render_diagrams() below.
                    mmd_dsl = spec["parameters"].get("mermaid_dsl", "")
                    if not isinstance(mmd_dsl, str) or not mmd_dsl.strip():
                        sys.stderr.write(f"  [illustrate] empty mermaid_dsl for {diagram_id}, skipping\n")
                        continue
                    # Guard the mindmap DSL: re-nest any stray top-level branch
                    # under the root so a render-breaking "multiple roots" output
                    # can't slip through (no-op for flowchart/graph DSL).
                    if stype == "mermaid-mindmap":
                        mmd_dsl = _normalize_mindmap_dsl(mmd_dsl)
                    mmd_file = diagram_dir / f"{diagram_id}.mmd"
                    svg_path = str(diagram_dir / f"{diagram_id}.svg")
                    mmd_file.write_text(mmd_dsl, encoding="utf-8")
                    manifest.append(
                        {
                            "diagram_id": diagram_id,
                            "section": heading,
                            "anchor_text": spec["anchor_text"],
                            "structure_type": stype,
                            "diagram_type": stype.replace("mermaid-", ""),  # compat
                            "caption": spec["caption"],
                            "mmd_path": str(mmd_file),
                            "svg_path": svg_path,
                        }
                    )

                else:
                    # ── SVG-pattern path ──
                    # Pure-Python renderer in _svg_patterns; no Playwright needed.
                    svg_path = _generate_pattern_svg_file(spec, diagram_id, diagram_dir, book_dir)
                    if not svg_path:
                        continue
                    manifest.append(
                        {
                            "diagram_id": diagram_id,
                            "section": heading,
                            "anchor_text": spec["anchor_text"],
                            "structure_type": stype,
                            "diagram_type": stype,  # for manifest clarity
                            "caption": spec["caption"],
                            "svg_path": svg_path,
                        }
                    )

        except Exception as exc:
            manifest.append(failed_entry(heading, exc))  # unfinished, so the next run redraws this one

    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"    0book-illustrate: manifest written — {len(manifest)} total diagram(s)")

    _render_diagrams(book_dir, log=log)

    # Decouple visuals: the diagrams are generated exactly as before, but instead
    # of injecting them into the book text they are emitted as CANDIDATES to
    # book/visuals/index.json for human curation. book.md stays diagram-free; the
    # render input is book.md (see build_book_pdf._pick_book_md).
    from _visual_candidates import emit_diagram_candidates, merge_entries

    drawn = [e for e in manifest if not e.get("failed")]
    merge_entries(book_dir, emit_diagram_candidates(book_dir, drawn, log=log), log=log)
    log(f"    0book-illustrate: {len(manifest)} diagram candidate(s) offered, book.md left diagram-free")
    return book_md_path


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
