#!/usr/bin/env python3
"""extract_chapter.py — Capability-first extractor for the /podcast skill.

Resolves a chapter reference to a source file, reads its sidecar contract,
and emits a deterministic NotebookLM Audio Overview bundle: 00-framing.md,
02-key-passages.md, 03-context-pack.md,
04-discussion-spine.md, 99-show-notes.md.

INVOCATION

  python3 scripts/podcast/extract_chapter.py <chapter-ref>
  python3 scripts/podcast/extract_chapter.py <chapter-ref> --contract <path>
  python3 scripts/podcast/extract_chapter.py <chapter-ref> --force

CHAPTER REF RESOLUTION

  1. Literal path (absolute or repo-relative) → used as-is.
  2. `<book-slug>/<ref>` shorthand → resolves within that book only.
  3. Bare `<ref>` → searches every
     _workspace/*/*/chapters/<ref>.txt. If more than one book
     owns the same chapter slug, the script refuses with a disambiguation
     error rather than silently picking the alphabetically-first match.

CONTRACT RESOLUTION

  1. --contract <path> (explicit)
  2. _workspace/<category>/<book-slug>/chapter-contracts/<chapter-slug>.yml
  3. Falls back to a generated stub at the location above, with [TODO] markers.

OUTPUT (per contract.source_type)

  book-chapter:  content/drafts/<book_slug>/...
  article:       _workspace/articles/<book_slug>/...

  ├── chapters/ch##-<slug>.txt                       (chapter copy; SOURCE upload; THE refinement target)
  ├── _system/episode-drafts/EP##-<slug>/
  │   ├── 00-framing.md         (CUSTOMIZE PROMPT body — fed to build_episode_txt.py)
  │   ├── 02-key-passages.md    (scaffold with anchor markers)
  │   ├── 03-context-pack.md    (scaffold)
  │   ├── 04-discussion-spine.md (N beat templates per length_target)
  │   └── 99-show-notes.md      (optional, from contract.show_notes)
  └── (build_episode_txt.py emits episodes/EP##-<slug>.txt downstream)

  NOTE: No `01-source-primary.md` — the chapter file IS the source under v3.4's
  two-file deliverable model (SKILL.md §0 Invariant 1).

DETERMINISM GUARANTEE

  Same chapter + same contract → byte-identical bundle scaffolding.
  No timestamps, no random ordering, no environment-dependent paths.
  Content slots requiring downstream LLM authoring are clearly marked
  with [LLM-SELECT], [LLM-FILL], or [TODO].

BOUNDARY (SKILL.md §9)

  This script reads ONLY content/podcast/**. Memoir content
  (content/babu-memoir/**) is out of scope and refused by the adapter
  via PROHIBITED_PATH_PREFIXES.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
# Repo layout
# ─────────────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTENT_DIR = REPO_ROOT / "content"
PODCAST_DIR = CONTENT_DIR / "podcast"
LIBRARY_DIR = PODCAST_DIR / "library"  # legacy (retired 2026-05-23); kept for any
                                       # stragglers under the old tree.

# Post-restructure 2026-05-23: in-flight books live at content/drafts/<book>/
# and shipped books at content/published/books/<book>/. resolve_chapter_ref()
# checks these locations first, then falls back to the legacy LIBRARY_DIR.
DRAFTS_DIR = CONTENT_DIR / "drafts"
PUBLISHED_BOOKS_DIR = CONTENT_DIR / "published" / "books"


def _chapter_lookup_roots() -> list[Path]:
    """The directories under which to search for `<book>/chapters/<ref>.txt`.

    Listed in resolution priority. The first non-empty match wins; ambiguity
    across roots is treated as an error (drafts and published may both carry
    the same slug only mid-promotion — surface it).
    """
    return [DRAFTS_DIR, PUBLISHED_BOOKS_DIR, LIBRARY_DIR]


def _book_glob(book_slug: str, bare_ref: str) -> list[Path]:
    """Glob `<root>/<book_slug>/chapters/<bare_ref>.txt` across all known roots.

    Also matches `<root>/<category>/<book_slug>/chapters/<bare_ref>.txt` so
    the legacy LIBRARY_DIR shape (which puts books under a category dir) still
    resolves. New content/drafts and content/published/books are flat.
    """
    out: list[Path] = []
    for root in _chapter_lookup_roots():
        flat = root / book_slug / "chapters" / f"{bare_ref}.txt"
        if flat.exists():
            out.append(flat)
        out.extend(root.glob(f"*/{book_slug}/chapters/{bare_ref}.txt"))
    return out


def _all_chapter_paths(ref: str) -> list[Path]:
    """Find every `<root>/<book>/chapters/<ref>.txt` and
    `<root>/<category>/<book>/chapters/<ref>.txt`."""
    out: list[Path] = []
    for root in _chapter_lookup_roots():
        out.extend(p for p in root.glob(f"*/chapters/{ref}.txt") if p.is_file())
        out.extend(p for p in root.glob(f"*/*/chapters/{ref}.txt") if p.is_file())
    return out
HANDBOOK_DIR = PODCAST_DIR / ".skill" / "handbook"

# Boundary enforcement — any read that resolves into one of these is fatal.
# Memoir content is out of scope for the podcast skill.
PROHIBITED_PATH_PREFIXES = [
    "babu-memoir",
]

# ─────────────────────────────────────────────────────────────────────────────
# Tiny YAML reader (stdlib only — avoids adding a runtime dep)
#
# Handles the subset the contract uses: scalars, quoted strings, multiline
# folded scalars (`>`), block lists, mappings, and `null`. Refuses anything
# else with a clear error rather than guessing.
# ─────────────────────────────────────────────────────────────────────────────


def _parse_scalar(raw: str) -> Any:
    s = raw.strip()
    if s == "" or s.lower() == "null" or s == "~":
        return None
    if s.lower() == "true":
        return True
    if s.lower() == "false":
        return False
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(p) for p in inner.split(",")]
    if s.startswith("{") and s.endswith("}"):
        inner = s[1:-1].strip()
        if not inner:
            return {}
        out: dict[str, Any] = {}
        for pair in inner.split(","):
            if ":" not in pair:
                raise ValueError(f"bad inline map entry: {pair!r}")
            k, v = pair.split(":", 1)
            out[k.strip()] = _parse_scalar(v)
        return out
    try:
        if "." in s:
            return float(s)
        return int(s)
    except ValueError:
        return s


def load_yaml(text: str) -> dict[str, Any]:
    """Minimal YAML subset → dict. Raises ValueError on unsupported constructs."""
    lines = text.splitlines()
    i = 0
    result: dict[str, Any] = {}

    def parse_block(start: int, indent: int) -> tuple[Any, int]:
        # Decide if the block is a list (lines start with '- ') or a mapping.
        j = start
        while j < len(lines) and (not lines[j].strip() or lines[j].lstrip().startswith("#")):
            j += 1
        if j >= len(lines):
            return None, j
        first = lines[j]
        first_indent = len(first) - len(first.lstrip())
        if first_indent < indent:
            return None, j

        if first.lstrip().startswith("- "):
            items: list[Any] = []
            k = j
            while k < len(lines):
                ln = lines[k]
                if not ln.strip() or ln.lstrip().startswith("#"):
                    k += 1
                    continue
                ln_indent = len(ln) - len(ln.lstrip())
                if ln_indent < indent:
                    break
                if ln_indent == indent and ln.lstrip().startswith("- "):
                    item_text = ln.lstrip()[2:]
                    if ":" in item_text and not item_text.startswith("'") and not item_text.startswith('"'):
                        # nested mapping inside a list item
                        sub: dict[str, Any] = {}
                        key, _, val = item_text.partition(":")
                        if val.strip():
                            sub[key.strip()] = _parse_scalar(val)
                        # consume further indented lines as part of this mapping
                        k += 1
                        nested, k = parse_block(k, indent + 4)
                        if isinstance(nested, dict):
                            sub.update(nested)
                        items.append(sub)
                        continue
                    items.append(_parse_scalar(item_text))
                    k += 1
                else:
                    break
            return items, k

        # Mapping
        m: dict[str, Any] = {}
        k = j
        while k < len(lines):
            ln = lines[k]
            if not ln.strip() or ln.lstrip().startswith("#"):
                k += 1
                continue
            ln_indent = len(ln) - len(ln.lstrip())
            if ln_indent < indent:
                break
            if ln_indent > indent:
                k += 1
                continue
            if ":" not in ln:
                raise ValueError(f"line {k+1}: expected `key: value`, got: {ln!r}")
            key, _, val = ln.partition(":")
            key = key.strip()
            val = val.rstrip()
            if val.strip() == "":
                # Block scalar coming on next lines
                k += 1
                child, k = parse_block(k, indent + 2)
                m[key] = child
                continue
            if val.strip() == ">":
                # Folded scalar — collect indented lines until dedent
                k += 1
                buf: list[str] = []
                while k < len(lines):
                    nxt = lines[k]
                    if not nxt.strip():
                        buf.append("")
                        k += 1
                        continue
                    nxt_indent = len(nxt) - len(nxt.lstrip())
                    if nxt_indent <= indent:
                        break
                    buf.append(nxt.strip())
                    k += 1
                folded = " ".join(s for s in buf if s).strip()
                m[key] = folded
                continue
            m[key] = _parse_scalar(val.lstrip())
            k += 1
        return m, k

    parsed, _ = parse_block(0, 0)
    if not isinstance(parsed, dict):
        return {}
    return parsed


# ─────────────────────────────────────────────────────────────────────────────
# Boundary check
# ─────────────────────────────────────────────────────────────────────────────


def assert_boundary_safe(p: Path) -> None:
    """Refuse to read any path forbidden by SKILL.md §9."""
    try:
        rel = p.resolve().relative_to(CONTENT_DIR.resolve())
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


def resolve_chapter_ref(ref: str) -> ResolvedChapter:
    """Resolve a chapter ref string to a (path, source-bucket, num, slug).

    Resolution order (first definitive match wins; ambiguity is an error):

      1. Literal path (absolute or repo-relative) → used as-is.
      2. `<book-slug>/<ref>` shorthand → forces resolution within one book.
      3. Bare `<ref>` → searched across every
         `library/<category>/<book>/chapters/<ref>.txt`. If the same `<ref>`
         exists in more than one book, the script refuses and asks the caller
         to disambiguate via `<book-slug>/<ref>`.
    """

    def parse_chapter_filename(p: Path) -> tuple[int | None, str]:
        stem = p.stem
        m = CH_PREFIX_RE.match(stem)
        if m:
            return int(m.group(1)), m.group(2)
        return None, stem

    # 1. Literal path
    literal = Path(ref)
    if not literal.is_absolute():
        literal = (REPO_ROOT / ref).resolve()
    if literal.exists() and literal.is_file():
        assert_boundary_safe(literal)
        # Determine bucket from path (expected: _workspace/<category>/<book>/chapters/<file>.txt)
        try:
            rel = literal.relative_to(CONTENT_DIR)
            parts = rel.parts
            if parts[0] == "podcast" and len(parts) >= 4 and parts[1] == "library":
                bucket = parts[3]  # the book-slug under <category>/
            elif parts[0] == "podcast" and len(parts) >= 2:
                bucket = parts[1]  # legacy fallback
            else:
                bucket = parts[0]
        except ValueError:
            bucket = "unknown"
        num, slug = parse_chapter_filename(literal)
        return ResolvedChapter(literal, bucket, num, slug)

    # 2. `<book-slug>/<ref>` shorthand: explicit book scoping.
    if "/" in ref and not ref.startswith("/"):
        book_slug, bare_ref = ref.split("/", 1)
        candidates = _book_glob(book_slug, bare_ref)
        if len(candidates) == 1:
            cand = candidates[0]
            assert_boundary_safe(cand)
            num, slug = parse_chapter_filename(cand)
            return ResolvedChapter(cand, book_slug, num, slug)
        if len(candidates) > 1:
            sys.exit(
                f"ERROR: book-slug {book_slug!r} resolves to multiple paths. Found:\n"
                + "\n".join(f"    {c}" for c in candidates)
            )
        # 0 matches under the explicit book — fall through to bare-ref resolution
        # so the caller sees the standard "could not resolve" message with all
        # paths tried.

    # 3. Bare `<ref>`: search every {drafts,published,legacy-library}/<book>/chapters/.
    matches = _all_chapter_paths(ref)
    if len(matches) == 1:
        cand = matches[0]
        assert_boundary_safe(cand)
        num, slug = parse_chapter_filename(cand)
        bucket = cand.parents[1].name
        return ResolvedChapter(cand, bucket, num, slug)
    if len(matches) > 1:
        # Ambiguous: same chapter slug in two or more books. Refuse the lookup
        # rather than silently picking the first match (the old behavior favored
        # the alphabetically-first book, which is exactly the cross-book
        # contamination this script must avoid).
        sys.exit(
            f"ERROR: chapter ref {ref!r} matches in {len(matches)} books:\n"
            + "\n".join(f"    {c.parents[1].name}/  →  {c.relative_to(REPO_ROOT)}"
                        for c in matches) +
            f"\n  Disambiguate by passing `<book-slug>/{ref}` "
            f"(e.g. `<book-slug>/{ref}`) or the full repo-relative path."
        )

    sys.exit(
        f"ERROR: could not resolve chapter ref {ref!r}.\n"
        f"  Tried:\n"
        f"    {literal}\n"
        f"    {DRAFTS_DIR}/*/chapters/{ref}.txt\n"
        f"    {DRAFTS_DIR}/*/*/chapters/{ref}.txt\n"
        f"    {PUBLISHED_BOOKS_DIR}/*/chapters/{ref}.txt\n"
        f"    {LIBRARY_DIR}/*/*/chapters/{ref}.txt   (legacy)\n"
    )


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
    # chapter.path is library/<category>/<book>/chapters/ch##-<slug>.txt;
    # parents[1] is the <book> directory.
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
            f"  See content/podcast/.skill/handbook/chapter-contract.template.yml for the full schema."
        )
    if c.get("slug") != chapter.chapter_slug:
        sys.exit(
            f"ERROR: contract.slug ({c.get('slug')!r}) does not match "
            f"chapter slug ({chapter.chapter_slug!r}).\n"
            f"  Under the 1:1 chapter ↔ episode mapping (SKILL.md §0), these must match exactly."
        )

    # INVARIANT 6 (SKILL.md §0): per-chapter title is concise + unique within the book.
    # Skip this check for stub contracts — those are intentionally TODO-marked and
    # written to disk by emit_bundle so the author can edit them in place.
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
    valid_angles = {"faithful_exposition", "personal_application",
                    "critical_dialectical", "comparative"}
    if angle not in valid_angles:
        sys.exit(f"ERROR: contract.angle {angle!r} not in {valid_angles}.")
    mode = c.get("adaptation_mode")
    valid_modes = {"faithful", "bridge", "modern_paraphrase"}
    if mode not in valid_modes:
        sys.exit(f"ERROR: contract.adaptation_mode {mode!r} not in {valid_modes}.")

    # episode_format validation + mode-conditional required fields.
    # Default to deep_dive when absent (backward compat with pre-v3.6 contracts).
    episode_format = c.get("episode_format") or "deep_dive"
    valid_formats = {"deep_dive", "debate"}
    if episode_format not in valid_formats:
        sys.exit(
            f"ERROR: contract.episode_format {episode_format!r} not in {valid_formats}.\n"
            f"  See content/podcast/.skill/handbook/debate-framing.md for the debate spec."
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
    # The category folder is derived from the chapter's resolved path; the
    # contract's source_type must match. Mismatch usually means the contract
    # was copy-pasted from another book without updating source_type.
    source_type = c.get("source_type")
    valid_source_types = {"book-chapter", "article", "document", "lecture",
                          "interview", "letter"}
    if source_type not in valid_source_types:
        sys.exit(f"ERROR: contract.source_type {source_type!r} not in {valid_source_types}.")
    # Map source_type → expected category folder (plural noun under library/).
    expected_category = {
        "book-chapter": "books",
        "article":      "articles",
        "document":     "documents",
        "lecture":      "lectures",
        "interview":    "interviews",
        "letter":       "letters",
    }[source_type]
    # Post-restructure 2026-05-23: in-flight books live at content/drafts/<book>/
    # (NOT content/drafts/<category>/<book>/) and shipped books at
    # content/published/books/<book>/. The category check below only fires for
    # the legacy library/<category>/<book>/ layout. For the new layout, the
    # source_type → category mapping is irrelevant because the layout is flat
    # under drafts/ and published/books/ (no per-category subdirectory).
    try:
        parents = chapter.path.parents
        # Legacy layout: <root>/<category>/<book>/chapters/<file>.txt → parents[2].name = <category>
        # New layout (drafts):    content/drafts/<book>/chapters/<file>.txt → parents[2].name = "content"
        # New layout (published): content/published/books/<book>/chapters/<file>.txt → parents[2].name = "published"
        # We only flag a mismatch when the resolved root contains a real category dir.
        actual_category = parents[2].name
        if actual_category in ("books", "articles", "documents", "lectures", "interviews", "letters"):
            if actual_category != expected_category:
                sys.exit(
                    f"ERROR: contract.source_type {source_type!r} requires the chapter to live\n"
                    f"  under <root>/{expected_category}/<book-slug>/, but the\n"
                    f"  chapter resolved to a path under .../{actual_category}/.\n"
                    f"    Chapter: {chapter.path}\n"
                    f"  Fix: either move the chapter to the {expected_category}/ category, or\n"
                    f"  change contract.source_type to match the {actual_category}/ category."
                )
        # else: new flat layout under content/drafts/ or content/published/books/.
        # The category dimension is collapsed in the new layout; the source_type
        # field on the contract is the sole declaration of category.
    except IndexError:
        # Chapter resolved via a non-standard path (legacy literal-path fallback);
        # skip the category check rather than crashing.
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Meta-prose lint (mirrors build_episode_txt.py — fail fast at extract time
# rather than letting the build refuse a generated framing file).
# ─────────────────────────────────────────────────────────────────────────────

# Kept in sync with scripts/podcast/build_episode_txt.py. Any string that the
# build script's META_PROSE_TELLS / META_PROSE_REGEX_TELLS would catch will also
# fail here, but earlier — before the framing is even rendered.
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
    """Refuse contracts whose text would trip build_episode_txt.py's meta-prose
    guard. Runs before any file is written, so the user fixes the contract,
    not a generated artifact."""
    hits: list[str] = []
    for field in CONTRACT_LINTED_FIELDS:
        value = c.get(field)
        if value is None:
            continue
        items = value if isinstance(value, list) else [value]
        for i, item in enumerate(items):
            if not isinstance(item, str):
                continue
            lower = item.lower()
            for tell in CONTRACT_META_PROSE_TELLS:
                if tell in lower:
                    label = f"{field}[{i}]" if isinstance(value, list) else field
                    hits.append(f"  - {label}: contains {tell!r}\n    line: {item.strip()[:140]}")
                    break
            else:
                for pat in CONTRACT_META_PROSE_REGEX:
                    m = pat.search(item)
                    if m:
                        label = f"{field}[{i}]" if isinstance(value, list) else field
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


# ─────────────────────────────────────────────────────────────────────────────
# Episode number assignment
# ─────────────────────────────────────────────────────────────────────────────


def next_episode_number(bucket_root: Path) -> int:
    """Scan existing _system/episode-drafts/EP##-* and return next monotonic."""
    drafts = bucket_root / "_system" / "episode-drafts"
    if not drafts.exists():
        return 1
    highest = 0
    for d in drafts.iterdir():
        if not d.is_dir():
            continue
        m = re.match(r"^EP(\d+)-", d.name)
        if m:
            highest = max(highest, int(m.group(1)))
    return highest + 1


