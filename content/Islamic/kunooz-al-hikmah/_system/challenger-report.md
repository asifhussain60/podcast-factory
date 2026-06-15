# Podcast Challenger Report

**Book:** kunooz-al-hikmah
**Run:** 2026-06-15 18:49 EDT (challenger v2.5)
**Scope:** per-chapter later-lectures-and-the-end-of-book
**Iterations:** 1 (of 5 max — early break: zero auto-fixes available; all findings require authoring judgment)
**Verdict:** SHIP-WITH-CAUTION
**Content profile:** islamic_scholarly

## Auto-fixes applied (iteration-by-iteration)

None. All findings below require authoring judgment (F20 audio-label substitution, F25 apparatus table authoring, framing clause additions). The chapter passes all P0 hard gates: build_episode_txt validation (chapter SOURCE + framing CUSTOMIZE PROMPT both validated), doctrinal pack (T1–T5 clean, 0 findings), Quranic citations (11 plain-English citations, 0 terse-form violations), meta-prose tells, em-dashes-as-content, honorific repetition, cross-episode refs, R-RECURRING-THESIS spine present.

## Findings requiring author resolution

### P0 (blocks ship)

None.

### P1 (ship-with-caution)

#### F20-R-NO-ARABIC-TRANSLITERATION: chapter carries 14 Arabic transliterations
- **File:** content/Islamic/kunooz-al-hikmah/chapters/ch05b-later-lectures-and-the-end-of-book.txt
- **Sample:** Abu Talib, al-Aliyya, al-Aliyyu, al-Amidi, al-Azim, al-Bukhari, al-Hikam, al-Islam, al-Kalim, al-Khattab, al-Mutaman, al-Nada, al-Sadiq, al-Wahid, al-adab, al-hissiyyah, al-wasilah
- **F20 doctrine:** replace each transliteration with an English audio label (e.g. `al-Sadiq` → "the sixth Imam", `al-Bukhari` → "the Sunni hadith collector", `nafs al-hissiyyah` → "the sensitive soul"). The Pronunciation block in the framing already uses English labels for some terms; align the chapter prose with the same labels and keep the transliterations only in the 99-show-notes Name and Title Preservation Table.
- **Suggested fix:** author pass over the chapter substituting English labels; preserve the originals only in show-notes apparatus.

#### F25-APPARATUS-TABLE: 99-show-notes.md missing `## Name and Title Preservation Table`
- **File:** content/Islamic/kunooz-al-hikmah/_system/episode-drafts/EP05-later-lectures-and-the-end-of-book/99-show-notes.md
- **Current headers:** `## Related episodes`, `## References` only.
- **F25 doctrine:** every episode's show-notes must carry the written-layer apparatus (preserved Arabic / transliterations + audio-label crosswalk) that the TTS-safe audio omits.
- **Suggested fix:** add the section with a two-column table mapping each transliteration found above to the audio label used in the chapter.

### P2 (advisory)

#### I1-ANTI-REPETITION: framing has no explicit anti-repetition clause
- **File:** content/Islamic/kunooz-al-hikmah/_system/episode-drafts/EP05-later-lectures-and-the-end-of-book/00-framing.md
- The R-RECURRING-THESIS line ("repeat the spine thesis verbatim three times — at opening, pivot, and close") covers the spine, but no clause forbids restating other points or re-citing the same quotes.
- **Suggested fix:** append to the `## Do not` block: "No restating the same point more than once outside the spine; no re-citing the same quote across beats."

#### I2-NO-IRRELEVANT-BACKGROUND: framing does not bound biographical/historical background
- **File:** same framing
- **Suggested fix:** add to `## Tone constraints` or `## Do not`: "Biographical or historical background only when directly pertinent, and only once."

#### K1-CONVERSATION-DISCIPLINE: framing has no explicit interruption-avoidance clause
- **File:** same framing
- The Host dynamic block describes the seeker challenging three times and conceding once, which implies discipline but does not name the interjection rule.
- **Suggested fix:** add to `## Host dynamic`: "Hosts complete each other's thoughts; no mid-sentence interjections, no talking-over."

## Health metrics

| Artifact | Words | Status |
|---|---|---|
| ch05b-later-lectures-and-the-end-of-book.txt | 6,285 | Within contract band 5500–6000 (slight upward drift) |
| EP05 00-framing.md | 716 | Within framing band 200–3500 |
| EP05 99-show-notes.md | (present) | Missing F25 apparatus section |

| Check family | Result |
|---|---|
| Doctrinal (T1–T5) | clean (0 findings) |
| Quranic citation format (A1) | clean (11 plain-English, 0 terse) |
| Meta-prose tells (B1–B4) | clean |
| Cross-episode refs (B2) | clean |
| Honorific repetition (O1) | clean |
| R-RECURRING-THESIS | present (spine verbatim flagged for opening/pivot/close) |
| Host role parity (Q1–Q3) | OK across EP01/EP04/EP05/EP06/EP13 — Host A scholar, Host B seeker |
| DENY-modernize block (M1) | present |
| DENY-surprise block (M2) | present |
| No-read-aloud guard (N4) | present |
| Welcome opening (H1) | present |
| Closing landing (H3) | present (one reflective question, left open) |
| Anti-repetition clause (I1) | gap (P2) |
| Anti-background clause (I2) | gap (P2) |
| Interruption-discipline (K1) | gap (P2) |
| F25 apparatus table | missing (P1) |
| F20 audio-label substitution | 14 transliterations to substitute (P1) |
