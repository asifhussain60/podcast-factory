# 03 — Wisdom corpus: KQUR + KASHKOLE + KSESSIONS → one corpus  ✅ CONVERGED

> **STATUS 2026-05-29: design converged with Asif (decisions D1–D6).** This section is the binding outcome; the analysis below is retained as the rationale. No code until the holistic T1+T2+T3 plan entry is written, snapshotted, and approved (plan-first gate).

## Locked decisions (D1–D6)

| # | Decision |
|---|---|
| **D1** | Source lifecycle is MIXED: **KQUR frozen, KASHKOLE frozen** (one-time import, no sync); **KSESSIONS active** (idempotent re-sync required). |
| **D2** | Build a **new purpose-built wisdom corpus** (Option A, strengthened). Intelligently extract ONLY podcast/intelligence-relevant content; aggressive dedup (40%+ overlap KASHKOLE↔KSESSIONS and intra-book); retire originals. Everything injectable but intelligently filtered — no app baggage. NOT a lift-and-shift. |
| **D3** | **KSESSIONS kept** as the live session system-of-record; corpus re-syncs (deduplicated, on-demand) from it. **KQUR + KASHKOLE deleted** after one-time extraction. Retiring KSESSIONS into a single home deferred (would need session-authoring tooling built into the corpus first). |
| **D4** | Corpus engine = **SQLite** (server-less, in-repo, machine-agnostic; matches pipeline + reader + blackbox mirror). SQL Server/Docker dropped for the corpus. The ~6 useful queries re-expressed in Python. KSESSIONS stays SQL Server only as the external source read at sync time. |
| **D5** | **Single tradition.** Auto-stamp by source/content-type: teaching+commentary → `fatimid-ismaili`; raw Quran+hadith text → `universal`. Per-record `tradition` field on every atom (satisfies the locked tradition firewall). No hand-labeling. `universal` = raw text only, no interpretive note (honours audit P7). |
| **D6** | **KQUR is the canonical Quran**; KASHKOLE's duplicate `HQ*` Quran removed with KASHKOLE. |
| **D7** | **Tiered dedup.** High-confidence near-identical → auto-merge into ONE canonical record (most complete/most recent wins; other instances linked as references, not copied). Borderline near-duplicates → manual-review queue for human confirm. Ambiguous cases never auto-merged. Detection combines exact match + semantic/fuzzy similarity. |
| **D8** | **KASHKOLE is NOT retranslated (hard constraint).** Its Urdu is already processed + polished into English (expensive — never redone). Extraction ingests the EXISTING polished English as-is; the Urdu OCR is preserved/stored as a source field but never re-translated. KASHKOLE bypasses Azure Translator entirely. The Turboscribe-Urdu→Azure-Translator path applies ONLY to NEW Urdu lecture intake (e.g. Anwaar), never to KASHKOLE. |
| **D9** | **Wisdom Corpus UI (deferred wave).** The reader's "Kashkole" link is renamed **"Wisdom Corpus"** and gets a fully redesigned view giving Asif keep/delete curation control over corpus records; it also hosts the D7 dedup review/confirm queue. Own wave, discussed later. |

**Still to detail in this doc (build-time, not user decisions):** the extraction map (Q1.4 — resolve TopicData/TopicDataUnicode/TopicSimple, SessionDoctrines vs TopicDoctrines, exclude canvas.*/app-plumbing) and the concrete dedup mechanics (similarity thresholds, canonical-selection rule, link model) implementing D7.

---

**Your assumptions #2/#3:** Three DBs came from three fully-functional apps with stored procedures; you want the trio to *become* the wisdom corpus, merged intelligently without duplication; and you asked how this affects the MCP blackbox.

## What the three databases actually are (verified from the dumps)

| DB | Size | What it really is | Wisdom-bearing tables | App-plumbing tables (NOT corpus) |
|---|---|---|---|---|
| **KQUR** | 15 MB | Quran + Hadith + Arabic etymology engine | `QuranAyats`, `QuranSurahs`, `QuranVerses`, `Roots`, `Derivatives`, `Ahadees`, `Narrators`, `Ahadees*Tags*` | — (clean, almost all corpus) |
| **KASHKOLE** | 724 MB | Topic/binder teaching corpus | `Topics`, `TopicData(Unicode)`, `TopicAyats`, `TopicGlossaries`, `Glossary`, `DeeniTermGroup(Elements)`, `Binders`, `Chapters`, `Lookup_*` | `Emailer_*` (6 tbls), `_Backup_HQAyats`, `HQAyats_BeforeAlifMadUpdate`, `TopicDataSWF` (Flash) |
| **KSESSIONS** | 29 MB | A full community web app | `Sessions`, `SessionSummary`, `SessionTranscripts`, `SessionDoctrines`, `TopicDoctrines` | `Members`, `Groups`, `Families`, `Countries`, `Auth*`, `Audit*`, `*Token*`, `Session{Access,Feedback,Quiz,Images}`, `canvas.*` |

