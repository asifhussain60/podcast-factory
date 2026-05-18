# Podcast Skill — Learning Substrate

**Purpose.** Closed-loop intelligence training for the podcast pipeline. Every empirical signal the system observes (challenger findings, transcript drift, manual corrections) accumulates here. Recurring patterns get proposed as new rules. New rules must pass a fixture-based regression suite before merging into the normative rule files. The substrate guarantees that the challenger gets smarter over time without regressing prior fixes.

**Status.** Substrate live since 2026-05-18 (commit added in the "automated intelligence training" cycle).

---

## Layout

```
_learning/
├── README.md                 ← this file (contract)
├── findings.jsonl            ← append-only event ledger (one record per finding)
├── patterns.md               ← aggregator output: recurring signatures (≥2 books OR ≥3 episodes)
├── fixtures/                 ← regression fixtures (frozen input → expected output)
│   └── <check-id>/
│       ├── input.txt
│       └── expected.json
├── proposals/                ← rule-promotion proposals awaiting human review
│   └── YYYY-MM-DD-<signature>.md
├── promoted/                 ← proposals merged into normative rule files (with commit hash)
│   └── YYYY-MM-DD-<signature>.md
├── archive/                  ← rotated findings ledgers
│   └── findings-YYYYQN.jsonl
└── health/                   ← per-book quality score over time
    └── <book-slug>.json
```

---

## Pipeline (sense → aggregate → propose → test → promote)

| Stage | Producer | Consumer | Artifact |
|---|---|---|---|
| **Sense** | `audit_transcript.py`, `podcast-challenger` agent | — | `findings.jsonl` (append-only) |
| **Aggregate** | `scripts/podcast/learn_aggregate.py` | reads ledger | `patterns.md` (overwritten each run) |
| **Propose** | `scripts/podcast/learn_propose.py` | reads `patterns.md` | `proposals/*.md` (one per pattern crossing threshold) |
| **Test** | `scripts/podcast/test_challenger.py` | reads `fixtures/*` | exit 0 = green / non-zero = regression |
| **Promote** | human (after green test) | edits handbook + `_rules.py` | moves `proposals/<file>.md` → `promoted/<file>.md` with commit hash |

The sense and aggregate stages run unattended. Propose, test, and promote require a human `proceed` — this is deliberate (Goodhart-resistant).

---

## `findings.jsonl` schema

One JSON record per line. Append-only. Atomic single-line writes (each write < PIPE_BUF, safe across concurrent emitters). Fields:

```json
{
  "ts": "2026-05-18T13:24:12Z",          // ISO-8601 UTC, second precision
  "source": "podcast-challenger",          // "podcast-challenger" | "audit_transcript"
  "source_version": "1.9",                  // from CHALLENGER_VERSION or audit_transcript.py header
  "book": "kitab-al-riyad",                 // book-slug
  "episode": "EP01-the-lineage-of-a-lost-argument",  // EP##-<slug> or "" for book-scope
  "chapter": "ch01-the-lineage-of-a-lost-argument",  // chapter-slug or "" for framing-only
  "check_id": "A2",                         // Loop check ID (A1, B5, R4, etc.) or audit code (TX-MODERNIZE, TX-MANGLE)
  "severity": "P1",                         // P0 | P1 | P2 | INFO
  "signature": "ambiguous-citation:al-Kirmani-tradition",  // normalized human-readable canonical form (used for grouping)
  "file": "content/podcast/library/books/kitab-al-riyad/chapters/ch01-the-lineage-of-a-lost-argument.txt",
  "line": 169,                              // line number or null
  "context_excerpt": "divine address recorded in al-Kirmani's tradition; the verbal posture...",
  "resolution": "flagged"                   // "auto-fixed" | "flagged" | "carried" (still present in next run)
}
```

**Rules:**
- `signature` is the **grouping key**. Compose it deterministically from `check_id` + the smallest distinguishing detail (e.g., `A2:ambiguous-citation:al-Kirmani-tradition`, `R4:formal-transition:Firstly`, `TX-MANGLE:Tasawwuf→tassel wolf`). Two records with the same `signature` are by definition the same finding.
- `book` and `episode` together identify scope; aggregation thresholds use distinct counts of each.
- `source_version` lets us re-aggregate older data through a newer pattern lens.
- One record per finding per run (do **not** emit duplicates within a single run).

