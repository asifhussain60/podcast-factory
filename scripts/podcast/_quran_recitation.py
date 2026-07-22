#!/usr/bin/env python3
"""_quran_recitation.py — deterministic Quran citation -> verbatim KQur Arabic.

The faithfulness-safe bridge for ElevenLabs recitation: a Quran citation in the
dialogue script is resolved to (surah, ayat) by a STATIC canonical table + an
exact number parser, then the verbatim Arabic is read from the wisdom corpus
KQur (content/knowledge-base/mirror.db, table fts_quran via
source_library_mirror.quran_ayat_lookup). The model NEVER supplies the Arabic —
the same citation always yields the same canonical verse, or nothing.

Hard safety rule: an unresolved or unverified citation returns NOTHING (the
caller leaves the English as-is and logs it). Scripture is never guessed.

Resolution handles the forms the pipeline actually emits:
  - numeric    "(chapter 14, verse 7)"  /  "chapter 14, verse 7"
  - prose      "the chapter of Abraham, verse seven"
               "verse four of the chapter on Joseph"
Surah names cover the canonical transliterations + common English renderings.

Safety model: the DETERMINISTIC RESOLUTION is the guarantee — a canonical
surah table + an exact number parse map the citation to (surah, ayat), and
KQur returns the authoritative Arabic for exactly that verse (a non-existent
verse returns nothing -> skip). Translation-overlap verification is available
(`verify=True`) but DEFAULT OFF: two faithful English translations of the same
verse legitimately share few content words, so overlap-checking against the
book's own rendering produces false negatives and would suppress correct
recitations. It is retained only as an opt-in strict mode for diagnostics.

Pure + deterministic + read-only (mirror is opened read-only). No spend.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Canonical surah name -> number. Includes the standard transliteration and the
# common English-meaning name(s) used in scholarly prose. Normalized on lookup
# (lowercase, strip 'al-'/'the', collapse spaces/hyphens). Reference data — not
# model-generated; mirrors the canonical 114-surah ordering.
_SURAH_RAW: dict[str, int] = {
    "fatihah": 1,
    "the opening": 1,
    "opening": 1,
    "baqarah": 2,
    "the cow": 2,
    "cow": 2,
    "imran": 3,
    "family of imran": 3,
    "house of imran": 3,
    "ali imran": 3,
    "nisa": 4,
    "the women": 4,
    "women": 4,
    "maidah": 5,
    "the table": 5,
    "the table spread": 5,
    "the repast": 5,
    "anam": 6,
    "the cattle": 6,
    "cattle": 6,
    "araf": 7,
    "the heights": 7,
    "heights": 7,
    "anfal": 8,
    "the spoils of war": 8,
    "spoils of war": 8,
    "the spoils": 8,
    "tawbah": 9,
    "repentance": 9,
    "the repentance": 9,
    "yunus": 10,
    "jonah": 10,
    "hud": 11,
    "yusuf": 12,
    "joseph": 12,
    "rad": 13,
    "the thunder": 13,
    "thunder": 13,
    "ibrahim": 14,
    "abraham": 14,
    "hijr": 15,
    "the rocky tract": 15,
    "the stoneland": 15,
    "nahl": 16,
    "the bee": 16,
    "the bees": 16,
    "bee": 16,
    "isra": 17,
    "the night journey": 17,
    "night journey": 17,
    "bani israil": 17,
    "kahf": 18,
    "the cave": 18,
    "cave": 18,
    "maryam": 19,
    "mary": 19,
    "taha": 20,
    "ta ha": 20,
    "anbiya": 21,
    "the prophets": 21,
    "prophets": 21,
    "hajj": 22,
    "the pilgrimage": 22,
    "pilgrimage": 22,
    "muminun": 23,
    "the believers": 23,
    "believers": 23,
    "nur": 24,
    "the light": 24,
    "light": 24,
    "furqan": 25,
    "the criterion": 25,
    "criterion": 25,
    "shuara": 26,
    "the poets": 26,
    "poets": 26,
    "naml": 27,
    "the ant": 27,
    "the ants": 27,
    "ant": 27,
    "qasas": 28,
    "the stories": 28,
    "the story": 28,
    "stories": 28,
    "ankabut": 29,
    "the spider": 29,
    "spider": 29,
    "rum": 30,
    "the romans": 30,
    "the byzantines": 30,
    "romans": 30,
    "luqman": 31,
    "sajdah": 32,
    "the prostration": 32,
    "prostration": 32,
    "ahzab": 33,
    "the combined forces": 33,
    "the confederates": 33,
    "the clans": 33,
    "saba": 34,
    "sheba": 34,
    "fatir": 35,
    "the originator": 35,
    "originator": 35,
    "the angels": 35,
    "yasin": 36,
    "ya sin": 36,
    "ya-sin": 36,
    "saffat": 37,
    "those who set the ranks": 37,
    "the ranged ones": 37,
    "those ranged in ranks": 37,
    "sad": 38,
    "zumar": 39,
    "the troops": 39,
    "the groups": 39,
    "the crowds": 39,
    "ghafir": 40,
    "the forgiver": 40,
    "forgiver": 40,
    "mumin": 40,
    "the believer": 40,
    "fussilat": 41,
    "explained in detail": 41,
    "expounded": 41,
    "shura": 42,
    "the consultation": 42,
    "consultation": 42,
    "council": 42,
    "zukhruf": 43,
    "the gold adornments": 43,
    "ornaments of gold": 43,
    "gold": 43,
    "dukhan": 44,
    "the smoke": 44,
    "smoke": 44,
    "jathiyah": 45,
    "the kneeling": 45,
    "crouching": 45,
    "ahqaf": 46,
    "the wind curved sandhills": 46,
    "the dunes": 46,
    "the sand dunes": 46,
    "muhammad": 47,
    "fath": 48,
    "the victory": 48,
    "the conquest": 48,
    "hujurat": 49,
    "the rooms": 49,
    "the dwellings": 49,
    "the private apartments": 49,
    "qaf": 50,
    "dhariyat": 51,
    "the winnowing winds": 51,
    "the scatterers": 51,
    "the dispersing": 51,
    "tur": 52,
    "the mount": 52,
    "mount": 52,
    "najm": 53,
    "the star": 53,
    "star": 53,
    "qamar": 54,
    "the moon": 54,
    "moon": 54,
    "rahman": 55,
    "the most merciful": 55,
    "the most gracious": 55,
    "the beneficent": 55,
    "waqiah": 56,
    "the inevitable": 56,
    "the event": 56,
    "the occurrence": 56,
    "hadid": 57,
    "the iron": 57,
    "iron": 57,
    "mujadilah": 58,
    "the pleading woman": 58,
    "she that disputeth": 58,
    "the disputation": 58,
    "hashr": 59,
    "the exile": 59,
    "the gathering": 59,
    "the mustering": 59,
    "mumtahanah": 60,
    "the woman to be examined": 60,
    "she that is to be examined": 60,
    "saff": 61,
    "the ranks": 61,
    "battle array": 61,
    "the row": 61,
    "jumuah": 62,
    "friday": 62,
    "the congregation": 62,
    "the day of congregation": 62,
    "munafiqun": 63,
    "the hypocrites": 63,
    "hypocrites": 63,
    "taghabun": 64,
    "mutual disillusion": 64,
    "the cheating": 64,
    "loss and gain": 64,
    "talaq": 65,
    "divorce": 65,
    "the divorce": 65,
    "tahrim": 66,
    "the prohibition": 66,
    "the banning": 66,
    "prohibition": 66,
    "mulk": 67,
    "the dominion": 67,
    "the sovereignty": 67,
    "dominion": 67,
    "qalam": 68,
    "the pen": 68,
    "pen": 68,
    "haqqah": 69,
    "the reality": 69,
    "the inevitable hour": 69,
    "the sure reality": 69,
    "maarij": 70,
    "the ascending stairways": 70,
    "the ways of ascent": 70,
    "nuh": 71,
    "noah": 71,
    "jinn": 72,
    "the jinn": 72,
    "muzzammil": 73,
    "the enshrouded one": 73,
    "the enfolded one": 73,
    "the mantled one": 73,
    "muddaththir": 74,
    "the cloaked one": 74,
    "the one wrapped up": 74,
    "the one enveloped": 74,
    "qiyamah": 75,
    "the resurrection": 75,
    "resurrection": 75,
    "the rising of the dead": 75,
    "insan": 76,
    "man": 76,
    "the human": 76,
    "dahr": 76,
    "the human being": 76,
    "mursalat": 77,
    "those sent forth": 77,
    "the emissaries": 77,
    "the winds sent forth": 77,
    "naba": 78,
    "the tidings": 78,
    "the announcement": 78,
    "the great news": 78,
    "naziat": 79,
    "those who drag forth": 79,
    "the soul snatchers": 79,
    "those who pull out": 79,
    "abasa": 80,
    "he frowned": 80,
    "the frown": 80,
    "takwir": 81,
    "the overthrowing": 81,
    "the folding up": 81,
    "the shrouding in darkness": 81,
    "infitar": 82,
    "the cleaving": 82,
    "the cleaving asunder": 82,
    "bursting apart": 82,
    "mutaffifin": 83,
    "the defrauding": 83,
    "those who deal in fraud": 83,
    "the cheats": 83,
    "inshiqaq": 84,
    "the splitting open": 84,
    "the sundering": 84,
    "the rending asunder": 84,
    "buruj": 85,
    "the mansions of the stars": 85,
    "the constellations": 85,
    "the great star": 85,
    "tariq": 86,
    "the morning star": 86,
    "the nightcomer": 86,
    "the night visitant": 86,
    "ala": 87,
    "the most high": 87,
    "the all highest": 87,
    "glory to your lord in the highest": 87,
    "ghashiyah": 88,
    "the overwhelming": 88,
    "the pall": 88,
    "the overwhelming event": 88,
    "fajr": 89,
    "dawn": 89,
    "daybreak": 89,
    "balad": 90,
    "the city": 90,
    "the land": 90,
    "city": 90,
    "shams": 91,
    "the sun": 91,
    "sun": 91,
    "layl": 92,
    "the night": 92,
    "night": 92,
    "duha": 93,
    "the morning hours": 93,
    "the forenoon": 93,
    "morning bright": 93,
    "sharh": 94,
    "the relief": 94,
    "the expansion": 94,
    "solace": 94,
    "inshirah": 94,
    "the opening up of the heart": 94,
    "tin": 95,
    "the fig": 95,
    "fig": 95,
    "alaq": 96,
    "the clot": 96,
    "the clinging clot": 96,
    "read": 96,
    "iqra": 96,
    "qadr": 97,
    "the power": 97,
    "the night of decree": 97,
    "power": 97,
    "the majesty": 97,
    "bayyinah": 98,
    "the clear proof": 98,
    "the evidence": 98,
    "the clear evidence": 98,
    "zalzalah": 99,
    "the earthquake": 99,
    "earthquake": 99,
    "the shaking": 99,
    "adiyat": 100,
    "the courser": 100,
    "the chargers": 100,
    "those that run": 100,
    "the war horses": 100,
    "qariah": 101,
    "the calamity": 101,
    "the striking hour": 101,
    "the great calamity": 101,
    "takathur": 102,
    "rivalry in world increase": 102,
    "competition": 102,
    "vying for more and more": 102,
    "asr": 103,
    "the declining day": 103,
    "time": 103,
    "the epoch": 103,
    "the flight of time": 103,
    "humazah": 104,
    "the traducer": 104,
    "the slanderer": 104,
    "the scandalmonger": 104,
    "fil": 105,
    "the elephant": 105,
    "elephant": 105,
    "quraysh": 106,
    "quraish": 106,
    "maun": 107,
    "small kindnesses": 107,
    "almsgiving": 107,
    "the daily necessaries": 107,
    "assistance": 107,
    "kawthar": 108,
    "abundance": 108,
    "the abundance": 108,
    "plenty": 108,
    "the river of abundance": 108,
    "kafirun": 109,
    "the disbelievers": 109,
    "the unbelievers": 109,
    "those who reject faith": 109,
    "nasr": 110,
    "the divine support": 110,
    "the help": 110,
    "succour": 110,
    "victory": 110,
    "masad": 111,
    "the palm fiber": 111,
    "the flame": 111,
    "lahab": 111,
    "the father of flame": 111,
    "twisted strands": 111,
    "ikhlas": 112,
    "the sincerity": 112,
    "the purity of faith": 112,
    "sincerity": 112,
    "the unity": 112,
    "the fidelity": 112,
    "falaq": 113,
    "the daybreak": 113,
    "the dawn": 113,
    "the rising dawn": 113,
    "nas": 114,
    "mankind": 114,
    "the people": 114,
}


@dataclass(frozen=True)
class Citation:
    start: int  # char offset of the citation span in the source text
    end: int  # char offset just past the span (insertion point)
    surah: int
    ayat: int
    raw: str  # the matched citation text


# ── number parsing ────────────────────────────────────────────────────────────

_ONES = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
}
_TENS = {
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}


def parse_number(text: str) -> int | None:
    """Exact integer from a digit string OR an English number-word phrase
    (1-999). Returns None when it cannot parse confidently."""
    s = text.strip().lower().replace("-", " ")
    if s.isdigit():
        return int(s)
    words = [w for w in re.split(r"[\s]+", s) if w and w != "and"]
    if not words:
        return None
    total, current, seen = 0, 0, False
    for w in words:
        if w in _ONES:
            current += _ONES[w]
            seen = True
        elif w in _TENS:
            current += _TENS[w]
            seen = True
        elif w == "hundred":
            current = (current or 1) * 100
            seen = True
        else:
            return None
    if not seen:
        return None
    return total + current


def _norm_surah_name(name: str) -> str:
    s = name.strip().lower()
    # Strip leading qualifiers repeatedly ("the chapter of joseph" -> "joseph").
    prefix = re.compile(r"^(the\s+|surah\s+|surat\s+|sura\s+|chapter\s+(?:of|on)\s+|chapter\s+)")
    while True:
        s2 = prefix.sub("", s, count=1)
        if s2 == s:
            break
        s = s2
    s = s.replace("al-", "").replace("al ", "").replace("'", "").replace("`", "")
    s = re.sub(r"[^a-z\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def surah_number(name: str) -> int | None:
    """Canonical surah number for an English/transliterated name, or None."""
    return _SURAH_NUMBERS.get(_norm_surah_name(name))


_SURAH_NUMBERS = {_norm_surah_name(k): v for k, v in _SURAH_RAW.items()}


# ── citation patterns ───────────────────────────────────────────────────────
# All deterministic. Each yields (surah_token, verse_token) which the resolver
# maps to integers; an unparseable token kills that match (no guess).

_NUM = r"\d{1,3}"
_WORDNUM = r"[a-z\- ]+?"
# "(chapter 14, verse 7)" / "chapter 14 verse 7"
_RE_NUMERIC = re.compile(
    r"\bchapter\s+(?P<surah>%s)\s*,?\s*(?:and\s+)?verse[s]?\s+(?P<verse>%s)" % (_NUM, _NUM), re.IGNORECASE
)
# "the chapter of Abraham, verse seven" / "chapter on Joseph, verse 4"
_RE_PROSE_FWD = re.compile(
    r"\bchapter\s+(?:of|on)\s+(?P<surah>[A-Za-z'`\- ]+?)\s*,?\s*(?:and\s+)?verse[s]?\s+(?P<verse>%s|%s)\b"
    % (_NUM, _WORDNUM),
    re.IGNORECASE,
)
# "verse seven of the chapter of Abraham" / "verse four of the chapter on Joseph"
_RE_PROSE_REV = re.compile(
    r"\bverse[s]?\s+(?P<verse>%s|%s)\s+of\s+the\s+chapter\s+(?:of|on)\s+(?P<surah>[A-Za-z'`\- ]+?)(?=[\.,;:!?\)]|\s+(?:in|and|where|which|the)\b|$)"
    % (_NUM, _WORDNUM),
    re.IGNORECASE,
)


def _verse_from_token(tok: str) -> int | None:
    tok = tok.strip()
    return int(tok) if tok.isdigit() else parse_number(tok)


def find_citations(text: str) -> list[Citation]:
    """Every resolvable Quran citation in *text*, in order, de-overlapped.

    A match whose surah name or verse number does not resolve is dropped
    (never guessed). Overlapping matches keep the earliest/longest.
    """
    found: list[Citation] = []
    for rx, surah_is_num in ((_RE_NUMERIC, True), (_RE_PROSE_FWD, False), (_RE_PROSE_REV, False)):
        for m in rx.finditer(text):
            surah = int(m.group("surah")) if surah_is_num else surah_number(m.group("surah"))
            ayat = _verse_from_token(m.group("verse"))
            if not surah or not ayat or not (1 <= surah <= 114) or ayat < 1:
                continue
            found.append(Citation(m.start(), m.end(), surah, ayat, m.group(0)))
    # De-overlap: sort by start, drop any citation that overlaps one already kept.
    found.sort(key=lambda c: (c.start, -(c.end - c.start)))
    kept: list[Citation] = []
    last_end = -1
    for c in found:
        if c.start >= last_end:
            kept.append(c)
            last_end = c.end
    return kept


# ── verified Arabic lookup ────────────────────────────────────────────────────

_STOP = frozenset(
    "the a an and or of to in on for with as at by is are was were be this that "
    "it its from into not no but who whom your you we our us he she his her him "
    "they them their will shall would lord god allah o ye".split()
)


def _content_words(text: str) -> set[str]:
    return {w for w in re.split(r"[^a-z]+", text.lower()) if len(w) > 3 and w not in _STOP}


def verse_record(surah: int, ayat: int) -> dict | None:
    """Verbatim KQur verse record (mirror-only, read-only), or None.

    Never touches SQL Server — degrades to None if the mirror is absent, so
    the render path never depends on a running server.
    """
    try:
        from source_library_mirror import quran_ayat_lookup
    except Exception:
        return None
    try:
        return quran_ayat_lookup(int(surah), int(ayat))
    except Exception:
        return None


def _verified(rec: dict, context: str, min_overlap: float) -> bool:
    """Lenient guard: the verse's KQur English shares >= min_overlap of its
    content words with the surrounding script text. Catches a spuriously
    resolved citation before its Arabic is recited."""
    if min_overlap <= 0:
        return True
    eng = " ".join(str(rec.get(k) or "") for k in ("pickthall", "asad"))
    vw = _content_words(eng)
    if not vw:
        return True
    cw = _content_words(context)
    return (len(vw & cw) / len(vw)) >= min_overlap


def recitations_for_text(
    text: str, *, verify: bool = False, min_overlap: float = 0.25, log=None
) -> list[tuple[int, str]]:
    """(insertion_offset, arabic) for each citation whose verbatim Arabic was
    found in KQur. insertion_offset is the end of the citation span, so the
    caller splices the Arabic immediately after the citation. A citation that
    does not resolve (unknown surah / bad number) or whose verse is absent from
    KQur yields nothing (and is logged). *verify* (default OFF) adds the strict
    translation-overlap guard — off by default because cross-translation
    differences make it false-negative-prone (see module docstring)."""
    out: list[tuple[int, str]] = []
    for c in find_citations(text):
        rec = verse_record(c.surah, c.ayat)
        arabic = str((rec or {}).get("arabic") or "").strip()
        if not arabic:
            if log:
                log(f"  [recite] {c.surah}:{c.ayat} ({c.raw!r}) — not in KQur; left in English")
            continue
        if verify and not _verified(rec, text, min_overlap):
            if log:
                log(f"  [recite] {c.surah}:{c.ayat} ({c.raw!r}) — strict-verify mismatch; left in English")
            continue
        out.append((c.end, arabic))
    return out


def inject_recitations(text: str, *, verify: bool = False, min_overlap: float = 0.25, log=None) -> str:
    """Return *text* with verbatim Arabic spliced in after each resolvable,
    verified Quran citation. Pure; no-op when nothing resolves."""
    spans = recitations_for_text(text, verify=verify, min_overlap=min_overlap, log=log)
    if not spans:
        return text
    # Splice from the end so earlier offsets stay valid.
    out = text
    for pos, arabic in sorted(spans, key=lambda s: s[0], reverse=True):
        out = out[:pos] + f" «{arabic}»" + out[pos:]
    return out
