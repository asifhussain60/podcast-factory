#!/usr/bin/env python3
"""build_episode_txt.py — Validate the chapter + framing pair, emit the customize-prompt episode txt.

ARCHITECTURE (v3.4):

  - `BOOK_DIR/chapters/chNN-<slug>.txt` IS the NotebookLM SOURCE. The user uploads it
    directly. The build script does NOT transform it. It only validates it.
  - `BOOK_DIR/episodes/EP##-<slug>.txt` IS the NotebookLM CUSTOMIZE PROMPT. The user
    pastes it into NotebookLM's *Customize* prompt box. The build script writes it
    from the body of `BOOK_DIR/_system/episode-drafts/EP##-<slug>/00-framing.md`,
    minus any trailing "Upload checklist" section, minus any HTML comments.

So the per-episode upload flow is:

  1. Open `BOOK_DIR/chapters/chNN-<slug>.txt` in NotebookLM's "Add source" dialog.
     Upload the file as the single source for the notebook.
  2. Open `BOOK_DIR/episodes/EP##-<slug>.txt` in a text editor.
     Copy everything in the file. Paste into NotebookLM's *Customize* prompt box.
  3. Click *Generate*.

The slug after `ch##-` must match the slug after `EP##-` exactly (1:1 chapter ↔ episode
mapping, per SKILL.md §0).

VALIDATION GATES (both files):

  - `BOOK_DIR/chapters/` must contain at least one .txt before any episode can be built.
  - The matching `chNN-<slug>.txt` must exist for the requested `EP##-<slug>`.
  - **Chapter file (the SOURCE the user uploads):**
    - No HTML comments (would be read literally by NotebookLM).
    - No meta-prose tells (META_PROSE_TELLS + META_PROSE_REGEX_TELLS — any match is
      a hard error). Authoring metadata belongs in
      `BOOK_DIR/_system/enrichment-log.md`, NOT in the chapter file.
    - **No inline phonetic parens** (R-PHONETICS-OUT, 2026-05-17). Patterns like
      `*Term* (PHO-ne-tic; gloss)` or `> (bis-mil-laah ir-rah-maan ...)` are read
      aloud by NotebookLM as content. Phonetic guidance lives in the customize
      prompt's `## Pronunciation` block instead.
    - **No abbreviated work titles** (R-NO-ABBREVIATION). `the Ihya`, `EI`, `the Nahj`,
      `Sahihayn` etc. are forbidden; use full canonical titles.
    - **Honorific expansions appear at most once per figure** (R-HONORIFIC-ONCE).
      `(peace and blessings be upon him)` / `ﷺ` / `(PBUH)` / `(AS)` / `(RA)` and
      equivalents may expand only on first mention of each figure.
    - Word count in [500, 10000] hard band (notebooklm-best-practices.md §3).
      The 10,000 ceiling accommodates the **Extended Deep Dive** tier
      (~30–45 min audio, 5,500–9,500 words). Default Deep Dive remains
      in 1,800–2,800; Longer in 2,800–4,500; Extended in 5,500–9,500.
      The intentional gap between Longer (≤4,500) and Extended (≥5,500)
      is a tier-discipline boundary: chapters falling at 4,800 are in a
      dead zone (too dense for Longer, too thin to sustain Extended);
      either tighten ≤4,500 or expand via Phase 0e enrichment ≥5,500.
  - **Framing file (the CUSTOMIZE PROMPT):**
    - Strip trailing "Upload checklist" section (it's the user's how-to, not the prompt).
    - Strip HTML comments.
    - Re-check META_PROSE_TELLS on the framing too — leaks through here are equally bad,
      since the framing is pasted into NotebookLM's Customize box.
    - **`## Pronunciation` block uses imperative form** (R-PRONUNCIATION-IMPERATIVE).
      Every non-blank line MUST start with `Pronounce "` or `Do not`. Legacy
      passive-list pattern (`*term*: phonetic`) is rejected.
    - **`## Do not` DENY block present** (R-NOMODERNIZE + R-NOSURPRISE). Must include
      the canonical modernization-deny and surprise-deny terms.
    - **Final line is the no-read-aloud guard** (R-NO-READ-PROMPT).
    - Word count in [150, 2000] hard band.

Usage:
  python3 build_episode_txt.py <BOOK_DIR> <EP##-slug>

Example:
  python3 scripts/podcast/build_episode_txt.py \\
    content/podcast/library/<category>/<book-slug> \\
    EP##-<slug>

Per-book overrides (optional, book-agnostic):
  BOOK_DIR/_system/meta-prose-tells.md  — extra substring tells appended to
  the global META_PROSE_TELLS list. One tell per line, prefixed by `- `.
  Use this for book-specific authoring phrases (e.g. an author's name in
  a self-describing prose pattern) instead of editing this file.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Chapter (SOURCE) word-count bounds — per notebooklm-best-practices.md §3
# Tier bands:
#   Brief Deep Dive    (~6–10 min):  1,000–1,800 words
#   Default Deep Dive  (~12–15 min): 1,800–2,800
#   Longer Deep Dive   (~18–22 min): 2,800–4,500
#   Extended Deep Dive (~30–45 min): 5,500–9,500   ← recommended for dense / philosophical sources
# Hard band [500, 10,000] enforced here; soft sanity band [1,000, 9,500].
# The dead zone 4,500–5,500 produces tier-confused chapters (too dense for
# Longer, too thin to sustain Extended) — flagged with a soft warning but
# not refused.
CHAPTER_WORD_MIN_HARD = 500
CHAPTER_WORD_MAX_HARD = 10000
CHAPTER_WORD_MIN_SOFT = 1000
CHAPTER_WORD_MAX_SOFT = 9500
CHAPTER_DEAD_ZONE_MIN = 4500
CHAPTER_DEAD_ZONE_MAX = 5500

# Framing (CUSTOMIZE PROMPT) word-count bounds — per notebooklm-best-practices.md §5.
# Default tier framing: 200–500 words.  Longer tier: up to ~800.  Extended tier:
# 1,000–1,800 in body (the 6-part focus, 3 tensions, 4 anchor passages), plus a
# pronunciation block that on a name-dense source (8+ figures, multiple book
# titles, technical vocabulary) commonly runs another 1,000–1,500 words. Hard
# cap 3,500 to allow Extended episodes the headroom for full phonetic
# discipline + R-* mandatory clauses without authoring trim. Going past this
# risks NotebookLM deprioritizing the actual steering content.
FRAMING_WORD_MIN = 150
FRAMING_WORD_MAX = 3500

EP_PATTERN = re.compile(r"^EP(\d+)-(.+)$")
CH_PATTERN = re.compile(r"^ch(\d+)[a-z]?-(.+)\.txt$")

HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)

# Substrings that almost always introduce meta-prose about the file itself rather than
# content. Any match in chapter OR framing is a hard error.
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
    "per content/podcast/.skill/handbook",
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
# The chapter MUST NOT carry inline phonetic guides. Two failure shapes:
#   1. *Term* (PHO-NE-TIC; gloss)              — italicized term followed by paren
#   2. > (bis-mil-laah ir-rah-maan ir-ra-heem) — phonetic-only blockquote line
INLINE_PHONETIC_PATTERNS = [
    # *italic* ( UPPERCASE-HYPHEN-RESPELLING ...)  — e.g. *Sunnah* (SOON-nah; ...)
    re.compile(r"\*[A-Za-z'`\-]+\*\s*\(\s*[A-Za-z]+[-][A-Za-z]+"),
    # > (lowercase-hyphen-respelling lowercase-hyphen-respelling ...) — post-transliteration line
    re.compile(r"^>\s*\(\s*[a-z]+\-[a-z]+(?:[-\s][a-z\-]+)+", re.MULTILINE),
    # bare inline form (term) (PHO-NE-TIC) e.g. *Mujahadah* (moo-JAA-ha-dah; ...)
    re.compile(r"\([A-Z]{2,}[\-][A-Z][A-Z\-]+[a-z\-]*\b"),
]


# ─── R-NO-ABBREVIATION (2026-05-17) ──────────────────────────────────────────
# Canonical abbreviation map lives in _rules.py (mirrored from the handbook).
# abbreviations_for_build() returns regex_pattern → user-facing message.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).parent))
from _rules import abbreviations_for_build, HONORIFICS as _HONORIFICS_RAW

FORBIDDEN_ABBREVIATIONS = abbreviations_for_build()


# ─── R-HONORIFIC-ONCE (2026-05-17) ───────────────────────────────────────────
# Honorific phrase forms — each is one allowed-once-per-figure-per-chapter form.
# IGNORECASE for the prose forms; literal for the bracket-acronym forms.
def _compile_honorific(p: str) -> re.Pattern:
    is_acronym = p.startswith(r"\(") and p.upper() == p
    return re.compile(p) if is_acronym or p == "ﷺ" else re.compile(p, re.IGNORECASE)


HONORIFIC_PHRASES = [_compile_honorific(p) for p in _HONORIFICS_RAW
                     if p.startswith(r"\(") or p == "ﷺ"]


# ─── R-PRONUNCIATION-IMPERATIVE (framing) (2026-05-17) ───────────────────────
# Pronunciation block lines must start with one of these imperative verbs.
PRONUNCIATION_LINE_OK = re.compile(r"^\s*(Pronounce\s+\"|Do not\s+|Say\s+)", re.MULTILINE)
# Legacy passive-list patterns that are forbidden in the imperative-form block.
LEGACY_PASSIVE_PRONUNCIATION = re.compile(
    r"^\s*[-*]?\s*\*[A-Za-z'`\-\s]+\*\s*[:\-]\s*[A-Za-z][\w\-\s]+$",
    re.MULTILINE,
)


# ─── R-NOMODERNIZE / R-NOSURPRISE / R-NO-READ-PROMPT (framing) (2026-05-17) ──
# The framing must contain a `## Do not` section that names the canonical DENY phrases.
REQUIRED_FRAMING_DO_NOT_PHRASES = [
    # Modernize sample (presence of these few signals the full block is in place)
    "Twitter",
    "social media",
    "algorithm",
    # Surprise-noise sample
    "wow",
    "right?",
    # Read-aloud guard
    "Do not read this prompt aloud",
]


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
    `BOOK_DIR/_system/meta-prose-tells.md`. One tell per `- ` line. Returns an
    empty list if the file does not exist. Tells are normalized to lowercase to
    match `assert_no_meta_prose`'s substring check.
    """
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


