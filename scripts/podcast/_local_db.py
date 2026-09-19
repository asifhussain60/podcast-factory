"""_local_db.py — keep the LOCAL Library database's schema current before a local publish.

The git hooks apply local migrations only when `develop` moves. A book published from its own branch
(isaf-al-talib) reached a local database three migrations behind and failed with "table unit_detail has
no column named author". This checks first, applies what is pending to the LOCAL database only, and on
failure says the exact command. It never removes anything under listener/.wrangler/state — deleting
that signs Asif out of localhost and looks like nothing shipped.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from _wrangler import run as _wrangler_run

DB_NAME = "podcast-listener"
_MIGRATION = re.compile(r"\b(\d{4}_[A-Za-z0-9_-]+\.sql)\b")
REMEDY = f"cd listener && npm run db:migrate   (applies pending migrations to the local {DB_NAME} database)"


def pending_migrations(listener_dir: Path, *, run=_wrangler_run) -> list[str]:
    """Migration file names not yet applied to the local database."""
    out = run(
        ["npx", "wrangler", "d1", "migrations", "list", DB_NAME, "--local"], cwd=str(listener_dir), timeout=120
    ).stdout
    if "no migrations to apply" in out.lower():
        return []
    return list(dict.fromkeys(_MIGRATION.findall(out)))


def ensure_local_migrations(listener_dir: Path, *, run=_wrangler_run) -> str | None:
    """None when the local schema is current (applying anything pending first); else a report to print."""
    try:
        pending = pending_migrations(listener_dir, run=run)
        if not pending:
            return None
        proc = run(
            ["npx", "wrangler", "d1", "migrations", "apply", DB_NAME, "--local"], cwd=str(listener_dir), timeout=300
        )
    except (OSError, subprocess.SubprocessError) as error:
        return f"could not check the local database's schema ({error}). Run: {REMEDY}"
    if proc.returncode == 0:
        print(f"  local database brought up to date: {', '.join(pending)}")
        return None
    return (
        f"the local database is behind by {len(pending)} migration(s) ({', '.join(pending)}) and applying them failed: "
        f"{(proc.stderr or proc.stdout or '').strip()[:200]}. Run: {REMEDY}. "
        "Never delete listener/.wrangler/state — that signs you out of localhost."
    )
