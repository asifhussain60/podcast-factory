# Podcast Challenger Report

**Book:** the-master-and-the-disciple
**Run:** 2026-06-11 07:47 (challenger v2.5)
**Scope:** per-chapter who-is-allah-beyond-names
**Iterations:** 1 (of 5 max) — intelligent-break: no deterministic auto-fixes available
**Verdict:** SHIP-WITH-CAUTION
**content_profile:** islamic_scholarly  ← detected from _system/series-config.yaml

## Auto-fixes applied (iteration-by-iteration)

None. All five findings require authoring judgment (stylistic parallel sentence, character names from source dialogue, framing apparatus shape).

## Findings requiring author resolution

### P0 (blocks ship)

None.

### P1 (ship-with-caution)

#### B6-DOUBLED-PHRASE: stylistic parallel-sentence flagged as doubled phrase
- **File:** content/Islamic/the-master-and-the-disciple/chapters/ch17a-who-is-allah-beyond-names.txt:55
- **Context:** Two consecutive sentences both begin "It was giving him..." — a deliberate parallel construction by the source/adapter ("It was giving him the comfort...", "It was giving him the hidden..."), not a copy-paste duplication.
- **Suggested fix:** Author judgment — either accept as intentional parallelism or rewrite one of the two sentences to vary the opening.

#### R-NO-ARABIC-TRANSLITERATION: character name 'Abu Malik' (and 'Salih') appears in chapter
- **File:** content/Islamic/the-master-and-the-disciple/chapters/ch17a-who-is-allah-beyond-names.txt (throughout)
- **Context:** Salih and Abu Malik are the two named interlocutors in *The Master and the Disciple*'s source dialogue. The framing already instructs NotebookLM hosts to use "the master" / "the disciple" audio labels, so audio output is TTS-safe, but the chapter SOURCE retains the Arabic names since the source carries them.
- **Suggested fix:** Author decides — replace Salih/Abu Malik with "the master"/"the disciple" throughout the chapter text, or accept that the framing's name-discipline rule covers audio safety and the SOURCE preserves the names for the written show notes / preservation table.

#### R-NAMEDISCIPLINE: framing Name discipline lists 2 labels, no 3-way rotation
- **File:** content/Islamic/the-master-and-the-disciple/_system/episode-drafts/EP17-who-is-allah-beyond-names/00-framing.md:6–11
- **Context:** Build gate expects a `Rotation: a / b / c` pattern (3+ aliases). This chapter has only two named speakers (master, disciple) and the Commander of the Faithful as cited authority — no third rotation slot applies.
- **Suggested fix:** Author may either add a third alias line or accept that this two-speaker chapter doesn't need rotation (the warning is a band-of-correctness signal, not a content defect).

#### R-HONORIFIC-BOTH-BOUNDS: 'peace and blessings of Allah be upon him and his family' missing
- **File:** content/Islamic/the-master-and-the-disciple/_system/episode-drafts/EP17-who-is-allah-beyond-names/00-framing.md
- **Context:** Gate requires the honorific phrase to appear exactly 1× on first mention of the Prophet. This chapter does NOT mention the Prophet — only the Commander of the Faithful (with "peace be upon him") and the Quranic verses. The honorific would be a fabrication if added.
- **Suggested fix:** Accept — finding is a false positive for chapters that don't mention the Prophet. Surface to maintainer for gate-tuning.

#### F25-APPARATUS-TABLE: 99-show-notes.md missing 'Name and Title Preservation Table' section
- **File:** content/Islamic/the-master-and-the-disciple/_system/episode-drafts/EP17-who-is-allah-beyond-names/99-show-notes.md
- **Context:** Every published episode's 99-show-notes.md is expected to carry the written-layer apparatus (Original/Transliteration → Audio Label crosswalk). EP01 has one; EP17 does not.
- **Suggested fix:** Author writes the preservation table covering: Salih, Abu Malik, Allah, Quran, Nahj al-Balagha / The Peak of Eloquence, the Commander of the Faithful, the chapter on consultation (verse 11), the chapter on the heights (verse 143), and the later theological work cited at line 19.

### P2 (advisory)

- **CS5 chapter-set balance:** advisory only at per-chapter scope; book-scope check is the authority.
- **R2 reset clause:** spine has 6 beats — at the band edge; advisory.

## Health metrics

| Chapter | Words | Enrichment ratio | Tier diversity | Citations | Phonetic gaps |
|---|---|---|---|---|---|
| ch17a-who-is-allah-beyond-names | 2,718 | ~22% (Quranic verses 42:11, 7:143; Nahj al-Balagha Sermon 1; later theological work cited at line 19) | 3 tiers (Quran, Nahj al-Balagha, later kalam work) | 4 explicit | 0 (no inline phonetics per R-PHONETICS-OUT) |

## PEQ Score (Wave K)

Stable at iter-1; matches prior reviewed-clean state. Verdict held SHIP-WITH-CAUTION across runs.
