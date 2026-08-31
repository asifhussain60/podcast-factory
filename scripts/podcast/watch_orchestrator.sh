#!/usr/bin/env bash
# watch_orchestrator.sh — self-healing watchdog for orchestrate_book.py
#
# Relaunches --resume on crash or failure until the book reaches
# finalize/halted (SHIP-READY) or done. Survives Claude session close,
# laptop sleep, and network blips.
#
# Usage:
#   bash scripts/podcast/watch_orchestrator.sh <slug>
#   bash scripts/podcast/watch_orchestrator.sh <slug> --max-retries 30
#
# Exit codes:
#   0  — book reached finalize/halted or done (success)
#   1  — exhausted retries without completing
#   2  — bad arguments or missing state file

set -uo pipefail

# ── Args ─────────────────────────────────────────────────────────────────────
SLUG="${1:?Usage: watch_orchestrator.sh <slug> [--max-retries N]}"
MAX_RETRIES=20          # each retry = one orchestrator launch; 20 × ~30s backoff = ~10 min overhead max
RETRY_DELAY_S=30        # seconds to wait between a crash and the next attempt

shift
while [[ $# -gt 0 ]]; do
    case "$1" in
        --max-retries) MAX_RETRIES="$2"; shift 2 ;;
        *) echo "Unknown flag: $1" >&2; exit 2 ;;
    esac
done

# ── Paths ─────────────────────────────────────────────────────────────────────
REPO_ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
# Prefer the repo virtualenv if it has the required packages. If the venv
# exists but is missing deps (e.g., packages were installed via `pip install
# --user` rather than into the venv), fall back to the system python3 which
# can reach user-level site-packages. Only hard-code /usr/bin/python3 as a
# last resort — it may also lack deps, but orchestrate_book.py will surface
# a clear fix message in that case.
if [[ -x "$REPO_ROOT/.venv/bin/python" ]] && \
   "$REPO_ROOT/.venv/bin/python" -c "import yaml, anthropic, requests" 2>/dev/null; then
    PYTHON="$REPO_ROOT/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1 && \
     python3 -c "import yaml, anthropic, requests" 2>/dev/null; then
    PYTHON="python3"
else
    PYTHON=/usr/bin/python3
fi
ORCH="$REPO_ROOT/scripts/podcast/orchestrate_book.py"

# Resolve state file path via _paths.find_content() so every bucket
# (Islamic, Technical, Fiction, Guides) is found at its canonical location
# content/<Bucket>/<slug>/ rather than the legacy flat path.
#
# This ran twice: the first copy executed before _WD_SLUG was exported, so it
# always resolved the empty slug to nothing and was immediately overwritten.
export _WD_SLUG="$SLUG"
_CONTENT_DIR=$(cd "$REPO_ROOT" && _WD_SLUG="$SLUG" $PYTHON - <<'PYEOF' 2>/dev/null
import sys, os
sys.path.insert(0, 'scripts/podcast')
from _paths import find_content
slug = os.environ.get('_WD_SLUG', '')
r = find_content(slug)
if r:
    print(r[2])
PYEOF
)

if [[ -n "$_CONTENT_DIR" ]]; then
    BOOK_DIR="$_CONTENT_DIR"
else
    # Fallback: legacy flat path (books category, pre-2026-05-26 layout)
    BOOK_DIR="$REPO_ROOT/content/drafts/$SLUG"
fi
STATE="$BOOK_DIR/_system/orchestrator-state.json"
SENTINEL="$BOOK_DIR/_system/watchdog.json"

LOG_DIR="$REPO_ROOT/_workspace/logs"
LOG="$LOG_DIR/orchestrator-$SLUG.log"

mkdir -p "$LOG_DIR"

_log() { echo "[watchdog $(date -u +%H:%M:%SZ)] $*" | tee -a "$LOG"; }
_state() { jq -r "${1}" "$STATE" 2>/dev/null || echo ""; }

# ── Verify book exists ────────────────────────────────────────────────────────
if [[ ! -f "$STATE" ]]; then
    _log "ERROR: state file not found: $STATE"
    exit 2
fi

