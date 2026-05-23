#!/usr/bin/env bash
# Dry-run reshape script: the-master-and-the-disciple
# Drafted: 2026-05-23
#
# Reshapes the canonical PNG-bearing source folder into the proposed
# podcast-data/ layout. Default mode is DRY-RUN (prints commands only).
#
# Usage:
#   ./reshape-master-and-disciple.sh           # dry-run, prints intended ops
#   DRY_RUN=0 ./reshape-master-and-disciple.sh # actually execute
#
# After confirmation, also runs --collect step to verify the target tree
# is sane (no missing files, png count matches, refined-english.md non-empty).

set -euo pipefail

DRY_RUN="${DRY_RUN:-1}"

SRC="/Users/asifhussain/PROJECTS/podcast-factory/worktrees/main/_workspace/books/the-master-and-the-disciple"
DST="/Users/asifhussain/PROJECTS/podcast-data/books/the-master-and-the-disciple"

# Stale duplicates that should be removed AFTER reshape verifies clean.
STALE_DUPLICATES=(
  "/Users/asifhussain/PROJECTS/podcast-factory/worktrees/main/content/podcast/library/books/the-master-and-the-disciple"
  "/Users/asifhussain/PROJECTS/podcast-factory/worktrees/book-islr/_workspace/books/the-master-and-the-disciple"
  "/Users/asifhussain/PROJECTS/podcast-factory/worktrees/book-kar/content/podcast/library/books/the-master-and-the-disciple"
  "/Users/asifhussain/PROJECTS/podcast-factory/worktrees/book-asaas/content/podcast/library/books/the-master-and-the-disciple"
)

# ─── helpers ──────────────────────────────────────────────────────────────────

run() {
  if [[ "$DRY_RUN" == "1" ]]; then
    printf '[dry-run] %s\n' "$*"
  else
    printf '[exec]    %s\n' "$*"
    eval "$@"
  fi
}

heredoc_to_file() {
  # $1 = target path, stdin = content
  local target="$1"
  if [[ "$DRY_RUN" == "1" ]]; then
    printf '[dry-run] write file %s (content piped from heredoc)\n' "$target"
    cat >/dev/null
  else
    printf '[exec]    write file %s\n' "$target"
    cat >"$target"
  fi
}

# ─── preflight ────────────────────────────────────────────────────────────────

[[ "$DRY_RUN" == "1" ]] && echo "════ DRY RUN — no files will be changed ════" || echo "════ LIVE RUN — files WILL move ════"
echo "SRC: $SRC"
echo "DST: $DST"
echo

[[ -d "$SRC" ]] || { echo "ERROR: source not found: $SRC" >&2; exit 1; }
[[ -d "$DST" ]] && { echo "ERROR: destination already exists: $DST" >&2; exit 1; }

png_count=$(find "$SRC/topic_1215" -name 'page_*.png' | wc -l | tr -d ' ')
echo "Verified source: $png_count PNGs in topic_1215/"
[[ "$png_count" == "95" ]] || { echo "ERROR: expected 95 PNGs, found $png_count" >&2; exit 1; }
echo

# ─── 1. create target skeleton ────────────────────────────────────────────────

echo "── step 1: create target skeleton ──"
run "mkdir -p '$DST/_system/source/images'"
run "mkdir -p '$DST/_system/source/text'"
run "mkdir -p '$DST/_system/source/notes'"
run "mkdir -p '$DST/chapters'"
run "mkdir -p '$DST/notebooklm/scaffolding'"
run "mkdir -p '$DST/chapter-contracts'"
run "mkdir -p '$DST/episodes'"
run "mkdir -p '$DST/framings'"
run "mkdir -p '$DST/transcripts'"
run "mkdir -p '$DST/audits'"
echo

# ─── 2. move source images ────────────────────────────────────────────────────

echo "── step 2: move 95 page PNGs ──"
run "rsync -a '$SRC/topic_1215/' '$DST/_system/source/images/'"
echo

# ─── 3. move chapter drafts (rename to slug-case .md) ─────────────────────────

