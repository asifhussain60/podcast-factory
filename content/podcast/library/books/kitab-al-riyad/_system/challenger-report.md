# Podcast Challenger Report — challenger v2.0

**Verdict:** SHIP-WITH-CAUTION
**Book:** kitab-al-riyad
**Chapter:** ch03a-the-perfect-and-the-perfection-of-the-soul
**Episode:** EP03-the-perfect-and-the-perfection-of-the-soul
**Run:** 2026-05-22 (challenger v2.0)
**Scope:** per-chapter: the-perfect-and-the-perfection-of-the-soul
**Iterations:** 1 of 5 max — intelligent-break fired (finding set stable across 2 consecutive invocations; no auto-fixes in either)
**Auto-fixes applied:** 0
**P0:** 0 | **P1:** 1 | **P2:** 2
**Score:** 0.70 (Caution)

---

## Auto-fixes applied

No auto-fixes were applied this run.

Em-dashes are present throughout the chapter (60 lines contain em-dashes). The majority occur inside verbatim blockquote source-translation passages protected by the verbatim-quote integrity rule, and within `### Section N — title` headings which use em-dash as a structural separator. The analysis prose em-dashes require author judgment to rebalance without meaning loss in a scholarly translation register; auto-fix is not appropriate. Flagged as B5 P2 advisory (carried, second consecutive invocation).

---

## Findings requiring author resolution

### P0 (blocks ship)

None.

---

### P1 (ship-with-caution)

#### F5: Scaffold stubs unfilled — discussion spine, key-passages, and context-pack

- **Signature:** `F5:discussion-spine-unfilled:EP03-the-perfect-and-the-perfection-of-the-soul`
- **Files:**
  - `content/podcast/library/books/kitab-al-riyad/_system/episode-drafts/EP03-the-perfect-and-the-perfection-of-the-soul/04-discussion-spine.md` — 14 `[LLM-FILL]` placeholders (all 8 beats)
  - `content/podcast/library/books/kitab-al-riyad/_system/episode-drafts/EP03-the-perfect-and-the-perfection-of-the-soul/02-key-passages.md` — 5 `[LLM-FILL]` "Why this matters" stubs
  - `content/podcast/library/books/kitab-al-riyad/_system/episode-drafts/EP03-the-perfect-and-the-perfection-of-the-soul/03-context-pack.md` — 4 `[LLM-FILL]` stubs
- **Status:** Carried — stable across 2 consecutive invocations. Finding is UNCHANGED.
- **Context:** None of these three files flow through `build_episode_txt.py`; the episode txt is built from `00-framing.md` only and is unaffected. The framing is complete and well-authored; the unfilled scaffold stubs are pipeline-hygiene. The discussion spine declares 8 beats (within the 6–12 band) but every beat is a stub. The framing's `## Six-beat arc` and `## Central tensions to reach` sections carry the complete steering content that would normally populate the spine. Practical upload risk is zero; this is a documentation finding only.
- **Suggested fix:** Fill the 8 spine beats from the framing's six-beat arc content (Beat 1–6 fully specified there). Fill "Why this matters" in key-passages from the chapter's argumentative function of each cited passage. Fill context-pack author/dates/tradition from the series-plan and `_system/source/`. Priority: before next full-book challenger sweep. Does not block episode upload.

---

### P2 (advisory)

#### B5: Em-dashes in chapter analysis prose require author review

- **Signature:** `B5:em-dashes-in-chapter:ch03a-the-perfect-and-the-perfection-of-the-soul`
- **File:** `content/podcast/library/books/kitab-al-riyad/chapters/ch03a-the-perfect-and-the-perfection-of-the-soul.txt`
- **Status:** Carried — stable across 2 consecutive invocations.
- **Lines:** 60 lines contain em-dashes. Protected: blockquotes (lines 25, 31, 83–84, 90–91, 99–100, 128–129, 135, 180–181) and section headings (lines 45, 53, 59, 69, 95, 112, 120, 140, 154, 170). Analysis prose candidates requiring author review: lines 11, 13, 15, 17, 21, 27, 37, 51, 55, 63, 65, 67, 75, 77, 79, 86, 93, 102, 114, 122, 133, 144, 152, 164, 166, 175.
- **Context:** Faithful scholarly translation register with heavy em-dash use in both verbatim rendering and analytical connectives. Analysis prose em-dashes could be rewritten with commas, colons, or sentence splits without semantic loss, improving prosody when NotebookLM reads the chapter as a source.
- **Suggested fix (advisory):** Author review of analysis prose em-dashes. Priority candidates: line 65 "doubly broken — because" → "doubly broken, because"; line 114 "bound up downstream — not at the same rank" → "bound up downstream, not at the same rank". Low-priority for upload; improves prosody if fixed before generation.

