#!/usr/bin/env python3
"""restructure_episode_prompt.py — front-load HARD CONSTRAINTS block into episode prompts.

PURPOSE

  NotebookLM's Audio Overview engine reads the customise prompt as the
  director's brief but treats negative rules buried mid-prompt as weak
  suggestions. The original recipe template had `## Pronunciation`,
  `## Explicitly forbidden analogies`, `## R-NOMODERNIZE`, and `## Do not`
  scattered between lines 11 and 170 of each episode prompt; observed
  behavior in EP14 first run: every one of those sections was partially or
  fully ignored.

  This script transforms each episode prompt by:
    1. Injecting a `## HARD CONSTRAINTS — DO NOT VIOLATE` block as Section 1
       right after the title, with five sub-blocks: forbidden analogies,
       forbidden phrases, required spellings, Quranic citation substitution,
       anti-padding.
    2. Removing the now-redundant `## Pronunciation`, `## Explicitly forbidden
       analogies`, `## R-NOMODERNIZE`, `## Do not` sections.
    3. Applying the same diacritic-strip + Arabic-term substitution rules
       used by `sanitize_chapter_for_tts.py` (via shared `_tts_sanitize`).
    4. Preserving all per-episode content (Background, Stable role-labels,
       Host dynamic, Conversation choreography, Central tensions, Three-part
       focus, Tone constraints, Anti-noise rules, Landing).

USAGE

  python3 scripts/podcast/restructure_episode_prompt.py library/books/kitab-al-riyad/episodes/EP01-the-perfect-and-the-perfection-of-the-soul.txt
  python3 scripts/podcast/restructure_episode_prompt.py library/books/kitab-al-riyad/episodes/
  python3 scripts/podcast/restructure_episode_prompt.py --dry-run library/books/kitab-al-riyad/episodes/

IDEMPOTENCY

  Detects if `## HARD CONSTRAINTS` is already the second-line H2 and skips
  re-injection. Sanitization passes remain idempotent per `_tts_sanitize`.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from _tts_sanitize import sanitize_text  # noqa: E402


# ---------------------------------------------------------------------------
# The HARD CONSTRAINTS block — universal across all KaR episodes. Tailored
# per-book by updating SURAH_TABLE if the book cites surahs not listed.
# ---------------------------------------------------------------------------
HARD_CONSTRAINTS = """## HARD CONSTRAINTS — DO NOT VIOLATE

These rules override every other instinct the audio engine has. If any of them are violated the episode is unusable and must be regenerated. Read this section first and hold it in mind throughout the entire conversation.

