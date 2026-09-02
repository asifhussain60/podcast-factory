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
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

# The harness lives in tests/_harness.py so all three repo-surgeon modules build
# their synthetic trees the same way. See that file for why synthetic at all.
import repo_surgeon_specs as specs  # noqa: E402
from _harness import ids, make_probe, track, write  # noqa: E402


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


def test_an_unnumbered_migration_is_reported(tmp_path):
    """The third of this check's three severities, and the one that had no case.

    Migrations are applied in name order, so an unnumbered one has no defined
    position — it may run before or after the migration whose table it alters,
    depending only on how the filenames happen to sort.
    """
    probe = make_probe(tmp_path, app_profile())
    scaffold_db(
        tmp_path,
        migrations={
            "0001_a.sql": "CREATE TABLE chapter (id TEXT);",
            "add_episode.sql": "CREATE TABLE episode (id TEXT);",
        },
        writer="",
    )
    specs.check_data_contract(probe)
    assert ids(probe) == ["DB-MIGRATION-GAP"]
    assert probe.findings[0].severity == "P1"
    assert "add_episode.sql" in probe.findings[0].summary


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


# ---------- AU-S2: machine-specific paths in pipeline source ----------


def test_abs_paths_clean(tmp_path):
    write(tmp_path, "scripts/podcast/a.py", "PATH = Path(__file__).parent\n")
    probe = make_probe(tmp_path, {})
    specs.check_abs_paths(probe)
    assert ids(probe) == []


def test_abs_paths_flags_a_hardcoded_home_directory(tmp_path):
    write(tmp_path, "scripts/podcast/a.py", 'ROOT = "/Users/someone/PROJECTS/x"\n')
    probe = make_probe(tmp_path, {})
    specs.check_abs_paths(probe)
    assert ids(probe) == ["AU-S2"]
    assert probe.findings[0].severity == "P0"
    assert probe.findings[0].line == 1


def test_abs_paths_ignores_a_comment_and_a_test_tree(tmp_path):
    write(tmp_path, "scripts/podcast/a.py", '# see /Users/someone/notes.txt\nX = "ok"\n')
    write(tmp_path, "scripts/podcast/tests/test_a.py", 'ROOT = "/Users/someone/x"\n')
    probe = make_probe(tmp_path, {})
    specs.check_abs_paths(probe)
    assert ids(probe) == []


# ---------- A1: the skill registry ----------


def test_skill_registry_clean(tmp_path):
    write(tmp_path, "docs/reference/skill-registry.md", "| skills-staging/alpha/ | a skill |\n")
    write(tmp_path, "skills-staging/alpha/SKILL.md", "#\n")
    probe = make_probe(tmp_path, {})
    specs.check_skill_registry(probe)
    assert ids(probe) == []


def test_skill_registry_flags_a_missing_registry(tmp_path):
    probe = make_probe(tmp_path, {})
    specs.check_skill_registry(probe)
    assert ids(probe) == ["A1"]


def test_skill_registry_flags_a_skill_with_no_row(tmp_path):
    """Matched on the DEFINITION PATH, not the bare name: a loose substring match
    passes on any incidental prose mention."""
    write(tmp_path, "docs/reference/skill-registry.md", "alpha is mentioned here in passing\n")
    write(tmp_path, "skills-staging/alpha/SKILL.md", "#\n")
    probe = make_probe(tmp_path, {})
    specs.check_skill_registry(probe)
    assert ids(probe) == ["A1"]


def test_skill_registry_flags_a_skill_with_no_skill_md(tmp_path):
    write(tmp_path, "docs/reference/skill-registry.md", "| skills-staging/alpha/ |\n")
    write(tmp_path, "skills-staging/alpha/notes.md", "#\n")
    probe = make_probe(tmp_path, {})
    specs.check_skill_registry(probe)
    assert ids(probe) == ["A1"]
    assert "no SKILL.md" in probe.findings[0].summary


def test_skill_registry_survives_a_missing_skills_directory(tmp_path):
    """The registry's absence was a finding; the directory's absence was a traceback.

    A fresh clone that has not run the skill installer has no skills-staging/, so this
    crashed the pre-commit hook on the very first tree it was most likely to meet.
    """
    write(tmp_path, "docs/reference/skill-registry.md", "# registry\n")
    probe = make_probe(tmp_path, {})
    specs.check_skill_registry(probe)
    assert ids(probe) == ["A1"]
    assert "skills-staging" in probe.findings[0].summary


# ---------- A3: project-skill mirrors (skills-staging <-> .claude/skills) ----------


def test_project_skill_mirrors_clean(tmp_path):
    write(tmp_path, "skills-staging/alpha/SKILL.md", "#\n")
    write(tmp_path, ".claude/skills/alpha/SKILL.md", "#\n")
    probe = make_probe(tmp_path, {"project_skills": ["alpha"]})
    specs.check_project_skill_mirrors(probe)
    assert ids(probe) == []


def test_project_skill_mirrors_silent_with_nothing_declared(tmp_path):
    """No project_skills in the contract means this repo doesn't use the pattern —
    silence, not a finding about an empty list."""
    probe = make_probe(tmp_path, {})
    specs.check_project_skill_mirrors(probe)
    assert ids(probe) == []


def test_project_skill_mirrors_flags_a_declared_skill_with_no_canonical_source(tmp_path):
    probe = make_probe(tmp_path, {"project_skills": ["alpha"]})
    specs.check_project_skill_mirrors(probe)
    assert ids(probe) == ["A3"]
    assert "no canonical" in probe.findings[0].summary


