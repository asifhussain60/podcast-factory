#!/usr/bin/env python3
"""promote_staging_to_book.py — consolidate staging corpora into a canonical book.

An audio-sourced book may be transcribed in pieces: a SPINE corpus (the core
text) plus one or more AUGMENTATION corpora (other teachers' lecture sets on the
same subject), each transcribed in its own staging workspace with a throwaway
`*-staging` / `*-augment` slug. This step promotes them into ONE canonical book
slug with a single orchestrator-state.json, so the rest of the pipeline (synthesis
→ 0b → … → publish) runs against the clean slug from the start.

Deterministic. Zero LLM. Pure filesystem + JSON. Idempotent (copies, never moves
that destroy provenance; the canonical state file is written LAST so a half-run
never looks complete).

Layout produced under `content/<Bucket>/<slug>/`:
  _system/orchestrator-state.json                  ← single canonical state (LAST)
  _system/source/lectures/                         ← spine lectures + provenance
  _system/source/text/raw-extract.md               ← spine faithful master
  _system/source/multi/denoised/spine.md           ← spine denoised stream
  _system/source/augmentation/<name>/raw-extract.md  ← each augmentation master
  _system/source/augmentation/<name>/lectures/       ← each augmentation lectures
  _system/source/augmentation/_manifest.json       ← deterministic input contract
  _system/cost-ledger.jsonl                        ← all staging spend, concatenated
  _system/cost-ledger-provenance.json              ← per-staging-slug spend audit
  _system/staging-archive/<slug>-state.json        ← each staging state, archived

The staging `source/` and `augmentation/<name>/` dirs are left in place (the
irreplaceable mp3 audio lives there); promotion only COPIES out of them.

Usage:
  python3 scripts/podcast/promote_staging_to_book.py --slug al-anwaar-al-lateefah [--dry-run] [--force]
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from _paths import REPO_ROOT, find_content, resolve_bucket  # noqa: E402
from _branching import branch_name  # noqa: E402

EXIT_OK = 0
EXIT_ERROR = 2


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return p.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(p)


def _read_state(d: Path) -> dict[str, Any] | None:
    p = d / "_system" / "orchestrator-state.json"
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


class _Plan:
    """Accumulates copy/write ops so --dry-run can print them without touching disk."""

    def __init__(self, dry_run: bool) -> None:
        self.dry_run = dry_run
        self.ops: list[str] = []

    def copy_file(self, src: Path, dst: Path) -> None:
        self.ops.append(f"COPY  {_rel(src)}  ->  {_rel(dst)}")
        if not self.dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    def copy_tree(self, src: Path, dst: Path) -> int:
        n = 0
        for f in sorted(src.rglob("*")):
            if f.is_file():
                self.copy_file(f, dst / f.relative_to(src))
                n += 1
        return n

    def write_text(self, dst: Path, content: str, label: str) -> None:
        self.ops.append(f"WRITE {label}  ->  {_rel(dst)}")
        if not self.dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(content, encoding="utf-8")

    def append_lines(self, dst: Path, lines: list[str], label: str) -> None:
        self.ops.append(f"APPEND {label} ({len(lines)} lines)  ->  {_rel(dst)}")
        if not self.dry_run and lines:
            dst.parent.mkdir(parents=True, exist_ok=True)
            with dst.open("a", encoding="utf-8") as fh:
                fh.write("\n".join(lines) + "\n")


def _discover(book_dir: Path) -> tuple[Path | None, list[tuple[str, Path]]]:
    """Return (spine_dir, [(name, augmentation_dir), ...]).

    Spine = the `source/` child whose state slug ends in `-staging`.
    Augmentations = `augmentation/<name>/` children with a state slug ending `-augment`.
    Dirs without a state file (raw mp3 drops) are ignored.
    """
    spine = None
    src = book_dir / "source"
    if (st := _read_state(src)) and str(st.get("book_slug", "")).endswith("-staging"):
        spine = src

    augs: list[tuple[str, Path]] = []
    aug_root = book_dir / "augmentation"
    if aug_root.is_dir():
        for child in sorted(aug_root.iterdir()):
            if not child.is_dir():
                continue
            st = _read_state(child)
            if st and str(st.get("book_slug", "")).endswith("-augment"):
                augs.append((child.name, child))
    return spine, augs


def promote(slug: str, *, dry_run: bool = False, force: bool = False) -> int:
    hit = find_content(slug)
    book_dir = hit[2] if hit else None
    if book_dir is None or not book_dir.is_dir():
        print(f"promote: book dir not found for slug {slug!r}", file=sys.stderr)
        return EXIT_ERROR

    canonical_state = book_dir / "_system" / "orchestrator-state.json"
    if canonical_state.is_file() and not force:
        print(f"promote: canonical state already exists ({_rel(canonical_state)}); "
              f"use --force to re-promote.")
        return EXIT_OK

    spine, augs = _discover(book_dir)
    if spine is None:
        print(f"promote: no spine staging workspace (source/ with a *-staging slug) "
              f"under {_rel(book_dir)}", file=sys.stderr)
        return EXIT_ERROR

    spine_state = _read_state(spine) or {}
    bucket = resolve_bucket(bucket=None, profile=None, category=spine_state.get("category"))
    plan = _Plan(dry_run)

    print(f"promote: {slug}  (bucket={bucket})")
    print(f"  spine: {_rel(spine)}  slug={spine_state.get('book_slug')}  "
          f"lectures={spine_state.get('phases', {}).get('0a', {}).get('lectures')}")
    for name, d in augs:
        st = _read_state(d) or {}
        print(f"  aug:   {name:<20} slug={st.get('book_slug')}  "
              f"lectures={st.get('phases', {}).get('0a', {}).get('lectures')}")

    sys_dir = book_dir / "_system"

    # 1 — spine corpus into canonical root
    sp_lec = spine / "_system" / "source" / "lectures"
    if sp_lec.is_dir():
        plan.copy_tree(sp_lec, sys_dir / "source" / "lectures")
    sp_raw = spine / "_system" / "source" / "text" / "raw-extract.md"
    if sp_raw.is_file():
        plan.copy_file(sp_raw, sys_dir / "source" / "text" / "raw-extract.md")
    sp_denoised = spine / "_system" / "source" / "multi" / "denoised"
    if sp_denoised.is_dir():
        for f in sorted(sp_denoised.glob("*.md")):
            plan.copy_file(f, sys_dir / "source" / "multi" / "denoised" / "spine.md")
            break  # the single synthesized stream

    # 2 — augmentation corpora under a permanent namespaced home + manifest
    manifest: list[dict[str, Any]] = []
    for name, d in augs:
        st = _read_state(d) or {}
        a_lec = d / "_system" / "source" / "lectures"
        a_raw = d / "_system" / "source" / "text" / "raw-extract.md"
        dst_root = sys_dir / "source" / "augmentation" / name
        if a_lec.is_dir():
            plan.copy_tree(a_lec, dst_root / "lectures")
        if a_raw.is_file():
            plan.copy_file(a_raw, dst_root / "raw-extract.md")
        manifest.append({
            "name": name,
            "staging_slug": st.get("book_slug"),
            "lectures": st.get("phases", {}).get("0a", {}).get("lectures"),
            "source_language": st.get("source_language"),
            "raw_extract": (dst_root / "raw-extract.md").relative_to(book_dir).as_posix(),
            "origin_state": (d / "_system" / "orchestrator-state.json").relative_to(book_dir).as_posix(),
        })
    plan.write_text(sys_dir / "source" / "augmentation" / "_manifest.json",
                    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                    "augmentation manifest")

    # 3 — preserve every cost ledger + archive every staging state
    ledger_prov: dict[str, dict[str, Any]] = {}
    for d in [spine] + [ad for _n, ad in augs]:
        st = _read_state(d) or {}
        slug_d = st.get("book_slug") or d.name
        led = d / "_system" / "cost-ledger.jsonl"
        rows: list[str] = []
        total = 0.0
        if led.is_file():
            for line in led.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                rows.append(line)
                try:
                    total += float(json.loads(line).get("cost_usd", 0) or 0)
                except Exception:
                    pass
        plan.append_lines(sys_dir / "cost-ledger.jsonl", rows, f"ledger[{slug_d}]")
        ledger_prov[slug_d] = {"rows": len(rows), "total_usd": round(total, 4)}
        # archive staging state
        sp_state = d / "_system" / "orchestrator-state.json"
        if sp_state.is_file():
            plan.copy_file(sp_state, sys_dir / "staging-archive" / f"{slug_d}-state.json")
    plan.write_text(sys_dir / "cost-ledger-provenance.json",
                    json.dumps(ledger_prov, ensure_ascii=False, indent=2) + "\n",
                    "cost-ledger provenance")

    # 4 — canonical orchestrator-state.json (WRITTEN LAST — the existence signal)
    now = _utc()
    spine_lectures = spine_state.get("phases", {}).get("0a", {}).get("lectures")
    aug_lectures = sum((m.get("lectures") or 0) for m in manifest)
    canonical = {
        "schema_version": 1,
        "book_slug": slug,
        "source_kind": spine_state.get("source_kind", "audio"),
        "input_type": spine_state.get("input_type", "audio"),
        "source_language": spine_state.get("source_language", "ur"),
        "category": spine_state.get("category", "lectures"),
        "branch": branch_name(spine_state.get("category"), slug, bucket=bucket),
        "status": "draft",
        "phase": "0a-synthesize",
        "phase_status": "pending",
        "last_completed_phase": "0a",
        "last_error": None,
        "started": spine_state.get("started", now),
        "updated": now,
        "phases": {
            "0a": {
                "completed_via": "promote_staging_to_book.py (consolidated staging corpora)",
                "completed_at": now,
                "lectures": spine_lectures,
                "augmentation_corpora": len(manifest),
                "augmentation_lectures": aug_lectures,
                "engine": spine_state.get("phases", {}).get("0a", {}).get("engine"),
                "source_language": spine_state.get("source_language"),
            },
        },
        "multi_source": {
            "spine_slug": spine_state.get("book_slug"),
            "augmentation_manifest": "_system/source/augmentation/_manifest.json",
            "model": "spine+curated-merge+atoms",
        },
        "intake_via": "scripts/podcast/promote_staging_to_book.py",
    }
    plan.write_text(canonical_state,
                    json.dumps(canonical, ensure_ascii=False, indent=2) + "\n",
                    "CANONICAL orchestrator-state.json")

    # 5 — wire the branch (skip in dry-run; leave tree dirty for review)
    target_branch = branch_name(spine_state.get("category"), slug, bucket=bucket)
    if dry_run:
        plan.ops.append(f"BRANCH (skipped in dry-run): would ensure {target_branch}")
    else:
        _ensure_branch(target_branch)

    # report
    print()
    print(f"  plan: {len(plan.ops)} ops"
          f"{'  (DRY-RUN — nothing written)' if dry_run else ''}")
    for op in plan.ops:
        print(f"    {op}")
    print()
    if dry_run:
        print(f"  spine lectures={spine_lectures}  augmentation lectures={aug_lectures}  "
              f"({len(manifest)} corpora)")
        print("  Re-run without --dry-run to execute.")
    else:
        print(f"==> promoted {slug}: spine={spine_lectures} + aug={aug_lectures} lectures, "
              f"state→0a-synthesize/pending. Next: multi_source_synthesis.py --slug {slug}")
    return EXIT_OK


def _ensure_branch(target: str) -> None:
    import subprocess
    def _git(*a: str) -> tuple[int, str]:
        p = subprocess.run(["git", *a], cwd=REPO_ROOT, capture_output=True, text=True)
        return p.returncode, (p.stdout + p.stderr).strip()
    rc, cur = _git("rev-parse", "--abbrev-ref", "HEAD")
    cur = cur if rc == 0 else ""
    if cur == target:
        print(f"  branch: already on {target}")
        return
    rc, _ = _git("rev-parse", "--verify", target)
    if rc == 0:
        rc2, out = _git("checkout", target)
        print(f"  branch: checked out existing {target}" if rc2 == 0 else f"  branch: checkout failed: {out}")
    else:
        rc2, out = _git("checkout", "-b", target)
        print(f"  branch: created {target}" if rc2 == 0 else f"  branch: create failed: {out}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--slug", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="re-promote even if canonical state exists")
    args = ap.parse_args()
    return promote(args.slug, dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    raise SystemExit(main())
