# v4-revised doctrine propagation plan

**Status**: planning only. Do NOT edit `scripts/podcast/_authoring.py` or handbook canonical files while orchestrator is mid-flight on KaR. Apply after orchestrator quiesce.

**Scope**: propagate the empirically-validated v4-revised doctrine to the framework so every future book inherits it on round 1.

**Source of truth**: [Ch07 v4-revised lab](content/podcast/library/books/kitab-al-riyad/_system/ch07-lab/v4-revised/) + audit findings from v4 + v4-revised transcripts.

---

## What's empirically locked (proven across 3 audio audits)

| Doctrine | Validated by | Action |
|---|---|---|
| F20 — zero Arabic person/book/concept names | v3 + v4 + v4-revised audio (3 audits) | Propagate to `_authoring.py` Phase 0e + 0g prompts |
| F21 — book-wrap convention ("the book *X*") | Same | Same |
| F16 — episode-number announce ("This is Episode 7 of our walkthrough...") | Same | Already in `_authoring.py` via X14 (X16 was the framing-only addition) |
| Stable role-labels (one per figure, no rotation) | v4-revised audio | NEW: Phase 0g prompt update + handbook canonical |
| Proper-name labels for figures without established English titles | v4-revised audio (Jonathan + Samuel succeeded) | NEW: Phase 0d auto-emit name-aliases.yml with proper-name-where-needed pattern |
| Source-image carve-out (mirror, seven seas, speaker-foundation) | v4-revised audio | NEW: Phase 0g prompt update — distinguish governing-analogies-banned from source-images-permitted |
| Bounded honorifics (≥1, ≤1) | v4-revised partial; missed Commander of the Faithful first mention | NEW: Phase 0g prompt update — emphasize MANDATORY at first-mention |
| Literal pushback sentences for challenger friction | v4 + v4-revised both passed | NEW: Phase 0g prompt update — embed the 4 literal patterns |
| 50-60 min length target | v4 came in at 42; v4-revised at 39:24 — STILL BELOW target | DEFER — structural NotebookLM pacing limit; not framework-fixable |

## What's still NOT locked

| Issue | Evidence | Disposition |
|---|---|---|
| Analogy-cap enforcement | v4 mirror/banned-list fight; v4-revised wax-seal/cups/vault/costume leaks | F27 validator essential; prompt-only fix decays |
| R-NOMODERNIZE enforcement | v4-revised Frankenstein + popularity contest | F27 validator essential |
| Surah-name discipline | v4-revised "Qaf → cough" disaster | F29 + F27 validator |
| Length target | v4 = 42, v4-revised = 39:24 | NOT framework-fixable; accept ~40-45 min reality |
| Alqaab discipline (novel literal translations) | Not yet tested on KaR Ch07 (no novel alqaab in this chapter) | F24 + F27 validator |

---

## Concrete `_authoring.py` propagation diff

### Phase 0g `author_framing()` prompt — sections to update

Located near line 1191-1296 (current X10/X14/X15/X16/X18 patches).

#### 1. Stable role-labels section (replace existing rotation discipline)

**Current** (X15-era rotation discipline):
```
R-NAMEDISCIPLINE: Per-figure rotation set of 3-4 generic English descriptors
to avoid Arabic-name TTS mangling. Rotate aliases per figure to prevent
repetition fatigue while preserving identity tracking.
```

**Replace with** (v4-revised stable-label doctrine):
```
R-STABLE-ROLE-LABELS: Each recurring figure gets EXACTLY ONE English label,
used every time the figure is referenced. Do NOT rotate. Do NOT invent
synonyms. Identity tracking via stable labels > variety.

Label-type selection rule:
- Figures with established English titles (Commander of the Faithful,
  the Prophet, the fourth Imam, the Fatimid caliph, the Imam of the time)
  → use the established English title as the stable label.
- Figures whose primary identity is a structural role in this book's
  argument (the author of the chapter under discussion, the compiler,
  a companion of the Prophet, the early teachers)
  → use a functional role-title as the stable label.
- Figures with NO established English title AND whose role-title would
  create phonetic collision with chapter ontology
  → use a proper English name (e.g., Jonathan, Samuel) with a one-shot
  role-epithet at first mention: "Jonathan, the earlier scholar who
  wrote the book *The Correction*" → thereafter "Jonathan."

Per-book mapping lives in `_system/name-aliases.yml` (F26 schema v2).
```

