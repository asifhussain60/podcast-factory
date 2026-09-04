"""The wisdom-db container setup must not ship a password, nor expose the LAN.

`setup-wisdom-db.sh` held the `sa` password as a literal in a tracked file AND
published the container port as `-p 1433:1433`, which Docker binds on 0.0.0.0 —
so every device on the network could reach a SQL Server whose password was
readable in the repo. The two facts are only dangerous together, so both are
pinned here.

The password now comes from `MSSQL_SA_PASSWORD`, the same variable
`tools/source_extractor/db.py` already reads, and the port is bound to loopback.
This is a grep-the-source test on purpose: the defect is a property of the text
a reader (or an attacker with repo access) can see, not of anything the script
computes at runtime.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SETUP = REPO_ROOT / "infra" / "wisdom-db" / "setup-wisdom-db.sh"

# The literal that was committed, split so this test file is not itself a copy.
LEAKED = "Kashkole" + "_Local_2026!"

# Files that quoted the literal while reporting on it.
REPORTS = (
    REPO_ROOT / "_workspace" / "reviews" / "reports" / "2026-05-30-full-repo-audit.md",
    REPO_ROOT / "docs" / "assessment" / "repo-audit-2026-07-18.md",
)


def test_the_setup_script_holds_no_password() -> None:
    """No assignment of a literal secret to the password variable."""
    text = SETUP.read_text(encoding="utf-8")
    assert LEAKED not in text
    assert not re.search(r"^\s*PASSWORD=[\"']?[^\s\"'$]", text, re.MULTILINE)


def test_the_password_must_come_from_the_environment() -> None:
    """`${MSSQL_SA_PASSWORD:?...}` — the run fails loudly when it is unset,
    rather than falling back to a default anyone can read."""
    text = SETUP.read_text(encoding="utf-8")
    assert "MSSQL_SA_PASSWORD:?" in text


def test_the_container_port_is_bound_to_loopback_only() -> None:
    """`-p 1433:1433` binds 0.0.0.0. Only this machine may reach the database."""
    text = SETUP.read_text(encoding="utf-8")
    published = re.findall(r"-p\s+(\S+)", text)
    assert published, "the script no longer publishes a port — update this test"
    for spec in published:
        assert spec.startswith("127.0.0.1:"), f"port published beyond loopback: {spec}"


def test_the_audit_reports_no_longer_quote_the_password() -> None:
    """Scrubbing the reports is part of the fix: a report is tracked text too."""
    for report in REPORTS:
        assert LEAKED not in report.read_text(encoding="utf-8"), report
