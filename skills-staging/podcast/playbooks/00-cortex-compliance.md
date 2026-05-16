# Stage 00 — CORTEX Challenger Framework Compliance

**This playbook defines /podcast's compliance with the CORTEX Challenger Framework v1** (canonical: `journal/reference/cortex-challenger-framework.md`).

Compliance tier: **GOLD** (target).
Framework version targeted: **1.0**.

---

## CORE rules applied

| Rule | How /podcast applies it |
|---|---|
| **CORE-002** — All output inline, no .md/.txt result files within reasoning loop | Skill writes output files as its deliverable (this IS the purpose); does not litter reasoning with intermediate scratch files. Working state confined to `_*` subdirectories under WORK_DIR. |
| **CORE-035** — Single canonical implementation | One pipeline (16 stages); no duplicate Stage 12 / Stage 12b — they are distinct (12 = refinement, 12b = library proposals). One master lexicon, one source of truth. |
| **CORE-048** — Holistic Validation + Challenge Gate | Stage 14 runs five quality gates (mapped to P0–P3). Stage 09 segmentation triggers Challenge Gate when auto-detect produces low-confidence boundaries — alternatives proposed for human review. |
| **CORE-064** — Sweep Completeness | Multi-file inputs processed all-or-none. Library proposal application is all-of-one-source-or-none. Phonetic substitution applies to every detected term in a section or none (no partial substitutions). |
| **CORE-068** — Convergence Gate | Quality gates run in a 3-cycle convergence loop. If gate fails, the relevant stage re-runs, gates re-evaluate. Max 3 cycles before halt. |
| **CORE-071** — DoR Enforcement | Stage 00.5 (below) is the DoR gate. 100% required before pipeline begins. |
| **CORE-INTERNAL-001** — Internal pipeline never echoed to user | Skill reports gate verdicts and final summary, not stage-by-stage reasoning logs. |
| **CORE-VOICE-001** — Business language only | Summary uses operator-facing language ("12 quotes proposed", "all gates passed") not internal jargon. |

---

## Severity tier mapping (every gate, every finding)

### Pre-flight / DoR (Stage 00.5)

| Check | Severity | Trigger | Action |
|---|---|---|---|
| Input file readable | P0 | File not found or unreadable | HALT — user supplies fix |
| Title detectable | P0 | Auto-detection fails AND user did not supply | HALT — write `DOR-INCOMPLETE.md` with prompt |
| Author detectable | P0 | Auto-detection fails AND user did not supply | HALT — write `DOR-INCOMPLETE.md` with prompt |
| Content type classifiable | P1 | Confidence < 0.6 | HALT — ask user to confirm or supply |
| WORK_DIR creatable | P0 | Path collision unresolvable | HALT |
| Size within NotebookLM limits | P1 | > 500K words OR > 200MB | HALT — ask user to split |
| Master lexicon readable | P0 | `translations-glossary.md` missing | HALT — skill cannot operate without it |
| Tradition file readable (if specified) | P0 | `traditions/<name>.yml` missing | HALT |
| OCR/transcription tooling available (if needed) | P1 | Tool missing for required format | HALT — write `MISSING-TOOL.md` |

### Pipeline gates (Stages 01–13)

| Stage | Check | Severity |
|---|---|---|
| 02 | OCR confidence > 80% per page | P2 — warn but proceed; >20% low → P1 → ask user |
| 02 | Transcription completes for audio/video | P0 |
| 03 | Metadata required fields populated | P0 (per DoR) |
| 04 | Tradition detection confidence ≥ 0.80 | P1 if 0.60–0.79 (ask user); P0 if < 0.60 (ask user) |
| 05 | Word count delta from cleaning < 10% | P1 (>10% triggers user review) |
| 06 | All non-Latin terms classified | P0 |
| 07 | Phonetic generated for every new term | P0 (NEEDS_REVIEW → P1) |
| 09 | Segmentation boundaries human-approved if auto-detect fails | P0 — halt for review |
| 09a | Every line in exactly one section | P0 |
| 10 | Every enrichment cited in editorial notes | P0 |
| 10 | No enrichment from `forbidden_enrichment_sources` | P0 |
| 11 | No analogy from `avoid_domains` | P1 |
| 11 | Analogy density ≤ 1 per 300 words | P2 |
| 12 | No non-Latin script in `01-refined/` | P0 |
| 12 | Tone preserved per detected tone labels | P1 |
| 13 | Single-sentence opening per section | P0 |
| 13 | Opening contains source + section identity | P0 |
| 13 | Three-part Focus directive present | P0 |
| 13 | Eight-rule anti-noise block appended | P0 |

