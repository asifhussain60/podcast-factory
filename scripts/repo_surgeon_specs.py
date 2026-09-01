#!/usr/bin/env python3
"""Spec probes for repo-surgeon: the invariants this repo's NEWEST work created.

Third module of the probe, added 2026-08-16 for the same reason the second one was
split out of the first — a catalog nobody can hold in one reading is a catalog that
rots. `repo_surgeon_probe.py` owns the contract and the repo's shape;
`repo_surgeon_checks.py` owns what is true of a particular surface; this file owns
the invariants that arrived with specs written in the last few weeks and had, until
now, nothing watching them.

Each group below exists because a real thing was built and left unguarded:

  GT-UNDECLARED   The gate-coverage check audits gates the CONTRACT declares. So a
                  gate built after the contract was last edited is invisible to it
                  by construction — the check cannot report what it was never told
                  about. `verify:read-aloud` (a browser gate over every chapter of
                  every published book) lived exactly there for a day.

  DB-*            Six migrations landed in two weeks — narration, study tracks,
                  source references — each with a Python writer on the other side of
                  the wire. A write to a table no migration creates does not fail in
                  a test; it fails at DEPLOY, against the live database, after the
                  content is already prepared. And two branches both numbering a
                  migration 0019 produce one migration that simply never runs.

  GEN-UNPINNED    Three generators appeared in two weeks that write a COMMITTED
                  artifact out of another file in the repo. Two are pinned by a test
                  that runs the generator's own `--check`; the third is not, and its
                  output can drift from its source with nothing to say so. A
                  generated artifact is a mirror pair whose second leg is produced
                  mechanically — same drift, same cost, no watcher.

  SD-*            Two standards carrying 48 REQ ids between them arrived recently,
                  and the house rule for all of them is "cite by ID, never restate".
                  That rule has exactly one failure mode — a citation whose ID no
                  standard defines — and it is silent: the reader follows a rule
                  number to nothing and supplies their own idea of what it said.

Nothing here restates a project fact. The apps, their migrations, their SQL writers
and the generator list all come from `.repo-audit/profile.yaml`, and a field that
stops resolving is a finding against the contract rather than a silent skip.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from repo_surgeon_checks import GATE_SCRIPTS, LOCAL_ONLY_GATES, _apps

# A script whose name ENDS this way is a fixer, not a gate: it exists to change the
# tree, and demanding it be wired into CI would be demanding CI rewrite the repo.
FIXER_SUFFIXES = (":fix", ":update", ":write")


def _mentions(probe, needles: list[str]) -> dict[str, list[str]]:
    """For each needle, the tracked files whose text contains it.

    ONE `git grep` for the whole set rather than one per needle. This probe runs in
    a pre-commit hook and `content/` is both tracked and large, so a per-needle
    search costs a second each and a gate slow enough to be felt is a gate people
    learn to pass with `--no-verify`.
    """
    found: dict[str, list[str]] = {n: [] for n in needles}
    if not needles:
        return found
    args = ["git", "grep", "-F", "-h", "-I", "-n", "--name-only"]
    for n in needles:
        args += ["-e", n]
    # --name-only collapses to paths, which loses WHICH needle matched, so the
    # second pass re-reads only the files that matched anything at all — a handful,
    # not the repo.
    hits = subprocess.run(args, cwd=probe.root, capture_output=True, text=True, check=False).stdout
    for rel in sorted(set(filter(None, hits.splitlines()))):
        text = probe.read(rel)
        for n in needles:
            if n in text:
                found[n].append(rel)
    return found


def _tracked(probe, *, suffixes: tuple[str, ...] = (), under: str = "") -> list[str]:
    """Tracked paths, because every gate in this repo sees the index and not the disk."""
    out = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=probe.root,
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    rels = []
    for rel in filter(None, out.split("\0")):
        if under and not (rel == under or rel.startswith(f"{under}/")):
            continue
        if suffixes and not rel.endswith(suffixes):
            continue
        rels.append(rel)
    return sorted(rels)


# ---------- GT-UNDECLARED: a gate the contract has never heard of ----------


def check_gate_discovery(probe) -> None:
    """GT-UNDECLARED — the gate nobody declared.

    `check_gate_coverage` asks, of every gate the contract names, whether anything
    obliges someone to run it. This asks the question one level up: is there a gate
    the contract does not name at all? Those two are not the same check and the
    first cannot become the second, because a list can only be audited against
    itself.

    The vocabulary is deliberately narrow — the exact gate names, plus anything
    spelled `verify:*`, which is this repo's word for "prove a claim about the built
    thing". A wider net (every `lint:*`, say) would sweep in `lint:fix`, which is a
    fixer, and a rule that manufactures findings is a rule people learn to skip.

    An AGGREGATE is not a finding. `npm run check` that runs six declared gates in
    a row is a convenience alias; demanding it be declared and wired would double
    every constituent and teach nothing.
    """
    for app in _apps(probe):
        d = str(app["dir"])
        name = str(app.get("name") or d)
        declared = {str(g) for g in (app.get("gates") or [])}

        raw = probe.read(f"{d}/package.json")
        try:
            scripts = dict((json.loads(raw) if raw else {}).get("scripts") or {})
        except json.JSONDecodeError:
            continue

        for script, body in sorted(scripts.items()):
            if script in declared or script.endswith(FIXER_SUFFIXES):
                continue
            if not (script in GATE_SCRIPTS or script.startswith("verify:")):
                continue
            # An alias: every command in the body is `npm run <already-declared>`.
            parts = [c.strip() for c in re.split(r"&&|;", str(body)) if c.strip()]
            if parts and all(re.fullmatch(r"npm run ([\w:.-]+)", p) and p.split()[-1] in declared for p in parts):
                continue

            local_only = script in LOCAL_ONLY_GATES or script.startswith("verify:")
            probe.add(
                "P1",
                "GT-UNDECLARED",
                f"{name}: `npm run {script}` is gate-shaped but the contract's gates list for this app "
                "never names it — so the gate-coverage check cannot ask whether anything runs it, and "
                "nothing does" + (" (browser gate: the verify list is its home)" if local_only else ""),
                f"{d}/package.json",
                fingerprint=f"GT-UNDECLARED:{d}:{script}",
            )


# ---------- DB: the database contract between the pipeline and the app ----------

_WRITES = (
    re.compile(r"\bINSERT\s+(?:OR\s+\w+\s+)?INTO\s+[\"'`\[]?([a-z_][a-z0-9_]*)", re.I),
    re.compile(r"\bUPDATE\s+[\"'`\[]?([a-z_][a-z0-9_]*)[\"'`\]]?\s+SET\b", re.I),
    re.compile(r"\bDELETE\s+FROM\s+[\"'`\[]?([a-z_][a-z0-9_]*)", re.I),
)
_CREATES = re.compile(r"\bCREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[\"'`\[]?([a-z_][a-z0-9_]*)", re.I)
_MIGRATION_NAME = re.compile(r"^(\d+)[_-]")


def check_data_contract(probe) -> None:
    """DB-* — every table something writes is a table some migration creates.

    The type checker cannot see this: the statement is a string, the schema is a
    directory of SQL, and the two are joined only at deploy time against the live
    database. `publish_to_listener.py` is the ONLY writer of six of these tables and
    it runs unattended at the end of every publish.

    DB-MIGRATION-GAP is the other half. Migrations are applied in name order, once
    each, and the runner records what it has already done — so two branches that
    both reach for the next free number produce a pair where one is applied and the
    other is skipped forever on any database that saw the first. Numbering is the
    only place that collision is visible, and it is visible immediately.
    """
    for app in _apps(probe):
        d = str(app["dir"])
        name = str(app.get("name") or d)
        mig_rel = str(app.get("migrations") or "")
        if not mig_rel:
            continue

        mig_dir = probe.root / d / mig_rel
        if not mig_dir.is_dir():
            probe.add(
                "P1",
                "CT-PATH",
                f"contract declares migrations for {name} at {d}/{mig_rel}, which is not a directory",
                ".repo-audit/profile.yaml",
                fingerprint=f"CT-PATH:migrations:{d}",
            )
            continue

        created: set[str] = set()
        seen: dict[str, str] = {}
        for sql in sorted(mig_dir.glob("*.sql")):
            text = sql.read_text(encoding="utf-8", errors="replace")
            created |= {t.lower() for t in _CREATES.findall(text)}
            m = _MIGRATION_NAME.match(sql.name)
            if not m:
                probe.add(
                    "P1",
                    "DB-MIGRATION-GAP",
                    f"{name}: migration {sql.name} is not numbered — migrations are applied in name order, "
                    "so an unnumbered one has no defined position",
                    f"{d}/{mig_rel}/{sql.name}",
                    fingerprint=f"DB-MIGRATION-GAP:{d}:{sql.name}",
                )
                continue
            num = m.group(1)
            if num in seen:
                probe.add(
                    "P0",
                    "DB-MIGRATION-GAP",
                    f"{name}: migrations {seen[num]} and {sql.name} share the number {num} — the runner "
                    "records applied migrations by name, so on any database that saw the first, the "
                    "second never runs and never will",
                    f"{d}/{mig_rel}/{sql.name}",
                    fingerprint=f"DB-MIGRATION-GAP:{d}:dup:{num}",
                )
            seen[num] = sql.name

        numbers = sorted(int(n) for n in seen)
        for prev, nxt in zip(numbers, numbers[1:]):
            if nxt - prev > 1:
                probe.add(
                    "P2",
                    "DB-MIGRATION-GAP",
                    f"{name}: migration numbering jumps {prev:04d} -> {nxt:04d}. Not fatal on its own, but "
                    "the usual cause is a migration that was written, applied somewhere, and then deleted",
                    f"{d}/{mig_rel}",
                    fingerprint=f"DB-MIGRATION-GAP:{d}:gap:{prev}",
                )

        # Writers. Declared rather than sniffed: this repo also carries SQLite
        # corpora of its own (the mushaf mirror, the morphology database), and a
        # statement gives no clue which database it is aimed at.
        for writer in app.get("sql_writers") or []:
            writer = str(writer)
            target = probe.root / writer
            if not target.exists():
                probe.add(
                    "P1",
                    "CT-PATH",
                    f"contract names {writer} as a SQL writer for {name}; it does not exist",
                    ".repo-audit/profile.yaml",
                    fingerprint=f"CT-PATH:sql_writers:{writer}",
                )
                continue
            files = (
                _tracked(probe, suffixes=(".py", ".ts", ".tsx", ".mjs"), under=writer) if target.is_dir() else [writer]
            )
            for rel in files:
                text = probe.read(rel)
                for pattern in _WRITES:
                    for m in pattern.finditer(text):
                        table = m.group(1).lower()
                        if table in created:
                            continue
                        line = text.count("\n", 0, m.start()) + 1
                        probe.add(
                            "P0",
                            "DB-TABLE-MISSING",
                            f"{rel} writes to `{table}`, which no migration under {d}/{mig_rel}/ creates. "
                            "This does not fail in a test — it fails at deploy, against the live database, "
                            "after the content has already been prepared",
                            rel,
                            line,
                            fingerprint=f"DB-TABLE-MISSING:{rel}:{table}",
                        )


# ---------- GEN: generated artifacts ----------


def check_generated_artifacts(probe) -> None:
    """GEN-UNPINNED — a generated artifact nothing proves is current.

    The contract lists generators, not verdicts. Whether one is pinned is DERIVED
    here, by asking whether any tracked test or gate actually invokes its `--check`.
    That distinction matters: a "pinned: true" field in a contract is a claim
    somebody typed, and the whole point of this file is that a claim nobody can
    fail is not evidence.

    Only generators that OFFER a self-check are judged. A generator without one has
    no cheap proof available, which is a different (and larger) conversation than
    this probe should start on its own.
    """
    generators = [str(g) for g in (probe.profile.get("generators") or [])]
    if not generators:
        return

    live = []
    for gen in generators:
        if not probe.exists(gen):
            probe.add(
                "P1",
                "CT-PATH",
                f"contract lists generator {gen}, which does not exist",
                ".repo-audit/profile.yaml",
                fingerprint=f"CT-PATH:generators:{gen}",
            )
            continue
        if "--check" in probe.read(gen):
            live.append(gen)  # offers a self-check; anything else has none to demand

    mentions = _mentions(probe, [Path(g).name for g in live])
    for gen in live:
        base = Path(gen).name
        # The generator's OWN file is excluded. Every one of these documents
        # `--check` in a usage comment at the top, so a corpus containing the
        # generator answers "is this pinned?" with "it says so itself" — which is
        # how the one genuinely unpinned generator here passed the first draft.
        invoked = any(
            rel != gen and re.search(rf"{re.escape(base)}[\"',\s\]]*[^\n]{{0,40}}--check", probe.read(rel))
            for rel in mentions[base]
        )
        if not invoked:
            probe.add(
                "P1",
                "GEN-UNPINNED",
                f"{gen} writes a committed artifact and offers `--check`, but nothing tracked ever runs it "
                "with that flag — the generated output can drift from its source and no gate will say so",
                gen,
                fingerprint=f"GEN-UNPINNED:{gen}",
            )


# ---------- SD: the standards, and the citations that point at them ----------

_REQ = re.compile(r"\bREQ-[A-Z]{1,4}-\d{1,4}\b")


def check_standards(probe) -> None:
    """SD-* — a rule cited by number resolves to a rule.

    Every challenger spec in this repo is under orders to cite standards by ID and
    never restate them, precisely so a rule has one wording. That contract fails
    silently in one direction: a citation whose ID no standard defines sends the
    reader to nothing and they supply their own idea of what it said — which is the
    restatement the rule exists to prevent, arrived at by a longer road.

    SD-ORPHAN is the opposite end: a standard no agent, skill or normative document
    cites is a document with no way to bind anything.
    """
    std_dir = probe.root / "docs/standards"
    if not std_dir.is_dir():
        return
    standards = sorted(p for p in std_dir.glob("*.md"))

    defined: set[str] = set()
    for p in standards:
        defined |= set(_REQ.findall(p.read_text(encoding="utf-8", errors="replace")))

    # Two different questions, so two different corpora.
    #
    # A DANGLING citation is judged only where rules are written — an agent spec, a
    # skill, a normative document. A REQ id quoted in an old assessment or a session
    # log is a record of what was true then, and re-litigating history produces
    # findings nobody can act on.
    citers = _tracked(probe, suffixes=(".md",), under="infra/claude-agents")
    citers += _tracked(probe, suffixes=(".md",), under="skills-staging")
    citers += [r for r in ("CLAUDE.md", "framework.md", "README.md") if probe.exists(r)]

    for rel in citers:
        text = probe.read(rel)
        for n, line in enumerate(text.splitlines(), 1):
            for req in _REQ.findall(line):
                if req in defined:
                    continue
                probe.add(
                    "P1",
                    "SD-REQ-DANGLING",
                    f"{rel} cites {req}, which no standard under docs/standards/ defines — the citation "
                    "resolves to nothing and the reader supplies their own version of the rule",
                    rel,
                    n,
                    fingerprint=f"SD-REQ-DANGLING:{rel}:{req}",
                )

    # An ORPHAN is judged against everything tracked, because a standard binds by
    # being READ, and several here are read by the pipeline rather than cited in
    # prose: house-voice.md reaches a book through `_rules.py`, and a series-setup
    # standard through a book's own config. A check that looked only at markdown
    # would have called both orphaned while they were shaping every page of every
    # edition. `git grep` again, for the pre-commit reason above.
    mentions = _mentions(probe, [p.name for p in standards])
    for p in standards:
        rel = p.relative_to(probe.root).as_posix()
        # A standard citing itself, or its sibling, is not a binding.
        if any(h for h in mentions[p.name] if not h.startswith("docs/standards/")):
            continue
        probe.add(
            "P2",
            "SD-ORPHAN",
            f"{rel} is cited by no agent spec, skill or normative document — a standard nothing points at "
            "cannot bind anything, and reads as current long after it stops being so",
            rel,
            fingerprint=f"SD-ORPHAN:{rel}",
        )


def check_abs_paths(probe) -> None:
    """AU-S2 — moved here 2026-08-31 for DR-005 headroom, unchanged otherwise. A
    machine-specific path in pipeline source breaks on the next host."""
    pat = re.compile(r"(/Users/|/home/)[A-Za-z0-9._-]+/")
    for p in probe.py_sources("scripts/podcast"):
        for n, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#") or '"""' in stripped:
                continue
            if pat.search(line):
                rel = p.relative_to(probe.root).as_posix()
                probe.add(
                    "P0",
                    "AU-S2",
                    "hardcoded absolute path in pipeline source",
                    rel,
                    n,
                    fingerprint=f"AU-S2:{rel}:{n}",
                )