# ─────────────────────────────────────────────────────────────────────────────
# Bundle scaffolding (deterministic templates)
# ─────────────────────────────────────────────────────────────────────────────


def fmt_list(items: list[Any], prefix: str = "  - ") -> str:
    if not items:
        return f"{prefix}[LLM-FILL]\n"
    return "".join(f"{prefix}{x}\n" for x in items)


def render_framing(c: Contract, chapter: ResolvedChapter, ep_num: int) -> str:
    episode_format = c.get("episode_format") or "deep_dive"
    if episode_format == "debate":
        return _render_framing_debate(c, chapter, ep_num)
    return _render_framing_deep_dive(c, chapter, ep_num)


def _render_framing_deep_dive(c: Contract, chapter: ResolvedChapter, ep_num: int) -> str:
    title = c.get("title")
    audience = c.get("audience")
    angle = c.get("angle")
    host_dynamic = c.get("host_dynamic")
    if host_dynamic == "custom" and c.get("host_dynamic_custom"):
        host_dynamic = c.get("host_dynamic_custom")
    tensions = c.get("key_tensions", [])
    tone = c.get("tone_constraints", [])
    length = c.get("length_target", "default_deep_dive")

    length_blurb = {
        "brief": "Target ~6–10 min Audio Overview. Tight, single argument.",
        "default_deep_dive": "Target ~12–15 min Audio Overview. One coherent theme, two-to-three connected ideas, room for dialogue.",
        "longer": "Target ~22–40 min Audio Overview. Multi-thematic; let the conversation breathe.",
    }.get(length, "Target ~12–15 min Audio Overview.")

    phonetics = c.get("phonetic_overrides") or {}
    if phonetics:
        rows = "".join(f"  - **{term}** — {respelling}\n" for term, respelling in phonetics.items())
        pronunciation_block = (
            "Speak every term below using the respelling and gloss in parentheses. "
            "On first appearance per episode, pair the term with its brief gloss; on subsequent "
            "appearances, the term alone is fine.\n\n"
            f"{rows}"
        )
    else:
        pronunciation_block = (
            "[LLM-FILL — list every non-English term, transliteration, or name appearing in the "
            "source, with respelling and brief gloss. Or set contract.phonetic_overrides.]"
        )

    return f"""# {title}

**Episode format:** Deep Dive (two hosts walk through the source). See `.skill/handbook/two-host-framing.md` for the format spec; if this should be a debate instead, set `contract.episode_format: debate` and see `.skill/handbook/debate-framing.md`.

## Opening directive

In the first ten seconds, the hosts should name the work and the question this episode is asking. Do not open with "today we'll discuss". Start in the middle of the question.

## Audience

{audience}

## Angle

`{angle}` — see content/podcast/.skill/handbook/source-distillation.md for what this lens commits the hosts to.

## Length

{length_blurb}

## Host dynamic

`{host_dynamic}`. See content/podcast/.skill/handbook/two-host-framing.md for default personas.

## Central tensions to reach

The hosts MUST surface every one of these tensions, by name, in the conversation:

{fmt_list(tensions)}
## Tone constraints

The hosts must NOT do the following:

{fmt_list(tone)}
## Pronunciation hooks

{pronunciation_block}

## Anti-noise rules

- Quote directly from the source when discussing a beat. Do not paraphrase the source's voice.
- Treat this as a standalone Audio Overview. Do not reference other Audio Overviews — they are not in NotebookLM's context.
- Do not abbreviate honorifics; speak them in full.
- End on a question, not a conclusion.
"""


