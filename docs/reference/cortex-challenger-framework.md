# CORTEX Challenger Framework

**Canonical reference for skill enforcement consistency across the journal/Cowork ecosystem.**

Date: 2026-05-16
Status: ACTIVE — all skills shall converge on this framework
Authority: This document defines the *minimum enforcement contract* every skill must satisfy. It does not replace CORTEX. It applies CORTEX governance primitives uniformly across heterogeneous skills.

---

## Why this framework exists

Before this framework, skill enforcement was balkanized:

- ADLC used P0–P3 severity, full CORTEX integration.
- Journal used 5 quality loops with no severity tiers, no CORTEX integration.
- Podcast (v0) used 5 hard gates with no severity tiers, no DoR, no convergence.
- Refine / tell-me / clean-commit each used their own ad-hoc terms ("Tier 1/2", "Blocker/Warning", "Critical/High/Med/Low", "MAJOR").
- WIP skills used yet other taxonomies.

Result: a "blocker" in one skill meant something different from a "critical" in another, no shared rule language, non-deterministic outcomes, and silent failure modes the audit caught.

This framework fixes that.

---

## Section 1 — Severity Taxonomy (P0–P3)

Every skill **must** classify every quality check, gate, finding, or rule into one of four severity tiers. The taxonomy is precise and does not vary by skill.

### P0 — Critical / Immutable

**Definition:** A violation makes the output dangerous, incorrect, or non-compliant with non-negotiable governance. Cannot be deferred. Cannot be waived. Blocks all progression.

**Examples by skill type:**
- Voice violation that misrepresents the author (journal).
- Non-Latin script in podcast-ready audio output (podcast).
- Force-push to main, commit of secrets, deletion of tracked content files (clean-commit).
- Citation invented or fabricated (any skill).
- DoR < 100% before code-touching operation (any CORTEX-integrated skill).
- Quote attributed to a figure when the source did not attribute it (podcast, journal).

**Required action when P0 detected:** Halt immediately. Report. Do not proceed. Do not write output. Do not commit.

### P1 — High / Required

**Definition:** A violation produces output that is materially incorrect or significantly below quality standard, but not catastrophic. Blocks export / commit / apply. May be re-tried after correction.

**Examples:**
- Bracketed commentary heading in refined output (podcast).
- Section out of order (podcast, journal).
- Refined word count outside 70–140% of source (podcast).
- Uncommitted changes in target file at apply time (podcast apply, clean-commit).
- Missing CORE rule citation in skill-produced commit message (any skill).
- Synthesis older than latest transcript (tell-me).
- Inferred scope item shipped without operator confirmation (refine).

**Required action when P1 detected:** Halt the current operation. Report. Allow user to fix and re-run.

### P2 — Medium / Recommended

**Definition:** A violation reduces quality, clarity, or maintainability but does not block correctness. Should be reported with remediation guidance. User may waive with explicit acknowledgment.

**Examples:**
- Modern analogy density exceeds 1-per-300-words guideline (podcast).
- Long sentence (>40 words) not split when natural break exists (podcast).
- Multi-syllable term not hyphenated for stress (podcast phonetics).
- Identical paragraph appearing in two journal chapters (journal).
- Pass 4 zombie TODO older than 30 days (repo-surgeon).

**Required action when P2 detected:** Report with remediation. Allow proceed-with-warning. Log the waiver.

### P3 — Low / Advisory

**Definition:** A stylistic or convention preference. Reporting is informational only.

**Examples:**
- Preferred opening verb rotation suggests "explore" but skill used "examine" (podcast).
- Auto-clean removed a `.swp` file (clean-commit Tier 1).
- Section title could be more specific (any narrative skill).
- Convention-deviation that doesn't affect output correctness.

**Required action when P3 detected:** Report at end of run. Do not block.

### Mapping rule

When retrofitting an existing skill, map every existing check to exactly one of P0–P3 using this rubric:

