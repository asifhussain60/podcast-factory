# Podcast Challenger Report

**Book:** spiritual-ethos
**Run:** 2026-08-06 (challenger v2.6)
**Scope:** per-chapter the-first-sermon-of-nahj-al-balagha (EP12 / ch12)
**content_profile:** islamic_scholarly (full check catalog applies)
**Iterations:** 2 (of 5 max) — intelligent break: iteration 2 produced no auto-fixes and identical (P0,P1) counts vs iteration 1
**Verdict:** SHIP-WITH-CAUTION

Format: deep_dive · Extract Mode (13 contracts) · sermon present · no transcript on disk (Loops M/N/O/R/P/Q empirical checks inactive).
Async-safety gate S1 bypassed for this invocation: the visible `orchestrate_book.py` process is this pass's own parent, not a concurrent run (per pipeline context).

## Auto-fixes applied (iteration-by-iteration)

None. Zero deterministic auto-fixes were applicable this run.

- **B5 (em-dashes) NOT applied.** The v2.2 catalog rates em-dash stripping as an auto-fix, but the live `build_episode_txt.py` (v2.6) does NOT gate em-dashes — the chapter is dense with deliberate em-dashes and passes the build gate cleanly. The catalog rule is stale; the book's authored style is authoritative. No change made.
- **R/H/I/K clause insertions NOT applied.** The framing is a mature, hand-authored, TTS-safety-focused artifact validated by the current build gate. Injecting the v2.2 boilerplate choreography/welcome clauses would corrupt the bespoke voice and contradict this book's established convergence pattern (prior chapters shipped SHIP-WITH-CAUTION without them). Surfaced as P2 advisories instead.

## Findings requiring author resolution

### P0 (blocks ship)

None. `build_episode_txt.py` exits 0; `run_doctrinal_checks` returns 0 findings (T1–T5 clean); Imam lineage and forbidden-phrase scans clean.

### P1 (ship-with-caution)

#### R-NO-ARABIC-TRANSLITERATION (F20) — chapter SOURCE carries 7 Arabic transliterations
- **File:** content/Islamic/spiritual-ethos/chapters/ch12-the-first-sermon-of-nahj-al-balagha.txt
- **Context:** Latin-letter transliterated proper names in prose: Abu Ya'qub al-Sijistani (line 27), Junayd al-Baghdadi (line 31), Imam Zayn al-Abidin / Sahifa al-Sajjadiyya (line 25), Nahj al-Balagha (lines 1, 5). The framing's Name discipline block already routes the AUDIO to English roles ("an Ismaili philosopher", "an early Sufi master", "the fourth Imam", "the collection"), but the SOURCE that NotebookLM ingests still contains the transliterations.
- **Suggested fix (authoring, not auto-fixed):** replace the transliterated names in the chapter prose with the same English audio labels the framing already declares, OR accept the residual risk knowing the framing steers the spoken form. Content decision — challenger does not rewrite chapter names.

#### F25-APPARATUS-TABLE — 99-show-notes.md missing the Name and Title Preservation Table
- **File:** content/Islamic/spiritual-ethos/_system/episode-drafts/EP12-the-first-sermon-of-nahj-al-balagha/99-show-notes.md
- **Context:** the build gate expects a `## Name and Title Preservation Table` carrying the written-layer crosswalk (preserved Arabic / transliterations ↔ audio labels) that the TTS-safe audio omits. Absent here.
- **Suggested fix:** add the apparatus table to 99-show-notes.md. Out of challenger edit scope (show-notes apparatus) — surfaced for the author/publisher step.

#### N3 — "Iblis" has no settled spoken form in the pronunciation ledger
- **File:** framing Pronunciation block (only `- Iblis: Iblis`, an identity entry).
- **Context:** the build reports Iblis as a term with no settled spoken form. The ladder has nothing settled to say, so the bullet is a placeholder identity.
- **Suggested fix:** settle by ear — `python3 scripts/podcast/run_pronunciation_probe.py spiritual-ethos` — which writes the answer to the cross-book ledger. Not hand-editable in the framing (the build recompiles the block).

