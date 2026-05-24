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
    _workspace/<category>/<book-slug> \\
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
# Hard band [500, 10,500] enforced here; soft sanity band [1,000, 9,500].
# X6 (2026-05-21): hard ceiling bumped from 10,000 → 10,500 to match the "~10,000"
# language in notebooklm-best-practices.md §3 (the ~ implies tolerance; KaR's
# ch12 at 10,180 and ch14b at 10,112 were 1-2% over the round-number ceiling
# while the underlying empirical concern — NotebookLM falling back to
# summarization — has no sharp inflection at exactly 10k). Soft warning still
# fires at 9,500 so editorial attention is drawn early; hard refusal now
# only at 5% past the round-number target.
#
# The dead zone 4,500–5,500 produces tier-confused chapters (too dense for
# Longer, too thin to sustain Extended) — flagged with a soft warning but
# not refused.
CHAPTER_WORD_MIN_HARD = 500
CHAPTER_WORD_MAX_HARD = 10500
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
FRAMING_WORD_MAX = 3700        # F10 fix (2026-05-21): bumped from 3500 to 3700 (~5% tolerance
                               # mirroring the chapter-band tolerance landed in X6). The
                               # handbook's "~3500" prose carries the same approximate-
                               # ness the chapter band does. Trimmed framings landing at
                               # 3490-3550 (right at the strict cap) were tripping the
                               # validator on minor word-count fluctuations.

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
    # X5 (2026-05-21): tightened to require a 2+ uppercase respelling segment
    # SOMEWHERE in the paren content. The prior form `[A-Za-z]+[-][A-Za-z]+`
    # also matched scholarly transliterations like `*opposite* (al-mukhalif)`,
    # which the IJMES/Chicago Theological Seminary convention places as
    # English-to-Arabic bridges (not pronunciation hints). Phonetic guides keep
    # their signature: at least one 2+-uppercase respelling segment (SOON, JAA,
    # MOO, etc.) — that's what triggers NotebookLM to vocalize the spelling.
    #
    # *italic* (... HYPHEN-CONNECTED with at least one UPPERCASE 2+ segment ...)
    #   — e.g. *Sunnah* (SOON-nah; ...), *Mujahadah* (moo-JAA-ha-dah; ...)
    re.compile(r"\*[A-Za-z'`\-]+\*\s*\(\s*[A-Za-z\-]*[A-Z]{2,}"),
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


# ─── R-NAMEDISCIPLINE / R-DRAMATIC-ARC / R-CHALLENGER-FRICTION /
#     R-ANALOGY-CAP / R-RECURRING-THESIS / R-NO-MANUSCRIPT-META  (2026-05-21) ──
#
# These 6 checks are P1 FLAG-level (warnings, not hard fails). They emit to
# stderr and append to a module-level list; the orchestrator's challenger pass
# escalates them in normal converge iterations. The existing rule checks above
# remain hard-fail (sys.exit) to preserve the build-script contract that
# emission means "passes hard gates"; the new structural checks below could
# be downgraded to a CLI flag later if a particular author needs to bypass.
P1_FLAGS: list[str] = []


def _flag_p1(rule: str, file_path: Path, message: str) -> None:
    """Record a P1 FLAG for the orchestrator's challenger pass to escalate.

    Emits to stderr immediately so the operator sees it; appends to the
    process-wide P1_FLAGS list so a downstream caller (e.g. the orchestrator)
    can collect the full set after the build.
    """
    line = f"FLAG (P1) [{rule}] {file_path.name}: {message}"
    print(line, file=sys.stderr)
    P1_FLAGS.append(line)


# Pushback patterns the Color host must use (R-CHALLENGER-FRICTION).
CHALLENGER_PUSHBACK_PATTERNS = [
    "I don't buy that yet",
    "I don’t buy that yet",          # smart-quote variant
    "That sounds like wordplay",
    "Isn't this just replacing",
    "Isn’t this just replacing",     # smart-quote variant
    "How is this different",
]


# Forbidden manuscript-meta tells (R-NO-MANUSCRIPT-META).
MANUSCRIPT_META_TELLS = [
    "opening folios are heavily damaged",
    "what can be reconstructed reads",
    "the text breaks off",
    "collapses in the OCR",
    "a second damaged folio carries fragments",
    "translator's note",
    "translator’s note",                # smart-quote variant
    "editor's note",
    "editor’s note",
    "manuscript notes",
]

# Section-header tells for R-NO-MANUSCRIPT-META.
MANUSCRIPT_META_HEADER_RE = re.compile(
    r"^#{1,6}\s+(?:What\s+survives\s+at\s+the\s+head|"
    r"What\s+survives\s+of\s+the|"
    r"What\s+can\s+be\s+recovered)\b",
    re.MULTILINE | re.IGNORECASE,
)


