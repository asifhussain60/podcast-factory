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

import sys
from pathlib import Path

# Re-export everything from _validators so existing callers that do
#   `from build_episode_txt import X`
# continue to work without modification.
from _validators import *  # noqa: F401, F403
from _validators import (
    CHAPTER_WORD_MIN_HARD, CHAPTER_WORD_MAX_HARD,
    CHAPTER_WORD_MIN_SOFT, CHAPTER_WORD_MAX_SOFT,
    CHAPTER_DEAD_ZONE_MIN, CHAPTER_DEAD_ZONE_MAX,
    FRAMING_WORD_MIN, FRAMING_WORD_MAX,
    EP_PATTERN,
    assert_chapters_populated, find_chapter_by_slug,
    load_book_meta_prose_tells,
    assert_no_html_comments, assert_no_meta_prose,
    assert_no_inline_phonetics, assert_no_abbreviations,
    assert_honorifics_once_only, assert_doctrinal_clean,
    assert_chapter_no_manuscript_meta,
    assert_no_arabic_transliteration, assert_no_arabic_surah_names,
    assert_alqaab_only_established_or_paraphrased,
    assert_framing_pronunciation_imperative, assert_framing_deny_block,
    assert_framing_has_name_discipline_section,
    assert_framing_dramatic_arc_structure,
    assert_framing_challenger_friction_lists_patterns,
    assert_framing_analogy_cap_declared,
    assert_framing_recurring_thesis_present,
    assert_framing_analogy_cap_strict,
    assert_framing_no_modern_artifacts,
    assert_framing_honorific_bounded_both_sides,
    assert_show_notes_has_apparatus_table,
    strip_upload_checklist, strip_html_comments, word_count,
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
            f"See infra/claude-agents/podcast-challenger.md (Categories C, D, E for word-count + structure) §3."
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
            f"See infra/claude-agents/podcast-challenger.md (Categories C, D, E for word-count + structure) §5."
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