# ── Write sentinel (lets start-session.sh surface this to the user) ───────────
echo "{\"slug\":\"$SLUG\",\"pid\":$$,\"started\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" > "$SENTINEL"

_log "=== watchdog start: $SLUG (max $MAX_RETRIES retries, ${RETRY_DELAY_S}s backoff) ==="

# ── Self-owned status heartbeat ───────────────────────────────────────────────
# The status card used to exist only while a Claude session was attached to
# re-arm a wakeup and render it. A run that outlived the session kept working and
# stopped reporting, which is the failure "once started it should end after
# completing everything" is meant to rule out. So the RUN owns its own beat: a
# background loop writes the card to _system/status-card.txt on a fixed cadence,
# whether or not anyone is watching, and a session that attaches just reads the
# file.
#
# 270s, not 300: the interval predates this and is set just under five minutes to
# stay inside the prompt-cache window a reading session works in. Cheap either
# way — rendering the card is pure file I/O over state the pipeline already
# writes, no model spend.
HEARTBEAT_S="${HEARTBEAT_S:-270}"
CARD_PATH="$BOOK_DIR/_system/status-card.txt"

_emit_card() {
    # Written to a temp file and moved, so a reader never catches a half-written
    # card. Failure is silent by design: a status card that cannot be rendered
    # must never take down the run it is reporting on.
    local tmp="$CARD_PATH.tmp.$$"
    if "$PYTHON" "$REPO_ROOT/scripts/podcast/book_status_card.py" "$BOOK_DIR" > "$tmp" 2>/dev/null; then
        mv -f "$tmp" "$CARD_PATH"
    else
        rm -f "$tmp"
    fi
}

_heartbeat_loop() {
    while true; do
        _emit_card
        sleep "$HEARTBEAT_S"
    done
}

_heartbeat_loop &
HEARTBEAT_PID=$!
# EXIT only, and only the heartbeat child. The watchdog deliberately has no trap
# that reaches the orchestrator -- SIGTERM here would kill a live multi-hour run,
# which is why "never kill the watchdog" is a standing rule. This trap adds a
# child of its own and must not widen that blast radius.
trap 'kill "$HEARTBEAT_PID" 2>/dev/null; _emit_card' EXIT
_log "heartbeat: status card every ${HEARTBEAT_S}s -> ${CARD_PATH#"$REPO_ROOT/"}"


# ── Helpers: terminal and human-review states ─────────────────────────────────
_is_done() {
    # True when the book has reached a terminal success state (ship-ready or done).
    local phase status
    phase="$(_state '.phase')"
    status="$(_state '.phase_status')"
    if [[ "$phase" == "done" ]]; then return 0; fi
    if [[ "$phase" == "finalize" && "$status" == "halted" ]]; then return 0; fi
    return 1
}

_is_human_review_gate() {
    # True when the orchestrator has halted at a phase that requires human sign-off
    # before proceeding. The watchdog stops here — the human re-invokes --resume
    # (which auto-spawns a fresh watchdog) to advance past the gate.
    local phase status
    phase="$(_state '.phase')"
    status="$(_state '.phase_status')"
    # NOTE: 0f/halted is intentionally NOT a watchdog short-circuit. The dispatcher
    # (resume_dispatcher.py) clears the 0f gate on --resume and drives per-chapter;
    # short-circuiting here deadlocked --resume (the re-invoked watchdog re-saw
    # 0f/halted and exited before the orchestrator ran). Removed 2026-06-09.
    # 0ci: book intelligence gap analysis written; human reviews before Phase 0d runs.
    # Running --resume acknowledges the review — the driver now skips 0ci on re-entry.
    if [[ "$phase" == "0ci" && "$status" == "halted" ]]; then return 0; fi
    return 1
}

_is_iter_cap_halt() {
    # True when the per-chapter loop has exhausted its 3-iteration convergence cap
    # with unresolved P0/P1 findings. The orchestrator sets phase=per-chapter,
    # phase_status=failed intentionally. Retrying without human intervention will
    # reproduce the same finding and exhaust the watchdog's attempt budget.
    local phase status
    phase="$(_state '.phase')"
    status="$(_state '.phase_status')"
    if [[ "$phase" == "per-chapter" && "$status" == "failed" ]]; then return 0; fi
    return 1
}

