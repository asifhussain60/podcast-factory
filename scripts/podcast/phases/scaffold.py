"""phases/scaffold.py — Branch + scaffold + 0a OCR ingest + git commit.

Extracted from orchestrate_book.py (A4 split). Authority: plan.md §A4.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _paths import REPO_ROOT, content_dir as _content_dir
from phases.preflight import _in_preflight_artifacts_mode  # noqa: E402

SCAFFOLD_SCRIPT = REPO_ROOT / "scripts" / "podcast" / "scaffold_book.py"
INGEST_SCRIPT = REPO_ROOT / "scripts" / "podcast" / "ingest_source.py"


def _run(cmd: list[str], *, cwd: Path | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def _git(*args: str) -> tuple[int, str, str]:
    return _run(["git", *args], cwd=REPO_ROOT)


def _err(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)


def _info(msg: str) -> None:
    print(msg)


def phase_branch(book_slug: str, category: str) -> None:
    """Create + push the content branch. Idempotent on already-on-branch."""
    from _branching import branch_name as _branch_name
    rc, branch, _ = _git("rev-parse", "--abbrev-ref", "HEAD")
    branch = branch.strip() if rc == 0 else ""
    target = _branch_name(category, book_slug)
    if branch == target:
        _info(f"  already on {target}, skipping branch creation")
        return
    rc, _, err = _git("checkout", "-b", target)
    if rc != 0:
        raise RuntimeError(f"`git checkout -b {target}` failed: {err}")
    rc, _, err = _git("push", "-u", "origin", target)
    if rc != 0:
        _err(f"`git push -u origin {target}` failed: {err}\n  (continuing with local-only branch)")


def phase_scaffold(category: str, book_slug: str, title: str, author: str | None) -> Path:
    """Shell out to scaffold_book.py. Returns the BOOK_DIR.

    Detects preflight-artifacts mode (curated registry/glossary pre-staged)
    and passes --allow-existing so scaffold fills only missing stubs.
    """
    cmd = [sys.executable, str(SCAFFOLD_SCRIPT), category, book_slug, title]
    if author:
        cmd += ["--author", author]
    if _in_preflight_artifacts_mode(book_slug, category):
        cmd += ["--allow-existing"]
    rc, out, err = _run(cmd)
    if rc != 0:
        raise RuntimeError(f"scaffold_book.py failed (rc={rc}):\n{err}\n{out}")
    book_dir = _content_dir(book_slug, stage="drafts", category=category)
    if not book_dir.is_dir():
        raise RuntimeError(f"scaffold did not create {book_dir}")
    return book_dir


def phase_0a_ingest(book_dir: Path, pdf_path: Path, category: str, book_slug: str) -> None:
    """Shell out to ingest_source.py for Azure OCR + Translation."""
    cmd = [
        sys.executable, str(INGEST_SCRIPT),
        str(pdf_path),
        "--book-slug", book_slug,
        "--category", category,
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
