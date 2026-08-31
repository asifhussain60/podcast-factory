#!/usr/bin/env python3
"""repo-surgeon deterministic probe — the project-specific half of a repo audit.

The generic half (root sprawl, dead code, duplicates, debris, visual QA) belongs to
the `repo-audit` skill and is NOT re-implemented here. This script checks only the
things that are true of *this* repo and that a generic engine cannot know: the
tracked contract's own accuracy, the retired-surface ban, the four agent mirrors,
the fixture-pinned TS/Python pairs, the book-pipeline invariants, and the plan.

Why a script and not a prose checklist: the prose version rotted. On 2026-07-27 an
audit of `skills-staging/repo-surgeon/SKILL.md` found 21 of its 38 rules dead,
inert, or aimed at directories deleted in the May repo split — and one rule that
manufactured 35 false findings on every run. Nothing had said so for two months
because no gate could fail. Every claim this file makes is executable, so the next
drift is a non-zero exit rather than a slow discovery.

Findings are sorted deterministically (severity -> id -> file -> line), never by
discovery order, so two runs on the same tree produce the same report.

Usage:
    python3 scripts/repo_surgeon_probe.py              # text report
    python3 scripts/repo_surgeon_probe.py --json       # machine-readable
    python3 scripts/repo_surgeon_probe.py --scope podcast   # pipeline probes only
    python3 scripts/repo_surgeon_probe.py --scope apps      # the two web surfaces only

Exit codes:
    0  no unwaived P0/P1 findings
    1  at least one unwaived P0 or P1
    2  the probe could not run (missing contract, unparseable YAML)
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - PyYAML is in requirements.txt
    print("repo_surgeon_probe: PyYAML is required (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

# The surface probes live beside this file. The path insert has to run BEFORE the
# import, so both are exempted from import-ordering: `isort` would hoist the
# import above the line that makes it resolvable.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import repo_surgeon_checks as surface  # noqa: E402, I001
import repo_surgeon_specs as specs  # noqa: E402, I001


SEVERITY_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}

# Every subprocess this probe runs is a git command over a repository whose history
# is several gigabytes. None of them had a timeout, so a hung `git grep` hung the
# pre-commit hook with no output and no way to tell it apart from a slow one.
GIT_TIMEOUT = 120


@dataclass(frozen=True)
class Finding:
    """One defect. `fingerprint` is what a waiver matches on, so it must be stable."""

    severity: str
    id: str
    summary: str
    file: str = ""
    line: int = 0
    fingerprint: str = ""

    def sort_key(self) -> tuple:
        return (SEVERITY_RANK.get(self.severity, 9), self.id, self.file, self.line)


def _waiver_expiry(value) -> "dt.date | None":
    """A waiver's expiry as a date, or None when it cannot be read as one."""
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str):
        try:
            return dt.date.fromisoformat(value.strip())
        except ValueError:
            return None
    return None


