"""Every repo-surgeon CORE check must be able to FAIL.

The two sibling modules (`repo_surgeon_checks.py`, `repo_surgeon_specs.py`) have had
this treatment since the day they were written. `repo_surgeon_probe.py` — the oldest
and largest of the three, and the one that owns the contract, the mirror pins, the
retired-surface ban, the agent and skill registries, the pipeline invariants and the
whole plan parse — had none, while carrying in its own docstring the argument for
why that is unacceptable: 21 of 38 prose rules had been passing for two months
without ever running, because no gate could fail.

This file closes that. Same shape as its siblings: one synthetic tree per defect, a
clean-tree case per check asserting silence, and an empty-tree case asserting no
check can crash on a partial clone. Same reason for synthetic trees, too — a test
pinned to the live repo's state fails the day somebody legitimately changes it.

Several tests here assert the ABSENCE of a finding. Those are not padding: each one
pins a false positive that `check_plan` was rewritten to kill (the wave-family
resolution, the challenger catalog as the first resolution universe, the P0-P3
severity-grammar collision). Those fixes are recorded only as prose comments in the
check, which is to say they are recorded nowhere that can fail.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import repo_surgeon_probe as probe_mod  # noqa: E402
from _harness import ids, make_probe, track, write  # noqa: E402
from repo_surgeon_probe import CHECKS, Finding, Probe, checks_for  # noqa: E402

PROBE_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "repo_surgeon_probe.py"


# ---------- CT: the contract's own accuracy ----------


def test_contract_clean(tmp_path):
    write(tmp_path, "README.md", "#\n")
    write(tmp_path, "scripts/x.py", "")
    write(tmp_path, "ratchet.json", "{}")
    probe = make_probe(
        tmp_path,
        {
            "root": {"allow_files": ["README.md"], "allow_dirs": ["scripts"]},
            "cites": ["README.md"],
            "protected": ["scripts/**"],
            "size_gates": [{"glob": "scripts/**", "ratchet": "ratchet.json"}],
        },
    )
    probe.check_contract()
    assert ids(probe) == []


@pytest.mark.parametrize(
    "profile,label",
    [
        ({"root": {"allow_files": ["gone.md"]}}, "root.allow_files"),
        ({"root": {"allow_dirs": ["gone"]}}, "root.allow_dirs"),
        ({"cites": ["gone.md"]}, "cites"),
        ({"protected": ["gone/**"]}, "protected"),
    ],
)
def test_contract_flags_every_path_bucket_it_claims_to_audit(tmp_path, profile, label):
    """All four buckets, because a bucket silently dropped from the loop is invisible."""
    probe = make_probe(tmp_path, profile)
    probe.check_contract()
    assert ids(probe) == ["CT-PATH"]


def test_contract_ignores_a_trailing_comment_on_an_entry(tmp_path):
    """Contract entries carry `# why` comments; those are not part of the path."""
    write(tmp_path, "README.md", "#\n")
    probe = make_probe(tmp_path, {"root": {"allow_files": ["README.md]  # the front door"]}})
    probe.check_contract()
    assert ids(probe) == ["CT-PATH"]  # the bracket typo is a real miss
    probe2 = make_probe(tmp_path, {"root": {"allow_files": ["README.md  # the front door"]}})
    probe2.check_contract()
    assert ids(probe2) == []


def test_contract_flags_a_size_gate_whose_ratchet_is_gone(tmp_path):
    """P0: without its ratchet a size gate cannot grandfather, so it fails everything."""
    probe = make_probe(tmp_path, {"size_gates": [{"glob": "a/**", "ratchet": "gone.json"}]})
    probe.check_contract()
    assert ids(probe) == ["CT-RATCHET"]
    assert probe.findings[0].severity == "P0"


# ---------- CT-VERIFY: every verify command resolves to something runnable ----------


def test_verify_commands_clean(tmp_path):
    write(tmp_path, "scripts/gate.py", "")
    write(tmp_path, "app/package.json", json.dumps({"scripts": {"test": "vitest"}}))
    write(tmp_path, "Makefile", "lint:\n\techo\n")
    probe = make_probe(
        tmp_path,
        {"verify": ["python3 scripts/gate.py", "cd app && npm run test", "make lint"]},
    )
    probe.check_verify_commands()
    assert ids(probe) == []


@pytest.mark.parametrize(
    "cmd,tree",
    [
        ("python3 scripts/gone.py", {}),
        ("cd app && npm run test", {}),
        ("cd app && npm run gone", {"app/package.json": '{"scripts": {"test": "vitest"}}'}),
        ("make gone", {"Makefile": "lint:\n\techo\n"}),
    ],
)
def test_verify_commands_flags_every_unrunnable_form(tmp_path, cmd, tree):
    for rel, text in tree.items():
        write(tmp_path, rel, text)
    probe = make_probe(tmp_path, {"verify": [cmd]})
    probe.check_verify_commands()
    assert ids(probe) == ["CT-VERIFY"]


def test_verify_commands_survives_a_malformed_package_json(tmp_path):
    """A broken package.json is a finding about that file, never a traceback.

    The sibling module guards exactly this (repo_surgeon_specs.check_gate_discovery);
    this one did not, so one unparseable file aborted the whole probe — and because
    the probe runs in the pre-commit hook, it aborted the commit with a stack trace
    instead of a sentence.
    """
    write(tmp_path, "app/package.json", "{ not json at all")
    probe = make_probe(tmp_path, {"verify": ["cd app && npm run test"]})
    probe.check_verify_commands()
    assert ids(probe) == ["CT-VERIFY"]
    assert "does not parse" in probe.findings[0].summary


def test_verify_commands_reports_a_form_it_cannot_check(tmp_path):
    """`python3 -m pytest -q` matched none of the recognised forms and was silently
    skipped — a verify entry nobody validates is the contract's promise downgraded to
    a slogan, which is the exact wording of this check's own docstring."""
    probe = make_probe(tmp_path, {"verify": ["python3 -m nosuchmodule -q"]})
    probe.check_verify_commands()
    assert ids(probe) == ["CT-VERIFY"]