1. Does the violation make the output *wrong*? → P0.
2. Does the violation make the output *materially worse* but recoverable? → P1.
3. Does the violation reduce *quality* but not *correctness*? → P2.
4. Is the violation a *preference*? → P3.

When in doubt, escalate one tier (P2 → P1). Hard-coded escalation paths are listed in each skill's overlay.

---

## Section 2 — The Six Challenger Primitives

Every skill must implement these six primitives, at minimum the ones marked **REQUIRED**. Optional primitives strengthen the skill but are not mandatory for compliance.

### Primitive 1 — Definition of Ready Gate (REQUIRED)

**CORTEX reference:** CORE-071 (DoR Enforcement Gate).

**Contract:** Before the skill performs its primary action, it verifies that the input meets a defined readiness threshold. If the threshold is not met, the skill halts and reports what is missing.

**Schema:** Each skill defines a DoR with these dimensions (weights skill-specific):

| Dimension | Description |
|---|---|
| Input completeness | Required inputs present, parseable, non-empty |
| Context clarity | Skill knows what the user wants (title, scope, target file, etc.) |
| Dependency resolution | Tools, files, lexicons the skill needs exist |
| Risk assessment | Any high-risk actions have been confirmed |
| Output target identified | Skill knows where to write |

**Pass criterion:** Weighted score ≥ threshold (skill-specific; typically 100% for code-touching ops, 80% for read-only ops).

**Failure handling:** Halt. Write a `DOR-INCOMPLETE.md` file (or analogous prompt) to the work directory naming what is missing. Do not proceed.

### Primitive 2 — Convergence Gate (REQUIRED for stateful skills)

**CORTEX reference:** CORE-068 (Convergence Gate).

**Contract:** When the skill makes changes, it iterates **detect → fix → rescan** until zero P0/P1 findings remain, OR until a maximum cycle count is reached (default: 3 cycles).

**Required when:** The skill modifies files, generates artifacts, or produces output that itself can fail subsequent quality gates.

**Optional when:** The skill is purely read-only and does not generate artifacts that require self-validation.

**Failure handling:** If max cycles reached and P0/P1 findings still exist, halt and report. Do not produce the final output. Do not declare success.

### Primitive 3 — Sweep Completeness Contract (REQUIRED for multi-target ops)

**CORTEX reference:** CORE-064 (Sweep Completeness — no partial sweeps).

**Contract:** When the skill applies a transformation to a class of targets (e.g., "all themes", "all chapters", "all .swp files"), it applies to **all matching targets or none**. No partial sweeps. No "I did 3 of 7 — finish the rest yourself."

**Required when:** The skill operates across multiple files or multiple instances of a pattern.

**Failure handling:** If applying to all matching targets would fail (e.g., one target has a hold), the skill applies to none and reports which target blocked the sweep.

### Primitive 4 — Holistic Validation Gate (REQUIRED for code/content-modifying skills)

**CORTEX reference:** CORE-048 (Holistic Validation Gate).

**Contract:** Before declaring success, the skill runs a five-check validation:

1. **Registry check** — affected files / artifacts are in the expected registry.
2. **Dependency drift check** — dependencies (lexicons, framework versions, sibling skill outputs) are current.
3. **Regression risk check** — modifications do not break existing tests / contracts.
4. **Governance compliance check** — output complies with this framework and applicable CORE rules.
5. **Challenge gate** — at least one alternative considered for non-trivial decisions.

**Pass criterion:** Composite risk score ≤ 0.6.

**Failure handling:** If risk > 0.6, generate alternatives and re-decide before producing final output.

### Primitive 5 — Challenge Gate (REQUIRED when scope or risk crosses thresholds)

**CORTEX reference:** CORE-048 (Challenge Gate, A/B comparison aspect).

**Contract:** When a non-trivial decision is made (architectural choice, design choice, scope expansion, anything with ≥ 2 plausible alternatives), the skill generates **at least two alternatives** with pros/cons/risk and either selects with reasoning or defers to the operator.

