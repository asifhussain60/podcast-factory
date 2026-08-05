"""_translit.py — Simplify scholarly Arabic transliteration to plain English.

Converts academic ALA-LC / IJMES transliteration (macrons + under-dots + the
ayn/hamza modifier letters) into the plain journalistic transliteration used in
the reading-edition book body and on the Podcast Factory Astro Site.

  Kīmiyāʾ al-Saʿāda   → Kimiya al-Saada
  Iḥyāʾ ʿUlūm al-Dīn  → Ihya Ulum al-Din
  Jawāhir al-Qurʾān   → Jawahir al-Quran
  Minhāj al-ʿĀbidīn   → Minhaj al-Abidin

Rules:
  - macrons / under-dots / over-dots on LATIN letters → stripped to the base letter
  - ʿ (ayn) and ʾ (hamza), and their curly-quote variants → DROPPED. The house
    style is plain letters: Quran, not Qur'an; duat, not du'at.
  - an apostrophe is kept ONLY where it is genuinely English — a clitic (God's,
    don't, we'll), a plural or name possessive (the brothers' books, Moses'
    staff), or a listed elision (o'clock). Everything else folds away.
  - ARABIC SCRIPT IS NEVER TOUCHED — Arabic harakat (combining vowel marks) are
    also category Mn, so we only strip combining marks that sit on a Latin base.

TypeScript mirror: plan-dashboard/src/lib/translit.ts — keep the two in sync
(see CLAUDE.md "TS↔Python mirror files").
"""

from __future__ import annotations

import unicodedata

# ayn / hamza modifier letters + curly-quote glyphs the LLM uses for them.
_AYN_HAMZA = "ʿʾʻʼˈ’‘ʹ׳'"
_SENTINEL = "\x00"

# The complete set of word-endings that make an apostrophe genuinely English.
# An apostrophe followed by anything else is an ayn/hamza and is dropped.
_ENGLISH_CLITICS = frozenset({"s", "t", "d", "m", "re", "ve", "ll"})

# The one common English word whose apostrophe marks an elision rather than a
# clitic. Without this, "o'clock" folded to "oclock".
_ELISIONS = {("o", "clock")}


def simplify_transliteration(text: str) -> str:
    """Return *text* with scholarly Arabic diacritics reduced to plain English.
    Arabic-script substrings (and their harakat) are preserved untouched."""
    if not text:
        return text

    # 1. Fold ayn/hamza (and apostrophe-like glyphs) to a sentinel for later
    #    boundary-aware handling.
    text = "".join(_SENTINEL if c in _AYN_HAMZA else c for c in text)

    # 2. Strip macrons/under-dots from LATIN transliteration only. We decompose
    #    PER CHARACTER (never the whole string) so Arabic script — whose harakat
    #    are also category Mn — is passed through byte-for-byte untouched.
    out: list[str] = []
    last_base_latin = False
    for c in text:
        if unicodedata.category(c) == "Mn":
            # combining mark already separate in the input: drop only off Latin
            if not last_base_latin:
                out.append(c)
            continue
        nfd = unicodedata.normalize("NFD", c)
        if len(nfd) > 1 and "LATIN" in unicodedata.name(nfd[0], ""):
            out.append(nfd[0])  # precomposed Latin (ā, ḥ, …) → base letter
            last_base_latin = True
        else:
            out.append(c)  # Arabic, ASCII, punctuation → unchanged
            last_base_latin = "LATIN" in unicodedata.name(c, "")
    folded = "".join(out)

    # 3. Resolve the sentinel: keep an apostrophe ONLY where it is genuinely
    #    English. Everywhere else it came from an ayn/hamza, and the house style
    #    is plain letters — Quran, not Qur'an. Three ways to earn one:
    #
    #      a) a clitic suffix at the end of the word — God's, don't, we'll
    #      b) word-final after an s — the PLURAL or name possessive:
    #         "the brothers' books", "Moses' staff". Both occur in the live
    #         book, and an earlier version of this rule silently deleted them
    #         ("the scholars' books" -> "the scholars books"). The `s` is what
    #         separates them from a transliteration that merely ends in an ayn
    #         (sama', Shia'), which still folds away.
    #      c) a listed elision — o'clock
    #
    #    Deliberately a rule and not a term list: a new Arabic name must not
    #    need a code edit to be spelled correctly.
    #      d) a QUOTATION MARK, decided by pairing rather than locally.
    #
    #    (d) exists because the local rules cannot tell `Allah'` closing a quoted
    #    phrase from `sama'` ending in an ayn — the shapes are identical, a letter
    #    before and a non-letter after. Judged alone, both folded, and the fold
    #    silently destroyed quoted speech: `He said, 'Go now.'` printed as
    #    `He said, Go now.`, and 7 quoted spans vanished from
    #    `the-master-and-the-disciple` and 18 from `asaas-al-taveel` the first time
    #    the apparatus ran over them.
    #
    #    An OPENING quote is unambiguous — no transliteration begins with an ayn
    #    preceded by whitespace — so it is recognised locally, and only while one
    #    is open is a closer allowed. State resets at every newline: an unbalanced
    #    quote then costs at most one stray apostrophe on one line, whereas the
    #    error in the other direction costs the reader a quotation.
    res: list[str] = []
    in_quote = False
    for i, c in enumerate(folded):
        if c == "\n":
            in_quote = False
        if c == _SENTINEL:
            prev = folded[i - 1] if i > 0 else ""
            nxt = folded[i + 1] if i + 1 < len(folded) else ""
            # `prev != "-"`, not `prev not in "-"`: the empty string IS a
            # substring of "-", so the membership form silently refused to open a
            # quote at the very start of a line.
            if not in_quote and not prev.isalpha() and prev != "-" and nxt.isalpha():
                in_quote = True
                res.append("'")
                continue
            if in_quote and (prev.isalpha() or prev in ".,!?;:") and not nxt.isalpha():
                in_quote = False
                res.append("'")
                continue
            j = i + 1
            while j < len(folded) and folded[j].isalpha():
                j += 1
            suffix = folded[i + 1 : j]
            keep = (
                prev.isalpha()
                and (
                    suffix.lower() in _ENGLISH_CLITICS
                    or (not suffix and prev.lower() == "s")
                    or (prev.lower(), suffix.lower()) in _ELISIONS
                )
            ) or (
                # A ROOT RADICAL, not a diacritic: in a citation like the root of
                # Sharia "(sh-r-ʿ)" the ayn IS the third consonant. Folding it
                # away printed "(sh-r-)" — a two-letter root with a dangling
                # hyphen, making a claim the reader can see is false. A hyphen
                # before and nothing after marks that position; "al-ʿAbidin"
                # has a suffix, so it still folds to "al-Abidin".
                prev == "-" and not suffix
            )
            if keep:
                res.append("'")
        else:
            res.append(c)
    return "".join(res)


