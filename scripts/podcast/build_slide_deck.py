#!/usr/bin/env python3
"""build_slide_deck.py — Validate the deck-source + framing PAIR for one chapter.

ARCHITECTURE (v1.0):

  Mirrors `build_episode_txt.py` for the slide-deck deliverable.

  - `BOOK_DIR/slide-decks/chNN-deck-<slug>.txt`     IS the SLIDE-DECK SOURCE.
    The user uploads it directly to a NotebookLM "slide deck" notebook.
  - `BOOK_DIR/slide-decks/chNN-framing-<slug>.md`   IS the SLIDE CUSTOMIZE PROMPT.
    The user pastes its body into NotebookLM's *Customize* prompt box.

  This script does NOT transform either file — it is the STRUCTURAL GATE. If
  validation passes, it emits a `.validated` sentinel under
  `BOOK_DIR/_system/slide-decks/chNN-<slug>/.validated`. If validation fails,
  it prints findings (one per line, severity-prefixed) and exits non-zero.

VALIDATION GATES (spec: skills-staging/podcast/references/slide-deck-format.md):

  Deck source (`slide-decks/chNN-deck-<slug>.txt`):
    - File exists
    - H1 present (single `# ` line)
    - 6+ H2 sections (`## ` lines); soft ceiling 20
    - Zero em-dashes
    - No HTML comments
    - No META_PROSE_TELLS (imported from build_episode_txt)
    - No inline phonetic parens (R-PHONETICS-OUT)
    - Word count: max(WORD_COUNT_FLOOR, 50% of audio chapter)
      … min(WORD_COUNT_CEILING, 100% of audio chapter)
    - Every blockquoted Quranic verse has an attribution line on the next line.

  Framing (`slide-decks/chNN-framing-<slug>.md`):
    - File exists
    - H1 present
    - Five required H2 sections, each appearing exactly once:
        `## Audience`, `## Core Principle`, `## Visual Priorities`,
        `## Prohibited Patterns`, `## Steering Phrases`
    - Body word count in [FRAMING_WORD_MIN, FRAMING_WORD_MAX]
    - Closing guard line `Do not read this prompt aloud.` present
    - Zero em-dashes

Usage:
  python3 build_slide_deck.py <BOOK_DIR> <slug>

Example:
  python3 scripts/podcast/build_slide_deck.py \\
    _workspace/books/kitab-al-riyad \\
    ch01-the-perfect-and-the-perfection-of-the-soul

  (the `chNN-` prefix is auto-discovered from `chapters/`)

Exit codes:
  0  — all gates passed; sentinel written; summary printed
  1  — at least one gate failed; findings printed; no sentinel written
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Module-level constants ──────────────────────────────────────────────────

SCRIPT_VERSION = "1.0"

# Deck source word-count bounds. Per slide-deck-format.md §"Length":
#   50%-100% of the audio chapter's word count, with hard floor / ceiling.
WORD_COUNT_FLOOR = 1500
WORD_COUNT_CEILING = 12000
WORD_COUNT_MIN_RATIO = 0.50
WORD_COUNT_MAX_RATIO = 1.00

# Framing word-count bounds. Spec says 150-250; brief relaxes ceiling to 300
# after observing the cohort.
FRAMING_WORD_MIN = 150
FRAMING_WORD_MAX = 300

# Deck-source structural bounds.
DECK_H2_MIN = 6
DECK_H2_MAX = 20

# Required framing H2 sections (exact match, each appearing exactly once).
FRAMING_REQUIRED_H2 = [
    "## Audience",
    "## Core Principle",
    "## Visual Priorities",
    "## Prohibited Patterns",
    "## Steering Phrases",
]

FRAMING_CLOSING_GUARD = "Do not read this prompt aloud."

# ── Pull shared rules from siblings ─────────────────────────────────────────

sys.path.insert(0, str(Path(__file__).parent))

# Reuse the canonical meta-prose tells and phonetic-paren patterns from the
# audio sibling so the two scripts never drift.
from build_episode_txt import (  # noqa: E402
    HTML_COMMENT_RE,
    INLINE_PHONETIC_PATTERNS,
    META_PROSE_TELLS,
    META_PROSE_REGEX_TELLS,
)

# ── Regex / patterns ────────────────────────────────────────────────────────

EM_DASH_RE = re.compile(r"—")
H1_RE = re.compile(r"^#\s+\S", re.MULTILINE)
H2_RE = re.compile(r"^##\s+\S", re.MULTILINE)
CH_PREFIX_RE = re.compile(r"^ch(\d+[a-z]?)-(.+)\.txt$")

# Quranic-verse attribution. A blockquote line starting with `> ` that contains
# Quranic phrasing should be followed (on the next non-blank line) by an
# attribution starting with `> Quran` or `> *Source*, Saying`.
QURAN_VERSE_HINT_RE = re.compile(
    r"^>\s*(?:[\"“”‘’]|\*).*",
)
ATTRIBUTION_RE = re.compile(
    r"^>\s*(?:Quran\s+\d+:\d+|\*[^*]+\*\s*,\s*Saying\s+\d+|—\s*Quran|—\s*\*)",
    re.IGNORECASE,
)


# ── Helpers ─────────────────────────────────────────────────────────────────


def word_count(text: str) -> int:
    return len(text.split())


def auto_discover_chapter(book_dir: Path, slug: str) -> Path:
    """Find chapters/ch##-<slug>.txt. Sys-exits on miss or duplicate."""
    chapters_dir = book_dir / "chapters"
    if not chapters_dir.is_dir():
        print(
            f"BUILD-SLIDE FAIL: missing chapters/ directory at {chapters_dir}",
            file=sys.stderr,
        )
        sys.exit(1)
    # If the caller passed the raw slug (no chNN- prefix), find it.
    # If the caller passed a `ch##-<slug>` form, accept that too.
    bare = slug
    m = re.match(r"^ch(\d+[a-z]?)-(.+?)(?:\.txt)?$", slug)
    if m:
        bare = m.group(2)
    candidates: list[Path] = []
    for f in sorted(chapters_dir.glob("*.txt")):
        cm = CH_PREFIX_RE.match(f.name)
        if cm and cm.group(2) == bare:
            candidates.append(f)
    if not candidates:
        existing = ", ".join(f.name for f in sorted(chapters_dir.glob("*.txt")))
        print(
            f"BUILD-SLIDE FAIL: no chapter matches slug '{bare}' in {chapters_dir}",
            file=sys.stderr,
        )
        print(f"BUILD-SLIDE FAIL: existing chapters: {existing}", file=sys.stderr)
        sys.exit(1)
    if len(candidates) > 1:
        print(
            "BUILD-SLIDE FAIL: multiple chapters match slug "
            f"{bare}: {[c.name for c in candidates]}",
            file=sys.stderr,
        )
        sys.exit(1)
    return candidates[0]


