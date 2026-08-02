"""_validator_constants.py — Rule constants and helpers for the podcast validation layer.

Split from _validators.py (DR-005 — files must stay under 600 lines).
Imported by _validators.py and _validators_framing.py; all names re-exported from _validators.py.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# ─── Word-count bounds ────────────────────────────────────────────────────────
# Chapter (SOURCE) word-count bounds — per notebooklm-best-practices.md §3
CHAPTER_WORD_MIN_HARD = 500
CHAPTER_WORD_MAX_HARD = 12000
CHAPTER_WORD_MIN_SOFT = 1000
CHAPTER_WORD_MAX_SOFT = 11000
CHAPTER_DEAD_ZONE_MIN = 4500
CHAPTER_DEAD_ZONE_MAX = 5500

# Framing (CUSTOMIZE PROMPT) word-count bounds — per notebooklm-best-practices.md §5.
FRAMING_WORD_MIN = 150
FRAMING_WORD_MAX = 3700  # kept for back-compat; CHARACTER gate below is the binding one

# NotebookLM Customize box hard character ceiling (empirically measured 2026-06-05).
# NotebookLM truncates the pasted text at ~5,000 characters; we cap at 4,500 to leave
# 500-char headroom. This is the P0 gate — a framing that exceeds this will be silently
# truncated by NotebookLM, discarding name-discipline, do-not lists, and pronunciation
# imperatives. FRAMING_CHAR_MAX is the binding limit; FRAMING_WORD_MAX is secondary.
FRAMING_CHAR_MAX = 4500

# ─── Per-episode density ceiling (over-cramming brake, 2026-06-04) ────────────
# Max words an episode may carry before it counts as "over-crammed" — too many
# distinct teachings for one focused listen. Profile-aware: dense doctrinal
# content caps tighter than narrative (whose "extended" episodes can run long
# precisely because they're low-density). Phase 0d halts-and-surfaces above the
# ceiling rather than shipping a marathon episode. (Root-causes the case where
# Ayyuhal Walad's 8,955-word episodes packed ~24 teachings each.)
EPISODE_DENSITY_CEILING_DENSE = 6000  # Arabic-scholarly / doctrinal
EPISODE_DENSITY_CEILING_NARRATIVE = 9500  # narrative / consumer (the extended ceiling)

# Concept-count ceiling per episode (chapter-density standard, 2026-06-10).
# One concept = one `## H2` section in the rendered chapter .txt, excluding
# structural frames ("Where this episode opens", "What this episode lands",
# "Closing"). Single source of truth — chapter_density_audit.py and the
# Phase 0d post-write gate both import THIS constant. Full standard:
# docs/standards/chapter-density.md.
EPISODE_MAX_CONCEPTS = 3

# ─── R-QURAN-CITATION-FORMAT (2026-06-10) ─────────────────────────────────────
# Canonical inline format for Quranic quotations is plain English:
#   (chapter 16, verse 74)
# Terse scholarly forms are forbidden in chapter/framing prose — NotebookLM
# reads them aloud as "Q five nineteen" and listeners can't resolve them.
QURAN_CITATION_BAD_PATTERNS = [
    re.compile(r"\(\s*Q\.?\s*\d{1,3}\s*:\s*\d{1,3}\s*\)"),  # (Q 5:19)
    re.compile(r"\(\s*Quran\s+\d{1,3}\s*:\s*\d{1,3}\s*\)", re.I),  # (Quran 5:19)
    re.compile(r"\(\s*\d{1,3}\s*:\s*\d{1,3}\s*\)"),  # bare (16:74)
]

# ─── R-NO-TRANSLIT-FORMULA (2026-06-10) ───────────────────────────────────────
# A verbatim Arabic formula rendered as an italic transliteration run followed
# by an em-dash and its italic translation:  *Anna Allāha mubdiʿ...* — *...*
# Chapter prose carries the ENGLISH translation only (plain inline Arabic
# terms without diacritics remain allowed per the Phase 0d authority rules).
# The italic run must contain >=4 whitespace-separated tokens — short famous
# term-glosses like `*kun fa-yakūn* — *Be! and it became*` are legitimate
# inline teaching and stay un-flagged; long formula sentences are the target.
TRANSLIT_FORMULA_PAIR_RE = re.compile(r"\*(?=[^*\n]*[āīūēōḍḥṣṭẓġʿʾ])(?:[^*\s\n]+\s+){3,}[^*\s\n]+\*\s+—\s+\*")


def episode_overcrammed(words: int, episode_count: int, ceiling: int) -> int:
    """Density-brake check (pure). Given a source chapter's word count, how many
    episodes it currently maps to, and the per-episode density ceiling, return:
      0  — not over-crammed (per-episode words ≤ ceiling) or zero episodes, OR
      N  — the minimum episode_count this chapter SHOULD use (≥2) so each episode
           lands at/under the ceiling.
    """
    eps = int(episode_count)
    per_episode = int(words) // eps if eps >= 1 else 0  # 0 eps ships nothing to cram
    if per_episode <= ceiling:
        return 0
    return max(2, -(-int(words) // ceiling))  # ceil division


# ─── Regex patterns ──────────────────────────────────────────────────────────
EP_PATTERN = re.compile(r"^EP(\d+)-(.+)$")
CH_PATTERN = re.compile(r"^ch(\d+)[a-z]?-(.+)\.txt$")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)

# ─── META_PROSE_TELLS / META_PROSE_REGEX_TELLS ───────────────────────────────
META_PROSE_TELLS = [
    "this file is",
    "this document is",
    "this chapter file",
    "the body below",
    "the file below",
    "phase 0",
    "phase 0a",
    "phase 0b",
    "phase 0c",
    "phase 0d",
    "phase 0e",
    "phase 0f",
    "phase 0g",
    "enrichment status",
    "enrichment ratio",
    "per the meta-prose rule (B1) in infra/claude-agents/podcast-challenger.md",
    "nothing has been added that is not in the source",
    "anything the author only implies",
    "preserved in blockquotes with the original transliteration",
    "the author's prose has been clarified",
    "structured by beat",
    "refined and enriched presentation",
    "refined presentation of the section",
    "refined presentation of the chapter",
    "[verify citation",
    # Cross-episode references — NotebookLM has no context for other episodes.
    "previous episode",
    "earlier episode",
    "next episode",
    "prior episode",
    "earlier in this episode",
    "later in this episode",
    "the episode honors",
    # Translator-apparatus prefixes — the file describing its own translator's edits.
    "translator's clarification",
    "translator's interpolation",
    "the translator notes",
    "the translator adds",
    "the square brackets are",
    # File-length / authoring-trace self-references.
    "in a few thousand words",
    "in just a few thousand",
    "in a few hundred words",
    "source scope for this episode",
    "source scope:",
    "pages [0-9]+ through [0-9]+ of the printed translation",
]

META_PROSE_REGEX_TELLS = [
    r"\bEP\d{2}\b",
]

# ─── R-PHONETICS-OUT (2026-05-17) ────────────────────────────────────────────
INLINE_PHONETIC_PATTERNS = [
    re.compile(r"\*[A-Za-z'`\-]+\*\s*\(\s*[A-Za-z\-]*[A-Z]{2,}"),
    re.compile(r"^>\s*\(\s*[a-z]+\-[a-z]+(?:[-\s][a-z\-]+)+", re.MULTILINE),
    re.compile(r"\([A-Z]{2,}[\-][A-Z][A-Z\-]+[a-z\-]*\b"),
]

# ─── R-NO-ABBREVIATION (2026-05-17) ──────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
from _rules import (
    HONORIFICS as _HONORIFICS_RAW,
)
from _rules import (
    # Re-exported for _validators.py / _contract_validation.py (role-parity checks).
    HOST_A_ROLES_SCHOLAR as HOST_A_ROLES_SCHOLAR,
)
from _rules import (
    HOST_B_ROLES_SEEKER as HOST_B_ROLES_SEEKER,
)
from _rules import (
    abbreviations_for_build,
)

FORBIDDEN_ABBREVIATIONS = abbreviations_for_build()


# ─── R-HONORIFIC-ONCE (2026-05-17) ───────────────────────────────────────────
def _compile_honorific(p: str) -> re.Pattern:
    is_acronym = p.startswith(r"\(") and p.upper() == p
    return re.compile(p) if is_acronym or p == "ﷺ" else re.compile(p, re.IGNORECASE)


HONORIFIC_PHRASES = [_compile_honorific(p) for p in _HONORIFICS_RAW if p.startswith(r"\(") or p == "ﷺ"]

# ─── R-PRONUNCIATION-IMPERATIVE (framing) ────────────────────────────────────
# Old passive-list format (asterisk-bold style) — always was bad.
LEGACY_PASSIVE_PRONUNCIATION = re.compile(
    r"^\s*[-*]?\s*\*[A-Za-z'`\-\s]+\*\s*[:\-]\s*[A-Za-z][\w\-\s]+$",
    re.MULTILINE,
)

# "Pronounce X as Y" format — causes NotebookLM to say the term twice (R-PRONUNCIATION-DOUBLE).
# This was the previous "imperative" standard but was empirically the root cause of
# the double-read bug ("tahajjud, Tahajjud") first identified in Ayyuhal Walad audio.
PRONOUNCE_AS_DOUBLE_RE = re.compile(
    r'^\s*(?:-\s+)?Pronounce\s+(?:"[^"]+"|\*[^*]+\*)\s+as\s+["\']',
    re.MULTILINE,
)

# Trivial uppercase respelling: "- term: TERM" where the two differ only by case.
# Adds no phonetic value; P1 flag (not hard fail when anti-doubling instruction present).
TRIVIAL_UPPERCASE_RESPELLING_RE = re.compile(
    r"^\s*-\s+([\w'`\-\s]{2,30}):\s+([A-Z][A-Z'\-\s]{1,30})$",
    re.MULTILINE,
)

# Required anti-doubling instruction marker in the Pronunciation block.
ANTI_DOUBLING_INSTRUCTION_RE = re.compile(
    r"(?i)(say\s+each\s+term\s+once|say\s+it\s+once|never\s+say\s+(?:the\s+)?(?:original|both)|"
    r"do\s+not\s+(?:repeat|say\s+both)|once.*phonetic|phonetic.*once)",
)

# ─── R-NOMODERNIZE / R-NOSURPRISE / R-NO-READ-PROMPT (framing) ───────────────
REQUIRED_FRAMING_DO_NOT_PHRASES = [
    "Twitter",
    "social media",
    "algorithm",
    "wow",
    "right?",
    "Do not read this prompt aloud",
]

# ─── P1 FLAGS ─────────────────────────────────────────────────────────────────
P1_FLAGS: list[str] = []


def _flag_p1(rule: str, file_path: Path, message: str) -> None:
    """Record a P1 FLAG for the orchestrator's challenger pass to escalate."""
    line = f"FLAG (P1) [{rule}] {file_path.name}: {message}"
    print(line, file=sys.stderr)
    P1_FLAGS.append(line)


