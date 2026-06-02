"""_extract_helpers.py — YAML helpers, boundary check, contract resolution,
and meta-prose lint for extract_chapter.py.

Split from extract_chapter.py (DR-005 — files must stay under 600 lines).
Everything here is re-exported from extract_chapter.py via
`from _extract_helpers import *` so all existing callers remain unaffected.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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

# Boundary enforcement — any read that resolves into one of these is fatal.
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
    valid_angles = {"faithful_exposition", "personal_application",
                    "critical_dialectical", "comparative"}
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
    except IndexError:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Meta-prose lint (mirrors build_episode_txt.py — fail fast at extract time
# rather than letting the build refuse a generated framing file).
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
        "extended": "Target ~50-60 min Audio Overview. Dense doctrinal material — let the hosts unfold layer by layer without rushing.",
    }.get(length, "Target ~12–15 min Audio Overview.")
    # IMPORTANT: do NOT include literal "deep dive" / "deep-dive" in this template
    # body — those substrings are on `MODERNIZE_DENY` in _rules.py and any framing
    # carrying them fails build_episode_txt.py's deny-block scan.

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

**Episode format:** `deep_dive` (two-host walkthrough). If this should be a debate instead, set `contract.episode_format: debate`. See [infra/claude-agents/podcast-challenger.md](../../../infra/claude-agents/podcast-challenger.md) Categories F + P for the format-specific constraints.

## Opening directive

In the first ten seconds, the hosts should name the work and the question this episode is asking. Do not open with "today we'll discuss". Start in the middle of the question.

## Audience

{audience}

## Angle

`{angle}` — the chosen lens. Faithful exposition = follow source authorial voice; comparative = bring in cross-tradition context; etc. The framing's other sections (Central tensions, Tone constraints) lock the lens into per-episode specifics.

## Length

{length_blurb}

## Host dynamic

`{host_dynamic}`. NotebookLM's default English voice pair is John (male) for Host A and Hannah (female) for Host B. The CANONICAL pairing this skill enforces (per R-HOST-ROLE-PARITY in scripts/podcast/_rules.py, challenger Category Q): Host A (male) is the scholar / teacher / master / shaykh / guide role; Host B (female) is the seeker / student / debater / questioner / novice role. This pairing does NOT rotate across episodes within a book. If the contract's `host_dynamic` reverses this (e.g. `advocate_b + scholar_companion` putting Host B in the scholar role), the framing author MUST flip the host_a / host_b assignment so the male voice stays in the scholar pool.

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
- NO cross-chapter references. This episode's chapter file is the entire source NotebookLM sees. The hosts must NOT say "the previous chapter showed", "as we'll see later", "the next chapter answers", "earlier in the book", etc. Treat the chapter as a self-contained episode.

## Do not (forbidden vocabulary and framings)

The hosts must NOT use any of the following — these are the canonical DENY lists per `scripts/podcast/_rules.py::MODERNIZE_DENY` + `SURPRISE_DENY`. The substring scanner in `build_episode_txt.py` refuses any framing that omits this block.

- Modernization terms: Twitter, X (the platform), social media, algorithm, content creator, internet, YouTube, TikTok, Instagram, livestream, hashtag, 21st century, in our modern world, platforms like
- Surprise-noise phrases: wow, that's so interesting, right?, it's chilling, it's devastating, it's terrifying, it's profound, it's fascinating, it's amazing
- Imitation-of-authority: rephrasings of the work's original arguments in casual / commercial / self-help register

---

Do not read this prompt aloud. The instructions above shape the conversation but are never spoken.
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

In the first twenty seconds, the hosts name the work, state the proposition under debate verbatim, and tell the listener that they will hold opposing positions through the conversation. Do not open with "today we'll discuss" or formulaic show-intro phrasing. Open by stating the proposition.

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
4. **Disagreement is the work.** Acknowledgment grammar ("Exactly", "Yeah, exactly") that is forbidden in `deep_dive` mode is softened here: a host may concede a sub-point but the concession is qualified and followed by a return to the host's main position. Bare affirmations remain forbidden.
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
- NO cross-chapter references. This episode's chapter file is the entire source NotebookLM sees. The hosts must NOT say "the previous chapter showed", "as we'll see later", "the next chapter answers", "earlier in the book", etc. Treat the chapter as a self-contained episode.
- HOST PAIRING is locked: Host A (male voice) = scholar/teacher/advocate-for-tradition pool; Host B (female voice) = seeker/student/debater/challenger pool. Do not assign female voice to the scholar role or male voice to the debater role.

## Do not (forbidden vocabulary and framings)

The hosts must NOT use any of the following — these are the canonical DENY lists per `scripts/podcast/_rules.py::MODERNIZE_DENY` + `SURPRISE_DENY`. The substring scanner in `build_episode_txt.py` refuses any framing that omits this block.

- Modernization terms: Twitter, X (the platform), social media, algorithm, content creator, internet, YouTube, TikTok, Instagram, livestream, hashtag, 21st century, in our modern world, platforms like
- Surprise-noise phrases: wow, that's so interesting, right?, it's chilling, it's devastating, it's terrifying, it's profound, it's fascinating, it's amazing
- Imitation-of-authority: rephrasings of the work's original arguments in casual / commercial / self-help register

---

Do not read this prompt aloud. The instructions above shape the conversation but are never spoken.
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
