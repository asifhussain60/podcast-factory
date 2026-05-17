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

CHAPTER REF RESOLUTION (first match wins)

  1. Literal path (absolute or repo-relative) → used as-is.
  2. content/babu-memoir/chapters/<ref>.txt        (memoir sanctioned crossing)
  3. content/podcast/*/chapters/<ref>.txt          (any book chapter)

CONTRACT RESOLUTION

  1. --contract <path> (explicit)
  2. content/podcast/<source-slug>/chapter-contracts/<chapter-slug>.yml
  3. Falls back to a generated stub at the location above, with [TODO] markers.

OUTPUT (per contract.source_type)

  memoir:        content/podcast/from-memoir/...
  book-chapter:  content/podcast/<book_slug>/...
  article:       content/podcast/<book_slug>/...

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

BOUNDARY (SKILL.md §9 v2)

  This script reads ONLY:
    - content/babu-memoir/chapters/*.txt  (sanctioned crossing point)
    - content/podcast/**                  (this skill's workspace)
  It MUST NOT read content/babu-memoir/reference/, _system/, scratchpad/,
  voice-fingerprint*, or master-context*. The adapter is enforced below
  via PROHIBITED_PATHS.
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
MEMOIR_CHAPTERS = CONTENT_DIR / "babu-memoir" / "chapters"
PODCAST_DIR = CONTENT_DIR / "podcast"
HANDBOOK_DIR = PODCAST_DIR / "_handbook"

# Boundary enforcement — any read that resolves into one of these is fatal.
# Wildcards are simple string `startswith` matches against the resolved path
# relative to CONTENT_DIR.
PROHIBITED_PATH_PREFIXES = [
    "babu-memoir/reference",
    "babu-memoir/_system",
    "babu-memoir/scratchpad",
]
PROHIBITED_NAME_PATTERNS = [
    re.compile(r"^voice-fingerprint", re.IGNORECASE),
    re.compile(r"^master-context", re.IGNORECASE),
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
    """Refuse to read any path forbidden by SKILL.md §9 v2."""
    try:
        rel = p.resolve().relative_to(CONTENT_DIR.resolve())
    except ValueError:
        return  # outside content/ — caller's problem, not the boundary's
    rel_str = str(rel).replace("\\", "/")
    for prefix in PROHIBITED_PATH_PREFIXES:
        if rel_str.startswith(prefix):
            sys.exit(
                f"BOUNDARY VIOLATION: refused to read {rel_str}\n"
                f"  SKILL.md §9 v2 prohibits podcast access to journal {prefix}/. "
                f"Only content/babu-memoir/chapters/*.txt is sanctioned."
            )
    for pat in PROHIBITED_NAME_PATTERNS:
        if pat.match(p.name):
            sys.exit(
                f"BOUNDARY VIOLATION: refused to read {p.name}\n"
                f"  SKILL.md §9 v2 prohibits podcast access to {p.name}."
            )


# ─────────────────────────────────────────────────────────────────────────────
# Chapter ref resolution
# ─────────────────────────────────────────────────────────────────────────────


CH_PREFIX_RE = re.compile(r"^ch(\d+)-(.+)$")


@dataclass
class ResolvedChapter:
    path: Path
    source_bucket: str  # "from-memoir" or a book slug
    chapter_number: int | None
    chapter_slug: str   # the slug after ch## (e.g. "man" from "ch01-man")


def resolve_chapter_ref(ref: str) -> ResolvedChapter:
    """Resolve a chapter ref string to a (path, source-bucket, num, slug)."""

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
        # Determine bucket from path
        try:
            rel = literal.relative_to(CONTENT_DIR)
            parts = rel.parts
            if parts[0] == "babu-memoir":
                bucket = "from-memoir"
            elif parts[0] == "podcast" and len(parts) >= 2:
                bucket = parts[1]
            else:
                bucket = parts[0]
        except ValueError:
            bucket = "from-memoir"  # fallback
        num, slug = parse_chapter_filename(literal)
        return ResolvedChapter(literal, bucket, num, slug)

    # 2. Memoir chapters (sanctioned crossing)
    memoir_candidate = MEMOIR_CHAPTERS / f"{ref}.txt"
    if memoir_candidate.exists():
        assert_boundary_safe(memoir_candidate)
        num, slug = parse_chapter_filename(memoir_candidate)
        return ResolvedChapter(memoir_candidate, "from-memoir", num, slug)

    # 3. Any podcast book chapters
    for book_chapters in sorted(PODCAST_DIR.glob("*/chapters")):
        cand = book_chapters / f"{ref}.txt"
        if cand.exists():
            assert_boundary_safe(cand)
            num, slug = parse_chapter_filename(cand)
            bucket = cand.parents[1].name
            return ResolvedChapter(cand, bucket, num, slug)

    sys.exit(
        f"ERROR: could not resolve chapter ref {ref!r}.\n"
        f"  Tried:\n"
        f"    {literal}\n"
        f"    {memoir_candidate}\n"
        f"    {PODCAST_DIR}/*/chapters/{ref}.txt\n"
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
    return PODCAST_DIR / chapter.source_bucket / "chapter-contracts" / f"{chapter.chapter_slug}.yml"


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
        "source_type": "memoir" if chapter.source_bucket == "from-memoir" else "book-chapter",
        "book_slug": None if chapter.source_bucket == "from-memoir" else chapter.source_bucket,
        "episode_number": chapter.chapter_number,
        "title": "[TODO] Episode title",
        "audience": "[TODO] Concrete audience description.",
        "angle": "personal_application",
        "host_dynamic": "curious_mind + scholar_companion",
        "host_dynamic_custom": None,
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
            f"  See content/podcast/_handbook/chapter-contract.template.yml for the full schema."
        )
    if c.get("slug") != chapter.chapter_slug:
        sys.exit(
            f"ERROR: contract.slug ({c.get('slug')!r}) does not match "
            f"chapter slug ({chapter.chapter_slug!r}).\n"
            f"  Under the 1:1 chapter ↔ episode mapping (SKILL.md §0), these must match exactly."
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

## Opening directive

In the first ten seconds, the hosts should name the work and the question this episode is asking. Do not open with "today we'll discuss". Start in the middle of the question.

## Audience

{audience}

## Angle

`{angle}` — see content/podcast/_handbook/source-distillation.md for what this lens commits the hosts to.

## Length

{length_blurb}

## Host dynamic

`{host_dynamic}`. See content/podcast/_handbook/two-host-framing.md for default personas.

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

[LLM-FILL — for memoir, this is Babu (Asif), writing for his children. For book chapters, name the author, dates, tradition.]

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
    bucket = chapter.source_bucket if chapter.source_bucket != "from-memoir" else "from-memoir"
    if c.get("source_type") == "book-chapter" and c.get("book_slug"):
        bucket = c.get("book_slug")
    bucket_root = PODCAST_DIR / bucket

    ep_num = c.get("episode_number") or chapter.chapter_number or next_episode_number(bucket_root)
    slug = c.get("slug")
    ep_id = f"EP{ep_num:02d}-{slug}"

    chapter_text = chapter.path.read_text(encoding="utf-8")

    # Word-count band check — surfaces collisions with NotebookLM's Audio Overview limits
    # at extract time, not at build time. See content/podcast/_handbook/notebooklm-best-practices.md §3.
    word_count = len(chapter_text.split())
    band_warnings: list[str] = []
    if word_count > 5500:
        band_warnings.append(
            f"  WARN: chapter is {word_count} words — over the 5,500 word ceiling.\n"
            f"        NotebookLM will summarize away content past this. Canon says split.\n"
            f"        build_episode_txt.py will REFUSE this chapter.\n"
            f"        Paths: (a) refine the chapter file ({chapter.path.name}) in place\n"
            f"        down to ≤4,500 words; (b) split into two derivative chapters\n"
            f"        with distinct slugs; (c) explicitly raise CHAPTER_WORD_MAX_HARD\n"
            f"        in build_episode_txt.py (against canon — only do this knowingly)."
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

    # 1. Chapter copy → content/podcast/<bucket>/chapters/ch##-<slug>.txt
    ch_num = chapter.chapter_number or ep_num
    chapter_out = bucket_root / "chapters" / f"ch{ch_num:02d}-{slug}.txt"

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
                    help="Explicit contract file. Default: content/podcast/<bucket>/chapter-contracts/<slug>.yml")
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
