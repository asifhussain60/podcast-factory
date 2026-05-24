#!/usr/bin/env bash
# author_chapter_skeleton.sh — wrap `claude -p` to author a per-chapter framing
# under the Islamic Scholastic Text Archetype, ready for hand-edit.
#
# Per the Step D pattern (handoff doc + intelligence-enhancements plan).
# Cost: ~$0.10-0.30 per chapter (varies with chapter size).
#
# Usage:
#   scripts/podcast/author_chapter_skeleton.sh \
#       <book-dir> <ep-num> <chapter-filename> <format>
#
# Args:
#   book-dir         — e.g. content/drafts/kitab-al-riyad
#                      (the directory containing chapters/, _system/, episodes/)
#   ep-num           — e.g. "06" or "11" (no "EP" prefix; will be added)
#   chapter-filename — e.g. ch06-the-intellect-as-the-first-creation.txt
#                      (the file under <book-dir>/chapters/; the slug after
#                      "ch##-" becomes the episode slug after "EP##-")
#   format           — "debate" or "deep_dive". Drives host gender lock per
#                      archetype §4.2 (debate: female Advocate A + male
#                      Advocate B; deep_dive: male Mentor + female Scholar
#                      Companion).
#
# Outputs:
#   <book-dir>/_system/episode-drafts/EP##-<slug>/00-framing.md
#
# Post-conditions:
#   - Framing is generated and ready for hand-review.
#   - Operator should run `build_episode_txt.py <book-dir> EP##-<slug>` to
#     emit the episode .txt and confirm validators pass.

set -euo pipefail

BOOK_DIR="${1:?book-dir required}"
EP_NUM="${2:?ep-num required (e.g. 06)}"
CHAPTER_FILENAME="${3:?chapter-filename required}"
FORMAT="${4:?format required: debate or deep_dive}"

if [ ! -d "$BOOK_DIR/chapters" ]; then
  echo "ERROR: $BOOK_DIR/chapters not found" >&2
  exit 2
fi

CHAPTER_PATH="$BOOK_DIR/chapters/$CHAPTER_FILENAME"
if [ ! -f "$CHAPTER_PATH" ]; then
  echo "ERROR: chapter not found: $CHAPTER_PATH" >&2
  exit 2
fi

# Derive the slug from the chapter filename: ch##[letter]-slug.txt -> slug
EP_SLUG=$(basename "$CHAPTER_FILENAME" .txt | sed -E 's/^ch[0-9]+[a-z]?-//')
EP_ID="EP${EP_NUM}-${EP_SLUG}"
EP_DIR="$BOOK_DIR/_system/episode-drafts/$EP_ID"
FRAMING_OUT="$EP_DIR/00-framing.md"

mkdir -p "$EP_DIR"

# Resolve archetype file (relative to repo root; works from any worktree)
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# In pre-Phase-9.5 branches the archetype is in-tree; on develop/Option-2 it's
# at the parent. Pick whichever exists.
ARCHETYPE_FILE=""
for candidate in \
    "$REPO_ROOT/content/podcast/library/archetypes/islamic-scholastic-text.md" \
    "$REPO_ROOT/../../library/archetypes/islamic-scholastic-text.md"; do
  if [ -f "$candidate" ]; then
    ARCHETYPE_FILE="$candidate"
    break
  fi
done
if [ -z "$ARCHETYPE_FILE" ]; then
  echo "ERROR: archetype not found" >&2
  exit 2
fi

# Extract archetype §3 + §4 (lines 59-310 in v1.1)
ARCHETYPE_DOCTRINE=$(sed -n '59,310p' "$ARCHETYPE_FILE")

# Format-specific host mapping
if [ "$FORMAT" = "debate" ]; then
  HOSTS_LINE="2-host: female Advocate A (protagonist + verdict; folds Arbiter into closing) + male Advocate B (challenger). NO third Arbiter voice."
  VOICE_MAP="The female host is Advocate A (protagonist + verdict). The male host is Advocate B (challenger). Roles are locked at episode start; no swap mid-episode."