def test_verify_commands_accepts_a_module_that_is_importable(tmp_path):
    probe = make_probe(tmp_path, {"verify": ["python3 -m json.tool --help"]})
    probe.check_verify_commands()
    assert ids(probe) == []


# ---------- MI: the fixture-pinned mirror pairs ----------


def test_mirror_pins_clean(tmp_path):
    for rel in ("a.ts", "b.py", "pin.json"):
        write(tmp_path, rel, "")
    probe = make_probe(tmp_path, {"mirrors": [{"a": "a.ts", "b": "b.py", "pinned_by": "pin.json"}]})
    probe.check_mirror_pins()
    assert ids(probe) == []


def test_mirror_pins_flags_a_pair_nothing_pins(tmp_path):
    for rel in ("a.ts", "b.py"):
        write(tmp_path, rel, "")
    probe = make_probe(tmp_path, {"mirrors": [{"a": "a.ts", "b": "b.py"}]})
    probe.check_mirror_pins()
    assert ids(probe) == ["MI-UNPINNED"]


def test_mirror_pins_flags_a_pin_that_is_gone(tmp_path):
    for rel in ("a.ts", "b.py"):
        write(tmp_path, rel, "")
    probe = make_probe(tmp_path, {"mirrors": [{"a": "a.ts", "b": "b.py", "pinned_by": "gone.json"}]})
    probe.check_mirror_pins()
    assert ids(probe) == ["MI-PIN-GONE"]
    assert probe.findings[0].severity == "P0"


def test_mirror_pins_flags_a_side_that_does_not_exist(tmp_path):
    write(tmp_path, "pin.json", "")
    write(tmp_path, "b.py", "")
    probe = make_probe(tmp_path, {"mirrors": [{"a": "gone.ts", "b": "b.py", "pinned_by": "pin.json"}]})
    probe.check_mirror_pins()
    assert ids(probe) == ["MI-PATH"]


def test_mirror_pins_ignores_a_prose_side(tmp_path):
    """The `b` side is sometimes a sentence naming several producers, not a path."""
    write(tmp_path, "a.ts", "")
    write(tmp_path, "pin.json", "")
    probe = make_probe(
        tmp_path,
        {"mirrors": [{"a": "a.ts", "b": "several scripts under scripts/", "pinned_by": "pin.json"}]},
    )
    probe.check_mirror_pins()
    assert ids(probe) == []


# ---------- R1: root membership ----------


def test_root_clean(tmp_path):
    probe = make_probe(tmp_path, {"root": {"allow_files": ["README.md"], "allow_dirs": ["scripts"]}})
    write(tmp_path, "README.md", "#\n")
    write(tmp_path, "scripts/x.py", "")
    track(tmp_path)
    probe.check_root()
    assert ids(probe) == []


def test_root_flags_a_stray_file_and_a_stray_directory(tmp_path):
    probe = make_probe(tmp_path, {"root": {"allow_files": ["README.md"], "allow_dirs": []}})
    write(tmp_path, "README.md", "#\n")
    write(tmp_path, "stray.txt", "")
    write(tmp_path, "strays/x.py", "")
    track(tmp_path)
    probe.check_root()
    assert ids(probe) == ["R1", "R1"]
    assert {f.file for f in probe.findings} == {"stray.txt", "strays"}


def test_root_reports_a_git_failure_rather_than_a_clean_tree(tmp_path):
    """`git ls-files` failing yielded empty output, so every root entry looked
    allow-listed. A gate that reports 'clean' because it could not look is worse than
    one that is absent — the reader cannot tell the two apart."""
    plain = tmp_path / "not-a-repo"
    plain.mkdir()
    probe = Probe(root=plain, profile={"root": {"allow_files": []}})
    probe.check_root()
    assert ids(probe) == ["R1"]
    assert "could not" in probe.findings[0].summary.lower()


