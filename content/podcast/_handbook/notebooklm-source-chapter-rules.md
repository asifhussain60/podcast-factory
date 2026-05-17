# NotebookLM Source-Chapter Rules

**Normative.** This file is the single source of truth for what a chapter file at `BOOK_DIR/chapters/chNN-<slug>.txt` (which NotebookLM ingests verbatim as the SOURCE) **must** and **must not** carry.

**Read by**: the podcast skill (Phase 0d + Phase 0e + Phase 4 step 1) AND the `podcast-challenger` agent (Loops B + C + D + E). If this file and other handbook files disagree, **this file wins** for chapter-as-source contracts.

**Authority for the agent**: each rule below ends with `Authority for challenger:` naming the exact check ID that enforces it.

---

## R-NOHTML · No HTML comments in the chapter

### Rule

The chapter file MUST contain zero HTML comments (`<!-- ... -->`). NotebookLM reads them aloud as if they were source content.

### Why

NotebookLM's parser does not strip HTML comments from text files. Any author metadata, enrichment status notes, page-break markers, or scratchpad debris that survives in the chapter file will be voiced by the hosts.

### Auto-detect

Substring scan for `<!--`. Any match → P0.

### Auto-fix or flag

**FLAG (P0)**. The author moves the metadata to `BOOK_DIR/_system/enrichment-log.md` and removes the comment. `build_episode_txt.py` refuses to emit the episode txt otherwise.

### Authority for challenger

`podcast-challenger` Loop **B1**.

---

## R-NOMETAPROSE · No meta-prose describing the chapter

### Rule

The chapter file MUST NOT describe itself. Forbidden patterns:
- "This file is a refined presentation…"
- "Nothing has been added that is not in the source…"
- "Phase 0e enrichment was applied…"
- "Anything Ghazali only implies is marked as such…"

### Why

Same failure mode as HTML comments — NotebookLM voices it as source content. Listeners hear the hosts narrate authoring metadata.

### Auto-detect

Substring + regex scan against `META_PROSE_TELLS` and `META_PROSE_REGEX_TELLS` in `scripts/podcast/build_episode_txt.py`.

### Auto-fix or flag

**FLAG (P0)**. Author rewords; build script enforces.

### Authority for challenger

`podcast-challenger` Loop **B2** (semantic equivalents that the substring match would miss).

---

## R-CROSSREF · No cross-episode references

### Rule

The chapter file MUST NOT reference other episodes (`EP\d\d`), "previous episode", "earlier episode", or "next episode". Each chapter stands alone for NotebookLM.

### Why

NotebookLM has no context across uploads. A reference to "as we discussed in EP02" produces hosts asking each other what EP02 was.

### Auto-detect

Regex `EP\d\d` + substring scan for "previous episode", "earlier episode", "next episode".

### Auto-fix

**AUTO-FIX** (deterministic): rewrite to source-anchored phrasing ("earlier in the letter", "in an earlier passage").

### Authority for challenger

`podcast-challenger` Loop **B3**.

---

## R-NOEMDASH · No em-dashes in chapter prose

### Rule

The chapter file MUST use commas, semicolons, or sentence restructuring instead of em-dashes (`—`). Em-dashes confuse NotebookLM's prosody — the hosts read them as awkward mid-sentence pauses.

### Auto-detect

Regex `—` or ` - ` with surrounding spaces (the prose form).

### Auto-fix

**AUTO-FIX** (deterministic): `—` → `, ` with sentence rebalance.

### Authority for challenger

`podcast-challenger` Loop **B4**.

---

## R-WORDBAND · Chapter word count band

### Rule

The chapter file MUST land within:
- **Sweet spot**: 1,800–2,800 words (Default Deep Dive)
- **Acceptable**: 1,500–4,500 words (with noted rationale for the outliers)
- **Hard refuse**: outside [500, 5,500] words → `build_episode_txt.py` rejects emission

### Why

NotebookLM's Audio Overview targets ~10–15 minutes. Source files outside the band produce unbalanced or truncated episodes. The hard refuse band is enforced structurally; the soft band is enforced semantically by the challenger.

### Auto-detect

`wc -w` on the chapter post HTML-comment strip.

### Auto-fix or flag

**FLAG (P1)** if outside soft band. **FLAG (P0)** if outside hard band (build script auto-fails).

