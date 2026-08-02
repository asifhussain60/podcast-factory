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

    0. book override         -> whatever the human wrote      (_system/pronunciation.md)
    1. loanword allowlist   -> keep the canonical spelling   (Allah, Quran, Kaaba)
    2. name-exonym table     -> the English exonym             (Qabil -> Cain)
    3. confirmed ledger form -> a form a human HEARD come out right
    4. gloss (ledger / book) -> the English translation        (al-batin -> the inner)
    5. otherwise             -> plain transliteration           (al-Tabari) — diacritics
                                stripped, NO hyphens, NO CAPS, never an unheard respelling

Rung 0 is the one place a respelling may still win, and it exists because the
ladder below it is a heuristic while a human listening to the audio is not. The
per-book table at ``BOOK_DIR/_system/pronunciation.md`` has been the documented
override authority since the books began; until 2026-08-01 nothing read it, so
its rows only ever reached the audio when someone also pasted them into a
framing by hand. Now it governs. A row whose value begins with ``substitute``
means "say this English instead of the Arabic"; any other value is the spoken
form verbatim, respelling or not — the human's ear outranks the classifier.

Rung 3 is the same principle applied corpus-wide. The premise this module
rejects is trusting an UNHEARD respelling; a ledger entry marked ``confirmed``
is by definition one somebody listened to and accepted, so refusing it would
strand the probe -> listen -> correct loop that writes those entries. Rungs 1
and 2 still outrank it: a loanword forced into a respelling is exactly how
"Imam" became "e-Maam" in the live 2026-06-12 render.

Corpus-wide and LLM-free: the two tables live in ``content/knowledge-base/``
(``exonyms.json`` + ``loanwords.json``); the gloss comes from the cross-book
pronunciation ledger or from the book's OWN inline glosses (``mine_glosses``). A
per-term person/place/concept LLM classifier for the long tail is a separate,
deferred layer that feeds the same ``gloss`` field — it is intentionally NOT here.

``book_glosses`` is accepted but, as of 2026-08-01, the NotebookLM audio path no
longer passes it (``_pronunciation_block`` and the probe both stopped). See
``mine_glosses`` for why: it is the one input here that can invert the meaning it
is supposed to carry.
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
TIER_BOOK_OVERRIDE = "book-override"
TIER_LOANWORD = "loanword"
TIER_EXONYM = "exonym"
TIER_LEDGER_CONFIRMED = "ledger-confirmed"
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


# A row of the per-book override table: ``| Term | Phonetic | Notes |``. The
# Notes column is documentation for the next human and is never rendered.
_OVERRIDE_SEPARATOR = re.compile(r"^[\s|:-]+$")
# "substitute the pillars" / "substitute *the lower self*" -> say the English.
_SUBSTITUTE_PREFIX = re.compile(r"^substitute\b[:\s]*", re.IGNORECASE)
# A row that names a term but asserts nothing about how it sounds: "this word
# matters in this book, and the answer is whatever the ladder resolves". It
# exists so a disproven value can be WITHDRAWN without deleting the row — the
# probe builds its inventory from this table, so deleting the row would drop the
# term from the very run meant to settle it.
_PLAIN_VALUES = frozenset({"plain", "-", "--", "—", "(plain)", "n/a"})


def is_withdrawn(value: str) -> bool:
    """True when an override row names a term but supplies no spoken form."""
    return value.strip().lower() in _PLAIN_VALUES