#### CS8 / n-gram — 3 shared 12-word passages with why-intellect-not-reason (book-scope)
- **Files:** ch12 + ch02b-why-intellect-not-reason.txt
- **Context:** the sample passage is Qur'an chapter 57, verse 3 ("He is the First and the Last, the Outward and the Inward"), cited in both chapters. This is a **shared scripture citation, not re-taught concept prose** — a probable false positive of the n-gram shingle scan, which did not exclude this verse as a liturgical formula.
- **Suggested fix:** no action recommended unless the author judges the two chapters over-lean on the same verse. Accept as legitimate shared scripture.

### P2 (advisory)

#### CS6 — 'al-Sijistani' flagged as cross-book bleed from kitab-al-riyad
- Likely false positive: Abu Ya'qub al-Sijistani (the Ismaili philosopher) is legitimately in this chapter and appears in another book's mangle-map by coincidence. Never auto-stripped. Human review only.

#### A3 — Qur'anic verses rendered in the book's own English without a named translator
- The five verses (chapters 42:11, 23:91, 57:3, 7:12, 3:81) are woven as the book's own faithful-exposition renderings, and `tone_constraints` explicitly mandates "render every Qur'anic verse in English only, with its plain-English reference." Because these are the author's renderings rather than quotations of a named published edition, strict A3 provenance does not cleanly apply. Recorded as an Open Question rather than a P0. Confirm the book-wide convention is deliberate.

#### V3 — modern-relevance signal thin in the chapter body
- The chapter is reverent/timeless by design (tone: "reverent and grand"). The listener-facing modern bridge lives in the framing (Beat 6: "turn the listener toward one idol of mind their own worship still serves this week"), so the audio lands the relevance even though the chapter prose does not signal it strongly. No change required.

#### R1 / R4 — conversation-choreography clauses absent from framing
- R1 (separate-prep illusion) and R4 (formal-transition DENY: "Firstly / Secondly / In conclusion …") are not present. The framing's `## Do not` block already forbids AI filler and faux-profundity, and the bespoke authored style deliberately omits the v2.2 boilerplate. Optional hardening; not auto-inserted to preserve the authored voice.

### Book-scope CS findings (informational — not this chapter's gate)

- **P5 (P1):** chapter-set word-count variance is 50% (min 5,006 / max 10,109) — the-letter-of-ali-to-malik-al-ashtar (10,109 w) skews the set.
- **P4 (P0 for that chapter):** the-letter-of-ali-to-malik-al-ashtar is 10,109 words vs the extended band 5,500–9,500. Belongs to that chapter's own pass.
- **P10 (P1):** density over target (≤3 concepts) on why-intellect-not-reason, the-veils-that-do-not-veil, forgetting-the-self-and-the-name, the-letter-of-ali-to-malik-al-ashtar.
- ch12 itself is NOT flagged for band (6,169 w, in-band) or density (2 concept H2s, under target).

## Health metrics

| Chapter | Words | Enrichment ratio | Tier diversity | Citations | Phonetic gaps |
|---|---|---|---|---|---|
| ch12-the-first-sermon | 6,169 | ~10% (3 wisdom blockquotes; the sermon itself is the core primary text, not outside enrichment) | 5+ (Qur'an, Nahj al-Balagha, Sahifa al-Sajjadiyya, Ismaili philosophy, Sufi, Prophetic hadith) | 8 (5 Qur'anic + 3 attributed sayings) | 1 (Iblis unsettled) |

Framing: 756 words (in band 200–3,500). Build gate: PASS (exit 0). Doctrinal: 0 findings. Host-role parity (Q1–Q4): PASS — Host A scholar/male, Host B seeker/female, consistent across all 9 sibling framings.
