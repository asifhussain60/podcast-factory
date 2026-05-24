# Podcast — An Introduction to Statistical Learning (ISL2) — MAS-I Subset

**Source:** *An Introduction to Statistical Learning*, 2nd Edition (Springer 2021) by Gareth James, Daniela Witten, Trevor Hastie, Robert Tibshirani. **Born-digital** (TeX-generated), 612 pages. **Upstream canonical path:** `~/Library/CloudStorage/GoogleDrive-asifhussain60@gmail.com/My Drive/BOOKS/Textbooks/James-G.-et-al.-2nd-edition-Springer-2021.pdf` (md5 `e1ae3b1657be89f99e342909677862f7`). A verbatim local copy lives at [`_system/source/ISL2_James_et_al_2021.pdf`](_system/source/) for repository self-containment.

**Slug:** `islr-mas-i` · **Category:** `books` · **Architecture:** v3.5 (chapter-as-source; phonetics in customize prompt only).

**Audience:** an actuarial student who has passed SOA Exams P and FM and is preparing for **MAS-I** (Modern Actuarial Statistics I). Listening mode: **casual walking-listen** — theory-heavy, qualitative, formulas referenced but not drilled.

## What makes this book different from the rest of the library

Every other book under [library/books/](../) (`asaas-al-taveel`, `kitab-al-riyad`, `ayyuhal-walad`, `the-master-and-the-disciple`) and [library/lectures/](../../lectures/) is a **classical Islamic religious text** — Ismaili esoteric exegesis, Sufi pedagogy, Fatimid cosmology. The pipeline's mandatory pre-reads, enrichment pool, phonetics index, and Loop N numeric-disambiguation protocol are calibrated for that domain.

ISL2 is a **secular STEM textbook**. The pipeline's structural invariants survive untouched (chapter design > source promotion; concise unique titles; per-chapter contracts; build/extract/challenger/ship cycle), but three content surfaces need re-fueling: **Phase 0a source-ingest path**, **Phase 0c phonetics lookup pool**, and **Phase 0e enrichment whitelist**. See [`_system/integration-analysis.md`](_system/integration-analysis.md) for the deltas and how they fit into the existing architecture without major changes.

## MAS-I scope (what the student is actually tested on)

- Chapter 1 — full
- Chapter 2 — **excluding §2.2.3** (The Classification Setting)
- Chapter 3 — **§3.1–§3.3 only**, plus §3.6 *labs on §3.1–§3.3 only*
- Chapter 4 — **§4.1–§4.4**, *excluding the LDA portion of §4.4* (skip 4.4.1 and 4.4.2; keep QDA 4.4.3 and Naive Bayes 4.4.4)
- Chapter 5 — full
- Chapter 6 — full
- Chapter 7 — full

Section-by-section mapping with PDF page anchors and the 7-episode plan: [`_system/source/text/chapters-rationale.md`](_system/source/text/chapters-rationale.md).

## Folder layout

Per `content/podcast/.skill/handbook/book-dir-layout.md`. Two non-standard preflight artifacts in `_system/`:

- `_system/source/text/ch0N-*.raw.txt` (×7) — `pdftotext -layout` extraction. **Replaces Phase 0a Azure OCR output for this book** (PDF is born-digital, English; Azure would degrade math/formula rendering).
- `_system/jargon-glossary.md` — hard-to-pronounce statistics terms (heteroscedasticity, multicollinearity, etc.) and concept primers. **Replaces the Arabic phonetics surface** for this book; consumed by Phase 0c in place of the SHARED_ARABIC manifest lookups.

## Upload checklist (per episode)

1. Upload `chapters/ch##-<slug>.txt` to NotebookLM as the **single source**.
2. Paste contents of `episodes/EP##-<slug>.txt` into NotebookLM's **Customize prompt** box.
3. Click *Generate*.
4. After audio renders: transcribe via external service (https://transcripts.ai), drop the transcript at `transcripts/EP##-<slug>.transcript.txt`, then run `scripts/podcast/audit_transcript.py <BOOK_DIR> EP##-<slug>`.

## Orchestrator posture (Mode-2 with two book-local bypasses)

This book runs **Mode-2 (orchestrator)**, NOT Mode-3 (Pre-Refined Source Mode), with two bypasses configured at the book level:

1. **Phase 0a bypass** — use `pdftotext -layout` on a born-digital English source. Azure OCR/Translate is skipped. The Azure half of the pre-flight is also skipped for this book. Pre-extracted raw text already lives in `_system/source/text/`.
2. **Enrichment-pool swap (Phase 0e)** — swap the per-book enrichment pool from the library default (Quran / hadith / Imam Ali / Ismaili tradition) to **modern data-science analogies + actuarial-exam context + R/Python ecosystem references**, capped at the existing 60% ceiling. Pool enumerated in `_system/enrichment-whitelist.md`.

Both bypasses are book-local configuration; no skill-spec or handbook edits are strictly required to ship ISL2. The longer-term integration recommendation — adding a reusable `enrichment_pool` axis to the skill — is documented in `_system/integration-analysis.md` §4.
