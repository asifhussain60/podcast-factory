# Canonical BOOK_DIR Layout

**Authoritative status:** Normative. Every podcasted source under `content/podcast/library/<category>/<book-slug>/` MUST follow the shape defined here. `scripts/podcast/scaffold_book.py` creates this layout in one shot; any deviation should be reconciled.

A `<category>` is one of: `books`, `articles`, `documents`, `lectures`, `interviews`, `letters`. A `<book-slug>` is kebab-case, ≤40 chars, unique under its category.

## Tree

```
content/podcast/library/<category>/<book-slug>/
├── _README.md book-specific blurb + upload checklist
├── chapters/ ← SOURCE files (uploaded to NotebookLM as-is)
│ ├── ch01-<slug>.txt
│ ├── ch02-<slug>.txt
│ └──...
├── chapter-contracts/ ← the signed contract per chapter
│ ├── <slug>.yml
│ └──...
├── episodes/ ← CUSTOMIZE PROMPT files (paste into NotebookLM Customize box)
│ ├── EP01-<slug>.txt
│ ├── EP02-<slug>.txt
│ └──...
├── transcripts/ ← human-input only (NotebookLM Audio Overview transcripts)
│ ├── _README.md
│ ├── EP01-<slug>.transcript.txt
│ └──...
└── _system/ ← authoring metadata, never uploaded
 ├── registry.md ← per-book episode index
 ├── _README.md ← (optional) book authoring notes
 ├── pronunciation.md ← per-book phonetic overrides
 ├── mangle-map.md ← per-book NotebookLM TTS mangling map
 ├── meta-prose-tells.md ← per-book author-specific meta-prose tells
 ├── enrichment-whitelist.md ← Tier 1 author's-own-corpus (per book)
 ├── enrichment-log.md ← per-chapter enrichment status + provenance
 ├── concept-glossary.md ← (optional) per-book conceptual term inventory
 ├── challenger-report.md ← latest podcast-challenger output
 ├── scratchpad/
 │ └── series-policies.md ← Tier-3 @@policy markers (series-wide)
 ├── source/
 │ ├── <Source-Title>.<ext> verbatim original (audit anchor; never modified)
 │ └── text/
 │ ├── normalized.md Phase 0a output (one cleaned source file)
 │ ├── _phonetics.md Phase 0c index
 │ ├── chapters-rationale.md Phase 0d segmentation rationale
 │ └── content-range.md (optional) body-page declaration: skip editor's apparatus + indexes
 └── episode-drafts/
 ├── EP01-<slug>/
 │ ├── 00-framing.md CUSTOMIZE PROMPT body
 │ ├── 02-key-passages.md
 │ ├── 03-context-pack.md
 │ ├── 04-discussion-spine.md
 │ ├── 99-show-notes.md (optional)
 │ └── chapter.scratch.md refinement surface mirroring chapters/ch01-<slug>.txt
 ├── EP02-<slug>/
 └──...
```

## What each file/folder owns

