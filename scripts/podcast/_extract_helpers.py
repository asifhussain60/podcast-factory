"""_extract_helpers.py — Bundle rendering functions and re-exports for extract_chapter.py.

Three-file split (DR-005 — files must stay under 600 lines):
  _extract_yaml.py     — minimal YAML reader (_parse_scalar, load_yaml)
  _extract_contract.py — boundary check, ResolvedChapter, Contract, validation, meta-prose lint
  _extract_helpers.py (this) — framing/bundle rendering + re-exports

Everything is re-exported from extract_chapter.py via `from _extract_helpers import *`
so all existing callers remain unaffected.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from _extract_contract import (
    CH_PREFIX_RE,
    CONTRACT_LINTED_FIELDS,
    CONTRACT_META_PROSE_REGEX,
    CONTRACT_META_PROSE_TELLS,
    PROHIBITED_PATH_PREFIXES,
    REQUIRED_FIELDS,
    Contract,
    ResolvedChapter,
    assert_boundary_safe,
    contract_path_for,
    lint_contract_meta_prose,
    load_contract,
    stub_contract,
    validate_contract,
)
from _extract_yaml import load_yaml

# Re-export everything so callers that do `from _extract_helpers import X` keep working.
__all__ = [
    "load_yaml",
    "PROHIBITED_PATH_PREFIXES",
    "assert_boundary_safe",
    "CH_PREFIX_RE",
    "ResolvedChapter",
    "REQUIRED_FIELDS",
    "Contract",
    "contract_path_for",
    "load_contract",
    "stub_contract",
    "validate_contract",
    "CONTRACT_META_PROSE_TELLS",
    "CONTRACT_META_PROSE_REGEX",
    "CONTRACT_LINTED_FIELDS",
    "lint_contract_meta_prose",
    "fmt_list",
    "render_framing",
    "render_key_passages",
    "render_context_pack",
    "render_discussion_spine",
    "render_show_notes",
]


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
            "For each term below: say it ONCE using the phonetic form given — never say the "
            "original spelling and the phonetic form back-to-back. If a Substitute is listed, "
            "use the English substitute and skip the Arabic term entirely.\n\n"
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
    moves_a_block = (
        fmt_list(moves_a) if moves_a else "  - [LLM-FILL — quotes, passages, and traditions Host A draws on]\n"
    )
    moves_b_block = (
        fmt_list(moves_b) if moves_b else "  - [LLM-FILL — quotes, passages, and traditions Host B draws on]\n"
    )

    phonetics = c.get("phonetic_overrides") or {}
    if phonetics:
        rows = "".join(f"  - **{term}** — {respelling}\n" for term, respelling in phonetics.items())
        pronunciation_block = (
            "For each term below: say it ONCE using the phonetic form given — never say the "
            "original spelling and the phonetic form back-to-back. If a Substitute is listed, "
            f"use the English substitute and skip the Arabic term entirely.\n\n{rows}"
        )
    else:
        pronunciation_block = (
            "[LLM-FILL — list every non-English term with respelling and gloss, or set contract.phonetic_overrides.]"
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

**Host A — {host_a.get("role", "[LLM-FILL role]")}.**
Position: {host_a.get("position", "[LLM-FILL position]")}

Source moves available to Host A:
{moves_a_block}
**Host B — {host_b.get("role", "[LLM-FILL role]")}.**
Position: {host_b.get("position", "[LLM-FILL position]")}

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


def _build_apparatus_table(book_dir: Path) -> str:
    """Build the ## Name and Title Preservation Table section from name-aliases.yml.

    Returns an empty string when name-aliases.yml is absent (defensive).
    """
    aliases_path = book_dir / "_system" / "name-aliases.yml"
    if not aliases_path.exists():
        return ""
    try:
        data = load_yaml(aliases_path.read_text(encoding="utf-8"))
    except Exception:
        return ""
    if not isinstance(data, dict):
        return ""

    rows: list[tuple[str, str, str, str, str]] = []  # (orig, category, written, audio_label, first_use)
    for section_key, category_label in (
        ("figures", "Person"),
        ("book_titles", "Book Title"),
        ("concept_words", "Concept Term"),
    ):
        section = data.get(section_key) or {}
        if not isinstance(section, dict):
            continue
        for _key, entry in section.items():
            if not isinstance(entry, dict):
                continue
            first_mention = entry.get("first_mention") or ""
            rotation = entry.get("rotation") or []
            audio_label = rotation[0] if rotation else "—"
            # Derive transliteration from the start of first_mention (up to first comma).
            orig_part = first_mention.split(",")[0].strip() if first_mention else "—"
            category = entry.get("category") or category_label
            rows.append((orig_part, category, first_mention or "—", audio_label, "first mention"))

    if not rows:
        return ""

    header = "## Name and Title Preservation Table\n\n"
    table_header = "| Original / Transliteration | Category | Written Form | Audio Label | First Audio Use |\n"
    separator = "|---|---|---|---|---|\n"
    table_rows = "".join(
        f"| {orig} | {cat} | {written} | {audio} | {first} |\n" for orig, cat, written, audio, first in rows
    )
    return header + table_header + separator + table_rows


def render_show_notes(c: Contract, chapter: ResolvedChapter, ep_num: int) -> str:
    sn = c.get("show_notes") or {}
    # The LLM contract writer sometimes emits show_notes as a bullet LIST instead
    # of the {blurb, related_episodes, references} dict the renderer expects.
    # Coerce a list into the dict (the bullets become references) so extraction
    # never crashes on the drift and no content is lost (2026-06-15).
    if isinstance(sn, list):
        sn = {"references": [str(x) for x in sn if str(x).strip()]}
    elif not isinstance(sn, dict):
        sn = {}
    blurb = sn.get("blurb") or "[LLM-FILL — 1–2 sentence episode description]"
    related = sn.get("related_episodes") or []
    refs = sn.get("references") or []
    title = c.get("title")
    none_line = "  - [none]" + "\n"
    related_block = fmt_list(related) if related else none_line
    refs_block = fmt_list(refs) if refs else none_line

    # F25: apparatus table — derive book_dir from chapter path (chapters/ is one level below book root).
    book_dir = chapter.path.parents[1]
    apparatus_section = _build_apparatus_table(book_dir)
    apparatus_block = f"\n{apparatus_section}\n" if apparatus_section else ""

    return f"""# Show notes — EP{ep_num:02d}

**Title:** {title}

**Blurb:** {blurb}

**Length estimate:** see contract.length_target ({c.get("length_target")})
{apparatus_block}
## Related episodes

{related_block}
## References

{refs_block}"""