def test_root_reports_a_working_directory_that_is_not_there(tmp_path):
    """Not the same failure as git exiting non-zero: this one raises before git runs."""
    probe = Probe(root=tmp_path / "nowhere", profile={"root": {"allow_files": []}})
    probe.check_root()
    assert ids(probe) == ["R1"]


# ---------- RS: the retired-surface ban ----------


def test_retired_surfaces_clean(tmp_path):
    probe = make_probe(tmp_path, {})
    probe.check_retired_surfaces()
    assert ids(probe) == []


@pytest.mark.parametrize("banned", ["server", "site", "shared", "wrangler.toml", "site-worker.js", "docs/cloudflare"])
def test_retired_surfaces_flags_each_banned_path(tmp_path, banned):
    """All six, because a list this check reads from its own body is a list that can
    lose an entry with nothing noticing."""
    write(tmp_path, f"{banned}/x" if "." not in banned else banned, "")
    probe = make_probe(tmp_path, {})
    probe.check_retired_surfaces()
    assert ids(probe) == ["RS-RESURRECT"]
    assert probe.findings[0].severity == "P0"


# ---------- A2: the agent registry (A1, the skill registry, moved to
# test_repo_surgeon_specs.py alongside A3/A4 when check_skill_registry moved) ----------


def test_agent_mirrors_clean(tmp_path):
    write(tmp_path, "infra/claude-agents/alpha.md", "#\n")
    write(tmp_path, ".github/agents/alpha.agent.md", "#\n")
    probe = make_probe(tmp_path, {})
    probe.check_agent_mirrors()
    assert ids(probe) == []


def test_agent_mirrors_ignores_an_underscore_prefixed_spec(tmp_path):
    write(tmp_path, "infra/claude-agents/alpha.md", "#\n")
    write(tmp_path, "infra/claude-agents/_template.md", "#\n")
    write(tmp_path, ".github/agents/alpha.agent.md", "#\n")
    probe = make_probe(tmp_path, {})
    probe.check_agent_mirrors()
    assert ids(probe) == []


def test_agent_mirrors_flags_a_spec_with_no_generated_mirror(tmp_path):
    write(tmp_path, "infra/claude-agents/alpha.md", "#\n")
    probe = make_probe(tmp_path, {})
    probe.check_agent_mirrors()
    assert ids(probe) == ["A2"]


def test_agent_mirrors_flags_a_mirror_with_no_canonical_spec(tmp_path):
    write(tmp_path, "infra/claude-agents/alpha.md", "#\n")
    write(tmp_path, ".github/agents/alpha.agent.md", "#\n")
    write(tmp_path, ".github/agents/ghost.agent.md", "#\n")
    probe = make_probe(tmp_path, {})
    probe.check_agent_mirrors()
    assert ids(probe) == ["A2"]
    assert "ghost" in probe.findings[0].summary


def test_agent_mirrors_escalates_an_empty_canonical_directory(tmp_path):
    probe = make_probe(tmp_path, {})
    probe.check_agent_mirrors()
    assert ids(probe) == ["A2"]
    assert probe.findings[0].severity == "P0"


# ---------- SK: the audit's own references ----------

SPEC_TARGETS = ("skills-staging/repo-surgeon/SKILL.md", "infra/claude-agents/repo-surgeon.md")


def test_self_references_clean(tmp_path):
    write(tmp_path, "docs/thing.md", "#\n")
    for rel in SPEC_TARGETS:
        write(tmp_path, rel, "See [the thing](docs/thing.md) and [the web](https://example.com).\n")
    probe = make_probe(tmp_path, {})
    probe.check_self_references()
    assert ids(probe) == []


def test_self_references_flags_a_missing_spec(tmp_path):
    write(tmp_path, SPEC_TARGETS[0], "#\n")
    probe = make_probe(tmp_path, {})
    probe.check_self_references()
    assert ids(probe) == ["SK-MISSING"]
    assert probe.findings[0].severity == "P0"


def test_self_references_flags_a_dead_relative_link(tmp_path):
    """The check that would have caught the whole rot: the old skill opened by telling
    the reader to load three documents at a path prefix that had moved."""
    for rel in SPEC_TARGETS:
        write(tmp_path, rel, "Load [the gone thing](docs/gone.md).\n")
    probe = make_probe(tmp_path, {})
    probe.check_self_references()
    assert ids(probe) == ["SK-DEADREF", "SK-DEADREF"]
    assert probe.findings[0].line == 1


def test_self_references_ignores_anchors_and_mail_links(tmp_path):
    for rel in SPEC_TARGETS:
        write(tmp_path, rel, "[a](#section) [b](mailto:x@y.z) [c](http://x) [d](https://x)\n")
    probe = make_probe(tmp_path, {})
    probe.check_self_references()
    assert ids(probe) == []


