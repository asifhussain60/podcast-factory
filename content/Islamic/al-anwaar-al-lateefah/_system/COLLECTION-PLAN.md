# Al-Anwaar al-Lateefah — Collection Build Plan (LOCKED 2026-06-17)

**This document is the source of truth for the al-anwaar build. Do not deviate without Asif's explicit approval.** Supersedes `POST-SYNTHESIS-TASKS.md`.

---

## 1. Context & why this design

`al-anwaar-al-lateefah` is an audio-sourced Ismaili *'uloom-e-haqa'iq* work (recorded Mabda-wa-Maad lessons, taught under *ijazat*). The synthesized merged book is **enormous and dense**: **284,537 words / 3,037 teachings (1 per 93 words), 59% abstract doctrine**. As a single podcast it would be **48–95 episodes / 16–32 hours** — un-listenable and un-completable.

**Listener-POV verdict (Asif-approved):** a **collection of standalone-feeling volumes under one root**, and **curate** what becomes audio (do not air all 3,037 teachings).

## 2. Current state (verified 2026-06-17)

- Branch `Islamic/al-anwaar-al-lateefah` **merged into `develop` and pushed** (merge `e8e5aa98`).
- Capabilities (on develop): `promote_staging_to_book.py`, `multi_source_synthesis.py` (chunked ledgers + 500-retry, `LEDGER_CHUNK_LECTURES=5`), `arabic_integrity.py` (`R-ARABIC-INTEGRITY`, finalize gate **G14**, `MIN_ARABIC_LETTERS=2`), `0a-synthesize` dispatch, 0b/0e Arabic hooks.
- **Synthesis COMPLETE → state `phase=0c`.** `_system/unified-book.md` (284,537 w, 28 H2 sections), unified ledger `_system/source/text/_teaching-ledger.json` (3,037 teachings: 1,093 spine + 1,944 aug), fidelity **1,093/1,093**, Arabic **63 protected spans intact** (49 Quran + 14 hadith), **90 augmentation atom-candidates** emitted.
- **SPINE IS COMPLETE — 65 lectures.** The apparent "missing 61–66 / 69–71" was **original-file naming only**, not missing content (confirmed by Asif). Source mp3s **serialized to `lec01–65`**; map at `_system/source/_serialization-map.json`. Any thin Ma'ad coverage is **filled by the hazrat-zia augmentation** (1980 Mabda-wa-Maad set, 29 lectures / 202 merged teachings, already in the book). **No re-synthesis required.**

## 3. LOCKED design decisions (anti-deviation)

1. **One root, multi-volume "work".** Everything under `content/Islamic/al-anwaar-al-lateefah/` as a work: `work.yml` + `vol-01..05/` (each a normal book dir), **one branch** (`_branching.branch_for_work`), rolled-up status (`_paths.work_rollup_status`). NOT separate top-level books.
2. **Each volume authored to stand alone** — own title, on-ramp, conclusion; a completable ~6–10 episode "season"; presented as the **Al-Anwaar Collection**.
3. **Curate audio; full depth in the reading edition.** Podcasts carry the **spine through-line** (~1,093 spine teachings, breathably paced). The **reading edition (`book.pdf`)** carries the full 3,037-teaching depth. (Listen for the arc; read for detail.)
4. **5 volumes** — the four pillars, the two largest split (mapping in §5).
5. **No re-synthesis** — the merged book at `0c` is the complete work; proceed to volume design.

## 4. Invariants (must hold at every step)

- **Arabic preservation (P0):** `R-ARABIC-INTEGRITY` / G14 — Quran/hadith/term Arabic byte-stable across all LLM passes; changeable ONLY by canonical injection or Astro phonetic-view curation. (Merge already passed: 63 spans intact.)
- **No teaching lost:** fidelity 100% spine coverage at full depth (1,093/1,093).
- **All augmentation accounted for:** every aug span merged-inline / atom-candidate / dropped-as-noise (`_curation-log.md` + `_atom-candidates.jsonl`); only genuine audio noise dropped.
- **No repetition within OR across volumes:** every teaching ID → exactly ONE volume + ONE episode (enforced at 0d chapter design).
- **Density per NotebookLM:** breathable (~3,000–4,000 source words/ep for this dense content); never crammed; `episode_count ≥ ⌈words/ceiling⌉`.

