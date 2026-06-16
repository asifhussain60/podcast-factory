# Podcast Challenger Report

**Book:** kunooz-al-hikmah
**Run:** 2026-06-15 8:23 PM EST (challenger v2.5)
**Scope:** per-chapter the-cycle-and-the-practical-frame
**Content profile:** islamic_scholarly (default — series-config.yaml absent)
**Iterations:** 1 (of 5 max — intelligent break: zero auto-fixes, finding counts stable vs prior pass)
**Verdict:** SHIP-WITH-CAUTION

## Auto-fixes applied

| Iter | Check | File | Action |
|---|---|---|---|
| 1 | U4/B3 | ch07b-the-cycle-and-the-practical-frame.txt:47 | Replaced AI-cliche self-reference "in this episode" with source-anchored "in the appendix" |

## Findings requiring author resolution

### P0 (blocks ship)
None remaining after auto-fix.

### P1 (ship-with-caution)

#### F25-APPARATUS-TABLE: 99-show-notes.md missing Name and Title Preservation Table
- **File:** content/Islamic/kunooz-al-hikmah/_system/episode-drafts/EP07-the-cycle-and-the-practical-frame/99-show-notes.md
- **Context:** F25 doctrine requires the written-layer apparatus that audio omits. Build script flags but does not block.
- **Suggested fix:** Author adds the apparatus table per F25 template.

#### F4: Tone constraints over-prescribes "Exactly three governing analogies"
- **File:** _system/episode-drafts/EP07-the-cycle-and-the-practical-frame/00-framing.md:53
- **Context:** Framing names three specific analogies (perfume bottle, night/day, 360 souls). All three appear in the chapter. Steering is sound, but the "Exactly" constraint risks suppressing natural conversation around the rich cosmological material (great cycle, two Mehdis, four-phrase litany).
- **Suggested fix:** Author judgment — consider softening to "Three governing analogies" without the "Exactly" lock.

### P2 (advisory)

#### CS-SCRIPT-CRASH: check_chapter_set.py crashes on contract length_target type
- **File:** scripts/podcast/check_chapter_set.py:275
- **Context:** `'int' object has no attribute 'lower'` — book-wide chapter-set integrity scan could not run; one or more chapter-contract `length_target` fields are integers instead of strings. Pre-existing across prior SHIP-WITH-CAUTION episodes of this book.
- **Suggested fix:** Book-wide cleanup (out of per-chapter scope). Normalize `length_target` to string enum in chapter-contracts.

## Health metrics

| Chapter | Words | Citations | Tier diversity | Honorifics | Phonetic gaps |
|---|---|---|---|---|---|
| ch07b-the-cycle-and-the-practical-frame | 6014 | 9 Quran + 2 hadith/Ghurar + 1 Corbin | 4 tiers (Quran, hadith, Ghurar al-Hikam, Corbin) | All via descriptive titles (Father of Imams, the Messenger) — Name discipline applied | 0 (terms covered in framing imperative Pronunciation block) |

Notes:
- Word count 6014 is over the standard Default Deep Dive band (1800–2800); chapter is best classified as Longer (2800–4500) or Extended. Author's choice for the dense closing appendix is defensible; flagging here for CS4 awareness rather than blocking.
- Citation discipline: every Quran ref carries translator (Saheeh International) per A3; Corbin cite includes pages + series per A1; Ghurar cite carries saying number per A1.
- All blockquoted material reads as integrated prose with proper attribution — no stacking, no source-shifting detected.
- Doctrinal: no T1-T3 violations. Father of Imams is referenced by leadership-title only (never paired with personal name per naming-conventions.yml). Two-Mehdis doctrine correctly distinguishes the eleventh Imam vs. fiftieth (Mehdi of End of Time) — consistent with Ismaili-Tayyibi tradition.
- Framing carries: welcome clause (H1), spine-repeat directive (R-RECURRING-THESIS three-time repeat at open/pivot/close), name discipline block (J1), imperative Pronunciation block (N2), no-read-aloud guard (N4), Do-not block with modernize + surprise + abbreviation tells (M1/M2/O2), host dynamic with friction quotes + concession discipline (K1/P11), three governing analogies, anti-recap landing (H3).
