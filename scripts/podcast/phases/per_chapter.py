"""phases/per_chapter.py — per_chapter_pass: extract → frame → build → converge.

Extracted from orchestrate_book.py (A4 split). Authority: plan.md §A4.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _paths import REPO_ROOT  # noqa: E402
from _authoring import AuthoringError, author_framing  # noqa: E402
from _convergence import ChapterOutcome, converge_chapter  # noqa: E402
from phases.series_plan import _resolve_episode_id  # noqa: E402

EXTRACT_SCRIPT = REPO_ROOT / "scripts" / "podcast" / "extract_chapter.py"
BUILD_SCRIPT = REPO_ROOT / "scripts" / "podcast" / "build_episode_txt.py"


def _run(cmd: list[str], *, cwd: Path | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def per_chapter_pass(book_dir: Path, chapter_slug: str) -> ChapterOutcome:
    """Run the full per-chapter pipeline for one chapter.

    extract → author framing → pipeline_lint → build episode .txt → converge.
    Returns the convergence ChapterOutcome. Never raises — failure is encoded
    in the returned outcome's `final_verdict = "FAILED"`.
    """
    book_slug = book_dir.name

    chapter_file = next((book_dir / "chapters").glob(f"ch*-{chapter_slug}.txt"), None)
    if chapter_file is None:
        return ChapterOutcome(
            chapter_slug=chapter_slug,
            final_verdict="FAILED",
            outer_iterations=0,
            fixer_attempts=0,
            p0_remaining=0, p1_remaining=0, p2_remaining=0,
            notes=[f"chapter file missing for slug {chapter_slug} "
                   f"(expected at chapters/ch*-{chapter_slug}.txt)"],
        )
    chapter_ref = f"{book_slug}/{chapter_file.stem}"

    # 1. Extract — scaffold the episode-draft folder + bundle from the contract.
    rc, out, err = _run(
        [sys.executable, str(EXTRACT_SCRIPT), chapter_ref, "--force"]
    )
    if rc != 0:
        return ChapterOutcome(
            chapter_slug=chapter_slug,
            final_verdict="FAILED",
            outer_iterations=0,
            fixer_attempts=0,
            p0_remaining=0, p1_remaining=0, p2_remaining=0,
            notes=[f"extract_chapter.py failed for {chapter_ref!r}: rc={rc}: {err.strip()[:200]}"],
        )

    # 2. Author framing — LLM call.
    try:
        author_framing(book_dir, chapter_slug)
    except AuthoringError as e:
        return ChapterOutcome(
            chapter_slug=chapter_slug,
            final_verdict="FAILED",
            outer_iterations=0,
            fixer_attempts=0,
            p0_remaining=0, p1_remaining=0, p2_remaining=0,
            notes=[f"framing authoring failed: {e}"],
        )

    # 2.5. Pre-flight lint: run pipeline_lint against the freshly-authored
    # framing + chapter pair. Catches structural mismatches BEFORE build's hard
    # gates do. Deterministic, $0 cost.
    _episode_id = _resolve_episode_id(book_dir, chapter_file, chapter_slug)
    _lint_path = Path(__file__).resolve().parents[1] / "pipeline_lint.py"
    _lint_rc, _lint_out, _lint_err = _run(
        [sys.executable, str(_lint_path),
         "--book-dir", str(book_dir),
         "--episode", _episode_id]
    )
    if _lint_rc == 1:
        return ChapterOutcome(
            chapter_slug=chapter_slug,
            final_verdict="FAILED",
            outer_iterations=0,
            fixer_attempts=0,
            p0_remaining=1, p1_remaining=0, p2_remaining=0,
            notes=[f"pipeline_lint P0: framing structural mismatch:\n{_lint_out.strip()[:600]}"],
        )

    # 3. Build the episode .txt — deterministic gate.
    episode_id = _resolve_episode_id(book_dir, chapter_file, chapter_slug)
    rc, out, err = _run([sys.executable, str(BUILD_SCRIPT), str(book_dir), episode_id])
    if rc != 0:
        return ChapterOutcome(
            chapter_slug=chapter_slug,
            final_verdict="FAILED",
            outer_iterations=0,
            fixer_attempts=0,
            p0_remaining=0, p1_remaining=0, p2_remaining=0,
            notes=[f"build_episode_txt.py failed: rc={rc}: {err.strip()[:300]}"],
        )

    # 4. Convergence loop.
    return converge_chapter(book_dir, chapter_slug)