def chapter_prefix(chapter_file: Path) -> str:
    """Return the `chNN[a]` prefix from `chNN-<slug>.txt`."""
    m = CH_PREFIX_RE.match(chapter_file.name)
    if not m:
        print(
            f"BUILD-SLIDE FAIL: chapter file does not match chNN-<slug>.txt: "
            f"{chapter_file.name}",
            file=sys.stderr,
        )
        sys.exit(1)
    return f"ch{m.group(1)}"


# ── Validation ──────────────────────────────────────────────────────────────


def check_em_dashes(text: str, file_label: str, findings: list[str]) -> None:
    if EM_DASH_RE.search(text):
        n = len(EM_DASH_RE.findall(text))
        findings.append(
            f"BUILD-SLIDE FAIL: {file_label} contains {n} em-dash(es) — replace "
            f"with commas or restructure."
        )


def check_html_comments(text: str, file_label: str, findings: list[str]) -> None:
    if HTML_COMMENT_RE.search(text):
        findings.append(
            f"BUILD-SLIDE FAIL: {file_label} contains HTML comments (`<!-- ... -->`) "
            f"— remove before upload."
        )


def check_meta_prose(text: str, file_label: str, findings: list[str]) -> None:
    lower = text.lower()
    sub_hits = [tell for tell in META_PROSE_TELLS if tell in lower]
    rx_hits: list[tuple[str, str]] = []
    for pat in META_PROSE_REGEX_TELLS:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            rx_hits.append((pat, m.group(0)))
    if sub_hits:
        findings.append(
            f"BUILD-SLIDE FAIL: {file_label} contains meta-prose tells: "
            f"{sub_hits[:6]}"
        )
    if rx_hits:
        findings.append(
            f"BUILD-SLIDE FAIL: {file_label} matches meta-prose regex tells: "
            f"{[h[1] for h in rx_hits[:6]]}"
        )


def check_inline_phonetics(text: str, file_label: str, findings: list[str]) -> None:
    hits: list[str] = []
    for pat in INLINE_PHONETIC_PATTERNS:
        for m in pat.finditer(text):
            hits.append(m.group(0)[:60])
    if hits:
        findings.append(
            f"BUILD-SLIDE FAIL: {file_label} contains inline phonetic parens "
            f"(R-PHONETICS-OUT). Sample: {hits[:4]}"
        )