# Self-test — run `python3 scripts/podcast/_translit.py`.
if __name__ == "__main__":
    CASES = [
        ("Kīmiyāʾ al-Saʿāda", "Kimiya al-Saada"),
        ("Iḥyāʾ ʿUlūm al-Dīn", "Ihya Ulum al-Din"),
        ("Jawāhir al-Qurʾān", "Jawahir al-Quran"),
        ("Minhāj al-ʿĀbidīn", "Minhaj al-Abidin"),
        ("Arbaʿīn", "Arbain"),
        ("Sharīʿah", "Shariah"),
        ("mujāhadah", "mujahadah"),
        ("Ḥasan al-Baṣrī", "Hasan al-Basri"),
        ("Ayyuhā al-Walad", "Ayyuha al-Walad"),
        # Arabic script must survive untouched (vowel marks kept):
        ("وَأَنْ لَيْسَ", "وَأَنْ لَيْسَ"),
        # English possessives and contractions keep their apostrophe …
        ("God's mercy", "God's mercy"),
        ("the book's own voice", "the book's own voice"),
        (
            "don't and we'll and I've and they're and he'd and I'm",
            "don't and we'll and I've and they're and he'd and I'm",
        ),
        # … while ayn/hamza in a transliterated term does not.
        ("Qur'an and Qur'anic", "Quran and Quranic"),
        ("du'at, Ka'b, ta'wil, da'wa, Ja'far, Shu'ayb", "duat, Kab, tawil, dawa, Jafar, Shuayb"),
        ("Bayt al-Ma'mur", "Bayt al-Mamur"),
        # A possessive ON a transliterated name still reads as English.
        ("Salih's road", "Salih's road"),
        # Plural and name possessives keep theirs — an earlier rule deleted these.
        ("the brothers' books", "the brothers' books"),
        ("Moses' staff", "Moses' staff"),
        ("the scholars' obligation", "the scholars' obligation"),
        # …but a transliteration merely ENDING in an ayn still folds away.
        ("sama' and Shia'", "sama and Shia"),
        # The one elision worth keeping.
        ("five o'clock", "five o'clock"),
        # A ROOT RADICAL survives — the ayn IS the third consonant here.
        ("The root of Sharia (sh-r-\u02bf)", "The root of Sharia (sh-r-')"),
        # …but a hyphen followed by MORE letters is an ordinary prefix.
        ("Minh\u0101j al-\u02bf\u0100bid\u012bn", "Minhaj al-Abidin"),
    ]
    failures = 0
    for src, want in CASES:
        got = simplify_transliteration(src)
        ok = got == want
        failures += not ok
        print(f"{'ok ' if ok else 'XX '} {src!r} -> {got!r}" + ("" if ok else f"  (want {want!r})"))
    raise SystemExit(1 if failures else 0)
