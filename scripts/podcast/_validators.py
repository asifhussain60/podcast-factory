"""_validators.py — Validation constants, helpers, and assert_* / validate_* functions.

Split from build_episode_txt.py (DR-005 — files must stay under 600 lines).
Everything here is re-exported from build_episode_txt.py via `from _validators import *`
so all existing callers remain unaffected.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# ─── Word-count bounds ────────────────────────────────────────────────────────
# Chapter (SOURCE) word-count bounds — per notebooklm-best-practices.md §3
# Tier bands:
#   Brief Deep Dive    (~6–10 min):  1,000–1,800 words
#   Default Deep Dive  (~12–15 min): 1,800–2,800
#   Longer Deep Dive   (~18–22 min): 2,800–4,500
#   Extended Deep Dive (~30–45 min): 5,500–9,500
# Hard band [500, 12,000] enforced here; soft sanity band [1,000, 11,000].
CHAPTER_WORD_MIN_HARD = 500
CHAPTER_WORD_MAX_HARD = 12000
CHAPTER_WORD_MIN_SOFT = 1000
CHAPTER_WORD_MAX_SOFT = 11000
CHAPTER_DEAD_ZONE_MIN = 4500
CHAPTER_DEAD_ZONE_MAX = 5500

# Framing (CUSTOMIZE PROMPT) word-count bounds — per notebooklm-best-practices.md §5.
FRAMING_WORD_MIN = 150
FRAMING_WORD_MAX = 3700

# ─── Regex patterns ──────────────────────────────────────────────────────────
EP_PATTERN = re.compile(r"^EP(\d+)-(.+)$")
CH_PATTERN = re.compile(r"^ch(\d+)[a-z]?-(.+)\.txt$")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)

# ─── META_PROSE_TELLS / META_PROSE_REGEX_TELLS ───────────────────────────────
# Substrings that almost always introduce meta-prose about the file itself rather
# than content. Any match in chapter OR framing is a hard error.
META_PROSE_TELLS = [
    "this file is",
    "this document is",
    "this chapter file",
    "the body below",
    "the file below",
    "phase 0",
    "phase 0a", "phase 0b", "phase 0c", "phase 0d", "phase 0e", "phase 0f", "phase 0g",
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

# Regex tells (case-insensitive). Used in tandem with the substring list.
META_PROSE_REGEX_TELLS = [
    r"\bEP\d{2}\b",  # any EP## reference NotebookLM cannot resolve
]


# ─── R-PHONETICS-OUT (2026-05-17) ────────────────────────────────────────────
# The chapter MUST NOT carry inline phonetic guides.
INLINE_PHONETIC_PATTERNS = [
    # *italic* (... HYPHEN-CONNECTED with at least one UPPERCASE 2+ segment ...)
    re.compile(r"\*[A-Za-z'`\-]+\*\s*\(\s*[A-Za-z\-]*[A-Z]{2,}"),
    # > (lowercase-hyphen-respelling ...) — post-transliteration line
    re.compile(r"^>\s*\(\s*[a-z]+\-[a-z]+(?:[-\s][a-z\-]+)+", re.MULTILINE),
    # bare inline form (PHO-NE-TIC)
    re.compile(r"\([A-Z]{2,}[\-][A-Z][A-Z\-]+[a-z\-]*\b"),
]


# ─── R-NO-ABBREVIATION (2026-05-17) ──────────────────────────────────────────
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).parent))
from _rules import (
    abbreviations_for_build,
    HONORIFICS as _HONORIFICS_RAW,
    HOST_A_ROLES_SCHOLAR,
    HOST_B_ROLES_SEEKER,
)

FORBIDDEN_ABBREVIATIONS = abbreviations_for_build()


# ─── R-HONORIFIC-ONCE (2026-05-17) ───────────────────────────────────────────
def _compile_honorific(p: str) -> re.Pattern:
    is_acronym = p.startswith(r"\(") and p.upper() == p
    return re.compile(p) if is_acronym or p == "ﷺ" else re.compile(p, re.IGNORECASE)


HONORIFIC_PHRASES = [_compile_honorific(p) for p in _HONORIFICS_RAW
                     if p.startswith(r"\(") or p == "ﷺ"]


# ─── R-PRONUNCIATION-IMPERATIVE (framing) (2026-05-17) ───────────────────────
PRONUNCIATION_LINE_OK = re.compile(r"^\s*(Pronounce\s+\"|Do not\s+|Say\s+)", re.MULTILINE)
LEGACY_PASSIVE_PRONUNCIATION = re.compile(
    r"^\s*[-*]?\s*\*[A-Za-z'`\-\s]+\*\s*[:\-]\s*[A-Za-z][\w\-\s]+$",
    re.MULTILINE,
)


# ─── R-NOMODERNIZE / R-NOSURPRISE / R-NO-READ-PROMPT (framing) (2026-05-17) ──
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
    "I don't buy that yet",          # smart-quote variant
    "That sounds like wordplay",
    "Isn't this just replacing",
    "Isn't this just replacing",     # smart-quote variant
    "How is this different",
]

MANUSCRIPT_META_TELLS = [
    "opening folios are heavily damaged",
    "what can be reconstructed reads",
    "the text breaks off",
    "collapses in the OCR",
    "a second damaged folio carries fragments",
    "translator's note",
    "translator's note",                # smart-quote variant
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
    "quran", "imam", "medina", "ismaili", "fatimid", "fatimi",
    "yusuf ali", "muhammad",
    "al-bari", "al-mubdi", "al-wahid", "al-haqq",
}

KNOWN_SURAH_NAMES_LOWER = {
    "al-ahzab", "al-shams", "al-isra", "al-baqarah", "al-imran",
    "al-nisa", "al-maidah", "al-anam", "al-araf", "al-anfal",
    "al-tawbah", "yunus", "hud", "yusuf", "al-rad", "ibrahim",
    "al-hijr", "al-nahl", "al-kahf", "maryam", "ta-ha", "al-anbiya",
    "al-hajj", "al-muminun", "al-nur", "al-furqan", "al-shuara",
    "al-naml", "al-qasas", "al-ankabut", "al-rum", "luqman",
    "al-sajdah", "saba", "fatir", "ya-sin", "al-saffat", "sad",
    "al-zumar", "ghafir", "fussilat", "al-shura", "al-zukhruf",
    "al-dukhan", "al-jathiyah", "al-ahqaf", "al-fath", "al-hujurat",
    "qaf", "al-dhariyat", "al-tur", "al-najm", "al-qamar",
    "al-rahman", "al-waqiah", "al-hadid", "al-mujadilah", "al-hashr",
    "al-mumtahanah", "al-saff", "al-jumuah", "al-munafiqun",
    "al-taghabun", "al-talaq", "al-tahrim", "al-mulk", "al-qalam",
    "al-haqqah", "al-maarij", "nuh", "al-jinn", "al-muzzammil",
    "al-muddaththir", "al-qiyamah", "al-insan", "al-mursalat",
    "al-naba", "al-naziat", "abasa", "al-takwir", "al-infitar",
    "al-mutaffifin", "al-inshiqaq", "al-buruj", "al-tariq", "al-ala",
    "al-ghashiyah", "al-fajr", "al-balad", "al-layl", "al-duha",
    "al-sharh", "al-tin", "al-alaq", "al-qadr", "al-bayyinah",
    "al-zalzalah", "al-adiyat", "al-qariah", "al-takathur", "al-asr",
    "al-humazah", "al-fil", "quraysh", "al-maun", "al-kawthar",
    "al-kafirun", "al-nasr", "al-masad", "al-ikhlas", "al-falaq",
    "al-nas",
}

FORBIDDEN_ANALOGY_KEYWORDS = {
    "sealed room", "two rooms", "two sealed",
    "mail carrier", "mailman", "postal",
    "television", "tv set", "tv screen",
    "broadcast", "data stream", "streaming service",
    "4k", "hd resolution", "sd resolution", "pixels",
    "teacup", "tea cup",
    "battery", "positive terminal", "negative terminal",
    "signet ring", "wax seal", "wax-seal", "wax stamped",
    "crystal pitcher", "silver cup",
    "cosmic ruler",
    "venn diagram",
    "radio tower", "antenna",
    "cosplay", "dress-up",
    "campfire", "camp fire",
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
    "television", "monitor", "tablet", "computer", "laptop",
    "broadcast", "data stream", "internet", "software",
    "streaming",
    "sd ", "hd ", "4k", "8k", "pixels",
    "twitter", "tiktok", "instagram", "youtube",
    "social media", "algorithm", "internet troll", "reply guy",
    "cognitive behavioral therapy", "productivity framework",
    "life hack", "self-help", "mindfulness app", "dopamine hit",
    "attention economy",
    "refrigerator", "lightbulb", "coffee maker",
    "influencer", "podcaster", "blogger", "vlogger",
    "21st century", "in our modern world", "modern listener",
    "in today's world", "in the 1990s", "modern-day",
    "cosplay", "hot take", "doomscroll", "deep dive",
    "screen time", "notification",
    "nation-state", "democracy", "parliament",
    "frankenstein", "popularity contest", "synthetic chemistry",
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


# ─── assert_* functions ───────────────────────────────────────────────────────

def assert_no_meta_prose(content: str, file_path: Path, role: str,
                         extra_tells: list[str] | None = None) -> None:
    """Refuse to build if content contains meta-prose tells."""
    lower = content.lower()
    all_tells = META_PROSE_TELLS + list(extra_tells or [])
    lines = content.splitlines()

    substring_hits: list[str] = []
    for tell in all_tells:
        if tell not in lower:
            continue
        any_real_leak = False
        for line in lines:
            if tell in line.lower() and not _is_rule_example_line(line, tell):
                any_real_leak = True
                break
        if any_real_leak:
            substring_hits.append(tell)
    regex_hits = []
    for pat in META_PROSE_REGEX_TELLS:
        for m in re.finditer(pat, content, flags=re.IGNORECASE):
            regex_hits.append((pat, m.group(0)))
    if not (substring_hits or regex_hits):
        return

    offending = []
    for tell in substring_hits:
        for ln, line in enumerate(lines, 1):
            if tell in line.lower() and not _is_rule_example_line(line, tell):
                offending.append(f"  {file_path.name}:{ln}: {line.strip()[:120]}")
                break
    for pat, matched in regex_hits[:5]:
        for ln, line in enumerate(lines, 1):
            if re.search(pat, line, flags=re.IGNORECASE):
                offending.append(f"  {file_path.name}:{ln} (regex {pat!r} matched {matched!r}): {line.strip()[:120]}")
                break

    joined = "\n".join(offending[:10])
    tells_summary = ", ".join(repr(h) for h in substring_hits)
    if regex_hits:
        tells_summary += " | regex: " + ", ".join(repr(p) for p, _ in regex_hits[:5])
    sys.exit(
        f"ERROR: {role} file contains meta-prose that would reach NotebookLM.\n"
        f"  Tells found: {tells_summary}\n"
        f"  Offending lines:\n{joined}\n\n"
        f"  Chapter files are uploaded as-is to NotebookLM as the SOURCE — meta inside\n"
        f"  the file is read literally by the hosts. Authoring metadata belongs in\n"
        f"  `BOOK_DIR/_system/enrichment-log.md`, NOT inline.\n"
        f"  Framing files are pasted as-is into NotebookLM's Customize box — meta there\n"
        f"  becomes steering noise.\n"
        f"  See skills-staging/podcast/SKILL.md §6 Output Rules."
    )


def assert_no_html_comments(content: str, file_path: Path, role: str) -> None:
    if has_html_comments(content):
        sys.exit(
            f"ERROR: {role} file contains HTML comments (`<!-- ... -->`).\n"
            f"  File: {file_path}\n"
            f"  Chapter files are uploaded as-is to NotebookLM as the SOURCE. HTML\n"
            f"  comments would be read literally by the hosts. Move authoring metadata\n"
            f"  to `BOOK_DIR/_system/enrichment-log.md` and remove the inline comment.\n"
            f"  Framing files are pasted as-is into Customize box; same constraint.\n"
            f"  (build_episode_txt.py does NOT strip — it refuses, so the chapter file\n"
            f"  is always upload-ready.)"
        )


def assert_no_inline_phonetics(content: str, file_path: Path) -> None:
    """R-PHONETICS-OUT: chapter must not carry inline phonetic guides."""
    hits: list[tuple[int, str]] = []
    for pat in INLINE_PHONETIC_PATTERNS:
        for m in pat.finditer(content):
            ln = content[: m.start()].count("\n") + 1
            line = content.splitlines()[ln - 1] if ln - 1 < len(content.splitlines()) else ""
            hits.append((ln, line.strip()[:120]))
    if not hits:
        return
    joined = "\n".join(f"  {file_path.name}:{ln}: {line}" for ln, line in hits[:10])
    sys.exit(
        f"ERROR: chapter (SOURCE) file contains inline phonetic guides.\n"
        f"  Hits ({len(hits)} found; first 10 shown):\n{joined}\n\n"
        f"  R-PHONETICS-OUT (2026-05-17): chapter files must not carry inline\n"
        f"  `*Term* (PHO-ne-tic; gloss)` parens or post-transliteration phonetic\n"
        f"  blockquote lines. NotebookLM reads them aloud as content — empirically\n"
        f"  producing 'Sahih Sitta, sahasita' doublings and mangled names like\n"
        f"  'tassel wolf' for *Tasawwuf*. Move every phonetic into the matching\n"
        f"  framing's `## Pronunciation` block as an imperative line:\n"
        f"      Pronounce \"Tasawwuf\" as \"ta-SAW-wuf\". Say it as one fluent word.\n"
        f"  See scripts/podcast/_rules.py (rules R-PHONETICS-OUT, R-NO-ABBREVIATION, etc.)\n"
        f"  R-PHONETICS-OUT and notebooklm-customize-prompt-rules.md\n"
        f"  R-PRONUNCIATION-IMPERATIVE."
    )


def assert_no_abbreviations(content: str, file_path: Path) -> None:
    """R-NO-ABBREVIATION: chapter must spell out canonical work titles."""
    hits: list[tuple[int, str, str]] = []
    for pat, label in FORBIDDEN_ABBREVIATIONS.items():
        for m in re.finditer(pat, content):
            ln = content[: m.start()].count("\n") + 1
            line = content.splitlines()[ln - 1] if ln - 1 < len(content.splitlines()) else ""
            hits.append((ln, label, line.strip()[:120]))
    if not hits:
        return
    joined = "\n".join(f"  {file_path.name}:{ln}: {label} → in: {line}" for ln, label, line in hits[:10])
    sys.exit(
        f"ERROR: chapter (SOURCE) file contains abbreviated work titles.\n"
        f"  Hits:\n{joined}\n\n"
        f"  R-NO-ABBREVIATION: listeners cannot resolve unfamiliar contractions.\n"
        f"  Use the full canonical title every time. See\n"
        f"  scripts/podcast/_rules.py (rules R-PHONETICS-OUT, R-NO-ABBREVIATION, etc.) R-NO-ABBREVIATION."
    )


def assert_honorifics_once_only(content: str, file_path: Path) -> None:
    """R-HONORIFIC-ONCE: each honorific phrase form expanded ≤1 time per chapter."""
    over: list[tuple[str, int]] = []
    for pat in HONORIFIC_PHRASES:
        n = len(pat.findall(content))
        if n > 1:
            over.append((pat.pattern, n))
    if not over:
        return
    joined = "\n".join(f"  '{pat}' appears {n} times" for pat, n in over)
    sys.exit(
        f"ERROR: chapter (SOURCE) file repeats honorific expansions.\n"
        f"  File: {file_path}\n"
        f"  Repeated honorifics (allowed once per chapter per form):\n{joined}\n\n"
        f"  R-HONORIFIC-ONCE: expand each honorific exactly once per figure on\n"
        f"  first mention; subsequent mentions use the contracted name only\n"
        f"  ('the Prophet', 'Imam Ali'). NotebookLM reads every expansion aloud\n"
        f"  — empirically: 9 expansions of '(peace and blessings be upon him)'\n"
        f"  in a single audited episode. See\n"
        f"  scripts/podcast/_rules.py (rules R-PHONETICS-OUT, R-NO-ABBREVIATION, etc.)\n"
        f"  R-HONORIFIC-ONCE."
    )


def assert_framing_pronunciation_imperative(content: str, file_path: Path) -> None:
    """R-PRONUNCIATION-IMPERATIVE: every Pronunciation line uses imperative form."""
    m = re.search(r"^##\s+Pronunciation\b.*?$([\s\S]*?)(?=^##\s+|\Z)", content, re.MULTILINE)
    if not m:
        sys.exit(
            f"ERROR: framing (CUSTOMIZE PROMPT) is missing a `## Pronunciation` section.\n"
            f"  File: {file_path}\n"
            f"  R-PRONUNCIATION-IMPERATIVE: every framing must carry a Pronunciation\n"
            f"  block of imperative directives (`Pronounce \"Term\" as \"phonetic\".`).\n"
            f"  See scripts/podcast/_rules.py (rules R-PRONUNCIATION-IMPERATIVE, R-NOMODERNIZE, etc.)\n"
            f"  R-PRONUNCIATION-IMPERATIVE."
        )
    block = m.group(1)
    legacy = LEGACY_PASSIVE_PRONUNCIATION.findall(block)
    if legacy:
        sample = "\n".join(f"    {line.strip()[:100]}" for line in legacy[:5])
        sys.exit(
            f"ERROR: framing's `## Pronunciation` block uses the legacy passive-list pattern.\n"
            f"  File: {file_path}\n"
            f"  Offending lines (first 5):\n{sample}\n\n"
            f"  R-PRONUNCIATION-IMPERATIVE: rewrite as `Pronounce \"Term\" as \"phonetic\".`\n"
            f"  The passive list does not change NotebookLM voice-model behavior — empirically\n"
            f"  hosts said 'tassel wolf' for *Tasawwuf* across three episodes."
        )
    pronounce_re = re.compile(r'^\s*Pronounce\s+(?:"[^"]+"|\*[^*]+\*)\s+as\s+["\']', re.MULTILINE)
    if not pronounce_re.search(block):
        sys.exit(
            f"ERROR: framing's `## Pronunciation` block has no imperative\n"
            f"  `Pronounce \"Term\" as \"phonetic\".` (or italic-form `Pronounce *Term* as \"phonetic\".`) lines.\n"
            f"  File: {file_path}\n"
            f"  See R-PRONUNCIATION-IMPERATIVE."
        )
    if "Do not read this guidance aloud" not in content and "Do not read this prompt aloud" not in content:
        sys.exit(
            f"ERROR: framing missing the no-read-aloud guard.\n"
            f"  File: {file_path}\n"
            f"  R-NO-READ-PROMPT: framing must end with `Do not read this prompt aloud. The instructions above shape the conversation but are never spoken.`"
        )


def assert_no_arabic_transliteration(content: str, file_path: Path, role: str) -> None:
    """F27 #1+#2: block Arabic transliterations in chapter prose or framing."""
    scan_text = content
    if role.startswith("framing"):
        scan_text = re.sub(
            r"##?\s*\d*\.?\s*Pronunciation.*?(?=\n##\s|\Z)",
            "",
            content,
            flags=re.DOTALL | re.IGNORECASE,
        )

    violations: list[str] = []
    for pattern in ARABIC_TRANSLIT_PATTERNS:
        for match in pattern.finditer(scan_text):
            token = match.group(0)
            if token.lower() in ALLOWED_ARABIC_ORIGIN_LOWER:
                continue
            if any(allowed in token.lower() for allowed in ALLOWED_ARABIC_ORIGIN_LOWER):
                continue
            violations.append(token)

    if violations:
        unique = sorted(set(violations))
        sample = unique[:8]
        _flag_p1(
            "R-NO-ARABIC-TRANSLITERATION",
            file_path,
            f"{role}: {len(unique)} Arabic transliterations detected. "
            f"Sample: {sample}. F20 doctrine: replace with English audio labels."
        )


