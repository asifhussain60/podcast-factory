# Podcast Challenger Report

**Book:** kunooz-al-hikmah
**Run:** 2026-06-15 (challenger v2.5)
**Scope:** per-chapter `lectures-twelve-fourteen-fifteen-continued` (chapter `ch10c`, episode `EP10`)
**Iterations:** 1 (clean re-run after prior fixer pass — zero new auto-fixes, intelligent break)
**Verdict:** SHIP-WITH-CAUTION
**content_profile:** islamic_scholarly (default — meta.yml has no override)

## Auto-fixes applied

No auto-fixes this run. Prior fixer pass (earlier 2026-06-15 cycle) already resolved:
- B5 em-dashes in both chapter and framing (re-verified: 0 em-dashes remain)
- R-NO-ARABIC-TRANSLITERATION: `Abu Talib`, `Umm al-Nada`, `Hudhayfah al-Yamani` replaced with framing-declared aliases (re-verified: 0 hits)
- R-NAMEDISCIPLINE: rotation set added to framing

## Findings requiring author resolution

### P0 (blocks ship) — none

Doctrinal pack (`_doctrinal.run_doctrinal_checks`) returned zero hits. Build script `build_episode_txt.py` validated chapter (6,188 words) and emitted episode (731 words) cleanly.

### P1 (ship-with-caution)

#### B6-DOUBLED-PHRASE — intentional rhetorical anaphora (2 instances)
- **File:** `chapters/ch10c-lectures-twelve-fourteen-fifteen-continued.txt`
- **Build flag:** `"the persons of the chain."` and `"the inner core of the era of concealment."` each appear in back-to-back sentences.
- **Assessment:** intentional didactic restate-then-elaborate ("…the inner core of the era of concealment. The inner core of the era of concealment is constituted by these three."). Standard scholarly Arabic exposition pattern.
- **Recommendation:** leave as-is (authorial intent); not auto-fixed.

#### R-DRAMATIC-ARC — 3-beat doctrinal-march form (matches book pattern)
- **File:** `_system/episode-drafts/EP10-lectures-twelve-fourteen-fifteen-continued/00-framing.md`
- **Detection:** 3 Beat markers, 1/4 dramatic-arc structure tells.
- **Assessment:** the three already-shipped sibling episodes of this book (`lectures-six-seven-eight-continued`, `lectures-nine-ten-eleven-continued`, `later-lectures-and-the-end-of-book`) all use the same 3-beat doctrinal-march form and shipped SHIP-WITH-CAUTION. Consistent with book voice.
- **Recommendation:** retain 3-beat form; flagged for traceability.

#### F25-APPARATUS-TABLE — show-notes missing Name and Title Preservation Table
- **File:** `_system/episode-drafts/EP10-lectures-twelve-fourteen-fifteen-continued/99-show-notes.md`
- **Detection:** no `## Name and Title Preservation Table` H2 (current H2s: `## Related episodes`, `## References`).
- **Recommendation:** author to add the preserved-Arabic + audio-label crosswalk table. Not on the challenger auto-fix allowlist.

### P2 (advisory) — none

## Health metrics

| File | Words | Notes |
|---|---|---|
| ch10c chapter | 6,188 | Inside hard band [500–12000]; 0 em-dashes; 0 transliterations remain; aligns with `length_target` of prior siblings |
| EP10 framing | 731 | Under hard caps; welcome+landing+name-discipline+pronunciation+DENY-modernize+host-roles+no-read-aloud-guard all present |

## Convergence record

- Iter 1: 0 auto-fixes (prior fixer pass already converged); same 3 P1 findings as prior report (anaphora-vs-doubling counted as 2 hits in build but logged as one type); intelligent break per Section 4 step 6b.

## Verdict rationale

SHIP-WITH-CAUTION. Zero P0 findings. Doctrinal checks clean. Build script emits the episode txt successfully. Three P1 finding types remain, all requiring authorial judgment and all consistent with the SHIP-WITH-CAUTION pattern of the three prior shipped episodes of this book. The chapter + framing are upload-ready as-is.