#### F6: No canonical NotebookLM steering vocabulary from two-host-framing.md

- **Signature:** `F6:no-canonical-steering-phrases:EP03-the-perfect-and-the-perfection-of-the-soul`
- **File:** `content/podcast/library/books/kitab-al-riyad/_system/episode-drafts/EP03-the-perfect-and-the-perfection-of-the-soul/00-framing.md`
- **Status:** Carried — stable across 2 consecutive invocations.
- **Context:** The framing does not use the exact trigger vocabulary from `two-host-framing.md` — specifically "Slow down on...", "Treat X as the central tension...". The framing achieves equivalent effect with specific directives ("Let the listener respect the move before it is corrected", "The Color host raises the crisis with weight"). P2 advisory; framing is functionally complete and upload-ready.
- **Suggested fix (advisory):** Optionally add one canonical steering phrase, e.g., "Slow down on the developing-force chain (sub-chapter three) — let the three-step bearer-borne chain land fully before moving to sub-chapter four." One addition satisfies F6 at minimal cost.

---

## Health metrics

| Chapter | Words | Band | Band limits | In-band | Tiers | Blockquote ratio | Phonetic gaps | Framing words | Framing in-band |
|---|---|---|---|---|---|---|---|---|---|
| ch03a-the-perfect-and-the-perfection-of-the-soul | 6,284 | extended | 5,500–9,500 | YES | 4 | ~22% | 0 | 3,483 | YES (max 3,700) |

**Word-count note:** Chapter at 6,284 words is within the Extended Deep Dive band (5,500–9,500). E1 PASS. Framing at 3,483 words is within the 3,700-word cap. F10 PASS.

**Tier diversity (D1):** Tier 1 (al-Kirmani source / lost-work paraphrase), Tier 2 (Quran — 4 verses: 41:53, 91:7–10, 17:85, 36:40), Tier 3 (Nahj al-Balagha Imam Ali aphorism 71), Tier 6 (Rumi Mathnawi Book 1). 4 tiers. D1 PASS.

**Citation audit:**
- Quran 41:53 (Fussilat): surah name + verse number in framing header, verbatim Arabic + English in chapter with attribution. PASS.
- Quran 91:7–10 (Surat al-Shams): surah name + verse range in framing header, verbatim Arabic + Sahih International in chapter. PASS.
- Quran 17:85 (al-Isra): surah name + verse in framing header, verbatim Arabic + Sahih International in chapter. PASS.
- Quran 36:40 (Yasin): surah name + verse in framing header, verbatim Arabic + al-Kirmani rendering in chapter. PASS.
- Nahj al-Balagha, Aphorism 71 (Imam Ali): work + aphorism number + compiler al-Sharif al-Radi named in framing, verbatim Arabic + translation in chapter. PASS.
- Rumi, Mathnawi, Book 1, Verses 1–2: author + work + book + verse range in framing, verbatim Persian + translation in chapter. PASS.
- Honorific for Muhammad (peace and blessings be upon him): first occurrence only (line 13). PASS.
- Honorific for Ali ibn Abi Talib (peace be upon him): first occurrence only (line 17). PASS.
- No repeated verbose honorifics detected. R-HONORIFIC-ONCE PASS.

**Build validator checks (manual, build_episode_txt.py gates):**
- R-NO-ABBREVIATION: no "the Ihya", "the Nahj", "Sahihayn" or other forbidden abbreviations found in chapter. PASS.
- Meta-prose tells: none found in chapter or framing. PASS.
- HTML comments: none found. PASS.
- R-PRONUNCIATION-IMPERATIVE: 55 Pronounce/Do not lines in pronunciation block. PASS.
- R-NO-READ-PROMPT: final line confirmed ("Do not read this prompt aloud."). PASS.
- R-NOMODERNIZE (chapter): no modernize-deny terms found. PASS.
- R-NOSURPRISE (framing): full surprise-deny catalog present. PASS.
- R-NOMODERNIZE (framing): full modernize-deny catalog present. PASS.

