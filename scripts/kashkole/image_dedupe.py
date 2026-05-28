"""Image deduplicator for the autonomous KAHSKOLE rollout.

Groups all PNG images across the bundle tree by SHA-256. Surfaces unique
hashes that don't yet have a 'canonical' sidecar. Lets us classify one
representative per hash and copy that sidecar to all byte-identical siblings.

Usage:
  python scripts/kashkole/image_dedupe.py scan         # show all unique hashes
  python scripts/kashkole/image_dedupe.py pending      # unique hashes lacking a canonical
  python scripts/kashkole/image_dedupe.py propagate    # for each hash with one or more sidecars, copy sidecar to all PNGs that share the hash
"""
from __future__ import annotations
import hashlib
import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
EXTRACT_ROOT = REPO_ROOT / "CONTENT" / "_shared" / "source-library" / "extracted" / "kashkole"


def all_pngs() -> list[Path]:
    return sorted(EXTRACT_ROOT.glob("*/*/_system/source/images/*.png"))


def png_sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def group_by_hash() -> dict[str, list[Path]]:
    groups: dict[str, list[Path]] = defaultdict(list)
    for p in all_pngs():
        groups[png_sha(p)].append(p)
    return groups


def cmd_scan() -> None:
    groups = group_by_hash()
    print(f"# Total PNGs: {sum(len(v) for v in groups.values())}")
    print(f"# Unique hashes: {len(groups)}")
    sizes = sorted(((len(v), h, v[0]) for h, v in groups.items()), reverse=True)
    print(f"# Top hashes by duplicate count:")
    for count, h, sample in sizes[:30]:
        sidecar = sample.with_suffix(".json")
        marker = "  (HAS_SIDECAR)" if sidecar.exists() else "  (NO_SIDECAR)"
        print(f"  {count:>4d}  {h[:12]}  sample={sample.relative_to(REPO_ROOT)}{marker}")


def cmd_pending() -> None:
    """List hashes where NO instance has a sidecar."""
    groups = group_by_hash()
    pending: list[tuple[int, str, Path]] = []
    for h, ps in groups.items():
        if not any(p.with_suffix(".json").exists() for p in ps):
            pending.append((len(ps), h, ps[0]))
    pending.sort(reverse=True)
    print(f"# Unique hashes without any sidecar: {len(pending)}")
    print(f"# Total PNG instances covered: {sum(c for c, _, _ in pending)}")
    for count, h, sample in pending:
        print(f"  {count:>4d}  {h[:12]}  {sample.relative_to(REPO_ROOT)}")


def cmd_propagate() -> None:
    """For every hash group with at least one sidecar, copy that sidecar to
    all other instances. If multiple instances have sidecars and they differ,
    skip (leave both — human will reconcile). Otherwise copy."""
    groups = group_by_hash()
    copied = 0
    skipped_conflict = 0
    already_set = 0
    for h, ps in groups.items():
        with_sidecar = [p for p in ps if p.with_suffix(".json").exists()]
        if not with_sidecar:
            continue
        # If multiple sidecars exist, check they're identical.
        sidecar_contents = []
        for p in with_sidecar:
            try:
                sidecar_contents.append(p.with_suffix(".json").read_text(encoding="utf-8"))
            except Exception:
                pass
        unique = set(sidecar_contents)
        if len(unique) > 1:
            skipped_conflict += 1
            print(f"  CONFLICT  {h[:12]}  multiple sidecars differ:")
            for p in with_sidecar:
                print(f"    {p.relative_to(REPO_ROOT)}")
            continue
        canonical = with_sidecar[0].with_suffix(".json")
        for p in ps:
            target = p.with_suffix(".json")
            if target.exists():
                already_set += 1
                continue
            shutil.copy(canonical, target)
            copied += 1
    print(f"# Propagated {copied} sidecars; {already_set} already set; "
          f"{skipped_conflict} conflicts skipped.")


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    phase = sys.argv[1]
    if phase == "scan":
        cmd_scan()
    elif phase == "pending":
        cmd_pending()
    elif phase == "propagate":
        cmd_propagate()
    else:
        print(f"Unknown phase: {phase}")
        sys.exit(2)


if __name__ == "__main__":
    main()
