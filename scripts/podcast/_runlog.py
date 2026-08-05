#!/usr/bin/env python3
"""_runlog.py — run-correlated structured event log for the orchestrator.

Extracted verbatim from ``_progress.py`` (DR-005 gate, 2026-07-31): the run-log
block pushed that module to 642 lines, past the 600-line limit. ADR 0001 had
placed it in ``_progress.py`` as "already the state/observability module"; the
gate is right and the ADR is amended (see [A5] there). Behaviour unchanged, and
every name stays importable from ``_progress`` via re-export.

state.json is the CHECKPOINT (where a run is now); this is the NARRATIVE (what
happened, in order). They are joined by ``run_id``. See docs/adr/0001-*.md.

Nothing here may raise into the pipeline: a broken log must never turn a working
phase into a failed one. Every public entry point is individually wrapped.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ─── Run-correlated structured event log ──────────────────────────────────────
# A complement to the state file, not a competitor: state.json is the CHECKPOINT
# (where the run is now), the run JSONL is the NARRATIVE (what happened, in
# order). They are joined by `run_id`.
#
# Lives under _workspace/runs/<slug>/<run_id>.jsonl — NOT under the book's
# _system/, because _system/ is tracked in git (cost-ledger.jsonl et al. are
# committed) and per-run logs on every book branch would be merge noise and
# repo bloat. _workspace/runs/ is already reserved and gitignored.

RUN_LOG_RETENTION = 10  # runs kept per book; the newest failed run is never pruned
RUN_LOG_TAIL_CHARS = 800  # bound on stdout/stderr excerpts inside an event

_RUN: dict[str, Any] = {"run_id": None, "slug": None, "path": None}


def mint_run_id() -> str:
    """A sortable, collision-resistant id for one orchestrator process."""
    import secrets

    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(3)


def current_run_id() -> str | None:
    return _RUN["run_id"]


def run_log_path() -> Path | None:
    return _RUN["path"]


def reset_run_log() -> None:
    """Drop the process-wide run context. For tests."""
    _RUN.update({"run_id": None, "slug": None, "path": None})


def runs_dir(slug: str) -> Path:
    try:
        from _paths import REPO_ROOT as _root
    except Exception:
        _root = Path(__file__).resolve().parents[2]
    return Path(_root) / "_workspace" / "runs" / (slug or "_unknown")


def tail(text: Any, limit: int = RUN_LOG_TAIL_CHARS) -> str:
    """Bounded excerpt of a stream. Full evidence lives in the failure sidecar."""
    if not text:
        return ""
    if isinstance(text, bytes):
        text = text.decode("utf-8", "replace")
    text = str(text)
    if len(text) <= limit:
        return text
    return "…[truncated]…" + text[-limit:]


def run_log_enabled(book_dir: Path | None) -> bool:
    """Whether this process should keep a run log.

    ``PODCAST_RUN_LOG=1|0`` forces it on/off. Otherwise it engages only for a
    book that actually lives under the repo's content root — so the ~170 unit
    tests that drive update_phase against temp directories never write into a
    developer's real _workspace/runs/.
    """
    flag = os.environ.get("PODCAST_RUN_LOG", "").strip().lower()
    if flag in ("0", "off", "false", "no"):
        return False
    if flag in ("1", "on", "true", "yes"):
        return True
    if book_dir is None:
        return False
    try:
        from _paths import CONTENT_ROOT

        Path(book_dir).resolve().relative_to(Path(CONTENT_ROOT).resolve())
        return True
    except Exception:
        return False


def init_run_log(book_dir: Path | None, *, slug: str | None = None, run_id: str | None = None) -> str | None:
    """Open the run log for this process. Idempotent; never raises.

    Returns the run id, or None if no log could be opened (in which case
    log_event degrades to a no-op and the pipeline is unaffected).
    """
    if _RUN["run_id"]:
        return _RUN["run_id"]
    if not run_log_enabled(book_dir):
        return None
    try:
        if not slug and book_dir is not None:
            # Lazy: _progress imports this module, so a top-level import here
            # would close the cycle.
            from _progress import read_state

            state = read_state(Path(book_dir))
            slug = (state or {}).get("book_slug")
        if not slug and book_dir is not None:
            slug = Path(book_dir).name
        if not slug:
            return None
        rid = run_id or mint_run_id()
        d = runs_dir(slug)
        d.mkdir(parents=True, exist_ok=True)
        _RUN.update({"run_id": rid, "slug": slug, "path": d / f"{rid}.jsonl"})
        _prune_runs(d)
        return rid
    except Exception as e:  # observability must never break the pipeline
        sys.stderr.write(f"[init_run_log] disabled: {e!r}\n")
        return None


def _prune_runs(d: Path) -> None:
    """Keep the newest RUN_LOG_RETENTION runs, plus the newest failed run.

    A failed run's log is worth more than several clean ones, so recency alone
    is the wrong eviction key.
    """
    try:
        logs = sorted((p for p in d.glob("*.jsonl")), reverse=True)
        doomed = logs[RUN_LOG_RETENTION:]
        for p in doomed:
            try:
                if '"level": "error"' in p.read_text(encoding="utf-8", errors="replace"):
                    doomed = [x for x in doomed if x is not p]
                    break  # newest failed run — keep it and stop searching
            except OSError:
                pass
        for p in doomed:
            p.unlink(missing_ok=True)
            for side in d.glob(f"{p.stem}.*.failure.txt"):
                side.unlink(missing_ok=True)
    except Exception:
        pass


def log_event(
    event: str,
    *,
    book_dir: Path | None = None,
    level: str = "info",
    phase: str | None = None,
    chapter: str | None = None,
    slug: str | None = None,
    msg: str = "",
    **fields: Any,
) -> None:
    """Append one structured event to the run timeline. NEVER raises.

    Unknown keyword fields land in the record verbatim, so callers can attach
    rc / duration_ms / tokens / artifacts without this signature growing.
    """
    try:
        if not _RUN["run_id"]:
            if init_run_log(book_dir, slug=slug) is None:
                return  # no-op before init / when the book is unknown
        path = _RUN["path"]
        if path is None:
            return
        record = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "run_id": _RUN["run_id"],
            "book_slug": slug or _RUN["slug"],
            "phase": phase,
            "chapter": chapter,
            "event": event,
            "level": level if level in ("debug", "info", "warn", "error") else "info",
            "msg": msg,
        }
        record.update(fields)
        with Path(path).open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        sys.stderr.write(f"[log_event] dropped {event!r}: {e!r}\n")


def read_run_events(limit: int | None = None) -> list[dict[str, Any]]:
    """Read back this run's events (oldest first). Returns [] on any problem."""
    try:
        path = _RUN["path"]
        if not path or not Path(path).exists():
            return []
        rows = []
        for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return rows[-limit:] if limit else rows
    except Exception:
        return []


