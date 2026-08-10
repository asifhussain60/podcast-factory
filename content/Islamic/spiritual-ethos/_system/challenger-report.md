# Podcast Challenger Report

**Book:** spiritual-ethos
**Run:** 2026-08-06 19:49 (challenger v2.6)
**Scope:** per-chapter the-letter-of-ali-to-malik-al-ashtar (ch13 + EP13)
**Iterations:** 1 (of 5 max — intelligent break: 0 auto-fixes, deterministic gates stable)
**Verdict:** SHIP-WITH-CAUTION

content_profile: islamic_scholarly  ← detected from _system/series-config.yaml

> Pipeline-internal invocation (orchestrate_book.py per-chapter loop). Category S1
> async-safety gate bypassed for the parent orchestrator process per invocation
> contract. All other categories run in full.

## Summary

The chapter (the SOURCE, 10,109 words) and framing (the CUSTOMIZE PROMPT, 702
words emitted) both pass the build-time gate (`build_episode_txt.py` exit 0).
Doctrinal checks T1–T5 are clean across chapter, framing, and show-notes (0
findings each). Every Quran citation is in the canonical `(chapter N, verse M)`
form (6 of them). Honorific forms each appear once. Host roles are the
book-consistent pair (A male scholar / B female seeker). No AI-cliché hits. No
P0 findings. Three P1 findings carry over as ship-with-caution, matching the
standard the book's twelve prior chapters shipped at.

No auto-fixes were applied this run — see "Auto-fix decisions" for why the
em-dash and framing-clause auto-fixers were deliberately withheld to preserve
book-wide parity.

## Auto-fixes applied (iteration-by-iteration)

| Iter | Check | File | Action |
|---|---|---|---|
| — | — | — | None. No deterministic auto-fix was warranted (see decisions below). |

### Auto-fix decisions (why nothing was changed)

- **B5 (em-dashes) — withheld.** The chapter carries 109 em-dashes; the
  already-shipped ch10 carries 66. Em-dashes are this book's established house
  style and the build gate does not flag them. Auto-replacing 109 of them would
  destructively diverge ch13 from the twelve shipped chapters. Not applied.
- **C3 / O1 (honorifics) — not needed.** Each English honorific form appears
  exactly once (`God bless him and his family` ×1; `God bless him and his good
  and pure progeny` ×1). No repeat to strip.
- **B2 (cross-episode refs) — not needed.** No literal `EP##` / "previous
  episode" / "earlier episode" strings. The "earlier chapter" callbacks are
  book-internal narrative, not the episode-reference form B2 targets (see P2).
- **M1/M2, I1/I2, K1/K2, R1–R5, N4 (framing clause insertions) — withheld.**
  The framing uses this book's established compact template, shared in shape
  across all thirteen episodes. Unilaterally inserting divergent DENY /
  choreography clauses into ch13's framing alone would break the book-wide
  framing parity the twelve shipped episodes established. The build gate accepts
  the current framing (exit 0). The framing's Pronunciation block already uses
  the correct say-once `- term: form` bullet shape (N2/N7 clean) and carries the
  DENY / no-read-aloud / R-RECURRING-THESIS content in its `## Do not` section.
  Flagged for book-level consideration rather than single-episode auto-fix.

## Findings requiring author resolution

### P0 (blocks ship)

None.

### P1 (ship-with-caution)

#### R-NO-ARABIC-TRANSLITERATION: 'al-Ashtar' in chapter opening
- **File:** content/Islamic/spiritual-ethos/chapters/ch13-the-letter-of-ali-to-malik-al-ashtar.txt:1
- **Context:** "the mandate he sent with Malik al-Ashtar when he made him governor of Egypt". One Arabic transliteration (`al-Ashtar`) in the SOURCE. F20 doctrine prefers English audio labels; the framing already routes the hosts to "the governor".
- **Note:** This is the addressee's intrinsic family name (and the chapter's own title). There is no English translation to substitute; resolution is an authoring judgment (keep the historical name once vs. reword to "the man he made governor"). Not a mechanical fix. Consistent with proper-name handling in the book's other chapters.

#### F25-APPARATUS-TABLE: show-notes missing Name and Title Preservation Table
- **File:** content/Islamic/spiritual-ethos/_system/episode-drafts/EP13-the-letter-of-ali-to-malik-al-ashtar/99-show-notes.md
- **Context:** No `## Name and Title Preservation Table` header. F25 doctrine wants the written-layer apparatus (preserved Arabic / transliterations + audio-label crosswalk) in each episode's show-notes.
- **Note:** Show-notes are published-library apparatus; the challenger does not edit `99-show-notes.md` (Section 8). Flagged for the author. Does not reach NotebookLM audio.