### The decisive finding: Quran is duplicated
KQUR has the Quran in `QuranAyats/QuranSurahs/QuranVerses`. **KASHKOLE has a SECOND complete Quran** in `HQAyats / HQSurahs / HQSurahIndex / HQSurahIndexAyats / HQSurahAyatWords` (+ two backup copies). A naïve merge would carry two Qurans. Any merge MUST pick **one canonical Quran** (recommend KQUR's — it's the etymology-linked one, via `Roots`/`Derivatives` and `GetAyatsByToken`).

### The second finding: most stored procedures are NOT corpus logic
Proc counts: KQUR 30, KASHKOLE 75, KSESSIONS 128. But reading the names:
- KASHKOLE: ~40 are `Admin_*` (backup/restore/migration/reorder) and `Emailer_*` (newsletter). These are **maintenance for the source app**, not corpus query logic.
- KSESSIONS: the large majority are member/auth/token/feedback/access CRUD — **community-app plumbing**.
- The genuinely valuable query logic is a **thin layer**: etymology search + ayat-by-token (KQUR), topic + deeni-term search (KASHKOLE), session summary/transcript retrieval (KSESSIONS).

**That thin layer is exactly what Wave J already started re-expressing as the 6 MCP tools.**

## The reframe (my recommendation)
"Merge the three into one without duplication" is the right *goal*, but lifting-and-shifting three production app databases (with their Flash blobs, emailers, member tables, T-SQL stored procs) into one SQL Server is the wrong *method*. It would import 724 MB of mostly-baggage and duplicate the Quran.

Instead: **define a single, clean, purpose-built wisdom-corpus schema and ingest only the wisdom-bearing subset from each source, deduplicated.** The three SQL Server DBs become the *import source / system-of-record for re-ingestion*, not the runtime corpus.

### Option A — Canonical Wisdom Corpus (RECOMMENDED)
Build one corpus store (SQLite, the existing `knowledge.db` lineage or a dedicated `wisdom.db`) with a clean schema:
- `quran_ayat` (from KQUR, canonical) ← drop KASHKOLE's HQ* duplicate
- `quran_root` + `quran_derivative` (etymology, from KQUR)
- `hadith` + `narrator` (from KQUR)
- `topic` + `topic_ayat` + `topic_term` (from KASHKOLE)
- `glossary_term` + `term_group` (unify KASHKOLE Glossary/DeeniTerm + KQUR roots)
- `session_summary` + `session_transcript` (wisdom subset of KSESSIONS only)
- Provenance column on every row (`source_db`, `source_pk`) so re-ingestion is idempotent and auditable.
The query logic (the useful stored procs) is re-expressed in Python behind the MCP tools — **already the Wave J pattern**.
*Pros:* one source of truth, no duplication, no app baggage, offline-capable, version-controllable. *Cons:* requires writing ingestion adapters per source.

### Option B — Keep 3 DBs, unify ONLY behind the blackbox
Leave the three SQL Server DBs as-is in Docker; the MCP server hides them and dedupes at query time (already roughly the current Wave J direction).
*Pros:* least migration work; preserves stored procs verbatim. *Cons:* the duplication and 724 MB baggage persist; requires Docker + SQL Server always running; no clean "corpus" artifact; the FTS5 mirror (`mirror.db`) becomes the de-facto corpus anyway (and it isn't built yet).

### Option C — Merge into one SQL Server DB (literal reading)
Restore all three into one SQL Server database, reconcile schemas, keep stored procs.
*Pros:* preserves T-SQL logic; matches the literal ask. *Cons:* carries 724 MB + Flash + emailer + member/auth tables into the "corpus"; must still resolve the Quran duplication by hand; heaviest runtime dependency; least aligned with the file-based, offline, machine-agnostic architecture this repo otherwise follows.

## How the merge affects the MCP blackbox (your #3)
**It almost doesn't — and that's the point.** Consumers (reader popovers, intelligence pipeline, agents) only ever see the 6 tools (`quran_lookup`, `quran_theme_search`, `word_etymology`, `topic_search`, `topic_get`, `session_style_fetch`). Whether those resolve against 3 Docker DBs (Option B/C) or one canonical corpus (Option A) is an implementation detail behind the blackbox. So: **decide the corpus architecture freely; the blackbox contract shields every consumer.** The only blackbox change Option A enables is *simplification* — the FTS5 mirror becomes a straight projection of one schema instead of a 3-DB union.

## Open questions for our discussion
1. Is the corpus meant to be **read-only reference** (my assumption) or will you keep *editing* topics/sessions in the original KASHKOLE/KSESSIONS apps and need re-sync? (If you still author in those apps, Option A needs a refresh cadence; if those apps are retired, Option A is a one-time ingest.)
2. Do you need the **stored-proc business logic** preserved as T-SQL, or is re-expressing the ~6 useful queries in Python (the Wave J approach) acceptable? (This is the single biggest fork.)
3. Should `session_transcript` (raw teaching transcripts) be part of the corpus the pipeline draws style from, or kept private?
