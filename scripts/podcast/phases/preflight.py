"""phases/preflight.py — Pre-flight gates for initial and resume runs.

Extracted from orchestrate_book.py (A4 split). Authority: plan.md §A4.

Functions:
  _in_preflight_artifacts_mode  — detect pre-staged curated artifact mode
  preflight_initial             — hard gates for a new book run
  preflight_resume              — hard gates for a resume run
  _run_chapter_set_check        — post-0d advisory chapter-set check
  _sweep_orphan_episode_drafts  — F8: remove stale episode-draft dirs
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _paths import REPO_ROOT, content_dir as _content_dir, find_content as _find_content, relative_to_repo as _rel  # noqa: E402
from _progress import read_state  # noqa: E402
from _rules import ALLOWED_CATEGORIES  # noqa: E402

AZURE_PROBE = REPO_ROOT / "scripts" / "podcast" / "test_azure_connectivity.py"
CHAPTER_SET_SCRIPT = REPO_ROOT / "scripts" / "podcast" / "check_chapter_set.py"
LIBRARY_ROOT = REPO_ROOT / "content" / "drafts"
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _run(cmd: list[str], *, cwd: Path | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def _git(*args: str) -> tuple[int, str, str]:
    return _run(["git", *args], cwd=REPO_ROOT)


def _err(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)


def _info(msg: str) -> None:
    print(msg)


def _book_dir(book_slug: str) -> Path | None:
    """Locate <slug> across all stage/category combos. Returns dir or None."""
    found = _find_content(book_slug)
    return found[2] if found else None


def _resolve_book_path(category: str, slug: str) -> Path:
    """Return canonical drafts path for a piece of content."""
    return _content_dir(slug, stage="drafts", category=category)


# ─── pre-flight artifact mode detection ──────────────────────────────────────


def _in_preflight_artifacts_mode(slug: str, category: str) -> bool:
    """True when curated preflight artifacts exist but Phase 0a has not run.

    Operators may pre-stage _system/registry.md, _system/concept-glossary.md
    and _system/source/ BEFORE invoking orchestrate_book.py. This mode relaxes
    the `dir-not-exists` and branch gates so the orchestrator fills in stubs.
    """
    book_dir = _resolve_book_path(category, slug)
    registry = book_dir / "_system" / "registry.md"
    state    = book_dir / "_system" / "orchestrator-state.json"
    return registry.exists() and not state.exists()


# ─── initial-run gates ────────────────────────────────────────────────────────


def preflight_initial(pdf_path: Path, slug: str, category: str) -> list[str]:
    """Return list of failure reasons. Empty list = pass."""
    fails: list[str] = []
    preflight_mode = _in_preflight_artifacts_mode(slug, category)

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

    # 3. On a valid starting branch
    rc, branch, _ = _git("rev-parse", "--abbrev-ref", "HEAD")
    branch = branch.strip() if rc == 0 else ""
    from _branching import branch_name as _branch_name
    expected_content_branch = _branch_name(category, slug)
    valid_branches = {"develop"}
    if preflight_mode:
        valid_branches |= {"feat/podcast-w1-foundation", expected_content_branch}
    if branch not in valid_branches:
        fails.append(
            f"current branch is '{branch}'; expected one of {sorted(valid_branches)}. "
            "Run: git checkout " + (sorted(valid_branches)[0] if not preflight_mode else expected_content_branch)
        )

    # 4. PDF exists + readable
    if not pdf_path.exists() or not pdf_path.is_file():
        fails.append(f"PDF not found or not a file: {pdf_path}")
    elif pdf_path.stat().st_size == 0:
        fails.append(f"PDF is empty: {pdf_path}")

    # 5. Slug valid + uncollided locally
    if not SLUG_RE.match(slug):
        fails.append(f"slug invalid: {slug!r} (lowercase, hyphens, alphanumerics only)")
    elif (_resolve_book_path(category, slug)).exists() and not preflight_mode:
        fails.append(
            f"slug collides with existing book at "
            f"{(_resolve_book_path(category, slug)).relative_to(REPO_ROOT)}. "
            "Use --resume or pick a different slug."
        )

    # 6. Slug uncollided remotely
    if SLUG_RE.match(slug):
        rc, out, _ = _git("ls-remote", "--heads", "origin", expected_content_branch)
        if rc == 0 and out.strip():
            remote_sha = out.split()[0] if out else ""
            rc2, local_sha, _ = _git("rev-parse", expected_content_branch)
            local_sha = local_sha.strip() if rc2 == 0 else ""
            if not (preflight_mode and remote_sha and local_sha and remote_sha == local_sha):
                fails.append(
                    f"remote branch {expected_content_branch!r} already exists. "
                    "Either pick a different slug or use --resume."
                )

    # 7. Category allowed
    if category not in ALLOWED_CATEGORIES:
        fails.append(f"category {category!r} not in {ALLOWED_CATEGORIES}")

    return fails


# ─── resume gates ─────────────────────────────────────────────────────────────


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

    # 2. F8 sweep — remove orphan episode-drafts/EP* dirs before tree-clean check
    try:
        n_swept = _sweep_orphan_episode_drafts(book_dir)
        if n_swept:
            _info(f"pre-flight sweep: removed {n_swept} orphan episode-drafts/ subdir(s)")
    except Exception as _e:  # noqa: BLE001
        _info(f"pre-flight sweep: skipped ({_e!r})")

    # 3. Working tree clean (with runtime-artifact allowlist)
    rc, out, _ = _git("status", "--porcelain")
    if rc != 0:
        fails.append("git status failed; cannot determine working-tree state")
    else:
        _bd_for_prefix = _book_dir(book_slug)
        if _bd_for_prefix is not None:
            book_runtime_prefix = f"{_rel(_bd_for_prefix)}/"
        else:
            book_runtime_prefix = f"content/drafts/books/{book_slug}/"
        runtime_artifact_suffixes = (
            "/_system/cost-ledger.jsonl",
            "/_system/orchestrator-state.json",
            "/_system/challenger-report.md",
            "/_system/enrichment-log.md",
            "/_system/chapter-set-report.md",
            "/_system/health-trend.md",
            "/_system/watchdog.json",
            "scripts/podcast/tighten_source.py",
            ".code-workspace",
        )
        runtime_artifact_dirs = (
            f"{book_runtime_prefix}_system/episode-drafts/",
            f"{book_runtime_prefix}_system/per-chapter-reports/",
            f"{book_runtime_prefix}_system/slide-challenger-reports/",
            f"{book_runtime_prefix}_system/source/text/_chunks/",
            f"{book_runtime_prefix}chapter-contracts/",
            f"{book_runtime_prefix}chapters/",
            f"{book_runtime_prefix}episodes/",
            f"{book_runtime_prefix}slide-decks/",
            "content/podcast/.skill/_learning/",
            "_workspace/tmp/",
            "_workspace/logs/",
            "content/m4a/",
        )
        runtime_artifact_suffixes_lc = tuple(s.lower() for s in runtime_artifact_suffixes)
        runtime_artifact_dirs_lc = tuple(d.lower() for d in runtime_artifact_dirs)
        non_runtime: list[str] = []
        for line in out.splitlines():
            path = line[3:] if len(line) > 3 else ""
            if not path:
                continue
            path_lc = path.lower()
            if any(path_lc.endswith(suf) for suf in runtime_artifact_suffixes_lc):
                continue
            if any(path_lc.startswith(d) for d in runtime_artifact_dirs_lc):
                continue
            non_runtime.append(line)
        if non_runtime:
            fails.append(
                "working tree not clean (non-runtime files modified or untracked). "
                "Commit or stash first, then --resume. Files:\n  "
                + "\n  ".join(non_runtime[:10])
                + ("\n  …" if len(non_runtime) > 10 else "")
            )

    # 4. On matching branch
    from _branching import branch_name as _branch_name
    expected_branch = (state or {}).get("branch") or _branch_name(
        (state or {}).get("category"), book_slug
    )
    rc, branch, _ = _git("rev-parse", "--abbrev-ref", "HEAD")
    branch = branch.strip() if rc == 0 else ""
    if branch != expected_branch:
        fails.append(
            f"current branch is {branch!r}; expected {expected_branch!r}. "
            f"Run: git checkout {expected_branch}"
        )

    return book_dir, fails


# ─── chapter-set advisory check (post-0d) ─────────────────────────────────────


def _run_chapter_set_check(book_dir: Path, log=_info) -> None:
    """G2 cohesion fix: post-Phase-0d advisory chapter-set check.

    Shells out to check_chapter_set.py; writes _system/chapter-set-report.md.
    Never raises — advisory only. Catches title collisions, word-band misfits,
    generic titles, and inter-chapter balance variance BEFORE Phase 0e spend.
    """
    log("phase: 0d.5 · chapter-set advisory check")
    rc, stdout, stderr = _run([sys.executable, str(CHAPTER_SET_SCRIPT), str(book_dir)])
    findings: list[dict] = []
    if stdout.strip():
        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError:
            log(f"  · chapter-set check emitted non-JSON output; rc={rc}; skipping report")
            return
        if isinstance(parsed, dict):
            findings = parsed.get("findings", [])
        elif isinstance(parsed, list):
            findings = parsed

    counts = {"P0": 0, "P1": 0, "P2": 0}
    for f in findings:
        sev = f.get("severity", "P2")
        counts[sev] = counts.get(sev, 0) + 1

    report_path = book_dir / "_system" / "chapter-set-report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lines = [
        f"# Chapter-set advisory report — {book_dir.name}",
        "",
        f"Generated: {ts}",
        f"Source: `scripts/podcast/check_chapter_set.py` (challenger Category P)",
        "",
        "## Summary",
        f"- P0 (would block ship if challenger ran): **{counts.get('P0', 0)}**",
        f"- P1 (ship-with-caution): **{counts.get('P1', 0)}**",
        f"- P2 (advisory): **{counts.get('P2', 0)}**",
        "",
    ]
    if findings:
        lines.append("## Findings")
        lines.append("")
        for f in findings:
            check = f.get("check", "?")
            sev = f.get("severity", "?")
            slug = f.get("slug", "?")
            msg = f.get("msg", "")
            lines.append(f"- **{check}** [{sev}] `{slug}` — {msg}")
    else:
        lines.append("No findings. Chapter-set is clean.")
    lines.append("")
    report_path.write_text("\n".join(lines), encoding="utf-8")

    summary = (
        f"  · {counts.get('P0', 0)} P0 / "
        f"{counts.get('P1', 0)} P1 / "
        f"{counts.get('P2', 0)} P2 findings"
    )
    if counts.get("P0", 0) > 0:
        log(f"  · ⚠ P0 chapter-set findings — review {report_path.relative_to(REPO_ROOT)} before Phase 0e")
    log(summary)


# ─── orphan episode-draft sweep (F8) ─────────────────────────────────────────


def _sweep_orphan_episode_drafts(book_dir: Path) -> int:
    """F8 fix: auto-delete stale episode-drafts/EP##-... directories whose names
    don't match any current chapter's expected episode_id.

    Returns count of dirs removed. Safe to call any time (idempotent).
    """
    import shutil

    drafts_dir = book_dir / "_system" / "episode-drafts"
    if not drafts_dir.is_dir():
        return 0

    contracts_dir = book_dir / "chapter-contracts"
    if not contracts_dir.is_dir():
        return 0

    chapter_slugs = sorted(p.stem for p in contracts_dir.glob("*.yml"))
    chapters_dir = book_dir / "chapters"
    expected: set[str] = set()
    for slug in chapter_slugs:
        matches = list(chapters_dir.glob(f"ch*-{slug}.txt"))
        if not matches:
            continue
        chap_prefix = matches[0].stem.split("-", 1)[0]
        m = re.match(r"ch(\d+)", chap_prefix)
        chap_num = m.group(1) if m else chap_prefix[2:]
        expected.add(f"EP{chap_num}-{slug}")

    removed = 0
    for entry in sorted(drafts_dir.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name not in expected:
            shutil.rmtree(entry)
            _info(f"  swept orphan episode-draft: removed {entry.name}/")
            removed += 1
    return removed
