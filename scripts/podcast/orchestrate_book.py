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

DOES NOT MODIFY anything outside `content/drafts/<category>/<slug>/`
(the source PDF is supplied as an arbitrary path arg and copied in). Git
operations are limited to the active book branch; never pushes to main;
never force-pushes.

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
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


# ── Interpreter self-heal (Setup stage, part 1) ──────────────────────────────
# MUST run before the yaml-dependent local imports below. The system python3
# (and pyenv shims) frequently lack PyYAML/anthropic/requests, which crashes the
# whole pipeline at `import yaml` deep inside a phase module — with the watchdog
# then mis-reporting it as "working tree dirty". If the active interpreter can't
# import yaml, transparently re-exec under the repo virtualenv (.venv), which is
# provisioned with every dependency. Idempotent: a sentinel env var prevents an
# exec loop, and a missing/incomplete venv surfaces an actionable message.
def _ensure_capable_interpreter() -> None:
    try:
        import yaml  # noqa: F401

        return
    except ImportError:
        pass
    if os.environ.get("_PODCAST_REEXECED") == "1":
        sys.stderr.write(
            "FATAL: PyYAML is not importable under this interpreter:\n"
            f"    {sys.executable}\n"
            "  The repo virtualenv is missing or incomplete. Fix:\n"
            "    python3 -m venv .venv && .venv/bin/pip install -r requirements.txt\n"
        )
        raise SystemExit(1)
    repo_root = Path(__file__).resolve().parents[2]
    venv_py = repo_root / ".venv" / "bin" / "python"
    if venv_py.exists() and venv_py.resolve() != Path(sys.executable).resolve():
        os.environ["_PODCAST_REEXECED"] = "1"
        sys.stderr.write(f"  [setup] re-executing under repo venv: {venv_py}\n")
        os.execv(str(venv_py), [str(venv_py), str(Path(__file__).resolve()), *sys.argv[1:]])
    sys.stderr.write(
        "FATAL: PyYAML is not importable and no usable .venv was found.\n"
        "  Fix: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt\n"
    )
    raise SystemExit(1)


_ensure_capable_interpreter()

# Local imports (these live next to this script).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import REPO_ROOT
from _paths import content_dir as _paths_content_dir
from _paths import find_content as _paths_find_content
from _progress import (
    ORCHESTRATOR_VERSION,
    PHASES,
    read_state,
    render_status,
)
from _rules import ALLOWED_CATEGORIES

# ─── Re-exports from extracted phase modules (backward compat + test mocking) ─
# Callers that do `from orchestrate_book import phase_git_commit` continue to
# work.  Tests that mock.patch.object(orchestrate_book, "phase_git_commit", …)
# still intercept calls made from functions defined IN this module.

# Canonical phase order — used by run_resume and pinned by regression test.
# Single source of truth lives in _progress.PHASES — alias it here so existing
# references keep working without maintaining a parallel (drift-prone) copy.
CANONICAL_PHASES: tuple[str, ...] = PHASES

# Canonical layout is content/<Bucket>/<slug>/ — resolved through _paths, never
# by joining a root here. (The old LIBRARY_ROOT = content/drafts constant was
# unreferenced and named a tree the type-first migration emptied.)
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


def _run(cmd: list[str], *, cwd: Path | None = None, timeout: int = 120) -> tuple[int, str, str]:
    """Run a short, bounded command (git, etc.). NOT for long-running LLM phases —
    those are driven by run_wave/chapter_driver and supervised by the watchdog.
    On timeout, returns a non-zero rc + stderr instead of hanging forever.
    """
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        return 124, (e.stdout or ""), (f"{(e.stderr or '')}\ncommand timed out after {timeout}s: {' '.join(cmd)}")
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
            return line[len("# Podcast — ") :].strip()
    return None


