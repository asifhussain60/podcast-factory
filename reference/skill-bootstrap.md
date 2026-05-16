# Skill Bootstrap Contract

**Status:** ACTIVE — every CORTEX-Challenger-Framework v1.0 skill in this repo cites this file at SECTION 0.
**Authority:** Operationalizes `reference/cortex-challenger-framework.md` v1.0 for in-repo skills. Where this contract and the framework conflict, the framework wins; this file only fills in the operational details the framework left open.
**Last updated:** 2026-05-16

This document is the single shared "SECTION 0" contract that every skill in `skills-staging/` and every overlay-managed plugin skill points to. It tells the skill — and the agent reading the skill — exactly how to boot, how to score severity, how to keep output deterministic, and where to write the run report.

If a skill needs to deviate from any clause here, the deviation is named explicitly inside that skill's `cortex-compliance.md` (or playbooks/00-cortex-compliance.md for podcast) with a one-sentence justification.

---

## 1. Boot order — read before any action

Every skill, on invocation, reads in this exact order:

1. `reference/cortex-challenger-framework.md` — the framework (severity taxonomy, primitives, schema).
2. `reference/skill-bootstrap.md` — this file.
3. The skill's own compliance doc:
   - In-repo staging skills: `skills-staging/<skill>/cortex-compliance.md`.
   - Podcast (large skill with playbooks): `skills-staging/podcast/playbooks/00-cortex-compliance.md`.
   - Plugin skills with overlays: `reference/skill-overlays/<skill>-cortex-overlay.md`.
4. The skill's own `SKILL.md` body.
5. Any per-skill reference files the SKILL.md names explicitly.

A skill MUST NOT begin its primary action until steps 1–4 have been completed in order. If any of those files is missing or unreadable, the skill halts with a DoR-INCOMPLETE message naming the missing file.

This boot order is itself a P0 gate. Skipping it ships output that may violate framework primitives the skill is unaware of.

---

## 2. Severity taxonomy — universal P0–P3

Every gate, check, finding, or rule in any skill is tagged with exactly one of:

| Tier | Semantics | Action on detection |
|---|---|---|
| **P0** | Critical / immutable — output is wrong or unsafe | HALT. No waiver. No proceed. |
| **P1** | High / required — output is materially wrong but recoverable | HALT current operation. Allow re-run after fix. |
| **P2** | Medium / recommended — quality loss, not correctness loss | Report with remediation. May proceed with explicit waiver. |
| **P3** | Low / advisory — preference / style | Report informationally. Never blocks. |

Legacy labels (Blocker / Warning / Critical / High / Medium / Low / MAJOR / MINOR / BLOCKER / NIT / etc.) are deprecated. Every SKILL.md and every agent .md in this repo maps its legacy labels onto P0–P3 explicitly. If you see a legacy label still in active prose, treat it as a documentation bug and fix it.

Mapping rule (from framework §1):
1. Does the violation make output *wrong*? → P0.
2. Does it make output *materially worse* but recoverable? → P1.
3. Does it reduce *quality* but not *correctness*? → P2.
4. Is it a *preference*? → P3.

When in doubt, escalate one tier (P2 → P1).

---

## 3. The six primitives — minimum every skill implements

Every CORTEX-Challenger-compliant skill implements these primitives (the framework defines them; this section names the in-repo conventions):

| # | Primitive | In-repo convention |
|---|---|---|
| 1 | **Definition of Ready Gate** (REQUIRED) | Pass criterion = 100% for code/content-modifying ops, 80% for read-only ops. On failure: write `_workspace/<skill>-dor-incomplete-<run_id>.md` and halt. |
| 2 | **Convergence Gate** (REQUIRED for stateful skills) | Max 3 cycles. On exceed: write `_workspace/<skill>-convergence-failed-<run_id>.md` and halt. Read-only skills declare exemption. |
| 3 | **Sweep Completeness Contract** (REQUIRED for multi-target ops) | All-or-none across the named target set. On partial-failure: apply to none, name the blocker. |
| 4 | **Holistic Validation Gate** (REQUIRED for code/content-modifying skills) | Five-check at end of run: registry, dependency drift, regression risk, governance, challenge gate. Pass = composite risk ≤ 0.6. |
| 5 | **Challenge Gate** (REQUIRED when scope/risk crosses thresholds) | Triggers when scope > 3 files OR decision affects external contracts OR security/privacy implications OR irreversible. On trigger: ≥ 2 alternatives surfaced before commit. |
| 6 | **Determinism Contract** (REQUIRED) | See §4 below — this contract is what makes runs reproducible. |

---

## 4. Determinism Contract — non-negotiable defaults

Every deterministic stage of every skill MUST satisfy the following clauses. Any stage that cannot satisfy them MUST be explicitly named as non-deterministic in the skill's compliance doc with a one-sentence reason.

### 4.1 Findings sort order

Findings within a gate report are sorted (ascending) by:

1. `severity` (P0 → P1 → P2 → P3 — i.e., P0 first because it blocks)
2. `location.file` (lexicographic, POSIX path)
3. `location.line` (numeric)
4. `gate_id` (lexicographic)
5. `id` (the per-finding F-NN suffix, numeric)

