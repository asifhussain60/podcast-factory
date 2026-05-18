# Journal App Instructions for Genre-Agnostic Podcast Source Processing

## Primary architectural rule

The journal app must remain file-first for source content. Do not move book text, translations, podcast scripts, Qur'an/Bible excerpts, hadith, Ismaili sources, or memoir/source prose into a database as the source of truth. Databases may be used only for derived indexes, search metadata, embeddings, processing status, queue state, and cross-reference graph edges.

## First step for every upload: library placement review

Before OCR, translation, enhancement, or podcast generation, the app must perform an intake classification pass.

Required intake fields:

- `source_id`
- original filename
- detected language(s)
- script(s)
- genre
- domain
- religious tradition if applicable
- source status
- OCR status
- translation status
- copyright/licensing status
- recommended library folder
- whether source is primary, secondary, devotional, commentary, scripture, fiction, non-fiction, memoir, historical, legal, philosophical, or mixed

Recommended folder taxonomy:

```text
library/
  sources/
    islamic/
      quran/
      hadith/
      tafsir/
      philosophy/
      ethics_and_spiritual_counsel/
    ismaili/
      imamate/
      ta_wil_and_esotericism/
      majalis/
      philosophy_and_theology/
      devotional/
      history_and_adab/
      questions_and_answers/
      notes_and_lessons/
    comparative_religion/
      bible/
      quran_bible_comparison/
    novels/
    nonfiction/
    articles/
    scanned_unclassified/
```

The app should classify the source into the most specific folder, then create a `source.yaml` manifest before any transformation.

## Canonical processing state machine

Every source must move through these states:

1. `INGESTED`
2. `CLASSIFIED`
3. `TEXT_LAYER_CHECKED`
4. `OCR_REQUIRED` or `TEXT_EXTRACTED`
5. `OCR_DRAFTED`
6. `OCR_VERIFIED`
7. `RAW_TRANSLATION_DRAFTED`
8. `RAW_TRANSLATION_QC_PENDING`
9. `RAW_TRANSLATION_VERIFIED`
10. `CONTEXT_LAYER_CREATED`
11. `PODCAST_READY`
12. `NOTEBOOKLM_PACKAGED`

Never skip from scanned PDF to podcast output.

## OCR pipeline

Use this routing logic:

1. Run a text-layer check using PyMuPDF or pdfminer.six.
2. If the page has a good text layer, extract it and preserve page anchors.
3. If text layer is missing or garbage, convert pages to images using Poppler.
4. Preprocess images using OpenCV and/or unpaper.
5. OCR with an engine selected by language and quality.
6. Produce a confidence report.
7. Run normalization for Arabic script.
8. Save raw OCR exactly as produced.
9. Save cleaned OCR as a derived layer.
10. Compare OCR against any existing text layer if one exists.

Required page anchors:

```text
[[SRC-001:p0001]]
Arabic or original OCR text here.

[[SRC-001:p0002]]
Arabic or original OCR text here.
```

Do not remove page anchors during translation.

## Arabic OCR normalization rules

After OCR, normalize in a separate derived file only:

- Normalize Arabic presentation forms.
- Normalize alef variants only when safe.
- Preserve hamza where present.
- Preserve Qur'anic or devotional wording in the raw layer.
- Do not silently remove diacritics. Create a diacritic-stripped search layer separately.
- Preserve paragraph boundaries when possible.
- Detect footnotes and marginalia separately.
- Detect poetry, isnad chains, citations, Qur'anic quotations, hadith quotations, and section headings.

## Raw translation rules

The first English translation must be literal and complete. It is not a podcast script.

Required rules:

- Translate every paragraph in order.
- Preserve page anchors.
- Preserve numbered lists and headings.
- Preserve honorifics and names.
- Preserve Qur'anic verses and hadith references as references, not invented citations.
- Keep ambiguous terms in transliteration with a bracketed literal gloss.
- Do not simplify philosophical, theological, or legal arguments.
- Do not add modern interpretation during raw translation.
- Do not omit repetitive phrases just because they sound redundant.
- Do not merge multiple Arabic paragraphs unless the OCR clearly broke one paragraph by mistake.