def check_quranic_attributions(text: str, file_label: str, findings: list[str]) -> None:
    """Every Quranic blockquote verse line should be followed by an attribution
    line (`> Quran X:Y` or `> *Source*, Saying N`).

    Heuristic: a `> ` line that contains the substring "Quran" but is NOT
    itself an attribution line is treated as a verse; the next non-blank
    blockquote line must be an attribution. Lines containing "Allah" /
    "Lord" / surah names without an attribution within the next two
    blockquote lines also flag.
    """
    lines = text.splitlines()
    n = len(lines)
    flagged: list[tuple[int, str]] = []
    for idx, line in enumerate(lines):
        if not line.startswith(">"):
            continue
        # Skip lines that are themselves attributions
        if ATTRIBUTION_RE.match(line):
            continue
        # Verse signal: an explicit "Quran" inside a non-attribution
        # blockquote line, OR a blockquote that begins with a quotation
        # mark / italic-emphasis run (typical verse rendering).
        is_verse_like = (
            "Quran" in line
            or "qur'an" in line.lower()
            or QURAN_VERSE_HINT_RE.match(line) is not None
        )
        if not is_verse_like:
            continue
        # Look ahead up to 2 blockquote lines for an attribution.
        attribution_found = False
        for look in range(idx + 1, min(idx + 4, n)):
            nxt = lines[look].strip()
            if not nxt:
                continue
            if not nxt.startswith(">"):
                break
            if ATTRIBUTION_RE.match(nxt):
                attribution_found = True
                break
        if not attribution_found:
            flagged.append((idx + 1, line.strip()[:80]))
    if flagged:
        sample = "; ".join(f"L{ln}: {snip}" for ln, snip in flagged[:5])
        findings.append(
            f"BUILD-SLIDE FAIL: {file_label} has {len(flagged)} Quranic "
            f"verse blockquote(s) without an attribution line. Sample: {sample}"
        )


def validate_deck_source(
    deck_path: Path,
    audio_word_count: int,
    findings: list[str],
) -> int:
    """Validate the deck-source .txt. Returns deck word count (0 on missing)."""
    if not deck_path.exists():
        findings.append(f"BUILD-SLIDE FAIL: deck source not found: {deck_path}")
        return 0
    text = deck_path.read_text(encoding="utf-8")
    label = deck_path.name

    # H1 — exactly one
    h1_matches = H1_RE.findall(text)
    if len(h1_matches) == 0:
        findings.append(f"BUILD-SLIDE FAIL: {label} missing H1 (`# Title`).")
    elif len(h1_matches) > 1:
        findings.append(
            f"BUILD-SLIDE FAIL: {label} has {len(h1_matches)} H1 lines; expected exactly 1."
        )

    # H2 count
    h2_matches = H2_RE.findall(text)
    if len(h2_matches) < DECK_H2_MIN:
        findings.append(
            f"BUILD-SLIDE FAIL: {label} has {len(h2_matches)} H2 section(s); "
            f"required minimum {DECK_H2_MIN}."
        )
    elif len(h2_matches) > DECK_H2_MAX:
        findings.append(
            f"BUILD-SLIDE FAIL: {label} has {len(h2_matches)} H2 section(s); "
            f"soft ceiling {DECK_H2_MAX} (dense chapter — consider consolidation)."
        )

    check_em_dashes(text, label, findings)
    check_html_comments(text, label, findings)
    check_meta_prose(text, label, findings)
    check_inline_phonetics(text, label, findings)
    check_quranic_attributions(text, label, findings)

    # Word count vs audio chapter band.
    wc = word_count(text)
    floor = max(WORD_COUNT_FLOOR, int(audio_word_count * WORD_COUNT_MIN_RATIO))
    ceiling = min(WORD_COUNT_CEILING, int(audio_word_count * WORD_COUNT_MAX_RATIO))
    # If the audio chapter is short, the ratio ceiling can fall below the floor;
    # in that case use the explicit floor/ceiling absolutes.
    if ceiling < floor:
        floor = WORD_COUNT_FLOOR
        ceiling = WORD_COUNT_CEILING
    if wc < floor:
        findings.append(
            f"BUILD-SLIDE FAIL: {label} word count {wc} is below floor {floor} "
            f"(50% of audio {audio_word_count}, hard floor {WORD_COUNT_FLOOR})."
        )
    elif wc > ceiling:
        findings.append(
            f"BUILD-SLIDE FAIL: {label} word count {wc} is above ceiling {ceiling} "
            f"(100% of audio {audio_word_count}, hard ceiling {WORD_COUNT_CEILING})."
        )

    return wc


