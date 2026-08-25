#!/usr/bin/env python3
"""generate_reader_narration.py — on-demand CLI wrapper for the Compose tab's
"Generate narration" action.

Chapter read-aloud audio (`reader_narration.render_reader_narration`) is
normally produced automatically at the `publish_driver` step, AFTER Asif has
already reviewed and approved a book in the Book Composer — so today there is
no narration to listen to at the one place ("the compose tab is the review
gate") where the review actually happens. This script closes that gap WITHOUT
touching the automatic pipeline flow: it is only ever invoked by a human
action (the Compose tab's "Generate narration" button, via
`plan-dashboard/src/pages/api/studio/narration.ts`), never by the orchestrator,
so Azure-TTS spend only fires when Asif explicitly asks for it.

It is a THIN wrapper — all the real work (chapter splitting, TTS synthesis,
cue timing, manifest bookkeeping, cost-ledger entries) stays in
`reader_narration.render_reader_narration`, the SAME function the publish-time
driver (`phases/reader_narration_driver.py`) calls, so a chapter narrated
before publish and a chapter narrated at publish time can never diverge. This
script only adds process-lifecycle bookkeeping (a status file the Astro
endpoint can poll across a detached spawn) around that one call.

`render_reader_narration` already renders the WHOLE book incrementally — any
chapter whose source text + voice preset has not changed since its last
render is skipped in milliseconds, so a re-run after the first one is cheap.
There is no separate "render one chapter" entry point in the engine (and
adding one would duplicate the chapter-loop / manifest-write logic this
script is explicitly forbidden from re-implementing), so a click on any
chapter's "Generate narration" button narrates every chapter that is not yet
current — the same behavior the publish-time driver already relies on.

Progress is written to `_system/narration-status.json` (state: running | done
| error | skipped) so the Astro endpoint can poll a detached run, mirroring
`rearticulate_chapter.py`'s `_write_status` pattern.

Usage:
    python3 scripts/podcast/generate_reader_narration.py <slug> [--json]
    python3 scripts/podcast/generate_reader_narration.py --book-dir <dir>
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _paths import resolve_content
from reader_narration import render_reader_narration


def _status_path(book_dir: Path) -> Path:
    return book_dir / "_system" / "narration-status.json"


def _write_status(book_dir: Path, payload: dict) -> None:
    path = _status_path(book_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def generate(book_dir: Path, *, log=print) -> dict:
    started = datetime.now(timezone.utc).isoformat()
    # `pid` matters here, not just for record-keeping: the Astro endpoint's
    # status file was already stamped with `state: running` + this process's
    # pid the instant it spawned (so the first poll can never read a stale
    # "done"), and this call overwrites that same file next. Dropping the pid
    # here would make the very next liveness check see a `running` status
    # with no pid, read it as dead, and report "worker exited without a
    # result" while the worker is still very much alive. Mirrors
    # rearticulate_chapter.py's `_write_status` call for the same reason.
    _write_status(book_dir, {"state": "running", "started_at": started, "pid": os.getpid()})
    log(f"reader narration: rendering for {book_dir.name}")

    result = render_reader_narration(book_dir)

    state = "skipped" if result.outcome == "skipped" else "done"
    payload = {
        "state": state,
        "started_at": started,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "rendered": result.rendered,
        "skipped": result.skipped,
        "reason": result.reason,
        "chars": result.chars,
    }
    _write_status(book_dir, payload)
    log(f"reader narration: {state} — rendered {len(result.rendered)}, skipped {len(result.skipped)}")
    return payload


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("slug", nargs="?", help="content slug (resolved via _paths)")
    ap.add_argument("--book-dir", help="explicit book directory (overrides slug)")
    ap.add_argument("--json", action="store_true", help="emit the result as JSON on stdout")
    args = ap.parse_args()

    if args.book_dir:
        book_dir = Path(args.book_dir)
    elif args.slug:
        book_dir = resolve_content(args.slug)
    else:
        ap.error("either <slug> or --book-dir is required")

    log = (lambda *a, **k: None) if args.json else print

    try:
        result = generate(book_dir, log=log)
    except Exception as e:
        payload = {
            "state": "error",
            "error": str(e),
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            _write_status(Path(book_dir), payload)
        except Exception:
            pass
        print(json.dumps({"ok": False, **payload}, ensure_ascii=False))
        return 1

    if args.json:
        print(json.dumps({"ok": True, **result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