| Path | Owner | Read by | Written by |
|---|---|---|---|
| `_README.md` | the book | humans | author (manual) |
| `chapters/ch##-<slug>.txt` | the book — **the SOURCE** | NotebookLM (uploaded as-is); `build_episode_txt.py`; `podcast-challenger` | author (Phase 0d/0e); refinement pass |
| `chapter-contracts/<slug>.yml` | the book — Extract Mode contract | `extract_chapter.py`; `podcast-challenger` (Category G + P) | author; `extract_chapter.py` stub generator |
| `episodes/EP##-<slug>.txt` | the book — **the CUSTOMIZE PROMPT** | humans paste into NotebookLM | `build_episode_txt.py` (never hand-edit) |
| `transcripts/EP##-<slug>.transcript.txt` | the book — episode transcript | `audit_transcript.py`; `podcast-challenger` Loop M | human (manual drop) |
| `_system/registry.md` | the book | `validate_registry.py`; humans | `new_episode.py`; author |
| `_system/pronunciation.md` | the book — phonetic overrides | `build_episode_txt.py` (via `_rules`); `podcast-challenger` | author |
| `_system/mangle-map.md` | the book — TTS mangling overrides | `audit_transcript.py:load_book_mangle_map` | author |
| `_system/meta-prose-tells.md` | the book — author-specific tells | `build_episode_txt.py:load_book_meta_prose_tells` | author |
| `_system/enrichment-whitelist.md` | the book — Tier 1 corpus | `podcast-challenger` enrichment audit | author |
| `_system/enrichment-log.md` | the book — chapter status + verification notes | `podcast-challenger` | author |
| `_system/concept-glossary.md` | the book — per-book conceptual term inventory (optional) | Phase 11 framing authoring; `podcast-challenger` Category P | author (manual, claude-p, or extract) |
| `_system/challenger-report.md` | the book — latest challenger output | humans (verdict + findings) | `podcast-challenger` |
| `_system/scratchpad/series-policies.md` | the book — Tier-3 `@@policy` markers | refinement pass | scratchpad processing |
| `_system/source/<Source-Title>.<ext>` | the book — verbatim original | audit anchor | author (one-time drop) |
| `_system/source/text/normalized.md` | the book — Phase 0a output | Phase 0c–0e | Phase 0a |
| `_system/source/text/_phonetics.md` | the book — phonetic index | Phase 0d–0e + framing authoring | Phase 0c |
| `_system/source/text/chapters-rationale.md` | the book — segmentation rationale | humans, `podcast-challenger` Category P | Phase 0d |
| `_system/source/text/content-range.md` | the book — body-page declaration (optional) | Phase 0d (segmentation), Phase 0e (enrichment), Phase 11 (framing), Loop N | operator (via P22 review), or pre-authored alongside Phase 0d preflight |
| `_system/episode-drafts/EP##-<slug>/00-framing.md` | the episode — the source of CUSTOMIZE PROMPT | `build_episode_txt.py` | author (Phase 3) |
| `_system/episode-drafts/EP##-<slug>/02-key-passages.md` | the episode | humans, refinement | author |
| `_system/episode-drafts/EP##-<slug>/03-context-pack.md` | the episode | humans, refinement | author |
| `_system/episode-drafts/EP##-<slug>/04-discussion-spine.md` | the episode | humans, refinement | author |
| `_system/episode-drafts/EP##-<slug>/99-show-notes.md` | the episode | humans (post-render) | author (optional) |
| `_system/episode-drafts/EP##-<slug>/chapter.scratch.md` | the episode — refinement surface | refinement pass | author (drops `@@` markers); stripped after each pass |

## Strict shape rules

- **Empty folders are not required** to exist on disk. `chapter-contracts/` and `_system/scratchpad/` may not exist until needed; scripts create them lazily.
- **No `01-source-primary.md`** anywhere. Under v3.5 the chapter file IS the source; there is no separate source-primary file in the draft folder.
- **One slug per chapter, slug-identical across surfaces.** `chapters/chNN-<slug>.txt` ↔ `chapter-contracts/<slug>.yml` ↔ `_system/episode-drafts/EP##-<slug>/` ↔ `episodes/EP##-<slug>.txt` ↔ `transcripts/EP##-<slug>.transcript.txt`. `build_episode_txt.py` enforces the match by slug.
- **Per-book overrides MAY add, NEVER contradict the shared manifest.** `pronunciation.md`, `mangle-map.md`, `meta-prose-tells.md`, `enrichment-whitelist.md` extend their shared/canonical counterparts; they never override a globally-canonical entry. The challenger's Category P6 (cross-book bleed) backstops this.

## Per-book concept glossary

The optional file `_system/concept-glossary.md` is a per-book inventory of technical vocabulary the listener must acquire across episodes. It is **distinct** from neighboring artifacts:

| Artifact | What it captures |
|---|---|
| `pronunciation.md` | phonetic guides per term (how to say it) |
| `mangle-map.md` | TTS mangling overrides (NotebookLM voice fixes) |
| `concept-glossary.md` | one-sentence listener-gloss per term (what it MEANS) |

When present, the per-episode framing author (Phase 11) reads it: Episode 1 introduces ~8-10 foundational terms; Episode 2+ references "see glossary terms already established in Ep1" rather than re-defining. The `podcast-challenger` Category P gains one check — if the file exists, every framing must reference ≥1 glossary term OR declare zero-new-vocab.

### Schema

