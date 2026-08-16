"""Every repo-surgeon surface check must be able to FAIL.

The skill's own rule is "break the thing it guards, confirm it fails, restore" —
performed by hand, once, by whoever added the check. That proves the check worked
on the day it was written and nothing thereafter. These tests make it permanent:
each one builds a synthetic tree carrying exactly one defect and asserts the check
reports it, plus a clean-tree case asserting it stays quiet.

A check that cannot fail converts an unknown into false confidence, which is worse
than no check — the lesson recorded in repo_surgeon_probe.py's docstring, where 21
of 38 prose rules had been passing for two months without ever running.

Why synthetic trees rather than the live repo: a test pinned to the repo's current
state fails the day somebody legitimately changes it, and a test that has to be
edited to stay green is one people learn to edit rather than read.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import repo_surgeon_checks as surface  # noqa: E402
from repo_surgeon_probe import Probe  # noqa: E402


def make_probe(tmp_path: Path, profile: dict) -> Probe:
    """A git repo, because several checks read the index rather than the disk."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    return Probe(root=tmp_path, profile=profile)


def track(root: Path) -> None:
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)


def write(root: Path, rel: str, text: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def ids(probe: Probe) -> list[str]:
    return [f.id for f in probe.findings]


# ---------- a minimal app fixture the surface checks can read ----------


def scaffold_app(root: Path, *, scripts: dict, lint: bool = True) -> None:
    write(root, "listener/package.json", json.dumps({"scripts": scripts}))
    write(root, "listener/app/routes.ts", 'route("home", "routes/home.tsx");')
    write(root, "listener/app/routes/home.tsx", "export default function Home() { return null; }\n")
    write(root, "listener/app/root.tsx", "export function ErrorBoundary() { return null; }\n")
    if lint:
        write(root, "listener/eslint.config.js", "export default [];\n")
    track(root)


def app_profile(**overrides) -> dict:
    app = {
        "dir": "listener",
        "name": "Test App",
        "source": ["app"],
        "lint_config": "eslint.config.js",
        "route_kind": "manifest",
        "route_policy": "app/routes.ts",
        "route_dir": "app/routes",
        "error_boundary_owner": "app/root.tsx",
        "gates": ["test"],
    }
    app.update(overrides)
    return {"apps": [app], "verify": ["cd listener && npm run test"], "size_gates": [{"glob": "listener/**/*.ts"}]}


# ---------- GT: gate coverage ----------


def test_gate_coverage_clean(tmp_path):
    probe = make_probe(tmp_path, app_profile())
    scaffold_app(tmp_path, scripts={"test": "vitest run"})
    surface.check_gate_coverage(probe)
    assert ids(probe) == []


def test_gate_coverage_flags_an_app_missing_from_the_verify_list(tmp_path):
    profile = app_profile()
    profile["verify"] = ["make lint"]  # names the app nowhere
    probe = make_probe(tmp_path, profile)
    scaffold_app(tmp_path, scripts={"test": "vitest run"})
    surface.check_gate_coverage(probe)
    assert "GT-APP-UNVERIFIED" in ids(probe)


def test_gate_coverage_flags_a_gate_wired_nowhere(tmp_path):
    profile = app_profile(gates=["test", "security"])
    probe = make_probe(tmp_path, profile)
    scaffold_app(tmp_path, scripts={"test": "vitest run", "security": "node smoke.mjs"})
    surface.check_gate_coverage(probe)
    # `test` is in the verify list; `security` is in nothing.
    assert ids(probe) == ["GT-UNGATED"]
    assert "security" in probe.findings[0].summary


def test_gate_coverage_accepts_a_gate_wired_only_in_ci(tmp_path):
    profile = app_profile(gates=["test", "build"])
    probe = make_probe(tmp_path, profile)
    scaffold_app(tmp_path, scripts={"test": "vitest run", "build": "vite build"})
    write(tmp_path, ".github/workflows/lint.yml", "jobs:\n  a:\n    steps:\n      - run: npm run build\n")
    track(tmp_path)
    surface.check_gate_coverage(probe)
    assert ids(probe) == []


def test_gate_coverage_flags_a_contract_gate_the_app_does_not_define(tmp_path):
    probe = make_probe(tmp_path, app_profile(gates=["typecheck"]))
    scaffold_app(tmp_path, scripts={"test": "vitest run"})
    surface.check_gate_coverage(probe)
    assert "GT-MISSING" in ids(probe)


# ---------- RT: routes ----------


def test_routes_clean(tmp_path):
    probe = make_probe(tmp_path, app_profile())
    scaffold_app(tmp_path, scripts={"test": "x"})
    surface.check_routes(probe)
    assert ids(probe) == []


def test_routes_flags_a_route_the_policy_never_references(tmp_path):
    probe = make_probe(tmp_path, app_profile())
    scaffold_app(tmp_path, scripts={"test": "x"})
    write(tmp_path, "listener/app/routes/secret.tsx", "export default function S() { return null; }\n")
    track(tmp_path)
    surface.check_routes(probe)
    assert ids(probe) == ["RT-ORPHAN"]


def test_routes_flags_a_policy_entry_with_no_file(tmp_path):
    probe = make_probe(tmp_path, app_profile())
    scaffold_app(tmp_path, scripts={"test": "x"})
    write(tmp_path, "listener/app/routes.ts", 'route("home", "routes/home.tsx");\nroute("gone", "routes/gone.tsx");')
    track(tmp_path)
    surface.check_routes(probe)
    assert ids(probe) == ["RT-DANGLING"]


def test_routes_flags_an_error_boundary_outside_its_owner(tmp_path):
    probe = make_probe(tmp_path, app_profile())
    scaffold_app(tmp_path, scripts={"test": "x"})
    write(
        tmp_path,
        "listener/app/routes/home.tsx",
        "export default function Home() { return null; }\nexport function ErrorBoundary() { return null; }\n",
    )
    track(tmp_path)
    surface.check_routes(probe)
    assert ids(probe) == ["RT-BOUNDARY"]


def test_routes_flags_a_pathname_comparison_used_as_an_access_gate(tmp_path):
    probe = make_probe(tmp_path, app_profile())
    scaffold_app(tmp_path, scripts={"test": "x"})
    write(
        tmp_path,
        "listener/app/middleware/admin.ts",
        'export const guard = (url: URL) => url.pathname.startsWith("/admin");\n',
    )
    track(tmp_path)
    surface.check_routes(probe)
    assert ids(probe) == ["RT-PATH-GATE"]


def test_routes_ignores_a_pathname_comparison_inside_a_comment(tmp_path):
    probe = make_probe(tmp_path, app_profile())
    scaffold_app(tmp_path, scripts={"test": "x"})
    write(
        tmp_path,
        "listener/app/middleware/admin.ts",
        '// never write url.pathname.startsWith("/admin") — it is case-insensitive\n',
    )
    track(tmp_path)
    surface.check_routes(probe)
    assert ids(probe) == []


def test_routes_flags_a_missing_policy(tmp_path):
    probe = make_probe(tmp_path, app_profile())
    scaffold_app(tmp_path, scripts={"test": "x"})
    (tmp_path / "listener/app/routes.ts").unlink()
    surface.check_routes(probe)
    assert ids(probe) == ["RT-POLICY-GONE"]


# ---------- CAP: capabilities ----------


def scaffold_pipeline(root: Path, *, phases: list[str], handled: list[str]) -> None:
    write(root, "scripts/podcast/_progress.py", "PHASES = (\n" + "".join(f'    "{p}",\n' for p in phases) + ")\n")
    write(root, "scripts/podcast/phases/driver.py", "".join(f'if phase == "{p}": pass\n' for p in handled))
    write(root, "scripts/podcast/orchestrate_book.py", "# orchestrator\n")
    write(root, "infra/claude-agents/real-agent.md", "# spec\n")
    track(root)


def test_capabilities_clean(tmp_path):
    probe = make_probe(tmp_path, {})
    scaffold_pipeline(tmp_path, phases=["0a", "done"], handled=["0a", "done"])
    surface.check_capabilities(probe)
    assert ids(probe) == []


def test_capabilities_flags_a_phase_no_driver_handles(tmp_path):
    probe = make_probe(tmp_path, {})
    scaffold_pipeline(tmp_path, phases=["0a", "orphan-phase"], handled=["0a"])
    surface.check_capabilities(probe)
    assert ids(probe) == ["CAP-PHASE"]
    assert "orphan-phase" in probe.findings[0].summary


def test_capabilities_flags_an_agent_with_no_spec(tmp_path):
    probe = make_probe(tmp_path, {})
    scaffold_pipeline(tmp_path, phases=["0a"], handled=["0a"])
    write(tmp_path, "CLAUDE.md", 'Invoke with subagent_type: "ghost-agent" when needed.\n')
    track(tmp_path)
    surface.check_capabilities(probe)
    assert "CAP-AGENT-REF" in ids(probe)


def test_capabilities_flags_a_documented_command_that_does_not_exist(tmp_path):
    probe = make_probe(tmp_path, {})
    scaffold_pipeline(tmp_path, phases=["0a"], handled=["0a"])
    write(tmp_path, "README.md", "Run `python3 scripts/podcast/deleted_thing.py` to start.\n")
    track(tmp_path)
    surface.check_capabilities(probe)
    assert "CAP-CMD-REF" in ids(probe)


def test_capabilities_ignores_an_all_caps_placeholder(tmp_path):
    """`python3 scripts/podcast/X.py` is prose for "any script", not a command."""
    probe = make_probe(tmp_path, {})
    scaffold_pipeline(tmp_path, phases=["0a"], handled=["0a"])
    write(tmp_path, "README.md", "invocations of the form `python3 scripts/podcast/X.py`\n")
    track(tmp_path)
    surface.check_capabilities(probe)
    assert ids(probe) == []


# ---------- TS: test hygiene ----------


def test_focus_check_clean(tmp_path):
    probe = make_probe(tmp_path, {})
    write(tmp_path, "a.test.ts", 'it("works", () => {});\n')
    track(tmp_path)
    surface.check_test_hygiene(probe)
    assert ids(probe) == []


def test_focus_check_flags_a_committed_only(tmp_path):
    probe = make_probe(tmp_path, {})
    write(tmp_path, "a.test.ts", 'it.only("works", () => {});\nit("skipped silently", () => {});\n')
    track(tmp_path)
    surface.check_test_hygiene(probe)
    assert ids(probe) == ["TS-FOCUS"]
    assert probe.findings[0].severity == "P0"


def test_focus_check_ignores_only_in_a_comment(tmp_path):
    probe = make_probe(tmp_path, {})
    write(tmp_path, "a.test.ts", "// never commit it.only(...) — it disables the file\n")
    track(tmp_path)
    surface.check_test_hygiene(probe)
    assert ids(probe) == []


# ---------- CQ: clean code ----------


def test_clean_code_clean(tmp_path):
    probe = make_probe(tmp_path, app_profile())
    scaffold_app(tmp_path, scripts={"test": "x"})
    surface.check_clean_code(probe)
    assert ids(probe) == []


def test_clean_code_flags_an_app_with_no_lint_config(tmp_path):
    probe = make_probe(tmp_path, app_profile(lint_config=None))
    scaffold_app(tmp_path, scripts={"test": "x"}, lint=False)
    surface.check_clean_code(probe)
    assert "CQ-NO-LINT" in ids(probe)


def test_clean_code_flags_a_contract_that_names_a_missing_lint_config(tmp_path):
    probe = make_probe(tmp_path, app_profile())
    scaffold_app(tmp_path, scripts={"test": "x"}, lint=False)
    surface.check_clean_code(probe)
    assert "CQ-NO-LINT" in ids(probe)


def test_clean_code_flags_a_source_tree_outside_every_size_gate(tmp_path):
    profile = app_profile()
    profile["size_gates"] = [{"glob": "scripts/podcast/**/*.py"}]
    probe = make_probe(tmp_path, profile)
    scaffold_app(tmp_path, scripts={"test": "x"})
    surface.check_clean_code(probe)
    assert "CQ-NO-SIZE-GATE" in ids(probe)


def test_clean_code_flags_debug_output_in_shipped_source(tmp_path):
    probe = make_probe(tmp_path, app_profile())
    scaffold_app(tmp_path, scripts={"test": "x"})
    write(
        tmp_path, "listener/app/routes/home.tsx", 'console.log("here");\nexport default function H() { return null; }\n'
    )
    track(tmp_path)
    surface.check_clean_code(probe)
    assert "CQ-DEBUG" in ids(probe)


def test_clean_code_ignores_a_gated_diagnostic(tmp_path):
    """`console.debug` behind an opt-in is a facility somebody built, not one they
    forgot. The Library has a real example — read-aloud tracing behind a query
    flag — and flagging it taught nothing while costing a reader the trouble of
    proving it was fine."""
    probe = make_probe(tmp_path, app_profile())
    scaffold_app(tmp_path, scripts={"test": "x"})
    write(
        tmp_path,
        "listener/app/routes/home.tsx",
        'if (enabled) console.debug("[read-aloud]", label);\nexport default function H() { return null; }\n',
    )
    track(tmp_path)
    surface.check_clean_code(probe)
    assert "CQ-DEBUG" not in ids(probe)


def test_clean_code_ignores_debug_output_in_build_scripts(tmp_path):
    probe = make_probe(tmp_path, app_profile(source=["app", "scripts"]))
    scaffold_app(tmp_path, scripts={"test": "x"})
    write(tmp_path, "listener/scripts/build.ts", 'console.log("building");\n')
    track(tmp_path)
    surface.check_clean_code(probe)
    assert "CQ-DEBUG" not in ids(probe)


# ---------- HY: debris ----------


def test_debris_stays_quiet_below_the_threshold(tmp_path):
    probe = make_probe(tmp_path, {"hygiene": {"reclaimable": [{"name": "c", "match": "**/__pycache__"}]}})
    write(tmp_path, "pkg/__pycache__/x.pyc", "tiny")
    surface.check_debris(probe)
    assert ids(probe) == []


def test_debris_reports_a_large_reclaimable_tree(tmp_path):
    probe = make_probe(tmp_path, {"hygiene": {"reclaimable": [{"name": "c", "match": "**/__pycache__"}]}})
    write(tmp_path, "pkg/__pycache__/big.pyc", "x" * (60 * 1024 * 1024))
    surface.check_debris(probe)
    assert ids(probe) == ["HY-DEBRIS"]


def test_debris_skips_entries_that_require_confirmation(tmp_path):
    """A `confirm: true` entry is never part of the routine number — reporting a
    figure an operator cannot reclaim without a separate decision overstates it."""
    probe = make_probe(
        tmp_path,
        {"hygiene": {"reclaimable": [{"name": "c", "match": "**/__pycache__", "confirm": True}]}},
    )
    write(tmp_path, "pkg/__pycache__/big.pyc", "x" * (60 * 1024 * 1024))
    surface.check_debris(probe)
    assert ids(probe) == []


# ---------- the contract's own app entries ----------


def test_a_declared_app_that_does_not_exist_is_a_contract_finding(tmp_path):
    probe = make_probe(tmp_path, app_profile(dir="ghost-app"))
    surface.check_gate_coverage(probe)
    assert ids(probe) == ["CT-PATH"]


@pytest.mark.parametrize("check", [c for c in surface.ALL_CHECKS])
def test_every_check_survives_an_empty_repo(tmp_path, check):
    """No check may crash on a tree that is missing everything.

    A probe that raises is a probe that stops the commit for a reason nobody can
    read — and the first tree any of these meets on a fresh clone is a partial one.
    """
    probe = make_probe(tmp_path, {})
    check(probe)