### Output gates (Stage 14 — five quality gates)

| Gate | Severity | Per framework Section 3 schema |
|---|---|---|
| 1: No non-Latin script | **P0** | `gate_id: GATE-01`, `cortex_reference: CORE-068`, `severity: P0` |
| 2: No bracketed commentary | **P0** | `gate_id: GATE-02`, `cortex_reference: CORE-068`, `severity: P0` |
| 3: Citation provenance | **P0** | `gate_id: GATE-03`, `cortex_reference: framework-fab-prevention`, `severity: P0` |
| 4: Section order preserved | **P1** | `gate_id: GATE-04`, `cortex_reference: framework`, `severity: P1` |
| 5: Word count discipline (70-140%) | **P1** | `gate_id: GATE-05`, `cortex_reference: framework`, `severity: P1` |
| 6: Implicit citation detection (NEW) | **P0** | `gate_id: GATE-06`, `cortex_reference: framework`, `severity: P0` |
| 7: Per-section determinism check (NEW) | **P1** | `gate_id: GATE-07`, `cortex_reference: framework`, `severity: P1` |

Gates 6 and 7 are framework-added — described in `playbooks/14b-gates-6-7.md`.

### Apply gates (Stage 16)

| Check | Severity |
|---|---|
| Proposals file exists and parses | P0 |
| Quality gates passed for the run | P0 |
| Target libraries have no uncommitted changes | P1 |
| Target libraries exist | P0 |
| Per-proposal accept/reject decision read | P0 |
| Applied content keeps target libraries parseable | P0 |
| Journal-side quality gates pass after apply | P0 |
| Git commit succeeds | P1 |

---

## DoR Gate definition (Stage 00.5)

The DoR gate runs immediately after Stage 01 (ingest) and before any other stage. It scores against the framework's weighted dimensions:

| Dimension | Weight | Score 100% when |
|---|---|---|
| Input completeness | 30% | All input files readable and non-empty |
| Context clarity | 25% | Title + author + content type known (auto OR user-supplied) |
| Dependency resolution | 20% | Master lexicon readable; tradition file readable (if specified); OCR/transcription tools available (if needed) |
| Risk assessment | 15% | Within NotebookLM size limits; no flagged risk in input |
| Output target identified | 10% | WORK_DIR successfully created |

**Pass criterion:** Score = 100%. The DoR gate is binary at the dimension level: each dimension is either met or unmet; no partial credit.

**Failure handling:** Write `WORK_DIR/DOR-INCOMPLETE.md` listing every unmet dimension with the specific remediation needed. Halt. Skill cannot proceed until the user addresses each item and re-invokes.

---

## Convergence Gate behavior (Stage 14 wrapper)

The 5+2 quality gates run inside a convergence loop:

```
cycle = 0
WHILE cycle < 3:
    run all gates
    p0_count = count P0 failures
    p1_count = count P1 failures
    IF p0_count == 0 AND p1_count == 0:
        BREAK (converged)
    IF p0_count > 0:
        re-run stages that produced the P0 violations
    IF p1_count > 0:
        re-run stages that produced the P1 violations
    cycle += 1

IF p0_count > 0 OR p1_count > 0 after 3 cycles:
    HALT — write `CONVERGENCE-FAILED.md`
    do NOT export
    do NOT write ZIP
    do NOT write library proposals as final
```

Stage re-runs are scoped: only the stages producing the failing gates' inputs re-run, not the entire pipeline. The convergence loop is logged in `_challenger-report.yml`.

**Why max-3:** Per CORE-068. If three cycles don't converge, the input or the gate definitions need attention — not more cycles.

---

## Sweep Completeness contracts

| Sweep target | All-or-none unit |
|---|---|
| Multi-file source ingestion | Per source-slug — if one input file fails, all fail |
| Phonetic substitution within a section | All non-Latin terms in section, or none |
| Library proposal application | Per library, per source-slug (`/podcast apply <slug>` applies all accepted proposals to a single library atomically) |
| Section file generation | All sections, or none — if Stage 12 fails for any section, no `01-refined/` files written |

---

## Determinism Contract declarations

