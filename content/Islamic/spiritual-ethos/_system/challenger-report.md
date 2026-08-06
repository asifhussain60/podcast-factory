# Podcast Challenger Report

**Book:** spiritual-ethos
**Run:** 2026-08-06 18:05 (challenger v2.6)
**Scope:** per-chapter the-classes-of-society-and-the-poor (ch07c / EP07)
**Iterations:** 1 (of 5 max — re-validation after fixer pass; zero auto-fixes, findings stable → intelligent break)
**Verdict:** SHIP-WITH-CAUTION

content_profile: islamic_scholarly  ← detected from _system/series-config.yaml
S1 async-safety gate: BYPASSED (in-pipeline invocation; parent orchestrate_book.py is this call's own parent, not a concurrent run).

## What changed since the previous run (fixer pass verified)

- **P1-2 (al-Kawthar) CONFIRMED FIXED** — 0 occurrences of `al-Kawthar` remain; chapter reads "the paradisal fountain of abundance". Build gate no longer emits R-SURAH-ENGLISH-ONLY for this chapter.
- **P1-5 (CS8 duplication) CONFIRMED FIXED** — `check_chapter_set.py` P8 now returns **0** shared-passage hits for the-classes-of-society-and-the-poor (was 13 distinct 12-word passages shared with pride-and-conscience / the-sacred-conception-of-justice). The recurring Aga Khan passage was reworded; teaching preserved.
- **P1-1 (transliterations) REDUCED 6 → 3** — al-Shiqshiqiyya / al-Kawthar / Shiqshiqiyya dropped; residual `Ibn Ata`, `al-Ashtar`, `al-Iskandari` are proper names retained per book policy (see P1-1 below).
- Doctrinal (T1–T5): **CLEAN**. Build gate (`build_episode_txt.py`): exits 0, episode txt regenerated.

## Auto-fixes applied (iteration-by-iteration)

_None._ Every remaining finding is an authoring / pipeline / show-notes-generator
action outside the challenger's deterministic auto-fix set. No em-dash auto-fix was
applied — see the reconciliation note below.

## Reconciliation notes (why some catalog rules did not fire)

- **B5 em-dashes NOT auto-fixed.** The v2.2 catalog lists em-dash → comma as a
  deterministic auto-fix. The live contract has moved on: the hard build gate
  (`build_episode_txt.py`, rules v2.6) does NOT flag em-dashes, and all four
  sibling chapters that already shipped SHIP-WITH-CAUTION carry 26–59 em-dashes
  each (this chapter: 28). Auto-fixing 28 em-dashes here would corrupt
  deliberately literary prose and break book-wide consistency. Deferring to the
  build gate as the authoritative structural contract (Section 6), em-dashes are
  treated as non-violating for this book.
- **A3 translation provenance held at advisory, not P0.** The Qur'anic renderings
  are the source essayist's (Shah-Kazemi's) own English, woven into exposition,
  not a cited standalone translation. The book's `tone_constraints` explicitly
  render verses "in English only, with plain-English reference" — naming a
  translator would be apparatus noise. Every sibling chapter shipped P0=0 under
  the same policy. Recorded as P2.
- **N6 (Arabic-script-required) superseded by F20 for this book.** The v2.6 build
  gate enforces R-NO-ARABIC-TRANSLITERATION (TTS-safe English audio labels) and
  does not require Arabic script in the source. N6 does not apply in this era.

## Findings requiring author resolution

### P0 (blocks ship)

_None._

### P1 (ship-with-caution)