def run_status(args: argparse.Namespace) -> int:
    slug = args.status
    book_dir = _book_dir(slug)
    if book_dir is None:
        _err(f"no library directory matches book-slug {slug!r}")
        return 1
    state = read_state(book_dir)
    if state is None:
        _err(f"no orchestrator state at {(book_dir / '_system' / 'orchestrator-state.json').relative_to(REPO_ROOT)}")
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
            "  Initial:  orchestrate-book path/to/foo.pdf --slug foo --category books\n"
            "  Resume:   orchestrate-book --resume foo\n"
            "  Status:   orchestrate-book --status foo\n"
        ),
    )
    p.add_argument("pdf_path", nargs="?", help="path to the source PDF (initial run only)")
    p.add_argument("--slug", help="book slug (default: derived from PDF filename)")
    p.add_argument(
        "--category", default="books", choices=ALLOWED_CATEGORIES, help="library subdirectory (default: books)"
    )
    p.add_argument("--title", help="book title (default: derived from PDF filename)")
    p.add_argument("--author", default=None, help="book author (optional)")
    p.add_argument("--resume", metavar="SLUG", help="resume an orchestrator run for the named book slug")
    p.add_argument("--status", metavar="SLUG", help="render the current state for the named book slug")
    p.add_argument(
        "--retry-phase",
        metavar="PHASE_ID",
        default=None,
        help=(
            "(used with --resume) reset the named phase's status to 'pending' "
            "and re-run it. Example: --resume foo --retry-phase 0b"
        ),
    )
    p.add_argument(
        "--stop-after",
        metavar="PHASE_ID",
        default=None,
        help=(
            "(used with --resume) run forward through the authoring phases and "
            "halt cleanly AFTER the named phase completes, instead of continuing "
            "to the next review gate. Enables per-step review of one transformation "
            "at a time. Example: --resume foo --stop-after 0b"
        ),
    )
    p.add_argument(
        "--length-tier",
        default="extended",
        choices=("default_deep_dive", "longer", "extended"),
        help=("target episode length tier (initial run only; persisted in state). Default: extended."),
    )
    p.add_argument(
        "--unit-mode",
        default="auto",
        choices=("chapter", "section", "auto"),
        help=("Phase 0d episode segmentation (initial run only; persisted in state). Default: auto."),
    )
    p.add_argument(
        "--unattended",
        action="store_true",
        help=(
            "clear the human-approval gates that only pace an attended run (the "
            "06a source review), so the book runs through to the reading edition "
            "without a person at the keyboard. Persisted in state, so the "
            "watchdog's own --resume honours it. Halts that wait on a FILE only a "
            "human can supply (dropped audio, curated visuals) are unaffected."
        ),
    )
    p.add_argument(
        "--doctor",
        action="store_true",
        help=(
            "run ONLY the Setup-stage system check (deps, authoring AI auth, "
            "Anthropic + Azure connectivity) and exit. 0=ready, 1=blocked."
        ),
    )
    p.add_argument(
        "--skip-doctor",
        action="store_true",
        help=(
            "skip the Setup-stage system check. Use only when you know the "
            "failing subsystem is unused by the phases you are running."
        ),
    )
    p.add_argument(
        "--authoring-engine",
        choices=("auto", "claude", "codex"),
        default="auto",
        help=("authoring engine: auto=Claude primary with Codex fallback, or force claude/codex."),
    )
    p.add_argument("--no-codex-fallback", action="store_true", help="auto mode halts instead of using Codex.")
    p.add_argument("--version", action="version", version=f"orchestrate_book.py v{ORCHESTRATOR_VERSION}")
    return p


def _maybe_relaunch_under_watchdog(slug: str, *, retry_phase: str | None = None) -> None:
    """Auto-spawn watch_orchestrator.sh when --resume is called without it.

    ``retry_phase`` — this process is about to exit and hand the run to the
    watchdog, whose own subsequent ``--resume`` invocations never see the
    original ``--retry-phase`` the operator typed (verified 2026-07-31: the
    watchdog's stale-running recovery loop derives its OWN --retry-phase from
    state.phase when phase_status=="running" — an unrelated crash-recovery
    heuristic, not a pass-through of what was typed here). Without this, an
    operator's explicit ``--resume <slug> --retry-phase per-chapter`` after
    fixing a failed chapter silently did nothing: this process exited before
    ever calling into resume_dispatcher.run_resume, so the reset that flag
    was supposed to trigger never happened, and the relaunched watchdog saw
    the still-failed state and skipped the chapter again. Applying the same
    reset here — BEFORE the relaunch, mirroring how --unattended is already
    latched into state above this call — makes the flag take effect
    regardless of which process ends up running the phase loop.
    """
    if os.environ.get("PODCAST_WATCHDOG"):
        # Already running under the watchdog (or PODCAST_WATCHDOG=1 was set
        # deliberately to stay in-process) — this process continues on to
        # resume_dispatcher.run_resume itself, which applies --retry-phase
        # normally. Applying it again here would be redundant, not harmful,
        # but the point of this block is specifically to cover the case
        # where that normal path is never reached (below).
        return

    if retry_phase:
        _bd = _paths_find_content(slug)
        if _bd:
            from _progress import read_state as _read_state
            from _progress import write_state as _write_state
            from phases.resume_dispatcher import _clear_downstream_phases

            _st = _read_state(_bd[2]) or {}
            if retry_phase in _st.get("phases", {}):
                _clear_downstream_phases(_st, retry_phase, log=_info)
                _write_state(_bd[2], _st)
                _info(f"  --retry-phase {retry_phase}: applied before watchdog handoff")
            else:
                _err(
                    f"  --retry-phase {retry_phase}: unknown phase, not applied — {sorted(_st.get('phases', {}).keys())}"
                )

    watchdog = Path(__file__).resolve().parent / "watch_orchestrator.sh"
    if not watchdog.exists():
        _err("watch_orchestrator.sh not found — running WITHOUT self-healing watchdog")
        return

    log_dir = Path(__file__).resolve().parents[2] / "_workspace" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"orchestrator-{slug}.log"

    print(f"  [watchdog] auto-spawning watch_orchestrator.sh for {slug}")
    print(f"  [watchdog] log: {log_path}")
    print("  [watchdog] this process exits; watchdog owns the run from here.")

    # stdout is DISCARDED deliberately, and that is NOT dropped output: the watchdog
    # already tees everything it and the orchestrator produce into this same log. Also
    # passing it the log as stdout gave the file two writers per line, so every line was
    # written twice (measured at 128 watchdog lines for 64 distinct ones) — most of the
    # reason a run APPEARS to repeat itself, and it hid genuine repeats. stderr IS kept:
    # tee does not carry it, so a crash inside the watchdog would otherwise vanish.
    # Running the watchdog by hand still streams to the terminal — that path never had a
    # second writer, which is why only this auto-spawn path (the default) doubled.
    with open(log_path, "a") as log_fh:
        subprocess.Popen(
            ["/bin/bash", str(watchdog), slug],
            stdout=subprocess.DEVNULL,
            stderr=log_fh,
            start_new_session=True,
        )
    sys.exit(0)