**Required when:**
- Scope affects more than 3 files OR
- Decision affects external contracts OR
- Decision has security / privacy / correctness implications OR
- Decision is permanent (irreversible).

**Failure handling:** Skill cannot proceed with a single-path decision when a Challenge Gate trigger fires. Must generate alternatives.

### Primitive 6 — Determinism Contract (REQUIRED for reproducibility)

**Contract:** Given the same input, the same state, and the same configuration, the skill produces structurally identical output across runs. Specific clauses:

- Hash-stable identifiers (slugs, IDs) for the same input.
- Same gate verdicts on the same content.
- Same ordering of findings (deterministic sort).
- Same selection among ties (define tiebreaker; never random).

**Allowed non-determinism:** Time-of-run metadata (timestamps), explicit randomness flagged by parameter, content that requires user judgment (with judgment captured in the input).

**Failure handling:** If determinism is impossible (e.g., subjective craft judgment in `/journal` Phase 2), the skill explicitly declares which stages are non-deterministic and why, and how the human-in-the-loop captures that judgment.

---

## Section 3 — Gate Status Schema

Every skill reports gate results using the same schema. Cross-skill orchestration depends on this.

### Per-gate report

```yaml
gate_id: GATE-<NN>
gate_name: <human-readable name>
cortex_reference: <CORE-NNN or "framework">
severity: P0 | P1 | P2 | P3
verdict: PASS | FAIL | WAIVED | SKIPPED
findings:
  - id: F-<NN>
    description: <one-line>
    location: <file:line or section reference>
    suggested_action: <remediation>
    severity: P0 | P1 | P2 | P3
metrics:
  - name: <metric>
    value: <number or string>
    threshold: <number or string>
    pass: true | false
duration_ms: <integer>
```

### Per-run summary

```yaml
skill: <skill name>
run_id: <hash>
timestamp: <ISO-8601>
framework_version: 1.0
input_hash: <hash of canonical input>
dor:
  required: true | false
  threshold: <percent>
  score: <percent>
  pass: true | false
gates:
  - <gate report 1>
  - <gate report 2>
  ...
convergence:
  cycles_used: <integer>
  max_cycles: <integer>
  final_state: CONVERGED | EXCEEDED_MAX | NOT_APPLICABLE
overall_verdict: PASS | FAIL_P0 | FAIL_P1 | PASS_WITH_WAIVERS
p0_count: <integer>
p1_count: <integer>
p2_count: <integer>
p3_count: <integer>
artifacts_written: [list of files]
artifacts_blocked: [list of files that would have been written if not for failures]
```

### Storage location

For skills that operate in a work directory (podcast, repo-surgeon, etc.): write the summary to `<work-dir>/_challenger-report.yml`.

For skills that operate in-place (journal, refine, tell-me, clean-commit, css-theme-sync, ui-modernizer): write the summary to `_workspace/challenger-reports/<skill>-<timestamp>.yml`.

This makes every run auditable and creates a shared trail across skills.

---

## Section 4 — Adoption Checklist

A skill is **CORTEX-Challenger compliant** when it satisfies every item below.

| # | Requirement | Required? |
|---|---|---|
| 1 | Severity tiers explicit — every check / gate / finding tagged P0–P3 | YES |
| 2 | DoR gate implemented per Primitive 1 | YES |
| 3 | Convergence loop implemented per Primitive 2 | YES if stateful |
| 4 | Sweep completeness per Primitive 3 | YES if multi-target |
| 5 | Holistic Validation per Primitive 4 | YES if modifies code/content |
| 6 | Challenge Gate per Primitive 5 | YES if scope/risk gates apply |
| 7 | Determinism contract per Primitive 6 | YES; declare exceptions |
| 8 | Gate status schema used per Section 3 | YES |
| 9 | Run summary written per Section 3 storage | YES |
| 10 | Applicable CORE rules cited in skill's SKILL.md | YES |
| 11 | Overlay or in-place compliance doc references this framework by version | YES |