@dataclass
class Probe:
    root: Path
    profile: dict
    waivers: list = field(default_factory=list)
    findings: list = field(default_factory=list)
    suppressed: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    scope: str = "all"  # read by _apps() in repo_surgeon_checks.py to isolate one app

    # ---------- helpers ----------

    def add(
        self,
        severity: str,
        fid: str,
        summary: str,
        file: str = "",
        line: int = 0,
        fingerprint: str = "",
    ) -> None:
        self.findings.append(Finding(severity, fid, summary, file, line, fingerprint or f"{fid}:{file}"))

    def read(self, rel: str) -> str:
        """File text, or '' when absent. Absence is a finding, never an exception."""
        p = self.root / rel
        try:
            return p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    def exists(self, rel: str) -> bool:
        return (self.root / rel).exists()

    def py_sources(self, subdir: str, skip_tests: bool = True) -> list[Path]:
        out = []
        for p in sorted((self.root / subdir).rglob("*.py")):
            rel = p.relative_to(self.root).as_posix()
            if skip_tests and ("/tests/" in rel or rel.endswith("_test.py")):
                continue
            out.append(p)
        return out

    # ---------- CT: the contract's own accuracy ----------

    def check_contract(self) -> None:
        """A stale contract is worse than none, so it is audited before it is trusted.

        This mirrors repo-audit Phase 0.5b. It runs here too because the contract is
        the single source of the project facts every other check below reads.
        """
        r = self.profile.get("root") or {}
        buckets = [
            ("root.allow_files", r.get("allow_files") or []),
            ("root.allow_dirs", r.get("allow_dirs") or []),
            ("cites", self.profile.get("cites") or []),
        ]
        for label, entries in buckets:
            for entry in entries:
                name = str(entry).split("#", 1)[0].strip()
                if name and not self.exists(name):
                    self.add(
                        "P1",
                        "CT-PATH",
                        f"contract lists {name} under {label}, which does not exist",
                        ".repo-audit/profile.yaml",
                        fingerprint=f"CT-PATH:{label}:{name}",
                    )

        for entry in self.profile.get("protected") or []:
            base = str(entry).split("#", 1)[0].strip().replace("/**", "")
            if base and not self.exists(base):
                self.add(
                    "P1",
                    "CT-PATH",
                    f"contract protects {base}, which does not exist",
                    ".repo-audit/profile.yaml",
                    fingerprint=f"CT-PATH:protected:{base}",
                )

        for gate in self.profile.get("size_gates") or []:
            ratchet = gate.get("ratchet")
            if ratchet and not self.exists(ratchet):
                self.add(
                    "P0",
                    "CT-RATCHET",
                    f"size gate names ratchet {ratchet}, which does not exist — the gate cannot grandfather",
                    ".repo-audit/profile.yaml",
                    fingerprint=f"CT-RATCHET:{ratchet}",
                )

    def check_verify_commands(self) -> None:
        """Every verify command must resolve to something runnable.

        A verify list is the contract's promise that a change can be proven safe. A
        command naming a deleted script silently downgrades that promise to a slogan.
        """
        for cmd in self.profile.get("verify") or []:
            cmd = str(cmd).split("#", 1)[0].strip()
            if not cmd:
                continue
            # `python3 -m pkg` names a MODULE, not a file, so the script pattern below
            # never matched it and the entry was silently unvalidated — a verify list
            # is the contract's promise that a change can be proven safe, and an entry
            # nobody checks downgrades that promise to a slogan for exactly one line.
            module = re.match(r"python3?\s+-m\s+([A-Za-z_][\w.]*)", cmd)
            if module:
                name = module.group(1)
                try:
                    found = importlib.util.find_spec(name) is not None
                except (ImportError, ValueError):
                    found = False
                if not found:
                    self.add(
                        "P1",
                        "CT-VERIFY",
                        f"verify command runs `python3 -m {name}`, which is not importable",
                        ".repo-audit/profile.yaml",
                        fingerprint=f"CT-VERIFY:module:{name}",
                    )
                continue
            script = re.search(r"(?:python3|bash|sh)\s+(\S+\.(?:py|sh))", cmd)
            if script and not self.exists(script.group(1)):
                self.add(
                    "P1",
                    "CT-VERIFY",
                    f"verify command names {script.group(1)}, which does not exist",
                    ".repo-audit/profile.yaml",
                    fingerprint=f"CT-VERIFY:{script.group(1)}",
                )
                continue
            npm = re.match(r"cd\s+(\S+)\s+&&\s+(.+)", cmd)
            if npm:
                pkg_dir, rest = npm.group(1), npm.group(2)
                pkg = self.read(f"{pkg_dir}/package.json")
                if not pkg:
                    self.add(
                        "P1",
                        "CT-VERIFY",
                        f"verify command runs in {pkg_dir}, which has no package.json",
                        ".repo-audit/profile.yaml",
                        fingerprint=f"CT-VERIFY:{pkg_dir}",
                    )
                    continue
                try:
                    scripts = (json.loads(pkg) or {}).get("scripts", {})
                except json.JSONDecodeError as exc:
                    # A finding about that file, never a traceback. This runs in the
                    # pre-commit hook, where a stack trace blocks the commit with
                    # something nobody can act on.
                    self.add(
                        "P1",
                        "CT-VERIFY",
                        f"{pkg_dir}/package.json does not parse, so the gates it declares cannot be checked: {exc}",
                        f"{pkg_dir}/package.json",
                        fingerprint=f"CT-VERIFY:{pkg_dir}:unparseable",
                    )
                    continue
                for target in re.findall(r"npm run ([\w:.-]+)", rest):
                    if target not in scripts:
                        self.add(
                            "P1",
                            "CT-VERIFY",
                            f"verify command runs `npm run {target}` in {pkg_dir}, which defines no such script",
                            ".repo-audit/profile.yaml",
                            fingerprint=f"CT-VERIFY:{pkg_dir}:{target}",
                        )
            if cmd.startswith("make "):
                target = cmd.split()[1]
                if not re.search(rf"^{re.escape(target)}:", self.read("Makefile"), re.M):
                    self.add(
                        "P1",
                        "CT-VERIFY",
                        f"verify command `{cmd}` names a Makefile target that does not exist",
                        "Makefile",
                        fingerprint=f"CT-VERIFY:make:{target}",
                    )
                continue
            if not (script or npm):
                self.add(
                    "P1",
                    "CT-VERIFY",
                    f"verify command `{cmd}` is in no form this check can resolve, so nothing "
                    "confirms it still runs — add the form here or rewrite the command",
                    ".repo-audit/profile.yaml",
                    fingerprint=f"CT-VERIFY:unresolvable:{cmd}",
                )

    def check_mirror_pins(self) -> None:
        """Two files the contract says must change together, with nothing checking it,
        is a silent-divergence machine. Worse than a crash: nothing surfaces it."""
        for m in self.profile.get("mirrors") or []:
            pin = m.get("pinned_by")
            label = f"{m.get('a')} <-> {m.get('b')}"
            if not pin:
                self.add(
                    "P1",
                    "MI-UNPINNED",
                    f"mirror pair is unpinned: {label}",
                    ".repo-audit/profile.yaml",
                    fingerprint=f"MI-UNPINNED:{m.get('a')}",
                )
                continue
            if not self.exists(pin):
                self.add(
                    "P0",
                    "MI-PIN-GONE",
                    f"mirror {label} claims to be pinned by {pin}, which does not exist",
                    ".repo-audit/profile.yaml",
                    fingerprint=f"MI-PIN-GONE:{pin}",
                )
            # The `a` side may be a real path; the `b` side is sometimes a prose list
            # of several producers, so only single-token paths are checked.
            for side in ("a", "b"):
                val = str(m.get(side) or "")
                if val and " " not in val and not self.exists(val):
                    self.add(
                        "P1",
                        "MI-PATH",
                        f"mirror pair names {val}, which does not exist",
                        ".repo-audit/profile.yaml",
                        fingerprint=f"MI-PATH:{val}",
                    )

    # ---------- R1 / RS: root membership and the retired-surface ban ----------

    def check_root(self) -> None:
        """Root membership is the contract's call, not this script's. That is the whole
        point of having the contract: the list lives beside the code it describes."""
        r = self.profile.get("root") or {}
        allow_files = {str(x).split("#", 1)[0].strip() for x in (r.get("allow_files") or [])}
        allow_dirs = {str(x).split("#", 1)[0].strip() for x in (r.get("allow_dirs") or [])}
        try:
            listing = subprocess.run(
                ["git", "ls-files", "-z", "--", ":(top)"],
                cwd=self.root,
                capture_output=True,
                text=True,
                check=False,
                timeout=GIT_TIMEOUT,
            )
            failure = (listing.stderr or "").strip() if listing.returncode != 0 else ""
        except (OSError, subprocess.SubprocessError) as exc:
            # A missing working directory, no git on PATH, or a hung index: all three
            # are "could not look", and none of them is "nothing to report".
            listing, failure = None, str(exc)
        if failure or listing is None:
            # Empty output used to make every root entry look allow-listed. A gate
            # that reports "clean" because it could not look is worse than one that
            # is absent: the reader cannot tell the two apart.
            detail = (failure.splitlines() or ["no detail"])[0][:160]
            self.add(
                "P1",
                "R1",
                f"root membership could not be checked — git ls-files failed: {detail}",
                ".repo-audit/profile.yaml",
                fingerprint="R1:git-unavailable",
            )
            return
        tracked = listing.stdout
        top = set()
        for rel in filter(None, tracked.split("\0")):
            top.add(rel.split("/", 1)[0] if "/" in rel else rel)
        for entry in sorted(top):
            if (self.root / entry).is_dir():
                if entry not in allow_dirs:
                    self.add("P1", "R1", f"root directory not on the contract allow-list: {entry}/", entry)
            elif entry not in allow_files:
                self.add("P1", "R1", f"root file not on the contract allow-list: {entry}", entry)

    def check_retired_surfaces(self) -> None:
        """CLAUDE.md forbids recreating these. The old prose rule did the opposite —
        it allow-listed two of them at root while the brief banned them."""
        banned = [
            "server",
            "site",
            "shared",
            "wrangler.toml",
            "site-worker.js",
            "docs/cloudflare",
        ]
        for rel in banned:
            if self.exists(rel):
                self.add(
                    "P0",
                    "RS-RESURRECT",
                    f"{rel} was retired in the 2026-05-22 split and CLAUDE.md forbids recreating it",
                    rel,
                    fingerprint=f"RS-RESURRECT:{rel}",
                )

    # ---------- A: architecture invariants specific to this repo ----------

    def check_agent_mirrors(self) -> None:
        """Four homes, three generated. A hand-edited copy going a generation stale is
        how .codex/agents/book-challenger.toml drifted while claiming to be a mirror."""
        canonical = {
            p.stem for p in sorted((self.root / "infra/claude-agents").glob("*.md")) if not p.stem.startswith("_")
        }
        if not canonical:
            self.add("P0", "A2", "no canonical agent specs found under infra/claude-agents/", "infra/claude-agents")
            return
        github = {p.name[: -len(".agent.md")] for p in (self.root / ".github/agents").glob("*.agent.md")}
        for missing in sorted(canonical - github):
            self.add(
                "P1",
                "A2",
                f"agent {missing} has no generated .github mirror — run scripts/podcast/sync-agent-wrappers.sh",
                f".github/agents/{missing}.agent.md",
                fingerprint=f"A2:github:{missing}",
            )
        for orphan in sorted(github - canonical):
            self.add(
                "P1",
                "A2",
                f".github mirror {orphan} has no canonical spec under infra/claude-agents/",
                f".github/agents/{orphan}.agent.md",
                fingerprint=f"A2:orphan:{orphan}",
            )

    def check_self_references(self) -> None:
        """The check that would have caught this whole rot two months ago.

        Every relative markdown link and backticked path in the audit's OWN spec files
        must resolve. The old skill opened by telling the reader to load three documents
        at a path prefix that had moved, and nothing ever said so.
        """
        targets = [
            "skills-staging/repo-surgeon/SKILL.md",
            "infra/claude-agents/repo-surgeon.md",
        ]
        link = re.compile(r"\[[^\]]+\]\((?!https?:|#|mailto:)([^)#]+)")
        for rel in targets:
            text = self.read(rel)
            if not text:
                self.add("P0", "SK-MISSING", f"{rel} does not exist", rel)
                continue
            for n, line in enumerate(text.splitlines(), 1):
                for raw in link.findall(line):
                    cand = raw.strip()
                    if not cand or cand.startswith("<"):
                        continue
                    resolved = (self.root / rel).parent / cand if cand.startswith(("./", "../")) else self.root / cand
                    try:
                        ok = resolved.resolve().exists()
                    except OSError:
                        ok = False
                    if not ok:
                        self.add(
                            "P1",
                            "SK-DEADREF",
                            f"dead reference in the audit's own spec: {cand}",
                            rel,
                            n,
                            fingerprint=f"SK-DEADREF:{rel}:{cand}",
                        )

    # ---------- AU: pipeline + book-pipeline conformance ----------

    def check_version_constants(self) -> None:
        """AU-A2 — a version constant pinned in two places drifts.

        podcast-challenger is deliberately exempt: its spec instructs the agent to read
        CHALLENGER_VERSION at run time rather than hardcode it, so there is no second
        copy to drift. Only genuinely duplicated pins are compared.
        """
        rules = self.read("scripts/podcast/_rules.py")
        pairs = [
            ("SLIDE_DECK_CHALLENGER_VERSION", "infra/claude-agents/slide-deck-challenger.md", "challenger_version"),
        ]
        for const, spec, key in pairs:
            m = re.search(rf'^{const}\s*=\s*"([^"]+)"', rules, re.M)
            if not m:
                self.add("P1", "AU-A2", f"{const} is no longer defined in _rules.py", "scripts/podcast/_rules.py")
                continue
            want = m.group(1)
            text = self.read(spec)
            if not text:
                # An absent spec made `findall` return nothing, so the loop never ran
                # and the check reported success for a file that was not there.
                self.add(
                    "P1",
                    "AU-A2",
                    f"{spec} is missing, so nothing pins {const} on the spec side",
                    spec,
                    fingerprint=f"AU-A2:{const}:spec-missing",
                )
                continue
            found = re.findall(rf"{key}:\s*([0-9][0-9.]*)", text)
            for got in found:
                if got != want:
                    self.add(
                        "P0",
                        "AU-A2",
                        f"{const} is {want} in _rules.py but {spec} pins {key} at {got}",
                        spec,
                        fingerprint=f"AU-A2:{const}",
                    )

    def check_book_pipeline(self) -> None:
        """AU-V1/V2/V4/V5/V6 — the unified book route is the only route, its contract
        mirrors agree, and its governance ids resolve."""
        # AU-V1: unified compose, no resurrected flag dispatch.
        driver = self.read("scripts/podcast/phases/book_driver.py")
        if "compose_book_v2" not in driver:
            self.add(
                "P0", "AU-V1", "book_driver no longer calls compose_book_v2", "scripts/podcast/phases/book_driver.py"
            )
        for p in self.py_sources("scripts/podcast"):
            text = p.read_text(encoding="utf-8", errors="replace")
            for n, line in enumerate(text.splitlines(), 1):
                if re.search(r"book_pipeline_v2_enabled|FEATURE_FLAG_", line):
                    rel = p.relative_to(self.root).as_posix()
                    self.add(
                        "P0", "AU-V1", "a retired feature flag has reappeared", rel, n, fingerprint=f"AU-V1:{rel}:{n}"
                    )

        # AU-V2: the visual-layout schema string agrees across both live mirrors.
        schema = "book.visual-layout/v1"
        for rel in ("scripts/podcast/_visual_layout.py", "plan-dashboard/scripts/visual-layout.mjs"):
            if schema not in self.read(rel):
                self.add(
                    "P0",
                    "AU-V2",
                    f"{rel} no longer declares the {schema} schema string",
                    rel,
                    fingerprint=f"AU-V2:{rel}",
                )

        # AU-V4: the unified stages the knob matrix references must exist.
        for sym, rel in [
            ("def compose_book_v2", "scripts/podcast/_book_pipeline_v2.py"),
            ("def author_phase_book_augment", "scripts/podcast/_book_augment.py"),
            ("def apply_fluency_adapt", "scripts/podcast/_book_voice.py"),
            # Split out 2026-08-15 (DR-005) into its own module, re-exported from
            # _book_voice.py so every `from _book_voice import ...` caller is unaffected.
            ("def apply_author_companion_voice", "scripts/podcast/_book_voice_companion.py"),
        ]:
            if sym not in self.read(rel):
                self.add("P1", "AU-V4", f"{rel} no longer defines `{sym[4:]}`", rel, fingerprint=f"AU-V4:{sym}")

        # AU-V5: every BR-* id the render checks cite must exist in the standard.
        # This is the check the prose rule got wrong: it hardcoded the original four
        # and so never noticed three later ones citing a standard that omits them.
        checks = self.read("scripts/podcast/_book_render_checks.py")
        standard = self.read("docs/standards/book-print-quality.md")
        for bid in sorted(set(re.findall(r"\bBR-[A-Z][A-Z-]+\b", checks))):
            if bid not in standard:
                self.add(
                    "P1",
                    "AU-V5",
                    f"the render checks cite {bid}, which the print-quality standard does not define",
                    "docs/standards/book-print-quality.md",
                    fingerprint=f"AU-V5:{bid}",
                )
        for rel in (
            "infra/claude-agents/book-render-challenger.md",
            ".github/agents/book-render-challenger.agent.md",
        ):
            if not self.exists(rel):
                self.add("P1", "AU-V5", f"the book-render-challenger spec is missing from {rel}", rel)

        # AU-V6: retired compose paths stay retired.
        if self.exists("scripts/podcast/generate_translation_edition.py"):
            self.add(
                "P1",
                "AU-V6",
                "the retired translation-edition script has reappeared",
                "scripts/podcast/generate_translation_edition.py",
            )

    def check_book_identity(self) -> None:
        """AU-V7 — every book's identity is complete, or the gap is on record.

        `normalize_book_metadata.py` already computes this (that is the whole
        point of `.unknown()`: report a gap, never invent one — guessing an
        author or an Arabic title for a religious text is the one thing that
        script refuses to do). What it lacked was a gate that runs it: the
        script sat as a manual report nobody remembered to re-run, which is
        how `purification-of-the-heart` shipped to the Studio shelf with no
        Arabic title while every sibling Sessions/Islamic book had one. This
        check re-runs THAT script rather than re-deriving its resolution
        order — a second answer to "what is this book called" is exactly the
        drift the script's own docstring exists to end.

        P2, not P1: a missing identity field is a real gap, but it is closed
        by a human supplying the true name, not by a commit being blocked.
        """
        script = Path(__file__).resolve().parent / "podcast" / "normalize_book_metadata.py"
        if not script.exists():
            return
        try:
            result = subprocess.run(
                [sys.executable, str(script), "--json"],
                cwd=self.root,
                env={**os.environ, "PODCAST_FACTORY_ROOT": str(self.root)},
                capture_output=True,
                text=True,
                check=False,
                timeout=GIT_TIMEOUT,
            )
            data = json.loads(result.stdout or "{}")
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
            return
        for slug, gaps in sorted((data.get("unknown") or {}).items()):
            for gap in gaps:
                self.add(
                    "P2",
                    "AU-V7",
                    f"{slug} has no {gap} recorded anywhere the pipeline reads",
                    f"content/*/{slug}/meta.yml",
                    fingerprint=f"AU-V7:{slug}:{gap}",
                )

    # ---------- L: plan conformance ----------

    def wave_families(self, plan: dict) -> list:
        keys = [k for k in plan if k == "waves" or k.startswith(("waves_", "wave_"))]
        out = []
        for k in sorted(keys):
            if isinstance(plan.get(k), list):
                out.extend(x for x in plan[k] if isinstance(x, dict))
        return out

    @staticmethod
    def all_plan_ids(plan: dict) -> dict:
        """Every `id:` in the document, mapped to the key path that defines it.

        Resolving references against the `waves`/`waves_*` families alone produced two
        false positives in one sitting: `A1` is a STEP of wave A, and wave `F`
        ("Archetype Completion") lives under the top-level `excluded_by_design` key,
        which matches no wave-family pattern. A reference is only dangling if the id
        exists nowhere in the plan, so the universe has to be the whole document.
        """
        found: dict[str, list[str]] = {}

        def walk(node, path: str = "") -> None:
            if isinstance(node, dict):
                if node.get("id") is not None:
                    found.setdefault(str(node["id"]), []).append(path)
                for k, v in node.items():
                    walk(v, f"{path}.{k}" if path else str(k))
            elif isinstance(node, list):
                for item in node:
                    walk(item, path)

        walk(plan)
        return found

    def check_plan(self) -> None:
        rel = "_workspace/plan/refactor/plan.yaml"
        raw = self.read(rel)
        if not raw:
            self.add("P0", "L1", "the refactor plan is missing", rel)
            return
        try:
            plan = yaml.safe_load(raw) or {}
        except yaml.YAMLError as exc:
            self.add("P0", "L1", f"the refactor plan does not parse: {exc}", rel)
            return

        waves = self.wave_families(plan)
        ids = [w.get("id") for w in waves if w.get("id")]
        if not ids:
            self.add("P0", "L2", "no wave ids found in any wave family", rel)
            return

        # Which family defines each wave, so a reference can be judged intra- or
        # cross-family. A duplicated id is only AMBIGUOUS when something outside the
        # defining family points at it; within one family, proximity resolves it.
        family_of: dict[str, set] = {}
        for key in sorted(k for k in plan if k == "waves" or k.startswith(("waves_", "wave_"))):
            for w in plan.get(key) or []:
                if isinstance(w, dict) and w.get("id"):
                    family_of.setdefault(str(w["id"]), set()).add(key)

        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            ambiguous = []
            for key in sorted(k for k in plan if k == "waves" or k.startswith(("waves_", "wave_"))):
                for w in plan.get(key) or []:
                    if not isinstance(w, dict):
                        continue
                    for ref in (w.get("depends_on") or []) + (w.get("parallel_with") or []):
                        if str(ref) in dupes and key not in family_of.get(str(ref), set()):
                            ambiguous.append(f"{key}.{w.get('id')} -> {ref}")
            if ambiguous:
                self.add(
                    "P1",
                    "L2-DUP",
                    f"wave id(s) {', '.join(dupes)} are defined in more than one family AND are "
                    f"referenced across families, so these cannot be resolved: {'; '.join(ambiguous)}",
                    rel,
                    fingerprint=f"L2-DUP:ambiguous:{','.join(dupes)}",
                )
            else:
                # Reported, not escalated. The condition is real and known: the snapshot
                # generators resolve it by preferring the entry that carries steps, and
                # that rule is pinned by tests/test_snapshot_regenerator_parity.py. The
                # `waves` copies are completion records (execution_status: completed_*),
                # the `waves_*` copies hold the live steps. No current reference crosses
                # a family, so nothing is ambiguous today — but a future one would be,
                # and a reader of the plan has no way to tell which entry is meant.
                self.add(
                    "P3",
                    "L2-DUP",
                    f"wave id(s) {', '.join(dupes)} are reused across wave families; no reference "
                    "crosses a family today, so nothing is ambiguous yet, but the letters are "
                    "overloaded and a cross-family reference would be unresolvable",
                    rel,
                    fingerprint=f"L2-DUP:{','.join(dupes)}",
                )

        # Resolve against every id in the document, not just the wave families. See
        # all_plan_ids: a wave may depend on a STEP, and a wave may live under a
        # non-wave key (`excluded_by_design` holds wave F).
        known_targets = self.all_plan_ids(plan)
        for w in waves:
            for dep in (w.get("depends_on") or []) + (w.get("parallel_with") or []):
                if str(dep) not in known_targets:
                    self.add(
                        "P1",
                        "L2",
                        f"wave {w.get('id')} references {dep}, which is defined nowhere in the plan",
                        rel,
                        fingerprint=f"L2:{w.get('id')}:{dep}",
                    )

        checklist = "_workspace/plan/operations/per-book-ship-checklist.md"
        text = self.read(checklist)
        if not text:
            return

        # Same document-wide universe as L2 — plus legacy_id aliases and any explicit
        # translation map. Scanning only the wave families under-resolved here too.
        known = set(known_targets)
        legacy_ids = []

        def collect_legacy(node) -> None:
            if isinstance(node, dict):
                if node.get("legacy_id"):
                    legacy_ids.append(str(node["legacy_id"]))
                for v in node.values():
                    collect_legacy(v)
            elif isinstance(node, list):
                for x in node:
                    collect_legacy(x)

        collect_legacy(plan)
        known.update(legacy_ids)
        legacy = (plan.get("meta") or {}).get("legacy_id_map") or {}
        known.update(str(k) for k in legacy)
        known.update(str(v) for v in legacy.values())

        # The checklist's trailing parenthetical cites the podcast-challenger CHECK
        # CATALOG (ids A1..W6), not the plan — its own header says so. Resolving those
        # against plan.yaml reported 18 healthy references as broken. The universe is
        # the catalog first, then the plan, then any R-* rule name.
        catalog = self.read("infra/claude-agents/podcast-challenger.md")
        known |= set(re.findall(r"^\|\s*\*{0,2}([A-Z]\d{1,2})\*{0,2}\s*\|", catalog, re.M))
        known |= set(re.findall(r"\b(R-[A-Z][A-Z0-9-]+)\b", catalog))
        known |= set(re.findall(r"\b(R-[A-Z][A-Z0-9-]+)\b", self.read("scripts/podcast/_rules.py")))

        # The checklist's row ids (**A6**, **P4**, **T1**) are its OWN scheme; only the
        # trailing italic parenthetical is a cross-reference. The prose rule scanned
        # whole lines, so it flagged row ids and the P0-P3 severity grammar as unknown
        # plan ids — 30 findings, none of them real.
        unresolved: dict[str, int] = {}
        for n, line in enumerate(text.splitlines(), 1):
            if not re.match(r"\s*-\s*\[", line):
                continue
            for annot in re.findall(r"\*\(([^)]*)\)\*", line):
                for ref in re.findall(r"\b([A-Z]\d+(?:\.\d+)?)\b", annot):
                    # Bare P0-P3 IS this repo's severity grammar ("bumped to P0"), and
                    # the collision with a legacy id of the same spelling is unresolvable
                    # from text. Dotted forms (P1.1) are unambiguous and still counted.
                    if ref in ("P0", "P1", "P2", "P3"):
                        continue
                    if ref not in known:
                        unresolved.setdefault(ref, n)

        # One root cause, one finding. Thirty findings for a single missing translation
        # table is the same noise-generation failure this refactor exists to remove.
        if unresolved:
            listed = ", ".join(sorted(unresolved))
            self.add(
                "P2",
                "L10",
                f"the ship checklist cross-references {len(unresolved)} id(s) that resolve against "
                f"neither the podcast-challenger check catalog, the plan, nor any R-* rule "
                f"({listed})",
                checklist,
                min(unresolved.values()),
                fingerprint="L10:unresolved-cross-references",
            )

    # ---------- waivers ----------

    def apply_waivers(self, today: dt.date) -> None:
        """Suppress findings a human has ruled on, until the ruling expires.

        A waiver whose expiry cannot be read is treated as EXPIRED, never as
        permanent. `isinstance(expires, dt.date)` was False for a quoted YAML date
        and for a missing field alike, and both fell through to "do not expire" —
        so `expires: "2027-01-18"` suppressed its finding forever and silently. The
        whole point of the ledger is that a ruling is temporary; an entry that
        cannot expire is the one thing it must not be able to hold.
        """
        kept = []
        for f in self.findings:
            hit = None
            for w in self.waivers:
                if str(w.get("id")) != f.id or str(w.get("fingerprint")) != f.fingerprint:
                    continue
                hit = w
                break
            if not hit:
                kept.append(f)
                continue
            expires = _waiver_expiry(hit.get("expires"))
            if expires is None or expires < today:
                kept.append(
                    Finding(
                        f.severity,
                        f.id,
                        f"{f.summary} [previously waived on {hit.get('ruled_on')}, ruling has expired]",
                        f.file,
                        f.line,
                        f.fingerprint,
                    )
                )
                continue
            self.suppressed.append((f, hit))
        self.findings = kept