#### 2. Source-image carve-out (NEW; addresses v4 mirror-vs-banned-list fight)

**Add new section after R-ANALOGY-CAP:**
```
R-SOURCE-IMAGE-CARVEOUT: Chapter prose may contain its own analogical
images (e.g., mirror catching a shape, seven seas of the universal
Intellect, speaker and the foundation, male/female counterparts). When
these appear in the source:

(a) PERMITTED USE: quote or reference in passing, anchored to the
    chapter line where they originate. May serve as one of the 3
    governing analogies if the chapter prose features them centrally.
(b) FORBIDDEN USE: do NOT extend a source-image into a metaphor the
    chapter does not develop. Do NOT use source-images as a fresh
    analogy beyond their textual anchor.

Source-images are NOT exceptions to R-ANALOGY-CAP's banned list. They
are permitted because they ARE the source. The model-invented analogy
ban (sealed rooms, wax-seal, cosplay, etc.) remains absolute.
```

#### 3. Bounded honorifics (clarify MANDATORY)

**Current** (R-HONORIFIC-ONCE existing):
```
R-HONORIFIC-ONCE: Each honorific spoken in full English form ("peace be
upon him", "peace and blessings of Allah be upon him and his family")
exactly ONCE per episode, at first mention of the figure.
```

**Replace with**:
```
R-HONORIFIC-ONCE: Each honorific spoken in full English form EXACTLY
ONCE — not zero, not twice — at the first mention of its specific figure.
MANDATORY at first mention. If you find yourself omitting it, stop and
insert it. Do NOT abbreviate ("PBUH" forbidden).

Required honorifics in Islamic-tradition books:
- "peace be upon him" → at first mention of Ali ibn Abi Talib (the
  Commander of the Faithful)
- "peace and blessings of Allah be upon him and his family" → at first
  mention of the Prophet Muhammad

If the chapter does not reference these figures, omit. If it references
them once each, honorific exactly once each. If it references them
multiple times, honorific stays at first mention only.
```

#### 4. Literal pushback sentences (NEW; embed for R-CHALLENGER-FRICTION)

**Add**:
```
R-CHALLENGER-FRICTION-LITERAL: The Color host's role is FRICTION. Embed
at least 3 of the following 4 literal pushback patterns (or close
paraphrases) in the conversation. Three is the floor; four is preferred:

1. (early crisis): "I don't buy that yet. If [stated dichotomy], what
   *is* the [bridging concept] made of? Isn't this just rephrasing the
   problem?"
2. (pivot): "Isn't this just replacing '[surface explanation]' with
   '[new concept]' — hiding the same connection under a different word?"
3. (non-bodily correction): "That sounds like wordplay. If [refused
   category] isn't [X] and isn't [Y], what is it actually? Aren't you
   just refusing every concrete category I offer?"
4. (closing): "How is this different from hiding the problem under a
   different word? After [extended setup], [the author] just lets the
   chain stand. What changed?"

The Driver does NOT immediately resolve these. The Driver lets each
pushback sit for one or two sentences before answering. Pushback is
GENUINE doubt, not setup for a punchline.
```

#### 5. Surah-name English-meaning rule (NEW for F29)

