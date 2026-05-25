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
PYTHON=/usr/bin/python3
ORCH="$REPO_ROOT/scripts/podcast/orchestrate_book.py"
STATE="$REPO_ROOT/content/drafts/$SLUG/_system/orchestrator-state.json"
SENTINEL="$REPO_ROOT/content/drafts/$SLUG/_system/watchdog.json"
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

# ── Helper: are we done? ──────────────────────────────────────────────────────
_is_done() {
    local phase status
    phase="$(_state '.phase')"
    status="$(_state '.phase_status')"
    if [[ "$phase" == "done" ]]; then return 0; fi
    if [[ "$phase" == "finalize" && "$status" == "halted" ]]; then return 0; fi
    return 1
}

# ── Short-circuit if already done ─────────────────────────────────────────────
if _is_done; then
    _log "Already complete (phase=$(_state '.phase') status=$(_state '.phase_status')) — nothing to do."
    rm -f "$SENTINEL"
    exit 0
fi

# ── Main loop ─────────────────────────────────────────────────────────────────
for attempt in $(seq 1 "$MAX_RETRIES"); do
    PHASE="$(_state '.phase')"
    STATUS="$(_state '.phase_status')"

    _log "--- attempt $attempt/$MAX_RETRIES · phase=$PHASE · status=$STATUS ---"

    # PODCAST_WATCHDOG=1 tells orchestrate_book.py not to auto-relaunch
    # (preventing an infinite spawn loop).
    export PODCAST_WATCHDOG=1

    # Stale-running guard: orchestrator crashed while phase_status was "running".
    # --retry-phase clears the stale flag so --resume can proceed.
    if [[ "$STATUS" == "running" ]]; then
        _log "Stale running state detected — using --retry-phase $PHASE"
        "$PYTHON" "$ORCH" --resume "$SLUG" --retry-phase "$PHASE" 2>&1 | tee -a "$LOG"
    else
        "$PYTHON" "$ORCH" --resume "$SLUG" 2>&1 | tee -a "$LOG"
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
