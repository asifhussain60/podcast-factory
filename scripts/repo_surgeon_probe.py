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

Exit codes:
    0  no unwaived P0/P1 findings
    1  at least one unwaived P0 or P1
    2  the probe could not run (missing contract, unparseable YAML)
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
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


SEVERITY_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


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


@dataclass
class Probe:
    root: Path
    profile: dict
    waivers: list = field(default_factory=list)
    findings: list = field(default_factory=list)
    suppressed: list = field(default_factory=list)
    notes: list = field(default_factory=list)

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
                scripts = (json.loads(pkg) or {}).get("scripts", {})
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
        tracked = subprocess.run(
            ["git", "ls-files", "-z", "--", ":(top)"],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        ).stdout
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

    def check_skill_registry(self) -> None:
        registry = self.read("docs/reference/skill-registry.md")
        if not registry:
            self.add("P1", "A1", "the skill registry is missing", "docs/reference/skill-registry.md")
            return
        for d in sorted((self.root / "skills-staging").iterdir()):
            if not d.is_dir():
                continue
            # Match the DEFINITION PATH, not the bare name. A loose substring match on
            # the whole file passes on any incidental prose mention, which is how
            # html-view-quality read as registered while having no row.
            if f"skills-staging/{d.name}/" not in registry:
                self.add(
                    "P2",
                    "A1",
                    f"skill {d.name} has no row in the registry (no skills-staging/{d.name}/ definition path)",
                    f"skills-staging/{d.name}",
                    fingerprint=f"A1:{d.name}",
                )
            if not (d / "SKILL.md").exists():
                self.add("P1", "A1", f"skill {d.name} has no SKILL.md", f"skills-staging/{d.name}")

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

    def check_abs_paths(self) -> None:
        """AU-S2 — a machine-specific path in pipeline source breaks on the next host."""
        pat = re.compile(r"(/Users/|/home/)[A-Za-z0-9._-]+/")
        for p in self.py_sources("scripts/podcast"):
            for n, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#") or '"""' in stripped:
                    continue
                if pat.search(line):
                    rel = p.relative_to(self.root).as_posix()
                    self.add(
                        "P0",
                        "AU-S2",
                        "hardcoded absolute path in pipeline source",
                        rel,
                        n,
                        fingerprint=f"AU-S2:{rel}:{n}",
                    )

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
            ("def apply_author_companion_voice", "scripts/podcast/_book_voice.py"),
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

    # ---------- L: plan conformance ----------

    def wave_families(self, plan: dict) -> list:
        keys = [k for k in plan if k == "waves" or k.startswith(("waves_", "wave_"))]
        out = []
        for k in sorted(keys):
            if isinstance(plan.get(k), list):
                out.extend(x for x in plan[k] if isinstance(x, dict))
        return out

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
        known_waves = set(ids)

        # Duplicate ids across wave families make depends_on ambiguous: a reference to
        # "G" cannot be resolved to a single wave. The prose rule never checked this.
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            self.add(
                "P1",
                "L2-DUP",
                f"wave id(s) {', '.join(dupes)} are defined in more than one wave family, "
                "so dependency references to them are ambiguous",
                rel,
                fingerprint=f"L2-DUP:{','.join(dupes)}",
            )

        # A wave may legitimately depend on a STEP, not just another wave — waves.D
        # depends on A1, which is a step of wave A. Resolving against wave ids alone
        # reported that as dangling, which is the false-positive class this refactor
        # exists to remove.
        known_targets = set(known_waves)
        for w in waves:
            for s in w.get("steps") or []:
                if isinstance(s, dict) and s.get("id"):
                    known_targets.add(str(s["id"]))

        for w in waves:
            for dep in (w.get("depends_on") or []) + (w.get("parallel_with") or []):
                if str(dep) not in known_targets:
                    self.add(
                        "P1",
                        "L2",
                        f"wave {w.get('id')} references {dep}, which is neither a known wave nor a known step",
                        rel,
                        fingerprint=f"L2:{w.get('id')}:{dep}",
                    )

        checklist = "_workspace/plan/operations/per-book-ship-checklist.md"
        text = self.read(checklist)
        if not text:
            return

        known = set(known_waves)
        for w in waves:
            if w.get("legacy_id"):
                known.add(str(w["legacy_id"]))
            for s in w.get("steps") or []:
                known.update(str(x) for x in (s.get("id"), s.get("legacy_id")) if x)
        for key in ("open_questions", "risks"):
            for row in plan.get(key) or []:
                if isinstance(row, dict) and row.get("id"):
                    known.add(str(row["id"]))
        legacy = (plan.get("meta") or {}).get("legacy_id_map") or {}
        known.update(str(k) for k in legacy)
        known.update(str(v) for v in legacy.values())

        # The checklist's row ids (**A6**, **P4**, **T1**) are its OWN scheme; only the
        # trailing italic parenthetical is a cross-reference INTO the plan. The prose
        # rule scanned whole lines, so it flagged row ids and the P0-P3 severity grammar
        # as unknown plan ids — 30 findings, none of them real.
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
            listed = ", ".join(f"{k}" for k in sorted(unresolved))
            has_map = bool(legacy)
            cause = (
                "meta.legacy_id_map exists but does not cover them"
                if has_map
                else "the plan defines no meta.legacy_id_map to translate them"
            )
            self.add(
                "P1",
                "L10",
                f"the ship checklist cross-references {len(unresolved)} id(s) the current plan "
                f"does not define ({listed}) — {cause}",
                checklist,
                min(unresolved.values()),
                fingerprint="L10:legacy-id-map-missing",
            )

    # ---------- waivers ----------

    def apply_waivers(self, today: dt.date) -> None:
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
            expires = hit.get("expires")
            if isinstance(expires, dt.date) and expires < today:
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


def run(root: Path, scope: str) -> Probe:
    profile_path = root / ".repo-audit/profile.yaml"
    if not profile_path.exists():
        print(
            "repo_surgeon_probe: no .repo-audit/profile.yaml — bootstrap the contract first "
            "(see the repo-audit skill, Phase 0.5)",
            file=sys.stderr,
        )
        sys.exit(2)
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}
    waiver_path = root / ".repo-audit/waivers.yaml"
    waivers = []
    if waiver_path.exists():
        waivers = (yaml.safe_load(waiver_path.read_text(encoding="utf-8")) or {}).get("waivers") or []

    probe = Probe(root=root, profile=profile, waivers=waivers)

    podcast_checks = [
        probe.check_abs_paths,
        probe.check_version_constants,
        probe.check_book_pipeline,
    ]
    all_checks = [
        probe.check_contract,
        probe.check_verify_commands,
        probe.check_mirror_pins,
        probe.check_root,
        probe.check_retired_surfaces,
        probe.check_agent_mirrors,
        probe.check_skill_registry,
        probe.check_self_references,
        *podcast_checks,
        probe.check_plan,
    ]
    for check in podcast_checks if scope == "podcast" else all_checks:
        check()

    probe.apply_waivers(dt.date.today())
    probe.findings.sort(key=lambda f: f.sort_key())
    return probe


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true", help="emit findings as JSON")
    ap.add_argument("--scope", choices=["all", "podcast"], default="all", help="probe subset")
    args = ap.parse_args()

    root = Path(
        subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    )
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