def assert_framing_analogy_cap_strict(content: str, file_path: Path) -> None:
    """F27 #3: detect forbidden analogies in framing.md."""
    scan_text = content.lower()
    scan_text_scrubbed = re.sub(
        r"###?\s+(?:explicitly\s+)?forbidden\s+analogies.*?(?=\n##\s|\n###\s|\Z)",
        "",
        scan_text,
        flags=re.DOTALL,
    )
    violations = [k for k in FORBIDDEN_ANALOGY_KEYWORDS if k in scan_text_scrubbed]
    if violations:
        _flag_p1(
            "R-ANALOGY-CAP-STRICT",
            file_path,
            f"framing: forbidden analogy patterns detected: {violations[:8]}. "
            f"Allowed: mirror, messenger, light-on-glass-stone, source-images only."
        )


def assert_framing_no_modern_artifacts(content: str, file_path: Path) -> None:
    """F27 #4: detect modern-vocabulary contamination in framing.md."""
    scan_text = content.lower()
    scan_text_scrubbed = re.sub(
        r"##\s+\d*\.?\s*R-NOMODERNIZE.*?(?=\n##\s|\Z)",
        "",
        scan_text,
        flags=re.DOTALL,
    )
    scan_text_scrubbed = re.sub(
        r"##\s+do not\s*\(forbidden vocabulary.*?(?=\n##\s|\Z)",
        "",
        scan_text_scrubbed,
        flags=re.DOTALL,
    )
    violations = [k for k in FORBIDDEN_MODERN_KEYWORDS if k in scan_text_scrubbed]
    if violations:
        _flag_p1(
            "R-NOMODERNIZE-STRICT",
            file_path,
            f"framing: modern artifacts detected: {violations[:8]}. "
            f"R-NOMODERNIZE: tenth-century metaphysics — no modern vocabulary."
        )