```yaml
schema_version: 1
book_slug: <slug>
generated_by: <human | claude-p | extract>
generated_at: <ISO 8601 timestamp>
purpose: |
  Per-book inventory of technical vocabulary that the listener must
  acquire across episodes. Distinct from pronunciation.md (phonetic) and
  mangle-map.md (TTS-fix). This file is CONCEPTUAL: a one-sentence
  listener-gloss per term.
```

### Body shape

Bulleted terms grouped by domain. Example:

```markdown
## Cosmology
- **natiq** (ناطق): a "speaker prophet" who inaugurates a cosmological cycle.
- **asas** (أساس): the "foundation" — the figure who carries the inner meaning.
- **hujja** (حجة): "proof" — the senior teacher under the imam.

## Hermeneutics
- **ta'wil** (تأويل): allegorical interpretation returning a thing to its first principle.
- **zahir** (ظاهر): the outer/manifest meaning of scripture.
- **batin** (باطن): the inner/hidden meaning — what ta'wil discloses.
```

When the file is **absent**, episodes run as today — no challenger check fires. Adoption is opt-in per book.

## Per-book content range

The optional file `_system/source/text/content-range.md` declares which PDF pages of the refined English transcript contain the actual book — excluding editor's intros, modern bibliographies, and indexes. Edited Arabic / philosophical / religious sources routinely add 10-25% of front matter and 10-15% of back matter that listeners don't need; without this declaration the orchestrator wastes LLM token spend on Phases 0c/0e/11 refining material that won't appear in any episode.

Distinct from neighboring artifacts:

| Artifact | What it captures |
|---|---|
| `chapters-rationale.md` | Phase 0d's segmentation rationale + chapter map |
| `_phonetics.md` | Phase 0c phonetic index |
| `content-range.md` | Which pages are body content vs. editor's apparatus + back matter |

When present, Phase 0d drops sections outside the range from `chapters-rationale.md` and `chapters/chNN-*.txt`. Phase 0e (enrichment) and Phase 11 (per-chapter framing) only see body content. Loop N skips numeric claims in front/back-matter ranges (editor's bibliographic lists are not the source author's own enumerations).

### Schema

```yaml
schema_version: 1
book_slug: <slug>
generated_by: <human | claude-p | operator-review>
generated_at: <ISO 8601 timestamp>
body_starts_at_page: <int>       # PDF page where the source author's own preface or body opens
body_ends_at_page: <int>         # PDF page where the body's last section ends
include_author_preface: true|false  # author's own preface (NOT editor's) — usually true
include_author_toc: false           # author's own table-of-contents page — usually false (structural-only)
front_matter_summary: |
  One-line description of what the front matter contains. Listeners don't need this.
back_matter_summary: |
  One-line description of what the back matter contains. Listeners don't need this.
```

Pages are anchored to `<!-- page N -->` breadcrumbs which Phase 0a injects and which survive refinement. Line numbers are NOT used — they shift with reflow.

### Worked example — Kitab al-Riyad

```yaml
schema_version: 1
book_slug: kitab-al-riyad
body_starts_at_page: 52      # al-Kirmani's own preface opens here
body_ends_at_page: 232       # Bāb 10's last section ends here
include_author_preface: true
include_author_toc: false    # al-Kirmani's TOC is structural-only
front_matter_summary: "Pages 1-51: Editor Arif Tamir's 1960 Introduction — bios of al-Razi/al-Sijistani/al-Kirmani; editing notes (mss A and B); editor's TOC summary."
back_matter_summary: "Pages 233-254: six indexes — subject, Qurʾānic verses, manuscripts, message, names, places."
```

This drops 29% of the file from downstream LLM-token spend on KaR alone.

### How content_range is captured

`content-range.md` is typically authored at the P22 operator-review gate: the orchestrator surfaces the paginated transcript, the operator skims to find where the editor's apparatus ends and the author's voice opens, and declares the range in operator-review.md §7. The orchestrator then emits `content-range.md` from that declaration before resuming Phase 0c.

For books with hand-authored preflight (e.g. Asaas al-Taʾwīl), `content-range.md` can be authored alongside `chapters-rationale.md` as a Phase 0d preflight artifact — the operator-review gate then confirms rather than authors.

When the file is **absent**, behavior is unchanged — the whole `refined-english.md` flows into Phase 0d as today. Adoption is per-book and opt-in.

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
