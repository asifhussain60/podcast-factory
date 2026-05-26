# Intelligence Pipeline — Wave 1 Spec

**Status**: proposal v1, awaiting implementation greenlight
**Scope**: Quran + hadith atom types only (canonical-id dedup, no embedding layer)
**Companion view**: [view/intelligence-pipeline.html](view/intelligence-pipeline.html)
**Date**: 2026-05-25
**Phase name**: `0h-knowledge-extract` (runtime id `"0h"`); the prior draft used `0g` /
`08b` before discovering the name collision with the existing dual-auditor phase.

This spec is implementation-ready. Wave 2 (quotes + definitions, embedding layer) and Wave
3 (etymology, tree atoms) follow once Wave 1 is healthy on 1–2 books.

---

## 1. Goal

Build a growing, deduped, classified knowledge library extracted from each book the
pipeline polishes. Wave 1 ships two atom types — Quran verses and hadith — both of which
have canonical IDs (`quran:<surah>:<ayah>`, `hadith:<collection>:<num>`) so dedup is exact
string match. Library state lives in `content/knowledge-base/` as JSONL and merges to
`develop` with each book.

Wave 1 success: a second book through the pipeline can see (in its authoring + challenger
prompts) the Quran verses and hadith the first book cited, with sources attached.

---

## 2. Architecture (three pieces)

### 2.1 Extractor
- **When**: end of phase `0g` (dual-auditor), before `finalize`. Atoms come from
  audit-vetted content.
- **Reads**: per-chapter bundles under `content/drafts/<slug>/_system/episode-drafts/EP##-<slug>/`
  (chapter source + `00-framing.md`). Path conventions per `extract_chapter.py`.
- **Writes**: `content/drafts/<slug>/_system/knowledge-atoms-scratch.jsonl` (one atom
  per line, no dedup yet).
- **How**: structured-output LLM call (Claude Sonnet) per chapter with a strict JSON
  schema. Returns atoms with confidence scores. Low-confidence atoms (< 0.7) flagged
  for review.
- **Cost cap**: $2.00/book default (raised from initial $0.50 estimate after Risk 2 review — tafsir-heavy books can have 200+ citations). Halt if exceeded. Lower the cap after we have real per-book telemetry from the first 3 books.

### 2.2 Librarian
- **When**: immediately after Extractor.
- **Reads**: `knowledge-atoms-scratch.jsonl` + canonical library
  `content/knowledge-base/{quran,hadith}.jsonl`.
- **Writes**: merged library files + `_system/knowledge-merge-report.md` + (if any)
  `content/knowledge-base/_conflicts/pending-review.jsonl`.
- **How**: pure Python, no LLM. Exact-match dedup on canonical ID. Three outcomes per
  atom:
  - **New** → append to library with full envelope.
  - **Known** → merge sources list (this book becomes another citation). If text differs,
    add to `variants[]`.
  - **Conflict** (same ID, irreconcilable difference, e.g. different hadith grading) →
    write to `_conflicts/pending-review.jsonl`, halt phase.
- **Halt behavior**: any conflict halts `0h-knowledge-extract` with
  `phase_status="halted"`. Resume requires conflict resolution.

### 2.3 Augmenter
- **When**: called as a helper from inside other phases of **future books**, NOT its own
  phase. The current book's content is already locked by the time `0h` runs, so the
  Augmenter has no in-book effect on the book that generated the atoms.
- **Reads**: `content/knowledge-base/{quran,hadith}.jsonl`.
- **Returns**: top-K atoms (K=5) relevant to the chapter or topic in question, formatted
  as injectable prompt context.