def _render_framing_debate(c: Contract, chapter: ResolvedChapter, ep_num: int) -> str:
    title = c.get("title")
    audience = c.get("audience")
    tone = c.get("tone_constraints", [])
    length = c.get("length_target", "default_deep_dive")
    debate = c.get("debate") or {}
    prop = debate.get("proposition", "[LLM-FILL — proposition under debate]")
    host_a = debate.get("host_a") or {}
    host_b = debate.get("host_b") or {}
    resolution = debate.get("resolution", "open")

    length_blurb = {
        "brief": "Target ~6–10 min Audio Overview. One tight exchange of positions.",
        "default_deep_dive": "Target ~12–15 min Audio Overview. Three or four moves per side, with a resolution beat at the close.",
        "longer": "Target ~22–40 min Audio Overview. Multi-stage debate; positions stress-tested through several rounds.",
    }.get(length, "Target ~12–15 min Audio Overview.")

    resolution_blurb = {
        "synthesis": "The two positions resolve into a richer reading the listener can carry. Both hosts arrive at a shared statement that neither one held at the start.",
        "open": "The two positions are held in tension at the close. No host announces a winner. The listener leaves with both views in mind.",
        "host_a_concedes": f"Host A — {host_a.get('role', '[role]')} — concedes the main point to Host B by the close, having lost the disputation on the source's own terms.",
        "host_b_concedes": f"Host B — {host_b.get('role', '[role]')} — concedes the main point to Host A by the close.",
        "historical_division": "The episode names the disagreement as one the tradition itself has held both ways. Neither host concedes; neither synthesizes. The close states that the tradition is divided.",
    }.get(resolution, "[LLM-FILL — resolution shape]")

    moves_a = host_a.get("source_moves", []) or []
    moves_b = host_b.get("source_moves", []) or []
    moves_a_block = fmt_list(moves_a) if moves_a else "  - [LLM-FILL — quotes, passages, and traditions Host A draws on]\n"
    moves_b_block = fmt_list(moves_b) if moves_b else "  - [LLM-FILL — quotes, passages, and traditions Host B draws on]\n"

    phonetics = c.get("phonetic_overrides") or {}
    if phonetics:
        rows = "".join(f"  - **{term}** — {respelling}\n" for term, respelling in phonetics.items())
        pronunciation_block = (
            "Speak every term below using the respelling and gloss in parentheses. "
            f"On first appearance, pair the term with its brief gloss.\n\n{rows}"
        )
    else:
        pronunciation_block = (
            "[LLM-FILL — list every non-English term with respelling and gloss, "
            "or set contract.phonetic_overrides.]"
        )

    return f"""# {title}

**Episode format:** Debate (each host adopts a role + position and argues from it). See `.skill/handbook/debate-framing.md` for the full format spec.

## Opening directive

In the first twenty seconds, the hosts name the work, state the proposition under debate verbatim, and tell the listener that they will hold opposing positions through the conversation. Do not open with "today we'll discuss" or "welcome to this deep dive". Open by stating the proposition.

## Audience

{audience}

## Length

{length_blurb}

## Proposition under debate

> {prop}

## Roles + positions

**Host A — {host_a.get('role', '[LLM-FILL role]')}.**
Position: {host_a.get('position', '[LLM-FILL position]')}

Source moves available to Host A:
{moves_a_block}
**Host B — {host_b.get('role', '[LLM-FILL role]')}.**
Position: {host_b.get('position', '[LLM-FILL position]')}

Source moves available to Host B:
{moves_b_block}
## Rules of debate (apply through the entire episode)

1. **No strawman.** Each host argues the strongest form of their position. The OTHER host names the weaknesses, never the host holding it.
2. **Source-grounded only.** Every move references the source text, a passage from the same author's larger corpus, or an established tradition the position is anchored in. No appeals to modern common sense.
3. **Defended positions stay defended.** A host may concede a sub-point with qualification ("That's a fair point on X, but...") but does not abandon their named position unless the resolution is `host_X_concedes`.
4. **Disagreement is the work.** Acknowledgment grammar ("Exactly", "Yeah, exactly") that is forbidden in Deep Dive is softened here: a host may concede a sub-point but the concession is qualified and followed by a return to the host's main position. Bare affirmations remain forbidden.
5. **One position at a time.** Each beat surfaces one part of the argument. Hosts do not jump topics.
6. **The proposition is named at open and at close.** Resolution is announced at the close per the contract's `resolution` field; no host announces a winner.
7. **No verdict from the host.** Neither host says "I've convinced you" or "you have to admit". The listener decides.
8. **The author's voice is third in the room.** A quote from the source is authoritative for that moment, regardless of which host invokes it.

## Resolution

`{resolution}` — {resolution_blurb}

## Tone constraints

The hosts must NOT do the following:

{fmt_list(tone)}
- No ad hominem. No characterizing the other position as foolish, naive, or fundamentalist.
- No sarcasm. Firm disagreement, not contempt.
- No theatrical opposition ("battle of ideas", "showdown", "who is right"). This is *munazara*, not boxing.

## Pronunciation hooks

{pronunciation_block}

## Anti-noise rules

- Quote directly from the source. Each host's moves cite specific passages.
- Treat this as a standalone Audio Overview. Do not reference other Audio Overviews.
- Do not abbreviate honorifics; speak them in full.
- Close on the resolution beat as specified above, not on a host paraphrase.
"""