### Authority for challenger

`podcast-challenger` Loop **E1**.

---

## R-ENRICH60 · Enrichment cap 60%

### Rule

Outside-source material (Quran, hadith, Imam Ali (AS), Ismaili tradition, Sufi voices) inserted via Phase 0e MUST NOT exceed 60% of the chapter's total word count. The source author's argument stays the spine.

### Why

When enrichment displaces the source, the chapter becomes a citation collage rather than a substantive treatment of the original.

### Auto-detect

Mark each blockquote and its surrounding bridge sentence; sum; divide by total.

### Auto-fix or flag

**FLAG (P1)**. Cutting enrichment is an authoring decision.

### Authority for challenger

`podcast-challenger` Loop **D2**.

---

## R-MULTITIER · Enrichment spans at least 3 tradition tiers

### Rule

Each chapter's enrichment MUST draw from at least 3 of the 7 whitelist tiers documented in `enrichment-sources.md`. A monoculture (all hadith, or all Ismaili, or all Sufi) weakens the chapter.

### Auto-detect

Classify each cited source by tier; count distinct tiers.

### Auto-fix or flag

**FLAG (P1)**. Authoring decision.

### Authority for challenger

`podcast-challenger` Loop **D1**.

---

## R-NOSTACK · No quote stacking

### Rule

The chapter file MUST NOT carry three or more consecutive blockquotes on the same beat without integrating prose (≥30 words) between them. One well-placed quote beats three loosely-placed ones.

### Auto-detect

Count consecutive blockquotes; flag stacks ≥3 without intervening commentary of ≥30 words.

### Auto-fix or flag

**FLAG (P1)**.

### Authority for challenger

`podcast-challenger` Loop **D4**.

---

## R-PHONETICS-OUT · No inline phonetic guides in the chapter

### Rule

The chapter file MUST NOT carry inline phonetic guides in parentheses (`*Term* (PHO-ne-tic; gloss)`, or `> (bis-mil-laah ir-rah-maan ir-ra-heem. …)` after a transliteration). All phonetic guidance for the episode lives in the customize prompt's **Pronunciation** block (R-PRONUNCIATION-IMPERATIVE in `notebooklm-customize-prompt-rules.md`). The chapter ships the transliteration only (or the English equivalent if substituted per R-SUBSTITUTION); a short English gloss after the term is permitted when it carries meaning the listener needs, but the **respelled phonetic itself never appears inline**.

### Why

This rule replaces the deprecated R-PHONETIC. NotebookLM has no TTS-engineer layer — it reads parenthetical text aloud as content. Empirical evidence (May 2026 audit against the 5 *Ayyuhal Walad* transcripts): inline `(SOON-nah; …)` produced systematic doublings — hosts saying "Sunnah, soon-nah" or "Sahih Sitta, sahasita" — and mangled names like "tassel wolf" for *Tasawwuf*, "shakestone noon mystery" for *Shaykh Dhul-Nun al-Misri*, "Najah Balala" for *Nahj al-Balagha*. Moving phonetic guidance out of read-aloud surface and into the imperative customize prompt is the structural fix.

### Auto-detect