def assert_framing_honorific_bounded_both_sides(content: str, file_path: Path) -> None:
    """F27 #5: each honorific appears EXACTLY ONCE."""
    scan_text_lower = content.lower()
    scan_text_lower = re.sub(
        r"##?\s*\d*\.?\s*R-HONORIFIC-ONCE.*?(?=\n##\s|\Z)",
        "",
        scan_text_lower,
        flags=re.DOTALL,
    )
    scan_text_lower = re.sub(
        r"##?\s*\d*\.?\s*Honorific\s+(?:1|2|discipline).*?(?=\n##\s|\Z)",
        "",
        scan_text_lower,
        flags=re.DOTALL,
    )

    pbuh_count = scan_text_lower.count("peace be upon him")
    pbuhf_count = scan_text_lower.count("peace and blessings of allah be upon him and his family")

    issues: list[str] = []
    if pbuh_count != 1:
        issues.append(f"'peace be upon him' occurs {pbuh_count}× (must equal 1; first mention of Commander of the Faithful)")
    if pbuhf_count != 1:
        issues.append(f"'peace and blessings of Allah...' occurs {pbuhf_count}× (must equal 1; first mention of the Prophet)")

    if issues:
        _flag_p1(
            "R-HONORIFIC-BOTH-BOUNDS",
            file_path,
            f"framing: " + "; ".join(issues)
        )