Output file:

```text
raw_translation_en.md
```

## Translation quality control

For every translated source, create `translation_qc.md` containing:

- OCR confidence summary
- pages with low confidence
- unresolved terms
- uncertain proper nouns
- religious terms requiring glossary entries
- possible missing pages
- duplicated pages
- likely footnote handling problems
- hallucination risk notes
- human review checklist

## Context layer rules

After raw translation exists, create a context layer. This is where the app may explain, summarize, and organize.

Create these derived files:

```text
source_context_en.md
concept_map.md
glossary.md
pronunciation_guide.md
cross_reference_candidates.md
notebooklm_audio_brief.md
```

The context layer must identify:

- what the source is
- author or attributed tradition
- historical period if known
- genre
- intended audience
- structure
- central themes
- key arguments
- vocabulary
- religious or philosophical terms
- source limitations
- how it should and should not be used in podcasts

## Podcast skill must be genre-agnostic

The `/podcast` skill must first classify the material, then choose the processing strategy. It must not assume all sources are books, novels, memoirs, Islamic texts, or technical documents.

Supported genres:

- Islamic classical texts
- Qur'an, tafsir, hadith, Ismaili ginan/qasida/majalis materials
- Bible and comparative scripture
- novels
- memoirs
- technical documentation
- articles
- lecture transcripts
- images and scanned books
- video/audio transcripts
- research papers
- business documents

For every genre, use the same invariant pipeline:

```text
intake classification -> library placement -> extraction/OCR -> raw text -> raw translation if needed -> context layer -> augmentation -> podcast package -> NotebookLM brief
```

## NotebookLM audio preview packaging

NotebookLM works best when it receives a clean, focused, structured source bundle rather than noisy OCR or a massive unsegmented book.

For each episode, generate:

1. `notebooklm_source.md` — cleaned raw translation or source text.
2. `episode_context.md` — source background and framing.
3. `pronunciation_guide.md` — Arabic/Sanskrit/Hebrew/Urdu/Greek/etc. terms.
4. `podcast_instruction.md` — tone, structure, exclusions, spoiler policy, and audience.
5. `citation_map.md` — source anchors back to pages.

NotebookLM instruction pattern:

- Keep the introduction brief.
- Stay faithful to the source.
- Do not over-explain background noise.
- Do not reveal later conclusions at the beginning.
- Explain terms only when needed for listener comprehension.
- Maintain the original genre tone.
- For religious material, avoid casual jokes and avoid flattening doctrine into generic spirituality.
- For novels, do not spoil later events beyond the selected source range.
- For technical material, preserve accuracy over entertainment.

## Cross-book reference and augmentation

Build a derived index with:

- source IDs
- page anchors
- topics
- people
- places
- scripture references
- doctrinal terms
- hadith IDs
- quote IDs
- embeddings
- translation status
- podcast usage status

Recommended derived stores:

- SQLite FTS5 for local full-text search
- FAISS for local vector search
- optional PostgreSQL + pgvector for larger deployments
- optional graph layer for relationships between texts, concepts, Imams, verses, hadith, and themes

Core text remains in files.

## Red-Green-Refactor convergence loop

For every new capability:

### Red

Write tests first:

- source manifest validation
- duplicate source ID detection
- page-anchor preservation
- OCR output creation
- raw translation output creation
- NotebookLM package creation
- no raw source overwrite
- no podcast generated from unverified OCR

### Green

Implement the narrowest working pipeline.

### Refactor

Clean redundant scripts, dead links, old prompt copies, and legacy paths. Run full regression checks.

## Non-regression gates

No PR should pass unless:

- existing memoir and trip flows still work
- file-first invariant remains intact
- raw source files are never overwritten
- all derived outputs are traceable to source anchors
- OCR and translation status are explicit
- NotebookLM files do not contain unverified OCR
- generated podcasts cite source bundles, not vague memory
- Islamic and scripture content is not paraphrased before raw translation exists