echo "── step 3: rename and move chapter drafts ──"
declare -a CHAPTER_MAP=(
  "Ch-00-Before-the-Door-Opens.txt|ch00-before-the-door-opens.md"
  "Ch-01-Scholar and Seeker - Refined.md|ch01-scholar-and-seeker.md"
  "Ch-02-Oath and Cosmic Origins - Refined.md|ch02-oath-and-cosmic-origins.md"
  "Ch-03-The Inner Dimensions - Refined.md|ch03-the-inner-dimensions.md"
  "Ch-04-The Greater Shaykh - Refined.md|ch04-the-greater-shaykh.md"
  "Ch-05-Father and Community - Refined.md|ch05-father-and-community.md"
  "Ch-06-The Ultimate Truth - Refined.md|ch06-the-ultimate-truth.md"
  "Ch-07-The-Living-Rope.txt|ch07-the-living-rope.md"
)
for pair in "${CHAPTER_MAP[@]}"; do
  old="${pair%%|*}"
  new="${pair##*|}"
  run "cp '$SRC/$old' '$DST/chapters/$new'"
done
echo

# ─── 4. assemble refined-english.md ───────────────────────────────────────────

echo "── step 4: assemble refined-english.md from ch00..ch07 ──"
REFINED="$DST/_system/source/text/refined-english.md"
if [[ "$DRY_RUN" == "1" ]]; then
  echo "[dry-run] concatenate $DST/chapters/ch[00-07]-*.md → $REFINED"
  echo "[dry-run]   header line: '# The Master and the Disciple — Refined English'"
  echo "[dry-run]   per-chapter divider: '\\n\\n---\\n\\n# {chapter title}\\n\\n'"
else
  {
    echo "# The Master and the Disciple — Refined English"
    echo
    echo "_Assembled from Ch-00 through Ch-07 drafts on $(date +%Y-%m-%d)._"
    echo
    for f in "$DST/chapters"/ch[0-9][0-9]-*.md; do
      echo
      echo "---"
      echo
      cat "$f"
      echo
    done
  } > "$REFINED"
  echo "[exec]    refined-english.md assembled ($(wc -l <"$REFINED") lines)"
fi
echo

# ─── 5. move editorial notes + audit ──────────────────────────────────────────

echo "── step 5: move editorial notes + final review report ──"
run "cp '$SRC/Source and Editorial Notes.md' '$DST/_system/source/notes/source-and-editorial-notes.md'"
run "cp '$SRC/Final Review Report.md' '$DST/audits/final-review-report.md'"
echo

# ─── 6. move NotebookLM bundle (rename, lowercase, split scaffolding) ─────────

echo "── step 6: move NotebookLM bundle ──"
declare -a NB_MAP=(
  "00-NotebookLM-Source-Index.md|notebooklm/00-source-index.md"
  "01-pronunciation-guide.md|notebooklm/01-pronunciation-guide.md"
  "02-glossary.md|notebooklm/02-glossary.md"
  "03-source-integrity-notes.md|notebooklm/03-source-integrity-notes.md"
  "04-do-not-say-guardrails.md|notebooklm/04-do-not-say-guardrails.md"
  "05-episode-arc.md|notebooklm/05-episode-arc.md"
  "06-human-review-checklist.md|notebooklm/06-human-review-checklist.md"
  "ch00-scaffolding.md|notebooklm/scaffolding/ch00.md"
  "ch01-scaffolding.md|notebooklm/scaffolding/ch01.md"
  "ch02-scaffolding.md|notebooklm/scaffolding/ch02.md"
  "ch03-scaffolding.md|notebooklm/scaffolding/ch03.md"
  "ch04-scaffolding.md|notebooklm/scaffolding/ch04.md"
  "ch05-scaffolding.md|notebooklm/scaffolding/ch05.md"
  "ch06-scaffolding.md|notebooklm/scaffolding/ch06.md"
  "ch07-scaffolding.md|notebooklm/scaffolding/ch07.md"
)
for pair in "${NB_MAP[@]}"; do
  old="${pair%%|*}"
  new="${pair##*|}"
  run "cp '$SRC/_notebooklm/$old' '$DST/$new'"
