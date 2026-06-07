"""_extract_contract.py — Boundary check, chapter/contract resolution, and meta-prose lint.

Split from _extract_helpers.py (DR-005 — files must stay under 600 lines).
Re-exported via _extract_helpers.py so all existing callers remain unaffected.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from _rules import ALLOWED_CATEGORIES  # F3: single source of truth for valid categories
from typing import Any

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

REQUIRED_FIELDS = ["chapter_ref", "slug", "source_type", "title", "audience", "angle",
                   "host_dynamic", "key_tensions"]


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
    missing = [k for k in REQUIRED_FIELDS if c.get(k) in (None, "", [])]
    if missing:
        loc = c.path or "(stub)"
        sys.exit(
            f"ERROR: contract at {loc} is missing required fields: {', '.join(missing)}.\n"
            f"  See scripts/podcast/extract_chapter.py::stub_contract() for the canonical schema."
        )
    if c.get("slug") != chapter.chapter_slug:
        sys.exit(
            f"ERROR: contract.slug ({c.get('slug')!r}) does not match "
            f"chapter slug ({chapter.chapter_slug!r}).\n"
            f"  Under the 1:1 chapter ↔ episode mapping (SKILL.md §0), these must match exactly."
        )

    # INVARIANT 6 (SKILL.md §0): per-chapter title is concise + unique within the book.
    if c.path is not None:
        title = c.get("title")
        if isinstance(title, str):
            stripped = title.strip()
            if not stripped or stripped.startswith("[TODO]"):
                sys.exit(
                    f"ERROR: contract.title at {c.path} is a TODO placeholder. Set a real "
                    f"concise title (≤ 60 chars; ≤ 6 words; unique within the book) before "
                    f"extracting."
                )
            if len(stripped) > 60:
                sys.exit(
                    f"ERROR: contract.title is {len(stripped)} chars (>60). "
                    f"Per SKILL.md INVARIANT 6, chapter titles must be concise."
                )
            # Uniqueness within the book: scan sibling contracts.
            contracts_dir = c.path.parent
            collisions: list[str] = []
            for sibling in sorted(contracts_dir.glob("*.yml")):
                if sibling == c.path:
                    continue
                try:
                    other = load_yaml(sibling.read_text(encoding="utf-8"))
                except Exception:
                    continue
                other_title = (other.get("title") or "").strip()
                if other_title and other_title.lower() == stripped.lower():
                    collisions.append(f"{sibling.name}: {other_title!r}")
            if collisions:
                sys.exit(
                    f"ERROR: contract.title {stripped!r} duplicates another chapter in "
                    f"this book:\n"
                    + "\n".join(f"    {c}" for c in collisions) +
                    f"\n  Per SKILL.md INVARIANT 6, every chapter must have a unique title."
                )
    angle = c.get("angle")
    valid_angles = {
        # Islamic scholarly angles (R-ANGLE family)
        "faithful_exposition", "personal_application",
        "critical_dialectical", "comparative",
        # Fiction / narrative angles
        "faithful_narrative",
    }
    if angle not in valid_angles:
        sys.exit(f"ERROR: contract.angle {angle!r} not in {valid_angles}.")
    mode = c.get("adaptation_mode")
    valid_modes = {"faithful", "bridge", "modern_paraphrase"}
    if mode not in valid_modes:
        sys.exit(f"ERROR: contract.adaptation_mode {mode!r} not in {valid_modes}.")

    # episode_format validation + mode-conditional required fields.
    episode_format = c.get("episode_format") or "deep_dive"
    from _rules import EPISODE_FORMAT_ALLOWED, EPISODE_FORMAT_FULLY_WIRED
    if episode_format not in EPISODE_FORMAT_ALLOWED:
        sys.exit(
            f"ERROR: contract.episode_format {episode_format!r} not in "
            f"{EPISODE_FORMAT_ALLOWED}.\n"
            f"  See infra/claude-agents/podcast-challenger.md Category P for the debate spec.\n"
            f"  F32 extended this enum 2026-05-25; if you're using a brand-new format, "
            f"  check _rules.EPISODE_FORMAT_ALLOWED for the current allowed set."
        )
    if episode_format not in EPISODE_FORMAT_FULLY_WIRED:
        print(
            f"WARNING: contract.episode_format {episode_format!r} is in "
            f"EPISODE_FORMAT_ALLOWED but NOT in EPISODE_FORMAT_FULLY_WIRED "
            f"({EPISODE_FORMAT_FULLY_WIRED}). Downstream framing-author + "
            f"R-HOST-ROLE-PARITY rules will exhibit best-effort behavior. "
            f"This is a P1 warning per F32 plan; not a build blocker.",
            file=sys.stderr,
        )
    if episode_format == "debate":
        debate = c.get("debate")
        if not isinstance(debate, dict):
            sys.exit(
                f"ERROR: contract.episode_format is 'debate' but contract.debate is "
                f"null/missing.\n  Required fields: debate.proposition, debate.host_a, "
                f"debate.host_b, debate.resolution. See debate-framing.md §Framing structure."
            )
        for required in ("proposition", "host_a", "host_b", "resolution"):
            if not debate.get(required):
                sys.exit(
                    f"ERROR: contract.debate.{required} is missing or empty.\n"
                    f"  See debate-framing.md §Vocabulary for what each field means."
                )
        valid_resolutions = {"synthesis", "open", "host_a_concedes",
                             "host_b_concedes", "historical_division"}
        if debate.get("resolution") not in valid_resolutions:
            sys.exit(
                f"ERROR: contract.debate.resolution {debate.get('resolution')!r} not in "
                f"{valid_resolutions}."
            )
        for host_key in ("host_a", "host_b"):
            host = debate.get(host_key)
            if not isinstance(host, dict):
                sys.exit(f"ERROR: contract.debate.{host_key} must be a mapping with role + position + source_moves.")
            for sub in ("role", "position"):
                if not host.get(sub):
                    sys.exit(f"ERROR: contract.debate.{host_key}.{sub} is missing or empty.")

    # source_type ↔ library/<category>/ folder coupling.
    source_type = c.get("source_type")
    valid_source_types = {"book-chapter", "article", "document", "lecture",
                          "interview", "letter",
                          "synthesized-explainer", "explainer-doc"}
    if source_type not in valid_source_types:
        sys.exit(f"ERROR: contract.source_type {source_type!r} not in {valid_source_types}.")
    expected_category = {
        "book-chapter": "books",
        "article":      "articles",
        "document":     "documents",
        "lecture":      "lectures",
        "interview":    "interviews",
        "letter":       "letters",
        "synthesized-explainer": "explainers",
        "explainer-doc": "explainers",
    }[source_type]
    try:
        parents = chapter.path.parents
        actual_category = parents[2].name
        if actual_category in ALLOWED_CATEGORIES:
            if actual_category != expected_category:
                sys.exit(
                    f"ERROR: contract.source_type {source_type!r} requires the chapter to live\n"
                    f"  under <root>/{expected_category}/<book-slug>/, but the\n"
                    f"  chapter resolved to a path under .../{actual_category}/.\n"
                    f"    Chapter: {chapter.path}\n"
                    f"  Fix: either move the chapter to the {expected_category}/ category, or\n"
                    f"  change contract.source_type to match the {actual_category}/ category."
                )
    except IndexError:
        pass


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
