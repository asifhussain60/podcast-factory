# Podcast Challenger Report

**Book:** spiritual-ethos
**Run:** 2026-08-06 15:49 (challenger v2.6)
**Scope:** per-chapter joy-virtue-and-the-hereafter (chapter ch04d-joy-virtue-and-the-hereafter.txt + EP04 framing)
**Iterations:** 1 (of 5 max — intelligent break: no net auto-fixes, findings stable vs prior pass)
**Verdict:** SHIP-WITH-CAUTION

content_profile: islamic_scholarly  <- detected from _system/series-config.yaml

> Scope note: per-chapter invocation from within the orchestrator pipeline.
> Category S1 (async-safety) intentionally bypassed for the parent orchestrator
> process per pipeline context. Category CS runs book-scope once; its P0 (CS-P4)
> and P1 (CS-P5) belong to a DIFFERENT chapter (the-letter-of-ali-to-malik-al-ashtar)
> and are reported below as book-scope context, NOT this chapter's remediation scope.

## Gates run this pass

| Gate | Result |
|---|---|
| build_episode_txt.py (structural + doctrinal T + phonetic N) | PASS (exit 0); P1 flags + pronunciation NOTE only |
| extract_chapter.py --force (Category G2) | PASS (exit 0); WARN length_target extended->longer |
| _doctrinal.py (Category T1-T5) | CLEAN (no findings) |
| check_chapter_set.py (Category CS, book-scope) | 1 P0 + 1 P1 belong to the-letter chapter; this chapter: 1 P2 advisory |
| A1 Quran citation format (plain-English) | 17 canonical "(chapter N, verse M)" cites; 0 non-canonical |
| B/U meta-prose, AI-cliche, self-reference | CLEAN via _rules regex; soft advisory only (see P2) |

## Auto-fixes applied (iteration-by-iteration)

| Iter | Check | File | Action |
|---|---|---|---|
| 1 | (repair) | EP04/00-framing.md | Restored authored framing after a challenger-side extract_chapter --force overwrote it with the extract scaffold stub; re-ran build_episode_txt (idempotent, framing == episode txt) |

No CONTENT auto-fixes were applied to the deliverables. Em-dashes (25+ lines in
chapter, 14 in framing) are house style for this scholarly prose, are NOT enforced
by the build gate (challenger v2.6), and are not auto-converted (would corrupt
meaning). This matches the prior pass and the pipeline convention.

## Findings requiring author resolution

### P0 (blocks ship)

None in this chapter's scope.

Book-scope (context only -- belongs to another chapter's pass):
- **CS-P4 (P0):** the-letter-of-ali-to-malik-al-ashtar is 10,109 words vs declared
  `extended` band 5,500-9,500. Address in that chapter's own convergence pass
  (rewrite to band, or relabel length_target: longer). Not this chapter.

### P1 (ship-with-caution)

#### N3 / pronunciation: transliterated terms have no settled spoken form
- **File:** EP04 framing `## Pronunciation` + chapter prose
- **Context:** Build NOTE -- `hilm` (and ihsan, husn, zuhd, taqwa, fana appearing in
  chapter prose) have no settled spoken form in the pronunciation ladder. The
  compiled framing block carries only `tawhid: tow-HEED`. The build recompiles the
  block from the ladder, so a gap means the ladder has nothing settled to say.
- **Suggested fix:** Settle by ear -- `python3 scripts/podcast/run_pronunciation_probe.py spiritual-ethos`.
  Structural; not hand-fixable in the framing (the build recompiles every value).

#### F25-APPARATUS-TABLE: 99-show-notes.md missing Name and Title Preservation Table
- **File:** EP04/99-show-notes.md
- **Context:** Build-flagged P1 -- no `## Name and Title Preservation Table` header.
  F25 doctrine: every episode's show-notes carries the written-layer apparatus
  (preserved Arabic / transliterations + audio-label crosswalk) the TTS-safe audio omits.
- **Suggested fix:** Add the apparatus table to 99-show-notes.md (out of challenger
  edit scope; authoring/publish-prep decision).

### P2 (advisory)

#### Source-prose self-reference (NotebookLM-literalness, soft)
- **File:** chapter ch04d, lines 1, 4, 61
- **Context:** "This episode covers the closing movement of the chapter", "this final
  episode begins", "Everything this chapter has traced". Not file-length tells (B3)
  and passed by the build's semantic B-gate; but NotebookLM reads them as content.
- **Suggested fix:** Optional -- soften "this episode/this chapter" self-references to
  source-anchored phrasing. Authoring judgment; not auto-fixed.

#### CS-P6: cross-book name bleed (false positive)
- **Context:** "tawhid" flagged as belonging to degrees-of-excellence's mangle-map.
  tawhid is a universal Islamic term, not book-specific -- advisory false positive.

#### A3-advisory: no inline translator named for Quranic renderings
- **Context:** The chapter renders 17 Quranic verses in English with no inline
  translator attribution. This is by design: the contract's tone_constraints require
  "every verse and saying in English only, with plain-English references", and the
  book is a scholarly essay quoting Shah-Kazemi's own renderings. Translator
  provenance belongs in the show-notes apparatus, not the TTS-safe spoken prose.
  Not raised as A3 P0 (consistent with the build gate and the prior pass).

Book-scope context (not this chapter):
- **CS-P5 (P1):** chapter-set word-count variance 50% (min 5,007 / max 10,109),
  driven by the-letter chapter. Rebalance decision at book scope.
- **CS-P2:** the-letter title is 8 words (>6 soft target).

## Health metrics

| Chapter | Words | Quran cites (canonical) | Doctrinal (T) | Arabic-script terms | Pronunciation gaps |
|---|---|---|---|---|---|
| ch04d-joy-virtue-and-the-hereafter | 6,122 | 17 | clean | tawhid | hilm (+5 unsettled transliterations) |