## 5. Volume structure (5 volumes, from the 28 merged sections)

| Vol | Slug | Title (provisional) | Pillar | Sections (by H2) | ~Words |
|----|----|----|----|----|----|
| 01 | `al-anwaar-al-lateefah-vol-01` | The Oneness (Tawheed) | Unity | Opening Covenant; Tawhid/Tanzih/Hudud | 24.5k |
| 02 | `…-vol-02` | The Origin (Mabda') | Origin | First Emanation → Intellects → Spheres → Man (7 sec) | 58.7k |
| 03 | `…-vol-03` | The Hidden Hierarchy | Metaphysical | Pillar of Light; Concealment/Unveiling; Souls; Soul's Ascent; House of Ibrahim | 60.4k |
| 04 | `…-vol-04` | The Sacred Line | Metaphysical | Genealogy → Husayn → Ahl al-Bayt → Muhammad ibn Isma'il | 31.9k |
| 05 | `…-vol-05` | The Return (Ma'ad) | Return | Two Paths → Resurrection → Retribution → Farthest Mosque → Dawn (10 sec) | 51.1k |

*Titles + exact section→volume boundaries are confirmed with Asif at the §6.1 split-design gate.*

## 6. Execution sequence (each step gated)

1. **Volume split design** — produce the per-volume teaching-ID assignment from the 3,037-teaching ledger (each ID → exactly one volume; no cross-volume repeats), finalize titles/groupings. **HALT for Asif approval.**
2. **Scaffold the multi-volume work** — `work.yml` + `vol-01..05/` via `intake_book.py --work` / `_work_manifest`; one branch.
3. **Per-volume pipeline (gated per volume):** 0d chapter design (density + cross-volume dedup) → 0e enrichment (weave augmentation atom-candidates) → per-chapter authoring + challenger convergence → finalize (G1–G14, incl. Arabic G14). **Each volume halts at finalize for review.**
4. **Curation rule applied at 0d:** audio episodes follow the spine arc breathably; the reading edition (`book.pdf`, 0book-* phases) carries full depth.
5. **Publish per volume** (Tier 2 — always ask) → status flip; work rolls up to published when all volumes are.

**Hard stops (never auto-proceed):** §6.1 split approval; every per-volume 0d→finalize review; every publish; `develop`→`main`.

## 7. Decision log

- **2026-06-17 — Spine is COMPLETE (65 lectures).** The 61–66/69–71 "gap" was file-naming only; serialized to lec01-65; hazrat-zia augmentation fills Ma'ad depth. **No re-synthesis.**
- **2026-06-17 — Volumes under one root, not separate books.** Same overarching category → one folder; reconciled with listener-completability by authoring each volume standalone (multi-volume work).
- **2026-06-17 — Curate audio, full depth in reading edition.** 1-teaching-per-93-words is too dense to air wholesale.
- **2026-06-16 — Arabic gate refined (MIN_ARABIC_LETTERS=2).** A lone illustrative letter is never a protected span; all real verses/hadith intact.

## 8. Command reference

```bash
# state probe
jq '{phase,phase_status,last_completed_phase,multi_source}' content/Islamic/al-anwaar-al-lateefah/_system/orchestrator-state.json
# merged book + ledger
wc -w content/Islamic/al-anwaar-al-lateefah/_system/unified-book.md
jq 'length' content/Islamic/al-anwaar-al-lateefah/_system/source/text/_teaching-ledger.json
# arabic gate (standalone, should pass)
.venv/bin/python scripts/podcast/arabic_integrity.py status al-anwaar-al-lateefah
```

*(System python lacks PyYAML — use `.venv/bin/python` for pipeline scripts.)*
