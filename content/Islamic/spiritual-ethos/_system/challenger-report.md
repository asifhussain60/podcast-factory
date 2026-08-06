# Podcast Challenger Report

**Book:** spiritual-ethos
**Run:** 2026-08-06 16:42 EDT (challenger v2.6)
**Scope:** per-chapter paradox-and-the-inner-struggle (ch03c / EP03)
**Iterations:** 1 (of 5 max — zero auto-fixes applied, finding set stable → intelligent break)
**Verdict:** SHIP-WITH-CAUTION

content_profile: islamic_scholarly  ← detected from _system/series-config.yaml
episode_format: deep_dive (Category P skipped)

## Summary

Build gate `build_episode_txt.py EP03` exits 0 (no P0 hard-fail); episode CUSTOMIZE
prompt regenerated (757 words). Doctrinal gate (`_doctrinal.run_doctrinal_checks`)
returns 0 findings — no forbidden leadership-title/personal-name pairing, no Imam-ordinal
violation, no mis-attribution. Chapter (8,321 words) fits the extended band (5,500–9,500)
declared by the contract. Host-role parity (Q1–Q4) holds and is consistent across all five
sibling framings (Host A male scholar / Host B female seeker, no rotation). Quran citations
all use the canonical plain-English `(chapter N, verse M)` form. No cross-episode refs, no
meta-prose tells, no `[VERIFY CITATION]`/`[CONTEXT NEEDED]` markers, honorific expansions
appear once only. Remaining items are P1/P2 flags that mirror the SHIP-WITH-CAUTION state
every sibling chapter shipped in.

## Auto-fixes applied (iteration-by-iteration)

| Iter | Check | File | Action |
|---|---|---|---|
| — | — | — | None. No deterministic auto-fix conditions fired. |

Notes on auto-fixes deliberately NOT applied:
- **B5 (em-dashes):** chapter carries 95 em-dashes. NOT fixed — every sibling shipped chapter
  retains em-dashes as deliberate house style, and the authoritative build gate does not flag
  them. Stripping them would corrupt gate-passing authored prose.
- **R4/R5 (framing Do-not hardening):** the framing `## Do not` block is compact and lacks the
  formal-transition DENY list and the explicit modern-analogy permission paragraph. NOT
  auto-inserted — the framing is pipeline-generated (carries `.framing-sig`), passes the hard
  build gate, and matches the exact shape of all five shipped siblings. A hand-edit would desync
  the signature and be overwritten by the next framing pass. Flagged for author judgment below.

## Findings requiring author resolution

### P0 (blocks ship)
None.

### P1 (ship-with-caution)

- **R-NO-ARABIC-TRANSLITERATION** — ch03c: 3 transliterations survive in the SOURCE
  (`Ibn Ata`, `al-Balagha`, `al-Rahman`). F20 audio-safety doctrine prefers English audio labels.
  Non-blocking; consistent with sibling posture in a faithful exposition.
- **R-SURAH-ENGLISH-ONLY** — ch03c: surah name `al-rahman` present. F29 doctrine prefers the
  English meaning ("the All-Compassionate" as a name of God is fine in prose; the surah-name
  sense is what F29 targets). Author to confirm intent.
- **F25-APPARATUS-TABLE** — `99-show-notes.md` has no `## Name and Title Preservation Table`.
  F25 wants the written-layer crosswalk the TTS-safe audio omits. Show-notes apparatus, not the
  voiced source; low listener risk.
- **N3 (pronunciation ledger gap)** — 4 terms (`Ali`, `Qur'an`, `Kumayl ibn Ziyad`, `Kufa`) have
  no settled spoken form in the cross-book ledger, so the compiled block left them without an
  entry. Settle by ear: `python3 scripts/podcast/run_pronunciation_probe.py spiritual-ethos`.
  Not hand-fixable per current N3 (manifest retired).
- **A1 (hadith citation completeness)** — line 35, the Prophet's supplication
  "I cannot enumerate Your praise…" is attributed "— the Prophet, in Muslim": collection named,
  but book + number + narrator absent. Faithful-exposition convention (matches the source essay);
  author to verify/complete if a fuller citation is desired. Recorded P1, not escalated.
- **R4 (formal-transition DENY absent in framing)** — `## Do not` block does not name Firstly/
  Secondly/Furthermore/In conclusion/Moving on to/Lastly. See NOT-applied note above.
- **R5 (modern-analogy permission absent in framing)** — `## Do not` block carries the DENY list
  but not the positive "DO use modern-life practical analogies" half. See NOT-applied note above.
- **CS5 / P5 (book-scope, set balance)** — chapter-set word-count variance is 50%
  (min 5,006 / max 10,109 = the-letter-to-malik-al-ashtar); >30% target. Book-scope authoring
  decision (resegment/rebalance), not specific to this chapter.

### P2 (advisory)

- **CS6 / P6 (cross-book bleed false positive)** — ch03c contains `tawhid`, which appears in the
  `degrees-of-excellence` mangle-map. `tawhid` is a universal Islamic term; this is a benign
  collision, never auto-stripped. Surfaced for human review only.

## Health metrics

| Chapter | Words | Quran cites (plain-English form) | Attributed blockquotes | Arabic script | Honorific expansions | Em-dashes |
|---|---|---|---|---|---|---|
| ch03c-paradox-and-the-inner-struggle | 8,321 | 8 (all canonical) | 5 (2 Quran + Prophet/Rumi/Ibn Ata Allah) | present (توحيد ×2) | 1 (ﷺ) | 95 |

Build gate: PASS (exit 0). Doctrinal gate: PASS (0 findings). Framing build validators: PASS.
