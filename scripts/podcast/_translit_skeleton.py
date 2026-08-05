"""Does this Latin string romanize THIS Arabic script? A structural answer.

WHY THIS EXISTS
---------------
`_book_substitution` decides whether to erase an English-lettered word from a
printed page and put Arabic in its place. Until 2026-08-03 it decided by asking
"is this word on a denylist of ninety English words?" — a list seeded, by its own
docstring, for a context where "a wrongly-kept candidate costs one lookup that
finds nothing". Carried into substitution the cost inverts: a miss writes Arabic
over an English word in running prose. `mukhtasar-ul-asar-1` carries a glossary
entry whose phonetic is literally the word `approach`, and the pass was ready to
print "and do not الْمُبَاشَرَة them during that time".

No denylist can be finished. Place names, single-token personal names and every
loanword outside the 21 in `loanwords.json` were never on it, and never could be
without someone remembering to add them.

So this module asks the opposite, closed question, which needs no list at all:
**does the romanization's consonant skeleton fit the script's?** `hudud` fits
`حدود`; `approach` does not fit `المباشرة` and cannot fit any Arabic word, since
Arabic has no `p` and no `ch`. That is positive evidence a human can check by
eye, it is deterministic, and it needs no corpus — which matters, because the
books this guard protects are exactly the ones with no Arabic scan to consult.

WHAT IT DELIBERATELY CANNOT DO
------------------------------
It judges FORM, not meaning. `surah` fits `صُورَة` perfectly well, and `صورة` is
*picture* — the chapter of the Quran is `سورة`. A wrong word that is spelled like
the right one is a glossary error, and the guard against THAT is the annotation
policy: a `legacy` (unclassified) entry is not substitutable at all, so nobody's
un-reviewed harvest reaches the page.

HOW THE MATCH WORKS
-------------------
Both sides reduce to a sequence of consonant units, and the romanization's must
appear IN ORDER inside the script's. Not equality — the script legitimately
carries letters the romanization drops:

    long vowels   `حدود` holds a و that `hudud` writes as the vowel `u`
    the article   `الناطق` holds `ال` that `natiq` leaves off
    hamza / ayn   `النقباء` ends in a ء that `nuqaba` writes as nothing at all

Shadda is expanded first (`تقيّة` is `t q y y h`, and `taqiyya` has the second
`y`), and ta marbuta matches either `h` or `t` because it is read both ways
(`دعاة` is `duat` in construct, `dawah` in pause).

Three ways a romanization legitimately fails a naive left-to-right scan, all
found by running this against the nine live glossaries and all handled by
searching rather than by loosening the letters:

    digraphs are ambiguous  `Fathiyyah` is `fa-t-h-iyyah` (فتح), not `fa-th-`.
                            `Ashab` is `a-s-h-ab` (أصحاب), not `a-sh-ab`. So a
                            digraph is TRIED, and the two letters are tried too.
    tanween is a letter     `Taubatun Nasuh` writes the `n` of `-un` that `ٌ`
                            carries as a mark, and the marks are stripped.
    gemination is optional  `al-haqq` doubles a `q` that plain `الحق` writes
                            once, because shadda is a mark the scan just removed.
"""

from __future__ import annotations

import re
import unicodedata

#: Arabic letter -> the Latin unit(s) a transliteration may write for it.
#: An empty string in the set means the letter may go unwritten — true of the
#: hamza family, of ayn, and of the long vowels و/ي, whose vowel reading the
#: romanization spells as `u`/`i` and this comparison has already discarded.
_LETTER: dict[str, frozenset[str]] = {
    "ا": frozenset({""}),
    "أ": frozenset({""}),
    "إ": frozenset({""}),
    "آ": frozenset({""}),
    "ء": frozenset({""}),
    "ؤ": frozenset({"", "w"}),
    "ئ": frozenset({"", "y"}),
    "ى": frozenset({""}),
    "ع": frozenset({""}),
    "ب": frozenset({"b"}),
    "ت": frozenset({"t"}),
    "ث": frozenset({"th", "t", "s"}),
    "ج": frozenset({"j", "g"}),
    "ح": frozenset({"h"}),
    "خ": frozenset({"kh", "k"}),
    "د": frozenset({"d"}),
    "ذ": frozenset({"dh", "d", "z"}),
    "ر": frozenset({"r"}),
    "ز": frozenset({"z"}),
    "س": frozenset({"s"}),
    "ش": frozenset({"sh"}),
    "ص": frozenset({"s"}),
    "ض": frozenset({"d", "z"}),
    "ط": frozenset({"t"}),
    "ظ": frozenset({"z", "dh"}),
    "غ": frozenset({"gh", "g"}),
    "ف": frozenset({"f"}),
    "ق": frozenset({"q", "k"}),
    "ك": frozenset({"k"}),
    "ل": frozenset({"l"}),
    "م": frozenset({"m"}),
    "ن": frozenset({"n"}),
    "ه": frozenset({"h"}),
    "ة": frozenset({"h", "t", ""}),
    "و": frozenset({"w", ""}),
    "ي": frozenset({"y", ""}),
    "ﷲ": frozenset({"llh"}),
}

#: Every form the letter alef takes. Its only job here is recognising `\u0627\u0644`.
_ALEF = frozenset("\u0627\u0623\u0625\u0622")
_SHADDA = "\u0651"
#: Tanween — the doubled final vowel signs, read `-un` / `-an` / `-in`. Not
#: decoration either: a romanization that spells the reading out carries an `n`
#: that no letter accounts for, which is how `Taubatun Nasuh` failed.
_TANWEEN = frozenset("\u064b\u064c\u064d")
#: Every other combining mark Arabic writes above or below a letter.
_MARKS = re.compile("[\u064e-\u0650\u0652-\u065f\u0670\u06d6-\u06ed]")