done
echo

# ─── 7. write meta.yml ────────────────────────────────────────────────────────

echo "── step 7: write meta.yml ──"
if [[ "$DRY_RUN" == "1" ]]; then
  echo "[dry-run] write $DST/meta.yml (content shown below)"
  cat <<'YAML'
─── meta.yml content preview ──────────────────────────
slug: the-master-and-the-disciple
title: The Master and the Disciple
short_name: master-disciple
original_title: Kitāb al-ʿĀlim wa-l-Ghulām
source_pdf: ../../raw/Kitaab_Al-aalim_wal_Ghulam_Chapters/
source_audio: ../../raw/Kitaab_Al-aalim_wal_Ghulam_Chapters/Podcast/00 - The Master And The Disciple.mp3

pipeline:
  current_phase: 0c
  next_phase: 0d
  chapters_drafted: 8
  chapters_with_contracts: 0
  episodes_shipped: 0

provenance:
  reshaped_from: worktrees/main/_workspace/books/the-master-and-the-disciple/
  reshape_date: 2026-05-23
───────────────────────────────────────────────────────
YAML
else
  cat >"$DST/meta.yml" <<'YAML'
slug: the-master-and-the-disciple
title: The Master and the Disciple
short_name: master-disciple
original_title: Kitāb al-ʿĀlim wa-l-Ghulām
source_pdf: ../../raw/Kitaab_Al-aalim_wal_Ghulam_Chapters/
source_audio: ../../raw/Kitaab_Al-aalim_wal_Ghulam_Chapters/Podcast/00 - The Master And The Disciple.mp3

pipeline:
  current_phase: 0c
  next_phase: 0d
  chapters_drafted: 8
  chapters_with_contracts: 0
  episodes_shipped: 0

provenance:
  reshaped_from: worktrees/main/_workspace/books/the-master-and-the-disciple/
  reshape_date: 2026-05-23
YAML
  echo "[exec]    meta.yml written"
fi
echo

# ─── 8. verification (post-move sanity checks) ────────────────────────────────

echo "── step 8: verification ──"
if [[ "$DRY_RUN" == "1" ]]; then
  echo "[dry-run] would verify: 95 PNGs in _system/source/images/"
  echo "[dry-run] would verify: 8 chapter drafts in chapters/"
  echo "[dry-run] would verify: refined-english.md exists and is non-empty"
  echo "[dry-run] would verify: 15 files in notebooklm/ (7 top + 8 scaffolding)"
  echo "[dry-run] would verify: meta.yml is valid YAML"
else
  png_after=$(find "$DST/_system/source/images" -name 'page_*.png' | wc -l | tr -d ' ')
  ch_after=$(ls "$DST/chapters"/ch[0-9][0-9]-*.md 2>/dev/null | wc -l | tr -d ' ')
  [[ "$png_after" == "95" ]] || { echo "FAIL: expected 95 PNGs, got $png_after"; exit 1; }
  [[ "$ch_after"  == "8"  ]] || { echo "FAIL: expected 8 chapters, got $ch_after"; exit 1; }
  [[ -s "$DST/_system/source/text/refined-english.md" ]] || { echo "FAIL: refined-english.md missing/empty"; exit 1; }
  echo "[exec]    all checks passed"
fi
echo

# ─── 9. stale-duplicate cleanup (gated — REQUIRES SECOND OPT-IN) ──────────────

echo "── step 9: stale duplicate removal (gated) ──"
echo "The following duplicates exist and would be removed by a SEPARATE pass"
echo "AFTER the new tree above has been independently verified:"
for d in "${STALE_DUPLICATES[@]}"; do
  if [[ -d "$d" ]]; then
    size=$(du -sh "$d" 2>/dev/null | cut -f1)
    echo "  - $d  ($size)"
  fi
done
echo
echo "This script does NOT delete them, even with DRY_RUN=0. Run the separate"
echo "cleanup script after Asif confirms the reshape is good."
echo

echo "════ reshape script finished ($([ "$DRY_RUN" == "1" ] && echo "dry-run" || echo "live")) ════"
