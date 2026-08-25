"""Every spec probe must be able to FAIL.

Same contract as tests/test_repo_surgeon_checks.py, and written for the same
reason: the skill's rule is "break the thing it guards, confirm it fails, restore",
which proves a check worked on the day it was written and nothing after. These make
it permanent — one synthetic tree per defect, plus a clean-tree case per group.

Two of these tests exist because the first draft of the check they cover was WRONG
in the live repo and passed anyway, which is the whole argument for the file:

  - `check_generated_artifacts` searched every tracked file for the generator's
    name near `--check`, and every generator documents that flag in its own usage
    comment — so an unpinned generator vouched for itself.
  - `check_standards` judged orphanhood against markdown only, and two standards
    here bind by being READ from Python rather than cited in prose — so it called
    live standards dead.

Both are pinned below, by name, so neither can come back.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import repo_surgeon_specs as specs  # noqa: E402
from repo_surgeon_probe import Probe  # noqa: E402


def make_probe(tmp_path: Path, profile: dict) -> Probe:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    return Probe(root=tmp_path, profile=profile)


def track(root: Path) -> None:
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    # `git grep` reads the working tree only for tracked paths, and an index with
    # no commit behind it is enough — but the files must be ADDED, which is the
    # scope every gate in this repo runs at.


def write(root: Path, rel: str, text: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def ids(probe: Probe) -> list[str]:
    return [f.id for f in probe.findings]


def app_profile(**overrides) -> dict:
    app = {
        "dir": "listener",
        "name": "Test App",
        "source": ["app"],
        "gates": ["test"],
        "migrations": "migrations",
        "sql_writers": ["listener/app/server"],
    }
    app.update(overrides)
    return {"apps": [app], "verify": ["cd listener && npm run test"]}


# ---------- GT-UNDECLARED: the gate the contract never heard of ----------


def test_a_declared_gate_raises_nothing(tmp_path):
    probe = make_probe(tmp_path, app_profile(gates=["test", "smoke"]))
    write(tmp_path, "listener/package.json", json.dumps({"scripts": {"test": "vitest", "smoke": "node s.mjs"}}))
    track(tmp_path)
    specs.check_gate_discovery(probe)
    assert ids(probe) == []


def test_a_gate_shaped_script_the_contract_never_names_is_reported(tmp_path):
    probe = make_probe(tmp_path, app_profile(gates=["test"]))
    write(tmp_path, "listener/package.json", json.dumps({"scripts": {"test": "vitest", "security": "node sec.mjs"}}))
    track(tmp_path)
    specs.check_gate_discovery(probe)
    assert ids(probe) == ["GT-UNDECLARED"]
    assert "security" in probe.findings[0].summary


def test_a_verify_prefixed_script_counts_as_a_gate(tmp_path):
    """The live case this check was written for: `verify:read-aloud` existed as a
    script for a day with the contract silent about it, and gate coverage cannot
    audit a gate it was never told about."""
    probe = make_probe(tmp_path, app_profile(gates=["test"]))
    write(
        tmp_path,
        "listener/package.json",
        json.dumps({"scripts": {"test": "vitest", "verify:read-aloud": "node v.mjs"}}),
    )
    track(tmp_path)
    specs.check_gate_discovery(probe)
    assert ids(probe) == ["GT-UNDECLARED"]
    assert "browser gate" in probe.findings[0].summary


def test_a_fixer_is_not_a_gate(tmp_path):
    """`lint:fix` exists to CHANGE the tree. Demanding CI run it is demanding CI
    rewrite the repo, and a rule that manufactures findings is one people skip."""
    probe = make_probe(tmp_path, app_profile(gates=["test"]))
    write(
        tmp_path,
        "listener/package.json",
        json.dumps({"scripts": {"test": "vitest", "lint:fix": "eslint --fix", "ratchets:update": "node r.mjs"}}),
    )
    track(tmp_path)
    specs.check_gate_discovery(probe)
    assert ids(probe) == []


def test_an_aggregate_of_declared_gates_is_not_a_finding(tmp_path):
    """`npm run check` running six declared gates in a row is a convenience alias.
    Reporting it would double every constituent and teach nothing."""
    probe = make_probe(tmp_path, app_profile(gates=["test", "lint"]))
    write(
        tmp_path,
        "listener/package.json",
        json.dumps({"scripts": {"test": "vitest", "lint": "eslint .", "check": "npm run lint && npm run test"}}),
    )
    track(tmp_path)
    specs.check_gate_discovery(probe)
    assert ids(probe) == []


def test_an_aggregate_hiding_an_undeclared_gate_is_still_a_finding(tmp_path):
    """The alias exemption may not become a laundry: a composite that runs
    something the contract never declared is exactly the condition being sought."""
    probe = make_probe(tmp_path, app_profile(gates=["test"]))
    write(
        tmp_path,
        "listener/package.json",
        json.dumps({"scripts": {"test": "vitest", "check": "npm run test && node undeclared-gate.mjs"}}),
    )
    track(tmp_path)
    specs.check_gate_discovery(probe)
    assert ids(probe) == ["GT-UNDECLARED"]


# ---------- DB: the database contract ----------


def scaffold_db(root: Path, *, migrations: dict, writer: str) -> None:
    for name, sql in migrations.items():
        write(root, f"listener/migrations/{name}", sql)
    write(root, "listener/app/server/publish.ts", writer)
    track(root)


def test_a_write_to_a_created_table_raises_nothing(tmp_path):
    probe = make_probe(tmp_path, app_profile())
    scaffold_db(
        tmp_path,
        migrations={"0001_a.sql": "CREATE TABLE chapter (id TEXT);"},
        writer='db.prepare("INSERT INTO chapter (id) VALUES (?)")',
    )
    specs.check_data_contract(probe)
    assert ids(probe) == []


def test_a_write_to_a_table_no_migration_creates_is_a_p0(tmp_path):
    probe = make_probe(tmp_path, app_profile())
    scaffold_db(
        tmp_path,
        migrations={"0001_a.sql": "CREATE TABLE chapter (id TEXT);"},
        writer='db.prepare("INSERT INTO narration (id) VALUES (?)")',
    )
    specs.check_data_contract(probe)
    assert ids(probe) == ["DB-TABLE-MISSING"]
    assert probe.findings[0].severity == "P0"
    assert "narration" in probe.findings[0].summary


@pytest.mark.parametrize(
    "statement",
    [
        'UPDATE ghost SET status = "published"',
        "DELETE FROM ghost WHERE slug = ?",
        "INSERT OR REPLACE INTO ghost (id) VALUES (?)",
    ],
)
def test_every_write_form_is_seen(tmp_path, statement):
    probe = make_probe(tmp_path, app_profile())
    scaffold_db(tmp_path, migrations={"0001_a.sql": "CREATE TABLE chapter (id TEXT);"}, writer=f'q("{statement}")')
    specs.check_data_contract(probe)
    assert ids(probe) == ["DB-TABLE-MISSING"]


def test_create_table_if_not_exists_counts_as_creating_it(tmp_path):
    probe = make_probe(tmp_path, app_profile())
    scaffold_db(
        tmp_path,
        migrations={"0001_a.sql": "CREATE TABLE IF NOT EXISTS chapter (id TEXT);"},
        writer='q("INSERT INTO chapter (id) VALUES (?)")',
    )
    specs.check_data_contract(probe)
    assert ids(probe) == []


def test_two_migrations_sharing_a_number_is_a_p0(tmp_path):
    """The runner records applied migrations by name, so on any database that saw
    the first, the second never runs and never will."""
    probe = make_probe(tmp_path, app_profile())
    scaffold_db(
        tmp_path,
        migrations={
            "0001_a.sql": "CREATE TABLE chapter (id TEXT);",
            "0001_b.sql": "CREATE TABLE episode (id TEXT);",
        },
        writer="",
    )
    specs.check_data_contract(probe)
    assert ids(probe) == ["DB-MIGRATION-GAP"]
    assert probe.findings[0].severity == "P0"


def test_a_hole_in_the_numbering_is_reported_but_does_not_block(tmp_path):
    probe = make_probe(tmp_path, app_profile())
    scaffold_db(
        tmp_path,
        migrations={
            "0001_a.sql": "CREATE TABLE chapter (id TEXT);",
            "0004_d.sql": "CREATE TABLE episode (id TEXT);",
        },
        writer="",
    )
    specs.check_data_contract(probe)
    assert ids(probe) == ["DB-MIGRATION-GAP"]
    assert probe.findings[0].severity == "P2"


def test_a_writer_the_contract_names_but_that_is_gone_is_a_contract_finding(tmp_path):
    probe = make_probe(tmp_path, app_profile(sql_writers=["scripts/ghost.py"]))
    write(tmp_path, "listener/migrations/0001_a.sql", "CREATE TABLE chapter (id TEXT);")
    track(tmp_path)
    specs.check_data_contract(probe)
    assert ids(probe) == ["CT-PATH"]


def test_an_app_with_no_declared_migrations_is_skipped_not_guessed(tmp_path):
    profile = app_profile()
    profile["apps"][0].pop("migrations")
    probe = make_probe(tmp_path, profile)
    write(tmp_path, "listener/app/server/x.ts", 'q("INSERT INTO whatever (id) VALUES (?)")')
    track(tmp_path)
    specs.check_data_contract(probe)
    assert ids(probe) == []


# ---------- GEN: generated artifacts ----------


def test_a_generator_pinned_by_a_test_raises_nothing(tmp_path):
    probe = make_probe(tmp_path, {"generators": ["app/scripts/sync-colors.mjs"]})
    write(tmp_path, "app/scripts/sync-colors.mjs", "// usage: node scripts/sync-colors.mjs [--check]\n")
    write(tmp_path, "app/test/colors.test.ts", 'execFileSync("node", ["scripts/sync-colors.mjs", "--check"]);')
    track(tmp_path)
    specs.check_generated_artifacts(probe)
    assert ids(probe) == []


def test_a_generator_nothing_checks_is_reported(tmp_path):
    probe = make_probe(tmp_path, {"generators": ["app/scripts/sync-colors.mjs"]})
    write(tmp_path, "app/scripts/sync-colors.mjs", "// usage: node scripts/sync-colors.mjs [--check]\n")
    track(tmp_path)
    specs.check_generated_artifacts(probe)
    assert ids(probe) == ["GEN-UNPINNED"]


def test_a_generator_may_not_vouch_for_itself(tmp_path):
    """The first draft's bug, pinned. Every generator documents `--check` in its own
    usage comment, so a corpus that includes the generator answers "is this pinned?"
    with "it says so itself" — and the one unpinned generator in the repo passed."""
    probe = make_probe(tmp_path, {"generators": ["app/scripts/sync-colors.mjs"]})
    write(
        tmp_path,
        "app/scripts/sync-colors.mjs",
        "// Run `node scripts/sync-colors.mjs --check` in CI to prove this is current.\n",
    )
    track(tmp_path)
    specs.check_generated_artifacts(probe)
    assert ids(probe) == ["GEN-UNPINNED"]


def test_a_generator_offering_no_self_check_is_left_alone(tmp_path):
    """No cheap proof exists, which is a larger conversation than this probe should
    start on its own."""
    probe = make_probe(tmp_path, {"generators": ["app/scripts/copy-thing.mjs"]})
    write(tmp_path, "app/scripts/copy-thing.mjs", "copyFileSync(a, b);\n")
    track(tmp_path)
    specs.check_generated_artifacts(probe)
    assert ids(probe) == []


def test_a_generator_the_contract_names_but_that_is_gone_is_a_contract_finding(tmp_path):
    probe = make_probe(tmp_path, {"generators": ["app/scripts/ghost.mjs"]})
    specs.check_generated_artifacts(probe)
    assert ids(probe) == ["CT-PATH"]


# ---------- SD: standards and the citations pointing at them ----------


def test_a_citation_that_resolves_raises_nothing(tmp_path):
    probe = make_probe(tmp_path, {})
    write(tmp_path, "docs/standards/thing.md", "REQ-TH-010 — do the thing.\n")
    write(tmp_path, "infra/claude-agents/a.md", "Per thing.md: cite REQ-TH-010, never restate it.\n")
    track(tmp_path)
    specs.check_standards(probe)
    assert ids(probe) == []


def test_a_citation_no_standard_defines_is_reported(tmp_path):
    probe = make_probe(tmp_path, {})
    write(tmp_path, "docs/standards/thing.md", "REQ-TH-010 — do the thing.\n")
    write(tmp_path, "infra/claude-agents/a.md", "Per thing.md: gate on REQ-TH-999 before shipping.\n")
    track(tmp_path)
    specs.check_standards(probe)
    assert ids(probe) == ["SD-REQ-DANGLING"]
    assert "REQ-TH-999" in probe.findings[0].summary


def test_a_standard_nothing_references_is_reported(tmp_path):
    probe = make_probe(tmp_path, {})
    write(tmp_path, "docs/standards/thing.md", "REQ-TH-010 — do the thing.\n")
    write(tmp_path, "infra/claude-agents/a.md", "Nothing to see here.\n")
    track(tmp_path)
    specs.check_standards(probe)
    assert ids(probe) == ["SD-ORPHAN"]


def test_a_standard_read_from_code_is_not_an_orphan(tmp_path):
    """The other first-draft bug, pinned. Several standards here bind by being READ
    rather than cited in prose — house-voice.md reaches a book through _rules.py —
    and judging orphanhood against markdown alone called live standards dead."""
    probe = make_probe(tmp_path, {})
    write(tmp_path, "docs/standards/thing.md", "REQ-TH-010 — do the thing.\n")
    write(tmp_path, "scripts/podcast/_rules.py", 'HOUSE = "docs/standards/thing.md"\n')
    track(tmp_path)
    specs.check_standards(probe)
    assert ids(probe) == []


def test_a_standard_referenced_only_by_a_sibling_standard_is_still_an_orphan(tmp_path):
    """A digest pointing at its own full text is not a binding — nothing outside
    docs/standards/ obliges anyone to either."""
    probe = make_probe(tmp_path, {})
    write(tmp_path, "docs/standards/thing.md", "REQ-TH-010 — do the thing.\n")
    write(tmp_path, "docs/standards/thing-digest.md", "The full text is in thing.md.\n")
    write(tmp_path, "infra/claude-agents/a.md", "See thing-digest.md.\n")
    track(tmp_path)
    specs.check_standards(probe)
    assert ids(probe) == ["SD-ORPHAN"]
    assert "thing.md" in probe.findings[0].file


# ---------- every group, on a tree missing everything ----------


@pytest.mark.parametrize("check", list(specs.ALL_CHECKS))
def test_every_check_survives_an_empty_repo(tmp_path, check):
    """A probe that raises stops a commit for a reason nobody can read — and the
    first tree any of these meets on a fresh clone is a partial one."""
    probe = make_probe(tmp_path, {})
    check(probe)