#### CS5: chapter-set word-count variance (book-scope)
- **Scope:** book-set (min=5,006, max=10,109 → 50% variance; >30% threshold)
- **Note:** Expected by design — the Letter is deliberately the longest chapter and its length band was widened on purpose (contract `length_target: 5500-10300`; commit "widen the Letter chapter's declared length band, don't trim it"). Surfaced for the record; no per-chapter action.

### P2 (advisory)

#### CS2: title length soft target
- **Slug:** the-letter-of-ali-to-malik-al-ashtar — title is 8 words (>6 soft target; under the 60-char hard cap). Advisory.

#### CS6: cross-book term bleed (book-scope, false-positive class)
- Common Islamic vocabulary (`tawhid`, `walaya`, `qutb`, `vicegerent`, `Ghadir Khumm`, `al-Sijistani`) in other chapters matches the `degrees-of-excellence` / `kitab-al-riyad` mangle-maps. These are shared-tradition terms, not genuine bleed. Surfaced for human review per CS6; never auto-stripped. None specific to ch13.

#### B1/B3-adjacent: capstone cross-chapter / series callbacks
- **File:** ch13 (multiple lines) — "This is the final chapter of the book." (line 1) plus ~10 "earlier chapter" / "the series" callbacks.
- **Note:** By design — the contract commissions this final chapter as a capstone with brief callbacks where the earlier commentary episodes already unfolded a doctrine. NotebookLM has only this source in the notebook, so the callbacks reference material not present; kept because they read as natural narrative context and match the authored intent. Advisory only.

### Book-scope (not ch13; surfaced for the record)

#### CS8 / P8: near-duplicate passages between two other chapters
- **Slugs:** dhikr-the-polish-for-hearts ↔ prayer-as-the-source-of-justice — 4 distinct 12-word passages shared (n-gram half of CS8). Sample: "has made the remembrance a polish for the hearts by which they…".
- **Note:** Book-scope P1 between two chapters other than ch13. Does not gate this per-chapter run; recorded so the author can decide whether to cut the overlap from one chapter. No source-range overlap was reported (the P0 half of CS8 did not fire).

### INFO / NOTE

- **N3 (pronunciation ladder):** 8 terms have no settled spoken form and were left
  without a settled framing entry: `ahd, hilm, kharaj, jizya, bayt al-mal,
  sa'ada, shahada, al-sa'ada, al-shahada`. The framing's Pronunciation block
  lists them in `- term: form` identity form (say-once), which is structurally
  correct; the ladder simply has nothing settled to say yet. Settle by ear when
  convenient: `python3 scripts/podcast/run_pronunciation_probe.py spiritual-ethos`.

## Health metrics

| Item | Value |
|---|---|
| Chapter | ch13-the-letter-of-ali-to-malik-al-ashtar |
| Chapter words (SOURCE) | 10,109 |
| Declared length band | 5,500–10,300 (widened for the Letter; within band) |
| Framing words (emitted CUSTOMIZE PROMPT) | 702 |
| Build gate | exit 0 (chapter validated, episode emitted) |
| Quran citations | 6, all canonical `(chapter N, verse M)` |
| Fabrication / VERIFY / CONTEXT markers | 0 |
| Doctrinal T1–T5 (chapter / framing / show-notes) | 0 / 0 / 0 findings |
| Honorific-form repeats | 0 (each form ×1) |
| Arabic script present (N6) | yes (`جزیۃ`, `(ع)`) |
| AI-cliché (U1) | 0 hits (chapter + framing) |
| Host-role parity (Q) | A male scholar / B female seeker — consistent |
| Em-dashes | 109 (house style; not gated) |
| P0 / P1 / P2 | 0 / 3 / 3 |

## Verdict

**SHIP-WITH-CAUTION** — no P0. Three P1 findings (one intrinsic proper name, one
show-notes apparatus gap the challenger does not edit, one book-scope length-band
variance that is intentional). This matches the ship standard of the book's twelve
prior chapters. Upload-ready:
1. Upload `chapters/ch13-the-letter-of-ali-to-malik-al-ashtar.txt` as the single source.
2. Paste `episodes/EP13-the-letter-of-ali-to-malik-al-ashtar.txt` into the Customize box.
3. Generate.