# ─── Pushback / manuscript-meta constants ─────────────────────────────────────
CHALLENGER_PUSHBACK_PATTERNS = [
    "I don't buy that yet",
    "I don’t buy that yet",  # smart-quote (right single quotation mark) variant
    "That sounds like wordplay",
    "Isn't this just replacing",
    "Isn’t this just replacing",  # smart-quote variant
    "How is this different",
]

MANUSCRIPT_META_TELLS = [
    "opening folios are heavily damaged",
    "what can be reconstructed reads",
    "the text breaks off",
    "collapses in the OCR",
    "a second damaged folio carries fragments",
    "translator's note",
    "translator's note",  # smart-quote variant
    "editor's note",
    "editor's note",
    "manuscript notes",
]

MANUSCRIPT_META_HEADER_RE = re.compile(
    r"^#{1,6}\s+(?:What\s+survives\s+at\s+the\s+head|"
    r"What\s+survives\s+of\s+the|"
    r"What\s+can\s+be\s+recovered)\b",
    re.MULTILINE | re.IGNORECASE,
)

# ─── F27 Tier 2.5 TTS-safe enforcement constants (2026-05-22) ─────────────────
ARABIC_TRANSLIT_PATTERNS = [
    re.compile(r"\bal-[A-Z][a-zA-Z]+\b"),
    re.compile(r"\bAbu\s+[A-Z][a-zA-Z]+"),
    re.compile(r"\bIbn\s+[A-Z][a-zA-Z]+"),
    re.compile(r"\bbint\s+[A-Z][a-zA-Z]+"),
    re.compile(r"\b[A-Za-z]+iyy[ah]\b"),
]

