# 05 — Intelligence pipeline + podcast pipeline working hand-in-hand  ✅ CONVERGED

> **STATUS 2026-05-29: design converged with Asif (decisions D14–D15). Deliberately lean — "best solution without over-engineering."** Binding outcome below; analysis retained as rationale. No code until the holistic T1+T2+T3 plan entry is written, snapshotted, approved.

## Locked decisions (D14–D15)

| # | Decision |
|---|---|
| **D14** | **One knowledge phase, one read, two renderers.** A single new pipeline phase runs after enrich (0e), immediately BEFORE the existing source-review gate (06a). It reads each chapter once (LLM call cached/skipped when the chapter is unchanged), verifies candidates against the corpus, and writes ONE verified-atom set. From that single set, two cheap/free renderers fan out: (1) episode-framing injection for the podcast, (2) the reader-sidecar markers from T2. The expensive read happens exactly once. **Reuse 06a** as the review point — NO new gate, NO new halt. Corpus↔chapter conflicts SURFACE to the human at 06a; no auto-resolution. Maps the prior doc's invented phase numbers (0h/11g/13) onto the real `CANONICAL_PHASES` (audit G2). |
| **D15** | **Rollout.** Injection is tradition-filtered by the T1/D5 firewall (book only gets its own tradition + universal). Prove the full chain end-to-end on the **ayyuhal-walad** pilot (5 chapters, already in the reader); flip on-by-default for all books only after the pilot proves clean. |

**Anti-over-engineering guardrails (explicitly NOT building now):** no second extraction pass for the reader (markers are a by-product of the same read); no new review gate; no automatic conflict resolution; defer the audit's nice-to-haves — P1 cross-episode similarity, P2 per-chapter model-version tracking, embeddings.

---

**Your assumption #4:** "Yes, the intelligence pipeline and podcast pipeline should work hand in hand."

## Current state (verified): they don't
- `orchestrate_book.py` `CANONICAL_PHASES` has no intelligence phase. The chain (`extractor → librarian → augmenter`) runs **only when invoked manually**.
- `wisdom_ingest_knowledge.py` (ingests the wisdom corpus into `atoms`) is also manual.
- The augmenter is gated by `enable_knowledge_augmenter` (default `False`, off on every book).
- `atoms` in `knowledge.db` are **write-only at runtime** — no phase reads them. So extracted knowledge never influences authoring, and never reaches the reader.

In short: the intelligence layer is a parked engine with no drive shaft to either the pipeline or the reader.

## What "hand-in-hand" should mean — the two integration seams

### Seam 1 — Intelligence INTO authoring (make episodes smarter)
Wire the chain into the pipeline so each book run:
1. **Extracts** atoms from the enriched chapters (after 0e).
2. **Librarian** dedupes/classifies against the corpus (NEW/KNOWN/VARIANT/CONFLICT) — surfaces conflicts to the review gate (06a already exists as the human gate).
3. **Augmenter** injects verified doctrine atoms into episode framing — *on by default*, not gated off.
Proposed phase placement: a `0h-knowledge` phase **after 0e, before 06a** (so the source-review gate can review what the augmenter wants to inject). This reuses the already-wired 06a gate rather than adding a new halt.

### Seam 2 — Intelligence INTO the reader (make chapters annotated)
The atoms the extractor finds (Quran/hadith/term, each with canonical ids and confidence) are *exactly* the silent markers doc `04` needs. Instead of a separate regex pass, the annotation sidecar is a **projection of the atoms table for that book/chapter**. This is the bridge that connects all three DISCUSS topics:

```
wisdom corpus (doc 03)  →  blackbox tools (doc 04)  →  extractor/librarian write atoms
        atoms  →  sidecar annotation JSON  →  reader renders silent markers (doc 04)
```

So docs 03/04/05 are not three projects — they are one pipeline seen from three angles. The corpus is the source, the blackbox is the access layer, the intelligence chain is the writer, the reader is the consumer.

## The design tension to resolve with you
The augmenter currently *prepends a doctrinal context block to episode text*. That's good for the **podcast** (NotebookLM reads richer framing) but it is NOT the same as **reader annotation** (inline verified markers). We should decide whether:
- **(a)** one pass produces both (atoms → augmenter block for episodes AND atoms → sidecar markers for the reader), or
- **(b)** they stay separate concerns with a shared atoms source.
My recommendation: **(a)** — single extract/classify pass, two renderers (episode-framing renderer + reader-sidecar renderer). One source of truth, no double-spend on LLM extraction.

## Risks / things to get right
- **Cost**: extraction is one LLM call per chapter. For a 14-chapter book that's 14 calls added to every run — must fit the spend cap. The librarian is pure-Python (free); the augmenter is template-based (free). So the only new cost is extraction, and it can be cached/skipped if chapters are unchanged.
- **Conflict handling**: librarian's CONFLICT class (corpus says X, chapter says Y) must route to 06a for human adjudication, not silently overwrite.
- **Determinism for the reader**: the sidecar must be regenerated only when the chapter changes, so reading is stable.

## Open questions for our discussion
1. Augmenter **on by default** for new books, or opt-in per book? (I recommend on-by-default once conflict-routing is proven on one book.)
2. Single pass producing both episode-framing AND reader-markers (my rec), or keep them separate?
3. Which book is the pilot for wiring this end-to-end? (`ayyuhal-walad` is small — 5 chapters — and already in the reader; good candidate.)
