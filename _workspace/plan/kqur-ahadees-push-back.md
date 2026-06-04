# KQUR Ahadees Push-Back — Investigation Findings

**Date:** 2026-05-30  
**Status:** Complete (read-only investigation; no DB writes made)

---

## Schema discovery

The `wisdom-mssql` Docker container was offline during this session, so `SELECT TOP 1 * FROM Ahadees` could not run. Column names in `source_library_mirror._SQL_HADITH` remain guesses.

**Action required:** start wisdom-mssql, then run:
```bash
python3 scripts/podcast/produce_bilingual.py --slug ayyuhal-walad --discover-hadith-schema
```
Update the aliases in `_SQL_HADITH` if any name differs from `AhadeesID / CollectionName / HadithNumber / ArabicText / EnglishText`.

---

## Architecture finding: KQUR is read-only by design

`tools/source_extractor/db.py` is the only transport to KQUR. It runs `SELECT ... FOR JSON PATH` queries via `docker exec sqlcmd`. There is **no write path** — no INSERT, no UPDATE, no stored-procedure call. All `scripts/wisdom/queries/` are read-only SELECTs.

**Recommendation: do not add write access to KQUR from the pipeline.** KQUR is a curated, authoritative reference DB. Canonical hadith collections (Bukhari, Muslim, etc.) are fixed corpora — the pipeline discovering a hadith in a book doesn't mean it should be appended to that collection. Adding write access introduces risk (accidental data corruption, schema drift) with low benefit.

---

## Where new hadith should go: the local atoms DB

The pipeline already has its own write target: the local SQLite atoms DB defined in `scripts/podcast/schema/001_atoms.sql`. It is designed for exactly this:

```sql
-- type='hadith', body JSON carries collection, number, arabic, english
INSERT INTO atoms (id, type, body, first_seen_book, first_seen_chapter, confidence)
VALUES ('hadith:bukhari:6502', 'hadith', '{"arabic":"...", "english":"...", "collection":"bukhari", "num":6502}',
        'ayyuhal-walad', 'ch01-frame-and-first-counsel', 0.85);
```

`schema/011_external_corpora.sql` defines `external_corpora` and `corpus_chapters` as **read-only reference tables populated at init time** — confirming the design intent: pipeline reads from KQUR, writes to its own atoms store.

---

## Proposed push-back pattern (local atoms, not KQUR)

| Step | Who | What |
|---|---|---|
| Hadith detected in book | Knowledge stage | `knowledge-report.json` entry with `text_en`, confidence |
| KQUR match attempted | `hadith_lookup()` | FTS search → if matched, Arabic text returned |
| Unmatched hadith | Pipeline | Write to local atoms with `status=pending_review`, `confidence < 0.9` |
| Human review (Studio) | Asif | Confirm Arabic text, assign collection + number |
| Confirmed atom | Studio write-back | Update local atoms to `confidence=1.0`, add `collection` + `num` fields |
| Next book processes | `hadith_lookup()` | Now finds it in local atoms mirror — Arabic text available |

**Dedup check:** `id` is the primary key in atoms (e.g., `hadith:bukhari:6502`). For unverified hadith with no collection:number, use a SHA-256 of the normalised Arabic text as the id (`hadith:unverified:<hash>`). Prevents duplicate inserts on re-run.

---

## Optional: flag KQUR gaps for DBA review

If a matched hadith is confirmed canonical (Bukhari, Muslim, Tirmidhi, etc.) but is **absent from KQUR**, write it to a human-review queue file (`_workspace/plan/kqur-gaps.md`). Asif or a DBA can decide whether to add it to KQUR manually. The pipeline never writes to KQUR directly.

---

## Pipeline phase that triggers this

**After the knowledge stage** (currently Phase 0h in the orchestrator). The knowledge stage already produces `knowledge-report.json` with `hadith_refs`. The push-back step:
1. Attempts `hadith_lookup()` for each ref
2. Writes matched results as atoms (confidence from lookup score)
3. Writes unmatched refs as pending atoms for Studio review
4. Flags canonical-but-missing entries for the KQUR gaps file

Script: `scripts/podcast/ingest_hadith_atoms.py` (to be built as part of Phase B5).