ALLOWED_ARABIC_ORIGIN_LOWER = {
    "quran",
    "imam",
    "medina",
    "ismaili",
    "fatimid",
    "fatimi",
    "yusuf ali",
    "muhammad",
    "al-bari",
    "al-mubdi",
    "al-wahid",
    "al-haqq",
    # Publisher names containing Arabic-origin al- prefix:
    "al-fikr",  # "Dar al-Fikr" (publisher)
    # Translator names:
    "al-khattab",  # "Nasiruddin al-Khattab" (translator)
    # Phonetic respellings used in pronunciation guidance (always uppercase):
    "al-lah",  # "al-LAH" (phonetic respelling of Allah)
}

# Context phrases that contain a surah name as a substring but are NOT references
# to the surah (e.g. translator names, phonetic forms). When any of these strings
# appear within 30 characters of a surah-name match, the match is skipped.
SURAH_ALLOWED_CONTEXT_LOWER = {
    "yusuf ali",  # A.Y. Ali (Quran translator — name contains surah "yusuf")
    "a.y. ali",  # abbreviated form of the same translator
}

KNOWN_SURAH_NAMES_LOWER = {
    "al-ahzab",
    "al-shams",
    "al-isra",
    "al-baqarah",
    "al-imran",
    "al-nisa",
    "al-maidah",
    "al-anam",
    "al-araf",
    "al-anfal",
    "al-tawbah",
    "yunus",
    "hud",
    "yusuf",
    "al-rad",
    "ibrahim",
    "al-hijr",
    "al-nahl",
    "al-kahf",
    "maryam",
    "ta-ha",
    "al-anbiya",
    "al-hajj",
    "al-muminun",
    "al-nur",
    "al-furqan",
    "al-shuara",
    "al-naml",
    "al-qasas",
    "al-ankabut",
    "al-rum",
    "luqman",
    "al-sajdah",
    "saba",
    "fatir",
    "ya-sin",
    "al-saffat",
    "sad",
    "al-zumar",
    "ghafir",
    "fussilat",
    "al-shura",
    "al-zukhruf",
    "al-dukhan",
    "al-jathiyah",
    "al-ahqaf",
    "al-fath",
    "al-hujurat",
    "qaf",
    "al-dhariyat",
    "al-tur",
    "al-najm",
    "al-qamar",
    "al-rahman",
    "al-waqiah",
    "al-hadid",
    "al-mujadilah",
    "al-hashr",
    "al-mumtahanah",
    "al-saff",
    "al-jumuah",
    "al-munafiqun",
    "al-taghabun",
    "al-talaq",
    "al-tahrim",
    "al-mulk",
    "al-qalam",
    "al-haqqah",
    "al-maarij",
    "nuh",
    "al-jinn",
    "al-muzzammil",
    "al-muddaththir",
    "al-qiyamah",
    "al-insan",
    "al-mursalat",
    "al-naba",
    "al-naziat",
    "abasa",
    "al-takwir",
    "al-infitar",
    "al-mutaffifin",
    "al-inshiqaq",
    "al-buruj",
    "al-tariq",
    "al-ala",
    "al-ghashiyah",
    "al-fajr",
    "al-balad",
    "al-layl",
    "al-duha",
    "al-sharh",
    "al-tin",
    "al-alaq",
    "al-qadr",
    "al-bayyinah",
    "al-zalzalah",
    "al-adiyat",
    "al-qariah",
    "al-takathur",
    "al-asr",
    "al-humazah",
    "al-fil",
    "quraysh",
    "al-maun",
    "al-kawthar",
    "al-kafirun",
    "al-nasr",
    "al-masad",
    "al-ikhlas",
    "al-falaq",
    "al-nas",
}

