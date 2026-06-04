# Podcast Episode Registry — Kitab al-Riyad

Author: **Hamid al-Din Ahmad ibn Abdullah al-Kirmani** (d. ca. 411/1020), Hujjat al-Iraqayn, senior Da'i of the Fatimid Imam-Caliph al-Hakim bi-Amr Allah.
Source: `_system/source/text/` (Azure-OCR'd Arabic → English-refined transcript; verbatim PDF at `_system/source/`). Content range pages 52–232 (body only; editorial front/back matter excluded per `_system/source/text/content-range.md`).
Segmentation: 15 episodes matching the orchestrator-shipped chapter layout (one episode per `chapters/chNN-<slug>.txt`). An earlier re-segmentation plan to 13 episodes (consolidating Bāb 1 into 3 and Bāb 9 into 2) was authored but never re-applied downstream; the registry realignment on 2026-05-23 restores registry truth to match the actual `chapters/` and `episodes/` contents on disk. See `_system/source/text/_chunks/0d/sc-NNN.rationale.md` for the original Phase 0d rationale.
Architecture: v3.5 (chapter-as-source; phonetics in customize prompt only). Length tier: extended (5500–9500 words/chapter).

Slide-deck enhancement (2026-05-23): four new columns added — `slide-deck-status` (pending / ready / uploaded / not-needed), `slide-deck-justification` (only when status = not-needed), `challenger-status` (pass / fail-iterating / not-run), `backfill-batch` (blank for KaR; this series runs forward-mode-with-default-on-slide-decks rather than retroactive backfill per the 2026-05-23 decision). `validate_registry.py` tolerates extra columns; the canonical `Status` column above continues to drive the existing pipeline.

| EP# | Title | Slug | Source Type | Status | Date Started | NotebookLM URL | slide-deck-status | slide-deck-justification | challenger-status | backfill-batch |
|-----|-------|------|-------------|--------|--------------|----------------|-------------------|--------------------------|-------------------|----------------|
| 01  | The Perfect and the Perfection of the Soul | the-perfect-and-the-perfection-of-the-soul | book-chapter | draft | 2026-05-20 | (pending) | pending |  | not-run |  |
| 02  | Soul, Intellect, and the Power of Emanation | soul-intellect-and-the-power-of-emanation | book-chapter | draft | 2026-05-20 | (pending) | pending |  | not-run |  |
| 03  | The Soul in Time and the Rejoinder to The Defense | the-soul-in-time-and-the-rejoinder-to-al-nusra | book-chapter | draft | 2026-05-20 | (pending) | pending |  | not-run |  |
| 04  | On the Perfection of the Soul: Unified Summary | summary-perfection-of-the-soul | book-chapter | draft | 2026-05-20 | (pending) | pending |  | not-run |  |
| 05  | The Intellect as the First Creation | the-intellect-as-the-first-creation | book-chapter | draft | 2026-05-20 | (pending) | pending |  | not-run |  |
| 06  | Soul and Spirit: One Substance or Two? | soul-and-spirit-one-substance-or-two | book-chapter | draft | 2026-05-20 | (pending) | pending |  | not-run |  |
| 07  | Souls: Parts of the First Truths, or Only Traces? | souls-as-parts-or-traces | book-chapter | draft | 2026-05-20 | (pending) | pending |  | not-run |  |
| 08  | The Human as Fruit of the Worlds | the-human-as-fruit-of-the-worlds | book-chapter | draft | 2026-05-20 | (pending) | pending |  | not-run |  |
| 09  | Motion, Stillness, Prime Matter, and Form | motion-stillness-hyle-and-form | book-chapter | draft | 2026-05-20 | (pending) | pending |  | not-run |  |
| 10  | The Sections of the World | the-sections-of-the-world | book-chapter | draft | 2026-05-20 | (pending) | pending |  | not-run |  |
| 11  | Qada and Qadar: Fate and Destiny | qada-and-qadar-fate-and-destiny | book-chapter | draft | 2026-05-20 | (pending) | pending |  | not-run |  |
| 12  | The Shari'ah of Adam and the First Speaker | the-shariah-of-adam-and-the-first-speaker | book-chapter | draft | 2026-05-20 | (pending) | pending |  | not-run |  |
| 13  | Prophets as Teachers, Monotheism, and the Ranks | prophets-as-teachers-monotheism-and-the-ranks | book-chapter | draft | 2026-05-20 | (pending) | pending |  | not-run |  |
| 14  | Monotheism and the Critique of The Harvest | tawhid-and-the-critique-of-al-mahsul | book-chapter | draft | 2026-05-20 | (pending) | pending |  | not-run |  |
| 15  | Kitab al-Riyad: Book Summary | book-summary | book-chapter | draft | 2026-05-20 | (pending) | pending |  | not-run |  |
