#!/usr/bin/env python3
"""publish_to_library.py — on-demand publish from `_workspace/books/<slug>/`
to `library/books/<slug>/`. Minimal output: chapters/ + episodes/ + README.md.

This script is the canonical writer of `library/books/<slug>/`. It supersedes
the older `ship_to_library.py` (now deprecated — see top of that file).

Library output is **filesystem-only** at `<repo-parent>/library/` and is
deliberately NOT git-tracked. The published copy is a derived artifact —
deletable + regeneratable from `_workspace/books/<slug>/` at any time.

GATES (all 6 must pass under default mode; failures block publish):

  G1  Required structure  : _workspace/books/<slug>/chapters/*.txt and
                            _workspace/books/<slug>/episodes/*.txt both
                            exist and non-empty.
  G2  Pair completeness   : every EP##-<slug>.txt has a matching
                            ch##-<slug>.txt and vice versa.
  G3  Sequential numbering: chapter and episode files are purely sequential
                            01..N (no letter suffixes, no .5 decimals).
                            Mirrors the future S-EPISODE-SEQUENTIAL
                            challenger check inlined here.
  G4  Build-clean         : running build_episode_txt.py on every episode
                            returns P0=0. P1 advisories are WARN-only in
                            default mode; --strict elevates P1 to blocking.
  G5  State checkpoint    : _workspace/books/<slug>/_system/orchestrator-
                            state.json shows phase=done OR (phase=per-chapter
                            AND phase_status=ship-with-caution|ship-ready).
  G6  Library-target sane : library/books/<slug>/ either doesn't exist or
                            --overwrite (default) wipe-and-recreates it.
                            --no-wipe coexists with prior content.

OUTPUT under library/books/<slug>/:

  chapters/                 — copied verbatim from _workspace/books/<slug>/chapters/
  episodes/                 — copied verbatim from _workspace/books/<slug>/episodes/
  README.md                 — generated; lists episode count, publish timestamp,
                              source git SHA (develop tip), EP→chapter pair table,
                              NotebookLM upload instructions.

The `library/_meta/catalog.md` row for <slug> is updated (or appended).

USAGE:

  scripts/podcast/publish_to_library.py <book-slug> [options]

OPTIONS:

  --strict      Elevate P1 advisories to blocking (default: P1 is warn-only).
  --no-wipe     Skip the wipe step; coexist with prior content at
                library/books/<slug>/.
  --dry-run     Run all gates + print the would-copy file list; do not write.
  --force       Skip G5 state-checkpoint gate (the per-chapter halts can leave
                state.json mid-flight; use cautiously).

EXIT CODES:

  0  — publish succeeded (or --dry-run completed all gates).
  1  — gate failed; publish aborted.
  2  — bad input (slug missing, workspace not found, etc).
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = REPO_ROOT / "_workspace" / "books"
# Option 2 layout: library/ lives above the worktree at <podcast-factory>/library/,
# two parents up from REPO_ROOT. Works from any worktree.
LIBRARY = REPO_ROOT.parent.parent / "library"

SHIPPABLE_STATUSES = {"shipped", "ship-ready", "ship-with-caution",
                      "ship-with-caution-approved", "halted_by_operator"}

CH_PATTERN = re.compile(r"^ch(\d+)-([a-z0-9][a-z0-9-]*)\.txt$")
EP_PATTERN = re.compile(r"^EP(\d+)-([a-z0-9][a-z0-9-]*)\.txt$")


def _info(msg: str) -> None:
    print(msg)


def _warn(msg: str) -> None:
    print(f"WARN  {msg}", file=sys.stderr)


def _fail(gate: str, msg: str) -> None:
    print(f"FAIL  [{gate}] {msg}", file=sys.stderr)


def _ok(gate: str, msg: str) -> None:
    print(f"OK    [{gate}] {msg}")


def git_sha() -> str:
    r = subprocess.run(["git", "rev-parse", "HEAD"],
                       cwd=REPO_ROOT, capture_output=True, text=True)
    return r.stdout.strip()[:12] if r.returncode == 0 else "unknown"


def git_branch() -> str:
    r = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                       cwd=REPO_ROOT, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else "unknown"


def gate_g1_structure(workspace: Path) -> tuple[bool, list[Path], list[Path]]:
    chap_dir = workspace / "chapters"
    ep_dir = workspace / "episodes"
    if not chap_dir.is_dir() or not ep_dir.is_dir():
        _fail("G1", f"missing chapters/ or episodes/ under {workspace}")
        return False, [], []
    chapters = sorted(p for p in chap_dir.glob("ch*.txt") if p.is_file())
    episodes = sorted(p for p in ep_dir.glob("EP*.txt") if p.is_file())
    if not chapters or not episodes:
        _fail("G1", f"no chapters/ or episodes/ content "
                    f"(chapters={len(chapters)}, episodes={len(episodes)})")
        return False, [], []
    _ok("G1", f"{len(chapters)} chapters + {len(episodes)} episodes present")
    return True, chapters, episodes


def gate_g2_pairs(chapters: list[Path], episodes: list[Path]) -> bool:
    ch_keys = {(int(m.group(1)), m.group(2)) for p in chapters
               if (m := CH_PATTERN.match(p.name))}
    ep_keys = {(int(m.group(1)), m.group(2)) for p in episodes
               if (m := EP_PATTERN.match(p.name))}
    unparseable_ch = [p.name for p in chapters if not CH_PATTERN.match(p.name)]
    unparseable_ep = [p.name for p in episodes if not EP_PATTERN.match(p.name)]
    if unparseable_ch or unparseable_ep:
        _fail("G2", f"unparseable filenames: chapters={unparseable_ch[:3]}, "
                    f"episodes={unparseable_ep[:3]}")
        return False
    missing_episodes = ch_keys - ep_keys
    missing_chapters = ep_keys - ch_keys
    if missing_episodes or missing_chapters:
        _fail("G2", f"chapter/episode pair mismatch: "
                    f"chapters without episodes={sorted(missing_episodes)[:3]}, "
                    f"episodes without chapters={sorted(missing_chapters)[:3]}")
        return False
    _ok("G2", f"{len(ch_keys)} chapter/episode pairs match")
    return True


def gate_g3_sequential(chapters: list[Path], episodes: list[Path]) -> bool:
    ch_nums = sorted(int(m.group(1)) for p in chapters
                     if (m := CH_PATTERN.match(p.name)))
    ep_nums = sorted(int(m.group(1)) for p in episodes
                     if (m := EP_PATTERN.match(p.name)))
    if ch_nums != list(range(1, len(ch_nums) + 1)):
        _fail("G3", f"chapter numbers not purely sequential 1..N: {ch_nums}")
        return False
    if ep_nums != list(range(1, len(ep_nums) + 1)):
        _fail("G3", f"episode numbers not purely sequential 1..N: {ep_nums}")
        return False
    # Reject any letter suffix (catches ch03a, ch14b that slipped past CH_PATTERN
    # since the pattern would not match them anyway). Belt-and-suspenders.
    suffix_re = re.compile(r"^(ch|EP)\d+[a-z]+-", re.IGNORECASE)
    bad = [p.name for p in chapters + episodes if suffix_re.match(p.name)]
    if bad:
        _fail("G3", f"letter-suffix names detected: {bad[:3]}")
        return False
    _ok("G3", f"chapters {ch_nums[0]}..{ch_nums[-1]} + episodes "
              f"{ep_nums[0]}..{ep_nums[-1]} purely sequential")
    return True


def gate_g4_build_clean(workspace: Path, slug: str,
                        episodes: list[Path], strict: bool) -> bool:
    builder = REPO_ROOT / "scripts" / "podcast" / "build_episode_txt.py"
    if not builder.exists():
        _warn(f"build_episode_txt.py not found at {builder}; skipping G4")
        return True
    book_dir = workspace.relative_to(REPO_ROOT)
    p0_total = 0
    p1_total = 0
    for ep in episodes:
        ep_id = ep.stem  # EP01-the-perfect-and-the-perfection-of-the-soul
        r = subprocess.run(
            ["python3", str(builder), str(book_dir), ep_id],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        p0 = len(re.findall(r"^FLAG \(P0\)", r.stdout + r.stderr, re.MULTILINE))
        p1 = len(re.findall(r"^FLAG \(P1\)", r.stdout + r.stderr, re.MULTILINE))
        if p0 > 0:
            _fail("G4", f"{ep_id}: {p0} P0 flag(s)")
        elif p1 > 0:
            (_fail if strict else _warn)(
                f"G4 {ep_id}: {p1} P1 advisor{'ies' if p1 != 1 else 'y'}"
                + (" (strict mode blocks)" if strict else " (warn-only)")
            )
        p0_total += p0
        p1_total += p1
    if p0_total > 0:
        _fail("G4", f"{p0_total} total P0 flags across {len(episodes)} episodes")
        return False
    if strict and p1_total > 0:
        _fail("G4", f"--strict: {p1_total} total P1 advisories block publish")
        return False
    _ok("G4", f"P0=0 across {len(episodes)} episodes "
              f"(P1={p1_total}, {'blocking' if strict else 'warn-only'})")
    return True


def gate_g5_state(workspace: Path, force: bool) -> bool:
    if force:
        _ok("G5", "--force: state checkpoint skipped")
        return True
    state_path = workspace / "_system" / "orchestrator-state.json"
    if not state_path.exists():
        _fail("G5", f"orchestrator-state.json not found at {state_path}")
        return False
    state = json.loads(state_path.read_text())
    phase = state.get("phase")
    phase_status = state.get("phase_status")
    if phase == "done":
        _ok("G5", f"state.json phase=done")
        return True
    if phase == "per-chapter" and phase_status in SHIPPABLE_STATUSES:
        _ok("G5", f"state.json phase=per-chapter phase_status={phase_status}")
        return True
    _fail("G5", f"state.json not in shippable state "
                f"(phase={phase}, phase_status={phase_status}). "
                f"Use --force to bypass.")
    return False


def gate_g6_target(target: Path, no_wipe: bool) -> bool:
    if not target.exists():
        _ok("G6", f"target {target} doesn't exist; will create")
        return True
    if no_wipe:
        _ok("G6", f"--no-wipe: coexisting with prior content at {target}")
        return True
    # Default: wipe-and-recreate is implicit; gate just confirms the target is
    # a directory we can safely remove (not a symlink, not outside LIBRARY).
    try:
        target.relative_to(LIBRARY)
    except ValueError:
        _fail("G6", f"target {target} is outside LIBRARY {LIBRARY} (refusing wipe)")
        return False
    if target.is_symlink():
        _fail("G6", f"target {target} is a symlink (refusing wipe)")
        return False
    _ok("G6", f"target {target} exists; wipe-and-recreate authorized")
    return True


def render_readme(slug: str, chapters: list[Path], episodes: list[Path],
                  source_sha: str, source_branch: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    pairs = []
    for ep in episodes:
        m = EP_PATTERN.match(ep.name)
        if not m:
            continue
        num, ep_slug = m.group(1), m.group(2)
        ch_name = f"ch{num}-{ep_slug}.txt"
        pairs.append((num, ch_name, ep.name, ep_slug))
    pair_rows = "\n".join(
        f"| EP{num} | `chapters/{ch_name}` | `episodes/{ep_name}` | {ep_slug.replace('-', ' ')} |"
        for num, ch_name, ep_name, ep_slug in pairs
    )
    return f"""# {slug} — published podcast assets

