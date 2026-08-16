#!/usr/bin/env python3
"""Reclaim disk from regenerable artifacts. Dry-run by default.

The final pass of a repo-surgeon run. `repo_surgeon_probe.py` REPORTS debris and
never removes it — it is wired into a pre-commit hook and CI, and a gate that
deletes files as a side effect of running is one people are right to route around.
This script is the executor, and it is a separate command that a human types.

What may be reclaimed and what may never be is read from `hygiene:` in
`.repo-audit/profile.yaml`, not decided here. Four refusals are structural rather
than configured, because each is a way a cleanup script destroys something real:

  1. A TRACKED file is never debris. Whatever a glob says, if git knows about it,
     this script will not remove it.
  2. `protected_runtime` paths are refused by prefix — the local D1 among them,
     because deleting it wipes the `session` table and silently signs the operator
     out of localhost, so the site shows a sign-in page and looks like nothing
     shipped. CLAUDE.md bans that by name.
  3. Nothing outside the repository root is touched, symlinks included: every
     candidate is resolved and re-checked before it is passed to a delete.
  4. Categories marked `confirm: true` are skipped unless named with --include.
     Large, app-adjacent, or slow to rebuild — the operator decides, not a default.

Untracked material that is NOT regenerable (experiment output, inbox drops) is
reported and never swept. A cleanup that guesses at somebody's working files is
the one you cannot undo.

Usage:
    python3 scripts/repo_cleanup.py                     # report what would go
    python3 scripts/repo_cleanup.py --apply             # sweep the safe categories
    python3 scripts/repo_cleanup.py --apply --include git-maintenance
    python3 scripts/repo_cleanup.py --json

Exit codes:
    0  ran (whether or not anything was reclaimable)
    2  could not run (no contract, not a git repo)
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - PyYAML is in requirements.txt
    print("repo_cleanup: PyYAML is required (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

MB = 1024 * 1024
# Directories whose contents belong to somebody else's tool. A `**/__pycache__`
# sweep that walks into node_modules reports a number the operator cannot act on.
SKIP_PARTS = (".git/", "node_modules/", ".venv/")


def human(n: int) -> str:
    return f"{n / MB:.1f} MB" if n >= MB else f"{n / 1024:.0f} KB"


@dataclass
class Candidate:
    path: Path
    rel: str
    size: int
    category: str


@dataclass
class Cleanup:
    root: Path
    profile: dict
    candidates: list[Candidate] = field(default_factory=list)
    refused: list[tuple[str, str]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    tracked: set[str] = field(default_factory=set)

    # ---------- safety ----------

    def load_tracked(self) -> None:
        out = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        ).stdout
        self.tracked = set(filter(None, out.split("\0")))

    def protected_prefixes(self) -> list[str]:
        hygiene = self.profile.get("hygiene") or {}
        out = [str(e.get("path") or "").strip() for e in (hygiene.get("protected_runtime") or [])]
        # The contract's own `protected:` list governs here too. It exists to stop
        # an audit rewriting the data; it must equally stop a sweep deleting it.
        for entry in self.profile.get("protected") or []:
            out.append(str(entry).split("#", 1)[0].strip().replace("/**", ""))
        return [p for p in out if p]

    def refuse(self, rel: str, why: str) -> None:
        self.refused.append((rel, why))

    def admissible(self, path: Path, rel: str) -> bool:
        """Every reason NOT to delete something, checked before it is offered."""
        if rel in self.tracked:
            self.refuse(rel, "tracked by git — a tracked file is never debris")
            return False
        if any(rel == p or rel.startswith(f"{p}/") for p in self.protected_prefixes()):
            self.refuse(rel, "protected by the contract")
            return False
        if path.is_symlink():
            self.refuse(rel, "a symlink — following it would delete outside the repo")
            return False
        try:
            resolved = path.resolve()
            resolved.relative_to(self.root.resolve())
        except (OSError, ValueError):
            self.refuse(rel, "resolves outside the repository root")
            return False
        # A directory holding even one tracked file is not a build artifact.
        if path.is_dir() and any(t.startswith(f"{rel}/") for t in self.tracked):
            self.refuse(rel, "contains tracked files")
            return False
        return True

    # ---------- discovery ----------

    def size_of(self, path: Path) -> int:
        if path.is_file():
            try:
                return path.stat().st_size
            except OSError:
                return 0
        total = 0
        for p in path.rglob("*"):
            try:
                if p.is_file() and not p.is_symlink():
                    total += p.stat().st_size
            except OSError:
                continue
        return total

    def resolve_pattern(self, pattern: str) -> list[Path]:
        if "*" not in pattern:
            p = self.root / pattern
            return [p] if p.exists() else []
        out = []
        for hit in self.root.glob(pattern):
            rel = hit.relative_to(self.root).as_posix()
            if any(part in f"{rel}/" for part in SKIP_PARTS):
                continue
            out.append(hit)
        return sorted(out)

    def collect(self, include: set[str]) -> None:
        for entry in (self.profile.get("hygiene") or {}).get("reclaimable") or []:
            name = str(entry.get("name") or "?")
            if entry.get("confirm") and name not in include:
                self.notes.append(f"{name}: skipped — needs --include {name}")
                continue
            if name == "git-maintenance":
                continue  # handled by run_git_maintenance, not by deleting a path
            patterns = entry.get("match")
            patterns = [patterns] if isinstance(patterns, str) else list(patterns or [])
            for pat in patterns:
                for hit in self.resolve_pattern(str(pat)):
                    rel = hit.relative_to(self.root).as_posix()
                    if not self.admissible(hit, rel):
                        continue
                    self.candidates.append(Candidate(hit, rel, self.size_of(hit), name))

    def survey_untracked(self, floor: int = 50 * MB) -> list[tuple[str, int]]:
        """Large untracked trees, REPORTED and never swept.

        These are somebody's working files — experiment output, inbox drops. A
        cleanup that guesses at them is the one that cannot be undone, so this
        surfaces the number and stops.
        """
        out = subprocess.run(
            ["git", "ls-files", "--others", "--directory", "--exclude-standard", "-z"],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        ).stdout
        swept = {c.rel for c in self.candidates}
        found = []
        for rel in filter(None, out.split("\0")):
            rel = rel.rstrip("/")
            if not rel or rel in swept or any(rel.startswith(f"{c}/") for c in swept):
                continue
            p = self.root / rel
            if not p.exists():
                continue
            size = self.size_of(p)
            if size >= floor:
                found.append((rel, size))
        return sorted(found, key=lambda x: -x[1])

    # ---------- execution ----------

    def apply(self) -> int:
        reclaimed = 0
        for c in self.candidates:
            # Re-check at the moment of deletion. The tree can change between the
            # survey and the sweep, and the survey is not the authority.
            if not self.admissible(c.path, c.rel):
                continue
            try:
                if c.path.is_dir():
                    shutil.rmtree(c.path)
                else:
                    c.path.unlink()
                reclaimed += c.size
            except OSError as exc:
                self.notes.append(f"could not remove {c.rel}: {exc}")
        return reclaimed

    def run_git_maintenance(self) -> int:
        """`git gc`, never a glob over .git/objects.

        Loose objects are only garbage if nothing references them, and the only
        thing that knows what is referenced is git. A glob here would delete
        history.
        """
        before = self.size_of(self.root / ".git")
        proc = subprocess.run(
            ["git", "gc", "--prune=now", "--quiet"],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            self.notes.append(f"git gc failed: {proc.stderr.strip().splitlines()[:1]}")
            return 0
        return max(0, before - self.size_of(self.root / ".git"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="actually remove (default is a dry run)")
    ap.add_argument("--include", nargs="*", default=[], metavar="CATEGORY", help="opt into a confirm-required category")
    ap.add_argument("--json", action="store_true", help="machine-readable")
    args = ap.parse_args()

    try:
        root = Path(
            subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        )
    except subprocess.CalledProcessError:
        print("repo_cleanup: not a git repository", file=sys.stderr)
        return 2

    profile_path = root / ".repo-audit/profile.yaml"
    if not profile_path.exists():
        print("repo_cleanup: no .repo-audit/profile.yaml — the hygiene rules live there", file=sys.stderr)
        return 2

    cleanup = Cleanup(root=root, profile=yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {})
    cleanup.load_tracked()
    include = set(args.include)
    cleanup.collect(include)
    cleanup.candidates.sort(key=lambda c: (-c.size, c.rel))

    by_cat: dict[str, tuple[int, int]] = {}
    for c in cleanup.candidates:
        n, size = by_cat.get(c.category, (0, 0))
        by_cat[c.category] = (n + 1, size + c.size)

    total = sum(c.size for c in cleanup.candidates)
    untracked = cleanup.survey_untracked()
    gc_reclaimed = 0

    if args.apply:
        total = cleanup.apply()
        if "git-maintenance" in include:
            gc_reclaimed = cleanup.run_git_maintenance()

    if args.json:
        print(
            json.dumps(
                {
                    "applied": args.apply,
                    "reclaimed_bytes": total + gc_reclaimed,
                    "categories": {k: {"count": n, "bytes": s} for k, (n, s) in sorted(by_cat.items())},
                    "refused": [{"path": p, "why": w} for p, w in cleanup.refused],
                    "large_untracked": [{"path": p, "bytes": s} for p, s in untracked],
                    "notes": cleanup.notes,
                },
                indent=2,
            )
        )
        return 0

    verb = "Reclaimed" if args.apply else "Would reclaim"
    if by_cat:
        for cat, (n, size) in sorted(by_cat.items(), key=lambda kv: -kv[1][1]):
            print(f"  {cat:<20} {n:>5} path(s)  {human(size):>10}")
    print(f"\n{verb}: {human(total + gc_reclaimed)}")
    if gc_reclaimed:
        print(f"  (of which git maintenance: {human(gc_reclaimed)})")

    # Both lines print at zero. A silent zero and an absent line read identically —
    # the same reasoning the probe's report footer is built on.
    print(f"{len(cleanup.refused)} path(s) refused on safety grounds")
    for rel, why in cleanup.refused[:10]:
        print(f"    - {rel}: {why}")
    if len(cleanup.refused) > 10:
        print(f"    ... and {len(cleanup.refused) - 10} more")

    print(f"{len(untracked)} large untracked tree(s) — reported, never swept")
    for rel, size in untracked[:10]:
        print(f"    - {rel}  {human(size)}  (yours to keep or remove)")

    for note in cleanup.notes:
        print(f"  note: {note}")
    if not args.apply and (by_cat or "git-maintenance" not in include):
        print("\nDry run. Re-run with --apply to execute.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
