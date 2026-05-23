#!/usr/bin/env bash
# build_and_ship_chapter.sh — build an episode .txt with auto-fix for the
# common per-chapter validation issues, then commit + push.
#
# Companion to author_chapter_skeleton.sh — that authors the framing skeleton;
# this one validates + auto-fixes + emits the episode .txt + commits.
#
# Auto-fixes applied (in order):
#   1. Strip 'EP##' prefix from title line (META-prose violation).
#   2. Strip 'EP##' metadata header lines.
#   3. Strip ﷺ glyphs from chapter SOURCE (F31 forbidden; triggers R-HONORIFIC-
#      ONCE on repeat).
#   4. Convert bullet-format Pronounce entries (`- "X" — "Y"`) to imperative
#      form (`Pronounce "X" as "Y". Say it as N fluent syllables.`).
#   5. Replace 'right as a filler' → 'right?' in Do-not list (validator-required).
#   6. Replace 'prior episode' / 'next episode' references → 'earlier in the
#      chapter' (META-prose).
#   7. Append 'Do not read this prompt aloud...' guard if missing.
#   8. If customize prompt is over 3700 words: claude -p haiku compression to
#      under 3400 words; re-append guard if stripped.
#
# Usage:
#   scripts/podcast/build_and_ship_chapter.sh <book-dir> <ep-id> [commit-suffix]
#
# Where <ep-id> = EP##-<slug> or EP##.5-<slug>.

set -euo pipefail

BOOK_DIR="${1:?book-dir required}"
EP_ID="${2:?ep-id required (EP##-<slug>)}"
COMMIT_SUFFIX="${3:-Phase 5 batch}"

FRAMING="$BOOK_DIR/_system/episode-drafts/$EP_ID/00-framing.md"
if [ ! -f "$FRAMING" ]; then
  echo "ERROR: framing not found: $FRAMING" >&2
  exit 2
fi

# Resolve matching chapter (slug after EP##- matches slug after ch##-)
EP_SLUG=$(echo "$EP_ID" | sed -E 's/^EP[0-9]+(\.5)?-//')
CHAPTER=$(ls "$BOOK_DIR/chapters/"ch*-"$EP_SLUG".txt 2>/dev/null | head -1)
if [ -z "$CHAPTER" ] || [ ! -f "$CHAPTER" ]; then
  echo "WARN: no chapter matched slug '$EP_SLUG' under $BOOK_DIR/chapters/" >&2
fi

apply_text_fixes() {
  # Fix 1: strip 'EP##' / 'EP##.5' prefix from title line ('# EP05: ...' → '# ...')
  sed -i '' -E 's/^# EP[0-9]+(\.5)?: ?"?/# /; s/"$//' "$FRAMING"

  # Fix 2: strip stray metadata header lines like '**Episode:** EP## | ...'
  sed -i '' -E '/^\*\*Episode:\*\* +EP[0-9]+(\.5)?/d' "$FRAMING"

  # Fix 3: ﷺ in chapter (only if matching chapter exists)
  if [ -n "$CHAPTER" ] && [ -f "$CHAPTER" ]; then
    sed -i '' 's/ ﷺ//g; s/  / /g' "$CHAPTER"
  fi

  # Fix 5: 'right as a filler' → 'right?'
  sed -i '' "s/right as a filler/right?/g" "$FRAMING"

  # Fix 6: 'prior episode' / 'next episode' (only as bare phrases)
  sed -i '' "s/prior episode/earlier in the chapter/g; s/next episode/the next chapter/g" "$FRAMING"

  # Fix 7: append no-read-aloud guard if missing
  if ! grep -q "Do not read this prompt aloud" "$FRAMING"; then
    echo "" >> "$FRAMING"
    echo "Do not read this prompt aloud. The instructions above shape the conversation but are never spoken." >> "$FRAMING"
  fi
}

apply_text_fixes