**Add to R-PHONETICS-OUT or new R-SURAH-ENGLISH-ONLY:**
```
R-SURAH-ENGLISH-ONLY: When citing a Quranic verse, refer to the surah
by its English meaning, NOT its Arabic name. The English meaning is
TTS-stable; the Arabic name mangles ("Qaf" → "cough"; "al-Shams" → various).

Lookup table for most-cited surahs in Islamic philosophy/devotional texts:
- al-Fatiha → "the opening chapter"
- al-Baqarah → "the chapter on the cow"
- al-Isra → "the chapter on the night journey"
- al-Ahzab → "the chapter on the confederates"
- Qaf → "the chapter on the letter Qaf" OR drop and lead with verse content
- al-Shams → "the chapter on the sun"
- al-Layl → "the chapter on the night"
- al-Ikhlas → "the chapter on sincerity"
- al-Nas → "the chapter on humankind"

When in doubt, lead with the verse content and omit the surah name
entirely: "The Quran tells us, '...verse...'" rather than "The Quran,
in the chapter [Arabic name], verse N, '...'"
```

#### 6. Length target (clarify aspirational, not hard)

**Current** (X18-era):
```
target a 45 to 60 minute deep-dive conversation
```

**Update** (after v4 audio empirical findings):
```
Target a 50-to-60-minute deep-dive conversation for dense scholarly
chapters. Provide per-beat minute budgets to encourage longer pacing.
Note: NotebookLM appears to have a structural pacing tendency to produce
~40-45 minute episodes regardless of target — this is acceptable when
the argument transmits cleanly. Do not penalize episodes that fall
slightly under the floor.
```

---

## Concrete handbook canonical updates

### `content/podcast/.skill/handbook/notebooklm-customize-prompt-rules.md`

Add new R-rule entries (in the existing Rule/Why/Required-clause/Auto-detect/Auto-fix/Authority template):

1. R-STABLE-ROLE-LABELS (replaces R-NAMEDISCIPLINE)
2. R-SOURCE-IMAGE-CARVEOUT (new)
3. R-HONORIFIC-ONCE (clarify bounded both sides)
4. R-CHALLENGER-FRICTION-LITERAL (new)
5. R-SURAH-ENGLISH-ONLY (new)

### `content/podcast/.skill/handbook/notebooklm-source-chapter-rules.md`

Add:
- R-NO-ARABIC-SURAH-NAMES (chapter prose must use English surah meanings; mirrors R-SURAH-ENGLISH-ONLY for the chapter side)

---

## Order of operations (after orchestrator quiesce)

1. **Apply F27 validators** to `build_episode_txt.py` (drafts in [f27-validator-drafts.md](_workspace/plan/f27-validator-drafts.md))
2. **Test validators** against KaR Ch07 v4-revised lab — confirm expected failures (al-Shams, al-Ahzab, wax-seal, etc.)
3. **Apply v4-revised doctrine** to `_authoring.py` Phase 0g `author_framing()` prompt (this doc, sections 1-6)
4. **Apply handbook canonical updates** to the two .md files
5. **Re-test on a new book's first chapter** to confirm v4-revised doctrine inherits cleanly (synthetic test or wait for next book)
6. **F26 schema migration** — evolve `name-aliases.yml` to v2 schema; backfill KaR + apply to next book

## Expected outcomes

- Future books inherit ALL v4-revised doctrine on round 1 — no 4-round Ch07-style lab cycle needed
- F27 validators catch the analogy-cap, R-NOMODERNIZE, honorific, surah-name failures the LLM keeps producing
- Per-book artifacts (name-aliases.yml v2) carry the figure → audio_label mapping
- Show-notes apparatus table (F25) carries the written-layer scholarly apparatus

## What stays manual / per-book

- The proper-name choice (Jonathan + Samuel for KaR; different names per book per Asif's preference) — Phase 0d emits candidates, Asif picks
- The book-thesis extraction (F23) — Phase 0d.5 auto-emits draft; Asif confirms
- The English meaning for any non-standard surah not in the lookup table — Phase 0e flags for review
