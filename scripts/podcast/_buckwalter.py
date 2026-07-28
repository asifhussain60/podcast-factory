"""_buckwalter.py — pure Buckwalter ↔ Arabic transliteration for the Quranic Arabic Corpus.

The corpus morphology file (quranic-corpus-morphology-0.4.txt, GPL, Kais Dukes /
corpus.quran.com) writes every FORM, LEM and ROOT in Buckwalter ASCII — `{ll~ahi`
is ٱللَّهِ, `rHm` is ر-ح-م. Nothing else in this repo speaks Buckwalter, and every
Arabic join in the pipeline runs on the consonantal skeleton from
``_arabic_coverage.normalize_arabic``. This module is the bridge: the standard
Buckwalter table plus the corpus's extended annotation marks, both directions,
and ``bw_skeleton`` — Buckwalter → Arabic → skeleton — as the ONE join key the
morphology layer exposes downstream.

Table source: corpus.quran.com/java/buckwalter.jsp (standard set) and the
JQuranTree extended encoding for Quranic annotation marks. The mapping is
bijective, so ``ar2bw`` is the exact inverse and round-trips are lossless.

Pure — no I/O, no LLM, no state. ``strict=True`` (the default) raises on any
character outside the table rather than guessing: the corpus build uses it to
prove the table covers the whole file ("verify, don't trust"), and a silent skip
here would quietly corrupt a join key.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _arabic_coverage import normalize_arabic

# ─── The table ───────────────────────────────────────────────────────────────
# Standard Buckwalter. Keys are the ASCII the corpus file uses; values are the
# Arabic codepoints they encode. Order follows the corpus documentation page.
_STANDARD: dict[str, str] = {
    "'": "ء",  # ء hamza
    "|": "آ",  # آ alif + madda
    ">": "أ",  # أ hamza on alif
    "&": "ؤ",  # ؤ hamza on waw
    "<": "إ",  # إ hamza under alif
    "}": "ئ",  # ئ hamza on ya
    "A": "ا",  # ا alif
    "b": "ب",  # ب ba
    "p": "ة",  # ة ta marbuta
    "t": "ت",  # ت ta
    "v": "ث",  # ث tha
    "j": "ج",  # ج jim
    "H": "ح",  # ح ha (emphatic)
    "x": "خ",  # خ kha
    "d": "د",  # د dal
    "*": "ذ",  # ذ dhal
    "r": "ر",  # ر ra
    "z": "ز",  # ز zay
    "s": "س",  # س sin
    "$": "ش",  # ش shin
    "S": "ص",  # ص sad
    "D": "ض",  # ض dad
    "T": "ط",  # ط ta (emphatic)
    "Z": "ظ",  # ظ za (emphatic)
    "E": "ع",  # ع ayn
    "g": "غ",  # غ ghayn
    "_": "ـ",  # ـ tatweel
    "f": "ف",  # ف fa
    "q": "ق",  # ق qaf
    "k": "ك",  # ك kaf
    "l": "ل",  # ل lam
    "m": "م",  # م mim
    "n": "ن",  # ن nun
    "h": "ه",  # ه ha
    "w": "و",  # و waw
    "Y": "ى",  # ى alif maqsura
    "y": "ي",  # ي ya
    "F": "ً",  # ً fathatan
    "N": "ٌ",  # ٌ dammatan
    "K": "ٍ",  # ٍ kasratan
    "a": "َ",  # َ fatha
    "u": "ُ",  # ُ damma
    "i": "ِ",  # ِ kasra
    "~": "ّ",  # ّ shadda
    "o": "ْ",  # ْ sukun
    "`": "ٰ",  # ٰ dagger alif
    "{": "ٱ",  # ٱ alif wasla
}

# JQuranTree extended set — the Uthmani-script annotation marks the corpus FORM
# field carries beyond plain letters and harakat (pause marks, small letters).
_EXTENDED: dict[str, str] = {
    "^": "ٓ",  # ٓ maddah above
    "#": "ٔ",  # ٔ hamza above
    ":": "ۜ",  # ۜ small high seen
    "@": "۟",  # ۟ small high rounded zero
    '"': "۠",  # ۠ small high upright rectangular zero
    "[": "ۢ",  # ۢ small high meem (isolated)
    ";": "ۣ",  # ۣ small low seen
    ",": "ۥ",  # ۥ small waw
    ".": "ۦ",  # ۦ small ya
    "!": "ۨ",  # ۨ small high noon
    "-": "۪",  # ۪ empty centre low stop
    "+": "۫",  # ۫ empty centre high stop
    "%": "۬",  # ۬ rounded high stop, filled centre
    "]": "ۭ",  # ۭ small low meem
}

_BW2AR: dict[str, str] = {**_STANDARD, **_EXTENDED}
_AR2BW: dict[str, str] = {v: k for k, v in _BW2AR.items()}
assert len(_AR2BW) == len(_BW2AR), "Buckwalter table must stay bijective"


def bw2ar(text: str, *, strict: bool = True) -> str:
    """Buckwalter → Arabic script. Whitespace passes through unchanged.

    ``strict=True`` raises ``ValueError`` naming every character outside the
    table; ``strict=False`` drops them (used only for skeleton derivation,
    where an unmappable mark cannot be part of the consonant chain anyway).
    """
    out: list[str] = []
    unknown: set[str] = set()
    for ch in text or "":
        if ch in _BW2AR:
            out.append(_BW2AR[ch])
        elif ch.isspace():
            out.append(ch)
        else:
            unknown.add(ch)
    if unknown and strict:
        raise ValueError(f"not Buckwalter: {sorted(unknown)!r} in {text!r}")
    return "".join(out)


def ar2bw(text: str, *, strict: bool = True) -> str:
    """Arabic script → Buckwalter. Exact inverse of ``bw2ar``."""
    out: list[str] = []
    unknown: set[str] = set()
    for ch in text or "":
        if ch in _AR2BW:
            out.append(_AR2BW[ch])
        elif ch.isspace():
            out.append(ch)
        else:
            unknown.add(ch)
    if unknown and strict:
        raise ValueError(f"not mappable Arabic: {sorted(unknown)!r} in {text!r}")
    return "".join(out)


def bw_skeleton(bw: str) -> str:
    """The repo-wide consonantal-skeleton join key for a Buckwalter string.

    Buckwalter → Arabic → ``normalize_arabic`` — the same fold the mushaf check,
    the Arabic audit, and the grounding gate all run on, so a corpus root/lemma
    and a book's own Arabic land on identical keys. Non-strict on purpose: an
    annotation mark outside the table carries no consonant.
    """
    return normalize_arabic(bw2ar(bw, strict=False))


# ─── Romanization folds: matching plain-English terms to Arabic skeletons ────
# Plain journalistic transliteration (the house style — see _translit.py) maps
# Arabic consonants AMBIGUOUSLY: `s` may be س or ص, `h` may be ه or ح, `t` may
# be ت or ط, and ayn/hamza vanish entirely. These folds put BOTH scripts into
# one deliberately-lossy ASCII space where an ambiguous letter and its whole
# Arabic class land on the same symbol. Two strings agreeing here is necessary
# — never sufficient — evidence of identity: every consumer treats a match as a
# candidate to check further (uniqueness, OCR grounding) and a non-match as
# "decline to judge". The lossiness therefore only ever UNDER-fires.
_ARABIC_TO_FOLD = {
    "ب": "b", "ت": "t", "ث": "th", "ج": "j", "ح": "h", "خ": "kh",
    "د": "d", "ذ": "dh", "ر": "r", "ز": "z", "س": "s", "ش": "sh",
    "ص": "s", "ض": "d", "ط": "t", "ظ": "z", "غ": "gh", "ف": "f",
    "ق": "q", "ك": "k", "ل": "l", "م": "m", "ن": "n", "ه": "h",
    "و": "w", "ي": "y",
    # ayn, hamza forms and bare alif carry nothing in plain transliteration.
    "ع": "", "ء": "", "ا": "",
}  # fmt: skip

_LATIN_VOWELS = str.maketrans("", "", "aeiou")


def _collapse(s: str) -> str:
    out: list[str] = []
    for ch in s:
        if not out or out[-1] != ch:
            out.append(ch)
    return "".join(out)


def arabic_fold(skeleton: str) -> str:
    """A ``normalize_arabic`` skeleton → the shared ASCII fold space."""
    return _collapse("".join(_ARABIC_TO_FOLD.get(c, "") for c in skeleton or ""))


def latin_fold(term: str) -> str:
    """A plain-English romanized term/root → the shared ASCII fold space.

    Lowercases, drops separators and apostrophes (ayn/hamza in the house
    style), strips vowels, collapses doubling (shadda): ``tawakkul`` → ``twkl``,
    ``n-f-s`` → ``nfs``, ``shukr`` → ``shkr``.
    """
    s = (term or "").lower()
    s = "".join(c for c in s if c.isascii() and c.isalpha())
    return _collapse(s.translate(_LATIN_VOWELS))


def folds_match(latin: str, arabic_skeleton_fold: str) -> bool:
    """Class-level agreement between a romanized term and an Arabic skeleton fold.

    Exact fold equality, plus the one systematic romanization gap: ta marbuta
    (skeleton ``ه``) is usually silent in plain style — ``sakina`` / سكينه — so
    a single trailing ``h`` on the Arabic side alone also matches.
    """
    if not latin or not arabic_skeleton_fold:
        return False
    return arabic_skeleton_fold == latin or arabic_skeleton_fold == latin + "h"