# ---------- AU-A2: a version constant pinned in two places ----------


def _rules(tmp_path, version="1.0"):
    write(tmp_path, "scripts/podcast/_rules.py", f'SLIDE_DECK_CHALLENGER_VERSION = "{version}"\n')


def test_version_constants_clean(tmp_path):
    _rules(tmp_path, "1.0")
    write(tmp_path, "infra/claude-agents/slide-deck-challenger.md", "challenger_version: 1.0\n")
    probe = make_probe(tmp_path, {})
    probe.check_version_constants()
    assert ids(probe) == []


def test_version_constants_flags_a_constant_that_is_gone(tmp_path):
    write(tmp_path, "scripts/podcast/_rules.py", "# nothing here\n")
    probe = make_probe(tmp_path, {})
    probe.check_version_constants()
    assert ids(probe) == ["AU-A2"]


def test_version_constants_flags_a_drifted_pin(tmp_path):
    _rules(tmp_path, "2.0")
    write(tmp_path, "infra/claude-agents/slide-deck-challenger.md", "challenger_version: 1.0\n")
    probe = make_probe(tmp_path, {})
    probe.check_version_constants()
    assert ids(probe) == ["AU-A2"]
    assert probe.findings[0].severity == "P0"


def test_version_constants_flags_a_spec_that_has_vanished(tmp_path):
    """A missing spec made `findall` return nothing, so the loop never ran and the
    check reported success for a file that was not there."""
    _rules(tmp_path, "1.0")
    probe = make_probe(tmp_path, {})
    probe.check_version_constants()
    assert ids(probe) == ["AU-A2"]
    assert "missing" in probe.findings[0].summary


# ---------- AU-V*: the unified book route ----------


def scaffold_book_pipeline(root: Path) -> None:
    write(root, "scripts/podcast/phases/book_driver.py", "compose_book_v2()\n")
    for rel in ("scripts/podcast/_visual_layout.py", "plan-dashboard/scripts/visual-layout.mjs"):
        write(root, rel, 'SCHEMA = "book.visual-layout/v1"\n')
    for sym, rel in [
        ("def compose_book_v2", "scripts/podcast/_book_pipeline_v2.py"),
        ("def author_phase_book_augment", "scripts/podcast/_book_augment.py"),
        ("def apply_fluency_adapt", "scripts/podcast/_book_voice.py"),
        ("def apply_author_companion_voice", "scripts/podcast/_book_voice_companion.py"),
    ]:
        write(root, rel, f"{sym}():\n    pass\n")
    write(root, "scripts/podcast/_book_render_checks.py", "IDS = ['BR-WATERMARK']\n")
    write(root, "docs/standards/book-print-quality.md", "BR-WATERMARK is defined here.\n")
    for rel in (
        "infra/claude-agents/book-render-challenger.md",
        ".github/agents/book-render-challenger.agent.md",
    ):
        write(root, rel, "#\n")


def test_book_pipeline_clean(tmp_path):
    scaffold_book_pipeline(tmp_path)
    probe = make_probe(tmp_path, {})
    probe.check_book_pipeline()
    assert ids(probe) == []


def test_book_pipeline_flags_a_driver_that_stopped_calling_the_unified_compose(tmp_path):
    scaffold_book_pipeline(tmp_path)
    write(tmp_path, "scripts/podcast/phases/book_driver.py", "compose_something_else()\n")
    probe = make_probe(tmp_path, {})
    probe.check_book_pipeline()
    assert ids(probe) == ["AU-V1"]


def test_book_pipeline_flags_a_resurrected_feature_flag(tmp_path):
    scaffold_book_pipeline(tmp_path)
    write(tmp_path, "scripts/podcast/x.py", "if book_pipeline_v2_enabled():\n    pass\n")
    probe = make_probe(tmp_path, {})
    probe.check_book_pipeline()
    assert ids(probe) == ["AU-V1"]
    assert probe.findings[0].severity == "P0"


def test_book_pipeline_flags_a_mirror_that_dropped_the_schema_string(tmp_path):
    scaffold_book_pipeline(tmp_path)
    write(tmp_path, "plan-dashboard/scripts/visual-layout.mjs", "// schema string removed\n")
    probe = make_probe(tmp_path, {})
    probe.check_book_pipeline()
    assert ids(probe) == ["AU-V2"]


def test_book_pipeline_flags_a_missing_unified_stage(tmp_path):
    scaffold_book_pipeline(tmp_path)
    write(tmp_path, "scripts/podcast/_book_voice.py", "# the fluency stage was removed\n")
    probe = make_probe(tmp_path, {})
    probe.check_book_pipeline()
    assert ids(probe) == ["AU-V4"]


