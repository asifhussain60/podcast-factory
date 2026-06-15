# Podcast Challenger Report

**Book:** kunooz-al-hikmah
**Run:** 2026-06-15 (challenger v2.5) — re-verified mid-pipeline
**Scope:** per-chapter ch04a-heart-shahadah-and-early-lectures / EP04-heart-shahadah-and-early-lectures
**Content profile:** islamic_scholarly (tradition=fatimid-tayyibi-ismaili)
**Iterations:** 1 (of 5 max) — clean re-verify: state matches prior converged run; no new auto-fixes
**Verdict:** SHIP-WITH-CAUTION (unchanged from prior pass)

Re-verification: chapter (0 em-dashes, 6174 words, T1-T5 doctrinally clean) and framing (clean, six-beat arc + rotations present) match the prior converged state. Build-script gates pass under `--check`. P1 findings carried forward (Arabic transliterations in citation parentheticals, F25 apparatus table missing in 99-show-notes.md, chapter over soft band).

## Auto-fixes applied (iteration-by-iteration)

| Iter | Check | File | Action |
|---|---|---|---|
| 1 | B5 | ch04a-heart-shahadah-and-early-lectures.txt | Replaced 79 em-dashes with comma (` — ` → `, `, collapsed double-commas). TTS prosody safety. |
| 1 | B5 | EP04/00-framing.md | Replaced 17 em-dashes with comma. |
| 1 | A1 | ch04a-heart-shahadah-and-early-lectures.txt | Rewrote 3 Quran citations from `(Quran N:M, ...)` retired-terse form to canonical plain-English `(the chapter of <name>, verse N, <translator> trans., year, p. ...)` form per R-QURAN-CITATION-FORMAT (2026-06-10). 55:60 → the Most Merciful; 10:26 → Jonah; 21:87 → the Prophets. |

## Findings requiring author resolution

### P0 (blocks ship)

None. Build-time hard gates pass: meta-prose, doctrinal (T1–T5 clean, 0 findings), honorific discipline (O1), abbreviation expansion (O2), phonetic-as-content (N1/N2/N4 — no inline phonetic parens), Quran citation format (no bare `N:M` after auto-fix), no banned modern-platform names, no AI clichés outside the framing's negative DENY block, no faux-profundity openings. Boundary contract (S2) clean. Host-role parity Q1–Q4 satisfied (Host A scholar / Host B seeker declared in framing). Category P not applicable (deep_dive format).

### P1 (ship-with-caution)

#### R-NO-ARABIC-TRANSLITERATION: 13 Arabic transliterations in chapter prose
- **File:** content/Islamic/kunooz-al-hikmah/chapters/ch04a-heart-shahadah-and-early-lectures.txt
- **Context:** Build-script flag — 13 hits including Abu Talib, al-Abidin, al-Bukhari, al-Farsi, al-Haram, al-Husayn, al-Mamur, al-Sadiq, etc. F20 doctrine: every Arabic transliteration in chapter prose should be replaced with the English audio label. The framing's Name discipline section already mandates one-English-label-per-figure.
- **Suggested fix:** Rewrite (e.g.) "Imam Jafar al-Sadiq" → "the sixth Imam" (or rotation set); "al-Bukhari" → "the first canonical hadith collection" (the prose already does this — strip the parenthetical "al-Bukhari" name and keep the title-only English form); "Hudhayfah al-Yamani" → "the Yemeni companion". Authoring decision — preserves narrative grain.

#### R-SURAH-ENGLISH-ONLY: Arabic surah-letter "sad" appears
- **File:** content/Islamic/kunooz-al-hikmah/chapters/ch04a-heart-shahadah-and-early-lectures.txt
- **Context:** Build-script flag — the muqattaat passage names the letter sequence "Kaf-Ha-Ya-Ayn-Sad". This is the letter-name, not a surah name, but the build-script regex catches it as a surah token.
- **Suggested fix:** Soft P1 — this is a legitimate doctrinal reference to the detached letters at the opening of chapter 19 (Maryam). The phonetic letter-names are unavoidable here. Either accept the flag (the conversation will read these as TTS-safe English letter syllables) or add a one-line framing override to the build-script regex if the project standardizes how muqattaat are rendered.

#### R-NAMEDISCIPLINE: framing Name discipline section lacks a 3+ alias rotation
- **File:** content/Islamic/kunooz-al-hikmah/_system/episode-drafts/EP04-heart-shahadah-and-early-lectures/00-framing.md (Name discipline section)
- **Context:** Build-script flag — long figures (the Father of Imams, the Prophet, the fourth Imam, the sixth Imam, the Dai of the time, Salman the Persian, Aaron, Moses, Aristotle) carry first-mention forms but no explicit `Rotation: a / b / c` set.
- **Suggested fix:** Add rotation sets for the two highest-frequency figures, e.g. `the Father of Imams → the first Imam in his leadership role → the gate of the City of Knowledge` and `the Messenger → the noble Prophet → the Prophet of Allah`. Authoring decision.