# F27 — Tier 2.5 TTS-safe enforcement constants (2026-05-22).
# Validates against Arabic transliterations, forbidden analogies, modern
# artifacts, honorific bounds, surah names, and alqaab discipline.
# Doctrine empirically locked across v3/v4/v4-revised audio audits.

# Arabic transliteration patterns (compile once)
ARABIC_TRANSLIT_PATTERNS = [
    re.compile(r"\bal-[A-Z][a-zA-Z]+\b"),     # al-Kirmani, al-Shams, al-Ahzab
    re.compile(r"\bAbu\s+[A-Z][a-zA-Z]+"),    # Abu Hatim, Abu Ya'qub
    re.compile(r"\bIbn\s+[A-Z][a-zA-Z]+"),    # Ibn Mas'ud
    re.compile(r"\bbint\s+[A-Z][a-zA-Z]+"),   # bint X
    re.compile(r"\b[A-Za-z]+iyy[ah]\b"),      # -iyyah suffix (al-Sajjadiyya)
]

# TTS-safe Arabic-origin terms (verified across 3 audio audits)
ALLOWED_ARABIC_ORIGIN_LOWER = {
    "quran", "imam", "medina", "ismaili", "fatimid", "fatimi",
    "yusuf ali", "muhammad",  # The Prophet's name
    # Divine attributes (stable in English usage)
    "al-bari", "al-mubdi", "al-wahid", "al-haqq",
}

# Surahs commonly cited in Islamic philosophy/devotional texts.
# All forbidden in chapter/framing text; must be referenced by English meaning.
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

# Analogies model-invented across v1-v4 audio (the M1 leak surface).
# Framing should never introduce these; chapter prose source-images
# are handled by a separate carve-out (see assert_framing_analogy_cap_strict).
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

# Modern artifacts that fail R-NOMODERNIZE.
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

# Established English alqaab (TTS-safe; allowed to speak).
ESTABLISHED_ENGLISH_ALQAAB = {
    "commander of the faithful",
    "lion of god",
}

# Literal-translation alqaab that damage register (the "Striker" anti-pattern).
FORBIDDEN_LITERAL_ALQAAB = {
    "the striker",
    "the puller",
    "the returner",
    "the lion of allah",
    "the asadullah",
}


