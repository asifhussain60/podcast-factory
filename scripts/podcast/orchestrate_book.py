#!/usr/bin/env python3
"""orchestrate_book.py — Autonomous book-to-NotebookLM pipeline driver (Phase A + B + C).

PURPOSE

  Deterministic Python driver for the `podcast-orchestrator` agent. v2 plan
  shipped Phases A + B + C in a single coherent landing (see
  docs/architecture/index.html#phases):

    Phase A · Driver pre-flight → Phase 0a (Azure ingest)
    Phase B · Per-chapter convergence loop (3 outer × 5 inner = 15 max)
    Phase C · Trainer invocation (substrate-driven, regression-gated)

  Pipeline (initial run):
    pre-flight → branch → scaffold → 0a (Azure) → 0b (English refinement) →
    0c (phonetic pass) → 0d (chapter design) → 0e (enrichment) →
    0f-halt (writes series-plan.md, exits for human review)

  Pipeline (--resume after Phase 0f approval):
    per-chapter (extract → frame → build → converge) → 0g (register) →
    trainer (substrate-driven) → merge book/<slug> → develop → done

  Phase 0b–0e LLM authoring shells out to `claude -p` via `_authoring.py`
  with phase-specific prompts. Each phase asserts a non-empty output
  artifact; failure halts the orchestrator with a manual-fallback message
  the human can follow via the conversational `/podcast` skill, then
  `--resume` picks up at the next deterministic checkpoint.

  State lives in `<BOOK_DIR>/_system/orchestrator-state.json` (atomic
  tmpfile + rename). `--status <slug>` renders it without modification.
  `--resume <slug>` reads it and advances from `last_completed_phase`.

USAGE

  orchestrate-book initial:
    python3 scripts/podcast/orchestrate_book.py <pdf-path> [--slug SLUG]
        [--category books|articles|...]  [--title "Book Title"]
        [--author "Author Name"]

  orchestrate-book resume:
    python3 scripts/podcast/orchestrate_book.py --resume <book-slug>

  orchestrate-book status:
    python3 scripts/podcast/orchestrate_book.py --status <book-slug>

EXIT CODES

  0   — phase completed successfully (book at next checkpoint or all done)
  1   — pre-flight failed (refuse-with-fix-command path)
  2   — runtime error during a phase (state.json carries the details)
  3   — halted at LLM-authoring boundary; manual --resume after /podcast

DOES NOT MODIFY anything outside `_workspace/<category>/<slug>/`
and `_workspace/Books/`. Git operations are limited to the active book
branch; never pushes to main; never force-pushes.

ARCHITECTURE NOTE (A4 split)

  Phase logic extracted to scripts/podcast/phases/:
    phases/preflight.py      — pre-flight gates (initial + resume)
    phases/scaffold.py       — branch, scaffold, ingest, git-commit
    phases/series_plan.py    — series-plan template + 0f write + 0g register
    phases/bundle_audit.py   — dual-auditor bundle sweep (0g)
    phases/per_chapter.py    — per_chapter_pass (extract→frame→build→converge)
    phases/chapter_driver.py — _drive_per_chapter_and_after loop + finalize
    phases/publish_driver.py — _drive_publish_through_done (publish→trainer→merge)
    phases/merge.py          — phase_merge_to_develop
    phases/initial_driver.py — run_initial + _drive_authoring_through_0f
    phases/resume_dispatcher.py — run_resume state-machine dispatcher

  This module retains: locking, status, argument parsing, main() entry point,
  and re-exports for backward compat with any external callers.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Local imports (these live next to this script).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _progress import (  # noqa: E402
    ORCHESTRATOR_VERSION,
    initial_state,
    read_state,
    render_status,
    update_phase,
    write_state,
)
from _authoring import (  # noqa: E402
    AuthoringError,
    author_phase_0b,
    author_phase_0c,
    author_phase_0d,
    author_phase_0e,
    author_framing,
    invoke_trainer,
)
from _convergence import (  # noqa: E402
    MAX_OUTER_ITERATIONS,
    ChapterOutcome,
    converge_chapter,
    render_outcome,
)
from _paths import REPO_ROOT, content_dir as _paths_content_dir, find_content as _paths_find_content, relative_to_repo as _paths_rel  # noqa: E402
from _rules import ALLOWED_CATEGORIES  # noqa: E402

# ─── Re-exports from extracted phase modules (backward compat + test mocking) ─
# Callers that do `from orchestrate_book import phase_git_commit` continue to
# work.  Tests that mock.patch.object(orchestrate_book, "phase_git_commit", …)
# still intercept calls made from functions defined IN this module.
from phases.preflight import (  # noqa: F401,E402
    _in_preflight_artifacts_mode,
    preflight_initial,
    preflight_resume,
    _run_chapter_set_check,
    _sweep_orphan_episode_drafts,
)
from phases.scaffold import (  # noqa: F401,E402
    phase_branch,
    phase_scaffold,
    phase_0a_ingest,
    phase_git_commit,
)
from phases.series_plan import (  # noqa: F401,E402
    SERIES_PLAN_TEMPLATE,
    phase_0f_write_series_plan,
    _resolve_episode_id,
    _series_numeric,
    _series_flag,
    _chapter_cost_so_far,
    phase_0g_register,
)
from phases.bundle_audit import (  # noqa: F401,E402
    _gemini_key_available,
    phase_0g_audit_bundles,
)
from phases.per_chapter import per_chapter_pass  # noqa: F401,E402
from phases.merge import phase_merge_to_develop  # noqa: F401,E402
from phases.chapter_driver import _drive_per_chapter_and_after  # noqa: F401,E402
from phases.publish_driver import _drive_publish_through_done  # noqa: F401,E402
from phases.initial_driver import run_initial, _drive_authoring_through_0f  # noqa: F401,E402

# Canonical phase order — used by run_resume and pinned by regression test.
CANONICAL_PHASES: tuple[str, ...] = (
    "pre-flight", "branch", "scaffold",
    "0a", "0b", "0c", "0d", "0e", "0f", "0g",
    "per-chapter", "per-chapter-slides",
    "finalize", "publish", "trainer", "merge", "done",
)

# 2026-05-26 restructure: canonical layout is content/<stage>/<category>/<slug>/
LIBRARY_ROOT = REPO_ROOT / "content" / "drafts"
SCAFFOLD_SCRIPT = REPO_ROOT / "scripts" / "podcast" / "scaffold_book.py"
INGEST_SCRIPT = REPO_ROOT / "scripts" / "podcast" / "ingest_source.py"
EXTRACT_SCRIPT = REPO_ROOT / "scripts" / "podcast" / "extract_chapter.py"
BUILD_SCRIPT = REPO_ROOT / "scripts" / "podcast" / "build_episode_txt.py"
AZURE_PROBE = REPO_ROOT / "scripts" / "podcast" / "test_azure_connectivity.py"
CHAPTER_SET_SCRIPT = REPO_ROOT / "scripts" / "podcast" / "check_chapter_set.py"
AUDIT_BUNDLE_SCRIPT = REPO_ROOT / "scripts" / "podcast" / "audit_bundle.py"
AUDIT_BUNDLE_GEMINI_SCRIPT = REPO_ROOT / "scripts" / "podcast" / "audit_bundle_gemini.py"
LOCKS_DIR = Path.home() / ".podcast-locks"
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# phased_rollout is always on — large LLM-spend committed only after human
# approval at each phase boundary (0f halt + finalize halt).
PHASED_ROLLOUT_ENABLED: bool = True


# ─── Phased-rollout boundary gate ─────────────────────────────────────────────


def _phase_boundary_gate(
    book_dir: Path,
    boundary_name: str,
    projected_cost_usd: float | None = None,
) -> None:
    """Log a phase boundary crossing for the phased_rollout audit trail."""
    _info(
        f"[phased_rollout] phase boundary: {boundary_name}"
        + (f" (projected cost: ${projected_cost_usd:.2f})" if projected_cost_usd else "")
    )


# ─── tiny utilities ──────────────────────────────────────────────────────────


def _run(cmd: list[str], *, cwd: Path | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def _git(*args: str) -> tuple[int, str, str]:
    return _run(["git", *args], cwd=REPO_ROOT)


def _err(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)


def _info(msg: str) -> None:
    print(msg)


def _resolve_book_path(category: str, slug: str) -> Path:
    """Return the canonical drafts path for a piece of content."""
    return _paths_content_dir(slug, stage="drafts", category=category)


def _book_dir(book_slug: str) -> Path | None:
    """Locate <slug> across all stage/category combos. Returns the directory or None."""
    found = _paths_find_content(book_slug)
    return found[2] if found else None


def derive_slug(pdf_path: Path) -> str:
    """Stem of the PDF, lowercased, non-alphanumeric → hyphen, collapsed."""
    stem = pdf_path.stem.lower()
    s = re.sub(r"[^a-z0-9]+", "-", stem).strip("-")
    return re.sub(r"-+", "-", s)


# ─── Lock management (G3 cohesion fix 2026-05-23) ────────────────────────────


def _is_pid_alive(pid: int) -> bool:
    """Probe whether `pid` is a live process via signal-0."""
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError, OSError):
        return False
    return True


def _acquire_book_lock(book_slug: str) -> tuple[int, Path] | None:
    """Acquire an exclusive fcntl lock for this book. Returns (fd, path) or None."""
    LOCKS_DIR.mkdir(parents=True, exist_ok=True)
    lock_path = LOCKS_DIR / f"{book_slug}.lock"

    def _try_acquire() -> int | None:
        fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, BlockingIOError):
            os.close(fd)
            return None
        os.ftruncate(fd, 0)
        body = (
            f"pid: {os.getpid()}\n"
            f"started_at: {datetime.now(timezone.utc).isoformat(timespec='seconds')}\n"
            f"book_slug: {book_slug}\n"
        )
        os.write(fd, body.encode("utf-8"))
        os.fsync(fd)
        return fd

    fd = _try_acquire()
    if fd is not None:
        return fd, lock_path

    try:
        existing = lock_path.read_text(encoding="utf-8")
    except OSError:
        existing = ""
    existing_pid: int | None = None
    for ln in existing.splitlines():
        if ln.startswith("pid:"):
            try:
                existing_pid = int(ln.split(":", 1)[1].strip())
            except ValueError:
                existing_pid = None
            break

    if existing_pid and _is_pid_alive(existing_pid):
        _err(f"book {book_slug!r} is already locked by another orchestrator process:")
        for ln in existing.splitlines():
            _err(f"  {ln}")
        _err(f"  lockfile: {lock_path}")
        _err("  if you're sure the other process is dead, delete the lockfile and re-run.")
        return None

    _info(f"  · cleaning up stale lockfile (PID {existing_pid} not alive): {lock_path.name}")
    try:
        lock_path.unlink()
    except OSError:
        pass
    fd = _try_acquire()
    if fd is None:
        _err(f"failed to acquire lock for {book_slug!r} after stale-cleanup")
        return None
    return fd, lock_path


def _release_book_lock(lock_fd: int, lock_path: Path) -> None:
    """Release the fcntl lock and remove the lockfile."""
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
    except OSError:
        pass
    try:
        os.close(lock_fd)
    except OSError:
        pass
    try:
        lock_path.unlink()
    except OSError:
        pass


# ─── Misc helpers ─────────────────────────────────────────────────────────────


def _read_book_title(book_dir: Path) -> str | None:
    """Best-effort title extraction from BOOK_DIR/_README.md."""
    readme = book_dir / "_README.md"
    if not readme.exists():
        return None
    for line in readme.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("# Podcast — "):
            return line[len("# Podcast — "):].strip()
    return None


def run_status(args: argparse.Namespace) -> int:
    slug = args.status
    book_dir = _book_dir(slug)
    if book_dir is None:
        _err(f"no library directory matches book-slug {slug!r}")
        return 1
    state = read_state(book_dir)
    if state is None:
        _err(
            f"no orchestrator state at "
            f"{(book_dir / '_system' / 'orchestrator-state.json').relative_to(REPO_ROOT)}"
        )
        return 1
    print(render_status(state))
    return 0


# ─── CLI ─────────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="orchestrate-book",
        description="Autonomous book-to-NotebookLM pipeline driver (Phase A + B + C).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  Initial:  orchestrate-book _workspace/Books/foo.pdf --slug foo --category books\n"
            "  Resume:   orchestrate-book --resume foo\n"
            "  Status:   orchestrate-book --status foo\n"
        ),
    )
    p.add_argument("pdf_path", nargs="?",
                   help="path to the source PDF (initial run only)")
    p.add_argument("--slug",
                   help="book slug (default: derived from PDF filename)")
    p.add_argument("--category", default="books",
                   choices=ALLOWED_CATEGORIES,
                   help="library subdirectory (default: books)")
    p.add_argument("--title",
                   help='book title (default: derived from PDF filename)')
    p.add_argument("--author", default=None,
                   help="book author (optional)")
    p.add_argument("--resume", metavar="SLUG",
                   help="resume an orchestrator run for the named book slug")
    p.add_argument("--status", metavar="SLUG",
                   help="render the current state for the named book slug")
    p.add_argument("--retry-phase", metavar="PHASE_ID", default=None,
                   help=(
                       "(used with --resume) reset the named phase's status to 'pending' "
                       "and re-run it. Example: --resume foo --retry-phase 0b"
                   ))
    p.add_argument("--length-tier", default="extended",
                   choices=("default_deep_dive", "longer", "extended"),
                   help=(
                       "target episode length tier (initial run only; persisted in state). "
                       "Default: extended."
                   ))
    p.add_argument("--unit-mode", default="auto",
                   choices=("chapter", "section", "auto"),
                   help=(
                       "Phase 0d episode segmentation (initial run only; persisted in state). "
                       "Default: auto."
                   ))
    p.add_argument("--version", action="version",
                   version=f"orchestrate_book.py v{ORCHESTRATOR_VERSION}")
    return p


def _maybe_relaunch_under_watchdog(slug: str) -> None:
    """Auto-spawn watch_orchestrator.sh when --resume is called without it."""
    if os.environ.get("PODCAST_WATCHDOG"):
        return

    watchdog = Path(__file__).resolve().parent / "watch_orchestrator.sh"
    if not watchdog.exists():
        _err("watch_orchestrator.sh not found — running WITHOUT self-healing watchdog")
        return

    log_dir = Path(__file__).resolve().parents[2] / "_workspace" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"orchestrator-{slug}.log"

    print(f"  [watchdog] auto-spawning watch_orchestrator.sh for {slug}")
    print(f"  [watchdog] log: {log_path}")
    print(f"  [watchdog] this process exits; watchdog owns the run from here.")

    with open(log_path, "a") as log_fh:
        subprocess.Popen(
            ["/bin/bash", str(watchdog), slug],
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    sys.exit(0)


def main() -> int:
    args = build_parser().parse_args()

    if args.status:
        return run_status(args)

    if args.resume:
        slug_for_lock = args.resume
    elif args.pdf_path:
        slug_for_lock = args.slug or derive_slug(Path(args.pdf_path).resolve())
    else:
        _err("either <pdf-path> (initial) or --resume <slug> or --status <slug> is required")
        return 1

    if args.resume:
        _maybe_relaunch_under_watchdog(slug_for_lock)

    lock_result = _acquire_book_lock(slug_for_lock)
    if lock_result is None:
        return 4
    lock_fd, lock_path = lock_result
    try:
        if args.resume:
            from phases.resume_dispatcher import run_resume
            return run_resume(args)
        from phases.initial_driver import run_initial
        return run_initial(args)
    finally:
        _release_book_lock(lock_fd, lock_path)


if __name__ == "__main__":
    sys.exit(main())
