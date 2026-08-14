# Knowledge Library

Canonical, deduped, classified knowledge atoms extracted from every book the podcast
pipeline processes. Shared across all books. Read by the **Augmenter** during future
books' enrichment, authoring, and challenger phases — so each new book walks in on the
shoulders of prior treatments.

> **Status — 2026-05-31**: `knowledge.db` is live. `mirror.db` holds the Kashkole FTS corpus (6,236 Quran rows + 1,347 topics).
>
> **Durability/portability — 2026-06-15**: `knowledge.db` is gitignored *local* state. The per-type JSONL files (`quran.jsonl`, `hadith.jsonl`, `doctrine.jsonl`, `quote.jsonl`, …) are the **committed, machine-portable source of truth** — text, one atom per line, sorted by id, so git union-merges two machines' atoms with no binary conflict. Keep them in sync with [`scripts/podcast/intelligence/corpus_sync.py`](../../scripts/podcast/intelligence/corpus_sync.py):
> - `export` — DB → JSONL (the pre-commit hook runs `export --safe` and stages the JSONL on every commit, so the corpus is always captured; `--safe` refuses to shrink a committed file).
> - `rebuild` — JSONL → DB, **additive-only** (INSERT OR IGNORE): a pull can only *add* atoms, never wipe local-only ones.
> - **Cross-machine protocol:** after `git pull`, run `corpus_sync.py rebuild` to absorb peers' atoms; before relying on a machine's export, `rebuild` first so its DB is a superset of git.

## Authoritative references

- **Spec**: [_workspace/plan/intelligence-pipeline-wave1-spec.md](../../_workspace/plan/intelligence-pipeline-wave1-spec.md)
- **Visual overview**: [_workspace/plan/view/intelligence-pipeline.html](../../_workspace/plan/view/intelligence-pipeline.html)
- **Agent definition**: [.github/agents/podcast-librarian.agent.md](../../.github/agents/podcast-librarian.agent.md)

## Layout

```
content/knowledge-base/
├── README.md                       # this file
├── knowledge.db                    # canonical SQLite — atoms, sources, variants, metadata
├── mirror.db                       # Kashkole + Quran FTS corpus (read-only source mirror)
├── quran.jsonl                     # committed source of truth (corpus_sync export)
├── hadith.jsonl                    # committed source of truth (corpus_sync export)
├── doctrine.jsonl                  # committed source of truth (corpus_sync export)
├── quote.jsonl                     # committed source of truth (corpus_sync export)
├── etymology.jsonl                 # committed source of truth (accuracy-gated etymology atoms)
├── lexicon.jsonl                   # committed root→meaning join (Lane/Maqayis/Mufradat, per root)
├── quranic-corpus/                 # Quranic Arabic Corpus morphology layer (GPL — see its README)
│   ├── source/…morphology-0.4.txt  # raw annotation file, committed with GPL header intact
│   └── morphology.db               # derived roots/lemmas/segments DB (committed, rebuildable)
├── lexicon/
│   └── source/{lane,maqayis,mufradat}/  # raw lexicon drops — untracked by default (gitignore)
├── _conflicts/
│   └── pending-review.jsonl        # flagged conflicts halting phase 08b
└── _index/
    ├── stats.json                  # counts, last-updated, top-cited
    ├── lexicon-coverage.json       # root-join coverage per lexicon source (no silent gaps)
    ├── embeddings.faiss            # Wave 2 — DERIVED artifact, rebuilt from knowledge.db
    └── id_map.json                 # Wave 2 — FAISS int index → atom id string
```

## Attribution & licensing

External reference data carries its upstream license; everything else in this
container is project-authored. Conventions:

- **Quranic Arabic Corpus** (`quranic-corpus/`) — GNU GPL, Copyright (C) Kais
  Dukes, <https://corpus.quran.com>. Redistributed with the license header
  intact; `morphology.db` is a derived work under the same license. Full
  notice + rebuild command: [quranic-corpus/README.md](quranic-corpus/README.md).
- **Classical lexica** (`lexicon/source/`, joined into `lexicon.jsonl`) — the
  texts (Lane's Arabic-English Lexicon; Ibn Faris, *Maqayis al-Lugha*;
  al-Raghib, *al-Mufradat*) are public domain; a specific digitization's own
  notes ship inside its drop folder. Drop folders are untracked by default —
  committing a given source text is a per-file decision.

### Vector index contract (Wave 2 — FAISS sidecar)

`embeddings.faiss` is a **derived artifact**, never a source of truth. If it is absent or corrupted, run:

```bash
python3 scripts/podcast/knowledge/build_faiss_index.py
```

This reads all atoms from `knowledge.db`, calls `text-embedding-3-small` in batch, writes the FAISS index and `_index/id_map.json`. No data is lost — `knowledge.db` is always the rebuild source. The index is NOT committed to git by default (add to `.gitignore`); it is rebuilt on the target machine as part of environment setup.

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
| **Wave 1** | Quran, hadith | Canonical-id exact match | Live — 7,036 atoms in `knowledge.db` |
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

## Quranic Studies import

Quranic Studies lecture knowledge enters the corpus through
`scripts/podcast/intelligence/import_quranic_studies.py`. The importer accepts a
candidate JSONL file, writes a dry-run report by default, and only writes to
`knowledge.db` when `--apply` is passed.

The import is intentionally conservative:

- Quran verses are normalized to `S:A` references and linked from the teaching
  body; the importer does not create duplicate Quran verse atoms.
- Teachings are doctrine atoms with `body.source_kind = "quranic_studies"`,
  plus `topic_tags`, `quran_refs`, series/session/source locator, and confidence.
- Exact duplicate teachings collapse onto one text-derived atom id.
- Near duplicates are sent to `manual_review_queue` as
  `quranic_studies_near_duplicate`, not silently merged.
- Topic tags are also mirrored to `atom_topic_tags` so the existing augmenter can
  retrieve them without a new parallel index.

Start every new source series with:

```bash
python3 scripts/podcast/intelligence/import_quranic_studies.py \
  --input <candidate-teachings.jsonl> \
  --dry-run
```

Apply only after the dry-run report has been reviewed.

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
