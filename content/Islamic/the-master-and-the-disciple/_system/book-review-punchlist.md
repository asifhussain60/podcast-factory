# Reading-edition review punch list — The Master and the Disciple

Asif's review findings on the rendered PDF (started 2026-06-11). Items are
fixed in batch after the review pass completes; each fix re-renders the PDF
locally (no pipeline re-run).

| # | Status | Finding | Fix sketch |
|---|---|---|---|
| 1 | OPEN | Arabic renders in the default system font — not a proper naskh face. Asif expects Amiri, Traditional Arabic Bold, or the Quran.com face (KFGQPC Uthmanic Script HAFS) | Add @font-face + `[lang=ar]`/Arabic-block font stack in the book render theme CSS used by build_book_pdf.py's Playwright render; embed the font file so the PDF is portable |