def render_key_passages(c: Contract, chapter: ResolvedChapter) -> str:
    anchors = c.get("anchor_passages", [])
    body = ""
    if anchors:
        for i, p in enumerate(anchors, 1):
            body += f"### Passage {i}\n\n> {p}\n\n*Why this matters:* [LLM-FILL]\n\n"
    else:
        body = """### [LLM-SELECT] 6–15 verbatim passages

The downstream authoring pass selects 6–15 verbatim passages from the chapter file (`BOOK_DIR/chapters/chNN-<slug>.txt`), ordered as they appear in the source. Each gets:

```
### Passage N

> [verbatim quote from source]

*Why this matters:* [one-line significance]
```

Bias toward passages that:
  - State a position clearly
  - Surprise the listener
  - Contradict another part of the chapter or another tradition
  - Land emotionally
"""
    return f"""# Key passages

Verbatim quotes from the source. NotebookLM retrieves these when the discussion spine directs hosts to a beat.

---

{body}"""


def render_context_pack(c: Contract, chapter: ResolvedChapter) -> str:
    return f"""# Context pack

Background the hosts need to stay grounded. Not airtime — retrieval support.

## Author / narrator

[LLM-FILL — name the author, dates, tradition.]

## What this chapter is responding to

[LLM-FILL — the question or wound or argument the chapter is answering.]

## Tradition / lineage

[LLM-FILL — what intellectual or emotional tradition this chapter sits inside.]

## Related works

[LLM-FILL — other chapters or books that touch the same territory.]

## Why this lands now

{"[LLM-FILL — the bridge to the contemporary listener; required when adaptation_mode = bridge.]" if c.get("adaptation_mode") == "bridge" else "[Not required for this adaptation mode.]"}
"""


