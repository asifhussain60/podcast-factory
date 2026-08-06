# Podcast — Spiritual Ethos

**Source:** *Spiritual Ethos* by Reza Shah-Kazemi.

**Slug:** `spiritual-ethos` · **Category:** `books` · **Architecture:** v3.5 (chapter-as-source; phonetics in customize prompt only).

## Folder layout

Canonical shape is established by this script (`scripts/podcast/scaffold_book.py`) and the kitab-al-riyad worked example under `content/Islamic/kitab-al-riyad/`. The full tree is reproducible from those references — this README is the book-specific blurb only.

## Upload checklist (per episode)

1. Upload `chapters/ch##-<slug>.txt` to NotebookLM as the **single source**.
2. Paste contents of `episodes/EP##-<slug>.txt` into NotebookLM's **Customize prompt** box.
3. Click *Generate*.
4. After audio renders: transcribe via Azure Speech-to-Text (`scripts/podcast/transcribe_episode.py`) or any external service, drop the transcript at `transcripts/EP##-<slug>.transcript.txt`, then run `audit_transcript.py <BOOK_DIR> EP##-<slug>`.