def test_book_pipeline_flags_a_render_id_the_standard_does_not_define(tmp_path):
    """The prose rule hardcoded the original four ids, so it never noticed three later
    ones citing a standard that omits them. This resolves whatever the checks cite."""
    scaffold_book_pipeline(tmp_path)
    write(tmp_path, "scripts/podcast/_book_render_checks.py", "IDS = ['BR-WATERMARK', 'BR-NEWLY-ADDED']\n")
    probe = make_probe(tmp_path, {})
    probe.check_book_pipeline()
    assert ids(probe) == ["AU-V5"]
    assert "BR-NEWLY-ADDED" in probe.findings[0].summary


def test_book_pipeline_flags_a_missing_render_challenger_spec(tmp_path):
    scaffold_book_pipeline(tmp_path)
    (tmp_path / ".github/agents/book-render-challenger.agent.md").unlink()
    probe = make_probe(tmp_path, {})
    probe.check_book_pipeline()
    assert ids(probe) == ["AU-V5"]


def test_book_pipeline_flags_a_retired_compose_path_coming_back(tmp_path):
    scaffold_book_pipeline(tmp_path)
    write(tmp_path, "scripts/podcast/generate_translation_edition.py", "")
    probe = make_probe(tmp_path, {})
    probe.check_book_pipeline()
    assert ids(probe) == ["AU-V6"]


# ---------- L: plan conformance ----------

PLAN = "_workspace/plan/refactor/plan.yaml"


def test_plan_clean(tmp_path):
    write(tmp_path, PLAN, "waves:\n  - id: A\n  - id: B\n    depends_on: [A]\n")
    probe = make_probe(tmp_path, {})
    probe.check_plan()
    assert ids(probe) == []


def test_plan_flags_a_missing_plan(tmp_path):
    probe = make_probe(tmp_path, {})
    probe.check_plan()
    assert ids(probe) == ["L1"]
    assert probe.findings[0].severity == "P0"


def test_plan_flags_a_plan_that_does_not_parse(tmp_path):
    write(tmp_path, PLAN, "waves:\n  - id: A\n   bad indent: [\n")
    probe = make_probe(tmp_path, {})
    probe.check_plan()
    assert ids(probe) == ["L1"]
    assert "does not parse" in probe.findings[0].summary


def test_plan_flags_a_plan_with_no_wave_ids(tmp_path):
    write(tmp_path, PLAN, "meta:\n  note: nothing here\n")
    probe = make_probe(tmp_path, {})
    probe.check_plan()
    assert ids(probe) == ["L2"]


def test_plan_flags_a_reference_to_a_wave_that_exists_nowhere(tmp_path):
    write(tmp_path, PLAN, "waves:\n  - id: A\n    depends_on: [ZZ]\n")
    probe = make_probe(tmp_path, {})
    probe.check_plan()
    assert ids(probe) == ["L2"]
    assert "ZZ" in probe.findings[0].summary


def test_plan_resolves_a_reference_to_a_step_not_only_a_wave(tmp_path):
    """`all_plan_ids` is document-wide on purpose: a wave may depend on a STEP, and a
    wave may live under a non-wave key. Resolving against the wave families alone
    reported healthy references as broken."""
    write(
        tmp_path,
        PLAN,
        "waves:\n  - id: A\n    depends_on: [S1]\n    steps:\n      - id: S1\n",
    )
    probe = make_probe(tmp_path, {})
    probe.check_plan()
    assert ids(probe) == []


def test_plan_reports_a_reused_wave_id_without_escalating_it(tmp_path):
    """P3, not P1: the `waves` copies are completion records and the `waves_*` copies
    hold the live steps. Nothing is ambiguous until a reference crosses a family."""
    write(tmp_path, PLAN, "waves:\n  - id: A\nwaves_live:\n  - id: A\n")
    probe = make_probe(tmp_path, {})
    probe.check_plan()
    assert ids(probe) == ["L2-DUP"]
    assert probe.findings[0].severity == "P3"


def test_plan_escalates_a_reused_id_that_is_referenced_across_families(tmp_path):
    write(
        tmp_path,
        PLAN,
        "waves:\n  - id: A\nwaves_live:\n  - id: A\n  - id: B\n    depends_on: [A]\nwaves_other:\n  - id: C\n    depends_on: [A]\n",
    )
    probe = make_probe(tmp_path, {})
    probe.check_plan()
    assert "L2-DUP" in ids(probe)
    dup = [f for f in probe.findings if f.id == "L2-DUP"][0]
    assert dup.severity == "P1"


def test_plan_flags_unresolved_checklist_cross_references(tmp_path):
    write(tmp_path, PLAN, "waves:\n  - id: A\n")
    write(
        tmp_path,
        "_workspace/plan/operations/per-book-ship-checklist.md",
        "- [ ] do the thing *(Q7)*\n",
    )
    probe = make_probe(tmp_path, {})
    probe.check_plan()
    assert ids(probe) == ["L10"]
    assert "Q7" in probe.findings[0].summary