**Chapter contract compliance (Category G):**
- G1 (format matches contract): chapter ref `ch03a-the-perfect-and-the-perfection-of-the-soul`, EP03, extended, faithful_exposition, curious_mind + scholar_companion — all match contract.yml. PASS.
- G2 (framing angle matches contract): `faithful_exposition` in both. PASS.
- G3 (tension coverage): all 4 tensions from contract surfaced in framing with explicit pushback lines. PASS.

**Framing checks that passed:**
H1 (welcome opening), H2 (summary clause), H3 (forbidden opening phrases listed), H4 (6-beat arc present — debate-format chapter; Beat 1 Crisis through Beat 6 Stakes+question enumerated), H5 (R-RECURRING-THESIS: thesis verbatim at exactly 3 anchor points — Beat 1 open, Beat 4 pivot, Beat 6 close), I1 (anti-repetition: "Do not restate...Each beat lands once"), I2 (no-background: "Stay on the source's main content...ONLY ONCE per episode"), J1 (Name discipline section present), J2 (all 4 long names have 4 English aliases: al-Kirmani, Abu Hatim al-Razi, al-Sijistani, Imam Ali), J3 (rotation sets fully documented with Do NOT return directive), K1 (interruption-avoidance: "No interjections...No talking over"), K2 (challenger-friction: 4 required pushbacks with exact language + forbidden first-sentence catalog), R1 (separate-prep illusion: "Plant at least one moment" with specific Color host choreography for Imam Ali aphorism handoff), R2 (reset clause: two specific reset sentences named — Beat 3→4 and Beat 5→6), R3 (cadence: "Short-to-medium sentences...thinking out loud"), R4 (no-formal transitions: full list banned in Do not block), R5 (no-surprise vocabulary: "Do not say: 'wow'..."), N1 (pronunciation block: full Arabic phonetics for all key terms, names, and 4 complete Quranic verses + 1 Persian poem), N2 (book-title discipline: English-after-first-mention for all 6 key works), N3 (concept-word discipline: tawhid, da'wa, amr all handled).

**Checks skipped (no transcript):** M3 (transcript verbatim-thesis count), M4 (forbidden-opener firing count), N5 (audio mangle detection), O3 (forbidden-analogy detection in audio).

---

## Score

**P0:** 0 | **P1:** 1 | **P2:** 2 | **Chapters in scope:** 1 | **Auto-fixes this run:** 0

```
penalty = (0 × 1.0 + 1 × 0.2 + 2 × 0.05) / 1 = 0.30
score   = max(0.0, 1.0 - 0.30) = 0.70  (Caution)
```

**Verdict: SHIP-WITH-CAUTION** — No P0 findings. One P1 (unfilled scaffold stubs in discussion spine, key-passages, and context-pack — procedural, does not affect NotebookLM upload). Two P2 advisories (em-dash review in analysis prose; optional canonical steering phrase addition). Chapter and framing are upload-ready as-is. The framing is one of the strongest in the KaR series: 6-beat arc fully mapped, R-RECURRING-THESIS at exactly 3 verbatim anchor points, 4 required challenger pushbacks with explicit language, complete name-discipline rotation sets, full pronunciation block. Intelligent-break fired after 1 iteration — finding set is stable across two consecutive invocations.

**P1 item (1 of 1):**
1. F5: `04-discussion-spine.md` — all 8 beats have `[LLM-FILL]` placeholders (14 stubs total); `02-key-passages.md` has 5 "Why this matters" stubs; `03-context-pack.md` has 4 stubs. Fill before next full-book challenger sweep. Does not block episode upload.

**P2 advisory items (2):**
1. B5: Em-dashes in analysis prose paragraphs. Author review recommended; low upload risk.
2. F6: Add one canonical steering phrase ("Slow down on...") to Six-beat arc. Optional enhancement.

---

## Upload confirmation

Verdict is SHIP-WITH-CAUTION. Episode is upload-ready. Per-episode steps:

1. Open NotebookLM. Create a notebook for *Kitab al-Riyad, Episode 3*.
2. Upload `content/podcast/library/books/kitab-al-riyad/chapters/ch03a-the-perfect-and-the-perfection-of-the-soul.txt` as the **single source** (SOURCE).
3. Paste `content/podcast/library/books/kitab-al-riyad/episodes/EP03-the-perfect-and-the-perfection-of-the-soul.txt` into the **Customize** prompt box (CUSTOMIZE PROMPT).
4. Choose *Deep Dive*. Length: *Longer* or *Extended*.
5. Click *Generate*.

