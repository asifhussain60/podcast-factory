# Meta-Prose Tells — Ayyuhal Walad (book-specific)

Loaded by `scripts/podcast/build_episode_txt.py` via `load_book_meta_prose_tells(BOOK_DIR)`
and appended to the global `META_PROSE_TELLS` list when validating any chapter or
framing in this book. The global list (in `build_episode_txt.py`) holds generic
author-neutral phrases; this file holds the book's author-specific tells so they
don't bleed across other books.

Format: one tell per line, prefixed with `- `. Strings are matched case-insensitively
as substrings against the chapter / framing text. Quotes around a tell are stripped.

## Tells

- anything ghazali only implies
- ghazali's prose has been clarified
