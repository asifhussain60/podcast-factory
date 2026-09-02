#!/usr/bin/env python3
"""audio_parity.py — do disk, localhost and production hold the SAME audio?

WHY THIS EXISTS. The recordings are gitignored (`content/**/m4a/**`), so a second
machine's copy of a book arrives by some route git never saw. Localhost and the
live site are also two physically separate R2 stores: Miniflare's local
simulation and the real bucket. Nothing in the pipeline compares them, so the
three copies can drift apart silently and the first symptom is a listener
hearing a recording nobody meant to ship.

`media_asset.sha256` is what makes the comparison possible — `publish_to_listener`
records the hash of the file it published, and clears `uploaded_at` whenever that
hash changes. This script simply reads that column back from both databases and
hashes what is actually on disk.

Rows are matched to files by `source_path`, the column recording which file on
disk the row was published from. The R2 KEY cannot be used for this: it is built
from the episode NUMBER (`<slug>/audio/ep07.m4a`), so a recording the author
named `EP-07-The Conspiracy Formula.mp3` has a key that shares nothing with its
filename, and deriving one from the other would be guesswork dressed as a check.

It is READ-ONLY. It writes nothing, uploads nothing, and fixes nothing; it tells
you which of the three copies disagree so you can decide, which is the only safe
thing to do when the disagreement might mean "this machine has the wrong audio".

    same        disk, local and remote agree
    unpublished on disk, but no row in either database
    local-only  a row locally, none in production
    STALE       a database row whose hash is not the file on disk
    MISMATCH    local and remote disagree with each other
    ORPHAN      a row whose source file is not on this machine at all

Read-along NARRATION is excluded. It is stored under `kind = 'audio'` too, which
is why a ten-chapter book with four recordings shows fourteen audio rows, but it
is synthesised from the chapter text rather than re-encoded from a master, so
comparing it here would report every book as disagreeing with itself.

CLI:
    python3 scripts/podcast/audio_parity.py                # whole library
    python3 scripts/podcast/audio_parity.py --slug <slug>  # one book
    python3 scripts/podcast/audio_parity.py --problems     # only what disagrees
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _paths import REPO_ROOT  # noqa: E402
from downsize_audio import book_dirs, shippable_audio  # noqa: E402

LISTENER = REPO_ROOT / "listener"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def local_rows() -> dict[str, dict]:
    """media_asset from Miniflare's own SQLite. Empty if this machine has no local store."""
    files = [
        f
        for f in glob.glob(str(LISTENER / ".wrangler/state/v3/d1/miniflare-D1DatabaseObject/*.sqlite"))
        if "metadata" not in f
    ]
    if not files:
        return {}
    con = sqlite3.connect(files[0])
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            "SELECT key, slug, bytes, sha256, uploaded_at, source_path "
            "FROM media_asset WHERE kind = 'audio' AND key NOT LIKE '%/narration/%'"
        ).fetchall()
    except sqlite3.OperationalError:
        return {}
    return {r["source_path"]: dict(r) for r in rows if r["source_path"]}


def remote_rows() -> dict[str, dict]:
    """media_asset from the deployed D1."""
    from _production_publish import cloudflare_env

    r = subprocess.run(
        [
            "npx",
            "wrangler",
            "d1",
            "execute",
            "podcast-listener",
            "--remote",
            "--json",
            "--command",
            "SELECT key, slug, bytes, sha256, uploaded_at, source_path "
            "FROM media_asset WHERE kind = 'audio' AND key NOT LIKE '%/narration/%';",
        ],
        cwd=LISTENER,
        env={**os.environ, **cloudflare_env()},
        capture_output=True,
        text=True,
    )
    start = r.stdout.find("[")
    if r.returncode != 0 or start < 0:
        raise SystemExit(f"audio_parity: could not read remote D1\n{(r.stderr or r.stdout)[:400]}")
    return {x["source_path"]: x for x in json.loads(r.stdout[start:])[0]["results"] if x["source_path"]}


