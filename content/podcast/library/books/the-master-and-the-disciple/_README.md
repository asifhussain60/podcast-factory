# Podcast — The Master and the Disciple

**Source:** *The Master and the Disciple* by Ja'far ibn Mansur al-Yaman.

**Slug:** `the-master-and-the-disciple` · **Category:** `books` · **Architecture:** v3.5 (chapter-as-source; phonetics in customize prompt only).

## Folder layout

Per `content/podcast/.skill/handbook/book-dir-layout.md`. The full tree is documented there — this README is the book-specific blurb only.

## Upload checklist (per episode)

1. Upload `chapters/ch##-<slug>.txt` to NotebookLM as the **single source**.
2. Paste contents of `episodes/EP##-<slug>.txt` into NotebookLM's **Customize prompt** box.
3. Click *Generate*.
4. After audio renders: transcribe via TurboScribe, drop the transcript at `turboscribe/EP##-<slug>.transcript.txt`, then run `audit_transcript.py <BOOK_DIR> EP##-<slug>`.