def parse_book_override_table(book_dir: Path | None) -> list[tuple[str, str]]:
    """Parse ``BOOK_DIR/_system/pronunciation.md`` -> ``[(display_term, value)]``.

    Table order is preserved and the term keeps the human's own spelling — a
    caller printing entries back into a framing must show ``al-Naysaburi``, not
    the lookup key ``al-naysaburi``. Values are VERBATIM (including a
    ``substitute`` prefix, which ``render_for_audio`` interprets).

    A missing file, an empty table, or a malformed row yields no entry rather
    than an error: an override table is an optional refinement, and a book that
    has never needed one must still render.
    """
    if book_dir is None:
        return []
    path = Path(book_dir) / "_system" / "pronunciation.md"
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()

    # Read the table under the canonical `| Term | Phonetic |` header, and only
    # that one. These files carry prose, and prose about pronunciation tends to
    # contain tables — an evidence table of "told to say / came out as" was
    # enough to put rows like `told to say -> Came out as` into rung 0 and
    # outrank every real override with them. Anchoring on the header makes the
    # contract the file states ("only the override table is read") actually true.
    # A file with no such header falls back to reading every row, so a book
    # whose table predates the header keeps working.
    start = 0
    for i, line in enumerate(lines):
        cells = [c.strip().lower() for c in line.strip().strip("|").split("|")]
        if line.strip().startswith("|") and len(cells) >= 2 and cells[0] == "term" and cells[1].startswith("phonetic"):
            start = i + 1
            break

    rows: list[tuple[str, str]] = []
    seen: set[str] = set()
    for line in lines[start:]:
        line = line.strip()
        if not line.startswith("|"):
            if start and rows:
                break  # the anchored table has ended
            continue
        if _OVERRIDE_SEPARATOR.fullmatch(line):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        term, value = cells[0], cells[1]
        if not term or not value or term.lower() == "term":  # blank or header row
            continue
        key = normalize_key(term)
        if key in seen:
            continue
        seen.add(key)
        rows.append((term, value))
    return rows


def load_book_overrides(book_dir: Path | None) -> dict[str, str]:
    """``{normalize_key(term): value}`` for ``render_for_audio``'s rung 0.

    Withdrawn rows are excluded: they keep a term on the book's list without
    claiming to know how it sounds, so rung 0 must not fire for them and the
    ladder resolves the term on its own.
    """
    return {
        normalize_key(term): value for term, value in parse_book_override_table(book_dir) if not is_withdrawn(value)
    }


