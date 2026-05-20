#!/usr/bin/env python3
"""HTML view updater — renders per-wave completion summaries into the planning views.

When `run_wave.py N` finishes a wave with `EXIT_EXECUTED_DONE` (every
acceptance row in the wave is `[x]`), this module is invoked. It reads
the wave's `on_completion.html_summary` from `_workspace/plan/podcast-plan.yaml`,
and injects it into each `target_files` HTML view as a marker-delimited block.

Marker convention:
    <!-- WAVE_SUMMARY_W{N}_START -->
    ...generated content...
    <!-- WAVE_SUMMARY_W{N}_END -->

Idempotent: re-running on a wave whose summary is already in the view is a
no-op. If the summary text changes (operator edits the YAML), the next call
rewrites the block. If the markers don't exist, the function appends the
block in a documented insertion location.

The whole pipeline is YAML-driven — to change a wave's summary, edit the
YAML; the next wave-done tick re-renders.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_YAML = REPO_ROOT / "_workspace" / "plan" / "podcast-plan.yaml"
DEFAULT_TARGET = REPO_ROOT / "_workspace" / "plan" / "view" / "index.html"

# Anchor in the target HTML where the wave-completion section lives. The
# updater inserts the section at first call; subsequent calls update markers
# inside it.
COMPLETION_SECTION_ANCHOR = "<!-- WAVE_COMPLETIONS_SECTION -->"


@dataclass(frozen=True)
class WaveCompletion:
    wave_id: str           # "W1" / "W2" / ...
    wave_name: str         # "Foundation & Guardrails"
    html_summary: str      # multi-paragraph text from YAML
    target_files: tuple[Path, ...]


def _load_wave_completion(wave_n: int, repo_root: Path | None = None) -> WaveCompletion | None:
    """Parse the YAML to find the wave's `on_completion` block.

    Hand-parsed (no PyYAML dependency in the system Python) — looks for the
    `- id: WN` block and pulls the `on_completion` sub-block. Falls back to
    None if the wave or its `on_completion` field is missing.

    `repo_root` parameter controls how `target_files` paths are resolved.
    Defaults to module-level `REPO_ROOT`.

    The parser is brittle by design — the YAML structure is stable; we don't
    need a full parser. Use Ruby YAML.load for full validation; this parser
    handles the specific 'waves[].on_completion' shape we own.
    """
    if repo_root is None:
        repo_root = REPO_ROOT
    text = PLAN_YAML.read_text()
    wave_id = f"W{wave_n}"
    # Find the wave header
    pattern = re.compile(
        rf"^  - id: {re.escape(wave_id)}\b(.*?)(?=^  - id: |^[a-z_]+:|^# )",
        re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(text)
    if not m:
        return None
    wave_block = m.group(1)

    # Wave name
    name_m = re.search(r"^    name:\s*['\"]?(.+?)['\"]?\s*$", wave_block, re.MULTILINE)
    name = name_m.group(1) if name_m else wave_id

    # on_completion sub-block: look for "    on_completion:" then everything
    # indented at 6+ spaces OR blank lines (blank lines are valid inside the
    # html_summary literal block; we must NOT terminate the sub-block on them).
    oc_m = re.search(
        r"^    on_completion:\s*\n((?:^      .*\n|^[ \t]*\n)+)",
        wave_block,
        re.MULTILINE,
    )
    if not oc_m:
        return None
    oc_block = oc_m.group(1)

    # update_html_views: true   (required for opt-in)
    if not re.search(r"^      update_html_views:\s*true\b", oc_block, re.MULTILINE):
        return None

    # target_files: list
    target_files: list[Path] = []
    targets_m = re.search(
        r"^      target_files:\s*\n((?:^        - .+\n)+)",
        oc_block,
        re.MULTILINE,
    )
    if targets_m:
        for line in targets_m.group(1).splitlines():
            stripped = line.strip()
            if stripped.startswith("- "):
                path_str = stripped[2:].strip().strip("'\"")
                target_files.append(repo_root / path_str)
    if not target_files:
        target_files.append(repo_root / "_workspace" / "plan" / "view" / "index.html")

    # html_summary: |  literal block; everything indented under it
    summary_m = re.search(
        r"^      html_summary:\s*\|\s*\n((?:^        .*\n|^\s*\n)+)",
        oc_block,
        re.MULTILINE,
    )
    if not summary_m:
        return None
    raw = summary_m.group(1)
    # Strip the 8-space block indent
    lines = []
    for line in raw.splitlines():
        if line.startswith("        "):
            lines.append(line[8:])
        elif line.strip() == "":
            lines.append("")
        else:
            break
    summary = "\n".join(lines).rstrip() + "\n"

    return WaveCompletion(
        wave_id=wave_id,
        wave_name=name,
        html_summary=summary,
        target_files=tuple(target_files),
    )


def _render_html_block(wc: WaveCompletion) -> str:
    """Build the marker-delimited HTML block for this wave's completion."""
    paragraphs = [p.strip() for p in wc.html_summary.split("\n\n") if p.strip()]
    paragraph_html = "\n".join(f"    <p>{_escape_html(p)}</p>" for p in paragraphs)
    return (
        f"<!-- WAVE_SUMMARY_{wc.wave_id}_START -->\n"
        f"  <div class=\"wave-completion\" data-wave=\"{wc.wave_id}\">\n"
        f"    <h3>{wc.wave_id} · {_escape_html(wc.wave_name)} — what was delivered</h3>\n"
        f"{paragraph_html}\n"
        f"  </div>\n"
        f"  <!-- WAVE_SUMMARY_{wc.wave_id}_END -->"
    )