def check_skill_registry(probe) -> None:
    """A1 — moved here 2026-08-31 alongside A3 (project-skill mirrors), its
    natural sibling: both audit the skill registry's completeness, and
    repo_surgeon_probe.py was at its own DR-005 ceiling with nowhere to grow."""
    registry = probe.read("docs/reference/skill-registry.md")
    if not registry:
        probe.add("P1", "A1", "the skill registry is missing", "docs/reference/skill-registry.md")
        return
    staging = probe.root / "skills-staging"
    if not staging.is_dir():
        # A fresh clone that has not run the skill installer has no
        # skills-staging/, so this crashed on the very tree it was most likely
        # to meet. The registry's absence was already a finding; the
        # directory's absence was a traceback.
        probe.add("P1", "A1", "skills-staging/ does not exist, so no skill can be registered", "skills-staging")
        return
    for d in sorted(staging.iterdir()):
        if not d.is_dir():
            continue
        # Match the DEFINITION PATH, not the bare name. A loose substring match on
        # the whole file passes on any incidental prose mention, which is how
        # html-view-quality read as registered while having no row.
        if f"skills-staging/{d.name}/" not in registry:
            probe.add(
                "P2",
                "A1",
                f"skill {d.name} has no row in the registry (no skills-staging/{d.name}/ definition path)",
                f"skills-staging/{d.name}",
                fingerprint=f"A1:{d.name}",
            )
        if not (d / "SKILL.md").exists():
            probe.add("P1", "A1", f"skill {d.name} has no SKILL.md", f"skills-staging/{d.name}")