_needs_human_fix() {
    # THE GENERAL RULE the three checks above are each a special case of
    # (Asif, 2026-08-31): a failure the CODE ITSELF described how to fix by hand
    # is not a crash to retry — it is a halt.
    #
    # `manual_fallback` is set by a failing phase precisely when it knows what a
    # person must do next, and it is already recorded at
    # `.phases[<phase>].manual_fallback`. Retrying regardless throws that
    # instruction away up to twenty times, each attempt paying for the same
    # model calls to reach the same deterministic failure.
    #
    # This repo learned the lesson twice and hard-coded a case each time —
    # per-chapter/failed (2026-05-25, "retrying blindly will reproduce the same
    # finding 20x") and 0ci/halted — without ever drawing the rule. A gate added
    # later, like phase 0d's supplied-chapter-set check, would have been retried
    # twenty times because its phase name was not on a list.
    local phase status mf
    phase="$(_state '.phase')"
    status="$(_state '.phase_status')"
    [[ "$status" == "failed" ]] || return 1
    mf="$(_state ".phases[\"$phase\"].manual_fallback // empty")"
    [[ -n "$mf" ]]
}

_log_human_fix() {
    local phase
    phase="$(_state '.phase')"
    _log "=== NEEDS A HUMAN: $SLUG failed at phase $phase. Watchdog will NOT retry. ==="
    _log "Review the log and fix the cause before starting this again."
    _log "Reason: $(_state '.last_error.message')"
    _log "Fix:    $(_state ".phases[\"$phase\"].manual_fallback")"
}

# ── Short-circuit if already done, at a human-review gate, or at iter-cap halt ─
if _is_done; then
    _log "Already complete (phase=$(_state '.phase') status=$(_state '.phase_status')) — nothing to do."
    rm -f "$SENTINEL"
    exit 0
fi
if _is_human_review_gate; then
    _log "At human-review gate (phase=$(_state '.phase') status=$(_state '.phase_status')) — watchdog pausing."
    _log "Review the series plan, then re-run: bash scripts/podcast/watch_orchestrator.sh $SLUG"
    rm -f "$SENTINEL"
    exit 0
fi
if _needs_human_fix; then
    _log_human_fix
    rm -f "$SENTINEL"
    exit 2
fi
if _is_iter_cap_halt; then
    _log "At iter-cap halt (per-chapter/failed) — human review required. Watchdog will not retry."
    _log "Check findings: jq '.last_error' $STATE"
    _log "Fix the unresolved P0/P1, then re-run: python3 scripts/podcast/orchestrate_book.py --resume $SLUG --retry-phase per-chapter"
    rm -f "$SENTINEL"
    exit 0
fi

