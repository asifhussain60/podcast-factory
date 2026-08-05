#!/usr/bin/env python3
"""_pronunciation_block.py — compile a framing's `## Pronunciation` block.

Until 2026-08-01 that block was free text an LLM wrote from a prompt that
literally asked for `- TermA: English-name-or-plain-translit`, and the only gate
checked its punctuation. So `arkan: the pillars` — a translation sitting in the
slot the block's own instruction calls a phonetic — passed every check and
shipped, and the hosts, told to "say each term ONCE using its phonetic form" and
handed a translation, said "Archon". Five of six episodes shipped that way.

Here the model no longer decides what to SAY. It still decides which terms need
help — that judgement is genuinely per-episode and the model reads the chapter —
but every value is resolved by ``knowledge/term_render.render_for_audio``, the
one deterministic ladder (book override > loanword > exonym > confirmed ledger
form > gloss > plain transliteration) the whole repo already shares with the
probe and the ElevenLabs dictionary.

Three properties matter and are pinned by tests:

  - **Nothing is invented.** A term the ladder can only spell back to us
    produces NO entry, because "say arkan as arkan" is not guidance. Those terms
    are reported to the caller so the probe can settle them by ear.
  - **Nothing is asserted about a term the episode never mentions.** The
    candidate set is filtered against the chapter the listener actually hears.
  - **It degrades to the status quo.** No candidates, no glossary, no overrides
    -> the authored block is left exactly as written. A book that has never had
    an override table builds byte-identically to before.

That last property is only safe in company: when this module declines to compile,
the authored block still faces ``R-PRONUNCIATION-RENDER`` in
``_validators_framing``, which rejects a translation sitting in the value slot.
The degrade defers to that gate rather than bypassing it — compiling replaces a
bad value, and the gate refuses one nobody replaced.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE / "knowledge") not in sys.path:
    sys.path.insert(0, str(_HERE / "knowledge"))

import term_render  # noqa: E402
from pronunciation_ledger import normalize_key  # noqa: E402

# The heading the framing carries. `## Pronunciation hooks` is an accepted
# legacy variant (R-CANONICAL-FRAMING-SECTIONS names both).
_SECTION_RE = re.compile(r"^(##\s+Pronunciation\b.*?)$([\s\S]*?)(?=^##\s+|\Z)", re.MULTILINE)

# An authored entry: `- term: value` (the value is discarded — only the TERM is
# read, as the model's opinion about what needs help).
_ENTRY_RE = re.compile(r"^\s*-\s+([^:\n]{1,60}?)\s*:\s*(.+?)\s*$", re.MULTILINE)

# The anti-doubling instruction. Must satisfy _validator_constants
# .ANTI_DOUBLING_INSTRUCTION_RE, which keys on "say each term once".
INSTRUCTION = (
    "Say each term ONCE, using the form given here and nothing else. "
    "Never say the original spelling and the form given here back-to-back."
)


def _iter_candidate_terms(book_dir: Path, authored_block: str) -> list[str]:
    """Every term worth an entry, in a stable order, deduped by lookup key.

    Three sources, and the union is deliberate: the override table is the human's
    list, the glossary is the pipeline's, and the authored block is the model's
    reading of THIS chapter. Merging them means the model can still surface a
    term nobody catalogued without being trusted to say what it sounds like.
    """
    seen: set[str] = set()
    out: list[str] = []

    def _add(term: str) -> None:
        term = term.strip().strip("*_`")
        if not term or len(term) > 60:
            return
        key = normalize_key(term)
        if not key or key in seen:
            return
        seen.add(key)
        out.append(term)

    for term, _value in term_render.parse_book_override_table(book_dir):
        _add(term)

    try:
        from pronunciation_compiler import load_glossary_entries

        for entry in load_glossary_entries(book_dir):
            _add(str(entry.get("transliteration") or entry.get("phonetic") or ""))
    except Exception:
        pass  # a missing/unparseable glossary must never break a build

    for m in _ENTRY_RE.finditer(authored_block):
        _add(m.group(1))

    return out


def _appears_in(term: str, chapter_norm: str) -> int:
    """Offset of the term's first appearance in the chapter, or -1.

    Matched on a whitespace-normalised, case-folded copy so a term broken across
    a line wrap still counts. Letters and digits block on both sides, so ``nass``
    does not match inside ``nassab`` — but a HYPHEN is a boundary rather than a
    blocker, because the prose writes ``ruh al-nutq`` and the term is ``nutq``.
    """
    key = normalize_key(term)
    if not key:
        return -1
    pattern = re.compile(r"(?<![a-z0-9])" + re.escape(key) + r"(?![a-z0-9])")
    m = pattern.search(chapter_norm)
    return m.start() if m else -1


def _normalise_for_search(text: str) -> str:
    """Case-folded, whitespace-collapsed, apostrophe-folded copy of the chapter.

    Folds the same hamza/ayn glyphs ``normalize_key`` folds so both sides of the
    comparison agree — otherwise ``ya'sub`` in the table never finds ``yaʿsub``
    in the prose.
    """
    return normalize_key(re.sub(r"\s+", " ", text))


def shadowed_loanwords(book_dir: Path) -> list[str]:
    """Override rows that respell a word the TTS already says correctly.

    Not an error — rung 0 exists precisely so a human can overrule the tables —
    but worth saying out loud, because forcing a respelling onto a loanword is
    the documented cause of "Imam" coming out as "e-Maam" in the 2026-06-12
    render, and a term that was already clean has nothing to gain.
    """
    _exonyms, loanwords = term_render.load_tables()
    out: list[str] = []
    for term, value in term_render.parse_book_override_table(book_dir):
        if term_render.is_withdrawn(value):
            continue  # names a term, asserts no spoken form — nothing to shadow
        key = normalize_key(term)
        bare = key[3:] if key.startswith("al-") else key
        if (key in loanwords or bare in loanwords) and normalize_key(value) != key:
            out.append(f"{term} -> {value}")
    return out


def compile_entries(book_dir: Path, chapter_text: str, authored_block: str) -> tuple[list[tuple[str, str]], list[str]]:
    """Return ``(entries, unresolved)`` for one episode.

    ``entries`` is ``[(term, spoken_form), ...]`` in chapter reading order.
    ``unresolved`` names the terms present in the chapter that the ladder could
    only spell back — real coverage gaps for the probe, not errors.
    """
    overrides = term_render.load_book_overrides(book_dir)
    tables = term_render.load_tables()
    # Book-mined glosses are deliberately NOT consulted. `English (translit)`
    # and `translit (English)` are the same shape, so when the Arabic carries no
    # macron or apostrophe to mark it, the miner guesses direction and can guess
    # backwards: the live text "the vicegerent (khalifa) of the Commander" mines
    # vicegerent -> khalifa, which would tell the hosts to answer an English
    # word with an Arabic one. Every other rung is a lookup in a table somebody
    # curated; this is the one built on a heuristic that can invert meaning, and
    # the cost of dropping it is small — a term the book already glosses inline
    # is one the listener meets glossed anyway.
    try:
        from pronunciation_ledger import load as load_library

        library = load_library()
    except Exception:
        library = None

    chapter_norm = _normalise_for_search(chapter_text)

    scored: list[tuple[int, str, str]] = []
    unresolved: list[str] = []
    for term in _iter_candidate_terms(book_dir, authored_block):
        at = _appears_in(term, chapter_norm)
        if at < 0:
            continue  # never spoken in this episode — no entry to make
        entry = library.lookup(term) if library else None
        ledger_entry = {"phonetic": entry.phonetic, "gloss": entry.gloss, "status": entry.status} if entry else None
        result = term_render.render_for_audio(
            term,
            ledger_entry=ledger_entry,
            book_overrides=overrides,
            tables=tables,
        )
        # A render that merely spells the term back carries no instruction. Say
        # so out loud rather than emitting `- arkan: arkan`.
        #
        # A human override is exempt. `AHL al-HAQQ` folds onto `ahl al-haqq`
        # under the lookup key, so the general test would silently discard a row
        # somebody deliberately typed — and where the term is several words, the
        # capitals are the only thing saying which one takes the stress.
        if result.tier != term_render.TIER_BOOK_OVERRIDE and normalize_key(result.text) == normalize_key(term):
            unresolved.append(term)
            continue
        scored.append((at, term, result.text))

    scored.sort(key=lambda t: (t[0], t[1]))
    return [(term, spoken) for _, term, spoken in scored], unresolved


def render_block(heading: str, entries: list[tuple[str, str]]) -> str:
    """The replacement section text, heading included."""
    lines = [heading.rstrip(), INSTRUCTION]
    lines += [f"- {term}: {spoken}" for term, spoken in entries]
    return "\n".join(lines) + "\n"


def apply_to_framing(
    cleaned: str,
    book_dir: Path | None,
    chapter_text: str | None,
    *,
    char_max: int | None = None,
) -> tuple[str, list[str]]:
    """Replace the framing's `## Pronunciation` body with the compiled block.

    Returns ``(framing, unresolved)``. Every resolvable term gets its entry, and
    the block is NEVER shortened to fit the Customize ceiling.

    An earlier version trimmed entries until the framing fit. On the first real
    framing it met, that meant dropping ten of eleven terms — and still not
    fitting, because a 4,900-character framing is not 4,900 characters' worth of
    pronunciation. Trading away the coverage this module exists to guarantee, to
    make room for prose bloat somewhere else, is the wrong way round: a missing
    entry is how *imamate* reached the audio with no guidance at all and came
    back garbled in 33 of 34 utterances. If the framing is over the ceiling the
    build's own character gate says so, and the fix is to compress the prose.
    ``char_max`` is accepted so callers can pass their ceiling and is used only
    to report the overflow, never to act on it.

    The framing is returned unchanged — no exception, no partial edit — when
    there is no book dir, no chapter, no `## Pronunciation` section, or nothing
    resolvable to say. Compiling is an improvement on the authored block, not a
    precondition for building.
    """
    if book_dir is None or chapter_text is None:
        return cleaned, []
    m = _SECTION_RE.search(cleaned)
    if not m:
        return cleaned, []

    entries, unresolved = compile_entries(book_dir, chapter_text, m.group(2))
    if not entries:
        return cleaned, unresolved

    block = render_block(m.group(1), entries)
    return cleaned[: m.start()] + block + cleaned[m.end() :], unresolved
