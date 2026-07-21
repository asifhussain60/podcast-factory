"""_translit.py — Simplify scholarly Arabic transliteration to plain English.

Converts academic ALA-LC / IJMES transliteration (macrons + under-dots + the
ayn/hamza modifier letters) into the plain journalistic transliteration used in
the reading-edition book body and on the Podcast Factory Astro Site.

  Kīmiyāʾ al-Saʿāda   → Kimiya al-Sa'ada
  Iḥyāʾ ʿUlūm al-Dīn  → Ihya Ulum al-Din
  Jawāhir al-Qurʾān   → Jawahir al-Qur'an
  Minhāj al-ʿĀbidīn   → Minhaj al-Abidin

Rules:
  - macrons / under-dots / over-dots on LATIN letters → stripped to the base letter
  - ʿ (ayn) and ʾ (hamza), and their curly-quote variants → an apostrophe, then
    that apostrophe is KEPT only between two letters; dropped at a word's
    start/end or next to a space/hyphen (so ʿUlūm→Ulum, Saʿāda→Sa'ada).
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

    # 3. Resolve the sentinel: keep an apostrophe ONLY where it is an English
    #    contraction or possessive. Everywhere else it came from an ayn/hamza,
    #    and the house style is plain letters — Quran, not Qur'an (see
    #    _ENGLISH_CLITICS). The discriminator is what FOLLOWS the apostrophe to
    #    the end of the word, so "God's"/"don't" keep theirs while "Qur'an",
    #    "du'at", "Ja'far", "Ma'mur" and "ta'wil" lose theirs. It is deliberately
    #    a rule and not a term list: a new Arabic name must not need a code edit.
    res: list[str] = []
    for i, c in enumerate(folded):
        if c == _SENTINEL:
            prev = folded[i - 1] if i > 0 else ""
            j = i + 1
            while j < len(folded) and folded[j].isalpha():
                j += 1
            suffix = folded[i + 1 : j]
            if prev.isalpha() and suffix.lower() in _ENGLISH_CLITICS:
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
    ]
    failures = 0
    for src, want in CASES:
        got = simplify_transliteration(src)
        ok = got == want
        failures += not ok
        print(f"{'ok ' if ok else 'XX '} {src!r} -> {got!r}" + ("" if ok else f"  (want {want!r})"))
    raise SystemExit(1 if failures else 0)
