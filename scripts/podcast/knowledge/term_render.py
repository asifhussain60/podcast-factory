#!/usr/bin/env python3
"""term_render.py — deterministic "how should NotebookLM SAY this Arabic term" resolver.

Generalises pronunciation across every book. It replaces the disproven premise
that a hyphen-CAPS respelling (``is-raa-FEEL``) can be validated by ear and reused:
the NotebookLM TTS reads such respellings LITERALLY — the asaas-vol-1 probe audio
turned ``JAA-far`` into "J.A. Far", ``is-raa-FEEL`` into "Israel, feel", and
``natiq`` (respelled) into "nae tick". Meanwhile every term given as a plain English
word or a plain transliteration came out flawless ("Cain", "Abel", "Satan").

So instead of hunting for a respelling the TTS can say, we render every term into
what the TTS ALREADY says perfectly, chosen by an ordered, deterministic classifier:

    1. loanword allowlist   -> keep the canonical spelling   (Allah, Quran, Kaaba)
    2. name-exonym table     -> the English exonym             (Qabil -> Cain)
    3. gloss (ledger / book) -> the English translation        (al-batin -> the inner)
    4. otherwise             -> plain transliteration           (al-Tabari) — diacritics
                                stripped, NO hyphens, NO CAPS, NEVER the `phonetic` field

Corpus-wide and LLM-free: the two tables live in ``content/knowledge-base/``
(``exonyms.json`` + ``loanwords.json``); the gloss comes from the cross-book
pronunciation ledger or from the book's OWN inline glosses (``mine_glosses``). A
per-term person/place/concept LLM classifier for the long tail is a separate,
deferred layer that feeds the same ``gloss`` field — it is intentionally NOT here.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from pronunciation_ledger import normalize_key  # same package (knowledge/)

# Segments the upstream probe assigns. Personal names / places must NOT be
# replaced by a book-mined common-noun gloss (a name is not a concept), so
# tier-3 book-gloss is skipped for these. They still get tier-2 exonyms.
_NAME_SEGMENTS = {"names", "places"}

# Tiers, in priority order — exposed for logging / provenance.
TIER_LOANWORD = "loanword"
TIER_EXONYM = "exonym"
TIER_GLOSS_LEDGER = "gloss-ledger"
TIER_GLOSS_BOOK = "gloss-book"
TIER_TRANSLIT = "translit"


@dataclass(frozen=True)
class RenderResult:
    """The NotebookLM-safe spoken form of a term, plus how it was chosen."""

    text: str  # what the hosts should SAY
    tier: str  # which classifier rung produced it
    is_english: bool  # True when `text` is an English substitute for the Arabic
    #                     (so the caller can say "say the English, not the Arabic")


def _strip_to_plain(s: str) -> str:
    """Plain natural transliteration: drop combining diacritics, collapse spaces.

    Keeps the readable transliteration (``al-Tabari``, ``Abi Talib``) intact —
    only removes macrons/under-dots/hamza-glyphs that would make the TTS spell
    the word out. Never introduces hyphen-syllables or CAPS stress.
    """
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("ʿ", "'").replace("ʾ", "'").replace("ʼ", "'")
    return re.sub(r"\s+", " ", s).strip()


def load_tables(kb_dir: Path | None = None) -> tuple[dict[str, str], dict[str, str]]:
    """Load (exonyms, loanwords), keyed by ``normalize_key``. Missing files -> {}.

    ``kb_dir`` defaults to ``content/knowledge-base/`` resolved from this file's
    location (scripts/podcast/knowledge/ -> ../../../content/knowledge-base/).
    """
    if kb_dir is None:
        kb_dir = Path(__file__).resolve().parents[3] / "content" / "knowledge-base"

    def _load(name: str) -> dict[str, str]:
        path = kb_dir / name
        if not path.exists():
            return {}
        raw = json.loads(path.read_text(encoding="utf-8"))
        return {normalize_key(k): v for k, v in raw.items() if not k.startswith("_") and isinstance(v, str)}

    return _load("exonyms.json"), _load("loanwords.json")


# A book's own inline gloss: ``translit (English phrase)`` — e.g.
# "tafsir (exegesis)", "tanzil (revelation)", "the symbol (ramz)". We harvest the
# Arabic-side token (1 word, optionally an ``al-`` prefixed / apostrophe'd form)
# immediately adjacent to a short English parenthetical, in EITHER order.
_GLOSS_LEFT = re.compile(r"\b([A-Za-z][A-Za-z'ʿʾ-]{2,})\s*\(([A-Za-z][A-Za-z ,'-]{2,40})\)")
_GLOSS_RIGHT = re.compile(r"\b([A-Za-z][A-Za-z ,'-]{2,40})\s*\(([A-Za-z][A-Za-z'ʿʾ-]{2,})\)")
# English parentheticals that are NOT glosses (citations, dates, refs).
_NOT_A_GLOSS = re.compile(r"\b(ed|trans|vol|p|pp|no|see|cf|ibid|d|r|b)\b", re.IGNORECASE)
# A clean gloss never starts with a conjunction/preposition/clause word — those
# signal we captured a sentence fragment, not the term's translation. ("the"/"a"
# ARE allowed: "the inner", "a covenant".)
_BAD_GLOSS_LEAD = frozenset(
    "and or of in on at to for with by from as that which who whom they we it "
    "is are was were has have had this these those".split()
)


def _looks_arabic_translit(tok: str) -> bool:
    """Heuristic: a single transliterated Arabic word (not an English phrase)."""
    t = tok.strip()
    if " " in t and not t.lower().startswith("al-"):
        return False
    return bool(re.search(r"[a-z]", t)) and len(t) >= 3


def mine_glosses(text: str) -> dict[str, str]:
    """Harvest ``key -> English gloss`` from a book's own inline parentheticals.

    Faithful by construction — it reuses the translator's OWN rendering, inventing
    nothing. Conservative: only single-word Arabic tokens paired with a short
    English phrase qualify, and obvious citation parentheticals are ignored. The
    caller decides whether to apply a mined gloss (tier 3 skips personal names).
    """
    out: dict[str, str] = {}

    def _consider(arabic: str, english: str) -> None:
        arabic, english = arabic.strip(), english.strip().rstrip(".,")
        words = english.split()
        if not words:
            return
        if not _looks_arabic_translit(arabic):
            return
        if "," in english:  # a comma means a fragment, not a gloss
            return
        if len(words) > 4:  # a clean gloss is short
            return
        if words[0].lower() in _BAD_GLOSS_LEAD:  # sentence-fragment lead-in
            return
        if _NOT_A_GLOSS.fullmatch(words[0]):  # citation token
            return
        if re.search(r"\d", english):  # dates / page numbers -> not a gloss
            return
        out.setdefault(normalize_key(arabic), english)

    for m in _GLOSS_LEFT.finditer(text):
        _consider(m.group(1), m.group(2))
    for m in _GLOSS_RIGHT.finditer(text):
        # right form is "English (translit)" -> swap
        _consider(m.group(2), m.group(1))
    return out


def render_for_audio(
    translit: str,
    *,
    segment: str | None = None,
    ledger_entry: dict | None = None,
    book_glosses: dict[str, str] | None = None,
    tables: tuple[dict[str, str], dict[str, str]] | None = None,
) -> RenderResult:
    """Resolve the NotebookLM-safe spoken form of one Arabic term.

    ``translit`` is the plain display transliteration (``Israfil``, ``al-batin``,
    ``al-Tabari``) — NOT the Arabic script and NOT a respelling. The result is
    always either an English substitute or a plain transliteration; it is NEVER a
    hyphen-CAPS phonetic respelling.
    """
    exonyms, loanwords = tables if tables is not None else load_tables()
    key = normalize_key(translit)
    # The definite article is not part of a name's identity for table lookup, so
    # ``al-Shaytan`` can still reach the ``shaytan`` exonym. Try the bare key too.
    bare = key[3:] if key.startswith("al-") else key

    # 1. Loanword — keep the canonical English spelling.
    if key in loanwords:
        return RenderResult(loanwords[key], TIER_LOANWORD, is_english=False)
    if bare in loanwords:
        return RenderResult(loanwords[bare], TIER_LOANWORD, is_english=False)

    # 2. Name exonym — the established English form.
    if key in exonyms:
        return RenderResult(exonyms[key], TIER_EXONYM, is_english=True)
    if bare in exonyms:
        return RenderResult(exonyms[bare], TIER_EXONYM, is_english=True)

    # 3a. Ledger gloss — a human-confirmed / unfixable English substitute.
    if ledger_entry:
        g = (ledger_entry.get("gloss") or "").strip()
        if g:
            return RenderResult(g, TIER_GLOSS_LEDGER, is_english=True)

    # 3b. Book-mined gloss — the translator's own English, for concept terms only.
    if book_glosses and (segment not in _NAME_SEGMENTS):
        g = book_glosses.get(key)
        if g:
            return RenderResult(g, TIER_GLOSS_BOOK, is_english=True)

    # 4. Plain natural transliteration — the safe default.
    return RenderResult(_strip_to_plain(translit), TIER_TRANSLIT, is_english=False)