def assert_no_arabic_surah_names(content: str, file_path: Path, role: str) -> None:
    """F27 #6: detect Arabic surah names. F29 doctrine: use English meanings."""
    scan_text = content.lower()
    scan_text_scrubbed = re.sub(
        r"##?\s*\d*\.?\s*(?:R-SURAH|surah\s+(?:lookup|reference|names)).*?(?=\n##\s|\Z)",
        "",
        scan_text,
        flags=re.DOTALL,
    )
    violations: list[str] = []
    for surah in KNOWN_SURAH_NAMES_LOWER:
        if surah in scan_text_scrubbed:
            violations.append(surah)
    if violations:
        _flag_p1(
            "R-SURAH-ENGLISH-ONLY",
            file_path,
            f"{role}: Arabic surah names detected: {sorted(violations)[:8]}. "
            f"F29 doctrine: use English meanings ('the chapter on the sun' etc.)."
        )


def assert_alqaab_only_established_or_paraphrased(content: str, file_path: Path, role: str) -> None:
    """F27 #7: block awkward literal alqaab translations."""
    scan_text_lower = content.lower()
    violations = [k for k in FORBIDDEN_LITERAL_ALQAAB if k in scan_text_lower]
    if violations:
        _flag_p1(
            "R-ALQAAB-FUNCTIONAL-PARAPHRASE",
            file_path,
            f"{role}: literal alqaab translations detected: {violations}. "
            f"F24 doctrine: use functional paraphrase ('one of his martial honorifics')."
        )