#: Latin digraphs that MAY stand for one Arabic letter. Only ever a maybe: the
#: two-letter reading is tried as well, or `Fathiyyah` (فتح) is read as `fa-th-`.
_DIGRAPHS = frozenset({"th", "kh", "dh", "sh", "gh"})
#: Consonants an Arabic word can be built from. Anything else — `p`, `v`, `x`, a
#: bare `c` — is proof on its own that the Latin string is not Arabic.
_CONSONANTS = frozenset("btjhdrzsfqklmnwyg")
#: Dropped before the skeleton is taken: vowels, the marks a scholarly
#: transliteration adds, and the punctuation that stands for hamza and ayn.
_SKIP = frozenset("aeiou'\u2019`\u02bf\u02be- \t.,/()")


#: The one-letter words Arabic writes joined to the next: `wa-` and, `bi-` with,
#: `li-` for, `ka-` like, `fa-` so. An article behind one of these is still an
#: article — `وَالنَّهْي` is `wa'l-nahy`, which `Wa Nahi` romanizes without the `l`.
_PROCLITIC = frozenset("وفبكل")


def _article_start(text: str, j: int) -> bool:
    """Does the alef at ``j`` open a word, allowing one joined proclitic?"""
    if j == 0 or text[j - 1].isspace():
        return True
    return text[j - 1] in _PROCLITIC and (j == 1 or text[j - 2].isspace())


def _script_units(script: str) -> list[frozenset[str]] | None:
    """The script as a sequence of Latin-unit alternatives, or None if not Arabic."""
    text = _MARKS.sub("", unicodedata.normalize("NFC", script or ""))
    units: list[frozenset[str]] = []
    for i, ch in enumerate(text):
        # THE DEFINITE ARTICLE, and why it is handled here rather than by letting
        # the search skip freely. `natiq` is a perfect romanization of `الناطق`
        # and spells no `l` at all; so is `duat` of `الدعاة`. A matcher allowed to
        # skip any unmatched letter would also accept nonsense, so only the lam
        # of a word-initial `ال` is made optional — the one letter a romanization
        # routinely drops.
        if ch == "ل" and i and text[i - 1] in _ALEF and _article_start(text, i - 1):
            units.append(frozenset({"l", ""}))
            continue
        if ch == _SHADDA:
            # Shadda doubles the letter it sits on, and the romanization is free
            # to write that or not — so the second copy is OPTIONAL. `taqiyya`
            # writes both of `تقيّة`'s y's; `natiq` writes neither of the n's in
            # `النَّاطِق`, where the shadda is only the article assimilating to a
            # sun letter and no reader expects to see it.
            if units:
                units.append(units[-1] | {""})
            continue
        if ch in _TANWEEN:
            units.append(frozenset({"n", ""}))
            continue
        opts = _LETTER.get(ch)
        if opts is not None:
            units.append(opts)
        elif ch.isalnum():
            return None  # a Latin letter or a digit inside the "script" field
    return units or None


def _roman_letters(phonetic: str) -> str | None:
    """The romanization stripped to consonant letters, or None if it cannot be
    Arabic at all. Left as a STRING, not tokenized: whether `th` is one letter or
    two is a question only the script can answer, so the search decides it."""
    text = unicodedata.normalize("NFD", str(phonetic or "").lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    out: list[str] = []
    for ch in text:
        if ch in _SKIP:
            continue
        if ch in _CONSONANTS:
            out.append(ch)
            continue
        return None  # `p`, `v`, `x`, a bare `c`: no Arabic letter makes this sound
    return "".join(out)


def _matches(roman: str, units: list[frozenset[str]]) -> bool:
    """Can every letter of ``roman`` be consumed, in order, by ``units``?

    A memoized search rather than a scan, because three of the moves are choices
    the left-to-right reading gets wrong as often as right: taking a digraph or
    its two letters, skipping a script letter the romanization does not write,
    and collapsing a doubled consonant the script leaves unmarked.
    """
    seen: set[tuple[int, int]] = set()
    stack = [(0, 0)]
    while stack:
        state = stack.pop()
        if state[0] >= len(roman):
            return True
        if state in seen:
            continue
        seen.add(state)
        ri, si = state
        # Gemination: `al-haqq` doubles a `q` that plain `الحق` writes once.
        if ri and roman[ri] == roman[ri - 1]:
            stack.append((ri + 1, si))
        if si >= len(units):
            continue
        opts = units[si]
        if "" in opts:  # a letter the romanization need not write
            stack.append((ri, si + 1))
        if roman[ri] in opts:
            stack.append((ri + 1, si + 1))
        two = roman[ri : ri + 2]
        if two in _DIGRAPHS and two in opts:
            stack.append((ri + 2, si + 1))
    return False


def romanizes(phonetic: str, script: str) -> bool:
    """Could ``phonetic`` be a transliteration of ``script``?

    Conservative in the direction that matters: a False here only means the pass
    leaves the English word alone, which is what the page already prints.
    """
    roman = _roman_letters(phonetic)
    units = _script_units(script)
    if not roman or units is None:
        return False
    variants = [roman]
    # The English plural of an Arabic term — `natiqs`, `hujjas`. The book writes
    # it; the script never carries it.
    if len(roman) > 1 and roman.endswith("s"):
        variants.append(roman[:-1])
    # A leading article the romanization spells and the script may not repeat,
    # or the reverse (`al-hawala` against a bare `حول`).
    for base in list(variants):
        if len(base) > 1 and base[0] == "l":
            variants.append(base[1:])
    return any(_matches(v, units) for v in variants)