### 1. Forbidden analogies — never use, never mention, do not pivot through
Do not, under any circumstances, frame any part of this conversation through any of the following images, whether as opening hook, closing bookend, throwaway aside, or extended metaphor:
- cathedral, church, temple, mosque, building under construction, masonry, spires, vaulted ceilings, architects designing structures
- solar panels, solar arrays, calculators powered by light, photovoltaic anything
- sealed rooms, mail carrier, postal service, courier
- TV, streaming services, signal-receiver, antenna, channel-changing, broken radio, Wi-Fi
- teacup, battery, signet-ring, wax seal, cosplay, campfire, waterfall, Frankenstein
- sun-and-plates as a positive framing (when the source quotes this as the earlier scholar's image used against itself, hosts reference it AS the image the author refuses, never as their own current framing)
- pie charts, percentages, recipes as proportion analogies
- light bulbs casting shadows, light hitting glass versus stone

If you find yourself reaching for any analogy involving a constructed building, a solar device, or a transmission medium, stop and use one of the source's own images instead.

### 2. Forbidden phrases — never say these words
The hosts never say:
- "wow", "oh wow", "oh my", "oh boy", "no way", "right?", "exactly", "of course", "of course not", "absolutely", "totally", "that's so interesting", "chilling", "devastating", "phenomenal", "incredible", "breathtaking", "fascinating", "brilliant", "genius", "amazing", "great way to put it", "great question"
- conversational softeners and fillers: "you know", "I mean", "like,", "kind of", "sort of", "basically", "literally" (when used as filler)
- formal-essay transitions: "Firstly", "Secondly", "Thirdly", "Furthermore", "In conclusion", "To summarize", "Moving on to", "Lastly", "It's worth noting that"
- modernization markers: "Twitter", "X", "social media", "algorithm", "YouTube", "TikTok", "Instagram", "in today's world", "going viral", "the internet age"
- the words "deep dive" anywhere — do not refer to this conversation as a deep dive, a podcast, an episode, or a show. Refer to it only as "this discussion" or by no name at all.
- the phrase "welcome to" anything, or any podcast-style opening greeting
- the phrase "as we close out" or any podcast-style closing flourish

The hosts speak as measured, sober journalists having a careful exchange. Not enthusiastic students, not breathless explainers.

### 3. Concept terminology — speak the English form as written
The source text uses English translations for all Arabic philosophical concepts. Speak each concept exactly as it appears in the source. The standard translations:
- "Divine Oneness" — for the doctrine of God's absolute unity
- "associating partners with God" — for the cardinal theological error
- "origination" — for the creative act
- "the mission" — for the religious mission
- "sacred law" — for the prescribed law
- "inner interpretation" — for the esoteric reading
- "the apparent" and "the hidden" — for the two registers of religion
- "the Supplication of Arafa" — for Imam Hussain's prayer

Do not introduce Arabic technical terms that do not appear in the source. The audio should sound like a careful English-language discussion of these doctrines.

### 4. Proper-name pronunciations — say these exactly as the source spells them
Names of people, places, and texts retain their Arabic forms. The TTS will pronounce these natural English orthographies correctly:
- al-Mubdi (the Originator)
- huwa (when discussed AS a word — "the pronoun huwa")
- Hussain (the second Imam)
- Ali (the Commander of the Faithful)
- Imran ibn Husayn (the companion-narrator)
- Maad ibn Ismail (the Fatimid caliph)
- Karbala
- Arafat (the plain)
- Quran
- Sahih al-Bukhari

If any Arabic technical term appears in the source that is not in this list, paraphrase it in English rather than attempting to pronounce it.

### 5. Quranic citation substitution — never speak the surah number alone, never speak the Arabic surah name
Replace every Quranic reference with its English chapter name. Common citations:
- Quran 3 → "the chapter of the family of Imran"
- Quran 5 → "the chapter of the table spread"
- Quran 6 → "the chapter of cattle"
- Quran 7 → "the chapter of the heights"
- Quran 13 → "the chapter of thunder"
- Quran 15 → "the chapter of the rocky tract"
- Quran 16 → "the chapter of the bee"
- Quran 17 → "the chapter of the night journey"
- Quran 18 → "the chapter of the cave"
- Quran 33 → "the chapter of the confederates"
- Quran 36 → "the chapter of Ya-Seen"
- Quran 41 → "the chapter explained in detail"
- Quran 42 → "the chapter of consultation"
- Quran 50 → "the chapter of Qaaf"
- Quran 53 → "the chapter of the star"
- Quran 54 → "the chapter of the moon"
- Quran 57 → "the chapter of iron"
- Quran 70 → "the chapter of the ascending stairways"
- Quran 89 → "the chapter of the dawn"
- Quran 91 → "the chapter of the sun"
- Quran 112 → "the chapter of sincerity"

Do not say "Surah", "Sura", "Surat", or any Arabic chapter name (al-Ikhlas, al-Hadid, al-Shura, etc.) — only the English meaning. The source text has been pre-substituted with these English names; speak them as written.

### 6. Anti-padding and structural rules
- The first three sentences are pure substance. No "imagine for a second" opening hooks, no architectural metaphors, no scene-setting flourishes. The opening drops directly into the chapter's content.
- The last sentence ends on the doctrinal verdict, not on a "what does this mean for the listener" reflection or a metaphor flourish.
- When the recipe specifies a thesis to be restated verbatim N times (see Anti-noise rules below), speak the thesis as a standalone sentence with natural conversational pacing, no paraphrase at the restatement points. Do not narrate stage directions like "short pause here" or "let me quote it directly" — those are guidance to you, never spoken content.
- If you find yourself padding to fill time, end the episode early. A shorter, cleaner episode is preferable to a longer one that wanders.

---

"""


# Sections to remove — they're now consolidated into HARD CONSTRAINTS. Regex
# captures the H2 header and everything until the next H2.
_SECTIONS_TO_REMOVE = {
    "## Pronunciation",
    "## Explicitly forbidden analogies",
    "## R-NOMODERNIZE",
    "## Do not",
}


def _remove_section(text: str, header: str) -> tuple[str, bool]:
    """Remove a `## Header` section and everything until the next `## ` or end.
    Returns (new_text, was_removed)."""
    # Escape the header for regex; match from header to (next H2 | end of file).
    pattern = re.compile(
        rf"^{re.escape(header)}\b.*?(?=^## |\Z)",
        re.DOTALL | re.MULTILINE,
    )
    new_text, n = pattern.subn("", text)
    return new_text, n > 0


def _inject_hard_constraints(text: str, force: bool = False) -> tuple[str, bool]:
    """Insert HARD CONSTRAINTS block right after the first H1 title.
    Returns (new_text, was_injected). With force=True, strips any existing
    HARD CONSTRAINTS block (between the H2 header and the next H2) and
    re-injects the current template — for updating the block in-place
    after a template edit."""
    if "## HARD CONSTRAINTS" in text:
        if not force:
            return text, False  # already present, idempotent
        # Strip the existing block before re-injecting
        text = re.sub(
            r"## HARD CONSTRAINTS.*?(?=^## [A-Z]|\Z)",
            "",
            text,
            count=1,
            flags=re.DOTALL | re.MULTILINE,
        )

    # Find first H1 line, then insert after the blank line following it
    lines = text.split("\n")
    insert_idx = None
    for i, line in enumerate(lines):
        if line.startswith("# ") and not line.startswith("## "):
            # Title found; find next non-blank skip if there's an Opening directive
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            insert_idx = j
            break
    if insert_idx is None:
        # No H1 — prepend to file
        return HARD_CONSTRAINTS + text, True

    new_lines = lines[:insert_idx] + HARD_CONSTRAINTS.split("\n") + lines[insert_idx:]
    return "\n".join(new_lines), True


def _strip_opening_directive(text: str) -> tuple[str, bool]:
    """The original `## Opening directive` block is a short prose paragraph
    that overlapped with what HARD CONSTRAINTS now governs. Remove it cleanly."""
    return _remove_section(text, "## Opening directive")


def _strip_tone_constraints_forbidden_subsection(text: str) -> tuple[str, int]:
    """Some episodes have a `### C4 retained Arabic` sub-block under `## Tone
    constraints` that listed Arabic terms — now covered by the Required
    Spellings table. Drop it.

    Also strip stray `**Retained Arabic technicals (C4).**` callouts inside
    prose paragraphs of Tone constraints."""
    n = 0
    # Remove ### C4 retained Arabic block
    pattern = re.compile(
        r"^### C4 retained Arabic.*?(?=^### |^## |\Z)",
        re.DOTALL | re.MULTILINE,
    )
    text, count = pattern.subn("", text)
    n += count
    # Strip inline retained-Arabic callouts
    pattern = re.compile(
        r"\*\*Retained Arabic technicals \(C4\)\.\*\*[^\n]*\n",
        re.MULTILINE,
    )
    text, count = pattern.subn("", text)
    n += count
    return text, n


def process_file(path: Path, dry_run: bool, force: bool = False) -> int:
    """Restructure one episode prompt. Returns number of structural changes.

    Order of operations is critical: sanitize the per-episode content BEFORE
    injecting HARD_CONSTRAINTS. Otherwise the sanitize pass corrupts the
    template's example references (e.g., "Divine Oneness (not Tawhid)" gets
    self-substituted to "Divine Oneness (not Divine Oneness)").
    """
    original = path.read_text(encoding="utf-8")
    text = original
    structural_changes = 0
    notes: list[str] = []

    # 1. First, strip any existing HARD CONSTRAINTS block (so sanitize doesn't
    #    touch the old one) — only when force=True; otherwise leave alone.
    if force and "## HARD CONSTRAINTS" in text:
        text = re.sub(
            r"## HARD CONSTRAINTS.*?(?=^## [A-Z]|\Z)",
            "",
            text,
            count=1,
            flags=re.DOTALL | re.MULTILINE,
        )

    # 2. Remove now-redundant sections from per-episode content
    for header in _SECTIONS_TO_REMOVE:
        text, removed = _remove_section(text, header)
        if removed:
            structural_changes += 1
            notes.append(f"removed '{header}' section")

    # 3. Strip Opening directive (overlapped with HARD CONSTRAINTS Section 6)
    text, removed = _strip_opening_directive(text)
    if removed:
        structural_changes += 1
        notes.append("removed '## Opening directive' section")

    # 4. Strip C4 retained-Arabic blocks (now in Required Spellings)
    text, n = _strip_tone_constraints_forbidden_subsection(text)
    if n:
        structural_changes += n
        notes.append(f"removed {n} retained-Arabic C4 block(s)")

    # 5. Apply sanitize pass to per-episode content (diacritics, Arabic-term
    #    translations, Quranic citations). Runs on the body content BEFORE
    #    the HARD CONSTRAINTS template is injected — protects the template.
    text, sanitize_report = sanitize_text(text)

    # 6. NOW inject the fresh HARD CONSTRAINTS template (unsanitized — it
    #    is the canonical instruction and must keep its example references
    #    like 'not "Tawhid"' intact).
    text, injected = _inject_hard_constraints(text, force=False)
    if injected:
        structural_changes += 1
        notes.append("injected HARD CONSTRAINTS block (post-sanitize)")
    else:
        notes.append("HARD CONSTRAINTS already present (skipped)")

    # 6. Collapse 3+ consecutive blank lines to 2 (cleanup after section removal)
    text = re.sub(r"\n{4,}", "\n\n\n", text)

    print(f"\n{path}")
    for note in notes:
        print(f"  {note}")
    print(sanitize_report.summary())

    if not dry_run and text != original:
        path.write_text(text, encoding="utf-8")
        print(f"  → wrote {len(text):,} bytes")
    elif dry_run and text != original:
        print(f"  → would write {len(text):,} bytes (dry-run)")

    return structural_changes + sanitize_report.total_changes


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="restructure_episode_prompt.py",
        description="Front-load HARD CONSTRAINTS block + sanitize an episode customise prompt.",
    )
    parser.add_argument("path", help="Episode prompt file or directory of episode .txt files")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report changes without modifying files")
    parser.add_argument("--force", action="store_true",
                        help="Strip any existing HARD CONSTRAINTS block and re-inject the current template (use after editing the template)")
    args = parser.parse_args(argv)

    target = Path(args.path).resolve()
    if not target.exists():
        print(f"ERROR: path not found: {target}", file=sys.stderr)
        return 1

    if target.is_file():
        files = [target]
    else:
        files = sorted(p for p in target.glob("EP*.txt") if p.is_file())
        if not files:
            print(f"ERROR: no EP*.txt files found in {target}", file=sys.stderr)
            return 1

    total = 0
    for f in files:
        total += process_file(f, args.dry_run, force=args.force)

    print(f"\n{'='*60}")
    print(f"Total: {len(files)} file(s), {total} change(s){' (dry-run)' if args.dry_run else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