# ---------- the check registry ----------
#
# ONE list, three readers: `run()` executes it, tests/test_repo_surgeon_probe.py
# parametrizes over it, and the catalog gate asserts SKILL.md's "Checked by the
# script" table says exactly what it says.
#
# It exists because those three were separately maintained and agreed only by
# luck. `run()` used to build three hardcoded lambda lists while the sibling
# modules exported an `ALL_CHECKS` that nothing but their own tests read, so a
# check could be run and untested, or tested and unrun, or listed in the catalog
# and neither — the exact prose-rot this file's docstring was written about,
# reached by a different road.
#
# `fn` takes the probe as its only argument for BOTH kinds of check: a `Probe`
# method accessed on the class is a plain function whose first parameter is the
# instance, so `Probe.check_contract(probe)` and `surface.check_routes(probe)`
# have the same shape and need no wrapper.
#
# `emits` is the contract the coverage ratchet enforces: every id here must be
# produced by at least one test in the suite. Adding an id without a test that
# provokes it fails the suite. Removing a check's last emitter fails it too.
#
# `scopes` names the --scope values that select the check; every check runs
# under `all`. DECLARATION ORDER IS THE RUN ORDER, preserved exactly from the
# lists this replaced (findings are sorted before output, so order cannot change
# the report — it is kept identical so that claim needs no argument).