| Stage | Deterministic? | Why / exception |
|---|---|---|
| 01 Ingest | YES | File copy is deterministic |
| 02 Extract | YES for text/PDF; PARTIAL for OCR (model-dependent) | OCR confidence varies with engine version; declare engine + version in report |
| 03 Metadata | YES for explicit metadata; PARTIAL for inferred fields | Confidence scores recorded for inferred fields |
| 04 Tradition detection | YES given the same tradition files | Tradition file edits between runs change detection |
| 05 Clean/normalize | YES | Rules are mechanical |
| 06 Foreign term detection | YES | Unicode block scan is deterministic |
| 07 Phonetic generation | YES given same transliteration tables | Table edits change output |
| 08 Pronunciation projection | YES | Set intersection is deterministic |
| 09 Segmentation | YES if Stage 1 succeeds; HUMAN-IN-LOOP otherwise | Human review captures judgment |
| 10 Enrichment | PARTIAL — uses Haiku-call for relevance scoring | Same input + same tradition file produces same enrichment if Haiku output is stable; if not, declared as non-deterministic stage |
| 11 Analogies | PARTIAL — uses Haiku-call | Same as Stage 10 |
| 12 Refinement | YES if tone preservation rules are mechanical | Subjective tone choices documented in editorial notes |
| 12b Library proposals | YES | Pattern matching + dedup are deterministic |
| 13 Instructions | YES | Templates are filled deterministically |
| 14 Gates | YES | Mechanical checks |
| 15 Export | YES | File operations are deterministic |
| 16 Apply | YES | Git operations are deterministic given same proposals file |

Non-deterministic stages (10, 11) record their inputs and Haiku-call signatures in `_challenger-report.yml` so re-runs can be cross-referenced.

---

## Challenge Gate triggers

The skill triggers Stage 09 Challenge Gate (segmentation alternatives) when:

- Auto-detect (Stage 09 Stage 1) finds no qualifying marker pattern.
- Heuristic fallback (Stage 09 Stage 2) produces any boundary with confidence < 0.7.
- Validation (Stage 09a) flags coverage / minimum-length / maximum-length issues.

The skill triggers a tradition Challenge Gate when:

- Tradition detection confidence is 0.60–0.79 (proposes detected tradition, alternatives, asks user).

The skill does NOT trigger Challenge Gates for:

- Phonetic transcription (deterministic per tables).
- Enrichment selection within a tradition's whitelist (constrained, not subjective).
- Refinement choices below the tone-preservation threshold.

---

## Gate Status Schema usage

The skill writes `WORK_DIR/_challenger-report.yml` per the framework's Section 3 schema. Schema is canonical — no deviations. Example structure (illustrative, not from a real run):

```yaml
skill: podcast
run_id: <hash>
timestamp: 2026-05-16T18:42:11Z
framework_version: 1.0
input_hash: <hash>
dor:
  required: true
  threshold: 100
  score: 100
  pass: true
gates:
  - gate_id: GATE-01
    gate_name: "No non-Latin script in podcast-ready output"
    cortex_reference: CORE-068
    severity: P0
    verdict: PASS
    findings: []
    metrics:
      - name: violations_count
        value: 0
        threshold: 0
        pass: true
    duration_ms: 87
  ... (gates 2-7)
convergence:
  cycles_used: 1
  max_cycles: 3
  final_state: CONVERGED
overall_verdict: PASS
p0_count: 0
p1_count: 0
p2_count: 2
p3_count: 1
artifacts_written: [01-refined/, 02-instructions/podcast-instructions.md, 03-pronunciation.md, 04-editorial-notes.md]
artifacts_blocked: []
```

---

## What this overlay does NOT change

This compliance retrofit does NOT modify:

- The 16 pipeline stages' behavior — only adds reporting and convergence on top.
- The five canonical templates — opening, instruction block, anti-noise block, pronunciation projection, library proposal entry.
- The three-tier library policy.
- The output file layout.
- The user-facing command surface.

It strengthens enforcement without redesigning the skill.

---

## Verification

To verify /podcast meets framework v1.0:

```
Read this file (00-cortex-compliance.md).
Confirm every CORE rule in the table is reflected in actual playbook content.
Confirm every gate listed under Stage 14 exists in playbooks/14-quality-gates.md and playbooks/14b-gates-6-7.md.
Run /podcast against fixtures/synthetic-chapter.md.
Verify _challenger-report.yml is produced per Section 3 schema.
Verify all P0 gates pass.
Verify convergence count = 1 for clean input.
```

Compliance is **active** when all five verifications pass.
