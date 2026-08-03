#!/usr/bin/env python3
"""Put the Listener's media into R2, and record that it is there.

`publish_to_listener.py` writes the INVENTORY — one `media_asset` row per audio
file, PDF, cover and deck page that exists on this disk. This script is what
turns those rows into objects the site can actually serve, and it is separate for
two reasons: it is the slow part (a single recording is 70 MB), and it is the
retryable part. Re-running it after a failure costs nothing and re-publishes no
prose.

    python3 scripts/podcast/upload_listener_media.py [<slug> …]
        [--remote]     the deployed bucket and database, not the local ones
        [--dry-run]    list what would be uploaded, upload nothing
        [--force]      re-upload even rows already marked uploaded

`uploaded_at` is the whole contract. A row without it means "this file exists on
Asif's disk"; a row with it means "this object is in R2". The site links only the
second and reports the first as not uploaded yet, so a half-uploaded library is
honest at every moment — including in the middle of this script's own run, which
stamps each row as that file lands rather than all of them at the end.

R2 must be enabled on the Cloudflare account first; until it is, bucket creation
fails with `10042` and this script says so and stops.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _listener_book import LISTENER  # noqa: E402
from _paths import REPO_ROOT  # noqa: E402

BUCKET = "podcast-listener-media"
DATABASE = "podcast-listener"


def d1(sql: str, *, remote: bool) -> list[dict]:
    """Run one statement and return its rows."""
    out = subprocess.run(
        [
            "npx",
            "wrangler",
            "d1",
            "execute",
            DATABASE,
            "--remote" if remote else "--local",
            "--json",
            "--command",
            sql,
        ],
        cwd=LISTENER,
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    # Wrangler prints its banner on stdout ahead of the JSON when it feels like
    # it, so parse from the first bracket rather than trusting the whole stream.
    start = out.index("[")
    return json.loads(out[start:])[0]["results"]


def pending(slugs: list[str], *, remote: bool, force: bool) -> list[dict]:
    where = "" if force else "uploaded_at IS NULL"
    if slugs:
        listed = ", ".join("'" + s.replace("'", "''") + "'" for s in slugs)
        clause = f"slug IN ({listed})"
        where = f"{where} AND {clause}" if where else clause

    return d1(
        "SELECT key, slug, kind, content_type, bytes, source_path FROM media_asset"
        + (f" WHERE {where}" if where else "")
        + " ORDER BY slug, kind, key",
        remote=remote,
    )


def bucket_exists(*, remote: bool) -> bool:
    """Whether the bucket is there, which for a local run is always true —
    Miniflare conjures one on demand and there is nothing to check."""
    if not remote:
        return True

    result = subprocess.run(
        ["npx", "wrangler", "r2", "bucket", "info", BUCKET],
        cwd=LISTENER,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def upload(row: dict, *, remote: bool) -> None:
    path = REPO_ROOT / row["source_path"]
    if not path.exists():
        raise FileNotFoundError(row["source_path"])

    subprocess.run(
        [
            "npx",
            "wrangler",
            "r2",
            "object",
            "put",
            f"{BUCKET}/{row['key']}",
            "--file",
            str(path),
            "--content-type",
            row["content_type"],
            "--remote" if remote else "--local",
        ],
        cwd=LISTENER,
        capture_output=True,
        text=True,
        check=True,
    )


def stamp(key: str, when: str, *, remote: bool) -> None:
    # One row at a time, immediately after its object lands. Stamping them all at
    # the end would mean an interrupted run leaves every file uploaded and no row
    # saying so — and the next run would push all of them again.
    escaped = key.replace("'", "''")
    d1(f"UPDATE media_asset SET uploaded_at = '{when}' WHERE key = '{escaped}'", remote=remote)


def megabytes(n: int) -> str:
    return f"{n / 1_000_000:.1f} MB"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slugs", nargs="*", help="default: every book")
    parser.add_argument("--remote", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    rows = pending(args.slugs, remote=args.remote, force=args.force)
    if not rows:
        print("nothing to upload — every known file is already in R2")
        return 0

    total = sum(int(r["bytes"]) for r in rows)
    print(f"{len(rows)} file(s), {megabytes(total)}\n")
    for row in rows:
        print(f"  {row['kind']:<10} {megabytes(int(row['bytes'])):>9}  {row['key']}")

    if args.dry_run:
        print("\ndry run — nothing uploaded")
        return 0

    if not bucket_exists(remote=args.remote):
        print(
            f"\nthe bucket '{BUCKET}' does not exist.\n"
            "R2 has to be enabled on the Cloudflare account first — it is a one-time\n"
            "opt-in in the dashboard, and until it is done bucket creation fails with\n"
            "'Please enable R2 through the Cloudflare Dashboard' (code 10042).\n"
            "Once it is on:\n"
            f"  cd listener && npx wrangler r2 bucket create {BUCKET}\n"
            "  # then uncomment the r2_buckets binding in wrangler.jsonc and redeploy"
        )
        return 1

    when = subprocess.run(
        ["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"], capture_output=True, text=True, check=True
    ).stdout.strip()

    failed = 0
    for i, row in enumerate(rows, 1):
        print(f"\n[{i}/{len(rows)}] {row['key']}  ({megabytes(int(row['bytes']))})")
        try:
            upload(row, remote=args.remote)
            stamp(row["key"], when, remote=args.remote)
            print("  uploaded")
        except (OSError, subprocess.SubprocessError) as error:
            # Keep going. One unreadable file must not strand the other forty,
            # and the row simply stays unstamped, which the site already reports
            # honestly.
            failed += 1
            print(f"  FAILED — {error}")

    print(f"\n{len(rows) - failed} uploaded, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
