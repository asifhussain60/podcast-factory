#!/usr/bin/env python3
"""Surface probes for repo-surgeon: the two web apps, the pipeline's capability
surface, test hygiene, and reclaimable debris.

Split out of `repo_surgeon_probe.py` on 2026-08-16 rather than appended to it, for
the reason that file's own docstring gives: the prose catalog rotted because nobody
could hold all of it at once. The probe owns the CONTRACT and the repo-shape
invariants; this module owns everything that is true of a particular surface.

Every function here takes the live `Probe` and calls `probe.add(...)`. The
dependency runs one way — probe imports checks, never the reverse — so `Finding`
stays defined in exactly one place.

Nothing here restates a project fact. The app list, their source roots, their
gates, their route policies and the hygiene rules all come from
`.repo-audit/profile.yaml`. A field that stops resolving is a finding against the
contract, exactly like every other contract entry, and never a silent skip.

WHAT THIS DELIBERATELY DOES NOT DO: re-check anything an existing gate already
proves. The Astro site's route coverage is pinned by site-health-routes.test.mjs;
the Library's gating rule is pinned by test/routes.test.ts; file sizes are pinned
by two ratchets. Duplicating those would produce a second answer to a question that
already has one. What is added here is the layer above them — whether each of those
gates is WIRED anywhere, which is the failure nobody notices, because a gate that
runs only when somebody types it is indistinguishable from a gate that passes.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

# A "gate-shaped" npm script: one whose purpose is to prove the tree is sound.
# Anything outside this vocabulary (dev, deploy, seed, sync-fonts) is a tool, not
# a gate, and is not expected to be wired anywhere.
GATE_SCRIPTS = {
    "build",
    "check",
    "controls",
    "format:check",
    "lint",
    "lint:views",
    "ratchets",
    "security",
    "smoke",
    "test",
    "typecheck",
}

# Gates that CANNOT run on a bare CI runner: each drives a real browser against a
# booted dev server backed by seeded local state. They are still expected to be
# recorded in the contract's verify list — that is where a human-run gate lives.
LOCAL_ONLY_GATES = {"controls", "security", "smoke"}


def _apps(probe) -> list[dict]:
    """The declared web surfaces, validated. An app whose directory is gone is a
    contract finding, not a crash and not a silent skip."""
    out = []
    for app in probe.profile.get("apps") or []:
        d = str(app.get("dir") or "").strip()
        if not d:
            continue
        if not probe.exists(d):
            probe.add(
                "P1",
                "CT-PATH",
                f"contract declares app {d}, which does not exist",
                ".repo-audit/profile.yaml",
                fingerprint=f"CT-PATH:apps:{d}",
            )
            continue
        out.append(app)
    return out


def _source_files(probe, app: dict, suffixes: tuple[str, ...]) -> list[Path]:
    """Tracked source files under an app's declared source roots.

    Tracked, not on-disk: an unstaged scratch file is invisible, which matches the
    scope of every other gate in this repo (CI and pre-commit both see the index).
    """
    root = probe.root / str(app["dir"])
    tracked = subprocess.run(
        ["git", "ls-files", "-z", "--", str(app["dir"])],
        cwd=probe.root,
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    roots = [str(s) for s in (app.get("source") or [])]
    out = []
    for rel in filter(None, tracked.split("\0")):
        p = probe.root / rel
        if p.suffix not in suffixes:
            continue
        try:
            inner = p.relative_to(root).as_posix()
        except ValueError:
            continue
        if roots and not any(inner == r or inner.startswith(f"{r}/") for r in roots):
            continue
        out.append(p)
    return sorted(out)


# ---------- GT: is each gate actually wired anywhere? ----------


def check_gate_coverage(probe) -> None:
    """GT-* — a gate nobody is obliged to run is not a gate.

    This is the check that would have caught the condition it was written for: the
    verify list named the pipeline and the Astro site and was silent about the
    Library, so `npm run security` — the access-control bypass probe on a private
    site — had no home in any contract, any hook or any workflow. It ran when
    somebody remembered.

    Two failures, deliberately distinct. GT-APP-UNVERIFIED is the whole surface
    going unmentioned, which is how one goes unnoticed for months. GT-UNGATED is
    one gate inside an otherwise-covered surface, which is how a new gate is
    written, verified once by hand, and never run again.
    """
    verify = " ".join(str(c) for c in (probe.profile.get("verify") or []))
    workflows = ""
    wf_dir = probe.root / ".github/workflows"
    if wf_dir.is_dir():
        for wf in sorted(wf_dir.glob("*.yml")) + sorted(wf_dir.glob("*.yaml")):
            workflows += wf.read_text(encoding="utf-8", errors="replace")
    hooks = ""
    hook_dir = probe.root / "infra/git-hooks"
    if hook_dir.is_dir():
        for h in sorted(hook_dir.iterdir()):
            if h.is_file():
                hooks += h.read_text(encoding="utf-8", errors="replace")

    for app in _apps(probe):
        d = str(app["dir"])
        name = str(app.get("name") or d)
        if f"cd {d} " not in verify and f"cd {d}&&" not in verify:
            probe.add(
                "P1",
                "GT-APP-UNVERIFIED",
                f"{name} ({d}/) is never named in the contract's verify list — "
                "nothing records what proves a change to it safe",
                ".repo-audit/profile.yaml",
                fingerprint=f"GT-APP-UNVERIFIED:{d}",
            )

        pkg_raw = probe.read(f"{d}/package.json")
        declared = set((json.loads(pkg_raw) if pkg_raw else {}).get("scripts", {}) or {})
        for gate in app.get("gates") or []:
            gate = str(gate)
            if gate not in declared:
                probe.add(
                    "P1",
                    "GT-MISSING",
                    f"contract lists `npm run {gate}` as a gate for {name}, but {d}/package.json defines no such script",
                    ".repo-audit/profile.yaml",
                    fingerprint=f"GT-MISSING:{d}:{gate}",
                )
                continue
            run = f"npm run {gate}"
            # `npm test` and `npm run test` are the same gate spelled two ways;
            # a check that only knew one spelling would report a wired gate as
            # unwired, and a false finding is what teaches people to skip the run.
            spellings = [run, f"npm {gate}"] if gate == "test" else [run]
            wired_ci = any(s in workflows for s in spellings)
            wired_verify = any(s in verify for s in spellings)
            wired_hook = any(s in hooks for s in spellings)
            if wired_ci or wired_verify or wired_hook:
                continue
            local_only = gate in LOCAL_ONLY_GATES
            probe.add(
                "P2" if local_only else "P1",
                "GT-UNGATED",
                f"{name}: `npm run {gate}` is wired into neither CI, a git hook, nor the "
                f"contract's verify list — it runs only when somebody types it"
                + (" (browser gate: CI cannot run it, so the verify list is its home)" if local_only else ""),
                f"{d}/package.json",
                fingerprint=f"GT-UNGATED:{d}:{gate}",
            )


# ---------- RT: routes ----------


def check_routes(probe) -> None:
    """RT-* — the route surface of both apps.

    For the Library the route tree IS the access policy, so its integrity is a
    security property rather than a tidiness one. test/routes.test.ts already
    proves every route sits inside the gate; what it cannot see is a module that
    is in neither place — present on disk, absent from the policy — which reads
    as a page, is reachable by nothing, and drifts out of step with the gate it
    was written under.
    """
    for app in _apps(probe):
        d = str(app["dir"])
        name = str(app.get("name") or d)
        if str(app.get("route_kind")) != "manifest":
            continue

        policy_rel = str(app.get("route_policy") or "")
        route_dir = str(app.get("route_dir") or "")
        policy = probe.read(f"{d}/{policy_rel}")
        if not policy:
            probe.add(
                "P0",
                "RT-POLICY-GONE",
                f"{name}: the route policy {policy_rel} is missing — nothing declares which routes are gated",
                f"{d}/{policy_rel}",
                fingerprint=f"RT-POLICY-GONE:{d}",
            )
            continue

        referenced = {m for m in re.findall(r'"(routes/[^"]+)"', policy)}
        for ref in sorted(referenced):
            if not probe.exists(f"{d}/app/{ref}"):
                probe.add(
                    "P0",
                    "RT-DANGLING",
                    f"{name}: the route policy names {ref}, which does not exist — the build cannot resolve it",
                    f"{d}/{policy_rel}",
                    fingerprint=f"RT-DANGLING:{d}:{ref}",
                )

        on_disk = probe.root / d / route_dir
        if on_disk.is_dir():
            for p in sorted(on_disk.iterdir()):
                if not p.is_file() or p.suffix not in (".ts", ".tsx"):
                    continue
                key = f"{route_dir.split('/')[-1]}/{p.name}"
                if key not in referenced:
                    probe.add(
                        "P1",
                        "RT-ORPHAN",
                        f"{name}: {key} is a route module the policy never references — "
                        "unreachable, and outside the gate it was written under",
                        f"{d}/{route_dir}/{p.name}",
                        fingerprint=f"RT-ORPHAN:{d}:{p.name}",
                    )

        # Only the declared owner may export an ErrorBoundary, or a denied 404 and
        # a genuine 404 render differently and reveal which slugs exist.
        owner = str(app.get("error_boundary_owner") or "")
        if owner:
            for p in _source_files(probe, app, (".ts", ".tsx")):
                rel = p.relative_to(probe.root / d).as_posix()
                if rel == owner:
                    continue
                text = p.read_text(encoding="utf-8", errors="replace")
                if re.search(r"^export\s+(?:async\s+)?(?:function|const|let|var)\s+ErrorBoundary\b", text, re.M):
                    probe.add(
                        "P0",
                        "RT-BOUNDARY",
                        f"{name}: {rel} exports an ErrorBoundary. Only {owner} may — otherwise a "
                        "denied page renders differently from a genuine 404 and becomes distinguishable",
                        f"{d}/{rel}",
                        fingerprint=f"RT-BOUNDARY:{d}:{rel}",
                    )

        # A pathname comparison used as an access gate. `compilePath` matches
        # case-insensitively, so `/Admin/people` defeats a startsWith check, and
        # the `.data` suffix is stripped only after middleware has seen the URL.
        gate_path = re.compile(
            r"""(?:pathname|url\.pathname|request\.url)[^\n;]{0,80}?"""
            r"""\.(?:startsWith|includes|indexOf|match)\s*\(\s*["'`]/(?:admin|api|book|media)""",
            re.I,
        )
        for p in _source_files(probe, app, (".ts", ".tsx")):
            rel = p.relative_to(probe.root / d).as_posix()
            if not (rel.startswith("app/middleware/") or rel.startswith("app/server/")):
                continue
            for n, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if line.lstrip().startswith(("*", "//")):
                    continue
                if gate_path.search(line):
                    probe.add(
                        "P0",
                        "RT-PATH-GATE",
                        f"{name}: {rel} decides access from a pathname comparison. Gating is POSITIONAL "
                        "in this app — the route tree is the policy — because path matching is "
                        "case-insensitive and defeated by a variant spelling",
                        f"{d}/{rel}",
                        n,
                        fingerprint=f"RT-PATH-GATE:{d}:{rel}:{n}",
                    )


# ---------- CAP: the pipeline's capability surface ----------


def check_capabilities(probe) -> None:
    """CAP-* — every capability the project claims resolves to something real.

    Three ways a claim goes hollow, and none of them is caught by an import graph:
    a pipeline phase declared in the canonical list that no driver handles; an
    agent named in a doc with no spec behind it; a command a normative document
    tells a reader to run that no longer exists. `check_doc_links.py` covers
    markdown LINKS, which is a different thing from an invocation in a fenced
    block — the form these are actually written in.
    """
    progress = probe.read("scripts/podcast/_progress.py")
    m = re.search(r"^PHASES\s*=\s*\((.*?)^\)", progress, re.S | re.M)
    if not m:
        probe.add(
            "P0",
            "CAP-PHASE",
            "the canonical PHASES tuple is no longer parseable in _progress.py — the phase registry is the "
            "single source of truth for what the orchestrator can do",
            "scripts/podcast/_progress.py",
        )
    else:
        phases = re.findall(r'"([^"]+)"', m.group(1))
        handlers = ""
        pdir = probe.root / "scripts/podcast/phases"
        if pdir.is_dir():
            for f in sorted(pdir.rglob("*.py")):
                handlers += f.read_text(encoding="utf-8", errors="replace")
        handlers += probe.read("scripts/podcast/orchestrate_book.py")
        for phase in phases:
            if f'"{phase}"' not in handlers:
                probe.add(
                    "P0",
                    "CAP-PHASE",
                    f"phase `{phase}` is declared in the canonical PHASES tuple but no driver or the "
                    "orchestrator handles it — a book that reaches it has nowhere to go",
                    "scripts/podcast/_progress.py",
                    fingerprint=f"CAP-PHASE:{phase}",
                )

    agents = {p.stem for p in sorted((probe.root / "infra/claude-agents").glob("*.md")) if not p.stem.startswith("_")}
    docs = [
        "CLAUDE.md",
        "framework.md",
        "skills-staging/podcast/SKILL.md",
        "skills-staging/repo-surgeon/SKILL.md",
    ]
    # An agent is only "named" when the text uses one of the forms that mean
    # invocation. A bare hyphenated word in prose is not a reference, and treating
    # it as one is how a rule starts manufacturing findings.
    invoke = re.compile(r"(?:subagent_type[\"']?\s*[:=]\s*[\"']([a-z][a-z0-9-]+)|/([a-z][a-z0-9-]+)\b)")
    for rel in docs:
        text = probe.read(rel)
        if not text:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            for a, b in invoke.findall(line):
                cand = a or b
                # Only judge names that LOOK like this repo's agents: a slash
                # command shares its syntax with skills and built-ins, so the
                # universe has to be narrowed to things claiming to be agents.
                if not cand or cand in agents:
                    continue
                if a:  # an explicit subagent_type is unambiguous
                    probe.add(
                        "P1",
                        "CAP-AGENT-REF",
                        f"{rel} invokes agent `{cand}`, which has no spec under infra/claude-agents/",
                        rel,
                        n,
                        fingerprint=f"CAP-AGENT-REF:{cand}",
                    )

    cmd = re.compile(r"(?:python3|bash)\s+((?:scripts|tools|infra)/[\w./-]+\.(?:py|sh))")
    # `python3 scripts/podcast/X.py` is prose standing in for "any script", not a
    # command. An ALL-CAPS basename is this repo's placeholder spelling, and a rule
    # that reports one is a rule that has started manufacturing findings — the
    # exact failure this whole refactor exists to remove.
    placeholder = re.compile(r"/[A-Z][A-Z_]*\.(?:py|sh)$")
    normative = ["CLAUDE.md", "README.md", "framework.md"]
    normative += [p.as_posix() for p in sorted((probe.root / "skills-staging").rglob("SKILL.md"))]
    normative += [p.as_posix() for p in sorted((probe.root / "infra/claude-agents").glob("*.md"))]
    for rel in normative:
        rel = rel.replace(f"{probe.root.as_posix()}/", "")
        text = probe.read(rel)
        if not text:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            for target in cmd.findall(line):
                if placeholder.search(target):
                    continue
                if not probe.exists(target):
                    probe.add(
                        "P1",
                        "CAP-CMD-REF",
                        f"{rel} tells the reader to run {target}, which does not exist",
                        rel,
                        n,
                        fingerprint=f"CAP-CMD-REF:{rel}:{target}",
                    )


# ---------- TS: test hygiene ----------


def check_test_hygiene(probe) -> None:
    """TS-FOCUS — a focused test silently disables every other test in its file.

    P0 and not a style note: the suite still exits zero, CI still goes green, and
    the coverage that vanished is invisible in the log. This is the one test defect
    that looks exactly like success.
    """
    focus = re.compile(r"\b(?:it|test|describe)\.only\s*\(")
    tracked = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=probe.root,
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    for rel in sorted(filter(None, tracked.split("\0"))):
        if not re.search(r"\.(test|spec)\.(ts|tsx|mjs|js)$", rel):
            continue
        text = probe.read(rel)
        for n, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith(("*", "//")):
                continue
            if focus.search(line):
                probe.add(
                    "P0",
                    "TS-FOCUS",
                    "a focused test (.only) is committed — every other test in this file is skipped "
                    "while the suite still reports success",
                    rel,
                    n,
                    fingerprint=f"TS-FOCUS:{rel}:{n}",
                )


# ---------- CQ: clean code across both apps ----------


def check_clean_code(probe) -> None:
    """CQ-* — the code-quality floor each app surface is held to.

    Not a second linter. Two of these three findings are about a MISSING gate
    rather than a line of code, which is the level an audit can add something at:
    ESLint cannot tell you it was never configured, and a size ratchet cannot tell
    you a whole source tree is outside its glob.
    """
    gate_globs = [str(g.get("glob") or "") for g in (probe.profile.get("size_gates") or [])]

    for app in _apps(probe):
        d = str(app["dir"])
        name = str(app.get("name") or d)

        declared_lint = app.get("lint_config")
        if declared_lint is None:
            found = [
                c
                for c in ("eslint.config.js", "eslint.config.mjs", ".eslintrc", ".eslintrc.json")
                if probe.exists(f"{d}/{c}")
            ]
            probe.add(
                "P2" if not found else "P1",
                "CQ-NO-LINT",
                (
                    f"{name} has no lint configuration, so nothing but the type checker looks at its "
                    f"{len(_source_files(probe, app, ('.ts', '.tsx')))} source files — style and the "
                    "correctness rules a linter carries (unused vars, exhaustive deps, floating promises) "
                    "are unenforced"
                )
                if not found
                else f"{name} declares no lint config in the contract but {found[0]} exists — the contract is stale",
                f"{d}/package.json",
                fingerprint=f"CQ-NO-LINT:{d}",
            )
        elif not probe.exists(f"{d}/{declared_lint}"):
            probe.add(
                "P1",
                "CQ-NO-LINT",
                f"{name}: the contract names {declared_lint}, which does not exist",
                ".repo-audit/profile.yaml",
                fingerprint=f"CQ-NO-LINT:{d}:missing",
            )

        if not any(g.startswith(f"{d}/") for g in gate_globs):
            files = _source_files(probe, app, (".ts", ".tsx", ".mjs", ".astro"))
            biggest = max(
                ((len(p.read_text(encoding="utf-8", errors="replace").splitlines()), p) for p in files),
                default=(0, None),
            )
            where = biggest[1].relative_to(probe.root).as_posix() if biggest[1] else d
            probe.add(
                "P2",
                "CQ-NO-SIZE-GATE",
                f"{name} is covered by no size gate — {len(files)} source files with no ceiling; "
                f"the largest is {where} at {biggest[0]} lines",
                ".repo-audit/profile.yaml",
                fingerprint=f"CQ-NO-SIZE-GATE:{d}",
            )

        # Debug LEFTOVERS in shipped source. Build scripts and tests print on
        # purpose; a page does not.
        #
        # `console.log` and `debugger` only — deliberately NOT `console.debug` or
        # `console.trace`. Those are the spellings a gated diagnostic uses, and
        # this app has a real one: `readAlongTrace` emits `console.debug` behind
        # a `?debugReadAloud` query flag and a localStorage opt-in, which is a
        # facility somebody built, not something they forgot. Flagging it taught
        # nothing and cost a reader the trouble of proving it was fine.
        debug = re.compile(r"\bconsole\.log\s*\(|(?<![\w.])debugger\s*;")
        for p in _source_files(probe, app, (".ts", ".tsx", ".astro")):
            rel = p.relative_to(probe.root).as_posix()
            if "/scripts/" in rel or re.search(r"\.(test|spec)\.", rel):
                continue
            for n, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if line.lstrip().startswith(("*", "//")):
                    continue
                if debug.search(line):
                    probe.add(
                        "P2",
                        "CQ-DEBUG",
                        f"{name}: debug output left in shipped source",
                        rel,
                        n,
                        fingerprint=f"CQ-DEBUG:{rel}:{n}",
                    )


# ---------- HY: reclaimable debris ----------


def _dir_bytes(path: Path) -> int:
    total = 0
    for p in path.rglob("*"):
        try:
            if p.is_file() and not p.is_symlink():
                total += p.stat().st_size
        except OSError:
            continue
    return total


def check_debris(probe) -> None:
    """HY-DEBRIS — regenerable artifacts, measured rather than described.

    Reported, never removed here: this probe is wired into a pre-commit hook and
    CI, and a gate that deletes files as a side effect of running is a gate people
    are right to distrust. `scripts/repo_cleanup.py` is the executor, is dry-run by
    default, and refuses the paths the contract marks protected.
    """
    hygiene = probe.profile.get("hygiene") or {}
    total = 0
    biggest: list[tuple[int, str]] = []
    for entry in hygiene.get("reclaimable") or []:
        if entry.get("confirm"):
            continue  # needs an explicit yes; not part of the routine number
        patterns = entry.get("match")
        patterns = [patterns] if isinstance(patterns, str) else list(patterns or [])
        for pat in patterns:
            for hit in _resolve(probe.root, str(pat)):
                size = _dir_bytes(hit) if hit.is_dir() else hit.stat().st_size
                total += size
                biggest.append((size, hit.relative_to(probe.root).as_posix()))

    if total > 50 * 1024 * 1024:
        biggest.sort(reverse=True)
        top = ", ".join(f"{r} ({s / 1024 / 1024:.0f} MB)" for s, r in biggest[:3])
        probe.add(
            "P2",
            "HY-DEBRIS",
            f"{total / 1024 / 1024:.0f} MB of regenerable artifacts on disk — largest: {top}. "
            "Reclaim with `python3 scripts/repo_cleanup.py --apply`",
            "",
            fingerprint="HY-DEBRIS",
        )


def _resolve(root: Path, pattern: str) -> list[Path]:
    """Contract globs, with the noise directories excluded.

    `**/__pycache__` must not walk into node_modules or .git: the answer would be
    dominated by caches belonging to somebody else's tool, and the number an
    operator is shown has to be the number they can actually reclaim.
    """
    skip = (".git/", "node_modules/", ".venv/")
    if "*" not in pattern:
        p = root / pattern
        return [p] if p.exists() else []
    out = []
    for hit in root.glob(pattern):
        rel = hit.relative_to(root).as_posix()
        if any(part in f"{rel}/" for part in skip):
            continue
        out.append(hit)
    return sorted(out)


ALL_CHECKS = (
    check_gate_coverage,
    check_routes,
    check_capabilities,
    check_test_hygiene,
    check_clean_code,
    check_debris,
)
