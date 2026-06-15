# Podcast Challenger Report

**Book:** kunooz-al-hikmah
**Run:** 2026-06-15 (challenger v2.5)
**Scope:** per-chapter ch01a-family-of-light / EP01-family-of-light
**Content profile:** islamic_scholarly (inferred — tradition=fatimid-tayyibi-ismaili, no explicit field in meta.yml)
**Iterations:** 1 (of 5 max) — intelligent-break: zero auto-fixes, identical findings vs prior pass
**Verdict:** SHIP-WITH-CAUTION

## Auto-fixes applied (iteration-by-iteration)

| Iter | Check | File | Action |
|---|---|---|---|
| — | — | — | None this pass. All deterministic auto-fixes (B5 em-dashes) were applied in the prior pass earlier this run. |

## Findings requiring author resolution

### P0 (blocks ship)

None. Build-time hard gates pass: meta-prose, doctrinal (T1–T5), honorific discipline (O1), abbreviation expansion (O2), phonetic-as-content (N1/N2/N4), Quran citation format (no bare `N:M`), no banned modern-platform names, no AI clichés, no faux-profundity openings outside the framing's negative DENY block. Boundary contract (S2) clean. Host-role parity Q1–Q4 satisfied.

### P1 (ship-with-caution)

#### E1 / CS4: chapter in tier dead-zone (5,413 words)
- **File:** content/Islamic/kunooz-al-hikmah/chapters/ch01a-family-of-light.txt
- **Context:** Chapter is 5,413 words — sits in the 4,500–5,500 "tier dead-zone" (too dense for Longer Deep Dive, too thin to sustain Extended Deep Dive in NotebookLM). Build script emits WARN.
- **Suggested fix:** Either tighten to ≤4,500 words or expand via Phase 0e enrichment to ≥5,500.

#### A1: Quran citation format uses retired terse form (4 occurrences)
- **File:** content/Islamic/kunooz-al-hikmah/chapters/ch01a-family-of-light.txt
- **Context:** Four Quranic references use the retired terse form: `(Quran 2:20`, `(Quran 3:61`, `(Quran 114:1`, `(Quran 113:1`. R-QURAN-CITATION-FORMAT (canonical since 2026-06-10) requires the plain-English `(the chapter of …, verse N)` form because TTS reads `2:20` as opaque number runs.
- **Suggested fix:** Rewrite to e.g. `(the chapter of the cow, verse 20, Pickthall trans.)`, `(the chapter of the family of Imran, verse 61, …)`, `(the chapter on the splitting of dawn, verse 1, …)`, `(the chapter on mankind, verse 1, …)`. The framing's Landing block already mandates Surah names in English, so chapter and framing converge naturally on the rewritten form.

#### R-NAMEDISCIPLINE: framing Name discipline section lacks a 3+ alias rotation
- **File:** content/Islamic/kunooz-al-hikmah/_system/episode-drafts/EP01-family-of-light/00-framing.md (Name discipline section)
- **Context:** Build script flag — long figures (the Prophet, Father of Imams, Commander of the Faithful, the Prophet's daughter, elder/younger grandson, Imam of the Time) are named with first-mention forms, but no explicit `Rotation: a / b / c` set is declared.
- **Suggested fix:** For the most frequently named figures add an explicit rotation set, e.g. `the Prophet → the Messenger of Allah → the noble Prophet` and `the Father of Imams → the Father of the Imams → the gate of the City of Knowledge`.

#### R-DRAMATIC-ARC: framing Three-part focus reads as 3 thematic beats, not a 6-beat dramatic arc
- **File:** content/Islamic/kunooz-al-hikmah/_system/episode-drafts/EP01-family-of-light/00-framing.md (Three-part focus)
- **Context:** Build script flag — found 3 Beat markers AND only 1/4 of the dramatic-arc structure tells (crisis / failed answer / pivot / stakes). Beats are thematic ("treasures for whom" / "equality in bewilderment" / "the veiling chain") rather than carrying the arc dynamics NotebookLM steers on.
- **Suggested fix:** Restructure as 6 beats with crisis (the astonishment of believer-as-substance), failed answer (a ladder-of-rungs picture that fails), pivot (equality in bewilderment), stakes (the believer's dignity / fifty-thousand-year horizon), and resolution. Authoring decision — challenger cannot rewrite the dramatic spine without losing voice.

#### F25-APPARATUS-TABLE: 99-show-notes.md missing Name and Title Preservation Table
- **File:** content/Islamic/kunooz-al-hikmah/_system/episode-drafts/EP01-family-of-light/99-show-notes.md
- **Context:** Build script flag — no `## Name and Title Preservation Table` section header. F25 doctrine requires every episode's 99-show-notes.md to carry the written-layer apparatus (preserved Arabic / transliterations + audio-label crosswalk) the TTS-safe audio omits.
- **Suggested fix:** Add the apparatus table mapping spoken English labels (the Prophet, the Father of Imams, the Commander of the Faithful, the Prophet's daughter, *The Stored Treasures of Wisdom*, *The Peak of Eloquence*, *The Sufficient*, *The Treasury of Sciences*) to their preserved Arabic and transliterated forms (Kunooz al-Hikmah, Nahj al-Balagha, al-Kafi, etc.).

### P2 (advisory)

None.

## Health metrics

| File | Words | Em-dashes | Terse Quran cites | Notes |
|---|---|---|---|---|
| ch01a-family-of-light.txt | 5,413 | 0 | 4 | Tier dead-zone (WARN); A1 P1 |
| EP01/00-framing.md | 707 | 0 | — | Name-discipline + dramatic-arc P1 |
| EP01/99-show-notes.md | — | — | — | F25 apparatus table missing (P1) |

Build-time hard gates (build_episode_txt.py): PASS. Episode customize-prompt regenerated.
