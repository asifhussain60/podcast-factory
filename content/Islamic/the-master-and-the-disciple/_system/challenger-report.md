# Podcast Challenger Report

**Book:** the-master-and-the-disciple
**Run:** 2026-06-11 (challenger v2.5)
**Scope:** per-chapter zahir-batin-and-the-seven-natiqs
**Content profile:** islamic_scholarly (detected from _system/series-config.yaml)
**Iterations:** 1 (of 5 max — early break: no auto-fixable deterministic findings remain; flagged items are authoring decisions)
**Verdict:** SHIP-WITH-CAUTION

## Auto-fixes applied

None this iteration. Prior pipeline passes already converged on the deterministic fixes (em-dash replacements where mechanical, honorific dedup, framing structural sections). The chapter and framing files validate cleanly through `build_episode_txt.py --check` (one P1 advisory on `99-show-notes.md` apparatus table — outside chapter/framing scope).

## Findings requiring author resolution

### P0 (blocks ship)

None.

### P1 (ship-with-caution)

#### B5: Em-dash density in chapter prose
- **File:** content/Islamic/the-master-and-the-disciple/chapters/ch06c-zahir-batin-and-the-seven-natiqs.txt
- **Count:** 42 em-dashes across the chapter; 24 in framing (framing count is acceptable — most are inside the Name-discipline rotation lines and the DENY block, which are not spoken prose).
- **Note:** Mass auto-replacement would damage sentence rhythm. This chapter is consistent with the rest of the shipped book — the book carries em-dashes throughout and has been shipping under SHIP-WITH-CAUTION on this signal.
- **Suggested fix:** Author pass to convert the highest-impact em-dashes (those at clause junctions where a comma reads naturally) and leave the parenthetical em-dash pairs intact.

#### F25: 99-show-notes.md apparatus table missing
- **File:** content/Islamic/the-master-and-the-disciple/_system/episode-drafts/EP06-zahir-batin-and-the-seven-natiqs/99-show-notes.md
- **Detail:** No `## Name and Title Preservation Table` section header. Surfaced by `build_episode_txt.py --check` after the chapter+framing validation pass.
- **Suggested fix:** Add the written-layer apparatus table (preserved Arabic + transliterations + audio-label crosswalk) to the show-notes file. Out of scope for chapter/framing review but noted here for completeness.

### P2 (advisory)

None.

## Health metrics

| File | Words | Band | Status |
|---|---|---|---|
| ch06c-zahir-batin-and-the-seven-natiqs.txt | 2,375 | 1,800–2,800 (default deep dive) | In band |
| EP06 00-framing.md | 734 | 200–2,000 | In band |

| Check family | Status |
|---|---|
| Doctrinal (Category T) | Clean — `_doctrinal.py` reports no findings |
| Citations (A1–A6) | Citations present and tier-diverse (Corbin, Daftary, Fyzee/Pillars of Islam, Peak of Eloquence, Quran with translator) |
| Phonetic discipline (N1–N4) | Clean — zero inline phonetic parens; framing carries imperative Pronunciation block |
| Honorifics (O1) | Clean — Muhammad PBUH at first mention; Commander of the Faithful PBUH at first mention |
| Welcome/Closing (H1–H3) | Present — opening welcome + reflective closing question |
| Anti-repetition / DENY blocks (I1, M1, M2) | Present — R-RECURRING-THESIS, Twitter/social-media/wow DENY |
| Name discipline (J1) | Present — full Name discipline block with rotation pools |
| Six-beat arc (E3) | Present — explicit beats 1–6 |
| Chapter-set design (CS1–CS6) | Clean for this chapter |

## Verdict reasoning

The chapter is content-clean: all P0 categories (doctrinal, citation authenticity, inline-phonetic-as-content, abbreviated work titles, modernization/surprise DENY blocks) pass. Word counts are in band. The framing carries every mandatory R-* clause (welcome, summary, landing, anti-repetition, name discipline, conversation choreography, DENY-modernize, DENY-surprise, no-read-aloud guard).

Em-dash density (B5) is the only material finding and is consistent with prior shipped chapters in this book — it is a known book-wide stylistic carry, not a chapter-specific defect. SHIP-WITH-CAUTION is the right verdict; the orchestrator can proceed to finalize/publish review.
