#!/usr/bin/env python3
"""r2_orphans.py — is there anything in the bucket no database row points at?

WHY THIS EXISTS. `upload_listener_media.py` and `audio_parity.py` both say, in
their own docstrings, that nothing can list an R2 bucket — `wrangler r2 object`
only has `get`, `put`, and `delete`. That is true of the wrangler CLI, but not
of the account: the Cloudflare v4 REST API's R2 endpoint
(`GET /accounts/{id}/r2/buckets/{bucket}/objects`) accepts the SAME token
`cloudflare_env()` already resolves, and answers with every object in the
bucket — key, size, last-modified. wrangler's gap was never a permissions gap.

WHAT COUNTS AS AN ORPHAN. Every object whose key has no matching `media_asset`
row in the DEPLOYED database. `publish_to_listener` already deletes the R2
object behind a row it drops during a republish (see `keys_in_bucket` there),
so an orphan here means something else removed a row without removing its
object — a book deleted by hand, a key scheme that changed, a failed publish
that partially wrote. This script only ever REPORTS; it deletes nothing. A
found orphan is deleted with `wrangler r2 object delete`, by a human who has
looked at the key and decided it is really unwanted.

CLI:
    python3 scripts/podcast/r2_orphans.py             # whole bucket, local D1 too
    python3 scripts/podcast/r2_orphans.py --remote-only # skip the local comparison
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _production_publish import ACCOUNT_ID, cloudflare_env  # noqa: E402
from upload_listener_media import BUCKET, LISTENER  # noqa: E402

API_ROOT = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/r2/buckets/{BUCKET}/objects"


def list_bucket(env: dict[str, str]) -> dict[str, int]:
    """Every object in the bucket, keyed by its R2 key, valued by its byte size."""
    objects: dict[str, int] = {}
    cursor: str | None = None
    while True:
        url = f"{API_ROOT}?per_page=1000"
        if cursor:
            url += f"&cursor={cursor}"
        r = subprocess.run(
            ["curl", "-s", "-H", f"Authorization: Bearer {env['CLOUDFLARE_API_TOKEN']}", url],
            capture_output=True,
            text=True,
        )
        try:
            data = json.loads(r.stdout)
        except ValueError:
            raise SystemExit(f"r2_orphans: could not parse R2 API response:\n{r.stdout[:400]}")
        if not data.get("success"):
            raise SystemExit(f"r2_orphans: R2 API refused the request:\n{data}")
        for obj in data["result"]:
            objects[obj["key"]] = obj["size"]
        info = data.get("result_info", {})
        if not info.get("is_truncated"):
            break
        cursor = info.get("cursor")
        if not cursor:
            break
    return objects


def db_keys(*, remote: bool, env: dict[str, str]) -> set[str]:
    """Every key the database (local or deployed) currently references."""
    if not remote:
        files = [
            f
            for f in glob.glob(str(LISTENER / ".wrangler/state/v3/d1/miniflare-D1DatabaseObject/*.sqlite"))
            if "metadata" not in f
        ]
        if not files:
            return set()
        import sqlite3

        con = sqlite3.connect(files[0])
        try:
            rows = con.execute("SELECT key FROM media_asset").fetchall()
        except sqlite3.OperationalError:
            return set()
        return {r[0] for r in rows}

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
            "SELECT key FROM media_asset;",
        ],
        cwd=LISTENER,
        env={**os.environ, **env},
        capture_output=True,
        text=True,
    )
    start = r.stdout.find("[")
    if r.returncode != 0 or start < 0:
        raise SystemExit(f"r2_orphans: could not read remote D1\n{(r.stderr or r.stdout)[:400]}")
    return {row["key"] for row in json.loads(r.stdout[start:])[0]["results"]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--remote-only",
        action="store_true",
        help="Skip the local-D1 comparison (this machine's dev store, separate from production).",
    )
    args = ap.parse_args()

    env = cloudflare_env()
    print(f"listing {BUCKET} …")
    objects = list_bucket(env)
    remote_keys = db_keys(remote=True, env=env)

    remote_orphans = {k: s for k, s in objects.items() if k not in remote_keys}
    missing = remote_keys - set(objects)

    print(f"\n{len(objects)} object(s) in the bucket, {sum(objects.values()) / 2**20:.1f} MB")
    print(f"{len(remote_keys)} row(s) in the deployed database")

    if remote_orphans:
        total = sum(remote_orphans.values())
        print(f"\nORPHAN — {len(remote_orphans)} object(s), {total / 2**20:.1f} MB, no row in production:")
        for key, size in sorted(remote_orphans.items()):
            print(f"    {key}  ({size / 2**20:.1f} MB)")
    else:
        print("\nno orphans — every object in the bucket has a production row")

    if missing:
        print(f"\nMISSING — {len(missing)} database row(s) whose object is not in the bucket:")
        for key in sorted(missing)[:20]:
            print(f"    {key}")

    if not args.remote_only and remote_orphans:
        local_keys = db_keys(remote=False, env=env)
        if local_keys:
            also_local_orphans = [k for k in remote_orphans if k not in local_keys]
            if 0 < len(also_local_orphans) < len(remote_orphans):
                print(
                    f"\nof those, {len(also_local_orphans)} also have no local row — not just a remote-only publish gap"
                )

    return 1 if remote_orphans else 0


if __name__ == "__main__":
    raise SystemExit(main())
