# Knowledge Library

Canonical, deduped, classified knowledge atoms extracted from every book the podcast
pipeline processes. Shared across all books. Read by the **Augmenter** during future
books' enrichment, authoring, and challenger phases — so each new book walks in on the
shoulders of prior treatments.

> **Status — 2026-05-25**: scaffolded, awaiting Wave 1 implementation.
> No atoms yet. First atoms arrive when the first book through the pipeline post-Wave-1
> completes phase `0h-knowledge-extract` (slotted between the existing `0g` audit and
> `finalize`).

## Authoritative references

- **Spec**: [_workspace/plan/intelligence-pipeline-wave1-spec.md](../../_workspace/plan/intelligence-pipeline-wave1-spec.md)
- **Visual overview**: [_workspace/plan/view/intelligence-pipeline.html](../../_workspace/plan/view/intelligence-pipeline.html)
- **Agent definition**: [.github/agents/podcast-librarian.agent.md](../../.github/agents/podcast-librarian.agent.md)

## Layout

```
content/knowledge-base/
├── README.md                       # this file
├── quran.jsonl                     # Quran verse atoms (Wave 1)
├── hadith.jsonl                    # Hadith atoms (Wave 1)
├── quotes.jsonl                    # Quote atoms (Wave 2 — not yet created)
├── etymology.jsonl                 # Etymology atoms (Wave 3 — not yet created)
├── definitions.jsonl               # Definition atoms (Wave 2 — not yet created)
├── _conflicts/
│   └── pending-review.jsonl        # flagged conflicts halting phase 08b
└── _index/
    └── stats.json                  # counts, last-updated, top-cited
    # _index/embeddings.faiss arrives in Wave 2
```

## Atom format (JSONL — one atom per line)

Every atom shares a common envelope. The body differs per type.

```jsonc
{
  "id":         "<type>:<canonical-id>",
  "type":       "quran" | "hadith" | "quote" | "etymology" | "definition",
  "first_seen": { "book": "<slug>", "chapter": "<n>", "date": "ISO8601" },
  "sources":    [ { "book": "<slug>", "chapter": "<n>", "locator": "<heading|para#>" } ],
  "variants":   [ /* captured wording differences */ ],
  "body":       { /* type-specific fields, see spec §4 */ }
}
```

## Wave roadmap

| Wave | Atom types | Dedup mechanism | Status |
|------|-----------|-----------------|--------|
| **Wave 1** | Quran, hadith | Canonical-id exact match | Awaiting implementation |
| **Wave 2** | + Quotes, definitions | Embedding similarity (≥ 0.92) | Planned |
| **Wave 3** | + Etymology | Root-keyed tree match | Planned |

Each wave is a focused build, not a parallel scramble. Wave 1 proves the architecture
on easy types; later waves add ML-driven dedup once the bones are validated.

## Defaults (post 2026-05-25 self-review)

- **Extractor cost cap**: $2.00/book (raised from initial $0.50 estimate; tafsir-heavy
  books can have 200+ citations).
- **Augmenter default state**: DISABLED. Every call site checks
  `series.enable_knowledge_augmenter` (default `false`) and short-circuits. Operator
  flips per-book during A/B rollout; default flips on only after the Gate I A/B
  acceptance check passes on at least one book pair.
- **Hadith fallback**: matn-only citations (no collection/number) accepted as
  `hadith:uncited:<sha256>` with text-hash dedup. Semantic dedup arrives in Wave 2.

## Operational rules

- This folder is read by the Augmenter, written by the Librarian (phase
  `0h-knowledge-extract`). No human writes here directly.
- Conflicts must be resolved (via `scripts/podcast/knowledge/resolve_conflicts.py`) and
  cleared from `_conflicts/pending-review.jsonl` before the phase can resume.
- Library state travels with each book branch's merge to `develop`. Cross-branch
  merge conflicts on these JSONL files are handled by re-running the Librarian on the
  merged state.
- `_index/embeddings.faiss` (Wave 2+) is regeneratable from the JSONL alone. If it
  corrupts, delete and regenerate; no backup discipline needed.

## Conventions

- **Greppable, diff-friendly, no daemon.** JSONL was chosen over SQLite + vector DB
  precisely because plain text survives a five-year shelf life and merges cleanly in
  git.
- **No emojis in atom content.** Atoms are scholarly references; bodies stay clean.
- **Provenance everywhere.** Every atom remembers which book and chapter introduced it,
  and every subsequent book that cites it.
- **Forward-only capture.** Wave 1 captures atoms only from books that complete
  `0h-knowledge-extract` going forward. A separate `backfill.py` script lives in
  `scripts/podcast/knowledge/` for the optional one-shot historical pass.