def test_plan_resolves_a_checklist_reference_against_the_challenger_catalog(tmp_path):
    """The checklist's trailing parenthetical cites the podcast-challenger CHECK
    CATALOG, not the plan. Resolving those against plan.yaml reported 18 healthy
    references as broken."""
    write(tmp_path, PLAN, "waves:\n  - id: A\n")
    write(tmp_path, "infra/claude-agents/podcast-challenger.md", "| **W6** | a check |\n")
    write(tmp_path, "_workspace/plan/operations/per-book-ship-checklist.md", "- [ ] do it *(W6)*\n")
    probe = make_probe(tmp_path, {})
    probe.check_plan()
    assert ids(probe) == []


def test_plan_does_not_mistake_the_severity_grammar_for_a_plan_id(tmp_path):
    """Bare P0-P3 IS this repo's severity grammar ('bumped to P0'). Treating it as an
    id produced 30 findings for a single missing translation table."""
    write(tmp_path, PLAN, "waves:\n  - id: A\n")
    write(tmp_path, "_workspace/plan/operations/per-book-ship-checklist.md", "- [ ] do it *(bumped to P0)*\n")
    probe = make_probe(tmp_path, {})
    probe.check_plan()
    assert ids(probe) == []


def test_plan_reports_one_finding_per_root_cause_not_one_per_reference(tmp_path):
    """Thirty findings for a single missing translation table is the same
    noise-generation failure this refactor exists to remove."""
    write(tmp_path, PLAN, "waves:\n  - id: A\n")
    write(
        tmp_path,
        "_workspace/plan/operations/per-book-ship-checklist.md",
        "- [ ] a *(Q7)*\n- [ ] b *(Q8)*\n- [ ] c *(Q9)*\n",
    )
    probe = make_probe(tmp_path, {})
    probe.check_plan()
    assert ids(probe) == ["L10"]


def test_plan_resolves_a_legacy_id_alias(tmp_path):
    write(tmp_path, PLAN, "waves:\n  - id: A\n    legacy_id: Q7\n")
    write(tmp_path, "_workspace/plan/operations/per-book-ship-checklist.md", "- [ ] do it *(Q7)*\n")
    probe = make_probe(tmp_path, {})
    probe.check_plan()
    assert ids(probe) == []


# ---------- waivers ----------


def _finding(fid="R1", fingerprint="R1:stray.txt"):
    return Finding("P1", fid, "a stray root file", "stray.txt", 0, fingerprint)


def _waiver(**over):
    w = {
        "id": "R1",
        "fingerprint": "R1:stray.txt",
        "reason": "ruled deliberate",
        "ruled_on": dt.date(2026, 1, 1),
        "expires": dt.date(2099, 1, 1),
    }
    w.update(over)
    return w


def test_a_waiver_suppresses_its_finding(tmp_path):
    probe = make_probe(tmp_path, {}, waivers=[_waiver()])
    probe.findings = [_finding()]
    probe.apply_waivers(dt.date(2026, 6, 1))
    assert probe.findings == []
    assert len(probe.suppressed) == 1


def test_a_waiver_matches_on_fingerprint_not_only_id(tmp_path):
    """Matching on id alone would let one ruling silence every finding of that class."""
    probe = make_probe(tmp_path, {}, waivers=[_waiver(fingerprint="R1:other.txt")])
    probe.findings = [_finding()]
    probe.apply_waivers(dt.date(2026, 6, 1))
    assert ids(probe) == ["R1"]


def test_an_expired_waiver_re_raises_its_finding_and_says_so(tmp_path):
    probe = make_probe(tmp_path, {}, waivers=[_waiver(expires=dt.date(2026, 1, 2))])
    probe.findings = [_finding()]
    probe.apply_waivers(dt.date(2026, 6, 1))
    assert ids(probe) == ["R1"]
    assert "ruling has expired" in probe.findings[0].summary


def test_a_quoted_expiry_date_still_expires(tmp_path):
    """`isinstance(expires, dt.date)` is False for a string, so a quoted YAML date
    suppressed its finding forever and silently. A waiver ledger whose entries cannot
    expire is the one failure mode it must not have — the whole point of the ledger is
    that a ruling is temporary.
    """
    probe = make_probe(tmp_path, {}, waivers=[_waiver(expires="2026-01-02")])
    probe.findings = [_finding()]
    probe.apply_waivers(dt.date(2026, 6, 1))
    assert ids(probe) == ["R1"]
    assert "ruling has expired" in probe.findings[0].summary


def test_a_waiver_with_no_expiry_is_refused_rather_than_honoured_forever(tmp_path):
    probe = make_probe(tmp_path, {}, waivers=[_waiver(expires=None)])
    probe.findings = [_finding()]
    probe.apply_waivers(dt.date(2026, 6, 1))
    assert ids(probe) == ["R1"]


# ---------- determinism ----------