FORBIDDEN_ANALOGY_KEYWORDS = {
    "sealed room",
    "two rooms",
    "two sealed",
    "mail carrier",
    "mailman",
    "postal",
    "television",
    "tv set",
    "tv screen",
    "broadcast",
    "data stream",
    "streaming service",
    "4k",
    "hd resolution",
    "sd resolution",
    "pixels",
    "teacup",
    "tea cup",
    "battery",
    "positive terminal",
    "negative terminal",
    "signet ring",
    "wax seal",
    "wax-seal",
    "wax stamped",
    "crystal pitcher",
    "silver cup",
    "cosmic ruler",
    "venn diagram",
    "radio tower",
    "antenna",
    "cosplay",
    "dress-up",
    "campfire",
    "camp fire",
    "waterfall",
    "solar panel",
    "cathedral",
    "fulcrum",
    "pie chart",
    "tape measure",
    "vault holding",
    "frankenstein",
}

FORBIDDEN_MODERN_KEYWORDS = {
    "television",
    "monitor",
    "tablet",
    "computer",
    "laptop",
    "broadcast",
    "data stream",
    "internet",
    "software",
    "streaming",
    "sd ",
    "hd ",
    "4k",
    "8k",
    "pixels",
    "twitter",
    "tiktok",
    "instagram",
    "youtube",
    "social media",
    "algorithm",
    "internet troll",
    "reply guy",
    "cognitive behavioral therapy",
    "productivity framework",
    "life hack",
    "self-help",
    "mindfulness app",
    "dopamine hit",
    "attention economy",
    "refrigerator",
    "lightbulb",
    "coffee maker",
    "influencer",
    "podcaster",
    "blogger",
    "vlogger",
    "21st century",
    "in our modern world",
    "modern listener",
    "in today's world",
    "in the 1990s",
    "modern-day",
    "cosplay",
    "hot take",
    "doomscroll",
    "deep dive",
    "screen time",
    "notification",
    "nation-state",
    "democracy",
    "parliament",
    "frankenstein",
    "popularity contest",
    "synthetic chemistry",
    "biological nature",
}

