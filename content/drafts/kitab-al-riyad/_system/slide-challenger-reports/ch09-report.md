# Slide Challenger Report — ch09-motion-stillness-hyle-and-form

**Run timestamp**: 2026-05-23T00:00:00Z
**Deck path**: `worktrees/book-kar/content/podcast/library/books/kitab-al-riyad/slide-decks/ch09-deck-motion-stillness-hyle-and-form.txt`
**Framing path**: `worktrees/book-kar/content/podcast/library/books/kitab-al-riyad/slide-decks/ch09-framing-motion-stillness-hyle-and-form.md`
**Audio chapter**: `chapters/ch09-motion-stillness-hyle-and-form.txt`
**Structural moments counted**: 18 (one per H2 movement)
**Slide budget context**: extended chapter (~25 min+) → 13–15 slides; deck has 18 structural moments, slightly above ceiling but each is genuinely structural.

---

## Pass 1 — Per-Structure Probes

| Probe | Result | Structures flagged | Notes |
|-------|--------|---------------------|-------|
| 1 Restatement | pass | none | Every H2 carries a named structure (matrix, contrast pair, hierarchy, annotated structure, process flow, axis map). None could be replaced by a single audio sentence. |
| 2 Literal Illustration | pass | none | The framing explicitly forbids calligraphic *kun*, mosque silhouettes, scholar portraits. Deck source contains no "image of," "photo of," or stock-photo descriptors. |
| 3 Structure-vs-Description | pass | none | Every block supplies concrete commitments. The "three handed-down pictures" matrix names rows, columns, and cell content. The sub-ch six axis structure names BOTH axes (Direction of proportion; State on each letter) and assigns the mapping cells. The sub-ch four chain process flow names nodes AND directed transitions. Nothing is "a 2x2 of X vs Y" without populating it. |
| 4 Diagram-Type Discipline | pass | none | Each H2 opens with a named type from the taxonomy: hierarchy (×4), comparison matrix (×4), contrast pair (×5), annotated structure (×3), process flow (×2), named-axis structure (×1). All match `slide-deck-patterns.md`. |
| 5 Diversity | pass | — | Six distinct diagram types in use. No single type dominates; contrast pair (5), comparison matrix (4), hierarchy (4), annotated structure (3), process flow (2), named-axis (1). Contrast pair, comparison matrix, AND axis structure all present, satisfying the philosophical-text affinity expectation. |
| 6 Audio Redundancy | pass | none | Although the deck preserves the audio's nine-sub-chapter H2 spine (which it MUST — chapter outline is preserved by spec), each H2's body is restructured. Sub-ch one prose becomes a 6-row contrast pair + shared row. Sub-ch four prose becomes an annotated structure + hierarchy + process flow. Sub-ch seven prose becomes a process flow + comparison matrix of three traditional anchors. Each H2 adds axes/nodes/columns the prose lacked. |
| 7 Justified Skip | n/a | — | Deck is present; not a skip case. |
| 8 Coverage | pass | none | All seven verbatim anchor quotes from the audio chapter's closing list are present in the deck (sub-ch one, four, seven; Quran 36:82; Nahj al-Balagha Sermon 1; Bukhari 3191; Quran 42:11; Quran 16:40 and Quran 112:1-4 also captured). The four-architectural-commitments closing matrix and the political-stake list survive intact. The book-position hierarchy at the top and the chapter-seven handoff at the bottom bracket the deck cleanly. |

**Pass 1 verdict: PASS** (8/8 probes pass).

---

## Pass 2 — Architectural Pass