def check_project_skill_mirrors(probe) -> None:
    """A3 — the skills-staging <-> .claude/skills pair, for the subset of skills
    Claude Code reads directly (project_skills: in the contract), same shape as
    repo_surgeon_probe.Probe.check_agent_mirrors. Two project skills existed only
    under the gitignored .claude/skills/ with no tracked source anywhere until this
    check existed — invisible to git, the registry, and every prior repo-surgeon
    run, on a repo whose own model is machine-agnostic."""
    # `or []`, not a bare `.get(...)`: a repo that never adopted this contract key
    # has nothing to check, but a repo that declared it as an EMPTY list still has
    # a runtime directory worth checking for orphans below.
    declared = [str(n) for n in (probe.profile.get("project_skills") or [])]
    staging = probe.root / "skills-staging"
    runtime = probe.root / ".claude" / "skills"
    for name in declared:
        canonical = staging / name / "SKILL.md"
        if not canonical.exists():
            probe.add(
                "P1",
                "A3",
                f"project skill {name!r} is declared in project_skills but has no canonical "
                f"source at skills-staging/{name}/SKILL.md",
                f"skills-staging/{name}",
                fingerprint=f"A3:no-canonical:{name}",
            )
            continue
        # Absent .claude/skills/ entirely means a fresh clone or CI that never ran
        # the sync — not a defect the tree can fix, same guard
        # sync-skill-wrappers.sh itself applies to its own check mode.
        if not runtime.is_dir():
            continue
        if not (runtime / name / "SKILL.md").exists():
            probe.add(
                "P1",
                "A3",
                f"project skill {name!r} has no generated runtime mirror — run scripts/podcast/sync-skill-wrappers.sh",
                f".claude/skills/{name}",
                fingerprint=f"A3:no-runtime:{name}",
            )
    if runtime.is_dir():
        declared_set = set(declared)
        for d in sorted(runtime.iterdir()):
            if not d.is_dir() or d.name in declared_set:
                continue
            probe.add(
                "P1",
                "A3",
                f".claude/skills/{d.name} has no entry in project_skills — either add it to the "
                "contract or remove the directory (it has no tracked source)",
                f".claude/skills/{d.name}",
                fingerprint=f"A3:orphan:{d.name}",
            )


