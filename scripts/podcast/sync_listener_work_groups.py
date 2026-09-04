#!/usr/bin/env python3
"""sync_listener_work_groups.py — deterministic multi-volume grouping for the
Podcast Factory Library's `content_unit` table.

WHY THIS EXISTS
----------------
The `WorkCard` stacked-set feature reads exactly one thing to decide two or
more books belong to one visual "set": every volume's `content_unit.work_slug`
column pointing at the same `kind='work'` parent row. For Asas al-Taweel, that
linkage was typed ONCE, by hand, inside `listener/migrations/0003_seed_catalog.sql`
— there is no script, tool, or repeatable mechanism that creates or maintains
it. A second multi-volume book (Mukhtasar ul-Asar) shipped with NO grouping at
all, because nothing ever re-ran that hand-written block for it.

This script is that missing mechanism. It reads declared multi-volume
groupings off disk (never a hardcoded slug — see "MANIFEST SOURCES" below) and
makes the database agree with them: idempotent, safe to run after every book
is published, safe to run on a fleet where nothing changed.

MANIFEST SOURCES (both scanned, neither hardcoded to a slug)
--------------------------------------------------------------
1. Real pipeline works — ``content/<Bucket>/<work_slug>/work.yml``, the
   schema `_work_manifest.py` already owns (nested ``vol-NN/`` volume dirs
   under one branch, one PDF-intake work). Asas al-Taweel and Al-Anwaar
   al-Lateefah are both this shape today.

2. Catalog-only groupings — ``content/<Bucket>/_listener-groups/<name>.yml``.
   This second kind exists because of a genuine schema mismatch found while
   building this script: `_work_manifest.py`'s ``work.yml`` is not just a
   list of volume slugs — `_paths.is_work_parent()` treats the mere PRESENCE
   of a file literally named ``work.yml`` inside a top-level
   ``content/<Bucket>/<slug>/`` directory as proof that directory is a work
   parent, and then `_paths.volume_dirs()` discovers volumes by globbing
   ``vol-*`` subdirectories underneath it — never by reading the manifest's
   own volume list. Mukhtasar ul-Asar's two volumes are independently
   published, FLAT, top-level content folders
   (``content/Islamic/mukhtasar-ul-asar-1/``, ``mukhtasar-ul-asar-2/``), not
   nested ``vol-01/``/``vol-02/`` dirs under a shared parent — so a real
   ``work.yml`` for it would either (a) require moving two already-published
   books' folders under a new nested parent, which the task creating this
   script explicitly deferred as a separate, larger decision, or (b) if
   dropped in place with a non-nested `dir:` pointer, would silently mislead
   `_paths.find_content()`/`is_work_parent()`/`orchestrate_work.py`/intake
   into treating an already-shipped, independently-resolvable book as an
   unfinished nested work with zero discoverable volumes. Neither is safe.
   The `_listener-groups/` convention sidesteps both failure modes: the
   directory name starts with ``_``, so `_paths.iter_content()`'s own scan
   (``if child.name.startswith(("_", ".")): continue``) already skips it,
   and the manifest file is never named ``work.yml``, so `is_work_parent()`
   never fires on it. It is read ONLY by this script — no pipeline phase,
   `_work_manifest.py`, `orchestrate_work.py`, or intake path touches it.

Both manifest shapes are parsed into the same minimal shape this script
needs: ``{work_slug, title, bucket, volumes: [{slug, order}, ...]}``. Extra
fields (``title_arabic``, ``content_profile``, ``shared``, per-volume
``sources``/``status``) are pipeline concerns this script does not read.

WHAT IT WRITES
---------------
Two things, both idempotent:

1. The `kind='work'` parent row — created only if no row for that slug
   exists yet (``ON CONFLICT ... DO UPDATE ... WHERE content_unit.kind =
   'work'`` — a slug collision with an existing NON-work row is left
   completely untouched, never clobbered). ``bucket``/``title`` are kept in
   sync with the manifest on every run; ``status``/``open_to_all`` are never
   named, exactly like `publish_to_listener.py` — those are the admin's
   privilege bits and this script has no opinion on visibility.
   ``sort_order`` is set ONLY at creation (one row short of its lowest
   volume's current sort_order, so the parent sorts first) and is never
   touched again, so a value a human hand-tunes later survives every re-run.

2. Each volume's `work_slug` column — set only when it is currently NULL.
   A volume already carrying the correct `work_slug` is a no-op (this is
   what makes the script recognize Asas al-Taweel's existing hand-written
   linkage and do nothing to it). A volume carrying a DIFFERENT non-null
   `work_slug` is left alone and reported as a conflict — this script never
   overwrites an existing grouping decision, only fills in a missing one.
   A manifest volume slug with no matching `content_unit` row at all (not
   published yet) is skipped and reported, never inserted — this script
   groups existing rows, it does not create book rows (`publish_to_listener.py`
   is the only writer of a book's own `content_unit` row).

USAGE
-----
    python3 scripts/podcast/sync_listener_work_groups.py
        [--remote]     write to the deployed D1 instead of the local one
        [--dry-run]    print the plan and the SQL; execute nothing
        [--json]       machine-readable summary on stdout
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml  # noqa: E402
from _listener_book import LISTENER  # noqa: E402
from _paths import BUCKETS, CONTENT_ROOT, REPO_ROOT  # noqa: E402
from _production_publish import account_ok, cloudflare_env  # noqa: E402
from _wrangler import run as wrangler  # noqa: E402
from publish_to_listener import sql_str  # noqa: E402
from upload_listener_media import DATABASE, d1  # noqa: E402

WORK_MANIFEST_NAME = "work.yml"
LISTENER_GROUPS_DIR = "_listener-groups"


# ---------------------------------------------------------------------------
# Manifest discovery — generic, no book slug named anywhere below.
# ---------------------------------------------------------------------------


class Group:
    def __init__(self, *, work_slug: str, title: str, bucket: str, volumes: list[dict[str, Any]], source: Path):
        self.work_slug = work_slug
        self.title = title
        self.bucket = bucket
        self.volumes = sorted(volumes, key=lambda v: v.get("order", 0))
        self.source = source


def _load_yaml(path: Path) -> dict[str, Any] | None:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _group_from_manifest(manifest: dict[str, Any], *, default_slug: str, source: Path) -> Group | None:
    work_slug = manifest.get("work_slug") or default_slug
    title = manifest.get("title")
    bucket = manifest.get("bucket")
    raw_volumes = manifest.get("volumes")
    if not work_slug or not title or not bucket or not isinstance(raw_volumes, list):
        return None
    volumes: list[dict[str, Any]] = []
    for v in raw_volumes:
        if isinstance(v, dict) and v.get("slug"):
            volumes.append({"slug": v["slug"], "order": v.get("order", 0)})
    if len(volumes) < 2:
        return None
    return Group(work_slug=work_slug, title=title, bucket=bucket, volumes=volumes, source=source)


def find_groups() -> list[Group]:
    """Every multi-volume grouping declared on disk, from either manifest shape.

    Generic over bucket and slug — nothing here names a specific book. A
    third manifest shape can be added later by adding one more glob + parse
    branch; no caller of this function changes.
    """
    groups: list[Group] = []

    for bucket in BUCKETS:
        bucket_dir = CONTENT_ROOT / bucket
        if not bucket_dir.is_dir():
            continue

        # (1) Real pipeline works: content/<Bucket>/<slug>/work.yml
        for manifest_path in sorted(bucket_dir.glob(f"*/{WORK_MANIFEST_NAME}")):
            data = _load_yaml(manifest_path)
            if data is None:
                continue
            group = _group_from_manifest(data, default_slug=manifest_path.parent.name, source=manifest_path)
            if group is not None:
                groups.append(group)

        # (2) Catalog-only groupings: content/<Bucket>/_listener-groups/*.yml
        groups_dir = bucket_dir / LISTENER_GROUPS_DIR
        if groups_dir.is_dir():
            for manifest_path in sorted(groups_dir.glob("*.yml")):
                data = _load_yaml(manifest_path)
                if data is None:
                    continue
                group = _group_from_manifest(data, default_slug=manifest_path.stem, source=manifest_path)
                if group is not None:
                    groups.append(group)

    return groups


# ---------------------------------------------------------------------------
# D1 state + SQL
# ---------------------------------------------------------------------------


def current_units(remote: bool) -> dict[str, dict[str, Any]]:
    """slug -> {kind, work_slug, sort_order, bucket, title} for every content_unit row."""
    rows = d1("SELECT slug, kind, work_slug, sort_order, bucket, title FROM content_unit", remote=remote)
    return {r["slug"]: r for r in rows}


def plan_for_group(group: Group, units: dict[str, dict[str, Any]]) -> tuple[list[str], list[str]]:
    """Return (sql_statements, notes) for one group, computed against `units`."""
    statements: list[str] = []
    notes: list[str] = []

    volume_rows = [(v["slug"], units.get(v["slug"])) for v in group.volumes]
    known_sort_orders = [row["sort_order"] for _slug, row in volume_rows if row is not None]
    missing = [slug for slug, row in volume_rows if row is None]
    for slug in missing:
        notes.append(f"  ! {group.work_slug}: volume {slug!r} has no content_unit row yet — not published, skipped")

    parent = units.get(group.work_slug)
    if parent is not None and parent["kind"] != "work":
        notes.append(
            f"  ! {group.work_slug}: a content_unit row already exists with kind={parent['kind']!r} "
            "— refusing to touch it or group anything under this slug"
        )
        return statements, notes

    parent_unchanged = parent is not None and parent["bucket"] == group.bucket and parent["title"] == group.title
    if not parent_unchanged:
        new_sort_order = (min(known_sort_orders) - 1) if known_sort_orders else 0
        statements.append(
            "INSERT INTO content_unit (slug, bucket, title, kind, work_slug, sort_order) VALUES "
            f"({sql_str(group.work_slug)}, {sql_str(group.bucket)}, {sql_str(group.title)}, 'work', NULL, {new_sort_order}) "
            "ON CONFLICT(slug) DO UPDATE SET bucket = excluded.bucket, title = excluded.title "
            "WHERE content_unit.kind = 'work';"
        )

    for slug, row in volume_rows:
        if row is None:
            continue
        if row["kind"] != "book":
            notes.append(f"  ! {group.work_slug}: {slug!r} is kind={row['kind']!r}, not a book — skipped")
            continue
        if row["work_slug"] == group.work_slug:
            continue  # already correctly linked — no-op, this is what makes a re-run on
            # Asas al-Taweel idempotent.
        if row["work_slug"] not in (None, ""):
            notes.append(
                f"  ! {slug}: already grouped under work_slug={row['work_slug']!r}, "
                f"manifest wants {group.work_slug!r} — left untouched, resolve by hand"
            )
            continue
        statements.append(
            f"UPDATE content_unit SET work_slug = {sql_str(group.work_slug)} "
            f"WHERE slug = {sql_str(slug)} AND kind = 'book' AND work_slug IS NULL;"
        )

    return statements, notes


def execute(statements: list[str], *, remote: bool) -> None:
    if not statements:
        return
    command = "\n".join(statements)
    wrangler(
        [
            "npx",
            "wrangler",
            "d1",
            "execute",
            DATABASE,
            "--remote" if remote else "--local",
            "--command",
            command,
            "--yes",
        ],
        cwd=LISTENER,
        check=True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote", action="store_true", help="write to the deployed D1")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.remote:
        try:
            os.environ.update(cloudflare_env())
        except RuntimeError as error:
            print(f"  ! {error}")
            return 2
        ok, who = account_ok(dict(os.environ), LISTENER)
        if not ok:
            print(f"  ! {who}")
            return 2

    groups = find_groups()
    units = current_units(remote=args.remote)

    all_statements: list[str] = []
    all_notes: list[str] = []
    per_group: list[dict[str, Any]] = []

    for group in groups:
        statements, notes = plan_for_group(group, units)
        all_statements.extend(statements)
        all_notes.extend(notes)
        per_group.append(
            {
                "work_slug": group.work_slug,
                "title": group.title,
                "bucket": group.bucket,
                "source": str(group.source.relative_to(REPO_ROOT)),
                "volumes": [v["slug"] for v in group.volumes],
                "statements": len(statements),
            }
        )

    if args.json:
        print(json.dumps({"groups": per_group, "notes": all_notes, "dry_run": args.dry_run}, indent=2))
    else:
        if not groups:
            print("no multi-volume manifests found under content/*/*/work.yml or content/*/_listener-groups/*.yml")
        for g in per_group:
            print(f"\n{g['title']}  ({g['work_slug']})  <- {g['source']}")
            print(f"  volumes   {', '.join(g['volumes'])}")
            print(f"  changes   {g['statements']} statement(s)" + ("  (no-op)" if g["statements"] == 0 else ""))
        for note in all_notes:
            print(note)

    if args.dry_run:
        if not args.json:
            print(f"\ndry run — {len(all_statements)} statement(s) would run, nothing executed")
            for s in all_statements:
                print(f"  {s}")
        return 0

    if all_statements:
        try:
            execute(all_statements, remote=args.remote)
        except subprocess.CalledProcessError as error:
            for stream in (error.stdout, error.stderr):
                text = str(stream or "").strip()
                if text:
                    print(text)
            print("  ! FAILED to write grouping changes")
            return 1

    if not args.json:
        target = "the deployed database" if args.remote else "the local database"
        print(f"\n{len(all_statements)} statement(s) written to {target}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