def test_findings_sort_by_severity_then_id_then_file_then_line():
    unsorted = [
        Finding("P2", "B", "s", "z.py", 2),
        Finding("P0", "Z", "s", "a.py", 1),
        Finding("P2", "B", "s", "a.py", 9),
        Finding("P1", "A", "s", "m.py", 1),
    ]
    got = [(f.severity, f.id, f.file, f.line) for f in sorted(unsorted, key=lambda f: f.sort_key())]
    assert got == [
        ("P0", "Z", "a.py", 1),
        ("P1", "A", "m.py", 1),
        ("P2", "B", "a.py", 9),
        ("P2", "B", "z.py", 2),
    ]


def test_an_unknown_severity_sorts_last_rather_than_crashing():
    assert Finding("P9", "X", "s").sort_key()[0] == 9


# ---------- the registry, and the run it drives ----------


def test_every_registered_check_is_reachable_from_some_scope():
    for spec in CHECKS:
        assert spec in checks_for("all"), spec.name


def test_the_scope_subsets_are_disjoint_and_cover_the_named_scopes():
    podcast, apps = set(checks_for("podcast")), set(checks_for("apps"))
    assert podcast and apps
    assert not (podcast & apps), "a check in two scopes would run twice under --scope all"


def test_the_registry_agrees_with_the_sibling_modules_own_lists(tmp_path):
    """`ALL_CHECKS` in each sibling exists for their empty-repo tests. If the registry
    and those lists disagree, one of them is running checks the other never sees."""
    import repo_surgeon_checks as surface
    import repo_surgeon_specs as specs

    registered = {c.fn for c in CHECKS}
    assert set(surface.ALL_CHECKS) <= registered
    assert set(specs.ALL_CHECKS) <= registered


def test_no_two_checks_share_a_name():
    names = [c.name for c in CHECKS]
    assert len(names) == len(set(names))


@pytest.mark.parametrize("spec", CHECKS, ids=[c.name for c in CHECKS])
def test_every_check_survives_an_empty_repo(tmp_path, spec):
    """No check may crash on a tree that is missing everything.

    A probe that raises is a probe that stops the commit for a reason nobody can read —
    and the first tree any of these meets on a fresh clone is a partial one.
    """
    probe = make_probe(tmp_path, {})
    spec(probe)


@pytest.mark.parametrize("spec", CHECKS, ids=[c.name for c in CHECKS])
def test_every_check_emits_only_ids_it_declares(tmp_path, spec):
    """A finding id the registry does not know about cannot be covered by the ratchet,
    documented in the catalog, or waived by anyone reading either."""
    probe = make_probe(tmp_path, {})
    spec(probe)
    assert {f.id for f in probe.findings} <= set(spec.emits), spec.name


# ---------- the catalog ----------
#
# The prose-rot check turned on the catalog itself. SK-DEADREF already proves the
# skill's LINKS resolve; nothing proved its IDS name checks that exist. That is the
# same failure in a different column: a reader who looks up an id and finds nothing
# supplies their own idea of what it means.

SKILL_MD = Path(__file__).resolve().parents[1] / "skills-staging" / "repo-surgeon" / "SKILL.md"

_TABLE_START = "### Checked by the script"
_TABLE_END = "### What the new groups deliberately do NOT re-check"


def _catalog_ids() -> set[str]:
    text = SKILL_MD.read_text(encoding="utf-8")
    # Fail loudly rather than silently comparing against an empty set: a renamed
    # heading must break this test, not quietly disable it.
    assert _TABLE_START in text, f"{_TABLE_START!r} heading is gone from SKILL.md"
    assert _TABLE_END in text, f"{_TABLE_END!r} heading is gone from SKILL.md"
    table = text[text.index(_TABLE_START) : text.index(_TABLE_END)]
    return set(re.findall(r"`([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*)`", table))


def test_the_catalog_documents_every_id_the_registry_declares():
    missing = sorted({i for c in CHECKS for i in c.emits} - _catalog_ids())
    assert not missing, (
        f"these ids are emitted but absent from SKILL.md's '{_TABLE_START}' table: {missing}. "
        "A finding nobody can look up is a finding nobody can act on."
    )


def test_the_catalog_claims_no_id_the_registry_does_not_emit():
    """The half that actually rotted last time: 21 of 38 documented rules were dead.

    Judgment rules that are deliberately NOT executable live under their own
    headings elsewhere in the skill; this table is only for what the script checks,
    so anything here with no code behind it is a claim that cannot fail.
    """
    phantom = sorted(_catalog_ids() - {i for c in CHECKS for i in c.emits})
    assert not phantom, (
        f"SKILL.md's '{_TABLE_START}' table names {phantom}, which no check emits. "
        "Either wire the check or move the rule to the judgment sections."
    )


# ---------- the exit-code contract ----------
#
# Every case below runs `--scope apps`, whose findings come entirely from the
# contract the test writes. The `all` scope looks for THIS repo's own files, so a
# synthetic tree can never be clean under it and an assertion about exit 0 there
# would be untestable — or, worse, would pass for a reason unrelated to the change.


