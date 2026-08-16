"""Run the Arabic-and-citations apparatus pass for a Sessions-lane book.

`sessions-apparatus` is the last step in `ingest.LANE_STEPS` and carries its own
status field, but nothing in this package has ever called it — `ingest.py`'s own
docstring says the apparatus "runs standalone... after" articulation, and the
only code that performs it is `_book_apparatus.apply_book_apparatus`, which the
regular orchestrated-book pipeline calls internally as its own compose tail.
Found 2026-08-12 while planning the finish line for Surah Al-Fateha: the step
existed as a name and a status field with no driver behind it, which is exactly
the `sessions-articulate` gap ("a step name with no code behind it") one layer
further down the lane.

ONE DEFINITION, reused rather than reimplemented: this module calls
`apply_book_apparatus` (the same tail every other book route runs) and
`ingest._write_state` (the same state writer `ingest.py` already uses), so the
apparatus's own house-style/Arabic/vowelling logic and the lane's own state
schema each stay defined in exactly one place.

ORDER IS FORCED. This must run AFTER read-along finishes, never before: the
apparatus vowels, cites and glossary-annotates whatever prose is on the page at
the moment it runs, and both articulation and the read-along corrector rewrite
that prose (the latter for spoken chapters only, added 2026-08-15). Running
apparatus first would mean a later prose pass immediately invalidates marks the
apparatus just placed. `run_apparatus` refuses to run while `sessions-read-along`
is not `completed`, rather than silently apparatus-ing a half-corrected book.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _book_apparatus import apply_book_apparatus  # noqa: E402
from _paths import content_dir  # noqa: E402

from sessions.ingest import LANE_STEPS, READ_ALONG_STEP, _write_state  # noqa: E402
from sessions.series import PROFILE, SERIES  # noqa: E402


def run_apparatus(slug: str, *, force: bool = False, log=print) -> dict:
    """Run the apparatus pass over a Sessions book's composed book.md.

    Refuses (rather than running against half-finished prose) unless
    `sessions-read-along` already reports `completed` in orchestrator-state.json,
    or `force` is passed to override that check.
    """
    series = SERIES[slug]
    book_dir = content_dir(slug, profile=PROFILE)
    state_path = book_dir / "_system" / "orchestrator-state.json"

    if not force:
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            return {"ran": False, "reason": f"could not read orchestrator-state.json: {exc}"}
        read_along_status = ((state.get("phases") or {}).get(READ_ALONG_STEP) or {}).get("status")
        if read_along_status != "completed":
            log(
                f"  apparatus: refusing — sessions-read-along is {read_along_status!r}, not completed. "
                "Run read_along.py to the end first, or pass --force to override."
            )
            return {"ran": False, "reason": f"sessions-read-along status is {read_along_status!r}"}

    apply_book_apparatus(book_dir, log=log)
    _write_state(book_dir, series, done_through=LANE_STEPS[-1])
    log(f"  apparatus: done — orchestrator-state.json now reports through {LANE_STEPS[-1]!r}")
    return {"ran": True}


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Run the apparatus pass for a Sessions-lane book.")
    parser.add_argument("slug", choices=sorted(SERIES))
    parser.add_argument("--force", action="store_true", help="run even if sessions-articulate is not completed")
    args = parser.parse_args(argv)

    result = run_apparatus(args.slug, force=args.force)
    if not result.get("ran"):
        print(f"apparatus: not run — {result.get('reason')}")
        return 1
    print("apparatus: done")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
