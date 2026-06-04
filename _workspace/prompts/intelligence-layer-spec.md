# Intelligence layer — architecture spec (converged 2026-05-29)

*Merged from 03-wisdom-corpus-merge, 04-mcp-blackbox-annotation-engine, 05-intelligence-podcast-integration.*
*All decisions locked. Status: CONVERGED. No code until plan entry written, snapshotted, and approved.*

---

## Part 1 — Wisdom corpus: KQUR + KASHKOLE + KSESSIONS → one corpus

### Locked decisions D1–D9

| # | Decision |
|---|---|
| D1 | Source lifecycle is MIXED: KQUR frozen, KASHKOLE frozen (one-time import); KSESSIONS active (idempotent re-sync). |
| D2 | Build a **new purpose-built wisdom corpus** — intelligently extract ONLY podcast/intelligence-relevant content; aggressive dedup (40%+ overlap KASHKOLE↔KSESSIONS). NOT a lift-and-shift. |
| D3 | KSESSIONS kept as the live session system-of-record; corpus re-syncs (deduplicated, on-demand) from it. KQUR + KASHKOLE deleted after one-time extraction. |
| D4 | Corpus engine = **SQLite** (server-less, in-repo, machine-agnostic). SQL Server/Docker dropped for the corpus. The ~6 useful queries re-expressed in Python. |
| D5 | Single tradition auto-stamp: teaching+commentary → `fatimid-ismaili`; raw Quran+hadith text → `universal`. Per-record `tradition` field on every atom. |
| D6 | KQUR is the canonical Quran; KASHKOLE's duplicate HQ* Quran removed. |
| D7 | Tiered dedup: high-confidence near-identical → auto-merge into ONE canonical record; borderline → manual-review queue; ambiguous → never auto-merged. |
| D8 | KASHKOLE NOT retranslated (hard constraint) — extraction ingests existing polished English as-is. |
| D9 | Wisdom Corpus UI (deferred wave): reader "Kashkole" link renamed "Wisdom Corpus"; curation view + dedup review queue. |

### Canonical schema (one SQLite corpus)
- `quran_ayat` — from KQUR (canonical); drops KASHKOLE HQ* duplicate
- `quran_root` + `quran_derivative` — etymology from KQUR
- `hadith` + `narrator` — from KQUR
- `topic` + `topic_ayat` + `topic_term` — from KASHKOLE
- `glossary_term` + `term_group` — unify KASHKOLE Glossary/DeeniTerm + KQUR roots
- `session_summary` + `session_transcript` — wisdom subset of KSESSIONS only
- Provenance column on every row (`source_db`, `source_pk`) for idempotent re-ingestion

### Three-database inventory (reference)

| DB | Size | Wisdom tables | App-plumbing (exclude) |
|---|---|---|---|
| KQUR | 15 MB | QuranAyats, Roots, Derivatives, Ahadees, Narrators | — (clean) |
| KASHKOLE | 724 MB | Topics, TopicData, TopicAyats, Glossary, Binders | Emailer_* (6), Flash/SWF, HQ* Quran |
| KSESSIONS | 29 MB | Sessions, SessionSummary, SessionTranscripts, SessionDoctrines | Members, Auth, Families, canvas.*, Token*, Quiz |

---

## Part 2 — MCP blackbox as the annotation + silent-marker engine

### Locked decisions D10–D13

| # | Decision |
|---|---|
| D10 | Sidecar markers — `<chapter>.annotations.json`, position-keyed. Prose stays clean, survives re-authoring. Markers render visibly IN THE EDITOR with distinct per-type visual treatment. |
| D11 | Annotation timing — automatic pipeline phase, regenerated when chapter text changes, PLUS a manual "refresh markers" action in the editor after Asif's own edits. |
| D12 | Interpretive scope — factual reference markers (Quran/hadith/term/topic) are auto-applied (corpus-verified). Interpretive tags (esoteric/reality/sharia) are suggest-only: surfaced in editor as dismissible suggestions, applied only on Asif's accept. Machine owns facts; human owns doctrine. |
| D13 | Add 7th blackbox tool `verify_and_classify(span, context)`; build corpus FTS/lookup index in SQLite (no Docker); re-point reader popovers off quran.com/Gemini to corpus/blackbox. Corpus is the SOLE authoritative source — no public-source fallback. |

### What the blackbox needs to become the annotation engine
- **7th tool: `verify_and_classify(span_text, context)`** — returns `{type, canonical_id, confidence, verified}` per span
- **FTS5 mirror built** (`mirror.db`) — not yet built; annotation pass and reader must not require Docker
- **Reader popovers re-pointed** from quran.com/Gemini to `:4390` (QuranPopover.tsx, TermPopover.tsx, api/quran/verse.ts)
- **Sidecar annotation format** + render path in `highlight-renderer.ts` preferring sidecar over regex

### Visual-differentiation taxonomy
Machine-derivable (auto-applied): Quran refs, Hadith refs, Arabic terms, topic cross-refs
Human-judgment (suggest-only): esoteric, reality, sharia tags

---

## Part 3 — Intelligence pipeline + podcast pipeline integration

### Locked decisions D14–D15

| # | Decision |
|---|---|
| D14 | One knowledge phase, one read, two renderers. A single `0h-knowledge` phase after 0e, before 06a. Reads each chapter once (LLM call cached when unchanged), verifies candidates against corpus, writes ONE verified-atom set. Two renderers: (1) episode-framing injection for podcast, (2) reader-sidecar markers. Reuse 06a as the review gate — no new halt. Corpus↔chapter conflicts surface to human at 06a. |
| D15 | Rollout: tradition-filtered by D5 firewall. Prove end-to-end on ayyuhal-walad pilot (5 chapters). Flip on-by-default for all books after pilot proves clean. |

### The integration architecture (three docs seen as one pipeline)
```
wisdom corpus (D1–D9)  →  blackbox tools (D10–D13)  →  extractor/librarian write atoms
        atoms  →  sidecar annotation JSON  →  reader renders silent markers
        atoms  →  augmenter prepends framing block  →  episode .txt (podcast)
```

### Phase placement in CANONICAL_PHASES
```
0e (enrich)  →  0h-knowledge (NEW: extract + librarian + augmenter)  →  06a (source-review gate)
```

### NOT building now (anti-over-engineering guardrails)
- No second extraction pass for the reader (markers are a by-product of the atom write)
- No new review gate
- No automatic conflict resolution
- P1 cross-episode similarity, P2 per-chapter model-version tracking, embeddings — all deferred