def assert_no_meta_prose(content: str, file_path: Path, role: str,
                         extra_tells: list[str] | None = None) -> None:
    """Refuse to build if content contains meta-prose tells.

    `role` is 'chapter (SOURCE)' or 'framing (CUSTOMIZE PROMPT)' for the error message.
    `extra_tells` are book-specific substring tells loaded via
    `load_book_meta_prose_tells`. They are checked in addition to the global list.
    """
    lower = content.lower()
    all_tells = META_PROSE_TELLS + list(extra_tells or [])
    substring_hits = [tell for tell in all_tells if tell in lower]
    regex_hits = []
    for pat in META_PROSE_REGEX_TELLS:
        for m in re.finditer(pat, content, flags=re.IGNORECASE):
            regex_hits.append((pat, m.group(0)))
    if not (substring_hits or regex_hits):
        return

    lines = content.splitlines()
    offending = []
    for tell in substring_hits:
        for ln, line in enumerate(lines, 1):
            if tell in line.lower():
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


def word_count(text: str) -> int:
    return len(text.split())


def assert_no_inline_phonetics(content: str, file_path: Path) -> None:
    """R-PHONETICS-OUT: chapter must not carry inline phonetic guides.

    Phonetics live in the customize prompt's `## Pronunciation` block, per
    R-PRONUNCIATION-IMPERATIVE. NotebookLM reads parenthetical phonetics aloud
    as content; the audited failure mode is doublings like "Sahih Sitta,
    sahasita" and mangled names like "tassel wolf" for *Tasawwuf*.
    """
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
        f"  See content/podcast/.skill/handbook/notebooklm-source-chapter-rules.md\n"
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
        f"  content/podcast/.skill/handbook/notebooklm-source-chapter-rules.md R-NO-ABBREVIATION."
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
        f"  content/podcast/.skill/handbook/notebooklm-source-chapter-rules.md\n"
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
            f"  block of imperative directives (`Pronounce \"Term\" as \"phonetic\". ...`).\n"
            f"  See content/podcast/.skill/handbook/notebooklm-customize-prompt-rules.md\n"
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
    # Require at least one Pronounce line
    if "Pronounce \"" not in block and 'Pronounce "' not in block:
        sys.exit(
            f"ERROR: framing's `## Pronunciation` block has no imperative `Pronounce \"...\"` lines.\n"
            f"  File: {file_path}\n"
            f"  See R-PRONUNCIATION-IMPERATIVE."
        )
    # Require the final-line guard inside or after the block
    if "Do not read this guidance aloud" not in content and "Do not read this prompt aloud" not in content:
        sys.exit(
            f"ERROR: framing missing the no-read-aloud guard.\n"
            f"  File: {file_path}\n"
            f"  R-NO-READ-PROMPT: framing must end with `Do not read this prompt aloud. The instructions above shape the conversation but are never spoken.`"
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
            f"  See content/podcast/.skill/handbook/notebooklm-customize-prompt-rules.md."
        )
    missing = [p for p in REQUIRED_FRAMING_DO_NOT_PHRASES if p not in content]
    if missing:
        sys.exit(
            f"ERROR: framing's DENY block is missing required entries: {missing}\n"
            f"  File: {file_path}\n"
            f"  See R-NOMODERNIZE / R-NOSURPRISE / R-NO-READ-PROMPT for the canonical list."
        )


