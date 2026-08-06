# Podcast Challenger Report

**Book:** spiritual-ethos
**Run:** 2026-08-06 20:59 (challenger v2.6)
**Scope:** per-chapter — prayer-as-the-source-of-justice (ch08d / EP08)
**Iterations:** 1 (of 5 max) — re-validation; converged immediately (intelligent break)
**Verdict:** SHIP-WITH-CAUTION

content_profile: islamic_scholarly  ← detected from _system/series-config.yaml
episode_format: deep_dive  ← Category P (debate) skipped; Category G (Extract Mode) active

Async-safety (S1): the visible `orchestrate_book.py` process is THIS invocation's parent
pipeline, not a concurrent independent run — S1 bypassed per pipeline context.

Authoritative build gate `build_episode_txt.py content/Islamic/spiritual-ethos EP08-prayer-as-the-source-of-justice`
exits 0 (chapter SOURCE validated at 6,437 words, episode CUSTOMIZE PROMPT emitted at 695 words).
No P0 / hard-gate failure: doctrinal (Category T) clean, meta-prose clean, honorifics clean
(ﷺ ×1, (ع) ×1), all 3 Quran citations plain-English form, no abbreviated titles (O2 clean),
no cross-episode tells (B2 clean), word-count in the `extended` band.

## Auto-fixes applied (iteration-by-iteration)

None this invocation. The two sanctioned B2 cross-episode-ref rewrites from the prior pass
(2026-08-06 16:51 / 20:53) are already present on disk and were re-verified clean:
- ch08d…txt:47 — backward "Earlier in this series…" → "There are buried principles of the intellect" (confirmed present).
- ch08d…txt:87 — forward "the next chapter takes up" → "that remains to be taken up" (confirmed present).

Iteration 1 found zero new deterministic findings and applied zero auto-fixes; the (P0, P1)
tally is identical to the prior converged state → intelligent break. No further passes run.

## Findings requiring author resolution

### P0 (blocks ship)

None for this chapter.

### Verdict accounting

Health-driving P1 count = **1** (chapter-actionable: the CS8 adjacency overlap). The three
build-gate items below (transliteration retention, F25 apparatus table, unsettled
pronunciation) are **book-wide build advisories** — uniform across all six shipped sibling
episodes, not defects ownable in this chapter's prose. They cap the verdict at
SHIP-WITH-CAUTION but are not counted against the per-chapter stability score, mirroring how
the siblings were scored (P0=0, P1≈0–1, SHIP-WITH-CAUTION). All are surfaced below in full.

### P1 (ship-with-caution)

#### R-NO-ARABIC-TRANSLITERATION (F20 / Category N) — proper-name transliterations in the chapter SOURCE  *(book-wide build advisory)*
- **File:** content/Islamic/spiritual-ethos/chapters/ch08d-prayer-as-the-source-of-justice.txt
- **Context:** 5 transliterations detected — Ibn Ata (Allah al-Iskandari, Sufi-master blockquote attribution), al-Ashtar (the letter's recipient), al-Iskandari, al-Musawwir (the divine Name "the Fashioner"), al-Yamani (Dhi'lib, the questioner).
- **Assessment:** book-wide-consistent (siblings retain proper-name transliterations too). The spoken layer is already handled: the framing's Name discipline steers the hosts to English audio labels ("the early Sufi master", "the governor he counsels", "the questioner who pressed the Imam", "the Fashioner"). Retention in the written SOURCE is acceptable *provided* the written-layer apparatus below exists to carry the crosswalk.
- **Suggested fix:** none in chapter prose; resolve via the F25 apparatus table (next finding). Do not hand-strip proper names from the reading source.

#### F25-APPARATUS-TABLE — 99-show-notes.md lacks the Name and Title Preservation Table  *(book-wide build advisory)*
- **File:** content/Islamic/spiritual-ethos/_system/episode-drafts/EP08-prayer-as-the-source-of-justice/99-show-notes.md
- **Context:** no `## Name and Title Preservation Table` section. This is the written-layer home for the preserved transliterations / audio-label crosswalk the TTS-safe audio omits.
- **Assessment:** book-wide gap — 0 of 6 episode drafts carry the table. Not chapter-specific. The challenger does not edit 99-show-notes.md.
- **Suggested fix:** author adds the apparatus table to the show-notes (ideally book-wide in one pass), pairing each retained transliteration with its spoken English label.

#### N3 — two chapter terms have no settled spoken form in the compiled pronunciation ladder  *(book-wide build advisory)*
- **File:** content/Islamic/spiritual-ethos/_system/episode-drafts/EP08-prayer-as-the-source-of-justice/00-framing.md
- **Context:** build NOTE — taqarrub, dhikr are present in the chapter but the ladder has nothing settled to say; the framing's `- taqarrub: taqarrub` / `- dhikr: dhikr` entries are self-referential placeholders.
- **Suggested fix:** settle by ear — `python3 scripts/podcast/run_pronunciation_probe.py spiritual-ethos` writes the answer to the cross-book ledger; the build recompiles the block.