def _run_probe(cwd: Path, *args):
    return subprocess.run(
        [sys.executable, str(PROBE_SCRIPT), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def _repo_with_profile(tmp_path: Path, profile_yaml: str) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    write(tmp_path, ".repo-audit/profile.yaml", profile_yaml)
    track(tmp_path)
    return tmp_path


APPS_CLEAN = "apps: []\n"

# An app the contract fully accounts for: named in `verify`, its one gate declared
# and wired. What is left over is exactly the two P2s the tests below assert on.
APP_VERIFIED = (
    "apps:\n  - dir: app\n    name: App\n    source: [src]\n    gates: [test]\nverify: ['cd app && npm run test']\n"
)


def test_a_clean_tree_exits_zero(tmp_path):
    repo = _repo_with_profile(tmp_path, APPS_CLEAN)
    r = _run_probe(repo, "--scope", "apps")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "clean" in r.stdout


def test_a_p2_only_report_does_not_block(tmp_path):
    """P2 and P3 print and are counted, but never fail the commit."""
    repo = _repo_with_profile(
        tmp_path,
        APP_VERIFIED,
    )
    write(repo, "app/src/x.ts", "export const a = 1;\n")
    write(repo, "app/package.json", '{"scripts": {"test": "vitest"}}')
    track(repo)
    r = _run_probe(repo, "--scope", "apps")
    assert "CQ-NO-SIZE-GATE" in r.stdout, r.stdout
    assert r.returncode == 0, r.stdout


def test_a_p0_blocks(tmp_path):
    repo = _repo_with_profile(
        tmp_path,
        "apps:\n"
        "  - dir: app\n"
        "    name: App\n"
        "    source: [src]\n"
        "    gates: []\n"
        "    route_kind: manifest\n"
        "    route_policy: app/routes.ts\n"
        "    route_dir: app/routes\n"
        "size_gates:\n  - glob: 'app/**/*.ts'\n",
    )
    write(repo, "app/src/x.ts", "export const a = 1;\n")
    write(repo, "app/package.json", '{"scripts": {}}')
    write(repo, "app/eslint.config.js", "export default [];\n")
    track(repo)
    r = _run_probe(repo, "--scope", "apps")
    assert "RT-POLICY-GONE" in r.stdout, r.stdout
    assert r.returncode == 1


def test_a_missing_contract_exits_two_not_one(tmp_path):
    """Exit 2 means 'the probe could not run'. Conflating it with exit 1 tells CI and
    the pre-commit hook that a defect was found, which is a different thing entirely."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    r = _run_probe(tmp_path)
    assert r.returncode == 2, r.stdout + r.stderr


def test_an_unparseable_contract_exits_two_not_one(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    write(tmp_path, ".repo-audit/profile.yaml", "root:\n  allow_files: [\n")
    r = _run_probe(tmp_path)
    assert r.returncode == 2, r.stdout + r.stderr
    assert "does not parse" in r.stderr


def test_an_unparseable_waiver_ledger_exits_two_not_one(tmp_path):
    repo = _repo_with_profile(tmp_path, APPS_CLEAN)
    write(repo, ".repo-audit/waivers.yaml", "waivers:\n  - id: [\n")
    r = _run_probe(repo, "--scope", "apps")
    assert r.returncode == 2, r.stdout + r.stderr


def test_running_outside_a_git_repo_exits_two_not_one(tmp_path):
    outside = tmp_path / "plain"
    outside.mkdir()
    r = _run_probe(outside)
    assert r.returncode == 2, r.stdout + r.stderr


def test_json_mode_carries_findings_counts_and_suppressions(tmp_path):
    repo = _repo_with_profile(
        tmp_path,
        APP_VERIFIED,
    )
    write(repo, "app/src/x.ts", "export const a = 1;\n")
    write(repo, "app/package.json", '{"scripts": {"test": "vitest"}}')
    track(repo)
    r = _run_probe(repo, "--scope", "apps", "--json")
    payload = json.loads(r.stdout)
    assert {"findings", "suppressed", "counts"} <= payload.keys()
    assert any(f["id"] == "CQ-NO-SIZE-GATE" for f in payload["findings"])


def test_two_runs_on_the_same_tree_produce_identical_output(tmp_path):
    """Determinism is a documented guarantee, and the thing that makes a diff between
    two runs mean something."""
    repo = _repo_with_profile(
        tmp_path,
        APP_VERIFIED,
    )
    write(repo, "app/src/x.ts", "export const a = 1;\n")
    write(repo, "app/package.json", '{"scripts": {"test": "vitest"}}')
    track(repo)
    first, second = _run_probe(repo, "--scope", "apps", "--json"), _run_probe(repo, "--scope", "apps", "--json")
    assert first.stdout == second.stdout


def test_the_probe_module_exposes_what_the_catalog_gate_needs():
    assert hasattr(probe_mod, "CHECKS") and hasattr(probe_mod, "checks_for")