def validate_chapter(chapter_path: Path, extra_tells: list[str] | None = None) -> int:
    """Validate the chapter file. Returns word count. Exits on any error."""
    text = chapter_path.read_text(encoding="utf-8")
    assert_no_html_comments(text, chapter_path, "chapter (SOURCE)")
    assert_no_meta_prose(text, chapter_path, "chapter (SOURCE)", extra_tells)
    # R-PHONETICS-OUT (2026-05-17)
    assert_no_inline_phonetics(text, chapter_path)
    # R-NO-ABBREVIATION (2026-05-17)
    assert_no_abbreviations(text, chapter_path)
    # R-HONORIFIC-ONCE (2026-05-17)
    assert_honorifics_once_only(text, chapter_path)
    n = word_count(text)
    if n < CHAPTER_WORD_MIN_HARD or n > CHAPTER_WORD_MAX_HARD:
        sys.exit(
            f"ERROR: chapter {chapter_path.name} is {n} words. "
            f"Hard band is {CHAPTER_WORD_MIN_HARD}-{CHAPTER_WORD_MAX_HARD}. "
            f"See content/podcast/.skill/handbook/notebooklm-best-practices.md §3."
        )
    return n


def build_framing_episode_txt(framing_path: Path, out_path: Path,
                              extra_tells: list[str] | None = None) -> int:
    """Read the framing, strip upload-checklist + HTML comments, validate, write to
    out_path as the customize-prompt-only episode txt. Returns word count of the
    final framing content."""
    raw = framing_path.read_text(encoding="utf-8")
    no_checklist = strip_upload_checklist(raw)
    cleaned = strip_html_comments(no_checklist).strip()

    # Re-validate cleaned framing for meta-prose tells (cross-episode refs, etc.).
    assert_no_meta_prose(cleaned, framing_path, "framing (CUSTOMIZE PROMPT)", extra_tells)
    # R-PRONUNCIATION-IMPERATIVE (2026-05-17)
    assert_framing_pronunciation_imperative(cleaned, framing_path)
    # R-NOMODERNIZE + R-NOSURPRISE + R-NO-READ-PROMPT (2026-05-17)
    assert_framing_deny_block(cleaned, framing_path)

    n = word_count(cleaned)
    if n < FRAMING_WORD_MIN or n > FRAMING_WORD_MAX:
        sys.exit(
            f"ERROR: framing {framing_path.name} produces a customize prompt of {n} "
            f"words. Target band is {FRAMING_WORD_MIN}-{FRAMING_WORD_MAX}. "
            f"See content/podcast/.skill/handbook/notebooklm-best-practices.md §5."
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(cleaned + "\n", encoding="utf-8")
    return n


def build(book_dir: Path, episode_id: str) -> None:
    book_dir = book_dir.resolve()
    if not book_dir.is_dir():
        sys.exit(f"ERROR: BOOK_DIR is not a directory: {book_dir}")

    m = EP_PATTERN.match(episode_id)
    if not m:
        sys.exit(
            f"ERROR: episode id '{episode_id}' does not match EP##-<slug>. "
            f"Example: EP01-frame-and-first-counsel"
        )
    episode_num, episode_slug = m.group(1), m.group(2)

    draft_dir = book_dir / "_system" / "episode-drafts" / episode_id
    if not draft_dir.is_dir():
        sys.exit(f"ERROR: missing draft folder: {draft_dir}")

    framing_file = draft_dir / "00-framing.md"
    if not framing_file.exists():
        sys.exit(f"ERROR: missing 00-framing.md in {draft_dir}")

    # Load any book-specific meta-prose tells from BOOK_DIR/_system/meta-prose-tells.md.
    # This keeps author-specific phrases (e.g. "anything <author> only implies") out of
    # the global META_PROSE_TELLS list — each book carries its own tells next to its
    # chapters, so they don't bleed across books.
    extra_tells = load_book_meta_prose_tells(book_dir)

    # 1. Validate the chapter (uploaded as-is to NotebookLM as the SOURCE).
    assert_chapters_populated(book_dir)
    chapter_file = find_chapter_by_slug(book_dir / "chapters", episode_slug)
    chapter_words = validate_chapter(chapter_file, extra_tells)

    # 2. Build the customize-prompt-only episode txt.
    out_path = book_dir / "episodes" / f"{episode_id}.txt"
    framing_words = build_framing_episode_txt(framing_file, out_path, extra_tells)

    # Word-count warnings (band-soft, not hard).
    warnings = []
    if chapter_words < CHAPTER_WORD_MIN_SOFT:
        warnings.append(
            f"chapter is {chapter_words} words — under the {CHAPTER_WORD_MIN_SOFT}-word "
            f"Brief Deep Dive floor. NotebookLM hosts may resort to filler."
        )
    if chapter_words > CHAPTER_WORD_MAX_SOFT:
        warnings.append(
            f"chapter is {chapter_words} words — over the {CHAPTER_WORD_MAX_SOFT}-word "
            f"Extended Deep Dive ceiling. Conversation may lose thread."
        )
    if CHAPTER_DEAD_ZONE_MIN < chapter_words < CHAPTER_DEAD_ZONE_MAX:
        warnings.append(
            f"chapter is {chapter_words} words — in the tier-dead-zone "
            f"({CHAPTER_DEAD_ZONE_MIN}-{CHAPTER_DEAD_ZONE_MAX}): too dense for Longer "
            f"Deep Dive, too thin to sustain Extended Deep Dive. Either tighten "
            f"to ≤{CHAPTER_DEAD_ZONE_MIN} or expand via Phase 0e enrichment "
            f"to ≥{CHAPTER_DEAD_ZONE_MAX}."
        )

    print(
        f"Validated chapter (SOURCE): {chapter_file}\n"
        f"  {chapter_words} words — uploaded as-is to NotebookLM\n"
        f"\n"
        f"Wrote episode (CUSTOMIZE PROMPT): {out_path}\n"
        f"  {framing_words} words — paste into NotebookLM's Customize prompt box\n"
        f"\n"
        f"To upload:\n"
        f"  1. Upload {chapter_file.relative_to(book_dir.parent.parent)} to NotebookLM as the single source.\n"
        f"  2. Paste contents of {out_path.relative_to(book_dir.parent.parent)} into NotebookLM's Customize prompt box.\n"
        f"  3. Click Generate."
    )
    for w in warnings:
        print(f"  WARN: {w}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Usage: build_episode_txt.py <BOOK_DIR> <EP##-slug>")
    build(Path(sys.argv[1]), sys.argv[2])