Published from `_workspace/books/{slug}/` to this directory on **{ts}**.

- **Source git ref:** `{source_branch}@{source_sha}`
- **Episode count:** {len(episodes)}
- **NotebookLM mode:** 2-voice Extended Deep Dive

## NotebookLM upload (per episode)

For each EP## row below:

1. Create a new NotebookLM notebook (or open an existing one).
2. Upload `chapters/ch##-<slug>.txt` as the single source.
3. Open the Customize prompt box and paste the contents of `episodes/EP##-<slug>.txt`.
4. Click **Generate**.

The chapter file is the SOURCE (uploaded as-is); the episode file is the CUSTOMIZE PROMPT (pasted into the prompt box). Do not concatenate them — NotebookLM treats them as different inputs.

## Episode list

| EP | Chapter file (SOURCE) | Episode file (CUSTOMIZE PROMPT) | Topic |
|---|---|---|---|
{pair_rows}

## Republishing

This directory is **filesystem-only** and **not git-tracked**. It can be deleted and regenerated at any time by re-running:

```
scripts/podcast/publish_to_library.py {slug}
```

from any worktree on the `podcast-factory` repo (the script resolves `library/` from `<repo-parent>/library/`).
"""


def update_catalog(slug: str, episode_count: int, source_sha: str) -> None:
    catalog_path = LIBRARY / "_meta" / "catalog.md"
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    new_row = (f"| [{slug}](../books/{slug}/README.md) | {episode_count} | "
               f"{ts} | `{source_sha}` |")
    header = ("# library/ — published catalog\n\n"
              "Auto-updated by `scripts/podcast/publish_to_library.py`. Each row\n"
              "tracks one published book. Republish a book to refresh its row.\n\n"
              "| Book | Episodes | Latest publish date | Source git SHA |\n"
              "|---|---|---|---|\n")

    def is_stale_format(text: str) -> bool:
        # Stale = legacy ship_to_library.py header (4-col with Verdict + Phase)
        # or missing the new tool's auto-update marker line.
        return ("Auto-generated by `scripts/podcast/ship_to_library.py`" in text
                or "| Latest verdict |" in text
                or "publish_to_library.py" not in text)

    if not catalog_path.exists():
        catalog_path.write_text(header + new_row + "\n")
        _info(f"    catalog: created {catalog_path.relative_to(LIBRARY.parent)} "
              f"with row for {slug}")
        return

    existing = catalog_path.read_text()
    if is_stale_format(existing):
        # Salvage any prior book-slug rows so we don't lose them, but rewrite
        # header + columns. Old rows had different columns; we drop those and
        # only preserve the book-slug link as a best-effort.
        prior_slugs = set(re.findall(r"\| \[([a-z0-9][a-z0-9-]*)\]", existing))
        prior_slugs.discard(slug)
        rows = [new_row]
        for ps in sorted(prior_slugs):
            rows.append(f"| [{ps}](../books/{ps}/README.md) | ? | (legacy) | `unknown` |")
        catalog_path.write_text(header + "\n".join(rows) + "\n")
        _info(f"    catalog: rewrote stale-format catalog; "
              f"{len(prior_slugs)} legacy row(s) preserved with placeholders")
        return

    lines = existing.splitlines()
    row_re = re.compile(rf"^\| \[{re.escape(slug)}\]")
    found = False
    for i, line in enumerate(lines):
        if row_re.match(line):
            lines[i] = new_row
            found = True
            break
    if not found:
        # Append before any trailing blank lines
        while lines and not lines[-1].strip():
            lines.pop()
        lines.append(new_row)
    catalog_path.write_text("\n".join(lines) + "\n")
    _info(f"    catalog: {'updated' if found else 'appended'} row for {slug}")


def publish(slug: str, args: argparse.Namespace) -> int:
    workspace = WORKSPACE / slug
    if not workspace.is_dir():
        print(f"publish_to_library: workspace not found: {workspace}",
              file=sys.stderr)
        return 2
    target = LIBRARY / "books" / slug

    _info(f"==> publish_to_library: {slug}")
    _info(f"    workspace: {workspace.relative_to(REPO_ROOT)}")
    _info(f"    target:    {target}")
    _info(f"    mode:      "
          f"{'dry-run' if args.dry_run else 'live'}"
          f"{', strict' if args.strict else ''}"
          f"{', no-wipe' if args.no_wipe else ''}"
          f"{', force' if args.force else ''}")
    _info("")
    _info("=== Gates ===")

    ok1, chapters, episodes = gate_g1_structure(workspace)
    if not ok1:
        return 1
    if not gate_g2_pairs(chapters, episodes):
        return 1
    if not gate_g3_sequential(chapters, episodes):
        return 1
    if not gate_g4_build_clean(workspace, slug, episodes, args.strict):
        return 1
    if not gate_g5_state(workspace, args.force):
        return 1
    if not gate_g6_target(target, args.no_wipe):
        return 1

    _info("")
    _info("=== Plan ===")
    _info(f"    would copy {len(chapters)} chapter(s) → {target}/chapters/")
    _info(f"    would copy {len(episodes)} episode(s) → {target}/episodes/")
    _info(f"    would write {target}/README.md")
    _info(f"    would update catalog row for {slug}")

    if args.dry_run:
        _info("")
        _info("==> DRY RUN: no files written. All gates passed.")
        return 0

    # Live publish
    _info("")
    _info("=== Publishing ===")
    if target.exists() and not args.no_wipe:
        shutil.rmtree(target)
        _info(f"    wiped: {target}")
    target.mkdir(parents=True, exist_ok=True)
    (target / "chapters").mkdir(exist_ok=True)
    (target / "episodes").mkdir(exist_ok=True)

    for chap in chapters:
        shutil.copy2(chap, target / "chapters" / chap.name)
    _info(f"    copied {len(chapters)} chapter(s)")
    for ep in episodes:
        shutil.copy2(ep, target / "episodes" / ep.name)
    _info(f"    copied {len(episodes)} episode(s)")

    sha = git_sha()
    branch = git_branch()
    readme = render_readme(slug, chapters, episodes, sha, branch)
    (target / "README.md").write_text(readme)
    _info(f"    wrote README.md")

    update_catalog(slug, len(episodes), sha)

    _info("")
    _info(f"==> DONE. Published {len(episodes)} episode(s) for {slug} "
          f"to {target}.")
    _info(f"    Inspect: open '{target}/README.md'")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="On-demand publish from _workspace/books/<slug>/ to library/books/<slug>/.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("slug", help="Book slug (e.g. kitab-al-riyad).")
    parser.add_argument("--strict", action="store_true",
                        help="Elevate P1 advisories to blocking.")
    parser.add_argument("--no-wipe", action="store_true",
                        help="Skip wipe step; coexist with prior content.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run gates + print plan; do not write.")
    parser.add_argument("--force", action="store_true",
                        help="Skip G5 state-checkpoint gate.")
    args = parser.parse_args()

    if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", args.slug):
        print(f"publish_to_library: invalid slug '{args.slug}' "
              f"(must be lowercase-kebab-case)", file=sys.stderr)
        return 2

    return publish(args.slug, args)


if __name__ == "__main__":
    sys.exit(main())