ESTABLISHED_ENGLISH_ALQAAB = {
    "commander of the faithful",
    "lion of god",
}

FORBIDDEN_LITERAL_ALQAAB = {
    "the striker",
    "the puller",
    "the returner",
    "the lion of allah",
    "the asadullah",
}

SHOW_NOTES_TABLE_HEADER = "## Name and Title Preservation Table"
SHOW_NOTES_REQUIRED_COLUMNS = (
    "Original / Transliteration",
    "Category",
    "Written Form",
    "Audio Label",
    "First Audio Use",
)


# ─── Helper functions ─────────────────────────────────────────────────────────


def word_count(text: str) -> int:
    return len(text.split())


def strip_upload_checklist(framing_md: str) -> str:
    """Drop any trailing '## Upload checklist' block — that's the user's how-to."""
    parts = re.split(r"(?im)^[#]{1,3}\s*Upload checklist.*$", framing_md, maxsplit=1)
    return parts[0].rstrip() + "\n"


def has_html_comments(text: str) -> bool:
    return bool(HTML_COMMENT_RE.search(text))


def strip_html_comments(text: str) -> str:
    cleaned = HTML_COMMENT_RE.sub("", text)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip() + "\n"


def load_book_meta_prose_tells(book_dir: Path) -> list[str]:
    """Read optional per-book extra meta-prose tells from
    `BOOK_DIR/_system/meta-prose-tells.md`. Returns empty list if absent."""
    f = book_dir / "_system" / "meta-prose-tells.md"
    if not f.exists():
        return []
    tells: list[str] = []
    for raw in f.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line.startswith("- "):
            continue
        tell = line[2:].strip().strip('"').strip("'").lower()
        if tell:
            tells.append(tell)
    return tells


def _is_rule_example_line(line: str, tell: str) -> bool:
    """True if `tell` appears in `line` ONLY as a quoted example within a
    rule-statement bullet."""
    stripped = line.strip()
    if not (stripped.startswith("- ") or stripped.startswith("* ")):
        return False
    tell_lower = tell.lower()
    line_lower = stripped.lower()
    in_quote = False
    quoted_spans: list[tuple[int, int]] = []
    span_start = -1
    for i, ch in enumerate(stripped):
        if ch == '"':
            if not in_quote:
                span_start = i + 1
                in_quote = True
            else:
                quoted_spans.append((span_start, i))
                in_quote = False
    pos = 0
    while True:
        idx = line_lower.find(tell_lower, pos)
        if idx < 0:
            break
        in_quoted = any(s <= idx and idx + len(tell_lower) <= e for s, e in quoted_spans)
        if not in_quoted:
            return False
        pos = idx + 1
    return True