---

## Health score

After every challenger run, the agent writes `_learning/health/<book-slug>.json`:

```json
{
  "ts": "2026-05-18T13:24:12Z",
  "book": "kitab-al-riyad",
  "chapters_in_scope": 1,
  "p0": 0,
  "p1": 5,
  "p2": 1,
  "auto_fixes": 6,
  "score": 0.00,            // see formula below
  "verdict": "SHIP-WITH-CAUTION",
  "challenger_version": "1.9"
}
```

**Score formula:**

```
penalty   = (P0 × 1.0 + P1 × 0.2 + P2 × 0.05) / chapters_in_scope
score     = max(0.0, 1.0 - penalty)
```

**Thresholds (advisory; SHIP-READY remains the binary gate):**

| Score | Badge | Meaning |
|---|---|---|
| ≥ 0.95 for ≥ 2 consecutive runs | **Stable** | Safe to use this book as a fixture corpus for new rules |
| ≥ 0.90 | **Healthy** | Normal ship state |
| 0.50–0.89 | **Drifting** | Auto-fix exhausted; author follow-up needed |
| < 0.50 | **Unstable** | Likely needs framing or chapter restructure |

The challenger also appends a one-line entry to `BOOK_DIR/_system/health-trend.md`:

```
| 2026-05-18T13:24Z | 1.9 | 1 chs | P0:0 P1:5 P2:1 | score:0.00 | SHIP-WITH-CAUTION |
```

Stable, append-only, diffable.

---

## Proposal template (`proposals/YYYY-MM-DD-<signature>.md`)

```markdown
# Rule Promotion Proposal — <signature>

**Trigger.** <pattern from patterns.md>
**Occurrences.** <N> records across <K> books, <M> episodes.
**First seen.** YYYY-MM-DD · <book>/<episode>
**Last seen.** YYYY-MM-DD · <book>/<episode>
**Producer:** `scripts/podcast/learn_propose.py` v<version>

## Candidate rule

<one-paragraph description of the rule to add>

## Target file(s)

- `<path to normative rule file>` — section to update
- `<path to _rules.py>` (when applicable) — constant list to extend

## Fixture

Add to `_learning/fixtures/<check-id>/`:
- `input.txt` — minimal artifact exhibiting the failure
- `expected.json` — challenger findings the new rule should emit

## Acceptance

- `scripts/podcast/test_challenger.py` exits 0 after the rule lands.
- `_learning/findings.jsonl` shows the signature **stops appearing** in subsequent challenger runs (or appears only as `resolution: auto-fixed`).
- ROADMAP.md Section A gains an entry referencing this proposal.

## Verdict (human)

- [ ] Accept — promote rule to normative file, move this file to `promoted/`, append commit hash.
- [ ] Reject — move this file to `archive/` with a `Rejected because…` line.
- [ ] Defer — leave in place; revisit after <N> more episodes.
```

---

## Cold-start contract for the challenger

When the `podcast-challenger` agent runs:

1. Append every finding to `findings.jsonl`.
2. Write `_learning/health/<book-slug>.json` and append to `BOOK_DIR/_system/health-trend.md`.
3. Stamp the report's `challenger v<X>` line from the `CHALLENGER_VERSION` constant in `scripts/podcast/_rules.py`.

The aggregator and proposer are run by the `/podcast` skill's Phase 4 post-SHIP-READY hook (skill drives them; the agent does not).

---

## Anti-anti-patterns

- **Do not** auto-merge proposals. Human approval is the Goodhart guard.
- **Do not** delete from `findings.jsonl` — rotate quarterly into `archive/`.
- **Do not** put authored chapter content into `fixtures/`. Fixtures are minimal — just enough to exhibit the failure.
- **Do not** treat the health score as a target. It is an advisory signal; SHIP-READY remains the binary gate.
- **Do not** version proposals (`-v2`, `-final`). A new proposal for the same signature replaces the prior file in place (atomically; old version moves to `archive/`).
