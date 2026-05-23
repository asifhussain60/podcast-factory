#!/usr/bin/env python3
"""DEPRECATED 2026-05-23 — use `scripts/podcast/publish_to_library.py` instead.

Rationale: the rich output convention of this script (transcript/, podcasts/
series-XX/, index.md, _meta.json) was retired by Asif directive 2026-05-23 in
favor of a minimal library/books/<slug>/ layout containing only chapters/ +
episodes/ + README.md — the bare set NotebookLM needs to render audio.
Invoking this script now prints a nag to stderr but still runs; remove the
nag block and rename the file to .deprecated when ready to retire fully.

============================================================================
ORIGINAL DOCSTRING (kept for reference until file is fully retired):
============================================================================
Promote shipped artifacts from _workspace/books/<slug>/ to library/books/<slug>/.

This is the ONLY supported writer of library/. CI enforces that any commit
touching library/ either has a message starting with "ship: " or carries the
`[library-manual-edit]` marker in its body (see .github/workflows/library-readonly.yml).

Behavior (Phase 9.5):
  * Reads _workspace/books/<slug>/_system/orchestrator-state.json to confirm
    a shippable phase_status. Halts unless one of:
      shipped | ship-ready | ship-with-caution | halted_by_operator
    (the last because the operator-halt path in KaR's archetype-driven manual
    finish is the same as a per-chapter ship). --force overrides.
  * Reads _workspace/books/<slug>/_system/challenger-report.md for the verdict
    and per-episode header. Falls back to verdict="unknown" if absent.
  * For each --episode (or every chapter in _system/orchestrator-state.json's
    `completed_slugs` when --episode is omitted):
      - Copies _workspace/books/<slug>/chapters/ch<NN>-<slug>.txt
        -> library/books/<slug>/transcript/<NN>-<slug>.md
        with a minimal YAML front-matter block (title, chapter-id,
        source-path-in-workspace, ship-date, ship-verdict).
      - Copies the same chapters/ file (verbatim, as NotebookLM SOURCE upload)
        -> library/books/<slug>/podcasts/series-01-<book-slug>/EP<NN>-<slug>/source.txt
      - Copies _workspace/books/<slug>/episodes/EP<NN>-<slug>.txt
        (the NotebookLM CUSTOMIZE prompt)
        -> library/books/<slug>/podcasts/series-01-<book-slug>/EP<NN>-<slug>/framing.md
      - Copies _workspace/books/<slug>/_system/challenger-report.md
        -> library/books/<slug>/podcasts/series-01-<book-slug>/EP<NN>-<slug>/challenger-report.md
      - If _workspace/books/<slug>/episode-drafts/<chapter>/audio.mp3 exists,
        copies it too. (Audio archival is opt-in per Phase 9.5 design pick 2.)
  * Generates library/books/<slug>/podcasts/_series-index.md from series-plan.md.
  * Generates library/books/<slug>/podcasts/series-01-<slug>/_series.md per-series.
  * Generates library/books/<slug>/index.md from series-plan + state + verdict.
  * Regenerates library/_meta/catalog.md (markdown table of all books).

Idempotency: re-running adds/updates only files for the requested episodes;
does not delete anything from library/.

Usage:
  ship_to_library.py --book <slug> [--episode EP<NN>] [--dry-run] [--force]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = REPO_ROOT / "_workspace" / "books"
# Option 2 layout (2026-05-22): library/ lives above the worktree at
# podcast-factory/library/, two parents up from REPO_ROOT. Works from any
# worktree (worktrees/main/ or worktrees/book-X/) since all worktrees sit
# at the same depth under podcast-factory/.
LIBRARY = REPO_ROOT.parent.parent / "library"


def _display(path: Path) -> str:
    """Render a path for user-facing log lines. Uses os.path.relpath so paths
    outside REPO_ROOT (notably under LIBRARY, which is the parent-of-parent
    of REPO_ROOT in the Option 2 layout) render as '../../library/foo.md'
    instead of crashing the way Path.relative_to() does on cross-tree paths."""
    import os
    return os.path.relpath(path, REPO_ROOT)

SHIPPABLE_STATUSES = {
    "shipped",
    "ship-ready",
    "ship-with-caution",
    "ship-with-caution-approved",
    "halted_by_operator",
}


@dataclass
class Episode:
    ep_num: str            # e.g. "10"
    chapter_slug: str      # e.g. "motion-stillness-hyle-and-form"
    chapter_basename: str  # e.g. "ch10-motion-stillness-hyle-and-form"
    title: str             # human title from series-plan
    chapter_txt: Path      # chapters/<basename>.txt
    episode_txt: Path      # episodes/EP<NN>-<slug>.txt


def _die(msg: str) -> None:
    print(f"ship_to_library: {msg}", file=sys.stderr)
    sys.exit(2)


def _read_state(book_dir: Path) -> dict:
    state_path = book_dir / "_system" / "orchestrator-state.json"
    if not state_path.exists():
        _die(f"missing orchestrator state at {_display(state_path)}")
    return json.loads(state_path.read_text())


def _read_verdict(book_dir: Path) -> str:
    report = book_dir / "_system" / "challenger-report.md"
    if not report.exists():
        return "unknown"
    for line in report.read_text().splitlines()[:20]:
        m = re.match(r"\*\*Verdict:\*\*\s*(.+)", line.strip())
        if m:
            return m.group(1).strip()
    return "unknown"


def _series_plan_episodes(book_dir: Path) -> list[Episode]:
    """Parse _system/series-plan.md to extract the canonical episode list."""
    plan = book_dir / "_system" / "series-plan.md"
    if not plan.exists():
        _die(f"missing series plan at {_display(plan)}")

    episodes: list[Episode] = []
    in_episode_table = False
    for raw in plan.read_text().splitlines():
        line = raw.strip()
        if line.startswith("| # | Title |"):
            in_episode_table = True
            continue
        if in_episode_table:
            if not line.startswith("|") or line.startswith("|---"):
                if line == "" or line.startswith("##"):
                    in_episode_table = False
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 8 or not cells[0].isdigit():
                continue
            ep_num = cells[0].zfill(2)
            title = cells[1]
            upload = cells[6]   # `chapters/ch<NN><suffix>-<slug>.txt`
            m = re.search(r"chapters/(ch\d+[a-z]?-[a-z0-9-]+)\.txt", upload)
            if not m:
                continue
            chapter_basename = m.group(1)
            slug = re.sub(r"^ch\d+[a-z]?-", "", chapter_basename)
            episodes.append(Episode(
                ep_num=ep_num,
                chapter_slug=slug,
                chapter_basename=chapter_basename,
                title=title,
                chapter_txt=book_dir / "chapters" / f"{chapter_basename}.txt",
                episode_txt=book_dir / "episodes" / f"EP{ep_num}-{slug}.txt",
            ))
    if not episodes:
        _die("no episodes parsed from series-plan.md (table format may have changed)")
    return episodes


def _select_episodes(all_eps: list[Episode], state: dict, episode_arg: str | None) -> list[Episode]:
    if episode_arg:
        target = episode_arg.upper().lstrip("EP").zfill(2)
        matches = [e for e in all_eps if e.ep_num == target]
        if not matches:
            _die(f"--episode EP{target} not found in series-plan.md")
        return matches
    completed = (state.get("phases", {}).get("per-chapter", {}).get("completed_slugs")
                 or state.get("completed_slugs") or [])
    if not completed:
        _die("no completed_slugs in state and no --episode given; nothing to ship")
    return [e for e in all_eps if e.chapter_slug in completed]


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _write(path: Path, content: str, dry_run: bool) -> None:
    if dry_run:
        print(f"  [dry-run] would write {_display(path)}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    print(f"  wrote {_display(path)}")


def _copy(src: Path, dst: Path, dry_run: bool) -> None:
    if not src.exists():
        print(f"  [skip] source missing: {_display(src)}")
        return
    if dry_run:
        print(f"  [dry-run] would copy {_display(src)} -> {_display(dst)}")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"  copied {_display(dst)}")


def _drop_gitkeep(path: Path, dry_run: bool) -> None:
    gk = path / ".gitkeep"
    if gk.exists() and not dry_run:
        gk.unlink()


def _promote_episode(book_slug: str, ep: Episode, verdict: str, ship_date: str, dry_run: bool) -> None:
    book_lib = LIBRARY / "books" / book_slug
    series_slug = f"series-01-{book_slug}"
    ep_dir_name = f"EP{ep.ep_num}-{ep.chapter_slug}"
    ep_dir = book_lib / "podcasts" / series_slug / ep_dir_name

    transcript_md = book_lib / "transcript" / f"{ep.ep_num}-{ep.chapter_slug}.md"
    transcript_body = ep.chapter_txt.read_text() if ep.chapter_txt.exists() else ""
    transcript_yaml = (
        "---\n"
        f"title: \"{ep.title}\"\n"
        f"chapter_id: \"{ep.chapter_basename}\"\n"
        f"episode: \"EP{ep.ep_num}\"\n"
        f"book: \"{book_slug}\"\n"
        f"source_in_workspace: \"_workspace/books/{book_slug}/chapters/{ep.chapter_basename}.txt\"\n"
        f"ship_date: \"{ship_date}\"\n"
        f"ship_verdict: \"{verdict}\"\n"
        "---\n\n"
    )
    _write(transcript_md, transcript_yaml + transcript_body, dry_run)
    _drop_gitkeep(book_lib / "transcript", dry_run)

    _copy(ep.chapter_txt, ep_dir / "source.txt", dry_run)
    _copy(ep.episode_txt, ep_dir / "framing.md", dry_run)
    _copy(ep.chapter_txt.parents[1] / "_system" / "challenger-report.md",
          ep_dir / "challenger-report.md", dry_run)

    audio_src = (ep.chapter_txt.parents[1] / "episode-drafts" /
                 ep.chapter_basename / "audio.mp3")
    if audio_src.exists():
        _copy(audio_src, ep_dir / "audio.mp3", dry_run)


def _write_series_index(book_slug: str, all_eps: list[Episode], dry_run: bool) -> None:
    book_lib = LIBRARY / "books" / book_slug
    series_slug = f"series-01-{book_slug}"
    rows = ["| EP | Title | Chapter slug |", "|---|---|---|"]
    for e in all_eps:
        rows.append(f"| EP{e.ep_num} | {e.title} | `{e.chapter_slug}` |")
    body = (
        f"# Series index — {book_slug}\n\n"
        f"Series in this book:\n\n"
        f"- [series-01](./{series_slug}/_series.md) — primary arc\n\n"
        "## All episodes\n\n" + "\n".join(rows) + "\n"
    )
    _write(book_lib / "podcasts" / "_series-index.md", body, dry_run)

    per_series = (
        f"# series-01 — {book_slug}\n\n"
        "Primary arc. One episode per chapter in canonical order.\n\n"
        "## Episodes\n\n" + "\n".join(rows) + "\n"
    )
    _write(book_lib / "podcasts" / series_slug / "_series.md", per_series, dry_run)


def _write_book_index(book_slug: str, all_eps: list[Episode], state: dict,
                      verdict: str, ship_date: str, dry_run: bool) -> None:
    book_lib = LIBRARY / "books" / book_slug
    phase_status = state.get("phase_status", "unknown")
    yaml = (
        "---\n"
        f"book_slug: \"{book_slug}\"\n"
        f"branch: \"{state.get('branch', 'unknown')}\"\n"
        f"category: \"{state.get('category', 'books')}\"\n"
        f"episode_count: {len(all_eps)}\n"
        f"latest_ship_date: \"{ship_date}\"\n"
        f"latest_verdict: \"{verdict}\"\n"
        f"orchestrator_phase: \"{state.get('phase', 'unknown')}\"\n"
        f"orchestrator_phase_status: \"{phase_status}\"\n"
        "---\n\n"
    )
    body = (
        f"# {book_slug}\n\n"
        f"**Episode count (planned):** {len(all_eps)}  \n"
        f"**Latest verdict:** {verdict}  \n"
        f"**Latest ship date:** {ship_date}  \n"
        f"**Pipeline phase:** {state.get('phase', 'unknown')} ({phase_status})\n\n"
        "## Series\n\n"
        f"- [series-01-{book_slug}](./podcasts/series-01-{book_slug}/_series.md)\n\n"
        "## Source\n\n"
        f"In-progress workspace: `_workspace/books/{book_slug}/`  \n"
        f"Shipped transcripts: [./transcript/](./transcript/)  \n"
        f"Shipped podcasts: [./podcasts/](./podcasts/)\n"
    )
    _write(book_lib / "index.md", yaml + body, dry_run)


def _regenerate_catalog(dry_run: bool) -> None:
    books_root = LIBRARY / "books"
    rows = ["| Book | Episodes | Latest verdict | Latest ship date | Phase |",
            "|---|---|---|---|---|"]
    if books_root.exists():
        for entry in sorted(books_root.iterdir()):
            idx = entry / "index.md"
            if not idx.exists():
                continue
            meta = {}
            text = idx.read_text()
            if text.startswith("---\n"):
                _, fm, _ = text.split("---\n", 2)
                for line in fm.splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        meta[k.strip()] = v.strip().strip('"')
            rows.append(
                f"| [{entry.name}](./books/{entry.name}/index.md) | "
                f"{meta.get('episode_count', '—')} | "
                f"{meta.get('latest_verdict', '—')} | "
                f"{meta.get('latest_ship_date', '—')} | "
                f"{meta.get('orchestrator_phase_status', '—')} |"
            )
    body = (
        "# library/ — shipped catalog\n\n"
        "Auto-generated by `scripts/podcast/ship_to_library.py`. Manual edits "
        "to this file are discouraged and CI-checked.\n\n"
        + "\n".join(rows) + "\n"
    )
    _write(LIBRARY / "_meta" / "catalog.md", body, dry_run)
    _drop_gitkeep(LIBRARY / "_meta", dry_run)


def main() -> None:
    sys.stderr.write(
        "\n"
        "*****************************************************************\n"
        "* DEPRECATED: ship_to_library.py was retired 2026-05-23.        *\n"
        "* Use:  scripts/podcast/publish_to_library.py <slug>            *\n"
        "* See:  skills-staging/publish-podcast/SKILL.md                 *\n"
        "*****************************************************************\n\n"
    )
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--book", required=True, help="book slug under _workspace/books/")
    ap.add_argument("--episode", help="EP id to promote (e.g. EP10). Default: all completed_slugs in state.")
    ap.add_argument("--dry-run", action="store_true", help="report what would happen; touch no files.")
    ap.add_argument("--force", action="store_true", help="bypass phase_status gate.")
    args = ap.parse_args()

    book_dir = WORKSPACE / args.book
    if not book_dir.is_dir():
        _die(f"book workspace not found: {_display(book_dir)}")

    state = _read_state(book_dir)
    phase_status = state.get("phase_status", "unknown")
    if phase_status not in SHIPPABLE_STATUSES and not args.force:
        _die(f"phase_status={phase_status!r} not in {sorted(SHIPPABLE_STATUSES)}; "
             "rerun with --force to override")

    verdict = _read_verdict(book_dir)
    ship_date = _today()
    all_eps = _series_plan_episodes(book_dir)
    targets = _select_episodes(all_eps, state, args.episode)

    print(f"ship_to_library: book={args.book} verdict={verdict} ship_date={ship_date}")
    print(f"  promoting {len(targets)} episode(s): {[f'EP{e.ep_num}' for e in targets]}")

    for ep in targets:
        print(f"-- EP{ep.ep_num}: {ep.title}")
        _promote_episode(args.book, ep, verdict, ship_date, args.dry_run)

    _write_series_index(args.book, all_eps, args.dry_run)
    _write_book_index(args.book, all_eps, state, verdict, ship_date, args.dry_run)
    _drop_gitkeep(LIBRARY / "books", args.dry_run)
    _regenerate_catalog(args.dry_run)

    print("ship_to_library: done.")


if __name__ == "__main__":
    main()