# ── Main loop ─────────────────────────────────────────────────────────────────
for attempt in $(seq 1 "$MAX_RETRIES"); do
    PHASE="$(_state '.phase')"
    STATUS="$(_state '.phase_status')"

    # PERSISTENT budget, checked before every relaunch. The `$attempt` counter
    # above is local to THIS watchdog, and orchestrate_book.py spawns a fresh
    # watchdog on every bare --resume — so that counter resets to 1 each time and
    # the ceiling it prints never actually bound. One real run reached 201
    # attempts, all of them logged as "attempt N/20". The real count lives in
    # orchestrator-state.json, keyed by phase, and is cleared the moment the
    # phase completes; see watchdog_budget.py.
    #
    # Exit 3 = this phase has burned its budget, stop. Exit 2 = the book or its
    # state could not be resolved, which must NOT stop a run the old code would
    # have made, so it degrades to the local counter alone.
    BUDGET_LINE="$("$PYTHON" "$REPO_ROOT/scripts/podcast/watchdog_budget.py" "$SLUG" --max "$MAX_RETRIES" 2>&1)"
    BUDGET_RC=$?
    _log "--- ${BUDGET_LINE%%$'\n'*} · status=$STATUS (local attempt $attempt) ---"
    if [[ "$BUDGET_RC" -eq 3 ]]; then
        _log "=== BUDGET EXHAUSTED: phase $PHASE attempted too many times without completing. ==="
        _log "Nothing is retried further — a repeat would reproduce the same failure."
        _log "1. Check: jq '.last_error, .phase_attempts' $STATE"
        _log "2. Fix the cause, then: python3 scripts/podcast/orchestrate_book.py --resume $SLUG --retry-phase $PHASE"
        rm -f "$SENTINEL"
        exit 1
    fi

    # PODCAST_WATCHDOG=1 tells orchestrate_book.py not to auto-relaunch
    # (preventing an infinite spawn loop).
    export PODCAST_WATCHDOG=1

    # Stale-running guard: orchestrator crashed while phase_status was "running".
    # --retry-phase clears the stale flag so --resume can proceed.
    if [[ "$STATUS" == "running" ]]; then
        _log "Stale running state detected — using --retry-phase $PHASE"
        "$PYTHON" "$ORCH" --resume "$SLUG" --retry-phase "$PHASE" --skip-doctor 2>&1 | tee -a "$LOG"
    else
        "$PYTHON" "$ORCH" --resume "$SLUG" --skip-doctor 2>&1 | tee -a "$LOG"
    fi

    RC=${PIPESTATUS[0]}
    PHASE="$(_state '.phase')"
    STATUS="$(_state '.phase_status')"
    _log "orchestrator exited rc=$RC · now phase=$PHASE status=$STATUS"

    if _is_done; then
        _log "=== COMPLETE: $SLUG reached $PHASE/$STATUS ==="
        rm -f "$SENTINEL"
        exit 0
    fi

    if _is_human_review_gate; then
        _log "=== HUMAN GATE: $SLUG halted at $PHASE/$STATUS — watchdog pausing. ==="
        _log "Review the series plan, then re-run: bash scripts/podcast/watch_orchestrator.sh $SLUG"
        rm -f "$SENTINEL"
        exit 0
    fi

    if _is_iter_cap_halt; then
        # Bug fix (2026-05-25): per-chapter/failed is an intentional HALT, not a crash.
        # The orchestrator exhausted its 3-iteration convergence cap with unresolved
        # findings. Retrying blindly will reproduce the same finding 20×, burning the
        # watchdog's attempt budget for zero gain. Stop here and tell the user what to do.
        _log "=== ITER-CAP HALT: $SLUG per-chapter/failed — human review required. ==="
        _log "Unresolved finding(s) blocked convergence. Do NOT re-run watchdog without fixing first."
        _log "1. Check: jq '.last_error' $STATE"
        _log "2. Read:  $BOOK_DIR/_system/challenger-report.md (P0 section)"
        _log "3. Fix the P0, then: python3 scripts/podcast/orchestrate_book.py --resume $SLUG --retry-phase per-chapter"
        rm -f "$SENTINEL"
        exit 0
    fi

    if _needs_human_fix; then
        _log_human_fix
        rm -f "$SENTINEL"
        exit 2
    fi

    if [[ "$RC" -eq 1 ]]; then
        # rc=1 = pre-flight failure (see orchestrate_book.py exit code table).
        # Pre-flight exits before changing any state; retrying will fail identically.
        # Common causes: dirty working tree (untracked/modified non-runtime files).
        _log "=== PRE-FLIGHT FAILURE (rc=1): working tree dirty or required config missing. ==="
        _log "Fix the issue (commit or stash untracked/modified files), then re-run:"
        _log "  bash scripts/podcast/watch_orchestrator.sh $SLUG"
        rm -f "$SENTINEL"
        exit 1
    fi

    if [[ "$RC" -eq 0 ]]; then
        # Exit 0 but not in a terminal state means finalize halted for review.
        _log "Orchestrator returned 0 but phase not terminal — checking..."
        if _is_done; then
            rm -f "$SENTINEL"
            exit 0
        fi
    fi

    if [[ "$attempt" -lt "$MAX_RETRIES" ]]; then
        _log "Waiting ${RETRY_DELAY_S}s before retry $((attempt + 1))/$MAX_RETRIES ..."
        sleep "$RETRY_DELAY_S"
    fi
done

_log "=== FATAL: $SLUG did not complete after $MAX_RETRIES attempts. Manual review required. ==="
rm -f "$SENTINEL"
exit 1
