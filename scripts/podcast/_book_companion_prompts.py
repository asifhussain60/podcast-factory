"""_book_companion_prompts.py — the model-facing half of Companion-card generation.

Everything a model reads or writes for the Companion lives here: the three lane
prompts, the ranking prompt, and the tolerant parsers for what comes back. The
sibling ``_book_companion`` keeps the half no model is trusted with — the
guardrails, the balance rule, and the on-disk write.

Split out of ``_book_companion`` (2026-07-19) to keep that module under the
DR-005 line cap, the same way ``_arabic_coverage`` was split out of
``_translation_edition``. The dependency runs one way (companion -> prompts), so
prompt wording can change without touching a gate.
"""

from __future__ import annotations

import json
import re
from typing import Any

# Each lane over-produces so the ranking pass has something to choose between.
CANDIDATES_PER_LANE = 10
# Prompt budgets. A transcript is chatty and a chapter is dense; both are trimmed
# so a long chapter cannot push its own prose out of the model's view.
TRANSCRIPT_CHARS = 9000
CHAPTER_CHARS = 9000

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.+?)\s*```", re.S)


def _json_array(raw: str) -> Any:
    """The first JSON array in a model reply, ignoring a code fence or stray prose."""
    text = (raw or "").strip()
    fence = _JSON_FENCE_RE.search(text)
    if fence:
        text = fence.group(1)
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except Exception:
        return None


def parse_cards(raw: str) -> list[dict[str, Any]]:
    """Parse a model's JSON array of cards. Junk yields no cards, never an exception."""
    data = _json_array(raw)
    return [c for c in data if isinstance(c, dict)] if isinstance(data, list) else []


def rank_order(raw: str, n: int) -> list[int]:
    """The ranking as valid candidate indices; an unusable reply keeps input order."""
    data = _json_array(raw)
    order = [int(i) for i in data if isinstance(i, (int, float)) and 0 <= int(i) < n] if isinstance(data, list) else []
    seen: set[int] = set()
    deduped = [i for i in order if not (i in seen or seen.add(i))]
    return deduped or list(range(n))


def corpus_line(atom: dict[str, Any], text: str) -> str:
    """One corpus line for a lane prompt, labeled where the prose alone hides the point.

    An etymology atom's prose reads as free text with the term itself in a sibling
    field, so an unlabeled line cannot be cited accurately.
    """
    body = atom.get("body") if isinstance(atom.get("body"), dict) else {}
    if atom.get("type") == "etymology" and body.get("term"):
        root = body.get("root_transliteration") or ""
        return f"ETYMOLOGY — {body['term']}" + (f" (root {root})" if root else "") + f": {text}"
    return f"{atom.get('type', 'source')}: {text}"


_LANE_RULES = """
Rules that apply to EVERY card:
- `body` is what you would SAY OUT LOUD: 25-110 words, plain modern English, no headings, no lists.
- `quote` MUST be copied character-for-character from the chapter text below, or omitted entirely.
  It is what the reader highlights on screen. A near-miss is worse than no quote.
- `anchor` is a short label for the card (a few words), not a sentence.
- Never write Arabic script unless you are copying it from the material given to you.
- Add nothing from outside the material provided. No outside authorities, no invented history.
- Return ONLY a JSON array. Each element: {"kind": ..., "anchor": ..., "body": ..., "quote": ...}

The kinds, and what each is for:
- "analogy"     — a comparison from ordinary life that makes the passage click.
- "explanation" — a plain-language unpacking of an idea the passage assumes you know.
- "question"    — a question to pose to the person you are reading with. One sentence.
- "note"        — a short aside: a connection, a caution, something easy to miss.
- "etymology"   — the root of a key term and how its original sense fits this passage.
"""


def chapter_lane_prompt(title: str, prose: str) -> str:
    """Lane 1 — what the chapter's own text yields."""
    return f"""You are preparing private teaching cards for someone about to read a chapter of a
classical Islamic dialogue aloud to a friend. The cards are for the READER, not for the book.

Produce up to {CANDIDATES_PER_LANE} cards drawn from the chapter's own text — the ideas a modern reader
will stumble on, and the comparisons that unlock them. Favour explanations and questions here;
another pass handles the podcast and the reference corpus.
{_LANE_RULES}
CHAPTER "{title}"
{prose[:CHAPTER_CHARS]}
"""


def podcast_lane_prompt(title: str, prose: str, transcript: str, ref: str) -> str:
    """Lane 2 — what two people talking it through found that the text alone does not give."""
    return f"""Below is the transcript of a recorded discussion ({ref}) covering the same material as the
chapter that follows. Two hosts talk it through: they reach for analogies, they push back, they
surface what a listener finds hard.

Harvest up to {CANDIDATES_PER_LANE} cards from what the DISCUSSION contributes — the analogies the hosts
found, the objections they raised, the plain restatements they landed on. Skip anything that is
merely the chapter read back. Every card must still stand on the chapter text.
{_LANE_RULES}
DISCUSSION TRANSCRIPT ({ref})
{transcript[:TRANSCRIPT_CHARS]}

CHAPTER "{title}" (the `quote` must come from HERE, not from the transcript)
{prose[:CHAPTER_CHARS]}
"""


def corpus_lane_prompt(title: str, prose: str, corpus: str) -> str:
    """Lane 3 — what the reference corpus makes possible and the chapter alone does not."""
    return f"""Below is a reliable reference corpus — verses, hadith, doctrinal statements, and word roots —
followed by a chapter that draws on the same material.

Produce up to {CANDIDATES_PER_LANE} cards that the corpus makes possible and the chapter alone does not:
above all "etymology" cards (a key term's root and how its original sense lights up this passage)
and "explanation" cards grounded in a corpus entry. Every claim must trace to a corpus line below.
If the corpus offers nothing for a term, say nothing about it — do not reconstruct a root.
{_LANE_RULES}
REFERENCE CORPUS
{corpus or "(none)"}

CHAPTER "{title}"
{prose[:CHAPTER_CHARS]}
"""


def judge_prompt(title: str, cards: list[dict[str, Any]], *, target_max: int, ceiling: int) -> str:
    """The holistic pick: rank the pooled candidates before the balance rule trims them."""
    listing = "\n".join(
        f"[{i}] ({c.get('kind')}) {c.get('anchor') or ''} — {str(c.get('body'))[:220]}" for i, c in enumerate(cards)
    )
    return f"""Below are candidate teaching cards for one chapter, pooled from three passes. They overlap and
they vary in value. Rank them for a reader who will use them while reading the chapter aloud.

Judge on: does it teach something the chapter itself does not hand you; would a listener remember it;
is it concrete rather than abstract; and is it distinct from the others. Demote restatements of the
chapter, vague praise, and near-duplicates.

Balance matters as much as individual quality: the chosen set should carry a genuine spread of kinds,
and no single kind should dominate (a hard cap of {ceiling} per kind applies after your ranking).

Return ONLY a JSON array of the candidate indices, best first, e.g. [7,2,11,0]. Include every index
worth keeping — at least {target_max} if that many are worth it. Omit the ones you would drop.

CHAPTER: {title}

CANDIDATES
{listing}
"""