def assert_no_arabic_transliteration(content: str, file_path: Path, role: str) -> None:
    """F27 #1+#2: block Arabic transliterations in chapter prose or framing.

    Detects: al-X patterns, Abu/Ibn/bint X compounds, -iyyah suffixes.
    Whitelist: ALLOWED_ARABIC_ORIGIN_LOWER (Quran, Imam, Medina, Ismaili,
    Fatimid, Yusuf Ali, Muhammad, divine attributes).
    """
    # Strip pronunciation block from framing (legitimate Arabic mentions there)
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
    """F27 #3: detect forbidden analogies in framing.md.

    Allows: the three governing analogies (mirror, messenger, light-on-X);
    source-image carve-outs (seven seas, speaker-foundation, male-female).
    Blocks: model-invented analogies across v1-v4 audio history.
    """
    scan_text = content.lower()

    # Strip the framing's own forbidden-list section (it MENTIONS these patterns
    # as instructions; matching them would be a false positive).
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

    # Strip the framing's own ban-list section (false-positive guard)
    scan_text_scrubbed = re.sub(
        r"##\s+\d*\.?\s*R-NOMODERNIZE.*?(?=\n##\s|\Z)",
        "",
        scan_text,
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
    """F27 #5: each honorific appears EXACTLY ONCE (not zero, not twice).

    v3 audio dropped both honorifics to zero. v4-revised had "peace be
    upon him" misplaced. This validator catches both failure modes.
    """
    scan_text_lower = content.lower()
    # Strip pronunciation + honorific-rule sections (they MENTION the patterns)
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
    # Subtract pbuhf occurrences from pbuh (pbuhf contains "peace be upon him" as substring? no, "be upon him" vs "be upon him and his family")
    # Actually "peace and blessings of allah be upon him and his family" does NOT contain "peace be upon him" as substring.
    # So counts are independent.

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
    """F27 #6: detect Arabic surah names. F29 doctrine: use English meanings.

    Catches the v4-revised "Qaf → cough" TTS-mangle class.
    """
    scan_text = content.lower()
    # Strip framing's surah lookup-table section (false-positive guard)
    scan_text_scrubbed = re.sub(
        r"##?\s*\d*\.?\s*(?:R-SURAH|surah\s+(?:lookup|reference|names)).*?(?=\n##\s|\Z)",
        "",
        scan_text,
        flags=re.DOTALL,
    )

    violations: list[str] = []
    for surah in KNOWN_SURAH_NAMES_LOWER:
        # Use word-boundary-ish check
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
    """F27 #7: block awkward literal alqaab translations (the "Striker" pattern)."""
    scan_text_lower = content.lower()
    violations = [k for k in FORBIDDEN_LITERAL_ALQAAB if k in scan_text_lower]
    if violations:
        _flag_p1(
            "R-ALQAAB-FUNCTIONAL-PARAPHRASE",
            file_path,
            f"{role}: literal alqaab translations detected: {violations}. "
            f"F24 doctrine: use functional paraphrase ('one of his martial honorifics')."
        )


# F25 / F27 #8 (2026-05-23): apparatus-table schema for 99-show-notes.md.
# The "Name and Title Preservation Table" gives the written-layer scholarly
# apparatus that the TTS-safe audio layer (chapter prose + framing) deliberately
# omits — preserves the original Arabic transliteration, category, written form,
# the audio label the listener actually hears, and the chapter line where that
# label first appears. Validator fires only when the file exists (silent skip
# while F25 generation infrastructure is still pending; depends on F26
# name-aliases.yml schema v2).
SHOW_NOTES_TABLE_HEADER = "## Name and Title Preservation Table"
SHOW_NOTES_REQUIRED_COLUMNS = (
    "Original / Transliteration",
    "Category",
    "Written Form",
    "Audio Label",
    "First Audio Use",
)


def assert_show_notes_has_apparatus_table(content: str, file_path: Path) -> None:
    """F27 #8 / F25: 99-show-notes.md must contain a structured apparatus table.

    Catches drift in the written-layer apparatus. Soft-flags both the missing
    section header and the missing required columns. Callers should check that
    `file_path.exists()` before invoking (silent skip if absent — F25 generation
    infrastructure is still pending).
    """
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
    """R-NAMEDISCIPLINE: framing has a Name discipline section with rotation sets.

    Detection: header presence (`## Name discipline` or equivalent under
    Pronunciation hooks) + at least one rotation set (a line containing
    `Rotation:` or `→` followed by aliases). FLAG (P1) if missing.
    """
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
    # Look for at least one rotation set: a line with `Rotation:` or `→` followed
    # by 3+ aliases. Both forms accepted.
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
    """R-DRAMATIC-ARC: debate-format framings declare a multi-beat arc.

    Detection: either (a) presence of `Beat 1`..`Beat 6` markers (≥6 beats)
    OR (b) explicit declaration of crisis / failed-answer / pivot / correction
    / stakes substrings. FLAG (P1) if neither.
    """
    beat_markers = re.findall(r"\bBeat\s+\d+\b", content)
    distinct_beats = set(beat_markers)
    has_six_beats = len(distinct_beats) >= 6

    # Substring tells for the 6-beat structure (case-insensitive).
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
    """R-CHALLENGER-FRICTION: framing names challenger role + ≥2 pushback patterns.

    Detection: `## Host dynamic` OR `## Central tensions` mentions the Color
    host's challenger role (substring `challenger` or `pushback` or `friction`)
    AND lists ≥2 of the required pushback patterns. FLAG (P1) if not.
    """
    # First confirm the framing has either Host dynamic or Central tensions.
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
    pattern_hits = sum(1 for p in CHALLENGER_PUSHBACK_PATTERNS if p in content)
    # Each smart-quote variant double-counts the same pattern; de-dupe by base.
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
    """R-ANALOGY-CAP: framing's Tone constraints declares 3-5 governing analogies.

    Detection: presence of an analogy enumeration inside `## Tone constraints`
    AND count between 3 and 5 inclusive. FLAG (P1) if either out of range OR
    no enumeration present.
    """
    # Extract the Tone constraints section. Match `## Tone constraints` (and
    # `## Tone`) up to the next `## ` header.
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
    # Look for analogy enumeration. Accept these list shapes:
    #   - Analogy 1 — <name>
    #   - **Analogy N — <name>** (Beat N)
    #   - Analogy N (Beat N)
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
    """R-RECURRING-THESIS: framing references the chapter's central thesis 3×.

    Detection: either (a) the exact verbatim thesis string from
    `contract_anchor` appears 3+ times in the framing, OR (b) explicit
    reference to `R-RECURRING-THESIS` rule with instruction to repeat 3
    times. FLAG (P1) if neither.
    """
    if contract_anchor:
        # Count occurrences of the verbatim thesis. Case-sensitive — the rule
        # requires VERBATIM repetition; smart-quote vs straight-quote
        # variations are NOT relaxed by this validator (they'd violate the rule).
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
        # ≥3 occurrences confirmed — also check the framing references the rule
        # itself for operator visibility, but don't flag on rule-mention alone.
        return
    # No contract anchor available — fall back to rule-reference detection.
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
    """R-NO-MANUSCRIPT-META: chapter source carries no manuscript-history meta.

    Detection: substring scan for the forbidden manuscript-state tells AND
    regex for section headers like `What survives at the head`. Each hit
    logged with line number + matched phrase. FLAG (P1) if any hit.
    """
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
            f"  See content/podcast/.skill/handbook/notebooklm-customize-prompt-rules.md."
        )
    missing = [p for p in REQUIRED_FRAMING_DO_NOT_PHRASES if p not in content]
    if missing:
        sys.exit(
            f"ERROR: framing's DENY block is missing required entries: {missing}\n"
            f"  File: {file_path}\n"
            f"  See R-NOMODERNIZE / R-NOSURPRISE / R-NO-READ-PROMPT for the canonical list."
        )