def write_failure_dump(book_dir: Path, state: dict[str, Any], *, last_events: int = 25) -> Path | None:
    """Write _system/last-failure.md — the one file to read after a failed run.

    Cross-references what previously took four artifacts: the failing phase and
    its error, the last LLM call with its return code and output excerpt, the
    tail of the run timeline, and the exact command to continue.
    """
    try:
        slug = state.get("book_slug") or Path(book_dir).name
        phase = state.get("phase") or "(unknown)"
        status = state.get("phase_status") or "(unknown)"
        err = state.get("last_error") or {}
        events = read_run_events()
        llm = [e for e in events if str(e.get("event", "")).startswith("claude_p.")]
        last_llm = llm[-1] if llm else None

        out = [
            f"# Last failure — {slug}",
            "",
            f"- **Phase:** `{phase}`  ·  **Status:** `{status}`",
            f"- **Run id:** `{state.get('run_id') or current_run_id() or '(none)'}`",
            f"- **When:** {err.get('ts') or state.get('ts_updated') or '(unknown)'}",
            f"- **Timeline:** `{run_log_path() or '(no run log)'}`",
            "",
            "## Error",
            "",
            "```",
            str(err.get("message") or "(no last_error recorded)").strip(),
            "```",
            "",
        ]

        out += ["## Last LLM call", ""]
        if last_llm:
            out += [
                f"- **Event:** `{last_llm.get('event')}`  ·  **rc:** `{last_llm.get('rc')}`"
                f"  ·  **duration:** {last_llm.get('duration_ms', '?')} ms",
                f"- **Phase/step:** `{last_llm.get('phase')}` / `{last_llm.get('step')}`",
                f"- **Model:** `{last_llm.get('model')}`"
                f"  ·  **tokens in/out:** {last_llm.get('tokens_in', '?')}/{last_llm.get('tokens_out', '?')}",
            ]
            if last_llm.get("prompt_dump"):
                out += [f"- **Full prompt + output:** `{last_llm['prompt_dump']}`"]
            for key, label in (("stdout_tail", "stdout (tail)"), ("stderr_tail", "stderr (tail)")):
                if last_llm.get(key):
                    out += ["", f"**{label}:**", "", "```", str(last_llm[key]).strip(), "```"]
        else:
            out += ["_No LLM call recorded in this run._"]
        out += [""]

        out += ["## Timeline (last events)", "", "```"]
        for e in events[-last_events:]:
            bits = f"{e.get('ts', '')}  [{e.get('level', '')}] {e.get('event', '')}"
            if e.get("phase"):
                bits += f"  phase={e['phase']}"
            if e.get("chapter"):
                bits += f"  chapter={e['chapter']}"
            if e.get("rc") is not None:
                bits += f"  rc={e['rc']}"
            if e.get("msg"):
                bits += f"  — {str(e['msg'])[:160]}"
            out.append(bits)
        if not events:
            out.append("(no events recorded)")
        out += ["```", ""]

        out += [
            "## Continue",
            "",
            "```bash",
            f"python3 scripts/podcast/orchestrate_book.py --resume {slug} --retry-phase {phase}",
            "```",
            "",
        ]

        p = Path(book_dir) / "_system" / "last-failure.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("\n".join(out), encoding="utf-8")
        return p
    except Exception as e:
        sys.stderr.write(f"[write_failure_dump] skipped: {e!r}\n")
        return None