def render_discussion_spine(c: Contract, chapter: ResolvedChapter) -> str:
    length = c.get("length_target", "default_deep_dive")
    beat_count = {"brief": 6, "default_deep_dive": 8, "longer": 12}.get(length, 8)
    tensions = c.get("key_tensions", [])
    tensions_line = "; ".join(str(t) for t in tensions[:3]) or "[contract.key_tensions]"

    beats = ""
    for i in range(1, beat_count + 1):
        if i == 1:
            beat_title = "Opening hook"
            hint = "Open inside the question. A single passage or a tension the listener walks in carrying. Never 'today we'll discuss'."
        elif i == beat_count:
            beat_title = "Landing"
            hint = "End on a question or unresolved tension. No takeaway. No summary."
        else:
            beat_title = f"[LLM-FILL] Beat {i}"
            hint = "Name the tension this beat asks. Name the passage it anchors to. Name the residue it leaves."
        beats += f"""### Beat {i}: {beat_title}

- **Key question:** [LLM-FILL]
- **Tension:** [LLM-FILL — must draw from: {tensions_line}]
- **Anchor passage:** [LLM-FILL — reference passage N from `02-key-passages.md`]
- **Landing:** {hint}

"""
    return f"""# Discussion spine

{beat_count} beats. The hidden steering layer — NotebookLM hosts follow this when it is well-built.

---

{beats.rstrip()}
"""


