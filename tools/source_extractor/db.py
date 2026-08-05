"""Thin wrapper around `docker exec sqlcmd` for the wisdom-mssql container.

We use FOR JSON PATH on the SQL Server side so multi-row results with
nvarchar(max) HTML payloads come back cleanly without TSV/quote heartburn.
sqlcmd writes its output to /tmp inside the container; we cat it back.
"""

from __future__ import annotations

import json
import os
import subprocess
import uuid

CONTAINER = "wisdom-mssql"


def _sa_password() -> str:
    """Local wisdom-mssql `sa` password, read from the environment.

    Resolved at call time (not import) so importing this module never fails.
    Set MSSQL_SA_PASSWORD before running the extractor (see .env.example).
    """
    pw = os.environ.get("MSSQL_SA_PASSWORD")
    if not pw:
        raise RuntimeError(
            "MSSQL_SA_PASSWORD is not set. Export the local SQL Server "
            "container's sa password first, e.g. `export MSSQL_SA_PASSWORD=...` "
            "(see .env.example)."
        )
    return pw


def query_json(database: str, sql: str) -> list[dict]:
    """Run `sql` against `database`, expecting a single FOR JSON PATH result.
    Returns the parsed Python object (typically list[dict])."""
    tmp_in = f"/tmp/q-{uuid.uuid4().hex}.sql"
    tmp_out = f"/tmp/q-{uuid.uuid4().hex}.json"
    wrapped = f"SET NOCOUNT ON;\nUSE [{database}];\n{sql}\n"

    subprocess.run(
        ["docker", "exec", "-i", CONTAINER, "sh", "-c", f"cat > {tmp_in}"],
        input=wrapped.encode("utf-8"),
        check=True,
    )
    subprocess.run(
        [
            "docker",
            "exec",
            CONTAINER,
            "/opt/mssql-tools18/bin/sqlcmd",
            "-S",
            "localhost",
            "-U",
            "sa",
            "-P",
            _sa_password(),
            "-C",
            "-y",
            "0",
            "-Y",
            "0",
            "-i",
            tmp_in,
            "-o",
            tmp_out,
        ],
        check=True,
    )
    raw = subprocess.run(
        ["docker", "exec", CONTAINER, "cat", tmp_out],
        capture_output=True,
        check=True,
    ).stdout.decode("utf-8")
    subprocess.run(["docker", "exec", CONTAINER, "rm", "-f", tmp_in, tmp_out], check=False)

    lines = [ln.rstrip("\r") for ln in raw.split("\n")]
    payload_lines = [ln for ln in lines if ln.strip() and not ln.startswith("Changed database context")]
    if not payload_lines:
        return []
    return json.loads("".join(payload_lines))


if __name__ == "__main__":
    rows = query_json("KSESSIONS", "SELECT GroupID, GroupName FROM Groups ORDER BY GroupID FOR JSON PATH;")
    print(f"Smoke test: {len(rows)} groups")
    for r in rows[:3]:
        print(" ", r)
