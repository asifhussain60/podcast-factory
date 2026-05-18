# Canonical BOOK_DIR Layout

**Authoritative status:** Normative. Every podcasted source under `content/podcast/library/<category>/<book-slug>/` MUST follow the shape defined here. `scripts/podcast/scaffold_book.py` creates this layout in one shot; any deviation should be reconciled.

A `<category>` is one of: `books`, `articles`, `documents`, `lectures`, `interviews`, `letters`. A `<book-slug>` is kebab-case, ≤40 chars, unique under its category.

## Tree

```
content/podcast/library/<category>/<book-slug>/
├── _README.md                                    book-specific blurb + upload checklist
├── chapters/                                     ← SOURCE files (uploaded to NotebookLM as-is)
│   ├── ch01-<slug>.txt
│   ├── ch02-<slug>.txt
│   └── ...
├── chapter-contracts/                            ← the signed contract per chapter
│   ├── <slug>.yml
│   └── ...
├── episodes/                                     ← CUSTOMIZE PROMPT files (paste into NotebookLM Customize box)
│   ├── EP01-<slug>.txt
│   ├── EP02-<slug>.txt
│   └── ...
├── turboscribe/                                  ← human-input only (NotebookLM Audio Overview transcripts)
│   ├── _README.md
│   ├── EP01-<slug>.transcript.txt
│   └── ...
└── _system/                                      ← authoring metadata, never uploaded
    ├── registry.md                               ← per-book episode index
    ├── _README.md                                ← (optional) book authoring notes
    ├── pronunciation.md                          ← per-book phonetic overrides
    ├── mangle-map.md                             ← per-book NotebookLM TTS mangling map
    ├── meta-prose-tells.md                       ← per-book author-specific meta-prose tells
    ├── enrichment-whitelist.md                   ← Tier 1 author's-own-corpus (per book)
    ├── enrichment-log.md                         ← per-chapter enrichment status + provenance
    ├── challenger-report.md                      ← latest podcast-challenger output
    ├── scratchpad/
    │   └── series-policies.md                    ← Tier-3 @@policy markers (series-wide)
    ├── source/
    │   ├── <Source-Title>.<ext>                  verbatim original (audit anchor; never modified)
    │   └── text/
    │       ├── normalized.md                     Phase 0a output (one cleaned source file)
    │       ├── _phonetics.md                     Phase 0c index
    │       └── chapters-rationale.md             Phase 0d segmentation rationale
    └── episode-drafts/
        ├── EP01-<slug>/
        │   ├── 00-framing.md                     CUSTOMIZE PROMPT body
        │   ├── 02-key-passages.md
        │   ├── 03-context-pack.md
        │   ├── 04-discussion-spine.md
        │   ├── 99-show-notes.md                  (optional)
        │   └── chapter.scratch.md                refinement surface mirroring chapters/ch01-<slug>.txt
        ├── EP02-<slug>/
        └── ...
```

## What each file/folder owns