- **Wired into** (Wave 1, future books only):
  - `0e` enrichment prompt (light injection: "here are verses/hadith prior books have
    already treated — use if directly relevant")
  - `per-chapter` authoring prompt (medium injection: prior treatments for the canonical
    IDs found in this chapter's source slice)
  - `0g` audit (`podcast-challenger` agent) — heavy injection: full prior-treatment
    context for every canonical citation in the chapter under review
- **Selection**: exact canonical-ID match first; if a chapter pre-cites `quran:2:255`
  the Augmenter returns the existing atom. No semantic ranking in Wave 1.
- **Caps**: max 5 atoms per injection, max 800 tokens of injected text per prompt.
- **Default state: DISABLED** (per Risk 1 review). The Augmenter ships off — every
  call site checks `series.enable_knowledge_augmenter` (default `false`) and
  short-circuits to empty string if not set. Operator flips the flag per-book during
  A/B rollout. Default flips to enabled only after the A/B acceptance gate (§11.I)
  fires green on at least one book pair.

---

## 3. Phase wiring — `0h-knowledge-extract`

### 3.1 New Phase enum entry
Add to `scripts/podcast/_phases.py`:

```python
class Phase(StrEnum):
    # ...existing entries through ENRICHMENT = "08-enrichment"...
    KNOWLEDGE       = "0h-knowledge-extract"   # NEW · Wave 1
    SERIES_PLAN     = "09-series-plan"
    # ...rest unchanged...
```

Slot position: directly after `ENRICHMENT`, before `SERIES_PLAN`. Phase numbering uses
runtime `"0h"` to slot cleanly after the existing `"0g"` dual-auditor phase.

### 3.2 Handler in `orchestrate_book.py`
Add `_run_0h(bd: Path)` next to existing `_run_0e`:

```python
def _run_0h(bd: Path) -> None:
    """Knowledge-extract phase: Extractor + Librarian on enriched chapters.

    Halts the orchestrator if Librarian flags any conflicts.
    """
    from scripts.podcast.knowledge.extractor import extract_atoms_for_book
    from scripts.podcast.knowledge.librarian import merge_into_library

    scratch = extract_atoms_for_book(bd)
    report = merge_into_library(bd, scratch)
    _write_phase_report(bd, "0h-knowledge-extract", report)

    if report.conflict_count > 0:
        raise PhaseHalt(
            f"{report.conflict_count} knowledge conflict(s) pending review. "
            f"See content/knowledge-base/_conflicts/pending-review.jsonl"
        )
```

### 3.3 New R-* constants in `_rules.py`
- `R_KNOWLEDGE_EXTRACTOR_COST_CAP_USD = 2.00` — per-book extractor cost ceiling (raised from 0.50 per Risk 2 review)
- `R_KNOWLEDGE_AUGMENTER_DEFAULT_ENABLED = False` — Augmenter starts disabled; series-config flag flips on per-book during A/B rollout (per Risk 1 review)
- `R_KNOWLEDGE_AUGMENT_MAX_ATOMS = 5` — Augmenter top-K cap
- `R_KNOWLEDGE_AUGMENT_MAX_TOKENS = 800` — injected token budget per prompt
- `R_KNOWLEDGE_LIBRARIAN_CONFLICT_HALT = True` — conflicts halt the phase
- `R_KNOWLEDGE_EMBEDDING_MIN_SIM_MERGE = 0.92` — placeholder for Wave 2 (unused in Wave 1)
- `R_KNOWLEDGE_EMBEDDING_MIN_SIM_FLAG = 0.80` — placeholder for Wave 2 (unused in Wave 1)

### 3.4 State-file additions
`content/drafts/<slug>/_system/orchestrator-state.json` gets a new sibling under `phases`:

```jsonc
"phases": {
  // ...existing keys...
  "0h": {
    "phase_status": "running | completed | halted | failed",
    "started_at": "ISO8601",
    "finished_at": "ISO8601 | null",
    "cost_usd": 0.0,
    "atoms_extracted": { "quran": 0, "hadith": 0 },
    "atoms_new":       { "quran": 0, "hadith": 0 },
    "atoms_merged":    { "quran": 0, "hadith": 0 },
    "atoms_conflict":  { "quran": 0, "hadith": 0 },
    "conflict_file":   "content/knowledge-base/_conflicts/pending-review.jsonl | null"
  }
}
```

### 3.5 Docs-sweep (per CLAUDE.md merge rule)
Same merge that adds the phase MUST update:
- `framework.md` — add `0h-knowledge-extract` to the phase table.
- `skills-staging/podcast/SKILL.md` — add knowledge-extract to the phase narrative.
- `_workspace/plan/view/agents/podcast-challenger.agent.md` (Category catalog) — add
  a Knowledge-Augmentation category for cross-book consistency findings.

---

## 4. Atom schemas (Wave 1 types only)

### 4.1 Common envelope (every atom)
```jsonc
{
  "id":         "<type>:<canonical-id>",
  "type":       "quran" | "hadith",
  "first_seen": { "book": "<slug>", "chapter": "<n>", "date": "ISO8601" },
  "sources":    [ { "book": "<slug>", "chapter": "<n>", "locator": "<heading|para#>" } ],
  "variants":   [ /* see §4.4 */ ],
  "body":       { /* type-specific, see below */ }
}
```

### 4.2 Quran body
```jsonc
"body": {
  "surah": 2,
  "ayah":  255,
  "text_ar":     "<Arabic verse text>",
  "text_en":     "<English translation as used in source>",
  "translator":  "<if attributable, else null>",
  "tafsir_refs": [ ]   // reserved for future use
}
```

Canonical id: `quran:2:255`. Sub-verses (e.g. `quran:2:255a`) handled in Wave 2.

### 4.3 Hadith body
```jsonc
"body": {
  "collection": "bukhari" | "muslim" | "tirmidhi" | "abu-dawud" | "nasai" | "ibn-majah" | "other",
  "number":     1234,
  "grade":      "sahih" | "hasan" | "daif" | "unknown",
  "text_ar":    "<Arabic matn>",
  "text_en":    "<English translation>",
  "chain":      "<isnad text if present, else null>",
  "narrator":   "<companion attribution if present, else null>"
}
```

Canonical id: `hadith:bukhari:1234`. Hadith outside the standard collections use
`hadith:other:<sha256 of normalized matn>` and dedup falls back to fuzzy in Wave 2 (in
Wave 1 they're left as separate atoms — accepted limitation).

### 4.4 Variants tracking
When the Librarian sees a known canonical ID with text that differs from the canonical
atom (e.g. different English translation):
```jsonc
"variants": [
  {
    "book":       "<slug>",
    "chapter":    "<n>",
    "text_en":    "<the differing English text>",
    "translator": "<if attributable>"
  }
]
```
Different translations of the same verse are variants, not conflicts. Only true semantic
contradiction (different `text_ar`, different hadith `grade`, different `narrator`) is a
conflict.

---

## 5. Conflict resolution flow

When the Librarian flags a conflict:

1. Atom appended to `content/knowledge-base/_conflicts/pending-review.jsonl` with
   `{existing_atom, incoming_atom, reason, book_slug, chapter}`.
2. Phase `0h-knowledge-extract` halts with `phase_status="halted"`.
3. Heartbeat card surfaces the halt + conflict count + file path.
4. Human reviews the conflict file. Three resolution options:
   - **Accept incoming** — overwrite existing, add old to variants.
   - **Keep existing** — discard incoming, log decision.
   - **Both as variants** — promote incoming difference into variants list.
5. Human runs `scripts/podcast/knowledge/resolve_conflicts.py <slug>` which applies the
   decisions and clears the conflict file.
6. Orchestrator resumed via `--retry-phase 0h-knowledge-extract`.

Resolution is the user's call. Wave 1 doesn't try to auto-merge conflicts.

---

## 6. Augmenter contract (Wave 1)

### 6.1 API
```python
# scripts/podcast/knowledge/augmenter.py

def augment_for_chapter(
    book_slug: str,
    chapter_id: str,
    chapter_text: str,
    *,
    types: tuple[str, ...] = ("quran", "hadith"),
    max_atoms: int = 5,
    max_tokens: int = 800,
) -> str:
    """Return a prompt-ready string of prior atoms relevant to this chapter.

    Wave 1 implementation: regex-scans chapter_text for canonical citations
    (e.g. "Quran 2:255", "Bukhari 1234") and looks them up directly. No
    semantic ranking.

    Default-disabled: returns empty string immediately if
    series.enable_knowledge_augmenter is not True. Operator flips per-book
    during A/B rollout. Default flips only after §11.I gate passes.

    Returns empty string if no matches. Always returns within max_tokens budget.
    """
```

### 6.2 Injection format
Returned string follows this template (injectable into any prompt):

```
--- PRIOR KNOWLEDGE CONTEXT ---
The following verses/hadith have been treated in earlier books in this corpus.
Use this context if directly relevant; otherwise ignore.

[quran:2:255] Ayat al-Kursi
  Prior treatment: kitab-al-riyad ch.3, framed as foundation for divine names.
  Source text variant: "Allah! There is no god but He..." (Pickthall)

[hadith:bukhari:1] "Innamal a'malu bin-niyyat..."
  Prior treatment: kashkole ch.7, used as opening of intention chapter.
  Prior treatment: kitab-al-riyad ch.1, framed as universal preface.

--- END PRIOR KNOWLEDGE ---
```

### 6.3 Call sites in Wave 1
| Caller (future books only, **gated by `series.enable_knowledge_augmenter`**) | Purpose | Token budget |
|---|---|---|
| `0e` enrichment per-chapter prompt | Light: hint that prior books touched these | 200 |
| `per-chapter` authoring | Medium: full prior treatment for citations | 500 |
| `0g` audit (`podcast-challenger` agent) | Heavy: complete cross-book context | 800 |

Each call site reads the flag at runtime; default `false`. Operator enables per-book
in `series-config.yaml` during A/B rollout. No code change required to flip a book in
or out.

---

## 7. File layout (canonical library)

```
content/
├── drafts/
│   └── <slug>/
│       └── _system/
│           ├── knowledge-atoms-scratch.jsonl       # per-book Extractor output
│           └── knowledge-merge-report.md           # per-book Librarian report
└── knowledge-base/                                 # NEW — shared, merged via develop
    ├── README.md                                   # explains the layout
    ├── quran.jsonl                                 # canonical Quran atoms
    ├── hadith.jsonl                                # canonical hadith atoms
    ├── _conflicts/
    │   └── pending-review.jsonl                    # halts the phase
    └── _index/
        └── stats.json                              # counts, last-updated, top-cited
        # _index/embeddings.faiss arrives in Wave 2
```

`quotes.jsonl`, `etymology.jsonl`, `definitions.jsonl` are NOT created in Wave 1 — they
arrive in Waves 2 and 3.

---

## 8. Branch + merge discipline

Wave 1 honors the existing per-book branch policy:
- Book on branch `<prefix>/<slug>` (e.g. `book/kitab-al-riyad`).
- Extractor writes scratch file to that branch's `content/drafts/<slug>/_system/`.
- Librarian writes to canonical library files on that same branch.
- When the book branch merges to `develop` (post-`publish`), library changes ride along.
- Two books in flight on parallel branches: last-merged book's Librarian re-runs against
  the now-updated library at merge time. This is automatic — handled by the standard
  merge conflict workflow plus a `git merge` hook that re-invokes Librarian on
  `content/knowledge-base/*.jsonl` if both branches touched it.

Acceptable limitation in Wave 1: if two parallel branches both add the same new atom,
the merge hook detects it and the human resolves by accepting one side and re-running
Librarian. Auto-merging multi-branch library writes is a Wave 4 problem if it becomes
common.

---

## 9. Testing plan

### 9.1 Unit tests (Python)
- `test_extractor_schema_validation.py` — bad atoms raise.
- `test_librarian_dedup_quran.py` — same ID merges sources.
- `test_librarian_dedup_hadith.py` — same collection+number merges; different grade
  flags conflict.
- `test_librarian_variants_added.py` — different `text_en` for same ID adds to variants,
  not conflicts.
- `test_augmenter_token_budget.py` — never returns > max_tokens.
- `test_augmenter_no_matches_empty.py` — returns empty string cleanly.

### 9.2 Integration test (one book end-to-end)
- Run pipeline on a small test book to phase `0h-knowledge-extract`.
- Assert `knowledge-atoms-scratch.jsonl` has N atoms.
- Assert `content/knowledge-base/quran.jsonl` has N atoms.
- Assert merge-report has zero conflicts.
- Run pipeline on a second test book that shares known atoms.
- Assert Librarian merges (no new atoms added, sources updated).
- Assert Augmenter returns prior atoms when authoring the second book.

### 9.3 Manual acceptance
- A human reads the merge report after one real book.
- A human reads three random atoms from `quran.jsonl` and confirms they match the
  source.
- A human reads two atoms from `hadith.jsonl` and confirms grading/collection accurate.

---

## 10. What's deliberately not in Wave 1

- Embedding model, FAISS index, semantic dedup (Wave 2 introduces these for quotes +
  definitions; Quran + hadith never need them).
- Web UI for browsing the library (out of scope until augmentation value is proven).
- Cross-book Q&A or chat over the library (separate future product decision).
- Backfill of already-published books — Wave 1 captures atoms forward-only. Backfill
  becomes a one-shot script in Wave 1.5 if needed.
- Etymology and definitions atom types (Waves 2–3).
- Sub-verse Quran granularity (`quran:2:255a` etc.) — single-ayah only in Wave 1.

---

## 11. Acceptance criteria (ship gate for Wave 1)

A. Phase `0h-knowledge-extract` runs as part of `orchestrate_book.py --resume <slug>`.
B. Extractor produces valid scratch JSONL on a 3-chapter test book in under 90 seconds.
C. Librarian dedup correctness verified by §9.1 unit tests passing.
D. Augmenter injection observed in authoring prompts for a second book that shares
   atoms with the first.
E. Heartbeat card shows new `0h` line with cost + atom counts.
F. Merge report on a 3-chapter book lists at least 5 atoms across both types.
G. Conflict halt verified by intentionally seeding a conflicting hadith and confirming
   the orchestrator halts cleanly.
H. Docs-sweep complete: `framework.md`, `SKILL.md`, `podcast-challenger.agent.md`
   updated in same PR as the code.
I. **A/B flywheel-health gate** — run Book N with `enable_knowledge_augmenter: false`
   and Book N+1 with the flag set `true`. The `podcast-challenger` audit on Book N+1
   must include at least one finding that references an Augmenter-injected atom
   (e.g., "this hadith was framed differently in Book X — author may want to address").
   Without that signal we have no evidence augmentation is actually changing outputs.
   Until Gate I fires green, the Augmenter default stays `false`.

When all nine pass on a real book run, Wave 1 ships and Wave 2 planning begins.

---

## 12. Open questions for implementation

1. **Extractor LLM choice** — Claude Sonnet 4 (default for the pipeline) or Haiku
   (cheaper, may miss complex citations). Recommend Sonnet first, profile, decide.
2. **Locator format** — Wave 1 uses heading text + paragraph number. Switch to byte
   offsets if needed for diff stability.
3. **Augmenter regex source-of-truth** — citation patterns need their own constants file
   (`scripts/podcast/knowledge/_citation_patterns.py`) since multiple books will use
   varying citation styles.
4. **Test-book selection** — recommend the smallest book currently in
   `content/drafts/` (or create a 3-chapter synthetic book under
   `_workspace/plan/_drivers/`).

These don't block spec acceptance; they're flagged for the implementation kickoff.

---

## 13. Implementation work breakdown (estimate)

| Step | Owner | Est. |
|---|---|---|
| 1. Scaffolding (this commit) | done | done |
| 2. `_phases.py` Phase enum + `_rules.py` constants | implementer | 30 min |
| 3. Extractor (LLM call + schema validation) | implementer | 3–4 hrs |
| 4. Librarian (dedup, merge, conflict flagging) | implementer | 3–4 hrs |
| 5. Augmenter (regex scan + lookup + injection) | implementer | 2 hrs |
| 6. Orchestrator handler `_run_0h` | implementer | 1 hr |
| 7. Wire Augmenter into `08-enrichment` prompt | implementer | 1 hr |
| 8. Wire Augmenter into `11-per-chapter` authoring | implementer | 1 hr |
| 9. Wire Augmenter into `podcast-challenger` | implementer | 1 hr |
| 10. Unit tests (§9.1) | implementer | 2 hrs |
| 11. Docs-sweep (framework.md, SKILL.md, challenger catalog) | implementer | 1 hr |
| 12. Integration test on real book | implementer | 1–2 hrs |
| **Wave 1 total** | | **~17–20 hrs of focused engineering** |

---

## 14. Revision log

- **2026-05-25** — Initial spec. Wave 1 scope = Quran + hadith only. Wave 2/3 to follow.
