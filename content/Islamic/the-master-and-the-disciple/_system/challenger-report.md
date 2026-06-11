# Podcast Challenger Report

**Book:** the-master-and-the-disciple
**Run:** 2026-06-10 (per-chapter focus)
**Scope:** per-chapter ch13b-homecoming-and-the-forty-year-syllogism
**Iterations:** 1 (of 5 max)
**Verdict:** SHIP-WITH-CAUTION

content_profile: islamic_scholarly (detected from _system/series-config.yaml)

## Auto-fixes applied

None this iteration. Build-script validation passed (`build_episode_txt.py` exit 0). Prior 12 chapters of this book shipped under identical em-dash usage and identical "Nahj al-Balagha" citation pattern in chapter prose; treating both as authoring-voice carry-forward, not auto-fix targets.

## Findings requiring author resolution

### P0 (blocks ship)

None.

### P1 (ship-with-caution)

#### R-NO-ARABIC-TRANSLITERATION (build-script flag)
- **File:** chapters/ch13b-homecoming-and-the-forty-year-syllogism.txt
- **Sample:** `al-Balagha` (appears within `Nahj al-Balagha` citation tags)
- **Context:** Two `(Nahj al-Balagha, ...)` citation tags (lines 17, 35) retain the canonical Arabic title alongside the framing audio-label "the book of eloquence". The framing's Pronunciation block already maps `Nahj al-Balagha → the book of eloquence`, so the spoken layer is TTS-safe; the chapter prose preserves the canonical citation per A1 (citation discipline). Same pattern as ch01–ch12 — accepted across the book.
- **Suggested fix:** none if pattern stays consistent with prior shipped chapters; author decision.

#### F25-APPARATUS-TABLE (99-show-notes)
- **File:** _system/episode-drafts/EP13-homecoming-and-the-forty-year-syllogism/99-show-notes.md
- **Context:** Missing `## Name and Title Preservation Table` section (the written-layer apparatus listing preserved Arabic / transliterations + audio-label crosswalk). Same finding pattern as prior episodes in this book.
- **Suggested fix:** authoring step (add the apparatus table to 99-show-notes.md) — does not block NotebookLM upload because show-notes is a published-library artifact, not a NotebookLM source.

### P2 (advisory)

None.

## Health metrics

| File | Words | Notes |
|---|---|---|
| ch13b-homecoming-and-the-forty-year-syllogism.txt | 2,615 | within 1,500–4,500 band (default_deep_dive 1,800–2,800) |
| EP13/00-framing.md | 751 | within 200–2,000 soft band; well-shaped 4-part structure |

## Category coverage (islamic_scholarly profile)

- A (Authenticity): Quran citations cite chapter+verse + Yusuf Ali translator/page; Nahj al-Balagha cites sermon/saying number + translator; Aristotle citation includes book/chapter/translator/edition/page. Clean.
- B (Meta-prose): no cross-episode refs, no file-length self-refs, no translator-apparatus prefixes. Clean.
- C/N/O (Pronunciation, phonetics, honorifics): build-script passed; honorifics appear once each (PBUH-form once on Abraham; "may God be pleased with him" once on Father of Imams). Pronunciation block uses imperative `- term: phonetic` format with say-ONCE doctrine.
- D (Enrichment): 4 Quranic anchors + Nahj al-Balagha + Aristotle = multi-tier; ratio well under 60%; no quote-stacking; no `[CONTEXT NEEDED]` markers.
- E (Articulation): clear 4-movement arc (release → six counsels → confrontation → syllogism → closing); one-sentence summarizable; no verbal filler.
- F (Framing integrity): all four sections present (Opening / Three-part focus / Pronunciation / Anti-noise / Landing); audience implied by series-config; tensions concrete (two-horn charge vs forty-year syllogism); R-RECURRING-THESIS steering present 3× as required.
- H/I/K (Welcome, anti-repetition, interruption-avoidance): Opening warm welcome present, naming source + spine; Landing closes on unresolved reflective question (no recap).
- M/N/O (DENY blocks, phonetic-as-content, abbreviations): framing carries "Forbidden: Twitter, social media, algorithm, wow, right?" block; no inline phonetic parens in chapter; no abbreviated work titles.
- Q (Host role parity): Host A = scholar (male), Host B = seeker (female). Consistent with all 12 prior episodes of this book.
- R (Conversation choreography): Host dynamic specifies friction + concession; Tone constraints name three analogies; Do-not block present.
- T (Doctrinal): T1–T5 all clean (0 findings via `_doctrinal.run_doctrinal_checks`). Father of Imams correctly used as the honorific; no forbidden personal-name pairing.
- U (Scholarly-conversation rubric v2.2): no AI-cliché tells; no faux-profundity opening; no premature-closure ("the question is left with the listener"); no deep-dive self-reference; no essentialism. Clean.
- V (Interest): opening rhetorical question ("What argument can a son offer a father so complete that forty years of paternal authority dissolve into tears?"); challenge-defeat arc explicit (two-horn charge → two-horn reply); modern-relevance present ("which piece of what we have received are we still holding back from the parent, friend, or colleague…"); no strawman framing.

