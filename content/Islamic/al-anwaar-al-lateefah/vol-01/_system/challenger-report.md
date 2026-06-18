# Podcast Challenger Report

**Book:** al-anwaar-al-lateefah-vol-01
**Run:** 2026-06-18 (podcast-challenger v2.5)
**Scope:** per-chapter `the-trust-and-the-science-of-realities` (ch01a / EP01)
**Iterations:** 2 (of 5 max — intelligent break: identical counts, zero auto-fixes on iter 2)
**Verdict:** SHIP-WITH-CAUTION

content_profile: islamic_scholarly  (default — no series-config.yaml / meta.yml present for this book)

## Summary

The chapter (the SOURCE) passes every hard build-time gate in `build_episode_txt.py` /
`_validators.py` (exit 0). Doctrinal checks T1–T5 are clean — the chapter correctly
names "the Father of Imams" throughout and never pairs the leadership-title with the
personal name. Citation discipline (A1–A6) is exemplary. All remaining findings are
P1 advisory (non-blocking) and require authoring judgment, not mechanical fixes.

No P0 findings. No auto-fixes were applied (none warranted — see B5 note below).

## Auto-fixes applied (iteration-by-iteration)

| Iter | Check | File | Action |
|---|---|---|---|
| — | — | — | None applied. |

**B5 (em-dashes) — deliberately NOT auto-fixed.** The chapter carries 28 em-dashes.
The spec's legacy B5 rule says auto-fix these, but the production validator suite
(v2.5) contains NO `assert_no_em_dash` gate — `build_episode_txt.py` passes the file
clean, and all 7 already-converged sibling chapters retain ~29 em-dashes each (e.g.
ch10g, ch03c). Per the agent's own reconciliation principle ("the Python rule modules
ARE the contract"), B5 is treated as superseded house-style; auto-fixing here would
diverge this chapter from the entire rest of the book and contradict the shipping
validator. Recorded as INFO, not actioned.

## Findings requiring author resolution

### P0 (blocks ship)

None.

### P1 (ship-with-caution)

#### R-NO-ARABIC-TRANSLITERATION (build P1) — 9 transliterations in chapter SOURCE
- **File:** chapters/ch01a-the-trust-and-the-science-of-realities.txt
- **Context:** al-Balagha, al-Da('i), al-Din, al-Lateefah, al-Latifah, al-Radi,
  al-Sahaba, al-Sharif, al-thaqalayn. All sit inside CITATION APPARATUS (compiler
  names al-Sharif al-Radi, the blessing on Sayyidna al-Da'i, source titles
  *Nahj al-Balagha* / *Anwaar al-Latifah*, the hadith name al-thaqalayn).
- **Assessment:** These are written-layer scholarly attribution tokens, largely
  unavoidable in a faithful citation. The framing's Name-discipline + Pronunciation
  blocks already instruct TTS to render English audio labels, so the audio path is
  protected. Advisory: the author may English-ify the in-prose ones (e.g. "compiled
  by al-Sharif al-Radi" → "compiled by its classical editor") if a fully translit-free
  source is desired, but this is an authoring decision, not a blocker.

#### R-NAMEDISCIPLINE (build P1) — framing Name-discipline lacks a 3+ alias rotation set
- **File:** _system/episode-drafts/EP01-.../00-framing.md (§ Name discipline)
- **Context:** The section lists one English label per figure (correct intent) but does
  not present an explicit `Rotation: a / b / c` line, which the validator looks for to
  confirm the host won't repeat one label monotonously.
- **Suggested fix:** Add a rotation line for the most-repeated figure, e.g. for the
  Father of Imams: `Rotation: the Father of Imams / the Commander of the Faithful / the master who taught the heart-as-vessel`.

#### R-DRAMATIC-ARC (build P1) — framing has a 3-beat focus, not a 6-beat dramatic arc
- **File:** _system/episode-drafts/EP01-.../00-framing.md (§ Three-part focus)
- **Context:** 3 Beat markers found; validator wants a 6-beat arc with crisis / failed
  answer / pivot / stakes structure tells (1 of 4 present).
- **Assessment:** Soft structural preference. The current 3-beat focus is coherent and
  maps cleanly to the chapter's movements. Author may expand to a 6-beat arc if a
  more dramatic conversational shape is desired.

#### F25-APPARATUS-TABLE (build P1) — 99-show-notes.md missing Name/Title Preservation Table
- **File:** _system/episode-drafts/EP01-.../99-show-notes.md
- **Context:** No `## Name and Title Preservation Table` header. F25 doctrine: the
  written show-notes layer should carry the preserved-Arabic ↔ audio-label crosswalk
  that the TTS-safe audio omits.
- **Note:** The challenger does NOT edit 99-show-notes.md (Section 8 boundary). Flagged
  for the author / show-notes generator.

#### CS8 (book-scope, P1) — n-gram overlap across chapters (citation-formula collisions)
- **Context:** 15 P8 n-gram-overlap pairs surfaced book-wide, but the dominant shared
  shingle is the recurring Nahj al-Balagha citation formula ("father of imams nahj al
  balagha compiled by al sharif al radi…") and liturgical formulae — which CS8
  excludes. The two genuine concept-overlap pairs (equal-but-not-infallible ×
  the-unknowable-originator-and-first-intellect, ×the-ladder-of-tawhid) do NOT involve
  ch01a. **ch01a is not implicated in any concept-duplication pair.**

#### CS10 (book-scope, P1, advisory) — ch01a has 8 concept sections (target ≤3)
- **Context:** This chapter is the densest in the set (8 concept H2s). As an opening
  "foundation" episode that lays provenance + covenant + architecture + method + path +
  return, the breadth is by-design and the contract declares `length_target: longer`
  (3,523 words, in-band). Advisory — re-split only if the listener can't hold it.

### P2 (advisory)

#### B5 (INFO) — 28 em-dashes (see Auto-fixes note above). Not enforced by v2.5 validators; house style.

## Health metrics

| Chapter | Words | Blockquotes | Citations | Concept H2 | Translit (citation-only) | Honorific repeats | Phonetic gaps | Doctrinal |
|---|---|---|---|---|---|---|---|---|
| ch01a | 3,523 | 5 | 6 | 8 | 9 (all in apparatus) | 0 | 0 | clean (T1–T5) |

**Hard-gate status:** PASS — `build_episode_txt.py` exits 0; episode CUSTOMIZE PROMPT
(713 words) builds successfully. Both upload artifacts are present and valid.

**Category roll-up:**
- A (Authenticity): PASS — canonical Quran citation form, real hadith numbers, translators named, cross-tradition hadith annotated (`cf.`).
- B (NotebookLM literalness): PASS — no meta-prose, no cross-episode refs, no inline phonetics. B5 em-dash superseded.
- C/N (Pronunciation): PASS — no inline phonetic parens; framing Pronunciation block uses say-ONCE imperative form.
- D (Enrichment): PASS — 4+ tier diversity (Quran, Nahj al-Balagha, Sunni hadith canon, Rumi); ratio within bound.
- E (Shape): PASS — clear hook/middle/landing arc; one-sentence summarizable; no filler.
- F (Framing): PASS structurally (Opening/Pronunciation/Host-dynamic/Tone/Landing/Do-not all present); R-DRAMATIC-ARC + R-NAMEDISCIPLINE advisory P1.
- O (Honorifics/abbrev): PASS — single honorific expansion; no abbreviated titles.
- Q (Host-role parity): PASS — Host A male/scholar, Host B female/seeker, consistent with book.
- T (Doctrinal): PASS — Father-of-Imams naming correct; no forbidden phrases.
