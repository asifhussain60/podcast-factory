"""adapt.py — Surface the in-conversation adaptation prompt for a translated bundle.

This stage does NOT call an LLM API. Instead it:
  1. Reads the translated bundle (raw-extract.md, raw-extract.en.md, editorial-review.md,
     R1/R2 decisions, fatimid-sources.yaml, adapt.md conventions).
  2. Prints a structured brief for the OPERATING SESSION (Claude in the terminal)
     to write adapted-extract.en.md + adaptation-citations.jsonl.
  3. After the operator writes those files, call `seal` with --stage adapted to
     advance bundle.yml.stage from translated → adapted.

Stage transition: translated → adapted  (manual, after operator writes the files)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CLASSIFIER_DATA = REPO_ROOT / "tools" / "content_classifier" / "data"
TRANSLATOR_DATA = REPO_ROOT / "tools" / "content_translator" / "data"
PROMPTS_DIR = REPO_ROOT / "tools" / "content_translator" / "prompts"


def _read_stage(bundle_yml: Path) -> str:
    for line in bundle_yml.read_text(encoding="utf-8").splitlines():
        if line.startswith("stage:"):
            return line.split(":", 1)[1].strip()
    return ""


def _find_r1_entry(binder_id: int, chapter_id: int) -> dict | None:
    r1_file = CLASSIFIER_DATA / "kashkole-r1-decisions.yaml"
    if not r1_file.exists():
        return None
    pattern = re.compile(
        rf"binder_id:\s*{binder_id}.*?chapter_id:\s*{chapter_id}.*?en_title:\s*\"([^\"]+)\"",
        re.DOTALL,
    )
    text = r1_file.read_text(encoding="utf-8")
    # Parse line-based: find the entry block
    for block in text.split("- {"):
        if f"binder_id: {binder_id}" in block and f"chapter_id: {chapter_id}" in block:
            m = re.search(r'en_title:\s*"([^"]+)"', block)
            if m:
                return {"en_title": m.group(1)}
    return None


def _find_r2_entries(binder_id: int, chapter_id: int) -> list[dict]:
    r2_file = CLASSIFIER_DATA / "kashkole-r2-decisions.yaml"
    if not r2_file.exists():
        return []
    entries = []
    text = r2_file.read_text(encoding="utf-8")
    for block in text.split("- {"):
        if f"binder_id: {binder_id}" in block and f"chapter_id: {chapter_id}" in block:
            source_m = re.search(r'source:\s*"([^"]+)"', block)
            en_m = re.search(r'en_title:\s*"([^"]+)"', block)
            topic_m = re.search(r'topic_id:\s*(\d+)', block)
            if en_m:
                entries.append({
                    "topic_id": int(topic_m.group(1)) if topic_m else None,
                    "source": source_m.group(1) if source_m else "",
                    "en_title": en_m.group(1),
                })
    return entries


def surface_adapt_brief(bundle_root: Path, binder_id: int, chapter_id: int) -> None:
    """Print the structured adaptation brief for the operating session."""
    bundle_yml = bundle_root / "bundle.yml"
    text_dir = bundle_root / "_system" / "source" / "text"
    raw_ur = text_dir / "raw-extract.md"
    raw_en = text_dir / "raw-extract.en.md"
    editorial = text_dir / "editorial-review.md"

    if not bundle_yml.exists():
        raise FileNotFoundError(f"bundle.yml not found: {bundle_yml}")

    stage = _read_stage(bundle_yml)
    if stage == "adapted":
        print(f"SKIPPED (already adapted): {bundle_root}")
        return
    if stage != "translated":
        raise RuntimeError(
            f"Stage is '{stage}' — run `translate` first before `adapt`."
        )

    if not raw_en.exists():
        raise FileNotFoundError(f"raw-extract.en.md not found — run translate first.")

    r1 = _find_r1_entry(binder_id, chapter_id)
    r2 = _find_r2_entries(binder_id, chapter_id)
    en_chapter_title = r1["en_title"] if r1 else f"[Chapter {chapter_id} — add R1 title]"

    # Load adapt.md conventions and fatimid sources
    adapt_conventions = ""
    adapt_md = PROMPTS_DIR / "adapt.md"
    if adapt_md.exists():
        adapt_conventions = adapt_md.read_text(encoding="utf-8")

    fatimid_sources = ""
    sources_yaml = TRANSLATOR_DATA / "fatimid-sources.yaml"
    if sources_yaml.exists():
        fatimid_sources = sources_yaml.read_text(encoding="utf-8")

    editorial_text = editorial.read_text(encoding="utf-8") if editorial.exists() else "(not found)"
    urdu_text = raw_ur.read_text(encoding="utf-8")
    english_literal = raw_en.read_text(encoding="utf-8")

    r2_map = "\n".join(
        f"  topic_id={e['topic_id']}: {e['source']} → {e['en_title']}"
        for e in r2
    ) or "  (none — use Urdu topic labels translated literally)"

    sep = "=" * 80
    print(f"""
{sep}
ADAPTATION BRIEF — binder {binder_id} / chapter {chapter_id}
{sep}

## English chapter title (R1)
{en_chapter_title}

## English topic titles (R2 — use as ## headings in adapted-extract.en.md)
{r2_map}

## Output files to write
1. {text_dir}/adapted-extract.en.md
2. {text_dir}/adaptation-citations.jsonl

## Allowed citation sources (fatimid-sources.yaml)
{fatimid_sources}

## Adaptation conventions (adapt.md)
{adapt_conventions}

## Editorial annotations (reviewer findings — address typos, quran-uncited)
{editorial_text[:3000]}{"...(truncated)" if len(editorial_text) > 3000 else ""}

{sep}
## URDU SOURCE (raw-extract.md) — DO NOT MODIFY
{sep}
{urdu_text}

{sep}
## LITERAL ENGLISH (raw-extract.en.md) — base for adaptation
{sep}
{english_literal}

{sep}
INSTRUCTIONS
{sep}
Write adapted-extract.en.md mirroring raw-extract.md's section structure exactly.
Every <!-- section N (id=X, raw_sort=Y): label --> marker must appear verbatim.
Use the R2 English topic titles as ## headings under each section marker.
Polish prose: eliminate translation choppiness, preserve all ⟪ar:⟫ markers,
all ⟪quran S:A⟫ markers, all tables, all blockquotes.
Add 0–3 augmentations per section as [^cite-N] inline footnotes.
Write every augmentation to adaptation-citations.jsonl (one JSON object per line).
When done, run:  python -m tools.content_translator seal --binder {binder_id} --chapter {chapter_id} --stage adapted
{sep}
""")