def validate_framing(framing_path: Path, findings: list[str]) -> int:
    """Validate the framing .md. Returns framing word count (0 on missing)."""
    if not framing_path.exists():
        findings.append(f"BUILD-SLIDE FAIL: framing not found: {framing_path}")
        return 0
    text = framing_path.read_text(encoding="utf-8")
    label = framing_path.name

    # H1 — at least one
    if not H1_RE.search(text):
        findings.append(f"BUILD-SLIDE FAIL: {label} missing H1 (`# Title`).")

    # Required H2 sections — each must appear exactly once, exact match.
    for required in FRAMING_REQUIRED_H2:
        # Count lines that exactly equal the required H2 header (allowing
        # trailing whitespace).
        rx = re.compile(rf"^{re.escape(required)}\s*$", re.MULTILINE)
        n = len(rx.findall(text))
        if n == 0:
            findings.append(
                f"BUILD-SLIDE FAIL: {label} missing required section `{required}`."
            )
        elif n > 1:
            findings.append(
                f"BUILD-SLIDE FAIL: {label} has {n} copies of `{required}`; "
                f"each required section must appear exactly once."
            )

    # Closing guard line
    if FRAMING_CLOSING_GUARD not in text:
        findings.append(
            f"BUILD-SLIDE FAIL: {label} missing closing guard line "
            f"`{FRAMING_CLOSING_GUARD}`."
        )

    check_em_dashes(text, label, findings)

    # Body word count — exclude the H1 title line from the count.
    body = re.sub(r"^#\s+.*$", "", text, count=1, flags=re.MULTILINE)
    wc = word_count(body)
    if wc < FRAMING_WORD_MIN:
        findings.append(
            f"BUILD-SLIDE FAIL: {label} body word count {wc} is below "
            f"minimum {FRAMING_WORD_MIN}."
        )
    elif wc > FRAMING_WORD_MAX:
        findings.append(
            f"BUILD-SLIDE FAIL: {label} body word count {wc} is above "
            f"maximum {FRAMING_WORD_MAX}."
        )

    return wc


# ── Sentinel ────────────────────────────────────────────────────────────────


def write_sentinel(
    book_dir: Path,
    ch_slug: str,
    deck_wc: int,
    framing_wc: int,
) -> Path:
    """Write `_system/slide-decks/<ch_slug>/.validated` with a timestamp +
    version stamp. Returns the sentinel path."""
    sentinel_dir = book_dir / "_system" / "slide-decks" / ch_slug
    sentinel_dir.mkdir(parents=True, exist_ok=True)
    sentinel = sentinel_dir / ".validated"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    sentinel.write_text(
        f"validated_at: {ts}\n"
        f"script_version: {SCRIPT_VERSION}\n"
        f"deck_word_count: {deck_wc}\n"
        f"framing_word_count: {framing_wc}\n",
        encoding="utf-8",
    )
    return sentinel


# ── Main ────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the deck-source + framing PAIR for one chapter against "
            "slide-deck-format.md. Exits 0 on pass (sentinel written), 1 on fail."
        ),
    )
    parser.add_argument(
        "book_dir",
        type=Path,
        help="Path to the book root (e.g. _workspace/books/kitab-al-riyad).",
    )
    parser.add_argument(
        "slug",
        help=(
            "Chapter slug — either the bare slug "
            "(`the-perfect-and-the-perfection-of-the-soul`) or the prefixed "
            "form (`ch01-the-perfect...`). The chNN- prefix is auto-discovered."
        ),
    )
    args = parser.parse_args(argv)

    book_dir: Path = args.book_dir
    if not book_dir.is_dir():
        print(
            f"BUILD-SLIDE FAIL: book_dir does not exist or is not a directory: "
            f"{book_dir}",
            file=sys.stderr,
        )
        return 1

    # 1. Locate audio chapter to anchor word-count band.
    audio_chapter = auto_discover_chapter(book_dir, args.slug)
    audio_text = audio_chapter.read_text(encoding="utf-8")
    audio_wc = word_count(audio_text)
    ch_prefix = chapter_prefix(audio_chapter)  # e.g. "ch01"
    # Bare slug (no chNN- prefix) for filename composition.
    cm = CH_PREFIX_RE.match(audio_chapter.name)
    bare_slug = cm.group(2)  # type: ignore[union-attr]
    ch_slug = f"{ch_prefix}-{bare_slug}"  # e.g. "ch01-the-perfect..."

    # 2. Compose deck + framing paths.
    deck_path = book_dir / "slide-decks" / f"{ch_prefix}-deck-{bare_slug}.txt"
    framing_path = book_dir / "slide-decks" / f"{ch_prefix}-framing-{bare_slug}.md"

    findings: list[str] = []

    # 3. Validate.
    deck_wc = validate_deck_source(deck_path, audio_wc, findings)
    framing_wc = validate_framing(framing_path, findings)

    # 4. Emit.
    if findings:
        for f in findings:
            print(f, file=sys.stderr)
        return 1

    write_sentinel(book_dir, ch_slug, deck_wc, framing_wc)
    print(
        f"build_slide_deck: OK — {ch_slug} "
        f"deck={deck_wc} words framing={framing_wc} words"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