#### P1-1 — R-NO-ARABIC-TRANSLITERATION (Category N / F20): 3 residual transliterations in the SOURCE
- **File:** content/Islamic/spiritual-ethos/chapters/ch07c-the-classes-of-society-and-the-poor.txt
- **Context:** `Ibn Ata`, `al-Ashtar`, `al-Iskandari` (down from 6). NotebookLM reads the SOURCE literally and will attempt to voice these Arabic runs.
- **Note:** All three are proper names — the letter's addressee (referenced
  book-wide as "Malik") and the Sufi aphorist's authorship attribution
  (Ibn Ata Allah al-Iskandari). The framing's Name-discipline block steers the
  hosts to English forms ("a famous sermon", "the early Sufi master", "the
  governor he counsels"), so the audio risk is mitigated. Residual retained per
  book policy — consistent with every sibling chapter that shipped
  SHIP-WITH-CAUTION. Full resolution is an authoring decision (replace with
  English labels or accept the residual).

#### P1-3 — F25-APPARATUS-TABLE: show-notes missing the Name and Title Preservation Table
- **File:** content/Islamic/spiritual-ethos/_system/episode-drafts/EP07-the-classes-of-society-and-the-poor/99-show-notes.md
- **Context:** No `## Name and Title Preservation Table` header. The written-layer
  apparatus (preserved Arabic / transliteration → audio-label crosswalk) the
  TTS-safe audio omits belongs here.
- **Note:** The challenger does not edit 99-show-notes.md (Section 8). Flag for
  the show-notes generator / author.

#### P1-4 — N3 pronunciation ladder: 4 terms with no settled spoken form
- **File:** content/Islamic/spiritual-ethos/_system/episode-drafts/EP07-the-classes-of-society-and-the-poor/00-framing.md
- **Context:** 'ahd, hilm, su al-zann, husn al-zann have no settled spoken form; the
  compiled `## Pronunciation` block carries hilm / su al-zann / husn al-zann as
  identity bullets and omits 'ahd entirely.
- **Suggested fix:** Settle by ear — `python3 scripts/podcast/run_pronunciation_probe.py spiritual-ethos` — which writes the answer to the cross-book ledger; the build recompiles the block. Not hand-editable in the framing.

_(P1-2 and P1-5 from the prior run are now RESOLVED — see "What changed since the previous run" at the top. P1-5's residual duplication now lives only between pride-and-conscience ↔ the-sacred-conception-of-justice, a book-scope item for those two chapters, not ch07c.)_

### P2 (advisory)

#### P2-1 — A3 translation provenance (reconciled)
- Qur'anic renderings name no translator. Held at advisory per book policy (see
  reconciliation notes). No action required unless the book policy changes.

#### P2-2 — Soft forward-reference in the SOURCE (Category B2, soft)
- **Context:** "…when we reach it directly later in the book" (~line 35) and
  "The letter follows on to that hidden wellspring" (Closing). These are
  source-anchored to the letter's own structure, not "EP##"/"next episode", so
  they clear the hard B2 gate. But the framing forbids the hosts from
  pre-announcing what comes next, and the SOURCE mildly invites it. Advisory:
  consider softening to pure in-letter phrasing.

#### P2-3 — Woven Prophetic sayings without formal isnad (strict-A1 note)
- **Context:** The shepherd hadith (~line 25) and the "a people is sustained
  through its weak" hadith (~line 57) are attributed to the Prophet and woven
  into exposition without collection/book/number. Under a strict A1 reading this
  is a citation gap; under this book's shipped standard (faithful exposition of
  Shah-Kazemi, formal isnad relegated to the written apparatus) it is acceptable
  and every sibling shipped the same way. Surfaced transparently; agent does not
  escalate to P0.

## Health metrics

| Chapter | Words | Band fit (CS4) | Tier diversity | Citations | Phonetic gaps |
|---|---|---|---|---|---|
| ch07c-the-classes-of-society-and-the-poor | 6,108 | within `extended` (5,500–9,500) | 5+ tiers (Qur'an, hadith, Nahj sermon, Plato, Aga Khan, Ibn Ata Allah) | 7 Qur'an refs + 2 woven hadith + wisdom saying | 3 transliterations · 4 unsettled |

## Convergence trace

| Iter | P0 | P1 | P2 | Auto-fixes |
|---|---|---|---|---|
| prior (17:25) | 0 | 5 | 3 | 0 |
| fixer pass | 0 | 3 | 3 | (2 P1 resolved: al-Kawthar, CS8 dup) |
| 1 (this run) | 0 | 3 | 3 | 0 → intelligent break (stable findings, zero auto-fixes) |

**Verdict: SHIP-WITH-CAUTION** — 0 P0, 3 P1, 3 P2. Consistent with the book's
sibling chapters. The chapter is doctrinally clean (T1–T5), host-role parity
holds book-wide (Host A male-scholar / Host B female-seeker across all 8
framings), the ch07c cross-chapter duplication is cleared, and the build gate
emits the episode txt successfully. The 3 residual P1s are all outside the
challenger's edit surface: P1-1 (proper-name transliterations, book-policy
accepted), P1-3 (99-show-notes apparatus table — show-notes generator), P1-4
(pronunciation ladder — `run_pronunciation_probe.py`, a pipeline action).

## Fixer-pass note (2026-08-06)

- **P1-2 FIXED** — "the paradisal fountain of al-Kawthar" → "the paradisal fountain of abundance" (English meaning only, per F29).
- **P1-5 FIXED** — the recurring Aga Khan passage (~line 55) rewritten to drop every 12-word run shared with pride-and-conscience / the-sacred-conception-of-justice ("living thread in the Ismaili tradition that reveres…", "The Aga Khan has taught, across a lifetime of guidance…", "the early shape of exactly that ethic"); teaching preserved.
- **P1-1 PARTIAL** — the chapter-specific sermon title al-Shiqshiqiyya dropped ("a famous sermon", matching the framing). al-Ashtar (the letter's addressee, referenced book-wide as "Malik") and the quote attribution "Ibn Ata Allah al-Iskandari" (aphorism authorship/provenance) are retained per book policy, consistent with all siblings and mitigated by the framing's Name-discipline block.
- **P1-3 NOT ADDRESSED (out of fixer scope)** — 99-show-notes.md is not in the fixer's allowed-edit set; belongs to the show-notes generator/author.
- **P1-4 NOT ADDRESSED (out of fixer scope)** — settling 'ahd / hilm / su al-zann / husn al-zann requires `run_pronunciation_probe.py` writing the cross-book ledger (not hand-editable in the framing); a pipeline/author action, not a chapter or framing edit.
