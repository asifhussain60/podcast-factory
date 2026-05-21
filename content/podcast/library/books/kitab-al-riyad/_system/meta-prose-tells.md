# Meta-Prose Tells — Kitab al-Riyad (book-specific)

Loaded by `scripts/podcast/build_episode_txt.py` via `load_book_meta_prose_tells(BOOK_DIR)`
and appended to the global `META_PROSE_TELLS` list when validating any chapter or
framing in this book. The global list (in `build_episode_txt.py`) holds generic
author-neutral phrases; this file holds the book's author-specific tells so they
don't bleed across other books.

A "tell" is meta-prose **about the file's authoring process** (translator
clarifications, enrichment scaffolding, pipeline-phase references) — *not*
prose about what the chapter teaches. The italicized chapter prelude (which
declares scope and audience to NotebookLM) is legitimate content; do not add
overly broad phrases that would match it.

Format: one tell per line, prefixed with `- `. Strings are matched case-insensitively
as substrings against the chapter / framing text.

## Tells

- anything al-kirmani only implies
- anything kirmani only implies
- al-kirmani's prose has been clarified
- kirmani's prose has been clarified
- al-kirmani's argument has been simplified
- al-kirmani's vocabulary has been modernized
- this is a paraphrase of al-kirmani
- the translator of al-riyad
- the english rendering of al-riyad
- the refined english of this passage
- arif tamir's 1960 edition
- the editor's footnote at this passage
- the editor's introduction to al-riyad
- compared to the arabic original
- the english reads more smoothly than the arabic
- al-kirmani's other works treat this more fully
- the al-riyad pdf
- the kitab al-riyad source file
