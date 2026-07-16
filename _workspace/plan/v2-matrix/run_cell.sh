#!/usr/bin/env bash
# v2 knob-matrix cell runner (Phase 4 validation) — PORTABLE tracked copy.
# See CONTINUATION.md in this directory for the full cross-machine protocol.
#
# Usage: run_cell.sh <BOOK_DIR> <augmentation> <voice> <cell-label> [resume]
#   full (default): stamp knobs, clean stage outputs, run the 0book branch
#                   (design->compose(v2)->illustrate->slide-import), then — if the
#                   run reached awaiting-layout — auto-layout + render the PDF.
#   resume:         skip the 0book driver; run slide-import -> layout -> render only.
set -uo pipefail
BOOK_DIR="$(cd "$1" && pwd)"; AUG="$2"; VOICE="$3"; CELL="$4"; MODE="${5:-full}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAIN="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
PY="$MAIN/.venv/bin/python3"
WT_ROOT="$(git -C "$BOOK_DIR" rev-parse --show-toplevel)"
EXP="$MAIN/_workspace/experiments/v2-matrix"   # machine-local logs/results (gitignored)
LOG="$EXP/logs/$CELL.log"
mkdir -p "$EXP/logs" "$EXP/results/$CELL"
exec >>"$LOG" 2>&1
echo "=== cell $CELL ($MODE) START $(date -u +%FT%TZ) aug=$AUG voice=$VOICE book=$BOOK_DIR"
echo "$$" > "$EXP/logs/$CELL.pid"

export BOOK_PIPELINE_V2=1
export PYTHONUNBUFFERED=1  # phase logs must stream to the cell log for liveness checks

# 1. stamp the two knobs into series-config.yaml (text-level edit, rest preserved)
"$PY" - "$BOOK_DIR" "$AUG" "$VOICE" <<'PYEOF'
import re, sys
from pathlib import Path
p = Path(sys.argv[1]) / "_system" / "series-config.yaml"
txt = p.read_text(encoding="utf-8")
for k in ("book_augmentation", "book_voice"):
    txt = re.sub(rf'(?m)^{k}:.*\n?', '', txt)
p.write_text(txt.rstrip("\n") + f"\nbook_augmentation: {sys.argv[2]}\nbook_voice: {sys.argv[3]}\n",
             encoding="utf-8")
print(f"knobs: book_augmentation={sys.argv[2]} book_voice={sys.argv[3]}")
PYEOF

if [ "$MODE" = "full" ]; then
  # 2. clean per-cell stage outputs. KEEP book/_chunks (per-chapter compose
  #    checkpoint — knob-independent faithful base) and book/book-toc.json.
  rm -f "$BOOK_DIR"/book/book.md "$BOOK_DIR"/book/book-illustrated.md \
        "$BOOK_DIR"/book/book-slides.md "$BOOK_DIR"/book/book.pdf \
        "$BOOK_DIR"/book/visual-layout.json
  rm -rf "$BOOK_DIR"/book/visuals

  # 3. run the 0book branch exactly as the orchestrator would
  PYTHONPATH="$WT_ROOT/scripts/podcast" "$PY" - "$BOOK_DIR" <<'PYEOF'
import sys
from pathlib import Path
from phases.book_driver import _drive_book_branch
rc = _drive_book_branch(Path(sys.argv[1]).resolve())
print(f"_drive_book_branch rc={rc}")
sys.exit(0 if rc in (0, 3) else 1)
PYEOF
  RC=$?
  if [ $RC -ne 0 ]; then
    echo "=== cell $CELL FAILED (driver rc=$RC) $(date -u +%FT%TZ)"
    exit 1
  fi
else
  # resume: slide-import only (deck halt resolved out-of-band)
  PYTHONPATH="$WT_ROOT/scripts/podcast" "$PY" - "$BOOK_DIR" <<'PYEOF'
import sys
from pathlib import Path
from _slide_import import author_phase_slide_import
from _progress import update_phase
book_dir = Path(sys.argv[1]).resolve()
result = author_phase_slide_import(book_dir, log=print)
print(f"slide-import resume: {result}")
update_phase(book_dir, phase="0book-slide-import", status="completed",
             extras={"imported": result.get("imported", {}),
                     "exempt": result.get("exempt", []),
                     "awaiting_layout": bool(result.get("awaiting_layout"))})
PYEOF
  RC=$?
  if [ $RC -ne 0 ]; then
    echo "=== cell $CELL FAILED (slide-import resume rc=$RC) $(date -u +%FT%TZ)"
    exit 1
  fi
fi

# 4. did we reach awaiting-layout, or halt on missing decks?
SLIDE_STATUS="$(jq -r '.phases."0book-slide-import".status' "$BOOK_DIR/_system/orchestrator-state.json")"
if [ "$SLIDE_STATUS" = "halted" ]; then
  echo "slide-import halted (decks not dropped) — cell paused pending deck/SKIP decision"
  echo "=== cell $CELL PAUSED $(date -u +%FT%TZ)"
  exit 3
fi
if [ ! -f "$BOOK_DIR/book/visuals/index.json" ]; then
  echo "no visuals/index.json after slide-import status=$SLIDE_STATUS — treating as zero-candidate cell"
  mkdir -p "$BOOK_DIR/book/visuals"
  printf '{"schema": "book.visuals-index/v1", "visuals": []}\n' > "$BOOK_DIR/book/visuals/index.json"
fi

# 5. auto-layout (Composer stand-in) + render
"$PY" "$SCRIPT_DIR/auto_layout.py" "$BOOK_DIR" || { echo "=== cell $CELL FAILED (auto-layout)"; exit 1; }
PYTHONPATH="$WT_ROOT/scripts/podcast" "$PY" "$WT_ROOT/scripts/podcast/build_book_pdf.py" "$BOOK_DIR" --json \
  || { echo "=== cell $CELL FAILED (render) $(date -u +%FT%TZ)"; exit 1; }

# 6. snapshot artifacts for the matrix record + commit + push cell state
cp "$BOOK_DIR"/book/book.md "$BOOK_DIR"/book/book.pdf "$BOOK_DIR"/book/visual-layout.json \
   "$EXP/results/$CELL/" 2>/dev/null
cp "$BOOK_DIR"/_system/book-fluency-report.json "$BOOK_DIR"/_system/book-voice-report.json \
   "$BOOK_DIR"/_system/book-augment-report.json "$BOOK_DIR"/_system/book-render-checks.json \
   "$BOOK_DIR"/_system/book-validation-report.json "$EXP/results/$CELL/" 2>/dev/null
git -C "$WT_ROOT" add -A "$BOOK_DIR" >/dev/null 2>&1
git -C "$WT_ROOT" commit -m "book($(basename "$BOOK_DIR")): v2 matrix cell $CELL — aug=$AUG voice=$VOICE" \
  >/dev/null 2>&1 || true
git -C "$WT_ROOT" push origin HEAD >/dev/null 2>&1 && echo "pushed to origin" || echo "push FAILED (retry manually)"
echo "=== cell $CELL RENDER-DONE $(date -u +%FT%TZ) — ready for challengers"
