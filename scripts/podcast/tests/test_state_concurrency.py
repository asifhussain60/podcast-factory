"""Concurrent writers must not silently drop each other's results.

The slide-deck cohort runs one chapter per worker thread. Every worker does
read_state -> mutate -> write_state on the SAME orchestrator-state.json. The
write itself is atomic (temp file + rename), which is why this never corrupts
the file — it just loses a verdict, with no error anywhere, which is worse.

These tests exist because the parallel cohort was landed on 2026-07-31 and the
only thing making it safe is the shared lock in `_progress`. If someone removes
that lock the fan-out keeps "working" and starts quietly losing chapters.
"""

from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from _progress import read_state, state_transaction, write_state  # noqa: E402
from _slide_convergence import _record_state  # noqa: E402

CHAPTERS = [f"chapter-{i:02d}" for i in range(24)]


def _seed(tmp_path: Path) -> Path:
    (tmp_path / "_system").mkdir(parents=True, exist_ok=True)
    write_state(tmp_path, {"book_slug": "test-book", "phases": {}})
    return tmp_path


def test_every_concurrent_chapter_verdict_survives(tmp_path: Path) -> None:
    """The real failure mode: N workers finish close together, each writes from a
    snapshot taken before its neighbours landed, and the last write wins."""
    book_dir = _seed(tmp_path)

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(
            pool.map(
                lambda slug: _record_state(book_dir, slug, phase_status="done", iterations=1, verdict="SHIP-READY"),
                CHAPTERS,
            )
        )

    recorded = (read_state(book_dir) or {}).get("slide_decks") or {}
    assert set(recorded) == set(CHAPTERS), f"lost {set(CHAPTERS) - set(recorded)}"
    assert all(v["slide_challenger_verdict"] == "SHIP-READY" for v in recorded.values())


def test_concurrent_writers_never_leave_the_state_file_unparseable(tmp_path: Path) -> None:
    book_dir = _seed(tmp_path)

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(
            pool.map(
                lambda slug: _record_state(book_dir, slug, phase_status="running", iterations=2, verdict="(x)"),
                CHAPTERS,
            )
        )

    raw = (book_dir / "_system" / "orchestrator-state.json").read_text(encoding="utf-8")
    assert json.loads(raw)["slide_decks"]


def test_the_lock_is_reentrant(tmp_path: Path) -> None:
    """update_phase() can be called from inside a caller that already holds the
    lock. A plain Lock would deadlock the cohort loop on its first chapter."""
    book_dir = _seed(tmp_path)
    with state_transaction():
        with state_transaction():
            _record_state(book_dir, "nested", phase_status="done", iterations=1, verdict="SHIP-READY")
    assert (read_state(book_dir) or {})["slide_decks"]["nested"]["slide_challenger_verdict"] == "SHIP-READY"


def test_an_unrelated_key_written_by_another_thread_is_not_clobbered(tmp_path: Path) -> None:
    """Workers touch `slide_decks`; the main thread touches the phase block. Both
    read the whole document, so an unguarded interleave loses whichever landed
    first regardless of which key each was aiming at."""
    book_dir = _seed(tmp_path)

    def _phase_writer(n: int) -> None:
        with state_transaction():
            state = read_state(book_dir) or {}
            state.setdefault("phases", {})[f"phase-{n}"] = {"status": "completed"}
            write_state(book_dir, state)

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [
            pool.submit(_record_state, book_dir, s, phase_status="done", iterations=1, verdict="OK") for s in CHAPTERS
        ]
        futures += [pool.submit(_phase_writer, n) for n in range(24)]
        for f in futures:
            f.result()

    state = read_state(book_dir) or {}
    assert len(state.get("slide_decks") or {}) == len(CHAPTERS)
    assert len([k for k in (state.get("phases") or {}) if k.startswith("phase-")]) == 24