_TRIGGER_TOKEN_RE = re.compile(r"'([A-Za-z][A-Za-z-]*)'")
_FRONTMATTER_DESC_RE = re.compile(r'^description:\s*"(.*)"\s*$', re.MULTILINE | re.DOTALL)


def check_trigger_collisions(probe) -> None:
    """A4 — a bare single-word quoted trigger ('challenge') shared by two specs is
    how a new skill silently hijacks an existing agent's invocation, or vice versa.
    Multi-word trigger phrases ('challenge this', 'challenge <slug>') are the
    normal, safe case and are never flagged — this only catches the exact shape
    that would have collided before challenge-my-request's own trigger list was
    deliberately narrowed to self-referential phrasing."""
    spec_texts: dict[str, str] = {}
    for base, glob, exclude in (
        ("infra/claude-agents", "*.md", "_README.md"),
        ("skills-staging", "*/SKILL.md", None),
        (".claude/skills", "*/SKILL.md", None),
    ):
        for p in sorted((probe.root / base).glob(glob)):
            if exclude and p.name == exclude:
                continue
            try:
                spec_texts[str(p.relative_to(probe.root))] = p.read_text(encoding="utf-8")
            except OSError:
                continue
    tokens: dict[str, set[str]] = {}
    for rel, text in spec_texts.items():
        m = _FRONTMATTER_DESC_RE.search(text[:6000])
        if not m:
            continue
        for word in _TRIGGER_TOKEN_RE.findall(m.group(1)):
            tokens.setdefault(word.lower(), set()).add(rel)
    for word, files in sorted(tokens.items()):
        if len(files) < 2:
            continue
        probe.add(
            "P2",
            "A4",
            f"bare-word trigger '{word}' is a quoted invocation phrase in {len(files)} specs "
            f"({', '.join(sorted(files))}) — confirm each excludes the others' targets, or widen "
            "the trigger to a multi-word phrase",
            sorted(files)[0],
            fingerprint=f"A4:{word}",
        )


ALL_CHECKS = (
    check_gate_discovery,
    check_data_contract,
    check_generated_artifacts,
    check_standards,
    check_abs_paths,
    check_skill_registry,
    check_project_skill_mirrors,
    check_trigger_collisions,
)