# A book's own inline gloss: ``translit (English phrase)`` — e.g.
# "tafsir (exegesis)", "tanzil (revelation)", "the symbol (ramz)". We harvest the
# Arabic-side token (1 word, optionally an ``al-`` prefixed / apostrophe'd form)
# immediately adjacent to a short English parenthetical, in EITHER order.
_GLOSS_LEFT = re.compile(r"\b([A-Za-z][A-Za-z'ʿʾ-]{2,})\s*\(([A-Za-z][A-Za-z ,'-]{2,40})\)")
_GLOSS_RIGHT = re.compile(r"\b([A-Za-z][A-Za-z ,'-]{2,40})\s*\(([A-Za-z][A-Za-z'ʿʾ-]{2,})\)")
# English parentheticals that are NOT glosses (citations, dates, refs).
_NOT_A_GLOSS = re.compile(r"\b(ed|trans|vol|p|pp|no|see|cf|ibid|d|r|b)\b", re.IGNORECASE)
# Marks that only a transliteration carries: macrons, under-dots, ayn/hamza.
_TRANSLIT_MARKS = re.compile(r"[āīūēōḥḍṣṭẓḏṯġḫʿʾ‘’]")
# A clean gloss never starts with a conjunction/preposition/clause word — those
# signal we captured a sentence fragment, not the term's translation. ("the"/"a"
# ARE allowed: "the inner", "a covenant".)
_BAD_GLOSS_LEAD = frozenset(
    # "indeed their chief (ya'sub)" mined a gloss of "indeed their chief".
    "indeed truly namely rather perhaps likewise moreover however therefore "
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

    KNOWN LIMITATION, and the reason the audio path stopped consuming this on
    2026-08-01: ``English (translit)`` and ``translit (English)`` are the same
    shape. The guards below reject a reversal whenever the Arabic side carries a
    mark — a macron, an under-dot, an ayn/hamza apostrophe — which covered every
    instance that reached a real bundle (``khalīfa``, ``ya'sub``, ``fay'``). When
    the Arabic carries none, "the vicegerent (khalifa) of the Commander" is
    indistinguishable from "tafsir (exegesis)" and the direction is a guess.
    Deciding it needs an English lexicon or the book's own term inventory, which
    belongs with a caller that has one.
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
        # A "gloss" carrying transliteration marks means the direction was read
        # backwards: the parenthesis holds the ARABIC. `a vicegerent (khalīfa)`
        # matches both patterns, and the left one mined it as
        # vicegerent -> khalīfa, which would have the hosts answer an English
        # word with an Arabic one — the opposite of what a gloss is for.
        if _TRANSLIT_MARKS.search(english):
            return
        # Same reversal, signalled by an apostrophe instead of a macron: the
        # parenthesis in "their chief (ya'sub)" and "'bestowal' (fay')" holds
        # the Arabic. A one-word gloss carrying an ayn/hamza apostrophe is a
        # transliteration; a real English gloss of one word has none, and a
        # possessive ("God's mercy") is more than one word.
        if len(words) == 1 and "'" in english:
            return
        # Metalinguistic, not a translation: "The word 'bestowal' (fay')" glosses
        # nothing — it names the word it is about.
        if re.match(r"^(the|a)\s+(word|term|name|title|phrase|expression)\b", english, re.IGNORECASE):
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
    book_overrides: dict[str, str] | None = None,
    tables: tuple[dict[str, str], dict[str, str]] | None = None,
) -> RenderResult:
    """Resolve the NotebookLM-safe spoken form of one Arabic term.

    ``translit`` is the plain display transliteration (``Israfil``, ``al-batin``,
    ``al-Tabari``) — NOT the Arabic script and NOT a respelling. Below the
    override rung the result is always either an English substitute or a plain
    transliteration, never a hyphen-CAPS respelling; a respelling reaches the
    audio only when a human put it in ``book_overrides`` (see module docstring).
    """
    exonyms, loanwords = tables if tables is not None else load_tables()
    key = normalize_key(translit)
    # The definite article is not part of a name's identity for table lookup, so
    # ``al-Shaytan`` can still reach the ``shaytan`` exonym. Try the bare key too.
    bare = key[3:] if key.startswith("al-") else key

    # 0. Per-book human override — outranks every heuristic below it.
    if book_overrides:
        raw = book_overrides.get(key) or book_overrides.get(bare)
        if raw:
            stripped = _SUBSTITUTE_PREFIX.sub("", raw).strip().strip("*").strip()
            is_sub = stripped != raw.strip()
            if stripped:
                return RenderResult(stripped, TIER_BOOK_OVERRIDE, is_english=is_sub)

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

    # 3. Confirmed ledger form — heard in real audio and accepted. An "unfixable"
    # entry deliberately falls through to its gloss below: that status means no
    # spoken form works, so the phonetic on it is a record, not a candidate.
    # The status must be EXPLICIT. Every row the ledger writes carries one
    # (PronEntry serialises the field unconditionally), so demanding it costs
    # nothing real and leaves a hand-built dict without a status resolving
    # exactly as it did before this rung existed.
    if ledger_entry and ledger_entry.get("status") == "confirmed":
        p = (ledger_entry.get("phonetic") or "").strip()
        if p and normalize_key(p) != key:
            return RenderResult(p, TIER_LEDGER_CONFIRMED, is_english=False)

    # 4a. Ledger gloss — a human-confirmed / unfixable English substitute.
    if ledger_entry:
        g = (ledger_entry.get("gloss") or "").strip()
        if g:
            return RenderResult(g, TIER_GLOSS_LEDGER, is_english=True)

    # 4b. Book-mined gloss — the translator's own English, for concept terms only.
    if book_glosses and (segment not in _NAME_SEGMENTS):
        g = book_glosses.get(key)
        if g:
            return RenderResult(g, TIER_GLOSS_BOOK, is_english=True)

    # 5. Plain natural transliteration — the safe default.
    return RenderResult(_strip_to_plain(translit), TIER_TRANSLIT, is_english=False)