This is the universal tiebreaker chain. No skill invents its own ordering.

### 4.2 Run identifiers

- `run_id` = SHA-256 hex digest of (`skill_name || "\0" || ISO-8601 UTC timestamp || "\0" || input_hash`), truncated to first 16 hex chars.
- `input_hash` = SHA-256 hex of the canonical (newline-normalized, BOM-stripped, trailing-whitespace-trimmed) input bytes. For multi-file inputs: sort filenames lexicographically, concat with NUL separators, hash the concatenation.
- `timestamp` = ISO-8601 UTC with millisecond precision, e.g. `2026-05-16T18:42:11.123Z`. UTC always — never local time.

These are the only allowed non-deterministic fields in the run summary. Everything else must be reproducible from the input.

### 4.3 Tiebreakers for ambiguous mappings

When two or more transformation rules match the same input (e.g., a hex value that could map to `--bg` or `--contrast-dark` depending on CSS property context), the skill MUST:

1. Define the disambiguator explicitly in its SKILL.md.
2. Apply the disambiguator in a single deterministic pass — no second-guessing.
3. If the disambiguator can't decide, downgrade the finding to `[JUDGE]` / P2 and surface for operator review. **Never pick at random. Never apply both.**

### 4.4 Locale and clock

- All numeric formatting: `en-US` decimal point, no thousands separators in machine output, optional `en-US` thousands in human-readable text output.
- All date strings in machine output: ISO-8601 UTC.
- All date strings in human-readable output (skill chooses): `en-US` with `America/New_York` timezone, named timezone in the string.
- Clock source: `Date.now()` (Node) / `time.time()` (Python) at the start of the run, captured once, used for all run-level timestamps.

### 4.5 Hash-stable identifiers

- Slugs for outputs: `kebab-case(lowercase(strip-non-alphanumeric(title)))` with hyphens collapsing runs of separators. Length capped at 64 chars at a word boundary.
- Stage / pass / phase IDs: zero-padded to 2 digits where the count is < 100 (`Stage 01`, `Pass 02`, `Phase 03`).
- File IDs in reports: relative POSIX paths from the repo root. Never absolute.

### 4.6 Random sources forbidden

No `Math.random()`, `random.choice()`, `uuid.uuid4()` etc. in any deterministic stage. If randomness is genuinely needed (it almost never is), it MUST be seeded from `input_hash` and the use named in the compliance doc.

---

## 5. Run summary — every skill writes one

After every run (success, failure, or halt), the skill writes a run summary to:

- `WORK_DIR/_challenger-report.yml` for skills that operate in a work directory (podcast, repo-surgeon multi-pass runs).
- `_workspace/challenger-reports/<skill>-<run_id>.yml` for in-place skills (journal, css-theme-sync, ui-modernizer, usage-auditor, ui-reviewer agent).

The summary follows the framework §3 schema exactly. The schema is canonical — no deviation.

If `_workspace/challenger-reports/` does not exist, the skill creates it on first write (no halt).

---

## 6. Output discipline

- **No prose dumps into chat.** Skills that produce text-based output (memoir, podcast scripts, reports) write to a file and surface a `computer://` link.
- **No intermediate scratch files in chat-visible scope.** Working state lives under `WORK_DIR` (per-skill) or `_workspace/` (general). Never at repo root.
- **One canonical output per artifact.** No `output-v2.txt`, `output-final.txt`, `output-FINAL2.txt`. Git is the version control; the canonical filename never carries version suffixes.

---

## 7. Cross-skill coordination

When multiple skills touch the same file, the framework §7 ownership table governs writes (canonical at `reference/skill-registry.md`). A skill writing to a file it does not own MUST:

1. Write to a staging file under its own WORK_DIR (e.g., `WORK_DIR/06-library-proposals.md`).
2. Surface an explicit apply step (`/<skill> apply <slug>`) that the user invokes.
3. The owning skill's apply step verifies the target has no uncommitted changes and applies atomically.

Cross-skill writes that bypass the staging+apply contract are a P0 governance violation.

---

## 8. How a new skill onboards to this contract

1. Author `SKILL.md` with frontmatter that includes `compliance-tier:` and `framework-version: 1.0`.
2. Author `cortex-compliance.md` (in-skill) or `reference/skill-overlays/<skill>-cortex-overlay.md` (overlay for plugin skill).
3. Cite this file (`reference/skill-bootstrap.md`) at the top of SECTION 0 of SKILL.md.
4. Map every severity label in the skill body to P0–P3 explicitly.
5. Declare which stages are deterministic and which are not (with reasons) per §4.
6. Add the skill to `reference/skill-registry.md` with target tier and overlay path.
7. Wire `_workspace/challenger-reports/<skill>-<run_id>.yml` output at end of run.

A skill is bootstrap-compliant when steps 1–7 are satisfied. The skill's tier in `skill-registry.md` reflects framework-compliance level; bootstrap-compliance is the floor for being listed at all.

---

## 9. Versioning

This document targets **CORTEX Challenger Framework v1.0**. When the framework moves to v1.1 (additive), this file is updated to match additive primitives. When the framework moves to v2.0 (breaking), every skill's compliance doc must be reviewed and this file rewritten.

Skills cite the framework version they target, not this file's version directly.
