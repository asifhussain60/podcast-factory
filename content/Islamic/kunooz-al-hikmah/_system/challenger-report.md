# Podcast Challenger Report

**Book:** kunooz-al-hikmah
**Run:** 2026-06-15 (challenger v2.5)
**Scope:** per-chapter EP02-named-duat-and-concealment
**Iterations:** 1 (of 5 max)
**Verdict:** SHIP-WITH-CAUTION

> Build-script structural gate (`build_episode_txt.py`) PASSED for the chapter+framing pair; episode customize-prompt written to `episodes/EP02-named-duat-and-concealment.txt` (719 words). All 9 findings are P1 (ship-with-caution); zero P0; zero doctrinal violations (T1-T5 clean against the `islam` tradition pack).

## Auto-fixes applied

None — every finding in this pass requires authoring judgment (translit→English audio labels, beat-arc restructure, apparatus-table authoring). The deterministic em-dash strip is not enforced in chapter prose for this content profile (`islamic_scholarly`); em-dashes in narration prose are tolerated by the build-script today.

## Findings requiring author resolution

### P0 (blocks ship)

None.

### P1 (ship-with-caution)

#### B6-DOUBLED-PHRASE — copy-paste duplication in chapter
- **File:** `content/Islamic/kunooz-al-hikmah/chapters/ch02b-named-duat-and-concealment.txt:1`
- **Context:** "O the High, O the Great," appears twice back-to-back.
- **Fix:** Collapse to one occurrence.

#### R-NO-ARABIC-TRANSLITERATION — 19 Arabic transliterations in chapter
- **File:** chapter source.
- **Context:** Abu Bakr, al-Alim, al-Aliyy, al-Anwar, al-Fath, al-Ghafur, al-Hajj, al-Hikmah, etc.
- **Fix (F20 doctrine):** Replace with English audio labels in chapter prose; preserved Arabic apparatus belongs in `99-show-notes.md`.

#### R-SURAH-ENGLISH-ONLY — Arabic surah names in chapter
- **File:** chapter source.
- **Context:** al-fath, al-hajj, al-rahman, ibrahim, sad.
- **Fix (F29 doctrine):** Use English meanings ("the chapter on the pilgrimage", "the chapter on the conquest", etc.). The framing already does this — chapter needs alignment.

#### B3 — file-length self-reference (chapter)
- **File:** `chapters/ch02b-...txt:7`
- **Context:** "This episode walks the second half of the front matter…" Chapter prose self-references the episode.
- **Fix:** Rewrite to source-anchored — "The second half of the front matter walks…".

#### N3 — Pronunciation block coverage gap (framing)
- **File:** `_system/episode-drafts/EP02-.../00-framing.md:12`
- **Context:** Chapter carries ~91 italicized transliterated terms; framing's Pronunciation declares 8.
- **Fix:** Add `Pronounce` / English-substitution lines for at minimum: jami al-asrar, hudud al-dawah, hujab, hujjat, ismah, itikaf, malakut, mawad qudsaniyah, namiyah, natiqah, sarib, tasbih, tawil, tayidat, wasiyy, wilayah, jihad, hifz, surah, suwarat.

#### R-NAMEDISCIPLINE — rotation set missing (framing)
- **File:** `00-framing.md:6`
- **Fix:** Add a `Rotation: a / b / c` line under Name discipline with 3+ aliases for at least one long-name target.

#### R-DRAMATIC-ARC — 3 beats vs required 6 (framing)
- **File:** `00-framing.md:23`
- **Context:** Only 1/4 structural tells (crisis/failed-answer/pivot/stakes) detected.
- **Fix:** Restructure `## Three-part focus` as a 6-beat arc.

#### R-HONORIFIC-BOTH-BOUNDS — missing first-mention honorific (framing)
- **File:** `00-framing.md`
- **Context:** Framing names "the Father of Imams" but `peace be upon him` occurs 0× (must equal 1 on first mention of Commander of the Faithful).
- **Fix:** Add `(peace be upon him)` on the first reference.

#### F25-APPARATUS-TABLE — missing apparatus section (show-notes)
- **File:** `_system/episode-drafts/EP02-.../99-show-notes.md`
- **Fix:** Add `## Name and Title Preservation Table` with the Arabic / transliteration / audio-label crosswalk.

### P2 (advisory)

None surfaced this pass.

## Health metrics

| Artifact | Words | Status |
|---|---|---|
| ch02b-named-duat-and-concealment.txt (SOURCE) | 6,135 | within hard band 500-12,000; over soft 4,500 — accepted (narrative-rich, well-shaped arc) |
| EP02 00-framing.md | 719 | within framing band 200-2,000 |
| EP02 episode customize-prompt (built) | 719 | written |

| Check family | Result |
|---|---|
| Category T (doctrinal, T1-T5) | CLEAN (0 findings) |
| Category B (meta-prose / NotebookLM literalness) | 1 P1 (B3 self-reference) + 1 P1 (B6 duplication) |
| Category N (phonetic discipline) | 1 P1 (N3 coverage gap) |
| Category F (framing integrity) | 3 P1 (NAMEDISCIPLINE / DRAMATIC-ARC / HONORIFIC-BOTH-BOUNDS) |
| Category M / O (modernize / honorific repeat) | CLEAN |
| Category Q (host-role parity) | CLEAN (Host A male scholar, Host B female seeker declared correctly) |
| F25 apparatus table | 1 P1 (show-notes missing crosswalk) |
| F29 / F20 audio-label doctrine | 2 P1 (chapter still carries Arabic transliterations + surah names) |

## Convergence notes

Single iteration sufficient: all surface-able findings require authoring judgment (translit→English audio labels, beat-arc restructure, apparatus-table authoring). The intelligent-break rule applies — further internal iteration cannot produce auto-fixes. Outer orchestrator should accept SHIP-WITH-CAUTION and proceed; the P1 list is durable and reviewable post-publish.
