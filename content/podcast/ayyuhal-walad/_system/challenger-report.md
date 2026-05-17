# Podcast Challenger Report

**Book:** ayyuhal-walad
**Run:** 2026-05-16 (challenger v1.1, post-architecture-v3.4 refactor)
**Scope:** per-book sweep (5 chapters + 5 framings under the new two-file model)
**Iterations:** 3 (of 3 max)
**Verdict:** SHIP-WITH-CAUTION (one open P1 awaiting Asif's policy decision)

---

## Architecture context (v3.4)

This run is the first under the **two-file deliverable model**:

| File | Role | NotebookLM action |
|---|---|---|
| `chapters/chNN-<slug>.txt` | The enriched chapter — the **SOURCE** | Uploaded directly (no transformation) |
| `episodes/EP##-<slug>.txt` | The customize prompt only — the **CUSTOMIZE PROMPT** | Pasted into NotebookLM's *Customize* prompt box |

The challenger now validates both file types separately, against the same META_PROSE_TELLS + HTML-comment + word-count gates that `build_episode_txt.py` enforces structurally.

---

## Iteration history

| Date | Iter | Verdict | Notes |
|---|---|---|---|
| 2026-05-16 | 1 | BLOCKED | 38 em-dashes auto-fixed; 4 P0 A3 (missing Yusuf Ali attribution) flagged |
| 2026-05-16 | 2 | SHIP-WITH-CAUTION | A3 resolved by author (Asif chose Yusuf Ali); C3 honorific policy remains as P1 |
| 2026-05-16 | 3 | SHIP-WITH-CAUTION | Post-v3.4 refactor: HTML comments stripped from chapters → sidecar enrichment-log; framing H1s + Upload Checklists rewritten; episode txts regenerated as customize-prompt only. All other 29 checks still pass. |

---

## Auto-fixes applied across all iterations

| Iter | Check | File | Action | Count |
|---|---|---|---|---|
| 1 | B5 | ch01–ch05 | em-dash → comma / colon / restructure | 38 |
| 3 | B1 + new architecture | ch01–ch05 chapters | strip leading `<!-- ENRICHMENT STATUS -->` HTML comment; metadata moved to `_system/enrichment-log.md` | 5 |
| 3 | F-arch | EP01–EP05 framings | drop `EP## Framing:` prefix from H1; rewrite Upload Checklist for two-file workflow; drop "This is the customize prompt for NotebookLM…" recursive self-description | 5 |
| 3 | (rebuild) | EP01–EP05 episode txts | regenerated as customize-prompt only via `build_episode_txt.py` | 5 |

**Total auto-fixes across all iterations:** 53 mechanical changes; chapter content unaltered (only metadata stripped); all framings restructured for the v3.4 model.

---

## Author resolutions

| Iter | Check | File | Resolution |
|---|---|---|---|
| 2 | A3 | ch01:46 | Added `English: Yusuf Ali` attribution at first Quranic translation (Quran 39:9) with subsequent-coverage clause |
| 2 | A3 | ch02:46-47 | Same attribution added at Quran 79:40-41 |
| 2 | A3 | ch04:121 | Same attribution added at Quran 2:44 |
| 2 | A3 | ch05:95 | Same attribution added at Quran 3:185 |

---

## Findings still requiring decision

### P1 (ship-with-caution, does NOT block upload)

#### C3 — Honorific repetition policy (unchanged from iter 2)

Per `enrichment-sources.md` §4 anti-pattern "Devotional padding": honorifics (PBUH, AS, RA, salawat) should appear at first mention only per chapter, not on every occurrence. Counts unchanged post-iter-3 (the architecture refactor did not touch chapter prose):

| Chapter | PBUH-like | AS-like | First-mention limit |
|---|---|---|---|
| ch01 | 2 | 3 | 1 each (4 redundant) |
| ch02 | 3 | 2 | 1 each (3 redundant) |
| ch03 | 3 | 1 | 1 each (2 redundant) |
| ch04 | 2 | 2 | 1 each (2 redundant) |
| ch05 | 0 | 1 | within limit |

**Decision required:** strict (auto-strip), devotional-preserve (keep as-is), or compromise (current state — honorifics at each direct-quote introduction). Current state is closest to compromise and defensible. Either way ships.

### Other categories — all pass

- **A1 Citation discipline**: every quote properly attributed.
- **A2 Citation authenticity**: no `[VERIFY CITATION]`; all hadith from canonical collections.
- **A3 Translation provenance**: ✅ Yusuf Ali named at first Quranic translation in chapters 1, 2, 4, 5; ch03 has no Quranic translations.
- **A4 Verbatim quote integrity**: passes spot-check.
- **A5 No source-shifting**: passes.
- **A6 No cross-tradition collision**: annotated correctly throughout.
- **B1–B6 NotebookLM literalness**: ✅ no meta-prose anywhere; no em-dashes (auto-fixed); no cross-episode refs in chapters OR framings; no HTML comments in any chapter; no translator-apparatus prefixes; no invented dialogue.
- **C1 Phonetic coverage**: every Arabic transliteration has phonetic on first chapter occurrence.
- **C2 Lexicon parity**: consistent across chapters.
- **D1 Tier diversity**: all chapters meet ≥3 tier threshold.
- **D2 Enrichment ratio**: 18–25% across chapters, well under 60% cap.
- **D3 Tradition-coherence**: enrichment citations cluster around chapter tensions.
- **D4 No quote-stacking**: passes.
- **D5 No [CONTEXT NEEDED]**: clean.
- **E1 Word-count band**: chapters 2,504–3,981 words; episode txts (customize prompts) 815–989 words — both inside target bands.
- **E2–E5 Articulation**: passes spot-check.
- **F1 Framing exists** for every chapter: ✅ all 5 present.
- **F2 Four-part structure** in framing: ✅ all 5 have Background → Audience → Angle → Central tensions → Host dynamic → Tone constraints → Pronunciation.
- **F3 Audience named concretely**: ✅ all 5.
- **F4 2–4 specific tensions named**: ✅ all 5.
- **F5 Discussion-spine 6–12 beats**: ✅ all 5.
- **F6 Steering phrases present**: ✅ all 5.

---

## Health metrics (post-iter-3, under v3.4 architecture)

| Episode | Chapter (SOURCE) words | Episode (CUSTOMIZE PROMPT) words | Status |
|---|---|---|---|
| EP01 frame-and-first-counsel | 3,981 | 815 | Longer Deep Dive band |
| EP02 hatim-eight-benefits | 2,873 | 989 | Default Deep Dive band |
| EP03 the-path | 2,746 | 967 | Default Deep Dive band |
| EP04 four-cautions | 3,325 | 931 | Longer Deep Dive band |
| EP05 method-and-closing-prayer | 2,504 | 913 | Default Deep Dive band |

All chapters within NotebookLM Default-to-Longer Deep Dive source band. All customize prompts within 150–2,000 framing band.

---

## Upload steps (per episode)

For each episode in the series:

1. Open https://notebooklm.google.com and create a new notebook (name it after the episode title).
2. Click *Add source*. Upload `content/podcast/ayyuhal-walad/chapters/chNN-<slug>.txt` as the single source.
3. Click *Audio Overview*, then *Customize*. Open `content/podcast/ayyuhal-walad/episodes/EP##-<slug>.txt` in a text editor; copy its entire contents into the Customize prompt box.
4. Click *Generate*. Wait 3–5 minutes.
5. Listen end-to-end. If strong, download the MP3 and paste the notebook URL into `_system/registry.md`.

---

## Verdict reasoning

**SHIP-WITH-CAUTION** because all 29 P0 and P1 checks pass except C3 (honorific policy decision). C3 does not block upload; current state is the defensible compromise (honorifics at each direct-quote introduction).

**Bundles are NotebookLM-ready right now.** The architecture refactor introduced zero new findings — clean transition.