def assert_show_notes_has_apparatus_table(content: str, file_path: Path) -> None:
    """F27 #8 / F25: 99-show-notes.md must contain a structured apparatus table."""
    if SHOW_NOTES_TABLE_HEADER not in content:
        _flag_p1(
            "F25-APPARATUS-TABLE", file_path,
            f"no '{SHOW_NOTES_TABLE_HEADER}' section header found. "
            f"F25 doctrine: every episode's 99-show-notes.md carries the "
            f"written-layer apparatus (preserved Arabic / transliterations + "
            f"audio-label crosswalk) the TTS-safe audio omits."
        )
        return
    missing = [col for col in SHOW_NOTES_REQUIRED_COLUMNS if col not in content]
    if missing:
        _flag_p1(
            "F25-APPARATUS-TABLE", file_path,
            f"apparatus table missing required columns: {missing}. "
            f"Required: {list(SHOW_NOTES_REQUIRED_COLUMNS)}."
        )


def assert_framing_has_name_discipline_section(content: str, file_path: Path) -> None:
    """R-NAMEDISCIPLINE: framing has a Name discipline section with rotation sets."""
    has_section = bool(re.search(
        r"^##\s+Name\s+discipline\b", content, re.MULTILINE | re.IGNORECASE
    )) or bool(re.search(
        r"^Name\s+discipline\b", content, re.MULTILINE | re.IGNORECASE
    ))
    if not has_section:
        _flag_p1(
            "R-NAMEDISCIPLINE", file_path,
            "no `## Name discipline` section found. Add a Name discipline "
            "section listing each figure's full Arabic name (once on first "
            "mention) + 3-4 English alias rotation set. See handbook: "
            "notebooklm-customize-prompt-rules.md R-NAMEDISCIPLINE."
        )
        return
    has_rotation = bool(re.search(
        r"(Rotation:|→)\s*[A-Za-z][^\n]*?[/,][^\n]*?[/,]",
        content,
    ))
    if not has_rotation:
        _flag_p1(
            "R-NAMEDISCIPLINE", file_path,
            "Name discipline section found but no rotation set with 3+ aliases "
            "(`Rotation: a / b / c` or `→ a / b / c`). See handbook."
        )


