"""_extract_contract.py — Boundary check, chapter/contract resolution, and meta-prose lint.

Split from _extract_helpers.py (DR-005 — files must stay under 600 lines).
Re-exported via _extract_helpers.py so all existing callers remain unaffected.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from typing import Any

from _contract_validation import REQUIRED_FIELDS, validate_contract_full  # FIX 14: one validator, four gates
from _extract_yaml import load_yaml

# ─────────────────────────────────────────────────────────────────────────────
# Boundary check
# ─────────────────────────────────────────────────────────────────────────────

PROHIBITED_PATH_PREFIXES = [
    "babu-memoir",
]


def assert_boundary_safe(p: Path, content_dir: Path) -> None:
    """Refuse to read any path forbidden by SKILL.md §9."""
    try:
        rel = p.resolve().relative_to(content_dir.resolve())
    except ValueError:
        return  # outside content/ — caller's problem, not the boundary's
    rel_str = str(rel).replace("\\", "/")
    for prefix in PROHIBITED_PATH_PREFIXES:
        if rel_str.startswith(prefix):
            sys.exit(
                f"BOUNDARY VIOLATION: refused to read {rel_str}\n"
                f"  SKILL.md §9 prohibits podcast access to content/{prefix}/."
            )


# ─────────────────────────────────────────────────────────────────────────────
# Chapter ref resolution
# ─────────────────────────────────────────────────────────────────────────────

CH_PREFIX_RE = re.compile(r"^ch(\d+)[a-z]?-(.+)$")


@dataclass
class ResolvedChapter:
    path: Path
    source_bucket: str  # book slug taken from library/<category>/<book>/ — never hardcoded
    chapter_number: int | None
    chapter_slug: str   # the slug after ch## (e.g. "man" from "ch01-man")


# ─────────────────────────────────────────────────────────────────────────────
# Contract resolution
# ─────────────────────────────────────────────────────────────────────────────

# REQUIRED_FIELDS now lives in _contract_validation.py (FIX 14) and is re-imported
# above so existing `from _extract_contract import REQUIRED_FIELDS` callers keep working.


@dataclass
class Contract:
    raw: dict[str, Any]
    path: Path | None  # None when stub-generated

    def get(self, key: str, default: Any = None) -> Any:
        return self.raw.get(key, default)


def contract_path_for(chapter: ResolvedChapter) -> Path:
    # Sits next to the chapter file at <book>/chapter-contracts/<slug>.yml.
    return chapter.path.parents[1] / "chapter-contracts" / f"{chapter.chapter_slug}.yml"


def load_contract(explicit: Path | None, chapter: ResolvedChapter) -> Contract:
    if explicit is not None:
        if not explicit.exists():
            sys.exit(f"ERROR: --contract {explicit} does not exist.")
        text = explicit.read_text(encoding="utf-8")
        return Contract(load_yaml(text), explicit)
    default_loc = contract_path_for(chapter)
    if default_loc.exists():
        text = default_loc.read_text(encoding="utf-8")
        return Contract(load_yaml(text), default_loc)
    # Stub
    stub = stub_contract(chapter)
    return Contract(stub, None)


def stub_contract(chapter: ResolvedChapter) -> dict[str, Any]:
    return {
        "chapter_ref": chapter.path.stem,
        "slug": chapter.chapter_slug,
        "source_type": "book-chapter",
        "book_slug": chapter.source_bucket,
        "episode_number": chapter.chapter_number,
        "title": "[TODO] Episode title",
        "audience": "[TODO] Concrete audience description.",
        "angle": "personal_application",
        "episode_format": "deep_dive",
        "host_dynamic": "curious_mind + scholar_companion",
        "host_dynamic_custom": None,
        "debate": None,
        "length_target": "default_deep_dive",
        "key_tensions": ["[TODO] Tension 1", "[TODO] Tension 2", "[TODO] Tension 3"],
        "tone_constraints": ["[TODO] Tone constraint 1"],
        "anchor_passages": [],
        "adaptation_mode": "faithful",
        "phonetic_overrides": {},
        "show_notes": {"blurb": None, "related_episodes": [], "references": []},
    }


def validate_contract(c: Contract, chapter: ResolvedChapter) -> None:
    """FIX 14: thin sys.exit wrapper over _contract_validation.validate_contract_full.

    ALL contract rules (required fields, slug↔file match, title discipline,
    angle/adaptation_mode/source_type enums, episode_format enum, full debate
    block schema, R-HOST-ROLE-PARITY role enums) live in
    _contract_validation.py — the single source of truth shared with the $0
    smoke gate, pipeline_lint, and the Phase-0d post-write gate. Do NOT add
    inline checks here; add them there so every gate inherits them.
    """
    findings = validate_contract_full(
        c.raw, chapter.path, chapter.path.parents[1], contract_path=c.path,
    )
    if findings:
        loc = c.path or "(stub)"
        sys.exit(
            f"ERROR: contract at {loc} failed validation ({len(findings)} finding(s)):\n"
            + "\n".join(f"  - {f}" for f in findings)
            + "\n  See scripts/podcast/_contract_validation.py for the canonical rules\n"
            f"  and scripts/podcast/extract_chapter.py::stub_contract() for the schema."
        )

    # P1 advisory (not a finding, never blocks): format allowed but not yet
    # fully wired downstream — preserved verbatim from the pre-FIX-14 layer.
    episode_format = c.get("episode_format") or "deep_dive"
    from _rules import EPISODE_FORMAT_FULLY_WIRED
    if episode_format not in EPISODE_FORMAT_FULLY_WIRED:
        print(
            f"WARNING: contract.episode_format {episode_format!r} is in "
            f"EPISODE_FORMAT_ALLOWED but NOT in EPISODE_FORMAT_FULLY_WIRED "
            f"({EPISODE_FORMAT_FULLY_WIRED}). Downstream framing-author + "
            f"R-HOST-ROLE-PARITY rules will exhibit best-effort behavior. "
            f"This is a P1 warning per F32 plan; not a build blocker.",
            file=sys.stderr,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Meta-prose lint
# ─────────────────────────────────────────────────────────────────────────────

CONTRACT_META_PROSE_TELLS = [
    "previous episode", "earlier episode", "next episode", "prior episode",
    "earlier in this episode", "later in this episode",
    "this file is", "this document is", "this chapter file",
    "the body below", "the file below",
    "phase 0", "phase 0a", "phase 0b", "phase 0c", "phase 0d", "phase 0e",
    "enrichment status", "enrichment ratio",
    "translator's clarification", "translator's interpolation",
    "the translator notes", "the translator adds",
]
CONTRACT_META_PROSE_REGEX = [
    re.compile(r"\bEP\d{2}\b"),
]

# Fields whose values reach the rendered framing file verbatim.
CONTRACT_LINTED_FIELDS = ("title", "audience", "key_tensions", "tone_constraints",
                          "anchor_passages")


def lint_contract_meta_prose(c: Contract) -> None:
    """Refuse contracts whose text would trip build_episode_txt.py's meta-prose guard."""
    hits: list[str] = []
    for fld in CONTRACT_LINTED_FIELDS:
        value = c.get(fld)
        if value is None:
            continue
        items = value if isinstance(value, list) else [value]
        for i, item in enumerate(items):
            if not isinstance(item, str):
                continue
            lower = item.lower()
            for tell in CONTRACT_META_PROSE_TELLS:
                if tell in lower:
                    label = f"{fld}[{i}]" if isinstance(value, list) else fld
                    hits.append(f"  - {label}: contains {tell!r}\n    line: {item.strip()[:140]}")
                    break
            else:
                for pat in CONTRACT_META_PROSE_REGEX:
                    m = pat.search(item)
                    if m:
                        label = f"{fld}[{i}]" if isinstance(value, list) else fld
                        hits.append(f"  - {label}: matches regex {pat.pattern!r} ({m.group(0)!r})\n    line: {item.strip()[:140]}")
                        break
    if hits:
        loc = c.path or "(stub)"
        sys.exit(
            f"ERROR: contract at {loc} contains meta-prose that would reach NotebookLM.\n"
            + "\n".join(hits) + "\n"
            f"  Reword to avoid cross-episode references (EP##, 'next/previous/earlier episode')\n"
            f"  and authoring metadata. NotebookLM has no context for other episodes — every\n"
            f"  Audio Overview is generated against a single source upload."
        )