| Path | Owner | Read by | Written by |
|---|---|---|---|
| `_README.md` | the book | humans | author (manual) |
| `chapters/ch##-<slug>.txt` | the book — **the SOURCE** | NotebookLM (uploaded as-is); `build_episode_txt.py`; `podcast-challenger` | author (Phase 0d/0e); refinement pass |
| `chapter-contracts/<slug>.yml` | the book — Extract Mode contract | `extract_chapter.py`; `podcast-challenger` (Category G + P) | author; `extract_chapter.py` stub generator |
| `episodes/EP##-<slug>.txt` | the book — **the CUSTOMIZE PROMPT** | humans paste into NotebookLM | `build_episode_txt.py` (never hand-edit) |
| `turboscribe/EP##-<slug>.transcript.txt` | the book — TurboScribe transcript | `audit_transcript.py`; `podcast-challenger` Loop M | human (manual drop) |
| `_system/registry.md` | the book | `validate_registry.py`; humans | `new_episode.py`; author |
| `_system/pronunciation.md` | the book — phonetic overrides | `build_episode_txt.py` (via `_rules`); `podcast-challenger` | author |
| `_system/mangle-map.md` | the book — TTS mangling overrides | `audit_transcript.py:load_book_mangle_map` | author |
| `_system/meta-prose-tells.md` | the book — author-specific tells | `build_episode_txt.py:load_book_meta_prose_tells` | author |
| `_system/enrichment-whitelist.md` | the book — Tier 1 corpus | `podcast-challenger` enrichment audit | author |
| `_system/enrichment-log.md` | the book — chapter status + verification notes | `podcast-challenger` | author |
| `_system/challenger-report.md` | the book — latest challenger output | humans (verdict + findings) | `podcast-challenger` |
| `_system/scratchpad/series-policies.md` | the book — Tier-3 `@@policy` markers | refinement pass | scratchpad processing |
| `_system/source/<Source-Title>.<ext>` | the book — verbatim original | audit anchor | author (one-time drop) |
| `_system/source/text/normalized.md` | the book — Phase 0a output | Phase 0c–0e | Phase 0a |
| `_system/source/text/_phonetics.md` | the book — phonetic index | Phase 0d–0e + framing authoring | Phase 0c |
| `_system/source/text/chapters-rationale.md` | the book — segmentation rationale | humans, `podcast-challenger` Category P | Phase 0d |
| `_system/episode-drafts/EP##-<slug>/00-framing.md` | the episode — the source of CUSTOMIZE PROMPT | `build_episode_txt.py` | author (Phase 3) |
| `_system/episode-drafts/EP##-<slug>/02-key-passages.md` | the episode | humans, refinement | author |
| `_system/episode-drafts/EP##-<slug>/03-context-pack.md` | the episode | humans, refinement | author |
| `_system/episode-drafts/EP##-<slug>/04-discussion-spine.md` | the episode | humans, refinement | author |
| `_system/episode-drafts/EP##-<slug>/99-show-notes.md` | the episode | humans (post-render) | author (optional) |
| `_system/episode-drafts/EP##-<slug>/chapter.scratch.md` | the episode — refinement surface | refinement pass | author (drops `@@` markers); stripped after each pass |

## Strict shape rules

- **Empty folders are not required** to exist on disk. `chapter-contracts/` and `_system/scratchpad/` may not exist until needed; scripts create them lazily.
- **No `01-source-primary.md`** anywhere. Under v3.5 the chapter file IS the source; there is no separate source-primary file in the draft folder.
- **One slug per chapter, slug-identical across surfaces.** `chapters/chNN-<slug>.txt` ↔ `chapter-contracts/<slug>.yml` ↔ `_system/episode-drafts/EP##-<slug>/` ↔ `episodes/EP##-<slug>.txt` ↔ `turboscribe/EP##-<slug>.transcript.txt`. `build_episode_txt.py` enforces the match by slug.
- **Per-book overrides MAY add, NEVER contradict the shared manifest.** `pronunciation.md`, `mangle-map.md`, `meta-prose-tells.md`, `enrichment-whitelist.md` extend their shared/canonical counterparts; they never override a globally-canonical entry. The challenger's Category P6 (cross-book bleed) backstops this.

## Onboarding a new book

```
python3 scripts/podcast/scaffold_book.py <category> <book-slug> "<Book Title>" [--author "<Author Name>"]
```

This creates the full tree above (with empty headers in each `_system/*.md` file), drops a starter `_README.md`, and appends a one-line row to `content/podcast/.skill/books.md`. After scaffolding, run Phase 0a (OCR / format normalization) on the source file you drop into `_system/source/`, then 0b → 0c → 0d → 0e per SKILL.md §1.5.

## Validation

| Script | Check |
|---|---|
| `validate_registry.py` | per-book registry rows are well-formed; slugs match real chapter files |
| `extract_chapter.py` (lint) | contract.slug ↔ chapter slug; contract.title concise + unique within book (INVARIANT 6) |
| `build_episode_txt.py` | chapter + framing pass META_PROSE_TELLS, HTML-comment refusal, R-PHONETICS-OUT, R-NO-ABBREVIATION, R-HONORIFIC-ONCE, framing DENY block |
| `audit_transcript.py` | transcript drift signals (Loop M empirical evidence) |
| `podcast-challenger` Category P | chapter-set design quality: title uniqueness, conciseness, band fit, balance, cross-book bleed |