@dataclass(frozen=True)
class CheckSpec:
    name: str
    fn: object
    emits: tuple
    scopes: tuple = ()

    def __call__(self, probe: "Probe") -> None:
        self.fn(probe)


CHECKS: tuple = (
    # -- the contract's own accuracy, and this repo's structural invariants --
    CheckSpec("check_contract", Probe.check_contract, ("CT-PATH", "CT-RATCHET")),
    CheckSpec("check_verify_commands", Probe.check_verify_commands, ("CT-VERIFY",)),
    CheckSpec("check_mirror_pins", Probe.check_mirror_pins, ("MI-UNPINNED", "MI-PIN-GONE", "MI-PATH")),
    CheckSpec("check_root", Probe.check_root, ("R1",)),
    CheckSpec("check_retired_surfaces", Probe.check_retired_surfaces, ("RS-RESURRECT",)),
    CheckSpec("check_agent_mirrors", Probe.check_agent_mirrors, ("A2",)),
    CheckSpec("check_skill_registry", specs.check_skill_registry, ("A1",)),
    CheckSpec("check_project_skill_mirrors", specs.check_project_skill_mirrors, ("A3",)),
    CheckSpec("check_trigger_collisions", specs.check_trigger_collisions, ("A4",)),
    CheckSpec("check_self_references", Probe.check_self_references, ("SK-MISSING", "SK-DEADREF")),
    # -- the pipeline's own surface --
    CheckSpec("check_abs_paths", specs.check_abs_paths, ("AU-S2",), ("podcast",)),
    CheckSpec("check_version_constants", Probe.check_version_constants, ("AU-A2",), ("podcast",)),
    CheckSpec(
        "check_book_pipeline",
        Probe.check_book_pipeline,
        ("AU-V1", "AU-V2", "AU-V4", "AU-V5", "AU-V6"),
        ("podcast",),
    ),
    CheckSpec("check_book_identity", Probe.check_book_identity, ("AU-V7",), ("podcast",)),
    CheckSpec(
        "check_capabilities",
        surface.check_capabilities,
        ("CAP-PHASE", "CAP-AGENT-REF", "CAP-CMD-REF"),
        ("podcast",),
    ),
    # -- the two web surfaces --
    # CT-PATH is declared HERE and on no other surface check: it comes from the
    # shared `_apps` helper, so demanding a defect case from each of its four
    # callers would buy four copies of one proof.
    CheckSpec(
        "check_gate_coverage",
        surface.check_gate_coverage,
        ("GT-APP-UNVERIFIED", "GT-MISSING", "GT-UNGATED", "CT-PATH"),
        ("apps", "dashboard", "library"),
    ),
    CheckSpec(
        "check_routes",
        surface.check_routes,
        ("RT-POLICY-GONE", "RT-DANGLING", "RT-ORPHAN", "RT-BOUNDARY", "RT-PATH-GATE"),
        ("apps", "dashboard", "library"),
    ),
    CheckSpec("check_test_hygiene", surface.check_test_hygiene, ("TS-FOCUS",), ("apps", "dashboard", "library")),
    CheckSpec(
        "check_clean_code",
        surface.check_clean_code,
        ("CQ-NO-LINT", "CQ-NO-SIZE-GATE", "CQ-DEBUG"),
        ("apps", "dashboard", "library"),
    ),
    CheckSpec("check_gate_discovery", specs.check_gate_discovery, ("GT-UNDECLARED",), ("apps", "dashboard", "library")),
    CheckSpec(
        "check_data_contract",
        specs.check_data_contract,
        ("DB-MIGRATION-GAP", "DB-TABLE-MISSING", "CT-PATH"),
        ("apps", "dashboard", "library"),
    ),
    # -- repo-wide: a generator writes across app boundaries, and a standard
    #    binds an agent, a skill and a pipeline pass at once --
    CheckSpec("check_generated_artifacts", specs.check_generated_artifacts, ("GEN-UNPINNED", "CT-PATH")),
    CheckSpec("check_standards", specs.check_standards, ("SD-REQ-DANGLING", "SD-ORPHAN")),
    CheckSpec("check_plan", Probe.check_plan, ("L1", "L2", "L2-DUP", "L10")),
    # -- last, and reported only. Removal is scripts/repo_cleanup.py's job: a gate
    #    that deletes as a side effect of running is one people route around. --
    CheckSpec("check_debris", surface.check_debris, ("HY-DEBRIS",)),
)