Compliance level = items satisfied / items applicable. A skill at 100% applicable items is "Fully Compliant".

A skill at <80% applicable items must report its compliance level in its SKILL.md description.

---

## Section 5 — Skill Compliance Tiers

For tracking purposes, skills are categorized:

| Tier | Definition |
|---|---|
| **GOLD** | 100% applicable items satisfied + all gates hard + framework references in SKILL.md |
| **SILVER** | 100% applicable items satisfied but some gates documented-but-not-enforced |
| **BRONZE** | ≥80% applicable items satisfied, key gates enforced |
| **NEEDS-WORK** | <80% applicable items satisfied |
| **PRE-COMPLIANCE** | Skill has not yet been retrofitted to the framework |

The `skill-registry.md` document records each skill's tier and last audit date.

---

## Section 6 — Overlay Schema for Read-Only Plugin Skills

For skills whose SKILL.md cannot be directly edited (plugin-managed read-only files), the framework is applied via an **overlay document** at `journal/reference/skill-overlays/<skill-name>-cortex-overlay.md`.

The overlay describes:

1. The skill's compliance tier (Section 5).
2. Mapping of existing checks/gates to P0–P3.
3. Missing primitives and how they should be added.
4. Applicable CORE rules.
5. Determinism declarations.
6. Specific silent-failure modes the audit caught and how the overlay closes them.

The overlay is **applied** by:

- Reading the overlay alongside the plugin SKILL.md when the skill is invoked.
- Manually patching the plugin SKILL.md on the next plugin rebuild/release.
- Adding overlay-defined checks to any external validators the skill uses.

Overlays are versioned with the framework. An overlay at framework v1.0 declares compliance against this document. Later framework versions require overlay updates.

---

## Section 7 — Cross-Skill Coordination

When multiple skills run against the same target (e.g., `/journal` and `/podcast` both touching `translations-glossary.md`), the framework defines coordination contracts:

### Write conflicts

Only one skill may write to a given file in a single transaction. Other skills propose changes via a staging file. The skill that "owns" the file's authoring (per `skill-registry.md`) accepts or rejects.

| Target | Owner |
|---|---|
| `chapters/*.txt` | journal |
| `content/babu-memoir/_system/translations-glossary.md` (memoir sections) | journal |
| `content/babu-memoir/_system/translations-glossary.md` (Podcast Pronunciation Lexicon section) | podcast |
| `content/babu-memoir/_system/quotes-library.txt` | journal (other skills propose) |
| `content/babu-memoir/_system/clinic-library.txt` | journal (other skills propose) |
| `content/babu-memoir/_system/incident-bank.md` | journal only |
| `content/babu-memoir/_system/voice-fingerprint*.md` | journal only |
| `_workspace/podcast/<slug>/*` | podcast |
| Theme CSS files | css-theme-sync |
| `site/*.html` | ui-modernizer (with css-theme-sync coordinating) |

### Read precedence

When a skill needs information from another skill's output:
- Prefer the latest committed version.
- If staging file is newer than committed, ask user which to use.
- Never silently mix staged and committed state.

### Failure propagation

If a downstream skill detects that an upstream skill's output is non-compliant (e.g., podcast detects a glossary entry that violates podcast's own determinism rules), it flags but does not auto-fix. Upstream skill owns its files.

---

## Section 8 — Framework Versioning

This is framework version **1.0**. Subsequent versions follow semantic versioning:

- **Major** (v2.0): Breaking change to severity tiers or primitive contracts. Requires every skill's overlay to be reviewed.
- **Minor** (v1.1): Additive — new primitive, new optional check, new overlay field. Existing compliant skills remain compliant.
- **Patch** (v1.0.1): Documentation clarification. No behavior change required.

A skill's overlay declares which framework version it targets. The skill registry tracks divergence.

---

## Section 9 — Adoption Status (as of 2026-05-16)