def assert_framing_dramatic_arc_structure(content: str, file_path: Path) -> None:
    """R-DRAMATIC-ARC: debate-format framings declare a multi-beat arc."""
    beat_markers = re.findall(r"\bBeat\s+\d+\b", content)
    distinct_beats = set(beat_markers)
    has_six_beats = len(distinct_beats) >= 6

    structure_tells = ["crisis", "failed answer", "pivot", "stakes"]
    lower = content.lower()
    structure_hits = sum(1 for t in structure_tells if t in lower)
    has_structure_declaration = structure_hits >= 3

    if not (has_six_beats or has_structure_declaration):
        _flag_p1(
            "R-DRAMATIC-ARC", file_path,
            f"no 6-beat dramatic arc detected — found {len(distinct_beats)} "
            f"distinct Beat markers AND only {structure_hits}/4 structure "
            f"tells (crisis / failed answer / pivot / stakes). Restructure "
            f"`## Three-part focus` as a 6-beat arc. See handbook: "
            f"notebooklm-customize-prompt-rules.md R-DRAMATIC-ARC."
        )


def assert_framing_challenger_friction_lists_patterns(content: str, file_path: Path) -> None:
    """R-CHALLENGER-FRICTION: framing names challenger role + ≥2 pushback patterns."""
    has_host_dynamic = bool(re.search(r"^##\s+Host\s+dynamic\b", content, re.MULTILINE | re.IGNORECASE))
    has_central_tensions = bool(re.search(r"^##\s+Central\s+tensions\b", content, re.MULTILINE | re.IGNORECASE))
    if not (has_host_dynamic or has_central_tensions):
        _flag_p1(
            "R-CHALLENGER-FRICTION", file_path,
            "no `## Host dynamic` or `## Central tensions` section found — the "
            "challenger-friction clause cannot be placed. See handbook: "
            "notebooklm-customize-prompt-rules.md R-CHALLENGER-FRICTION."
        )
        return
    lower = content.lower()
    has_challenger_role = any(t in lower for t in ("challenger", "pushback", "friction"))
    seen_bases = set()
    for p in CHALLENGER_PUSHBACK_PATTERNS:
        if p in content:
            base = p.replace("’", "'")
            seen_bases.add(base)
    distinct_patterns = len(seen_bases)

    if not has_challenger_role or distinct_patterns < 2:
        missing = []
        if not has_challenger_role:
            missing.append("no `challenger` / `pushback` / `friction` language in Host dynamic or Central tensions")
        if distinct_patterns < 2:
            missing.append(f"only {distinct_patterns} of the required pushback patterns found (need ≥2): "
                           f"I don't buy that yet… / That sounds like wordplay… / Isn't this just replacing… / "
                           f"How is this different…")
        _flag_p1(
            "R-CHALLENGER-FRICTION", file_path,
            "; ".join(missing) + ". See handbook: notebooklm-customize-prompt-rules.md R-CHALLENGER-FRICTION."
        )


def assert_framing_analogy_cap_declared(content: str, file_path: Path) -> None:
    """R-ANALOGY-CAP: framing's Tone constraints declares 3-5 governing analogies."""
    m = re.search(
        r"^##\s+Tone(?:\s+constraints)?\b.*?$([\s\S]*?)(?=^##\s+|\Z)",
        content, re.MULTILINE | re.IGNORECASE,
    )
    if not m:
        _flag_p1(
            "R-ANALOGY-CAP", file_path,
            "no `## Tone constraints` section found — cannot validate analogy "
            "enumeration. See handbook: notebooklm-customize-prompt-rules.md "
            "R-ANALOGY-CAP."
        )
        return
    tone_block = m.group(1)
    analogy_lines = re.findall(
        r"(?:^|\n)\s*[-*]?\s*\*{0,2}Analogy\s+\d+\b",
        tone_block, re.IGNORECASE,
    )
    n_analogies = len(analogy_lines)
    if n_analogies == 0:
        _flag_p1(
            "R-ANALOGY-CAP", file_path,
            "no governing-analogy enumeration found in `## Tone constraints`. "
            "Enumerate 3-5 analogies, each tied to a beat. See handbook: "
            "notebooklm-customize-prompt-rules.md R-ANALOGY-CAP."
        )
        return
    if n_analogies < 3 or n_analogies > 5:
        _flag_p1(
            "R-ANALOGY-CAP", file_path,
            f"found {n_analogies} governing analogies in `## Tone constraints`; "
            f"required range is 3-5 inclusive. See handbook: "
            f"notebooklm-customize-prompt-rules.md R-ANALOGY-CAP."
        )


