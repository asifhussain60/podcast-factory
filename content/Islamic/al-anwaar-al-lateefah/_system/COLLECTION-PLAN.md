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

## 5. Volume structure (6 volumes, from the 28 merged sections — APPROVED 2026-06-17)

Section→volume is a **partition of all 28 H2 sections** (each section in exactly one
volume; union = all 28). Full words are computed from `unified-book.md` (deterministic);
the §6.1-era 5-volume word estimates were stale (esp. the old Vol-05 was ~109k / 10
sections, ≈2× any other — broke the standalone-season goal), so the Return was split in
two at section 23. Audio-episode estimates are the curated **spine** basis per §3
(≈35–45% of full words ÷ 3,000–4,000 source words/ep; firms at 0d).

| Vol | Slug | Title | Sections (H2 #) | Full words | Audio eps |
|----|----|----|----|----|----|
| 01 | `al-anwaar-al-lateefah-vol-01` | The Oneness (Tawheed) | 1–2 | 24,501 | ~2–4 |
| 02 | `al-anwaar-al-lateefah-vol-02` | The Origin (Mabda') | 3–9 | 58,661 | ~5–9 |
| 03 | `al-anwaar-al-lateefah-vol-03` | The Hidden Hierarchy | 10–14 | 60,421 | ~5–9 |
| 04 | `al-anwaar-al-lateefah-vol-04` | The Sacred Line | 15–18 | 31,855 | ~3–5 |
| 05 | `al-anwaar-al-lateefah-vol-05` | The Two Paths and the Resurrection | 19–23 | 57,963 | ~5–9 |
| 06 | `al-anwaar-al-lateefah-vol-06` | Retribution and the Dawn | 24–28 | 51,090 | ~4–8 |
| | | **TOTAL** | **28** | **284,491** | **~34 (≈6/vol)** |

Section→volume detail (the assignment key — see §6.1 for the per-volume H2 list).
Every teaching → exactly ONE volume via its section home; the teaching-level
`_volume-split.json` + no-loss/no-repeat verification (`union==3,037`, pairwise-disjoint)
is generated at each volume's 0d, not at scaffold time.

## 6. Execution sequence (each step gated)

1. **Volume split design** — produce the per-volume teaching-ID assignment from the 3,037-teaching ledger (each ID → exactly one volume; no cross-volume repeats), finalize titles/groupings. **HALT for Asif approval.**
2. **Scaffold the multi-volume work** — `work.yml` + `vol-01..05/` via `intake_book.py --work` / `_work_manifest`; one branch.
3. **Per-volume pipeline (gated per volume):** 0d chapter design (density + cross-volume dedup) → 0e enrichment (weave augmentation atom-candidates) → per-chapter authoring + challenger convergence → finalize (G1–G14, incl. Arabic G14). **Each volume halts at finalize for review.**
4. **Curation rule applied at 0d:** audio episodes follow the spine arc breathably; the reading edition (`book.pdf`, 0book-* phases) carries full depth.
5. **Publish per volume** (Tier 2 — always ask) → status flip; work rolls up to published when all volumes are.

**Hard stops (never auto-proceed):** §6.1 split approval; every per-volume 0d→finalize review; every publish; `develop`→`main`.

## 7. Decision log

- **2026-06-17 — Split design APPROVED → 6 volumes (was 5).** Real full-depth word
  counts from `unified-book.md` showed the locked Vol-05 (The Return) was ~109k words /
  10 sections — ≈2× any other volume and ~10–16 audio episodes, breaking the
  "standalone ~6–10 episode season" invariant. The Return was split at the section-23
  thematic break: Vol-05 "The Two Paths and the Resurrection" (sec 19–23, ~58k) + Vol-06
  "Retribution and the Dawn" (sec 24–28, ~51k). Consistent with the existing Vol-03/04
  split of the Metaphysical pillar (volumes ≠ pillars). §5 table updated.
- **2026-06-17 — Teaching→section map is NOT deterministic on disk.** Ledger teachings
  are distilled atoms (0/3,037 verbatim in the book); augment-state files carry no
  anchor data. The split is defined at the section→volume level (a clean partition);
  per-ID→section assignment + the `_volume-split.json` no-loss/no-repeat gate are done
  at each volume's 0d.
- **2026-06-17 — Scaffold mechanism: bespoke synthesis-partition, not `intake_book.py
  --work`.** That intake path assumes one fresh source PDF per volume starting at
  preflight/0a, which would force re-synthesis (forbidden, §3.5). Following the
  asaas-al-taveel precedent, volumes are partitioned from the already-synthesized 0c
  `unified-book.md` into nested `vol-NN/` dirs (each its own book dir), starting at
  **0c**; the root `_system/` (synthesized book + unified ledger + Arabic fingerprints)
  stays as the work's **shared** source of truth (`work.yml` `shared:` block).
- **2026-06-17 — Per-volume phonetics/enrich aligns to the redesigned views.** Each
  volume runs `classify_term_defaults.py` (smart default language) + taa-marbuta
  normalization + the review-by-exception Arabic panel + Studio draft-retention edit
  flow. A work-level seed glossary keeps shared doctrinal vocabulary (ta'wil, nasut,
  hudud, sabiq…) consistent across volumes.
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
