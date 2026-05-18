#!/usr/bin/env python3
"""orchestrate_book.py — Autonomous book-to-NotebookLM pipeline driver (Phase A).

PURPOSE

  Deterministic Python driver for the `podcast-orchestrator` agent. v2 plan
  defines three phases of implementation (see
  docs/architecture/podcast-orchestrator.html §10):

    Phase A · Driver to Phase 0f         ← THIS FILE (current scope)
    Phase B · Per-chapter convergence    (future)
    Phase C · Trainer onto substrate     (spec-only; trainer is an LLM agent)

  Phase A — what's shipped here:
    - Pre-flight (HARD GATES): Azure connectivity, working-tree clean,
      on `develop` (or the matching `book/<slug>` branch on --resume),
      PDF readable, slug uncollided.
    - Branch creation: `git checkout -b book/<slug>` + push.
    - Scaffold: shells out to `scripts/podcast/scaffold_book.py`.
    - Phase 0a: shells out to `scripts/podcast/ingest_source.py` (Azure
      OCR + Translation), the only deterministic LLM-free phase.
    - State writes: every transition writes
      `<BOOK_DIR>/_system/orchestrator-state.json` via _progress.py
      (atomic tmpfile + rename).
    - 0b–0e: NOT yet autonomous — _authoring.py stubs raise
      AuthoringError with a manual-fallback message. The orchestrator
      writes a `phase_status: halted_pending_llm_authoring` and exits
      cleanly, naming the next `--resume` action.
    - 0f: the chapter list + tier review halt is deferred to Phase B
      (since 0b–0e produce the chapter list).
    - `--status <slug>`: renders the state.json without modifying anything.
    - `--resume <slug>`: re-enters the driver and advances from the last
      completed phase.

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

DOES NOT MODIFY anything outside `content/podcast/library/<category>/<slug>/`
and `_workspace/Books/`. Git operations are limited to the active book
branch; never pushes to main; never force-pushes.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
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

REPO_ROOT = Path(__file__).resolve().parents[2]
LIBRARY_ROOT = REPO_ROOT / "content" / "podcast" / "library"
SCAFFOLD_SCRIPT = REPO_ROOT / "scripts" / "podcast" / "scaffold_book.py"
INGEST_SCRIPT = REPO_ROOT / "scripts" / "podcast" / "ingest_source.py"
AZURE_PROBE = REPO_ROOT / "scripts" / "podcast" / "test_azure_connectivity.py"

ALLOWED_CATEGORIES = ("books", "articles", "documents", "lectures", "interviews", "letters")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


# ─── tiny utilities ──────────────────────────────────────────────────────────


def _run(cmd: list[str], *, cwd: Path | None = None) -> tuple[int, str, str]:
    """Run a subprocess; return (rc, stdout, stderr). No exceptions on non-zero."""
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def _git(*args: str) -> tuple[int, str, str]:
    return _run(["git", *args], cwd=REPO_ROOT)


def _err(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)


def _info(msg: str) -> None:
    print(msg)


def _book_dir(book_slug: str) -> Path | None:
    """Resolve <slug> to library/<category>/<slug>/ if it exists."""
    matches = [p for p in LIBRARY_ROOT.glob(f"*/{book_slug}") if p.is_dir()]
    return matches[0] if len(matches) == 1 else None


# ─── slug derivation ─────────────────────────────────────────────────────────


def derive_slug(pdf_path: Path) -> str:
    """Stem of the PDF, lowercased, non-alphanumeric → hyphen, collapsed."""
    stem = pdf_path.stem.lower()
    s = re.sub(r"[^a-z0-9]+", "-", stem).strip("-")
    s = re.sub(r"-+", "-", s)
    return s


# ─── pre-flight hard gates ───────────────────────────────────────────────────


def preflight_initial(pdf_path: Path, slug: str, category: str) -> list[str]:
    """Return list of failure reasons. Empty list = pass."""
    fails: list[str] = []

    # 1. Azure connectivity
    rc, _, _ = _run([sys.executable, str(AZURE_PROBE)])
    if rc != 0:
        fails.append(
            "Azure connectivity probe failed. Run: "
            f"python3 {AZURE_PROBE.relative_to(REPO_ROOT)}"
        )

    # 2. Working tree clean
    rc, out, _ = _git("status", "--porcelain")
    if rc != 0 or out.strip():
        fails.append(
            "working tree not clean. Run `git status` and commit / stash first."
        )

    # 3. On `develop` (initial run)
    rc, branch, _ = _git("rev-parse", "--abbrev-ref", "HEAD")
    if rc != 0 or branch.strip() != "develop":
        fails.append(
            f"current branch is '{branch.strip()}'; expected 'develop'. "
            "Run: git checkout develop"
        )

    # 4. PDF exists + readable
    if not pdf_path.exists() or not pdf_path.is_file():
        fails.append(f"PDF not found or not a file: {pdf_path}")
    elif pdf_path.stat().st_size == 0:
        fails.append(f"PDF is empty: {pdf_path}")

    # 5. Slug valid + uncollided locally
    if not SLUG_RE.match(slug):
        fails.append(f"slug invalid: {slug!r} (lowercase, hyphens, alphanumerics only)")
    elif (LIBRARY_ROOT / category / slug).exists():
        fails.append(
            f"slug collides with existing book at "
            f"{(LIBRARY_ROOT / category / slug).relative_to(REPO_ROOT)}. "
            "Use --resume or pick a different slug."
        )

    # 6. Slug uncollided remotely
    if SLUG_RE.match(slug):
        rc, out, _ = _git("ls-remote", "--heads", "origin", f"book/{slug}")
        if rc == 0 and out.strip():
            fails.append(
                f"remote branch 'book/{slug}' already exists. "
                "Either pick a different slug or use --resume."
            )

    # 7. Category allowed
    if category not in ALLOWED_CATEGORIES:
        fails.append(
            f"category {category!r} not in {ALLOWED_CATEGORIES}"
        )

    return fails


def preflight_resume(book_slug: str) -> tuple[Path | None, list[str]]:
    """Return (book_dir, failures). Empty list = pass."""
    fails: list[str] = []
    book_dir = _book_dir(book_slug)
    if book_dir is None:
        fails.append(
            f"no library directory matches book-slug {book_slug!r} under "
            f"{LIBRARY_ROOT.relative_to(REPO_ROOT)}"
        )
        return None, fails

    # 1. State file exists
    state = read_state(book_dir)
    if state is None:
        fails.append(
            f"no orchestrator state at "
            f"{(book_dir / '_system' / 'orchestrator-state.json').relative_to(REPO_ROOT)}. "
            "Was this book started via orchestrate_book.py?"
        )

    # 2. Working tree clean
    rc, out, _ = _git("status", "--porcelain")
    if rc != 0 or out.strip():
        fails.append("working tree not clean. Commit or stash first, then --resume.")

    # 3. On matching branch
    rc, branch, _ = _git("rev-parse", "--abbrev-ref", "HEAD")
    branch = branch.strip() if rc == 0 else ""
    if branch != f"book/{book_slug}":
        fails.append(
            f"current branch is {branch!r}; expected 'book/{book_slug}'. "
            f"Run: git checkout book/{book_slug}"
        )

    return book_dir, fails


# ─── phase runners ───────────────────────────────────────────────────────────


def phase_branch(book_slug: str) -> None:
    """Create + push the book branch. Idempotent on already-on-branch."""
    rc, branch, _ = _git("rev-parse", "--abbrev-ref", "HEAD")
    branch = branch.strip() if rc == 0 else ""
    target = f"book/{book_slug}"
    if branch == target:
        _info(f"  already on {target}, skipping branch creation")
        return
    rc, _, err = _git("checkout", "-b", target)
    if rc != 0:
        raise RuntimeError(f"`git checkout -b {target}` failed: {err}")
    rc, _, err = _git("push", "-u", "origin", target)
    if rc != 0:
        # Non-fatal — remote push can be retried; book branch is local-valid.
        _err(f"`git push -u origin {target}` failed: {err}\n  (continuing with local-only branch)")


def phase_scaffold(category: str, book_slug: str, title: str, author: str | None) -> Path:
    """Shell out to scaffold_book.py. Returns the BOOK_DIR."""
    cmd = [
        sys.executable,
        str(SCAFFOLD_SCRIPT),
        category,
        book_slug,
        "--title", title,
    ]
    if author:
        cmd += ["--author", author]
    rc, out, err = _run(cmd)
    if rc != 0:
        raise RuntimeError(f"scaffold_book.py failed (rc={rc}):\n{err}\n{out}")
    book_dir = LIBRARY_ROOT / category / book_slug
    if not book_dir.is_dir():
        raise RuntimeError(f"scaffold did not create {book_dir}")
    return book_dir


def phase_0a_ingest(book_dir: Path, pdf_path: Path) -> None:
    """Shell out to ingest_source.py for Azure OCR + Translation."""
    cmd = [
        sys.executable,
        str(INGEST_SCRIPT),
        str(pdf_path),
        str(book_dir),
    ]
    rc, out, err = _run(cmd)
    if rc != 0:
        raise RuntimeError(f"ingest_source.py failed (rc={rc}):\n{err}\n{out}")
    raw = book_dir / "_system" / "source" / "text" / "raw-extract.md"
    if not raw.exists() or raw.stat().st_size == 0:
        raise RuntimeError(f"Phase 0a did not produce a non-empty {raw}")


def phase_git_commit(book_dir: Path, subject: str) -> None:
    """Stage everything under BOOK_DIR + commit with the given subject."""
    rel = book_dir.relative_to(REPO_ROOT)
    rc, _, err = _git("add", str(rel))
    if rc != 0:
        raise RuntimeError(f"`git add {rel}` failed: {err}")
    rc, out, _ = _git("status", "--porcelain")
    if not out.strip():
        _info(f"  nothing to commit for: {subject}")
        return
    rc, _, err = _git("commit", "-m", subject)
    if rc != 0:
        raise RuntimeError(f"`git commit` failed: {err}")


# ─── driver ──────────────────────────────────────────────────────────────────


def run_initial(args: argparse.Namespace) -> int:
    pdf_path = Path(args.pdf_path).resolve()
    slug = args.slug or derive_slug(pdf_path)
    category = args.category
    title = args.title or pdf_path.stem.replace("-", " ").replace("_", " ").title()
    author = args.author

    _info(f"orchestrate_book: initial run — slug={slug} · category={category}")
    fails = preflight_initial(pdf_path, slug, category)
    if fails:
        _err("pre-flight FAILED:")
        for f in fails:
            _err(f"  · {f}")
        return 1

    # Create the BOOK_DIR (scaffold), then write initial state into it.
    _info("pre-flight: OK")
    _info(f"phase: branch · creating book/{slug}")
    try:
        phase_branch(slug)
    except RuntimeError as e:
        _err(str(e))
        return 2

    _info(f"phase: scaffold · {category}/{slug}")
    try:
        book_dir = phase_scaffold(category, slug, title, author)
    except RuntimeError as e:
        _err(str(e))
        return 2

    # Initialize the state file now that BOOK_DIR exists.
    state = initial_state(slug, category)
    write_state(book_dir, state)
    update_phase(book_dir, phase="pre-flight", status="completed")
    update_phase(book_dir, phase="branch",     status="completed")
    update_phase(book_dir, phase="scaffold",   status="completed",
                 extras={"book_dir": str(book_dir.relative_to(REPO_ROOT))})
    phase_git_commit(book_dir, f"podcast({slug}): scaffold book directory")

    _info(f"phase: 0a · Azure OCR + Translation on {pdf_path.name}")
    update_phase(book_dir, phase="0a", status="running")
    try:
        phase_0a_ingest(book_dir, pdf_path)
    except RuntimeError as e:
        update_phase(book_dir, phase="0a", status="failed", error=str(e))
        _err(str(e))
        return 2
    update_phase(book_dir, phase="0a", status="completed")
    phase_git_commit(book_dir, f"podcast({slug}): phase 0a Azure ingest")

    # Phase A boundary: 0b–0e are LLM-authoring stubs.
    update_phase(
        book_dir,
        phase="0b",
        status="halted",
        error=(
            "Phase A boundary: 0b-0e LLM authoring not yet autonomous. "
            "Drive Phases 0b-0e via the conversational /podcast skill on this "
            "BOOK_DIR, then re-invoke orchestrate-book --resume <slug>."
        ),
    )
    _info("")
    _info("─" * 72)
    _info(f"Phase A complete · halted at the 0b authoring boundary.")
    _info("")
    _info("Next steps (manual until Phase B lands):")
    _info(f"  1. /podcast — drive Phases 0b, 0c, 0d, 0e on this BOOK_DIR:")
    _info(f"     {book_dir.relative_to(REPO_ROOT)}")
    _info(f"  2. Re-invoke: python3 scripts/podcast/orchestrate_book.py --resume {slug}")
    _info("")
    _info(f"Current state: python3 scripts/podcast/orchestrate_book.py --status {slug}")
    _info("─" * 72)
    return 3


def run_resume(args: argparse.Namespace) -> int:
    slug = args.resume
    _info(f"orchestrate_book: resume — slug={slug}")
    book_dir, fails = preflight_resume(slug)
    if fails:
        _err("pre-flight FAILED:")
        for f in fails:
            _err(f"  · {f}")
        return 1

    assert book_dir is not None
    state = read_state(book_dir)
    if state is None:
        _err("state file missing despite pre-flight pass — abort")
        return 2

    last = state.get("last_completed_phase") or ""
    next_p = state.get("next_phase") or ""

    _info(f"  last completed: {last or '(none)'}")
    _info(f"  next phase:     {next_p or '(none)'}")

    # Phase B not yet implemented. If we're past 0a, we're either waiting on
    # manual LLM authoring (0b-0e) or in territory Phase B owns.
    if last in ("0a", "0b", "0c", "0d", "0e"):
        # Check whether the next deterministic checkpoint's preconditions are met.
        # For now: if all of refined-english.md, _phonetics.md, chapter files exist,
        # we can advance the marker; otherwise tell the user to keep authoring.
        srctext = book_dir / "_system" / "source" / "text"
        chapters_dir = book_dir / "chapters"
        has_refined = (srctext / "refined-english.md").exists()
        has_phonetics = (srctext / "_phonetics.md").exists()
        has_chapters = any(chapters_dir.glob("ch*.txt"))

        _info("")
        _info("  Phase B (per-chapter convergence) is not yet shipped.")
        _info("  Current authoring artifacts on disk:")
        _info(f"    refined-english.md: {'✓' if has_refined else '·'}")
        _info(f"    _phonetics.md:      {'✓' if has_phonetics else '·'}")
        _info(f"    chapters/*.txt:     {'✓' if has_chapters else '·'}")
        _info("")
        if has_chapters:
            _info("  All authoring artifacts present. Phase 0f (series plan)")
            _info("  + per-chapter convergence loop will ship in Phase B.")
            _info("  For now, drive Phase 3 (framings) + Phase 4 (build + challenger)")
            _info("  via the conversational /podcast skill.")
        else:
            _info("  Continue Phases 0b-0e via /podcast, then re-invoke --resume.")
        return 3

    _info("")
    _info(f"  No automated action for current phase '{next_p}'. State file:")
    _info(f"    {(book_dir / '_system' / 'orchestrator-state.json').relative_to(REPO_ROOT)}")
    return 3


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
        description="Autonomous book-to-NotebookLM pipeline driver (Phase A).",
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
    p.add_argument("--version", action="version",
                   version=f"orchestrate_book.py v{ORCHESTRATOR_VERSION}")
    return p


def main() -> int:
    args = build_parser().parse_args()

    if args.status:
        return run_status(args)
    if args.resume:
        return run_resume(args)
    if not args.pdf_path:
        _err("either <pdf-path> (initial) or --resume <slug> or --status <slug> is required")
        return 1
    return run_initial(args)


if __name__ == "__main__":
    sys.exit(main())