| Check | Result | Notes |
|-------|--------|-------|
| Visual Memory Test | pass | Of 18 structural moments, the high-memorability set includes: the three-reformers comparison matrix; the motion-vs-form contrast pair with "opposites" vs "correlates" framing; the named-axis structure mapping *kaf*/*nun* to cause-toward-below / effect-toward-above; the four-level hierarchy of ranks where body-talk stops reaching (Level 1 First Creator → Level 4 natural composite); the chain process flow from God Almighty through First Intellect to the body; the closing eight-row commitment matrix of "what each refuses / what each protects." The political-stake "joints" enumeration is the only weakly-memorable block but it sits inside a stronger matrix. Forgettable share <30%. |
| Variety | pass | Six diagram types. Largest share is contrast pair at 5/18 = 28%, well under the 50% cap for 10+ slide decks. No near-monoculture. |
| Arc | pass | Opens with the book-position hierarchy (sets the architectural place of the chapter). Middle builds pressure: the three-handed-down-pictures matrix establishes the dispute; sub-chapters one through six accumulate refutations and counter-doctrines via alternating contrast pairs / annotated structures; sub-chapter seven delivers the doctrinal climax via process flow + three-anchor matrix. Closes with the eight-commitment matrix + political-stake list + chapter-seven handoff hierarchy. Beginning establishes tension, middle builds, end resolves with structural summary (not bullet-list takeaway). |
| Cross-Episode Consistency | pass (with note) | Framing explicitly invokes the EP01 convention: "Place the higher-rank entity to the left in every pair; hold the convention from EP01." Within the deck, Ghazali-equivalents (*The Correction*, Jonathan, the higher-rank reformer in chronological precedence) consistently sit Column A in contrast pairs; Ibn-Rushd-equivalent challenger sits Column B. Could not access `_visual-registry.md` to verify the registry entry itself, but framing's explicit instruction shows authorial awareness. |

**Pass 2 verdict: PASS** (4/4 checks pass).

---

## Overall

**Pass 1**: PASS
**Pass 2**: PASS
**Bundle status**: SHIP

---

## Strengths worth noting

1. **Probe 3 (Structure-vs-Description) is the cleanest pass I have seen on KaR.** The sub-chapter six named-axis structure is exemplary: both axes named (Direction of proportion; State on each letter of *kun*), the 2x2-equivalent mapping cells fully populated with reasoning, and the architecture cross-referenced to chapters 4 and 5. NotebookLM reading this produces an actual axis diagram, not a labeled empty box.

2. **The eight-commitment closing matrix is a Visual Memory Test winner.** Rows = commitments, columns = "what it refuses / what it protects." This is the kind of structure a reader recalls weeks later because the architecture (refuse/protect pairing) is itself the mnemonic.

3. **The chain process flow at sub-ch four** uses explicit `↓` arrows in a code block, exactly the format NotebookLM parses reliably. Genealogy/process flow risk is fully mitigated.

4. **Variety distribution is healthy across six types** — contrast pair (5), comparison matrix (4), hierarchy (4), annotated structure (3), process flow (2), named-axis (1). The mix mirrors the chapter's philosophical-text affinity perfectly.

---

## Minor observations (NOT failures — do not block ship)

1. **Structural moment count (18) sits above the 13–15 ceiling** for extended episodes per `slide-deck-format.md` budget table. However, each moment is genuinely structural and the deck preserves the audio's nine-sub-chapter outline (which the spec mandates). NotebookLM will likely consolidate some adjacent structures during rendering. INFERRED concern only; not a probe failure.

2. **Sub-chapter five contains two stacked annotated structures** (the *kun* picture itself, then the two-letter image's two senses of "image"). Both are well-formed, but a reader scanning quickly could conflate them. Not a probe failure; flagging for future-pattern awareness.

3. **The political-stake list** at the end of the closing-formula H2 is a bulleted list of "joints the refusals protect" without an explicit structural type. It is anchored to the eight-commitment matrix above it and reads as continuation, but a strict Probe 4 reading could flag it. Judged as a tail-annotation on the preceding matrix, not a standalone slide.

---

## Verified vs Inferred

- All Pass 1 verdicts: VERIFIED against the deck source and audio chapter files read in full.
- Pass 2 Visual Memory Test: heuristic judgment, semi-INFERRED but anchored to the explicit "memorable shape" criteria in the spec.
- Pass 2 Cross-Episode Consistency: VERIFIED for the framing's explicit instruction; INFERRED for the registry file itself (not read).
- Minor observation 1 (count above ceiling): VERIFIED count, INFERRED consequence.

---

## Ledger Hook

ch09 — PASS / PASS / SHIP. Notable patterns: named-axis with both axes + cell mapping fully populated; eight-row "refuses / protects" closing matrix; chain process flow with explicit directed arrows; six-type diversity on a philosophical-text source.