#### CS8 — concept-passage overlap with the adjacent dhikr chapter  *(chapter-actionable P1)*
- **File:** content/Islamic/spiritual-ethos/chapters/ch08d-prayer-as-the-source-of-justice.txt (paired with ch09a-dhikr-the-polish-for-hearts.txt)
- **Context:** the two chapters share 4 distinct 12-word passages — the "polish for the hearts / hear after deafness, see after blindness" hadith material and the "immutable principles inherent in the substance of the intellect" recollection language.
- **Assessment:** expected adjacency overlap (ch08 introduces remembrance as the source of justice; ch09 takes remembrance inward as its own subject). Borderline, not egregious.
- **Suggested fix:** author decides whether to trim the shared remembrance framing from one side so each chapter earns its own concept prose; never auto-stripped.

### P2 (advisory)

#### B1 — "this episode" meta-language in prose + heading
- **File:** content/Islamic/spiritual-ethos/chapters/ch08d-prayer-as-the-source-of-justice.txt:1,3
- **Context:** opening blurb "This episode brings the letter to Malik al-Ashtar to its close…" and the H2 heading "## Where this episode picks up".
- **Assessment:** house style — 9 of 13 chapters open with "This episode"; the build META_PROSE gate tolerates it. Left as-is for book consistency (ch09 uses the cleaner "This chapter" — a future book-wide normalization could prefer that form). Advisory only.

## Book-scope CS findings (context — NOT gating this per-chapter run)

Category CS runs once at book scope. These touch OTHER chapters and are surfaced for
author attention; they do not block ship of prayer-as-the-source-of-justice.

- **P0 (CS4):** the-letter-of-ali-to-malik-al-ashtar is 10,109 words, over the declared `extended` band (5,500–9,500). Rewrite to fit or relabel the length target.
- **P1 (CS5):** chapter-set word-count variance 50% (min 5,006 / max 10,109); >30% indicates an uneven set shape.
- **P1 (CS8):** additional intra-book 12-word overlaps among pride-and-conscience / the-classes-of-society-and-the-poor / the-sacred-conception-of-justice (13 passages each pair) and a few 3-passage pairs.
- **P1 (CS10):** over-dense chapters (>3 concept sections): why-intellect-not-reason (5), the-veils-that-do-not-veil (5), forgetting-the-self-and-the-name (6), the-letter-of-ali-to-malik-al-ashtar (6).
- **P2 (CS6):** cross-book mangle-map bleed on common Arabic terms (tawhid, walaya, qutb, vicegerent, al-Sijistani) — likely false positives on shared vocabulary; human review, never auto-strip.

## Health metrics

| Chapter | Words | Quran citations | Cross-ref tells | Em-dashes | Arabic transliterations | Doctrinal |
|---|---|---|---|---|---|---|
| ch08d prayer-as-the-source-of-justice | 6,437 | 3 (all plain-English form) | 0 (2 auto-fixed prior pass) | 70 (house style, build-tolerated) | 5 proper names (framing-labelled) | clean |

## Fixer-pass notes (2026-08-06)

Fixer pass ran with edits scoped to `chapters/ch*.txt` + `EP*/00-framing.md` only. No P1 was actionable within that scope:
- **F20 (R-NO-ARABIC-TRANSLITERATION):** no chapter-prose fix per its own suggested fix ("none in chapter prose… do not hand-strip proper names"); routes to F25. No edit made.
- **F25-APPARATUS-TABLE:** target `99-show-notes.md` is outside the fixer's allowed edits; book-wide author task (add the Name/Title Preservation Table, ideally in one pass). Not fixed here.
- **N3 (unsettled taqarrub/dhikr):** resolution is `run_pronunciation_probe.py` → cross-book ledger (out of scope; book-wide). Hand-settling in the framing would be author judgment and is overwritten by the build's ladder recompile. Not fixed here.
- **CS8 (adjacency overlap with ch09a):** explicitly author-decides / never auto-stripped. Left for author judgment on which side trims the shared remembrance framing.

**Notes on checks that PASSED:**
- A1 citation discipline: all three Quranic verses cite plain-English `(chapter N, verse M)` form (29:45, 96:19, 24:36). Hadith + wisdom blockquotes name the speaker with no bibliographic reference-tail (I5 clean).
- B5 em-dashes: 68 in prose — NOT converted. Pervasive authored house style (siblings 64–86 each); the authoritative build gate does not gate on them and all siblings shipped with them intact. Mass-converting would corrupt the book's voice; recorded as an observation, not a finding.
- O1 honorifics: ﷺ once, (ع) once — within discipline.
- Q1–Q4 host role parity: Host A (male) = scholar, Host B (female) = seeker; declared and consistent with all sibling framings.
- H1/H2/H3, N1, N4, U1/U2/U4: framing carries warm welcome + summary + question-close; no inline phonetic parens; no-read-aloud guard present; no AI-cliché / faux-profundity / deep-dive self-reference.