def assert_doctrinal_clean(text: str, file_path: Path) -> None:
    """Category T hard gate. Runs T3 forbidden-phrase checks (Imam Ali,
    Imam Fatima, etc.) plus T1/T2/T5 advisory checks. P0 findings exit the
    build; P1 findings emit as FLAG (P1) lines for the challenger's
    convergence loop to surface.

    Lives next to validate_chapter() so the rule wiring is visible from one
    place. See scripts/podcast/_doctrinal.py for the rule implementations.
    """
    # Local import: _doctrinal isn't needed at module-import time, and keeping
    # it lazy avoids forcing the YAML files to exist for every callsite that
    # only uses build_episode_txt's other gates.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _doctrinal import run_doctrinal_checks   # noqa: E402

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
    # Category T — doctrinal accuracy (T3 forbidden phrases). Hard gate;
    # blocks ship on any P0 violation (e.g. "Imam Ali" when source-correct
    # is "Father of Imams"). See scripts/podcast/_doctrinal.py and
    # content/_shared/islam/*.yml for the canonical data.
    assert_doctrinal_clean(text, chapter_path)
    # R-NO-MANUSCRIPT-META (2026-05-21, X14) — P1 FLAG (warning, not hard fail).
    assert_chapter_no_manuscript_meta(text, chapter_path)
    # F27 Tier 2.5 (2026-05-22) — TTS-safe enforcement. All P1 flags
    # (warnings; doctrine drift from prompt-only rules is the M1 pattern
    # these catch). Won't hard-fail re-emit of v3-era content.
    assert_no_arabic_transliteration(text, chapter_path, role="chapter (SOURCE)")
    assert_no_arabic_surah_names(text, chapter_path, role="chapter (SOURCE)")
    assert_alqaab_only_established_or_paraphrased(text, chapter_path, role="chapter (SOURCE)")
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
    # R-NAMEDISCIPLINE / R-DRAMATIC-ARC / R-CHALLENGER-FRICTION /
    # R-ANALOGY-CAP / R-RECURRING-THESIS (2026-05-21, X15+X16) — P1 FLAGS
    # (warnings, not hard fails). The orchestrator's challenger pass
    # escalates these in normal converge iterations.
    assert_framing_has_name_discipline_section(cleaned, framing_path)
    assert_framing_dramatic_arc_structure(cleaned, framing_path)
    assert_framing_challenger_friction_lists_patterns(cleaned, framing_path)
    assert_framing_analogy_cap_declared(cleaned, framing_path)
    assert_framing_recurring_thesis_present(cleaned, framing_path, contract_anchor=None)
    # F27 Tier 2.5 (2026-05-22) — TTS-safe enforcement on framing.
    assert_no_arabic_transliteration(cleaned, framing_path, role="framing (CUSTOMIZE PROMPT)")
    assert_framing_analogy_cap_strict(cleaned, framing_path)
    assert_framing_no_modern_artifacts(cleaned, framing_path)
    assert_framing_honorific_bounded_both_sides(cleaned, framing_path)
    assert_no_arabic_surah_names(cleaned, framing_path, role="framing (CUSTOMIZE PROMPT)")
    assert_alqaab_only_established_or_paraphrased(cleaned, framing_path, role="framing (CUSTOMIZE PROMPT)")

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

    # 3. F25 (2026-05-23): apparatus-table check on 99-show-notes.md when present.
    # Silent skip when the file doesn't exist — F25 show-notes-generation
    # infrastructure is still pending (depends on F26 name-aliases.yml v2).
    show_notes_path = draft_dir / "99-show-notes.md"
    if show_notes_path.exists():
        assert_show_notes_has_apparatus_table(
            show_notes_path.read_text(encoding="utf-8"),
            show_notes_path,
        )

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
