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
    - Word count in [500, 5500] hard band (notebooklm-best-practices.md §3).
  - **Framing file (the CUSTOMIZE PROMPT):**
    - Strip trailing "Upload checklist" section (it's the user's how-to, not the prompt).
    - Strip HTML comments.
    - Re-check META_PROSE_TELLS on the framing too — leaks through here are equally bad,
      since the framing is pasted into NotebookLM's Customize box.
    - Word count in [200, 2000] soft target; warn at extremes.

Usage:
  python3 build_episode_txt.py <BOOK_DIR> <EP##-slug>

Example:
  python3 scripts/podcast/build_episode_txt.py \\
    content/podcast/ayyuhal-walad \\
    EP01-frame-and-first-counsel
"""

import re
import sys
from pathlib import Path

# Chapter (SOURCE) word-count bounds — per notebooklm-best-practices.md §3
CHAPTER_WORD_MIN_HARD = 500
CHAPTER_WORD_MAX_HARD = 5500
CHAPTER_WORD_MIN_SOFT = 1500
CHAPTER_WORD_MAX_SOFT = 4500

# Framing (CUSTOMIZE PROMPT) word-count bounds — per notebooklm-best-practices.md §5
FRAMING_WORD_MIN = 150
FRAMING_WORD_MAX = 2000

EP_PATTERN = re.compile(r"^EP(\d+)-(.+)$")
CH_PATTERN = re.compile(r"^ch(\d+)-(.+)\.txt$")

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
    "per content/podcast/_handbook",
    "nothing has been added that is not in the source",
    "anything ghazali only implies",
    "anything the author only implies",
    "preserved in blockquotes with the original transliteration",
    "ghazali's prose has been clarified",
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


def assert_no_meta_prose(content: str, file_path: Path, role: str) -> None:
    """Refuse to build if content contains meta-prose tells.

    `role` is 'chapter (SOURCE)' or 'framing (CUSTOMIZE PROMPT)' for the error message.
    """
    lower = content.lower()
    substring_hits = [tell for tell in META_PROSE_TELLS if tell in lower]
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


def validate_chapter(chapter_path: Path) -> int:
    """Validate the chapter file. Returns word count. Exits on any error."""
    text = chapter_path.read_text(encoding="utf-8")
    assert_no_html_comments(text, chapter_path, "chapter (SOURCE)")
    assert_no_meta_prose(text, chapter_path, "chapter (SOURCE)")
    n = word_count(text)
    if n < CHAPTER_WORD_MIN_HARD or n > CHAPTER_WORD_MAX_HARD:
        sys.exit(
            f"ERROR: chapter {chapter_path.name} is {n} words. "
            f"Hard band is {CHAPTER_WORD_MIN_HARD}-{CHAPTER_WORD_MAX_HARD}. "
            f"See content/podcast/_handbook/notebooklm-best-practices.md §3."
        )
    return n


def build_framing_episode_txt(framing_path: Path, out_path: Path) -> int:
    """Read the framing, strip upload-checklist + HTML comments, validate, write to
    out_path as the customize-prompt-only episode txt. Returns word count of the
    final framing content."""
    raw = framing_path.read_text(encoding="utf-8")
    no_checklist = strip_upload_checklist(raw)
    cleaned = strip_html_comments(no_checklist).strip()

    # Re-validate cleaned framing for meta-prose tells (cross-episode refs, etc.).
    assert_no_meta_prose(cleaned, framing_path, "framing (CUSTOMIZE PROMPT)")

    n = word_count(cleaned)
    if n < FRAMING_WORD_MIN or n > FRAMING_WORD_MAX:
        sys.exit(
            f"ERROR: framing {framing_path.name} produces a customize prompt of {n} "
            f"words. Target band is {FRAMING_WORD_MIN}-{FRAMING_WORD_MAX}. "
            f"See content/podcast/_handbook/notebooklm-best-practices.md §5."
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

    # 1. Validate the chapter (uploaded as-is to NotebookLM as the SOURCE).
    assert_chapters_populated(book_dir)
    chapter_file = find_chapter_by_slug(book_dir / "chapters", episode_slug)
    chapter_words = validate_chapter(chapter_file)

    # 2. Build the customize-prompt-only episode txt.
    out_path = book_dir / "episodes" / f"{episode_id}.txt"
    framing_words = build_framing_episode_txt(framing_file, out_path)

    # Word-count warnings (band-soft, not hard).
    warnings = []
    if chapter_words < CHAPTER_WORD_MIN_SOFT:
        warnings.append(
            f"chapter is {chapter_words} words — under the {CHAPTER_WORD_MIN_SOFT}-word "
            f"Default Deep Dive floor. NotebookLM hosts may resort to filler."
        )
    if chapter_words > CHAPTER_WORD_MAX_SOFT:
        warnings.append(
            f"chapter is {chapter_words} words — over the {CHAPTER_WORD_MAX_SOFT}-word "
            f"Longer Deep Dive ceiling. Conversation may lose thread."
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