def render_show_notes(c: Contract, chapter: ResolvedChapter, ep_num: int) -> str:
    sn = c.get("show_notes") or {}
    blurb = sn.get("blurb") or "[LLM-FILL — 1–2 sentence episode description]"
    related = sn.get("related_episodes") or []
    refs = sn.get("references") or []
    title = c.get("title")
    none_line = "  - [none]" + "\n"
    related_block = fmt_list(related) if related else none_line
    refs_block = fmt_list(refs) if refs else none_line
    return f"""# Show notes — EP{ep_num:02d}

**Title:** {title}

**Blurb:** {blurb}

**Length estimate:** see contract.length_target ({c.get('length_target')})

## Related episodes

{related_block}
## References

{refs_block}"""


# ─────────────────────────────────────────────────────────────────────────────
# Emit
# ─────────────────────────────────────────────────────────────────────────────


def write_if_needed(path: Path, content: str, force: bool, written: list[Path], skipped: list[Path]) -> None:
    if path.exists() and not force:
        existing = path.read_text(encoding="utf-8")
        if existing == content:
            skipped.append(path)
            return
        sys.exit(
            f"ERROR: {path} already exists and differs from the new render.\n"
            f"  Re-run with --force to overwrite, or diff manually."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    written.append(path)


def emit_bundle(chapter: ResolvedChapter, c: Contract, force: bool) -> None:
    bucket = chapter.source_bucket
    if c.get("source_type") == "book-chapter" and c.get("book_slug"):
        bucket = c.get("book_slug")
    # bucket_root derived from the resolved chapter path. Chapter file is at:
    #   - legacy:    library/<category>/<book>/chapters/<file>.txt → parents[1] = <book>
    #   - drafts:    content/drafts/<book>/chapters/<file>.txt    → parents[1] = <book>
    #   - published: content/published/books/<book>/chapters/<file>.txt → parents[1] = <book>
    # All three layouts have the same parents[1] semantics (the book dir).
    bucket_root = chapter.path.parents[1]
    # Defense-in-depth: confirm the resolved bucket_root really sits under one
    # of the canonical roots. A literal-path resolution outside these roots
    # would emit files in the wrong place; better to fail loud here.
    valid_root_ancestors = {"library", "drafts", "books"}  # 'books' under published/
    if bucket_root.parent.name not in valid_root_ancestors:
        sys.exit(
            f"ERROR: resolved chapter is not under a canonical root.\n"
            f"  bucket_root={bucket_root}\n"
            f"  bucket_root.parent.name={bucket_root.parent.name!r}\n"
            f"  Expected one of: {sorted(valid_root_ancestors)} (which means the\n"
            f"  chapter must live at content/drafts/<book>/chapters/, content/\n"
            f"  published/books/<book>/chapters/, or the legacy content/podcast/\n"
            f"  library/<category>/<book>/chapters/).\n"
            f"  This usually means a literal-path resolution outside the canonical\n"
            f"  layout. Move the chapter to one of the supported roots."
        )

    ep_num = c.get("episode_number") or chapter.chapter_number or next_episode_number(bucket_root)
    slug = c.get("slug")
    ep_id = f"EP{ep_num:02d}-{slug}"

    chapter_text = chapter.path.read_text(encoding="utf-8")

    # Word-count band check — surfaces collisions with NotebookLM's Audio Overview limits
    # at extract time, not at build time. See content/podcast/.skill/handbook/notebooklm-best-practices.md §3.
    word_count = len(chapter_text.split())
    band_warnings: list[str] = []
    # Soft warning fires at 9,500 words (above this NotebookLM starts to
    # summarize aggressively); hard refuse from build_episode_txt.py is at
    # CHAPTER_WORD_MAX_HARD (currently 12,000 post-2026-05-24 bump for the
    # `extended` tier). Authors get 2.5k words of headroom between the soft
    # warning and the hard refuse to decide whether to trim or accept.
    if word_count > 9500:
        band_warnings.append(
            f"  WARN: chapter is {word_count} words — over the 9,500 word soft ceiling.\n"
            f"        NotebookLM starts summarizing aggressively past this point.\n"
            f"        build_episode_txt.py HARD-refuses chapters > 12,000 words.\n"
            f"        Paths: (a) refine the chapter file ({chapter.path.name}) in place\n"
            f"        down to ≤9,500 words; (b) split into two derivative chapters\n"
            f"        with distinct slugs; (c) accept the summarization tradeoff —\n"
            f"        appropriate for `extended` tier dense doctrinal chapters where\n"
            f"        density matters more than precise length."
        )
    elif word_count > 4500 and c.get("length_target") != "longer":
        band_warnings.append(
            f"  WARN: chapter is {word_count} words but length_target is "
            f"{c.get('length_target')!r}. Consider length_target: longer."
        )
    elif word_count < 500:
        band_warnings.append(
            f"  WARN: chapter is {word_count} words — under the 500 word floor. "
            f"Hosts will resort to filler."
        )

    # 1. Chapter copy → content/podcast/<bucket>/chapters/ch##[a-z]?-<slug>.txt
    # Bug X4 (2026-05-21): always write back to the SAME filename we resolved
    # from. Earlier this rebuilt the path as f"ch{ch_num:02d}-{slug}.txt", which
    # silently DROPPED the letter suffix that Phase 0d uses on split-from-same-
    # source-chapter episodes (e.g., ch14b- when one source chapter produced 2
    # episodes). The renormalized path created a duplicate chapter file
    # (ch14- alongside the canonical ch14b-), which then made build_episode_txt
    # fail with "multiple chapter files match slug". Solution: write to
    # chapter.path verbatim — single canonical filename, no duplicate.
    chapter_out = chapter.path

    # 2. Bundle scaffolding → _system/episode-drafts/EP##-<slug>/
    draft_dir = bucket_root / "_system" / "episode-drafts" / ep_id

    written: list[Path] = []
    skipped: list[Path] = []

    # Chapter is copied verbatim (no transformation) — this IS the SOURCE upload.
    write_if_needed(chapter_out, chapter_text, force, written, skipped)

    write_if_needed(draft_dir / "00-framing.md", render_framing(c, chapter, ep_num), force, written, skipped)
    write_if_needed(draft_dir / "02-key-passages.md", render_key_passages(c, chapter), force, written, skipped)
    write_if_needed(draft_dir / "03-context-pack.md", render_context_pack(c, chapter), force, written, skipped)
    write_if_needed(draft_dir / "04-discussion-spine.md", render_discussion_spine(c, chapter), force, written, skipped)
    write_if_needed(draft_dir / "99-show-notes.md", render_show_notes(c, chapter, ep_num), force, written, skipped)

    # If contract was stub-generated, persist it so the user can edit it.
    if c.path is None:
        stub_dest = contract_path_for(chapter)
        # Re-emit a YAML representation of the stub (best-effort, simple).
        stub_yaml = render_stub_contract_yaml(c.raw)
        write_if_needed(stub_dest, stub_yaml, force, written, skipped)
        print(f"NOTE: no contract found — wrote stub at {stub_dest.relative_to(REPO_ROOT)}. Edit it and re-run with --force.")

    print(f"\nExtracted EP{ep_num:02d}-{slug} from {chapter.path.name}")
    print(f"  Source bucket: {bucket}")
    print(f"  Episode draft: {draft_dir.relative_to(REPO_ROOT)}")
    print(f"  Chapter words: {word_count}")
    print(f"  Files written: {len(written)}")
    print(f"  Files unchanged: {len(skipped)}")
    if band_warnings:
        print()
        for w in band_warnings:
            print(w)
    if written:
        print("\n  Written:")
        for p in written:
            print(f"    {p.relative_to(REPO_ROOT)}")
    if skipped:
        print("\n  Unchanged (deterministic re-render):")
        for p in skipped:
            print(f"    {p.relative_to(REPO_ROOT)}")
    print(f"\nNext: build the customize-prompt episode txt:")
    print(f"  python3 scripts/podcast/build_episode_txt.py {bucket_root.relative_to(REPO_ROOT)} {ep_id}")


def render_stub_contract_yaml(stub: dict[str, Any]) -> str:
    """Minimal YAML emitter for the stub contract. Only handles the schema we use."""
    out = ["# chapter-contract.yml — auto-generated stub. Edit and re-run extract_chapter.py --force.", ""]
    for k, v in stub.items():
        if v is None:
            out.append(f"{k}: null")
        elif isinstance(v, bool):
            out.append(f"{k}: {'true' if v else 'false'}")
        elif isinstance(v, (int, float)):
            out.append(f"{k}: {v}")
        elif isinstance(v, list):
            if not v:
                out.append(f"{k}: []")
            else:
                out.append(f"{k}:")
                for item in v:
                    out.append(f"  - {item}")
        elif isinstance(v, dict):
            if not v:
                out.append(f"{k}: {{}}")
            else:
                out.append(f"{k}:")
                for kk, vv in v.items():
                    if vv is None:
                        out.append(f"  {kk}: null")
                    elif isinstance(vv, list):
                        if not vv:
                            out.append(f"  {kk}: []")
                        else:
                            out.append(f"  {kk}:")
                            for item in vv:
                                out.append(f"    - {item}")
                    else:
                        out.append(f"  {kk}: {vv}")
        else:
            s = str(v)
            if "\n" in s or ":" in s or s.startswith(("'", '"')):
                out.append(f'{k}: "{s}"')
            else:
                out.append(f"{k}: {s}")
    return "\n".join(out) + "\n"


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Extract a chapter into a deterministic NotebookLM Audio Overview bundle.",
    )
    ap.add_argument("chapter_ref", help="Chapter path, slug, or basename (e.g. ch01-man).")
    ap.add_argument("--contract", type=Path, default=None,
                    help="Explicit contract file. Default: _workspace/<category>/<book>/chapter-contracts/<slug>.yml")
    ap.add_argument("--force", action="store_true",
                    help="Overwrite existing bundle files even if they differ.")
    args = ap.parse_args()

    chapter = resolve_chapter_ref(args.chapter_ref)
    c = load_contract(args.contract, chapter)
    validate_contract(c, chapter)
    lint_contract_meta_prose(c)
    emit_bundle(chapter, c, args.force)


if __name__ == "__main__":
    main()