def test_project_skill_mirrors_flags_a_missing_runtime_mirror(tmp_path):
    write(tmp_path, "skills-staging/alpha/SKILL.md", "#\n")
    write(tmp_path, ".claude/skills/.keep", "")  # runtime dir exists, alpha's copy doesn't
    probe = make_probe(tmp_path, {"project_skills": ["alpha"]})
    specs.check_project_skill_mirrors(probe)
    assert ids(probe) == ["A3"]
    assert "no generated runtime mirror" in probe.findings[0].summary


def test_project_skill_mirrors_survives_a_missing_claude_directory(tmp_path):
    """A fresh clone or CI has no .claude/skills/ at all (gitignored) — that must
    not read as every declared skill missing its mirror."""
    write(tmp_path, "skills-staging/alpha/SKILL.md", "#\n")
    probe = make_probe(tmp_path, {"project_skills": ["alpha"]})
    specs.check_project_skill_mirrors(probe)
    assert ids(probe) == []


def test_project_skill_mirrors_flags_an_undeclared_runtime_directory(tmp_path):
    write(tmp_path, ".claude/skills/ghost/SKILL.md", "#\n")
    probe = make_probe(tmp_path, {"project_skills": []})
    specs.check_project_skill_mirrors(probe)
    assert ids(probe) == ["A3"]
    assert "ghost" in probe.findings[0].summary


# ---------- A4: bare single-word trigger collisions ----------


def test_trigger_collisions_clean_with_multi_word_phrases(tmp_path):
    write(tmp_path, "infra/claude-agents/alpha.md", "---\ndescription: \"Invoke for: 'do the alpha thing'.\"\n---\n")
    write(
        tmp_path,
        "skills-staging/beta/SKILL.md",
        "---\ndescription: \"Invoke on: 'do the beta thing'.\"\n---\n",
    )
    probe = make_probe(tmp_path, {})
    specs.check_trigger_collisions(probe)
    assert ids(probe) == []


def test_trigger_collisions_flags_a_shared_bare_word(tmp_path):
    """The exact shape that would have let a new skill hijack an existing agent's
    invocation: two specs both claiming the bare word 'challenge' as a trigger."""
    write(tmp_path, "infra/claude-agents/alpha.md", "---\ndescription: \"Invoke for: 'challenge'.\"\n---\n")
    write(tmp_path, "skills-staging/beta/SKILL.md", "---\ndescription: \"Invoke on: 'challenge'.\"\n---\n")
    probe = make_probe(tmp_path, {})
    specs.check_trigger_collisions(probe)
    assert ids(probe) == ["A4"]
    assert "challenge" in probe.findings[0].summary
    assert probe.findings[0].severity == "P2"


def test_trigger_collisions_ignores_the_generated_readme(tmp_path):
    write(tmp_path, "infra/claude-agents/_README.md", "---\ndescription: \"'challenge' appears here too.\"\n---\n")
    write(tmp_path, "skills-staging/beta/SKILL.md", "---\ndescription: \"Invoke on: 'challenge'.\"\n---\n")
    probe = make_probe(tmp_path, {})
    specs.check_trigger_collisions(probe)
    assert ids(probe) == []


# ---------- AU-V7: book identity completeness ----------

NORMALIZE_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "podcast" / "normalize_book_metadata.py"


def write_book(root: Path, slug: str, meta: dict, *, bucket: str = "Islamic") -> None:
    """A minimal book meta.yml under a real bucket dir — `collect()` only needs
    `<bucket>/<slug>/meta.yml` to exist; it never reads the book's other files."""
    import yaml as _yaml

    write(root, f"content/{bucket}/{slug}/meta.yml", _yaml.safe_dump(meta, allow_unicode=True))


@pytest.mark.skipif(not NORMALIZE_SCRIPT.exists(), reason="normalize_book_metadata.py not found")
def test_book_identity_clean(tmp_path):
    write_book(
        tmp_path, "a-book", {"title": "A Book", "author": "Someone", "title_arabic": "كتاب", "study_track": "theology"}
    )
    probe = make_probe(tmp_path, {})
    specs.check_book_identity(probe)
    assert ids(probe) == []


@pytest.mark.skipif(not NORMALIZE_SCRIPT.exists(), reason="normalize_book_metadata.py not found")
def test_book_identity_flags_a_book_with_no_arabic_title_recorded_anywhere(tmp_path):
    # This is the live incident: `purification-of-the-heart` shipped to the
    # Studio shelf with no `title_arabic` and nothing else on disk (no
    # `doctrinal_context`, no sibling volume) could supply one either.
    write_book(
        tmp_path,
        "purification-of-the-heart",
        {"title": "Purification of the Heart", "author": "Someone", "study_track": "theology"},
    )
    probe = make_probe(tmp_path, {})
    specs.check_book_identity(probe)
    assert ids(probe) == ["AU-V7"]
    assert "no native-script title" in probe.findings[0].summary


@pytest.mark.skipif(not NORMALIZE_SCRIPT.exists(), reason="normalize_book_metadata.py not found")
def test_book_identity_stays_quiet_when_the_gap_is_already_filled(tmp_path):
    write_book(
        tmp_path,
        "purification-of-the-heart",
        {
            "title": "Purification of the Heart",
            "author": "Someone",
            "title_arabic": "مطهرة القلوب",
            "study_track": "theology",
        },
    )
    probe = make_probe(tmp_path, {})
    specs.check_book_identity(probe)
    assert ids(probe) == []


def test_book_identity_empty_tree_cannot_crash(tmp_path):
    probe = make_probe(tmp_path, {})
    specs.check_book_identity(probe)
    assert ids(probe) == []
