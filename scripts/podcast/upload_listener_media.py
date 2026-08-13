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
        [--no-audio]   covers, deck pages and the print edition only
        [--drop-local-audio]  delete local recordings and reclaim the disk

`--no-audio` exists for the LOCAL bucket (Asif, 2026-08-10). A recording pushed
there is a second copy of a file already on the same disk — 0.98 GB of the 1.04 GB
the local bucket held — and nothing about playing an episode locally is worth a
duplicate of every recording. The small assets still go, because a local page
missing its cover and deck pages is not the page it is standing in for.

`uploaded_at` is the whole contract. A row without it means "this file exists on
Asif's disk"; a row with it means "this object is in R2". The site links only the
second and reports the first as not uploaded yet, so a half-uploaded library is
honest at every moment — including in the middle of this script's own run, which
stamps each row as that file lands rather than all of them at the end.

R2 has to be enabled on the account before a bucket can exist at all; it was, on
2026-08-03. If the bucket is ever missing this script says so and stops rather
than reporting a successful upload of nothing.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _listener_book import LISTENER  # noqa: E402
from _paths import REPO_ROOT  # noqa: E402
from _production_publish import account_ok, cloudflare_env  # noqa: E402

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


def pending(slugs: list[str], *, remote: bool, force: bool, no_audio: bool = False) -> list[dict]:
    where = "" if force else "uploaded_at IS NULL"
    if slugs:
        listed = ", ".join("'" + s.replace("'", "''") + "'" for s in slugs)
        clause = f"slug IN ({listed})"
        where = f"{where} AND {clause}" if where else clause
    if no_audio:
        # The recordings are the whole weight — 0.98 GB of the 1.04 GB in the
        # local bucket on 2026-08-10, in 30 files against 159 of everything else.
        # Covers, deck pages and the print edition are 60 MB and are what make a
        # local page look like the real one, so they are NOT what gets dropped.
        where = f"{where} AND kind != 'audio'" if where else "kind != 'audio'"

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


def delete_object(key: str, *, remote: bool) -> bool:
    """Remove one object from the bucket. False if wrangler refused.

    Exists because nothing can LIST an R2 bucket from here — wrangler has
    `r2 object get/put/delete` and no list — so orphans cannot be found by
    sweeping. They have to be deleted by whoever knew the key, at the moment it
    stopped being wanted. That is the publish step, which is the only thing that
    ever removes a `media_asset` row.
    """
    result = subprocess.run(
        [
            "npx",
            "wrangler",
            "r2",
            "object",
            "delete",
            f"{BUCKET}/{key}",
            "--remote" if remote else "--local",
        ],
        cwd=LISTENER,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def stamp(key: str, when: str, *, remote: bool) -> None:
    # One row at a time, immediately after its object lands. Stamping them all at
    # the end would mean an interrupted run leaves every file uploaded and no row
    # saying so — and the next run would push all of them again.
    escaped = key.replace("'", "''")
    d1(f"UPDATE media_asset SET uploaded_at = '{when}' WHERE key = '{escaped}'", remote=remote)


def unstamp(key: str, *, remote: bool) -> None:
    """Say the object is no longer there. The inverse of `stamp`, and the reason
    dropping a recording is safe: the row survives, so the file is still
    INVENTORIED — the site simply reports it as not uploaded yet instead of
    linking an object that has gone. Deleting the row would lose the record that
    the recording exists on disk at all."""
    escaped = key.replace("'", "''")
    d1(f"UPDATE media_asset SET uploaded_at = NULL WHERE key = '{escaped}'", remote=remote)


def local_audio_objects(slugs: list[str]) -> list[dict]:
    """Recordings currently duplicated into the LOCAL bucket."""
    where = "kind = 'audio' AND uploaded_at IS NOT NULL"
    if slugs:
        listed = ", ".join("'" + s.replace("'", "''") + "'" for s in slugs)
        where += f" AND slug IN ({listed})"
    return d1(
        f"SELECT key, slug, bytes FROM media_asset WHERE {where} ORDER BY slug, key",
        remote=False,
    )


def drop_local_audio(slugs: list[str], *, dry_run: bool) -> int:
    """Reclaim the disk a local bucket spent on second copies of local files.

    LOCAL ONLY, and `main` refuses to combine it with `--remote`: the live site
    serves from R2 and has no other copy to fall back on, so the same operation
    there would take a book's recordings off the internet.

    Reversible in one command — `upload_listener_media.py <slug> --local-audio`
    is not needed, plain `upload_listener_media.py <slug>` re-uploads anything
    whose stamp is NULL — which is what makes this a cache eviction rather than a
    deletion of anything that matters.
    """
    rows = local_audio_objects(slugs)
    if not rows:
        print("no recordings are duplicated in the local bucket")
        return 0

    total = sum(int(r["bytes"]) for r in rows)
    print(f"{len(rows)} recording(s), {megabytes(total)} to reclaim\n")
    for row in rows:
        print(f"  {megabytes(int(row['bytes'])):>9}  {row['key']}")
    if dry_run:
        print("\ndry run — nothing deleted")
        return 0

    failed = 0
    for i, row in enumerate(rows, 1):
        print(f"\n[{i}/{len(rows)}] {row['key']}")
        if delete_object(row["key"], remote=False):
            # The stamp is cleared ONLY after the object is actually gone, so an
            # interrupted run never claims a file is missing while it is still
            # taking up the disk this is trying to reclaim.
            unstamp(row["key"], remote=False)
            print("  removed")
        else:
            failed += 1
            print("  FAILED — left in place and still marked uploaded")
    print(f"\nreclaimed {megabytes(total)}" + (f"; {failed} could not be removed" if failed else ""))
    return 1 if failed else 0


def megabytes(n: int) -> str:
    return f"{n / 1_000_000:.1f} MB"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slugs", nargs="*", help="default: every book")
    parser.add_argument("--remote", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--no-audio",
        action="store_true",
        help="skip the recordings; upload covers, deck pages and the print edition only",
    )
    parser.add_argument(
        "--drop-local-audio",
        action="store_true",
        help="delete recordings from the LOCAL bucket and mark them not-uploaded (reclaims disk)",
    )
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

    if args.drop_local_audio:
        if args.remote:
            print(
                "refused: --drop-local-audio is local only.\n"
                "The live site serves from R2 and has no other copy — deleting there would take\n"
                "a book's recordings off the internet."
            )
            return 2
        return drop_local_audio(args.slugs, dry_run=args.dry_run)

    rows = pending(args.slugs, remote=args.remote, force=args.force, no_audio=args.no_audio)
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
