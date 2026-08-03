"""_gloss_terms.py — find the Arabic terms a composed book GLOSSES in its prose.

The problem this solves. `degrees-of-excellence` prints 266 parenthetical glosses
across 188 distinct terms — `the ranks (hudud)`, `governance (siyasa)`, `the
proofs (hujaj)` — and exactly one of them carries Arabic script. Not because the
overlay is broken: because the glossary that drives it held ELEVEN entries. Its
input, `_system/source/text/_phonetics.md`, has had no writer since 2026-06-08,
and the fallback is a hard-coded 30-term list none of this book's vocabulary is
on. So the pipeline never learned the words the book was already teaching.

The glosses themselves are NOT the model's invention — 181 of 188 appear in the
source, because a critical edition teaches its vocabulary that way. They are kept
and converted, never stripped.

ONE MODULE, TWO CONSUMERS: `harvest_gloss_terms.py` (which adds what it finds to
the glossary) and the compose-time coverage gate. They must agree about what
counts as a gloss, or the gate would fail a book the harvester cannot fix.

CONFIDENCE, and why it can be loose. A candidate is STRONG when the SOURCE spells
the same word with scholarly diacritics that `simplify_transliteration` folds
away — `ḥudūd` -> `hudud`, `taʾwīl` -> `tawil`. That is direct evidence the word
is Arabic rather than English, and it covers 146 of 188 measured. The remaining
42 are WEAK and passed through anyway, because the pipeline already contains the
real arbiter: `fill_glossary_arabic` returns `""` for anything it cannot find in
the OCR, and `_book_inline_arabic._glossary_terms` excludes an entry with empty
script. So `(pole)` — an English word in a parenthesis — costs one lookup that
finds nothing and is never annotated. The filter only has to be good enough to
save spend, not to be correct, which is what makes it safe to be generous.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

from _translit import simplify_transliteration

#: See `_narrative.R_NO_LECTURE_VOICE` for why a rule id lives beside its check
#: rather than in `_rules.py`.
R_ARABIC_SCRIPT_SHOWN_ONCE: str = "R-ARABIC-SCRIPT-SHOWN-ONCE"  # REQ-BA-127

#: Lines that are not running prose: headings, quotes, fences, HTML, tables.
#: Shared shape with `_book_inline_arabic._SKIP_LINE` — a gloss inside a fenced
#: block or a table cell is not a gloss the reader meets in a sentence.
_SKIP_LINE = re.compile(r"^\s*(?:[>#]|```|<|\|)")

#: `(anything)` on one line, with the emphasis markers a source gloss often
#: carries (`(*bab*)`). Bounded length: a parenthesis holding a clause is an
#: aside, not a term.
_PAREN = re.compile(r"\((\*?)([^()\n]{2,45}?)\1\)")

#: `*term*` — the OTHER shape a book glosses in, and the one the articulation
#: pass produces. `_PAREN` alone finds `the gnosis (marifah)`; REQ-BA prose
#: writes `the *marifah* — the gnosis`, putting the Arabic word in emphasis and
#: the English in apposition. Same gloss, inverted.
#:
#: Measured 2026-08-03, and the reason this exists: `al-anwaar-al-lateefah/vol-01`
#: italicises 261 distinct terms across 359 uses and the harvester found ONE
#: candidate, because the book almost never uses the parenthetical form. 239 of
#: those terms reached the printed page with no Arabic script anywhere in the
#: book — `marifah`, `shariah`, `muwalat`, `muhabbah`, `mansubin` — which a
#: reader who does not read romanised Arabic cannot look up, cannot pronounce,
#: and cannot tell apart from an English word set in italics for emphasis.
#: `asaas-al-taveel/vol-01` had 61 and `ayyuhal-walad` 7 for the same reason.
#:
#: NOT bounded to single words for the same reason `_PAREN` is not: `nafi
#: al-jins` and `alam al-ruh` are terms. Doubled asterisks are excluded — bold is
#: emphasis, italic is the foreign-word convention.
_EMPHASIS = re.compile(r"(?<!\*)\*([^*\n]{2,45})\*(?!\*)")

_ARABIC = re.compile(r"[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]")

#: A romanized Arabic term is letters, spaces, hyphens and apostrophes. A digit,
#: a colon or a slash means a citation (`Al-Baqarah: 24`), a date (`d. 381/991`)
#: or a reference — never a term.
_SHAPE = re.compile(r"^[A-Za-z'’ʾʿ\-\s]{2,45}$")

#: Whole-token English that proves the parenthesis is a phrase, not a term.
#: Deliberately small: these are words that cannot appear in a transliterated
#: Arabic noun phrase, so a hit is decisive rather than probabilistic.
_ENGLISH_TOKENS = frozenset(
    """
    a an the and or but of to in on at by for with from as is are was were be been
    this that these those it its he she they we you i not no nor if then than
    may might can could will would shall should must
    see also cf ibid trans ed eds vol p pp n
    god allah lord praise blessing peace upon him her them
    general editor translator translated edited introduction preface note notes
    """.split()
)

#: Terms English has absorbed and the repo already lists as such, plus the
#: prophet exonyms. Both files exist for exactly this question, so the answer is
#: read rather than re-derived.
_KB = Path(__file__).resolve().parents[2] / "content" / "knowledge-base"


def _kb_words(name: str) -> frozenset[str]:
    try:
        data = json.loads((_KB / name).read_text(encoding="utf-8"))
    except Exception:
        return frozenset()
    return frozenset(k.lower() for k in data if not k.startswith("_"))


def absorbed_english() -> frozenset[str]:
    """Words that are English now — `imam`, `quran`, `islam`, plus prophet names.

    OUT OF SCOPE by Asif's rule (2026-08-02): the exclusion is about a term doing
    an ordinary English job in running prose. A parenthesis is the book stopping
    to SHOW the Arabic word, so a gloss of one of these is still a gloss — this
    set is used to judge running prose, never to reject a candidate.
    """
    return _kb_words("loanwords.json") | _kb_words("exonyms.json")


def normalize_term(raw: str) -> str:
    """The comparison form: folded transliteration, collapsed space, lowercased."""
    return " ".join(simplify_transliteration(str(raw or "")).split()).lower()


def _source_diacritic_forms(source_text: str) -> frozenset[str]:
    """Words the SOURCE spells with scholarly diacritics, in folded form.

    `ḥudūd` folds to `hudud` and differs from what it folded FROM, which is the
    evidence: an English word never changes under the fold. Built once per book.
    """
    out: set[str] = set()
    for token in re.findall(r"[^\s—–.,;:()\[\]\"'!?]+", source_text or ""):
        folded = simplify_transliteration(token)
        if folded != token and re.fullmatch(r"[A-Za-z'’\-]{2,}", folded):
            out.add(folded.lower())
    return frozenset(out)


def gloss_candidates(book_md: str, source_text: str = "") -> list[dict[str, Any]]:
    """Every parenthetical gloss of an Arabic term, deduped, strongest first.

    Each entry: ``{term, count, confidence, first_seen_snippet}``.
    """
    diacritic_forms = _source_diacritic_forms(source_text)
    seen: dict[str, dict[str, Any]] = {}

    for line in (book_md or "").splitlines():
        if not line.strip() or _SKIP_LINE.search(line):
            continue
        # Parenthetical shape FIRST, so when a term appears both ways the
        # snippet recorded is the one that already shows a gloss.
        matches = [(m, m.group(2)) for m in _PAREN.finditer(line)]
        matches += [(m, m.group(1)) for m in _EMPHASIS.finditer(line)]
        for match, raw in matches:
            inner = raw.strip()
            if _ARABIC.search(inner) or not _SHAPE.fullmatch(inner):
                continue
            tokens = inner.split()
            if not 1 <= len(tokens) <= 4:
                continue
            if any(t.strip("'’-").lower() in _ENGLISH_TOKENS for t in tokens):
                continue
            key = normalize_term(inner)
            if not key:
                continue
            hit = seen.get(key)
            if hit:
                hit["count"] += 1
                continue
            # STRONG when any word of the term is one the source spells with
            # diacritics. One word is enough for a phrase: `ra's al-ulama` is
            # proved Arabic by `ʿulamāʾ` alone.
            strong = any(t.lower().strip("'’-") in diacritic_forms for t in simplify_transliteration(inner).split())
            start = max(0, match.start() - 40)
            seen[key] = {
                "term": inner,
                "count": 1,
                "confidence": "strong" if strong else "weak",
                "first_seen_snippet": line[start : match.end() + 10].strip(),
            }

    return sorted(
        seen.values(),
        key=lambda c: (c["confidence"] != "strong", -c["count"], c["term"].lower()),
    )


#: First word of a WORK'S TITLE. A title is legitimately Arabic and legitimately
#: italicised, and it is not a term the glossary should teach or the overlay
#: should annotate — `*Kitab al-Anwar*` wants no script beside it.
_TITLE_HEADS = frozenset(
    "kitab kitaab risala risalah diwan ahya ihya minhaj rahat asas asaas tafsir sahih musnad".split()
)

#: Ordinary English set in italics — for emphasis, or as the GLOSS half of a pair
#: (`*batin*, the *inner*`). Same idiom and same justification as
#: `_ENGLISH_TOKENS` above: deliberately a list of words that cannot be a
#: transliterated Arabic term, so a whole-term hit is decisive rather than
#: probabilistic. Used ONLY to suppress a finding, never to reject a candidate —
#: a wrongly-kept candidate costs one lookup that finds nothing, while a wrongly
#: reported finding costs the reader's trust in the report.
#:
#: Seeded from what the five live editions actually produced (2026-08-03):
#: `water`, `way`, `light`, `road`, `knowledge`, `Curse`, `Path`, `Forty Steps`.
_ENGLISH_GLOSS_WORDS = frozenset(
    """
    water way ways road roads path paths door doors house houses tent tents
    light lights darkness dark life death born blind deaf dumb mute silent
    knowledge wisdom ignorance remembrance reminder reminders sign signs proof proofs
    curse blessing mercy justice truth falsehood faith disbelief belief
    inner outer hidden manifest apparent open closed sealed
    guardian guide guides teacher master disciple boy child children
    rank ranks limit limits bound bounds degree degrees station stations pole poles
    imamate caliphate prophethood
    first second third fourth fifth last next final
    forty thirty twenty ten seven five four three two one hundred
    step steps stage stages ladder chain circle rooms room
    speaking silent standing rising ascent descent
    tradition traditions grounded rooted
    outwardists inwardists literalists
    """.split()
)


def _looks_english(term: str) -> bool:
    """True when EVERY word of the term is ordinary English.

    Splits on hyphens as well as spaces, so an English compound set in italics
    (`*tradition-grounded*`) is caught — while `al` is dropped as the particle it
    is, keeping `al-asas` and `bayt al-mal` in scope.
    """
    tokens = [t for t in (p.strip("'’").lower() for p in re.split(r"[\s\-]+", term)) if t and t != "al"]
    return bool(tokens) and all(t in _ENGLISH_GLOSS_WORDS for t in tokens)


#: Every `(…)` on a line, found in ONE linear pass. What sits before it is read
#: in Python rather than matched by a look-behind: a backwards pattern like
#: `((?:[A-Za-z][\w\-]*[ \t]*\*?[ \t]*){1,4})\(` nests two unbounded quantifiers
#: and backtracks catastrophically on ordinary prose that has no parenthesis on
#: the line — it hung the test suite on the first fixture it met.
_BRACKET = re.compile(r"\(([^)\n]*)\)")

#: How far back a term can start. Four words of Arabic transliteration, which is
#: the widest `_PAREN` itself accepts.
_TERM_LOOKBACK = 60

_LATIN_WORD = re.compile(r"[A-Za-z'’ʾʿ][\w'’ʾʿ\-]*")


def scripted_terms(book_md: str) -> set[str]:
    """Every romanization this book gives Arabic script for, at least once.

    Registers each TRAILING suffix of the words before the parenthesis, not just
    the whole run: the annotation sits at the end of an ordinary sentence, so
    `the hudud (حُدُود)` must answer for `hudud` and not only for `the hudud`.
    Over-generating is free — the set is only ever asked about terms that are
    already glossary candidates.

    BOTH ORDERS COUNT. Where a passage discusses Arabic AS LETTERS the convention
    is inverted — `كُنْ (kun)`, script first, romanization inside — and BK-N4 in
    `book-challenger` requires exactly that form. Reading only one order reported
    `Kun` as never scripted on `the-master-and-the-disciple` when the book shows
    it plainly; a check that flags the form the standard demands is worse than no
    check.
    """
    text = book_md or ""
    out: set[str] = set()
    for m in _BRACKET.finditer(text):
        inside = m.group(1)
        before = text[max(0, m.start() - _TERM_LOOKBACK) : m.start()]
        if _ARABIC.search(inside):
            # `the hudud (حُدُود)` — the term precedes; register every trailing run.
            words = _LATIN_WORD.findall(before.replace("*", " "))[-4:]
            for n in range(1, len(words) + 1):
                key = normalize_term(" ".join(words[-n:]))
                if key:
                    out.add(key)
        elif _ARABIC.search(before[-8:]):
            # `كُنْ (kun)` — the script precedes, the romanization is inside. A
            # gloss, not a translation: `(Be, and it is)` is four words of English.
            key = normalize_term(inside.replace("*", " "))
            if key and len(key.split()) <= 4:
                out.add(key)
    return out


#: Annotation classes that mean "print this bare, on purpose". `familiar` is a
#: recognized English form (halal, Quran, Mount Sinai) and `silent` is a curated
#: decision to annotate nothing — both are the annotation policy working, not a
#: gap. Skipping them is what makes the finding list actionable: on
#: `ayyuhal-walad` it is the difference between 5 findings and the 2 that are real.
_DELIBERATELY_BARE = frozenset({"familiar", "silent"})


def bare_term_findings(
    book_md: str,
    source_text: str = "",
    entries: Iterable[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Terms the book sets as foreign but never once gives in Arabic script.

    R-ARABIC-SCRIPT-RETAINED asks whether script the SOURCE had survived. It
    cannot ask this, and neither can the Arabic audit: both enumerate Arabic RUNS,
    so a term that reached the page as `*marifah*` and nothing else produces no
    run and is invisible to the data structure — measured as "0 lost". This
    starts from the romanization instead.

    Why it matters to the reader rather than to a gate: Asif does not read
    romanised Arabic. `*marifah*` in italics is indistinguishable from an English
    word italicised for emphasis; he cannot pronounce it, look it up, or trace it
    through the argument. Found on the printed page of `al-anwaar-al-lateefah`
    (239 terms), `asaas-al-taveel` (61) and `ayyuhal-walad` (7) — every one of
    them shipped with `arabic_runs_lost: 0`.

    Work titles are excluded, not counted and forgiven: `*Kitab al-Anwar*` is a
    title, and a title wants no script beside it. So are terms the glossary has
    classified `familiar` or `silent` when ``entries`` is supplied — those are the
    annotation policy deciding, and a check that argues with a curated decision is
    noise.
    """
    have = scripted_terms(book_md)
    deliberate = {
        normalize_term(e.get("phonetic") or e.get("transliteration") or "")
        for e in (entries or [])
        if str(e.get("annotation_class") or "") in _DELIBERATELY_BARE
    }
    deliberate.discard("")
    out: list[dict[str, Any]] = []
    for c in gloss_candidates(book_md, source_text):
        key = normalize_term(c["term"])
        if key in have or key in deliberate or key.split()[0] in _TITLE_HEADS or _looks_english(c["term"]):
            continue
        out.append(
            {
                "term": c["term"],
                "uses": c["count"],
                "confidence": c["confidence"],
                "first_seen_snippet": c["first_seen_snippet"],
            }
        )
    return sorted(out, key=lambda r: (r["confidence"] != "strong", -r["uses"], r["term"].lower()))