def _escape_html(s: str) -> str:
    """Escape '<', '>', '&' for safe HTML insertion. Keeps Arabic / Unicode intact."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _ensure_completions_section(html: str) -> str:
    """If the target view lacks the Wave Completions section, append it.

    Inserts a `<section>` with the anchor comment just before the closing
    `</main>` tag (if found) or just before `</body>` (fallback).
    Idempotent: returns html unchanged if the anchor is already present.
    """
    if COMPLETION_SECTION_ANCHOR in html:
        return html

    section = (
        "\n<!-- =================================================== WAVE COMPLETIONS -->\n"
        f"{COMPLETION_SECTION_ANCHOR}\n"
        "<section aria-labelledby=\"wave-completions-title\">\n"
        "  <h2 id=\"wave-completions-title\">Wave completions</h2>\n"
        "  <p class=\"section-lead\">Plain-language summary of what each wave delivered. "
        "Auto-rendered from <code>_workspace/plan/podcast-plan.yaml</code> "
        "<code>waves[].on_completion.html_summary</code> when a wave's "
        "<code>done_signal</code> flips.</p>\n"
        "  <!-- WAVE_SUMMARY_W1_START --><!-- WAVE_SUMMARY_W1_END -->\n"
        "  <!-- WAVE_SUMMARY_W2_START --><!-- WAVE_SUMMARY_W2_END -->\n"
        "  <!-- WAVE_SUMMARY_W3_START --><!-- WAVE_SUMMARY_W3_END -->\n"
        "  <!-- WAVE_SUMMARY_W4_START --><!-- WAVE_SUMMARY_W4_END -->\n"
        "  <!-- WAVE_SUMMARY_W5_START --><!-- WAVE_SUMMARY_W5_END -->\n"
        "</section>\n"
    )

    # Prefer insertion just before </main>
    if "</main>" in html:
        return html.replace("</main>", section + "\n</main>", 1)
    # Fallback: before </body>
    if "</body>" in html:
        return html.replace("</body>", section + "\n</body>", 1)
    # Last resort: append
    return html + section


def _replace_marker_block(html: str, wave_id: str, new_block: str) -> tuple[str, bool]:
    """Replace the marker-delimited block for the given wave. Returns
    `(updated_html, changed)`. Idempotent — if the existing block equals the
    new block, `changed` is False and html is unchanged."""
    pattern = re.compile(
        rf"<!-- WAVE_SUMMARY_{wave_id}_START -->.*?<!-- WAVE_SUMMARY_{wave_id}_END -->",
        re.DOTALL,
    )
    m = pattern.search(html)
    if m is None:
        # Markers absent — append after the section anchor (if present)
        if COMPLETION_SECTION_ANCHOR in html:
            return (
                html.replace(
                    COMPLETION_SECTION_ANCHOR,
                    COMPLETION_SECTION_ANCHOR + "\n  " + new_block,
                    1,
                ),
                True,
            )
        return html + "\n" + new_block, True

    existing = m.group(0)
    if existing == new_block:
        return html, False
    return html[:m.start()] + new_block + html[m.end():], True


def update_view_for_wave(
    wave_n: int,
    repo_root: Path | None = None,
    *,
    plan_yaml: Path | None = None,
) -> dict[str, list[str]]:
    """Render the wave's completion summary into its `target_files` views.

    Returns `{"updated": [...], "skipped": [...], "missing_summary": True/False}`
    so the caller (run_wave.py) can log accurately. Never raises on missing
    summary — that's a documented case (the wave's on_completion block isn't
    set up yet).
    """
    if repo_root is None:
        repo_root = REPO_ROOT
    yaml_path = plan_yaml or (repo_root / "_workspace" / "plan" / "podcast-plan.yaml")
    if not yaml_path.exists():
        return {"updated": [], "skipped": [], "missing_summary": True}

    # Temporarily point module-level PLAN_YAML at the requested path
    global PLAN_YAML
    saved_plan = PLAN_YAML
    PLAN_YAML = yaml_path
    try:
        wc = _load_wave_completion(wave_n, repo_root=repo_root)
    finally:
        PLAN_YAML = saved_plan

    if wc is None:
        return {"updated": [], "skipped": [], "missing_summary": True}

    new_block = _render_html_block(wc)
    updated: list[str] = []
    skipped: list[str] = []
    for target in wc.target_files:
        if not target.exists():
            skipped.append(str(target))
            continue
        html = target.read_text()
        html = _ensure_completions_section(html)
        new_html, changed = _replace_marker_block(html, wc.wave_id, new_block)
        if changed:
            target.write_text(new_html)
            updated.append(str(target))
        else:
            skipped.append(str(target))
    return {"updated": updated, "skipped": skipped, "missing_summary": False}