def verdict(disk: str | None, loc: dict | None, rem: dict | None) -> str:
    if loc is None and rem is None:
        return "unpublished"
    if loc is not None and rem is None:
        return "local-only"
    lh, rh = (loc or {}).get("sha256"), (rem or {}).get("sha256")
    if lh and rh and lh != rh:
        return "MISMATCH"
    if disk and rh and disk != rh:
        return "STALE"
    if disk and lh and disk != lh:
        return "STALE"
    return "same"


def report(targets: list[Path], *, problems: bool = False, quiet_if_clean: bool = False) -> int:
    """Run the disk/local/remote comparison over `targets` and print it.

    Shared by the CLI and by `publish_to_listener`, which calls this on the
    books it just published so a drift is caught the moment it happens rather
    than the next time someone remembers to run the CLI by hand — which is how
    the `purification-of-the-heart` mismatch sat unnoticed for a session.
    `quiet_if_clean` is what `publish_to_listener` wants: silence when every
    file agrees, since that publish output is not the place to restate five
    lines of "same" on a book that always ships fine.
    """
    loc, rem = local_rows(), remote_rows()
    if not loc and not quiet_if_clean:
        print("audio_parity: no local D1 on this machine — comparing disk against production only.\n")

    counts: dict[str, int] = {}
    bad = 0
    for book_dir in targets:
        files = shippable_audio(book_dir)
        if not files:
            continue
        lines = []
        for path in files:
            rel = str(path.relative_to(REPO_ROOT))
            digest = sha256(path)
            v = verdict(digest, loc.get(rel), rem.get(rel))
            counts[v] = counts.get(v, 0) + 1
            if v not in ("same", "unpublished"):
                bad += 1
            if not problems or v not in ("same", "unpublished"):
                lines.append(f"    {v:<11} {path.name}  ({path.stat().st_size / 2**20:.1f} MB)")
        if lines:
            print(f"  {book_dir.name}")
            print("\n".join(lines))

    seen = {str(p.relative_to(REPO_ROOT)) for d in targets for p in shippable_audio(d)}
    scope = {d.name for d in targets}
    orphans = [
        r
        for src, r in (rem or loc).items()
        if r.get("slug") in scope and src not in seen and not (REPO_ROOT / src).exists()
    ]
    if orphans:
        print(f"\n  ORPHAN — {len(orphans)} published row(s) whose file is not on this machine:")
        for r in orphans[:10]:
            print(f"    {r['key']}  (published from {r['source_path']})")
        counts["ORPHAN"] = len(orphans)

    if bad or not quiet_if_clean:
        print("\n  " + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    if bad:
        print(f"\n  {bad} file(s) disagree — resolve before re-encoding or uploading.")
    elif quiet_if_clean:
        print("  audio parity: clean — disk, local and production agree")
    return 1 if bad else 0


def check_after_publish(slugs: list[str], failed: list[str], *, dry_run: bool, json_mode: bool) -> int:
    """`publish_to_listener` calls this on every run, after writing the SQL.

    Scoped to only the slugs THIS run actually published (`failed` drops out,
    so a book that never wrote is never checked against audio it may not even
    have), never the whole library — publishing one book must not pay to
    re-hash every other book's audio. Checked here rather than left for
    someone to remember to run the CLI by hand — that gap is exactly how the
    purification-of-the-heart mismatch (Asif, 2026-09-02) sat unnoticed for a
    whole session. A dry run wrote nothing to check; `--json` output is
    machine-read and gets no prose appended to it.
    """
    if dry_run or json_mode:
        return 0
    published = [s for s in slugs if s not in failed]
    if not published:
        return 0
    targets = [d for d in book_dirs(None) if d.name in set(published)]
    print()
    return report(targets, problems=True, quiet_if_clean=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--slug", help="Only this book (default: every book).")
    ap.add_argument("--problems", action="store_true", help="Only print rows that disagree.")
    args = ap.parse_args()

    targets = book_dirs(args.slug)
    if not targets:
        print(f"audio_parity: no book found for slug {args.slug!r}", file=sys.stderr)
        return 2

    return report(targets, problems=args.problems)


if __name__ == "__main__":
    raise SystemExit(main())