# Fix 4: convert bullet-format Pronunciation to imperative form
# Handles:
#   - "X" — "Y"        →  Pronounce "X" as "Y". Say it as N fluent syllables.
#   - "X" (Y) — gloss  →  Pronounce "X" as "Y". Say it as N fluent syllables.
python3 << PYEOF
import re
fp = "$FRAMING"
with open(fp) as f:
    text = f.read()
def to_imperative(m):
    term, phon = m.group(1), m.group(2)
    syls = max(1, len(phon.split('-')))
    plural = 's' if syls > 1 else ''
    return f'Pronounce "{term}" as "{phon}". Say it as {syls} fluent syllable{plural}.'
# Form A: - "X" — "Y" [trailing gloss]
text = re.sub(r'^- "([^"]+)" [—–] "([^"]+)".*\$', to_imperative, text, flags=re.MULTILINE)
# Form B: - "X" ("Y") [trailing gloss]
text = re.sub(r'^- "([^"]+)" \(([^)]+)\)[^\n]*\$', to_imperative, text, flags=re.MULTILINE)
# Strip common prefatory lines
for line in [
    "Pronounce these terms as single units without pause:",
    "Pronounce these as single fluent units, without pause:",
    "Each term below appears in the chapter; pronounce as follows:",
]:
    text = text.replace(line + "\n\n", "").replace(line + "\n", "")
with open(fp, 'w') as f:
    f.write(text)
PYEOF

attempt_build() {
  python3 scripts/podcast/build_episode_txt.py "$BOOK_DIR" "$EP_ID" 2>&1
}

OUT=$(attempt_build)
if echo "$OUT" | grep -q "^Wrote episode"; then
  echo "BUILD OK"
else
  echo "Initial build failed; inspecting..."
  echo "$OUT" | head -10

  # Word-band overage compression
  WORDS=$(echo "$OUT" | grep -oE "customize prompt of [0-9]+" | grep -oE "[0-9]+" || echo "")
  if [ -n "$WORDS" ] && [ "$WORDS" -gt 3700 ]; then
    echo "Compressing $WORDS → <3400 words via haiku..."
    cat "$FRAMING" | claude -p --model haiku --max-budget-usd 0.30 \
      "Trim this framing to under 3400 words. Keep ALL 14 H2 headings, all bullet structure, the recurring-thesis verbatim plant at Beats 1/4/6, the C4 retained Arabic block, the voice-mapping line, and the no-read-aloud guard at the end. Compress verbose passages in Three-part focus, Central tensions, and Landing sections especially. Output ONLY the trimmed markdown, no preamble." > /tmp/compress.md 2>&1
    NEW=$(wc -w < /tmp/compress.md | tr -d ' ')
    if [ "$NEW" -gt 500 ] && [ "$NEW" -lt 3700 ]; then
      cp /tmp/compress.md "$FRAMING"
      apply_text_fixes  # re-apply (compression may strip guard)
      OUT=$(attempt_build)
      if echo "$OUT" | grep -q "^Wrote episode"; then
        echo "BUILD OK after compression"
      else
        echo "STILL FAILING after compression:"
        echo "$OUT" | head -10
        exit 1
      fi
    else
      echo "Compression yielded $NEW words; not safe to use"
      exit 1
    fi
  else
    echo "Build failure not in scope of auto-fix; manual intervention needed"
    exit 1
  fi
fi

# Commit + push
git add "$BOOK_DIR/_system/episode-drafts/$EP_ID/" \
        "$BOOK_DIR/episodes/$EP_ID.txt" \
        "$CHAPTER" 2>/dev/null || true

EP_NUM=$(echo "$EP_ID" | grep -oE "EP[0-9.]+" | head -1)
git commit -m "podcast(kar-$EP_NUM): $COMMIT_SUFFIX — $EP_ID

Via author_chapter_skeleton.sh + build_and_ship_chapter.sh pipeline.
Auto-fixes applied for META-prose / band / honorific / pronunciation /
guard normalizations as needed." 2>&1 | tail -2

git push origin book/kitab-al-riyad 2>&1 | tail -2