def checks_for(scope: str) -> tuple:
    """The checks `--scope <scope>` selects, in declaration order."""
    if scope == "all":
        return CHECKS
    return tuple(c for c in CHECKS if scope in c.scopes)


def _cannot_run(message: str) -> None:
    """Exit 2 — "the probe could not run" — never 1, which means "defects found".

    Both the pre-commit hook and CI branch on the exit code alone. Letting a
    traceback exit 1 tells them a defect was found, which sends whoever reads the
    log looking for a finding that does not exist.
    """
    print(f"repo_surgeon_probe: {message}", file=sys.stderr)
    sys.exit(2)


def _load_yaml(path: Path, label: str) -> dict:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        _cannot_run(f"{label} does not parse: {exc}")
    except OSError as exc:
        _cannot_run(f"{label} could not be read: {exc}")
    return {}


def run(root: Path, scope: str) -> Probe:
    profile_path = root / ".repo-audit/profile.yaml"
    if not profile_path.exists():
        _cannot_run("no .repo-audit/profile.yaml — bootstrap the contract first (see the repo-audit skill, Phase 0.5)")
    profile = _load_yaml(profile_path, ".repo-audit/profile.yaml")
    waiver_path = root / ".repo-audit/waivers.yaml"
    waivers = []
    if waiver_path.exists():
        waivers = _load_yaml(waiver_path, ".repo-audit/waivers.yaml").get("waivers") or []

    probe = Probe(root=root, profile=profile, waivers=waivers, scope=scope)

    for check in checks_for(scope):
        check(probe)

    probe.apply_waivers(dt.date.today())
    probe.findings.sort(key=lambda f: f.sort_key())
    return probe


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true", help="emit findings as JSON")
    ap.add_argument(
        "--scope",
        choices=["all", "podcast", "apps", "dashboard", "library"],
        default="all",
        help="probe subset — dashboard/library audit one web surface, apps audits both",
    )
    args = ap.parse_args()

    top = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
        timeout=GIT_TIMEOUT,
    )
    if top.returncode != 0 or not top.stdout.strip():
        _cannot_run("not inside a git repository, so there is no repo to audit")
    root = Path(top.stdout.strip())
    probe = run(root, args.scope)
    blocking = [f for f in probe.findings if f.severity in ("P0", "P1")]

    if args.json:
        print(
            json.dumps(
                {
                    "findings": [f.__dict__ for f in probe.findings],
                    "suppressed": [
                        {"id": f.id, "reason": w.get("reason"), "ruled_on": str(w.get("ruled_on"))}
                        for f, w in probe.suppressed
                    ],
                    "counts": {s: sum(1 for f in probe.findings if f.severity == s) for s in SEVERITY_RANK},
                },
                indent=2,
                default=str,
            )
        )
        return 1 if blocking else 0

    if probe.findings:
        for f in probe.findings:
            where = f":{f.line}" if f.line else ""
            loc = f"  ({f.file}{where})" if f.file else ""
            print(f"{f.severity}  {f.id:<14} {f.summary}{loc}")
    else:
        print("repo-surgeon probe: clean — no findings.")

    counts = {s: sum(1 for f in probe.findings if f.severity == s) for s in SEVERITY_RANK}
    print("\n" + ", ".join(f"{n} {s}" for s, n in counts.items() if n) + (" findings" if any(counts.values()) else ""))
    # Both lines print even at zero: a silent zero and an absent line read the same.
    print(f"{len(probe.suppressed)} finding(s) suppressed by waiver")
    for f, w in probe.suppressed:
        print(f"    - {f.id}: {str(w.get('reason', '')).strip().splitlines()[0]} ({w.get('ruled_on')})")
    stale = sum(1 for f in probe.findings if f.id.startswith(("CT-", "MI-")))
    print(f"{stale} stale contract entry/entries")

    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