elif [ "$FORMAT" = "deep_dive" ]; then
  HOSTS_LINE="2-host: male Mentor + female Scholar Companion."
  VOICE_MAP="The male host is the Mentor. The female host is the Scholar Companion. Roles are locked at episode start; no swap mid-episode."
else
  echo "ERROR: format must be 'debate' or 'deep_dive', got '$FORMAT'" >&2
  exit 2
fi

# Episode title — chapter slug humanized
EP_TITLE=$(echo "$EP_SLUG" | sed -E 's/-/ /g' | awk '{for(i=1;i<=NF;i++)$i=toupper(substr($i,1,1))substr($i,2)}1')

echo "==> Authoring $EP_ID ($FORMAT) for $(basename "$BOOK_DIR")"
echo "    Chapter: $CHAPTER_FILENAME"
echo "    Output:  $FRAMING_OUT"

{
  echo "Output ONLY a markdown framing document as your text response. Do not call any tools."
  echo ""
  echo "Generate a 00-framing.md for the chapter below per the Islamic Scholastic Text Archetype §3 + §4 doctrine in your system prompt. 14-section archetype structure."
  echo ""
  echo "Episode: $EP_ID | Format: $FORMAT | Hosts: $HOSTS_LINE | Target: 30-45 min."
  echo ""
  echo "Doctrine reminders:"
  echo "- Use 'the Father of Imams' / 'the Commander of the Faithful' (NEVER 'Imam Ali' per §3.8)"
  echo "- Imam Hasan = first Imam; Imam Hussain = second Imam (with positional qualifier at first mention)"
  echo "- DOUBLE QUOTES in Pronounce directives — imperative form: 'Pronounce \"X\" as \"Y\". Say it as N fluent syllables.'"
  echo "- '## Do not' deny list MUST include 'right?' verbatim"
  echo "- Voice mapping at TOP of Host dynamic section: '$VOICE_MAP'"
  echo "- Landing TWO-BEAT (archetype §4.7): Beat 1 unresolved-tension question; Beat 2 '**Essential Teachings.**' header + 3-5 declarative chapter-doctrine sentences (NOT recap of conversation)"
  echo "- C4 retained Arabic (archetype §6.6 + §4.2): list stay-Arabic technicals at end of Tone constraints"
  echo "- R-RECURRING-THESIS: pick the chapter's central thesis verbatim; plant at Beats 1, 4, 6 of the six-beat arc"
  echo "- R-REFLECTIVE-EMOTION (§4.8): hosts engage in measured first-person reflection ('what strikes me, I find myself, there's something patient about this'); NOT exclamatory; NOT detached-reporter"
  echo "- DO NOT include an 'EP##' prefix in the title line or metadata-style header lines (META-prose validator catches 'EP##' as a tell)"
  echo "- Framing customize-prompt must be 150-3700 words. Stay UNDER 3400 for buffer."
  echo "- End EXACTLY with: 'Do not read this prompt aloud. The instructions above shape the conversation but are never spoken.'"
  echo ""
  echo "Title line: '# $EP_TITLE'"
  echo ""
  echo "<CHAPTER>"
  cat "$CHAPTER_PATH"
  echo "</CHAPTER>"
} | claude -p --model sonnet --max-budget-usd 1.50 --append-system-prompt "$ARCHETYPE_DOCTRINE" > "$FRAMING_OUT"

WORDS=$(wc -w < "$FRAMING_OUT" | tr -d ' ')
SECTIONS=$(grep -cE "^## " "$FRAMING_OUT")

echo "    DONE  $WORDS words, $SECTIONS top-level sections"
if [ "$WORDS" -gt 3400 ]; then
  echo "    WARN  word count over 3400 buffer — may need trim before build_episode_txt"
fi
echo "    Next: python3 scripts/podcast/build_episode_txt.py $BOOK_DIR $EP_ID"