def gloss_coverage(book_md: str, entries: Iterable[dict[str, Any]], source_text: str = "") -> dict[str, Any]:
    """How much of what the book glosses the glossary can actually annotate.

    THE number the pipeline never computed. `_book_arabic_audit` enumerates
    Arabic RUNS first, so a romanized term with no script produces no run and is
    not merely unmeasured — it is invisible to the data structure. This is its
    complement: it starts from the romanization and asks whether script exists.
    """
    known: dict[str, dict[str, Any]] = {}
    for e in entries:
        key = normalize_term(e.get("phonetic") or e.get("transliteration") or "")
        if key:
            known.setdefault(key, e)

    candidates = gloss_candidates(book_md, source_text)
    missing_strong: list[str] = []
    covered = 0
    for c in candidates:
        entry = known.get(normalize_term(c["term"]))
        if entry and str(entry.get("arabic_script") or "").strip():
            covered += 1
        elif c["confidence"] == "strong":
            missing_strong.append(c["term"])

    strong = [c for c in candidates if c["confidence"] == "strong"]
    # What actually reached the PAGE, independent of the strong/weak evidence.
    # `strong` needs the source to spell a word with scholarly diacritics, and an
    # articulated book's source does not — every one of the five live editions
    # measured `strong: 0`, so the ratio below reported "nothing to measure" and
    # passed while 219 terms printed as bare romanization. This asks the reader's
    # question instead: is the Arabic on the page at all?
    bare = bare_term_findings(book_md, source_text, known.values())
    return {
        "schema": "book.gloss-coverage/v2",
        "candidates": len(candidates),
        "strong": len(strong),
        "covered": covered,
        "missing_strong": sorted(missing_strong),
        "glossary_entries": len(known),
        "coverage": round(covered / len(candidates), 3) if candidates else 1.0,
        "strong_coverage": (round((len(strong) - len(missing_strong)) / len(strong), 3) if strong else 1.0),
        "bare_terms": len(bare),
        "bare_uses": sum(r["uses"] for r in bare),
        "bare": bare[:80],
    }
