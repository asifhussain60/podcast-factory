"""_tts_sanitize.py — shared text-sanitization rules for NotebookLM-bound files.

NOTE: This module is also imported by `restructure_episode_prompt.py` for its
HARD_CONSTRAINTS block, but that block is defined inline in the restructure
script — not here. If updating the forbidden-phrases list or the anti-padding
wording, edit `restructure_episode_prompt.py`'s HARD_CONSTRAINTS constant.


Centralizes the substitution maps used by both `sanitize_chapter_for_tts.py`
(applied to chapter sources, which the TTS reads literally) and
`restructure_episode_prompt.py` (applied to episode customise prompts).

Why both files need the same rules: NotebookLM's two-stage pipeline reads the
chapter source as the ground-truth content and the episode prompt as the
director's brief. The TTS engine speaks tokens that appear in BOTH; if a
diacritic-bearing token lives in either file the TTS may spell it letter by
letter or fabricate pronunciation. Sanitizing both is necessary.

The substitution lists were derived from RCA of EP14 KaR first-run (where
huwa was spelled "H-O-wa", al-mubdi was spoken "El-Mud", Du'a Arafa was
"D-O-A-R-O-F-A") and the Ch07 prior run (al-Kirmani spoken five different
ways, "Surah cough" for Surah Qaf, etc.). Subsequent Azure verbatim
transcription of the EP14 re-run validated that natural ASCII
transliteration with diacritics stripped pronounces correctly, except for
three residual cases: `Tawhid` slurs to "Tahit" late in long episodes (force
`Taw-heed`), `Ma'add ibn Isma'il` is broken into a phantom pause around the
hyphen-laden name (use `Ma'ad ibn Ismail`), and `soteriology` is mispronounced
"satiriology" (paraphrase to `the theology of salvation`).

USAGE — as a module:

    from _tts_sanitize import sanitize_text, SubstitutionReport
    new_text, report = sanitize_text(original_text)

The wrapper scripts in this directory invoke these functions and write the
result back to disk.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Pattern


# ---------------------------------------------------------------------------
# Diacritic → ASCII map. Covers every non-ASCII char observed in KaR source
# files (audit: ï ā ʾ ʿ ḍ ḥ ṣ ṭ ẓ ī ū ē). Em-dash and arrow and ellipsis are
# TTS-safe and left alone.
# ---------------------------------------------------------------------------
DIACRITIC_MAP: dict[str, str] = {
    "ʿ": "",   # Arabic ayin transliteration marker
    "ʾ": "",   # Arabic hamza transliteration marker
    "ʻ": "",   # turned comma (alt ayin)
    "ʼ": "",   # modifier apostrophe (alt hamza)
    "ḥ": "h", "Ḥ": "H",
    "ṭ": "t", "Ṭ": "T",
    "ḍ": "d", "Ḍ": "D",
    "ṣ": "s", "Ṣ": "S",
    "ẓ": "z", "Ẓ": "Z",
    "ī": "i", "Ī": "I",
    "ū": "u", "Ū": "U",
    "ā": "a", "Ā": "A",
    "ē": "e", "Ē": "E",
    "ō": "o", "Ō": "O",
    "ï": "i", "Ï": "I",
    "ñ": "n", "Ñ": "N",
}


def _strip_diacritics(text: str) -> tuple[str, int]:
    """Strip diacritic chars by direct map + NFD fallback. Returns (new_text, n_changes)."""
    n = 0
    for src, dst in DIACRITIC_MAP.items():
        if src in text:
            n += text.count(src)
            text = text.replace(src, dst)
    # NFD fallback for any combining-mark diacritics we missed (preserves base char)
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    if stripped != decomposed:
        n += sum(1 for c in decomposed if unicodedata.category(c) == "Mn")
    return unicodedata.normalize("NFC", stripped), n


# ---------------------------------------------------------------------------
# Compound Arabic term substitutions. Applied longest-first via the ordered
# list. Source-text only; the episode prompt's HARD CONSTRAINTS Required
# Spellings table is the canonical pronunciation reference and uses the same
# right-hand forms.
#
# Convention: natural English transliteration, ASCII-only, no internal
# hyphens on proper names. Hyphenation only on `Taw-heed` (forced phonetic
# to prevent slur observed in EP14 verbatim audit).
# ---------------------------------------------------------------------------
ARABIC_TERM_SUBS: list[tuple[str, str]] = [
    # ===== LEGACY PHONETIC CLEANUP (from EP14 hand-edit pre-pipeline era) =====
    # These hyphenated forms (al-Moob-dee, Hoo-sayn, etc.) lived in ch14
    # before the script was built. Map them to the current natural-ASCII
    # convention so all 15 chapters are uniform.
    ("Mah-add ibn is-Maa-eel",  "Maad ibn Ismail"),
    ("Im-ran ibn hoo-Sayn",     "Imran ibn Husayn"),
    ("Doo-ah ah-Rah-fah",       "the Supplication of Arafa"),
    ("al-Moob-dee al-Aw-wal",   "al-Mubdi al-Awwal"),
    ("al-Moob-dee",             "al-Mubdi"),
    ("al-Yowm al-Aa-khir",      "the Last Day"),
    ("al-Woo-jood al-Haqq",     "the true existence"),
    ("al-Noo-ta-kaa",           "the speaker-Prophets"),
    ("Ah-rah-faht",             "Arafat"),
    ("Kar-bah-lah",             "Karbala"),
    ("Hoo-sayn",                "Hussain"),
    ("Sha-ree-ah",              "sacred law"),
    ("Taw-heed",                "Divine Oneness"),
    ("Dah-wah",                 "the mission"),
    ("Ma-waa-lee",              "the loyalists"),
    ("Bah-tin",                 "the hidden"),
    ("Zah-hir",                 "the apparent"),
    ("Hoo-wah",                 "huwa"),
    ("Ah-rah-fah",              "Arafa"),
    ("Ah-lee",                  "Ali"),
    ("ib-Dah",                  "origination"),
    ("Dah-ees",                 "the missionaries"),
    ("Taa-weel",                "inner interpretation"),

    # ASIF-APPROVED 2026-05-23 (after EP09): Translate Arabic concept terms to
    # English equivalents. Eliminates an entire class of TTS pronunciation
    # failures (Tawhid → "Tahit" slur, daʿwa → spelling artifacts, Qaaf →
    # "Cough", etc.) and improves audio accessibility. Proper names and the
    # pronoun "huwa" (which the source discusses AS A WORD) are retained.

    # ===== COMPOUND FORMS (longest first to avoid partial matches) =====
    ("Maʿadd ibn Isma'il",      "Maad ibn Ismail"),
    ("Ma'add ibn Isma'il",      "Maad ibn Ismail"),
    ("Maʿadd ibn Ismaʾil",      "Maad ibn Ismail"),
    ("Duʿa ʿArafa",             "the Supplication of Arafa"),
    ("Du'a Arafa",              "the Supplication of Arafa"),
    ("Dua Arafa",               "the Supplication of Arafa"),  # already-sanitized form
    ("Day of ʿArafa",           "Day of Arafa"),
    ("Imran ibn Husayn",        "Imran ibn Husayn"),  # proper name — KEEP
    ("al-aimma al-bararah",     "the righteous successors"),  # English gloss
    ("al-wujud al-haqq",        "the true existence"),
    ("al-yawm al-akhir",        "the Last Day"),
    ("al-nuṭaqāʾ",              "the speaker-Prophets"),
    ("al-nutaqa'",              "the speaker-Prophets"),

    # ===== CORE CONCEPT TRANSLATIONS (Asif-approved set) =====

    # Tawhid → Divine Oneness. Includes already-sanitized "Taw-heed" form.
    ("Taw-heed",                "Divine Oneness"),
    ("taw-heed",                "divine oneness"),
    ("Tawheed",                 "Divine Oneness"),
    ("Tawhid",                  "Divine Oneness"),
    ("tawhid",                  "divine oneness"),

    # Shariah → sacred law. Includes prior-sanitize "Sharia" form.
    ("Shariʿah",                "sacred law"),
    ("Shari'ah",                "sacred law"),
    ("Shariah",                 "sacred law"),
    ("Sharia",                  "sacred law"),
    ("sharia",                  "sacred law"),

    # taʾwil → inner interpretation. Includes prior "taweel" / "tawil" forms.
    ("taʾwil",                  "inner interpretation"),
    ("ta'wil",                  "inner interpretation"),
    ("Taweel",                  "Inner interpretation"),
    ("taweel",                  "inner interpretation"),
    ("tawil",                   "inner interpretation"),
    ("tāʾwil",                  "inner interpretation"),

    # daʿwa → the mission. Includes prior "Dawa" form.
    # Handle "the daʿwa" / "the Dawa" first to avoid "the the mission".
    ("the daʿwa",               "the mission"),
    ("the da'wa",               "the mission"),
    ("the Dawa",                "the mission"),
    ("the dawa",                "the mission"),
    ("daʿwa",                   "the mission"),
    ("Daʿwa",                   "The mission"),
    ("da'wa",                   "the mission"),
    ("Da'wa",                   "The mission"),
    ("Dawa",                    "the mission"),
    ("dawa",                    "the mission"),

    # ibdaʿ → origination.
    ("ibdaʿ",                   "origination"),
    ("ibda'",                   "origination"),
    ("Ibda",                    "Origination"),
    ("ibda",                    "origination"),

    # zahir → the apparent. Handle "the zahir" first.
    ("the zahir",               "the apparent"),
    ("the Zahir",               "the apparent"),
    ("Zahir",                   "The apparent"),
    ("zahir",                   "the apparent"),

    # batin → the hidden. Handle "the batin" first.
    ("the batin",               "the hidden"),
    ("the Batin",               "the hidden"),
    ("Batin",                   "The hidden"),
    ("batin",                   "the hidden"),

    # shirk → associating partners with God.
    ("Shirk",                   "Associating partners with God"),
    ("shirk",                   "associating partners with God"),

    # ===== ARABIC LETTER NAMES (from EP09 audit — TTS reads them as English) =====
    ("Alif, Dal, Mim",          "Aleef, Daal, Meem"),
    ("Mim-Waw-Sin-Ya",          "Meem-Waaw-Seen-Yaa"),
    ("Alif-Ba-Ra-Ha-Ya-Mim",    "Aleef-Baa-Raa-Haa-Yaa-Meem"),
    ("Nun-Waw-Ha",              "Noon-Waaw-Haa"),
    ("Ayn-Ya-Sin-Ya",           "Ayn-Yaa-Seen-Yaa"),
    ("Mim-Ha-Mim-Dal",          "Meem-Haa-Meem-Daal"),
    (" vowel kaf ",             " vowel Kaaf "),
    (" consonant nun ",         " consonant Noon "),
    (" the kaf ",               " the Kaaf "),
    (" the nun ",               " the Noon "),

    # ===== KEEP AS-IS (proper names + pronoun-as-word per Asif split) =====
    # huwa is discussed in the source AS a word (the philosophical point is
    # that it's the only pronoun fit for God); keep so the doctrinal moment
    # lands properly.
    ("huwa",                    "huwa"),
    ("Huwa",                    "Huwa"),

    # Persian/Arabic proper names with ASCII apostrophes that TTS misreads.
    ("Sa'di",                   "Saadi"),
    ("Hu'd",                    "Hud"),

    # Proper nouns — kept (declared for sanitize-report visibility)
    ("Karbala",                 "Karbala"),
    ("Arafat",                  "Arafat"),
    ("Hussain",                 "Hussain"),
    ("al-mubdi",                "al-Mubdi"),
    ("mawali",                  "the loyalists"),  # gloss for clarity
]


# ---------------------------------------------------------------------------
# Quranic surah substitution. Replaces "(Quran X:Y)" / "(Quran X)" with the
# English chapter name inlined. NotebookLM's first KaR run said "Surah ash-
# Shams" and "Surah cough" (for Surah Qaf) because the recipe's negative
# rule ("don't use Arabic surah names") didn't supply positive substitutes
# at the source level.
#
# Map covers every surah cited across the 15 KaR chapters (audited via grep).
# Add new entries here when new books cite new surahs.
# ---------------------------------------------------------------------------
SURAH_NAMES: dict[int, str] = {
    3:   "the chapter of the family of Imran",
    5:   "the chapter of the table spread",
    6:   "the chapter of cattle",
    7:   "the chapter of the heights",
    13:  "the chapter of thunder",
    15:  "the chapter of the rocky tract",
    16:  "the chapter of the bee",
    17:  "the chapter of the night journey",
    2:   "the chapter of the Cow",
    4:   "the chapter of women",
    11:  "the chapter of Hud",
    18:  "the chapter of the cave",
    21:  "the chapter of the Prophets",
    23:  "the chapter of the believers",
    25:  "the chapter of the criterion",
    33:  "the chapter of the confederates",
    36:  "the chapter of Ya-Seen",
    41:  "the chapter explained in detail",
    42:  "the chapter of consultation",
    50:  "the chapter of Qaaf",
    53:  "the chapter of the star",
    54:  "the chapter of the moon",
    57:  "the chapter of iron",
    70:  "the chapter of the ascending stairways",
    89:  "the chapter of the dawn",
    91:  "the chapter of the sun",
    112: "the chapter of sincerity",
}


# Pattern: (Quran 12:34), (Quran 12:34–56), (Quran 12:34-56), (Quran 12)
# Optional trailing "translation/note" content is preserved.
_QURAN_RE = re.compile(
    r"\(Quran\s+(\d+)(?::(\d+(?:[–\-]\d+)?))?([^)]*)\)"
)


def _substitute_surah(match: re.Match) -> str:
    surah = int(match.group(1))
    verses = match.group(2)
    extra = match.group(3) or ""
    name = SURAH_NAMES.get(surah)
    if not name:
        # Unknown surah — leave the original citation intact, flag in report
        return match.group(0)
    # Idempotency guard: if the citation has already been expanded (extra text
    # already contains "the chapter of"), leave it alone.
    if "the chapter of" in extra.lower() or "the chapter explained" in extra.lower():
        return match.group(0)
    if verses:
        # Normalize en-dash to "through"
        if "–" in verses or "-" in verses:
            verses = re.sub(r"[–\-]", " through ", verses)
            piece = f"verses {verses}"
        else:
            piece = f"verse {verses}"
        return f"(Quran {surah}, {name}, {piece}{extra})"
    return f"(Quran {surah}, {name}{extra})"


# Pre-name and "Surah <Arabic>" inline phrases that crept into the source
# from earlier authoring passes. Replaced inline.
_PRE_SURAH_REPLACEMENTS: list[tuple[Pattern, str]] = [
    (re.compile(r"Surah\s+the\s+the\s+chapter\s+", re.IGNORECASE),
     "the chapter "),
    (re.compile(r"Surah\s+the\s+chapter\s+", re.IGNORECASE),
     "the chapter "),
    (re.compile(r"Surah\s+ash-Shams\b", re.IGNORECASE),  "the chapter of the sun"),
    (re.compile(r"Surah\s+Al-Isra\b",   re.IGNORECASE),  "the chapter of the night journey"),
    (re.compile(r"Surah\s+Al-Imran\b",  re.IGNORECASE),  "the chapter of the family of Imran"),
    (re.compile(r"Surah\s+Al-Hadid\b",  re.IGNORECASE),  "the chapter of iron"),
    (re.compile(r"Surah\s+Al-Ikhlas\b", re.IGNORECASE),  "the chapter of sincerity"),
    (re.compile(r"Surah\s+Al-Shura\b",  re.IGNORECASE),  "the chapter of consultation"),
    (re.compile(r"Surah\s+Qaaf?\b",     re.IGNORECASE),  "the chapter of Qaaf"),
    (re.compile(r"Surah\s+al-Furqan\b", re.IGNORECASE),  "the chapter of the criterion"),
    (re.compile(r"Surah\s+al-Mu'minun\b", re.IGNORECASE),  "the chapter of the believers"),
    (re.compile(r"Surah\s+al-A'?raf\b", re.IGNORECASE),  "the chapter of the heights"),
    (re.compile(r"Surah\s+Ya-?Sin\b",   re.IGNORECASE),  "the chapter of Ya-Seen"),
    (re.compile(r"Surah\s+Al-Fajr\b",   re.IGNORECASE),  "the chapter of the dawn"),
    (re.compile(r",\s*Surah\s+\S+\s*", re.IGNORECASE),  ", "),  # catch-all: ", Surah <something>" → ", "
    (re.compile(r"\bSurah\b\s*,", re.IGNORECASE),        ""),
]


# ---------------------------------------------------------------------------
# English idiom and academic-vocabulary fixes — items NotebookLM TTS
# mispronounces or that read awkwardly when spoken aloud.
# ---------------------------------------------------------------------------
ENGLISH_SUBS: list[tuple[str, str]] = [
    ("Dar the sanctified",  "the Abode of Holiness, Jerusalem"),
    ("Dar al-Quds",         "the Abode of Holiness, Jerusalem"),
    ("soteriology",         "the theology of salvation"),
    ("soteriological",      "salvific"),
    ("Soteriology",         "The theology of salvation"),
]


# ---------------------------------------------------------------------------
# Transliterated Arabic blockquote detection — paired-line patterns where
# the first quote line is romanized Arabic and the second is the English
# translation. The romanized line is unspeakable by TTS; we drop it and
# keep the English-only quote.
# ---------------------------------------------------------------------------
# Heuristic: a blockquote line whose words match the Arabic-romanization
# pattern (no English vowel-cluster regularity, contains characteristic
# Arabic stop words like "wa", "fi", "min", "ila", "lam", "lahu", "Allahu").
_ARABIC_STOPWORDS = {"Allahu", "wa", "fi", "min", "ila", "lam", "lahu",
                     "Qul", "Kana", "thumma", "alaa", "ala", "ghayruhu",
                     "yakun", "yulad", "yalid", "kufuwan", "ahad", "samad",
                     "khalaqa", "shay", "shayun", "arshuhu"}


def _is_romanized_arabic_blockquote(line: str) -> bool:
    """Heuristic: blockquote line is romanized Arabic if it contains 2+
    characteristic Arabic stopwords and lacks common English connectives."""
    stripped = line.strip().lstrip("> ").strip("*").strip()
    if not stripped:
        return False
    tokens = re.findall(r"\b\w+\b", stripped)
    if len(tokens) < 4:
        return False
    arabic_hits = sum(1 for t in tokens if t in _ARABIC_STOPWORDS)
    english_hits = sum(1 for t in tokens if t.lower() in
                       {"the", "and", "is", "of", "in", "to", "that",
                        "with", "for", "on", "at", "by", "an", "be"})
    return arabic_hits >= 2 and english_hits == 0


def _drop_romanized_blockquote_pairs(text: str) -> tuple[str, int]:
    """Remove blockquote lines that are romanized Arabic, keeping the English
    translation that immediately follows. Returns (new_text, n_dropped)."""
    lines = text.split("\n")
    out: list[str] = []
    n_dropped = 0
    skip_next_blockquote_arabic = False
    for line in lines:
        if line.lstrip().startswith(">") and _is_romanized_arabic_blockquote(line):
            n_dropped += 1
            continue
        out.append(line)
    return "\n".join(out), n_dropped


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
@dataclass
class SubstitutionReport:
    """Summary of what changed during a sanitize pass."""
    diacritics_stripped: int = 0
    arabic_terms_substituted: dict[str, int] = field(default_factory=dict)
    surahs_substituted: int = 0
    pre_surah_phrases_fixed: int = 0
    english_subs: dict[str, int] = field(default_factory=dict)
    romanized_blockquotes_dropped: int = 0

    def summary(self) -> str:
        lines = []
        if self.diacritics_stripped:
            lines.append(f"  diacritics stripped: {self.diacritics_stripped}")
        if self.arabic_terms_substituted:
            lines.append("  arabic terms substituted:")
            for term, n in sorted(self.arabic_terms_substituted.items()):
                lines.append(f"    {term}: {n}")
        if self.surahs_substituted:
            lines.append(f"  Quranic citations expanded: {self.surahs_substituted}")
        if self.pre_surah_phrases_fixed:
            lines.append(f"  inline 'Surah X' phrases fixed: {self.pre_surah_phrases_fixed}")
        if self.english_subs:
            lines.append("  english idiom/vocab fixes:")
            for term, n in sorted(self.english_subs.items()):
                lines.append(f"    {term}: {n}")
        if self.romanized_blockquotes_dropped:
            lines.append(f"  romanized Arabic blockquote lines dropped: {self.romanized_blockquotes_dropped}")
        return "\n".join(lines) or "  (no changes needed)"

    @property
    def total_changes(self) -> int:
        return (self.diacritics_stripped
                + sum(self.arabic_terms_substituted.values())
                + self.surahs_substituted
                + self.pre_surah_phrases_fixed
                + sum(self.english_subs.values())
                + self.romanized_blockquotes_dropped)


def sanitize_text(text: str) -> tuple[str, SubstitutionReport]:
    """Apply the full sanitization pipeline. Returns (new_text, report)."""
    report = SubstitutionReport()

    # Pass 1: Arabic compound terms (BEFORE diacritic strip, since some
    # patterns rely on the diacritic to distinguish from prose)
    for old, new in ARABIC_TERM_SUBS:
        if old in text and old != new:
            n = text.count(old)
            text = text.replace(old, new)
            report.arabic_terms_substituted[old] = report.arabic_terms_substituted.get(old, 0) + n

    # Pass 2: Strip remaining diacritics
    text, n_diacritics = _strip_diacritics(text)
    report.diacritics_stripped = n_diacritics

    # Pass 3: Inline "Surah X" phrases
    for pat, replacement in _PRE_SURAH_REPLACEMENTS:
        new_text, n = pat.subn(replacement, text)
        if n:
            report.pre_surah_phrases_fixed += n
            text = new_text

    # Pass 4: Quranic citation expansion (Quran X:Y → Quran X, the chapter of …, verse Y)
    new_text, n = _QURAN_RE.subn(_substitute_surah, text)
    if n:
        report.surahs_substituted = n
        text = new_text

    # Pass 5: English idiom + academic vocab
    for old, new in ENGLISH_SUBS:
        if old in text and old != new:
            n = text.count(old)
            text = text.replace(old, new)
            report.english_subs[old] = report.english_subs.get(old, 0) + n

    # Pass 6: Drop romanized Arabic blockquote lines (keep English translation)
    text, n_dropped = _drop_romanized_blockquote_pairs(text)
    report.romanized_blockquotes_dropped = n_dropped

    # Pass 7: Cleanup — collapse artifacts from translation substitutions.
    # The Arabic-concept translations (zahir → "the apparent", etc.) can
    # produce "the the apparent" when the source had "the zahir" not fully
    # captured by the longest-first match list. Backstop with a regex.
    cleanup_patterns = [
        (re.compile(r"\bthe\s+the\b", re.IGNORECASE), "the"),
        (re.compile(r"\ba\s+an\b", re.IGNORECASE), "an"),
        (re.compile(r"\ba\s+a\b", re.IGNORECASE), "a"),
        # "The mission's mission" can result from "Da'wa's daʿwa" patterns
        (re.compile(r"\bthe mission's mission\b", re.IGNORECASE), "the mission"),
    ]
    for pat, repl in cleanup_patterns:
        text = pat.sub(repl, text)

    return text, report