def assert_framing_recurring_thesis_present(content: str, file_path: Path,
                                            contract_anchor: str | None = None) -> None:
    """R-RECURRING-THESIS: framing references the chapter's central thesis 3×."""
    if contract_anchor:
        count = content.count(contract_anchor)
        if count < 3:
            _flag_p1(
                "R-RECURRING-THESIS", file_path,
                f"contract anchor thesis found {count}× in framing; "
                f"R-RECURRING-THESIS requires VERBATIM appearance ≥3× "
                f"(open + pivot + close). Thesis (first 80 chars): "
                f"{contract_anchor[:80]!r}. See handbook: "
                f"notebooklm-customize-prompt-rules.md R-RECURRING-THESIS."
            )
            return
        return
    has_rule_ref = "R-RECURRING-THESIS" in content
    has_three_times = bool(re.search(
        r"\b(three|3)\s+times\b.*?\b(verbatim|verbatim,)",
        content, re.IGNORECASE | re.DOTALL,
    )) or bool(re.search(
        r"\bverbatim\b.*?\b(three|3)\s+times\b",
        content, re.IGNORECASE | re.DOTALL,
    ))
    if not (has_rule_ref and has_three_times):
        _flag_p1(
            "R-RECURRING-THESIS", file_path,
            f"no contract anchor was provided AND framing lacks both an "
            f"R-RECURRING-THESIS rule reference and a 'verbatim … three times' "
            f"instruction. Add the rule clause to `## Anti-noise rules`. "
            f"See handbook: notebooklm-customize-prompt-rules.md "
            f"R-RECURRING-THESIS."
        )


def assert_chapter_no_manuscript_meta(content: str, file_path: Path) -> None:
    """R-NO-MANUSCRIPT-META: chapter source carries no manuscript-history meta."""
    hits: list[tuple[int, str, str]] = []
    lines = content.splitlines()
    lower_lines = [ln.lower() for ln in lines]
    for tell in MANUSCRIPT_META_TELLS:
        tell_lower = tell.lower()
        for ln_idx, ln_lower in enumerate(lower_lines):
            if tell_lower in ln_lower:
                hits.append((ln_idx + 1, tell, lines[ln_idx].strip()[:120]))
                break
    for m in MANUSCRIPT_META_HEADER_RE.finditer(content):
        ln_idx = content[: m.start()].count("\n")
        hits.append((ln_idx + 1, m.group(0).strip()[:80], lines[ln_idx].strip()[:120]))
    if not hits:
        return
    joined = "\n    ".join(f"{file_path.name}:{ln}: '{phrase}' in: {context}"
                          for ln, phrase, context in hits[:10])
    _flag_p1(
        "R-NO-MANUSCRIPT-META", file_path,
        f"chapter contains {len(hits)} manuscript-history meta-prose hit(s). "
        f"NotebookLM would voice these as content. Move manuscript-state "
        f"context to `BOOK_DIR/_system/manuscript-history.md`.\n    {joined}\n"
        f"  See handbook: notebooklm-source-chapter-rules.md "
        f"R-NO-MANUSCRIPT-META."
    )


def assert_framing_deny_block(content: str, file_path: Path) -> None:
    """R-NOMODERNIZE + R-NOSURPRISE + R-NO-READ-PROMPT: framing carries a `## Do not` block."""
    if not re.search(r"^##\s+Do not\b", content, re.MULTILINE):
        sys.exit(
            f"ERROR: framing missing the `## Do not (forbidden vocabulary and framings)` section.\n"
            f"  File: {file_path}\n"
            f"  R-NOMODERNIZE + R-NOSURPRISE: every framing must include a DENY block\n"
            f"  listing modernization terms (Twitter, X, social media, algorithm, ...) and\n"
            f"  surprise-noise phrases ('wow', 'right?', 'it's chilling', ...). The block\n"
            f"  is the structural fix for empirically-observed host drift away from\n"
            f"  faithful exposition into modern analogies and surprise loops.\n"
            f"  See scripts/podcast/_rules.py (rules R-PRONUNCIATION-IMPERATIVE, R-NOMODERNIZE, etc.)."
        )
    missing = [p for p in REQUIRED_FRAMING_DO_NOT_PHRASES if p not in content]
    if missing:
        sys.exit(
            f"ERROR: framing's DENY block is missing required entries: {missing}\n"
            f"  File: {file_path}\n"
            f"  See R-NOMODERNIZE / R-NOSURPRISE / R-NO-READ-PROMPT for the canonical list."
        )