Regex scan for the parenthetical respelling pattern. Anchor on:
- `\*[A-Za-z'`\-]+\*\s*\([A-Z][A-Z\-]+`
- `>\s*\([a-z\-]+\s+[a-z\-]+`  (the post-transliteration phonetic line in a blockquote)
- Any parenthesis whose contents are >50% hyphen-delimited respelled syllables.

### Auto-fix or flag

**AUTO-FIX** (deterministic): strip the parenthetical phonetic; keep the term + any non-phonetic gloss before the semicolon if present. If the parenthetical was a post-transliteration phonetic line, strip the whole line. Move the term + canonical phonetic into the customize prompt's Pronunciation block via R-PRONUNCIATION-IMPERATIVE.

### Authority for challenger

`podcast-challenger` Loop **N** (phonetic-as-content audit) + Loop **C1** (still tracks phonetic coverage but now measured against the customize prompt's Pronunciation block, not inline chapter parens).

---

## R-HONORIFIC-ONCE · Honorifics expanded exactly once per chapter

### Rule

Honorifics — `(PBUH)`, `(SAW)`, `(AS)`, `(RA)`, `(peace and blessings be upon him)`, `(peace be upon him)`, `(peace be upon them)`, `(may Allah be pleased with him/her)` — MUST be expanded **exactly once per chapter, on first mention of each figure**. Every subsequent mention of the same figure uses the contracted form (`the Prophet`, `Imam Ali`, `Imam Hasan`, `Aisha`, etc.) without re-attached honorific.

### Why

Devotional padding is the anti-pattern. NotebookLM reads every expanded honorific aloud, so a chapter that writes "the Prophet (peace and blessings be upon him)" eight times produces eight on-air recitations. The 2026-05-17 audit measured this on the *Eight Truths That Survive the Grave* transcript — the hosts said "the prophet, peace and blessings be upon him" nine times in a single episode.

### Auto-detect

For each known figure (Prophet, Imam Ali, Imam Hasan, Imam Husayn, Aisha, Hatim, Junaid, Ghazali, etc.), count expansions of any honorific form. First occurrence allowed; every subsequent → strip the honorific phrase, keep the name.

### Auto-fix

**AUTO-FIX** (deterministic): strip every 2nd+ honorific expansion. Replace `(peace and blessings be upon him)` / `ﷺ` / `PBUH` / `SAW` (2nd+) with empty string. Same for `(AS)`, `(RA)`, etc.

### Build-script enforcement

`build_episode_txt.py` counts honorific expansions and refuses the chapter when any expanded form appears more than once. The deterministic fix is automatic in the challenger; the build script enforces only after the fix has had a chance to run.

### Authority for challenger

`podcast-challenger` Loop **O** (honorific repetition count) + Loop **C3** (legacy alias).

---

## R-NAMES · Long names follow alias policy

### Rule

Long names (3+ tokens, e.g., "Imam Abu Hamid Muhammad al-Ghazali", "Hatim bin Ism al-Asamm") MUST appear in full on first chapter mention, then use the short alias from `content/_shared/arabic/05-name-alias-policy.md` for every subsequent mention.

### Why

Listener readability. The customize prompt (R-NAMEALIAS in `notebooklm-customize-prompt-rules.md`) tells the hosts the same rule; the chapter file must already follow it so the hosts have something natural to read.

### Auto-detect

For each known long name in the chapter, count occurrences; flag if the alias is not used after first mention.

### Auto-fix or flag

**AUTO-FIX** when the alias is in the policy file (replace subsequent full-name occurrences with the alias). **FLAG (P1)** when an unknown long name appears (author proposes alias).

### Authority for challenger

`podcast-challenger` Loop **J2** (chapter-side counterpart to the framing-side check).

---

## R-SUBSTITUTION · Common Arabic terms substituted per policy

### Rule

Every Arabic term flagged in `content/_shared/arabic/04-common-term-substitutions.md` §2 (nafs, shaytan, ruh, qalb, aql, hawa, dunya, akhirah, jannah, jahannam, qiyamah, ilm, hikmah, sabr, shukr, niyyah, malak, zuhd, wara', tasawwuf) MUST be substituted with the English equivalent unless `00-framing.md` documents a justification for keeping the Arabic.

### Authority for challenger

`podcast-challenger` Loop **C4**.

---

## R-ATTRIBUTION · Every citation correctly attributed

### Rule

Every quote MUST carry attribution:
- Quran citations: `(Quran <Surah>:<Verse>)` with translator named on first per-chapter use
- Hadith: collection + number (e.g., `Sahih Bukhari 6502`)
- Imam Ali (AS): `Nahj al-Balagha`, sermon/letter/saying number
- Ismaili sources: named work + section
- Sufi sources: named author + work

### Auto-detect

Pattern scan per source type.

### Auto-fix or flag

**FLAG (P0)** for missing attribution; **FLAG (P1)** for ambiguous attribution (e.g., translator unnamed).

### Authority for challenger

`podcast-challenger` Loop **A1** (existing source-integrity check).

---

## R-NOFABRIC · No invented content

### Rule

The chapter file MUST contain no invented dialogue, fictionalized scenes, fabricated quotes, or `[CONTEXT NEEDED]` markers left unfilled at ship time.

### Auto-detect

Substring scan for `[CONTEXT NEEDED]`. Semantic check for content not traceable to source or whitelist enrichment.

### Auto-fix or flag

**FLAG (P0)** always.

### Authority for challenger

`podcast-challenger` Loop **A2** + **D5**.

---

## R-NO-ABBREVIATION · Full names of major works on every appearance

### Rule

Titles of canonical works MUST appear in their full, recognizable form **every time** they are mentioned. Forbidden contractions in the chapter: `the Ihya`, `EI`, `IUD`, `the Nahj`, `NJB`, `the Mishkat`, `the Sahifa`, `Sahihayn`. The hosts must be able to read the title once and have the listener recognize the work.

Allowed canonical forms (drawn from `enrichment-sources.md` Tier 1–6):
- `Ihya Ulum al-Din` (Ghazali, *Revival of the Religious Sciences*)
- `Kimiya al-Sa'ada` (Ghazali, *Alchemy of Happiness*)
- `Munqidh min al-Dalal` (Ghazali, *Deliverance from Error*)
- `Mishkat al-Anwar`, `Bidayat al-Hidaya`, `Jawahir al-Quran` (Ghazali)
- `Nahj al-Balagha` (Imam Ali (AS), the Peak of Eloquence)
- `Ghurar al-Hikam`, `Sahifa al-Sajjadiyya`
- `Sahih Bukhari`, `Sahih Muslim`, `Sunan Abu Dawud`, `Sunan Tirmidhi`, `Sunan Nasa'i`, `Sunan Ibn Majah`, `Riyad al-Salihin`

### Why

Empirical evidence from the *Architecture of Refusal* transcript: Ghazali's `Ihya Ulum al-Din` was abbreviated in the chapter as `the Ihya`, and the host called it `the EI`. Listeners cannot recognize an abbreviation they have never heard before; the hosts will not glide past an unfamiliar contraction smoothly.

### Auto-detect

Substring scan for the forbidden contractions above; flag any hit.

### Auto-fix

**AUTO-FIX** (deterministic) for the known list: `the Ihya` → `Ihya Ulum al-Din`; `the Nahj` → `Nahj al-Balagha`; `EI` → `Ihya Ulum al-Din`. Add new entries to the deterministic map as new works enter the corpus.

### Authority for challenger

`podcast-challenger` Loop **B7** (work-title abbreviation audit) — new check added 2026-05-17.

---

## R-OPENFRAME · Chapter opens with one-paragraph contextual frame

### Rule

Each chapter MUST open with a one-paragraph contextual frame ("This chapter covers …") so a listener landing mid-series can orient themselves. The frame is part of the chapter, not metadata. It is the only place the chapter is allowed to introduce itself.

### Why

NotebookLM hosts use this opening to set up the conversation. Without it, the hosts default to generic introductions.

### Auto-detect

Inspect first paragraph; must contain a topic-naming sentence.

### Auto-fix or flag

**FLAG (P1)**. Authoring decision.

### Authority for challenger

`podcast-challenger` Loop **E3** (existing beginning/middle/end arc check).

---

## Maintenance protocol

Same as `notebooklm-customize-prompt-rules.md` — append new rules as `## R-<NAME>` sections following the structure; add matching check to the agent; update the revision log.

---

## Revision log

- 2026-05-17 (later) — **Architectural pivot driven by empirical audit of 5 NotebookLM transcripts.** Replaced R-PHONETIC (inline phonetic guides) with R-PHONETICS-OUT (chapter ships clean transliteration; phonetic guidance lives in the customize prompt). Renamed R-HONORIFICS → R-HONORIFIC-ONCE with stricter language and build-script enforcement. Added R-NO-ABBREVIATION for canonical work titles. Root cause: NotebookLM reads parenthetical phonetics aloud as content, producing systematic doublings ("Sahih Sitta, sahasita") and mangled names ("tassel wolf" for *Tasawwuf*, "Najah Balala" for *Nahj al-Balagha*, "the EI" for *Ihya Ulum al-Din*).
- 2026-05-17 — Seeded with R-NOHTML, R-NOMETAPROSE, R-CROSSREF, R-NOEMDASH, R-WORDBAND, R-ENRICH60, R-MULTITIER, R-NOSTACK, R-PHONETIC, R-HONORIFICS, R-NAMES, R-SUBSTITUTION, R-ATTRIBUTION, R-NOFABRIC, R-OPENFRAME. Extracted from SKILL.md §0 Invariants 1–5 and §6 Output Rules plus podcast-challenger Loops A–G.