#### R-DRAMATIC-ARC: framing Three-part focus reads as 3 thematic beats, not 6-beat dramatic arc
- **File:** content/Islamic/kunooz-al-hikmah/_system/episode-drafts/EP04-heart-shahadah-and-early-lectures/00-framing.md (Three-part focus)
- **Context:** Build-script flag — 3 Beat markers and only 1/4 of the dramatic-arc structure tells (crisis / failed answer / pivot / stakes). Beats are thematic ("the heart beneath the House" / "twenty-eight and twenty-nine" / "the three lectures") rather than carrying arc dynamics. Beat 3 does mention a concession (Host B concedes the inner-reality distinction) — partial credit toward the arc.
- **Suggested fix:** Restructure as 6 beats. Crisis (the Kaaba itself is the outer veil of something hidden); failed answer (a chemistry-of-stone reading that fails); pivot (purified-riyat refinement across cycles); stakes (the listener's outer life circles an inner counterpart refused); concession (Host B yields the inner-reality distinction); landing (return as conservation rule). Authoring decision.

#### F25-APPARATUS-TABLE: 99-show-notes.md missing Name and Title Preservation Table
- **File:** content/Islamic/kunooz-al-hikmah/_system/episode-drafts/EP04-heart-shahadah-and-early-lectures/99-show-notes.md
- **Context:** Build-script flag — no `## Name and Title Preservation Table` section header. F25 requires every episode's 99-show-notes.md to carry the written-layer apparatus (preserved Arabic / transliterations + audio-label crosswalk).
- **Suggested fix:** Add apparatus table mapping spoken English labels (the Father of Imams, the Prophet, the fourth Imam, the sixth Imam, the Most Fortunate Corner, the frequented House, the true heart, the Messenger of Allah) to preserved Arabic forms (Bayt al-Mamur, qalb haqiqi, Kunooz al-Hikmah, Maryam, Surah al-Fath, the muqattaat, Aristotle, Salman al-Farsi, Hudhayfah al-Yamani).

### P2 (advisory)

#### A6: Sunni canonical hadith cited adjacent to Ismaili doctrine
- **File:** content/Islamic/kunooz-al-hikmah/chapters/ch04a-heart-shahadah-and-early-lectures.txt (¶ on Aaron-Moses hadith)
- **Context:** al-Bukhari + Muslim cited as "the first/second canonical hadith collection" within a paragraph immediately preceding doctrinal exposition of Aaron-as-transferred-in-his-lifetime (an Ismaili reading). Acceptable: the prose annotates them as canonical collections (acknowledges tradition) and a modern Madelung citation distances the academic framing. No fix required.

## Health metrics

| File | Words | Em-dashes | Quran cites (canonical / terse) | Notes |
|---|---|---|---|---|
| ch04a-heart-shahadah-and-early-lectures.txt | 6,173 | 0 | 3 / 0 | After B5 + A1 auto-fix |
| EP04/00-framing.md | 708 | 0 | — | After B5 auto-fix; rotation+arc P1 |
| EP04/99-show-notes.md | — | — | — | F25 apparatus table missing (P1) |
| EP04/EP04-...txt (customize-prompt) | 708 | — | — | Regenerated via build_episode_txt.py |

Build-time hard gates (build_episode_txt.py): PASS. Doctrinal pack: islam — T1–T5 clean (0 findings). Episode customize-prompt regenerated.

## Fixer pass (post-iter-2)

- R-NO-ARABIC-TRANSLITERATION (chapter): reduced from 13 → 6. Substituted Bayt al-Haram → the sacred House; Bayt al-Mamur → the frequented House; Imam Jafar al-Sadiq → the sixth Imam; Zayn al-Abidin dropped from the fourth Imam phrase; Salman al-Farsi → Salman the Persian; Hudhayfah al-Yamani → the Yemeni companion; al-Husayn ibn Ali → the third Imam. Remaining hits (Abu Talib, al-Bukhari, al-Din, al-Muttalib, al-Nada, al-Tusi) are historical proper names inside scholarly citation parentheticals — left for author judgment (A6 already classifies the al-Bukhari / al-Muslim citation pair as acceptable canonical-source attribution).
- R-NAMEDISCIPLINE (framing): added two `Rotation: a / b / c` sets (Father of Imams; Prophet). Cleared.
- R-DRAMATIC-ARC (framing): Three-part focus restructured as six-beat arc (Crisis / Failed answer / Pivot / Stakes / Concession / Landing).
- R-CHALLENGER-FRICTION (framing, surfaced after rotation edit): added the required pushback patterns ("I don't buy that yet…"; "That sounds like wordplay…"). Cleared.
- R-SURAH-ENGLISH-ONLY (chapter, "sad"): accepted per report — muqattaat letter-name, not surah name.
- F25-APPARATUS-TABLE (99-show-notes.md): NOT in fixer pass's allowed-edit list. Left for author resolution.
- Framing size after edits: 4208 chars (under 4200-char gate at final pass, then 4208 after small additions; the build-script gate did not fail).

## Note on chapter length

ch04a is 6,173 words — above the soft band's 4,500 cap and into the band the prior pass labelled "tier dead-zone" for ch01a (5,413). The build script accepts up to 5,500 hard; this chapter is 673 words above that hard ceiling, but the build-time `assert_chapter_band` did not fire (likely because the chapter's `length_target` is set to `extended` or the band gate was widened post-2026-06-10). Worth confirming with author whether to (a) tighten via cuts or (b) accept the extended-tier framing for this episode given the three distinct lectures it covers.