def main() -> int:
    args = build_parser().parse_args()
    os.environ["PODCAST_FACTORY_AUTHORING_ENGINE"] = args.authoring_engine
    if args.no_codex_fallback:
        os.environ["PODCAST_FACTORY_CODEX_FALLBACK"] = "0"

    if args.status:
        return run_status(args)

    # ── Setup stage: full system check ──────────────────────────────────────
    # `--doctor` runs ONLY the check and exits. Otherwise the check gates every
    # run (initial + resume) BEFORE the watchdog is spawned — so an unavailable
    # authoring engine or connectivity break fails fast with the exact fix
    # command, instead of the watchdog retry-looping a doomed run 20×.
    from preflight_doctor import run_doctor as _run_doctor

    if args.doctor:
        # Standalone: assume the heaviest scope (azure included) for a full sweep.
        return _run_doctor(need_azure=True)

    if not args.skip_doctor:
        # Azure is only needed while an ingest phase 0a still has to run. On a
        # resume past 0a, skip the Azure probe so a book mid-pipeline isn't
        # blocked by an ingest-only dependency.
        need_azure = True
        if args.resume:
            _bd = _paths_find_content(args.resume)
            _state = read_state(_bd[2]) if _bd else None
            if _state:
                _zd = _state.get("phases", {}).get("0a", {})
                need_azure = _zd.get("status") != "completed"
        if _run_doctor(need_azure=need_azure) != 0:
            return 1

    if args.resume:
        slug_for_lock = args.resume
    elif args.pdf_path:
        pdf = Path(args.pdf_path).expanduser().resolve()
        if not pdf.is_file():
            _err(f"source not found (or not a file): {args.pdf_path}")
            return 1
        slug_for_lock = args.slug or derive_slug(pdf)
        if not SLUG_RE.match(slug_for_lock):
            _err(
                f"invalid slug {slug_for_lock!r} "
                f"(derived from {pdf.name!r}). Must be lowercase-kebab-case "
                f"(a-z, 0-9, hyphens). Pass an explicit --slug."
            )
            return 1
    else:
        _err("either <pdf-path> (initial) or --resume <slug> or --status <slug> is required")
        return 1

    if args.resume:
        # BEFORE the watchdog handoff, not inside run_resume: the relaunch replaces
        # this process with one the watchdog invokes WITHOUT --unattended, so a flag
        # latched further down would never be written at all. It was not — the book
        # sat at the same gate it had just been authorized past.
        if getattr(args, "unattended", False):
            _bd = _paths_find_content(args.resume)
            if _bd:
                from _progress import UNATTENDED_KEY, write_state

                _st = read_state(_bd[2]) or {}
                if not _st.get(UNATTENDED_KEY):
                    _st[UNATTENDED_KEY] = True
                    write_state(_bd[2], _st)
                    _info("  --unattended: human-approval gates auto-cleared for this book from here on.")
        _maybe_relaunch_under_watchdog(slug_for_lock, retry_phase=getattr(args, "retry_phase", None))

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