def validate_host_role_parity(contract: dict) -> list[str]:
    """R-HOST-ROLE-PARITY (Q4) — deterministic host-pairing gate."""
    findings: list[str] = []
    debate = (contract or {}).get("debate") or {}
    if not isinstance(debate, dict) or not debate:
        return findings
    host_a = (debate.get("host_a") or {}).get("role", "")
    host_b = (debate.get("host_b") or {}).get("role", "")
    if host_a and host_a.lower() not in {r.lower() for r in HOST_A_ROLES_SCHOLAR}:
        findings.append(
            f"R-HOST-ROLE-PARITY (Q4): contract.debate.host_a.role={host_a!r} not in "
            f"scholar pool {HOST_A_ROLES_SCHOLAR}. Host A (male voice) must be in the "
            f"scholar/teacher pool. If contract assigns the scholar role to Host B, "
            f"swap the assignments so the male voice carries the scholar role."
        )
    if host_b and host_b.lower() not in {r.lower() for r in HOST_B_ROLES_SEEKER}:
        findings.append(
            f"R-HOST-ROLE-PARITY (Q4): contract.debate.host_b.role={host_b!r} not in "
            f"seeker pool {HOST_B_ROLES_SEEKER}. Host B (female voice) must be in the "
            f"seeker/student/debater pool."
        )
    return findings


def assert_chapters_populated(book_dir: Path) -> list[Path]:
    chapters_dir = book_dir / "chapters"
    if not chapters_dir.is_dir():
        sys.exit(
            f"ERROR: missing chapters/ directory: {chapters_dir}\n"
            f"  Episodes cannot exist without source-book chapters. "
            f"Run Phase 0 (SKILL.md §1.5) to design and enrich chapters first."
        )
    txt_files = sorted(chapters_dir.glob("*.txt"))
    if not txt_files:
        sys.exit(
            f"ERROR: chapters/ is empty: {chapters_dir}\n"
            f"  Episodes cannot exist without source-book chapters. "
            f"Run Phase 0 (SKILL.md §1.5) to design and enrich chapters first."
        )
    return txt_files


def find_chapter_by_slug(chapters_dir: Path, episode_slug: str) -> Path:
    candidates = []
    for f in sorted(chapters_dir.glob("*.txt")):
        m = CH_PATTERN.match(f.name)
        if m and m.group(2) == episode_slug:
            candidates.append(f)
    if not candidates:
        existing = ", ".join(f.name for f in sorted(chapters_dir.glob("*.txt")))
        sys.exit(
            f"ERROR: no chapter file matches slug '{episode_slug}' in {chapters_dir}\n"
            f"  Expected: ch??-{episode_slug}.txt\n"
            f"  Existing chapters: {existing}\n"
            f"  Under the 1:1 chapter ↔ episode mapping (SKILL.md §0), the episode "
            f"slug after 'EP##-' must match the chapter slug after 'ch##-' exactly."
        )
    if len(candidates) > 1:
        sys.exit(
            f"ERROR: multiple chapter files match slug '{episode_slug}': "
            f"{[c.name for c in candidates]}. Resolve the duplicate before building."
        )
    return candidates[0]


def _resolve_book_tradition(file_path: Path) -> str:
    """F34 (2026-05-25): walk up from `file_path` to find series-config.yaml."""
    resolved = file_path.resolve()
    cursor = resolved if resolved.is_dir() else resolved.parent
    for _ in range(8):
        cfg = cursor / "series-config.yaml"
        if cfg.exists():
            try:
                text = cfg.read_text(encoding="utf-8")
                for line in text.splitlines():
                    line = line.strip()
                    if line.startswith("source_tradition:"):
                        return line.split(":", 1)[1].strip().strip("'\"").lower() or "islam"
            except OSError:
                pass
            break
        if cursor == cursor.parent:
            break
        cursor = cursor.parent
    return "islam"


def assert_doctrinal_clean(text: str, file_path: Path) -> None:
    """Category T hard gate. Runs T3 forbidden-phrase checks plus T1/T2/T5 advisory checks."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _doctrinal import run_doctrinal_checks, tradition_pack_dir  # noqa: E402

    tradition = _resolve_book_tradition(file_path)
    pack_dir = tradition_pack_dir(tradition)
    if not pack_dir.is_dir():
        print(
            f"INFO: T-NO-PACK — book's source_tradition={tradition!r} has no doctrinal "
            f"data pack at {pack_dir}. "
            f"Skipping Category T checks. Add a tradition pack under "
            f"content/_shared/<tradition>/ to enable doctrinal gating for this book.",
            file=sys.stderr,
        )
        return

    findings = run_doctrinal_checks(text)
    p0_findings = [f for f in findings if f.severity == "P0"]
    p1_findings = [f for f in findings if f.severity == "P1"]

    for f in p1_findings:
        _flag_p1(
            f.check_id,
            file_path,
            f"{f.signature} — {f.reason[:140]} "
            f"(context: …{f.context_excerpt[:80]}…)"
            + (f" — use: {f.replacement}" if f.replacement else ""),
        )

    if p0_findings:
        lines = ["ERROR: doctrinal-accuracy P0 violations in chapter:"]
        for f in p0_findings:
            lines.append(
                f"  [{f.check_id}] {f.signature}"
                + (f" → use '{f.replacement}'" if f.replacement else "")
            )
            lines.append(f"    context: …{f.context_excerpt[:200]}…")
            if f.reason:
                lines.append(f"    reason: {f.reason[:200]}")
        lines.append(
            f"  See content/_shared/islam/ for the canonical data and "
            f"scripts/podcast/_doctrinal.py for the rule logic."
        )
        sys.exit("\n".join(lines))