| Skill | Tier | Framework version targeted | Overlay path |
|---|---|---|---|
| ADLC | GOLD (pre-existing) | implicit (predates framework) | (none — already CORTEX-native) |
| CORTEX | BASELINE | (defines its own rules) | (none) |
| Podcast | GOLD | 1.0 (in-place retrofit) | (in SKILL.md) |
| Journal | SILVER (target after overlay applied) | 1.0 | `skill-overlays/journal-cortex-overlay.md` |
| Refine | BRONZE (target after overlay applied) | 1.0 | `skill-overlays/refine-cortex-overlay.md` |
| Tell-me | SILVER (target after overlay applied) | 1.0 | `skill-overlays/tell-me-cortex-overlay.md` |
| Clean-commit | BRONZE (target after overlay applied) | 1.0 | `skill-overlays/clean-commit-cortex-overlay.md` |
| css-theme-sync | SILVER (target after retrofit) | 1.0 | (in skill files) |
| repo-surgeon | BRONZE (target after retrofit) | 1.0 | (in skill files) |
| ui-modernizer | SILVER (target after retrofit) | 1.0 | (in skill files) |
| usage-auditor | BRONZE (target after retrofit) | 1.0 | (in skill files) |

Targets above represent the post-retrofit state. Until retrofits land, all skills except ADLC and CORTEX are at PRE-COMPLIANCE.

---

## Section 10 — How to use this framework

**For a skill author:**

1. Read this entire document.
2. Map your skill's existing checks/gates to P0–P3.
3. Identify which primitives apply.
4. For each applicable primitive, implement (or declare a documented exception).
5. Add the Gate Status Schema to your skill's output.
6. Cite this framework by version in your SKILL.md.
7. For read-only plugin skills, write an overlay at `journal/reference/skill-overlays/<skill>-cortex-overlay.md`.
8. Register in `journal/reference/skill-registry.md`.
9. On every run, write the run summary per Section 3.

**For a skill user:**

- Every skill that targets framework v1.0 produces a `_challenger-report.yml` after each run.
- Severity tiers mean the same thing across skills — P0 always halts; P3 is always advisory.
- DoR failures will always halt before work begins, never after.
- Convergence is bounded at 3 cycles by default; if your skill hits the limit, it's a signal that the input or the gate definitions need attention.

---

## Section 11 — Anti-patterns

These patterns violate the framework:

| Anti-pattern | Why it's wrong | Correct pattern |
|---|---|---|
| Calling everything "Blocker" or "Warning" | No severity hierarchy | Use P0–P3 explicitly |
| Running gates after writing output | Output can't be un-written | Run gates BEFORE writing |
| Allowing P0 waivers | P0 is immutable by definition | If it's waivable, it's P1 or lower |
| Manual convergence ("ask user to re-run") | Not deterministic | Automated 3-cycle loop |
| Silent partial sweeps | Violates CORE-064 | All-or-none, named target list |
| Gate verdicts that depend on subjective judgment | Not deterministic | Externalize judgment (ask user, record decision) |
| Skill writes to another skill's owned files | Violates Section 7 | Staging file + apply step |

---

## Glossary

- **Challenger**: The mechanism that enforces a rule. Includes gates, validators, convergence loops, sweep contracts.
- **Gate**: A specific check with a binary or graded verdict.
- **Primitive**: One of the six universal mechanisms every compliant skill implements (DoR, Convergence, Sweep, Holistic Validation, Challenge, Determinism).
- **Overlay**: A framework-compliance document for a read-only plugin skill.
- **Severity tier**: P0 / P1 / P2 / P3 — the universal priority taxonomy.
- **CORE rule**: A CORTEX governance rule (e.g., CORE-068). Defined by CORTEX, not by this framework.
- **DoR**: Definition of Ready.
- **Convergence**: Detect → fix → rescan until clean or max-cycles.
- **Sweep**: An operation across multiple matching targets.

---

End of CORTEX Challenger Framework v1.
