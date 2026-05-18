# Additional Recommendations for Domain-Agnostic Podcast Generation

## Core principle

The podcast skill should not care whether the source is a novel, Qur'an, Bible, hadith collection, Ismaili majlis, technical document, memoir entry, article, transcript, or scanned book. It should always run the same first step: classify the content and place it in the right library folder.

## Genre-aware but pipeline-consistent

After classification, apply genre-specific constraints:

### Scripture

- Preserve verses and references.
- Never paraphrase sacred text as if it were the source text.
- Separate translation, commentary, and application.
- Include pronunciation and term guide.

### Hadith and religious reports

- Track source, chain if available, authenticity rating if known, and variant wording.
- Do not present uncertain reports as authoritative.
- Keep narrator/source metadata visible.

### Ismaili / Fatimid sources

- Preserve Imam names, titles, and doctrinal terms.
- Distinguish zahir, batin, ta'wil, imamate, da'wa, intellect, soul, hierarchy, and cosmology terms.
- Do not flatten theological precision into generic spirituality.

### Novels

- Preserve plot sequence.
- Avoid spoilers outside the selected source range.
- Explain themes without giving away later turns.
- Keep character names and relationships straight.

### Technical documents

- Preserve procedural accuracy.
- Use diagrams and examples.
- Separate explanation from implementation instructions.

### Memoir / personal writing

- Preserve user voice.
- Do not over-polish emotional material.
- Keep derived podcast scripts separate from source prose.

## Podcast output layers

For every source, generate:

```text
01_source_context.md
02_raw_text_or_translation.md
03_glossary.md
04_pronunciation_guide.md
05_cross_references.md
06_episode_outline.md
07_notebooklm_audio_prompt.md
08_qc_report.md
```

## Library review before processing

The source should not be processed until a library placement decision is made. The app should ask:

- What is this source?
- What language and script is it in?
- Is it primary or secondary?
- Is it sacred, devotional, scholarly, literary, technical, personal, or mixed?
- Is OCR needed?
- Is translation needed?
- Is it safe to summarize?
- Should it be split by chapter, page, sermon, epistle, verse, report, scene, or argument unit?

## NotebookLM-specific recommendations

- Never upload an entire 800-page corpus as one source if a specific episode covers only one chapter or treatise.
- Create small source bundles.
- Include an explicit “do not discuss outside this source range” instruction.
- Include a pronunciation guide.
- Include a short source-context file but keep it separate from the raw translation.
- For religious texts, include “do not modernize doctrine unless asked” and “do not invent cross-references.”

