# Pipeline debt — framework gaps observed in flight, queued for fix

Tracks framework-level gaps in the podcast pipeline that today's per-book operator runs have surfaced. Each entry is a fix that lives in the pipeline code/prompts/rules — NOT in any single book's content. When a fix lands, it benefits every future book the pipeline processes (Raahat al-Aqal, Kitab Maqbas, Rasail Ikhwan AsSafa, etc.) automatically.

Both Air and Studio sessions write to this file (multi-writer, per `operators/coordination-protocol.md §14`). Add new items at the bottom of the relevant section. Use F-prefix IDs (F1, F2, ...) for framework debt items so they don't collide with X-prefix runtime fixes that are already-shipped code patches.

## Active framework debt

| ID | Title | Discovered | Severity | Status | Owner |
|---|---|---|---|---|---|
| F1 | Phase 0g framing-gen LLM ignores hard word-count caps | 2026-05-21 (KaR EP14) | High | Triaged ([X10](https://github.com/asifhussain60/Journal/commit/HEAD) added per-section caps + self-check in author_framing prompt) | — |
| F2 | Phase 0g framing-gen produces unused pronunciation entries | 2026-05-21 (KaR EP14) | Medium | Triaged ([X10](https://github.com/asifhussain60/Journal/commit/HEAD) prompt now requires grep chapter for terms before generating entries) | — |
| F3 | Phase 0e enrichment emits manuscript-history meta-commentary that NotebookLM hosts then vocalize | 2026-05-21 (KaR ch03a et al.) | High | Open | — |
| F4 | Phase 0d chapter design includes editorial-intro chapters that aren't substantive book content | 2026-05-21 (KaR ch01a) | Medium | Open | — |
| F5 | Phase 0e enrichment emits repeated honorific glyphs (ﷺ) per chapter; R-HONORIFIC-ONCE flags downstream | 2026-05-21 (KaR ch08/ch09/ch12/ch14b) | Medium | Open | — |
| F6 | Cost-ledger silently fails on Python 3.9 due to `datetime.UTC` (3.11+ feature) | 2026-05-21 (KaR Phase 0g) | Medium | Open | — |
| F7 | Orchestrator doesn't surface multi-task cost projection before starting long runs | 2026-05-21 (KaR Phase 0g) | Low | Open | — |
| F8 | Stale `episode-drafts/EP*` directories accumulate across X-class fix cycles; no auto-clean on resume | 2026-05-21 (KaR EP14b) | Low | Open | — |
| F9 | R-PHONETICS-OUT pattern #1 was over-broad; suggests rule-set audit for intent/implementation alignment | 2026-05-21 (KaR EP14 first attempt) | Low | Triaged ([X5](https://github.com/asifhussain60/Journal/commit/c9424dd) fixed pattern #1; audit remaining patterns) | — |
| F10 | Word-band rules with "~" prose use exact thresholds in code (no tolerance) | 2026-05-21 (KaR ch12/ch14b at 10180/10112) | Low | Triaged ([X6](https://github.com/asifhussain60/Journal/commit/801d2fd) bumped chapter ceiling 10000→10500; framing band 3500 still exact) | — |

---

## Item details

### F1 — Phase 0g framing-gen LLM ignores hard word-count caps

**Where:** `scripts/podcast/_authoring.py:author_framing()` lines 1158–1187, the `claude -p` prompt that generates `00-framing.md`.

**What goes wrong:** The prompt explicitly says `"Length: Default tier 200–500 words; Extended tier 1,000–1,800 body words + pronunciation block; hard cap 3,500 words per build_episode_txt.py"`. For KaR EP14, the LLM produced 4,959 words anyway — 41% over the cap. Validator then halted on R-FRAMING-WORD-BAND.

**Impact:** Every chapter whose generated framing overshoots the cap requires a manual `claude -p` trim pass ($1–3 + 5–10 min editor time per episode). At-scale, this is ~12 retries per book × queued books = 60+ retries projected.

**Proposed fix:** Add explicit per-section word caps in the framing-gen prompt (e.g., `Pronunciation: max 800 words; Central tensions: max 500 words; Three-part focus: max 500 words; other sections: max 200 words each`). Optionally: instruct the LLM to self-check word count before returning, and re-trim if over.

**Verification:** Re-run framing-gen for one over-budget chapter (e.g., ch14b) and confirm output ≤ 3500 words without manual trim.

---

### F2 — Phase 0g framing-gen produces unused pronunciation entries

**Where:** Same prompt as F1; the Pronunciation section in particular.

**What goes wrong:** The prompt instructs `"Use imperative \`Pronounce \"X\" as \"Y\". Say it as one fluent word.\` for every Arabic term that appears in the chapter (consult \`_phonetics.md\` first)"`. The LLM correctly consults `_phonetics.md` but generates entries for EVERY phonetics-mapped term in the BOOK, not just terms in this CHAPTER. For KaR EP14, 19 of the pronunciation entries were for terms not in ch14b — pure padding.

**Impact:** Inflates the framing word count (the Pronunciation section was the single biggest contributor to EP14's overflow). Wastes NotebookLM's customize-prompt budget on unused entries.

**Proposed fix:** Tighten the prompt — explicitly instruct: `"First, grep the chapter file for every Arabic/transliterated term. Then for each term found, look up its phonetic in _phonetics.md and generate one imperative line. Do NOT generate entries for terms not present in the chapter file."` Alternative: do the grep deterministically in Python before invoking the LLM, and pass only the chapter-relevant subset of `_phonetics.md`.

**Verification:** Re-run framing-gen for a name-dense chapter (ch14b) and confirm only terms appearing in the chapter source get pronunciation entries.

---

### F3 — Phase 0e enrichment emits manuscript-history meta-commentary

**Where:** `scripts/podcast/_authoring.py:author_phase_0e()` (or equivalent — the enrichment prompt that produces `chapters/ch##-*.txt`).

**What goes wrong:** Phase 0e enriches the source into NotebookLM-ready prose. The current prompt produces sections like `"## What survives at the head of the manuscript"` followed by paragraphs about "damaged folios," "reconstructed fragments," "the text breaks off." These are editorial framings about the manuscript's physical condition that have no place in the spoken audio — NotebookLM hosts will read them aloud and the listener gets meta-commentary about the manuscript instead of the philosophy.

**Impact:** Five KaR chapters carry this noise (ch03a heaviest, then ch04b/ch07/ch15). Each affected chapter needs hand-cleanup before its episode ships.

**Proposed fix:** Add a "Do NOT include" instruction to the Phase 0e prompt: `"Do not write editorial framings about the source manuscript's physical state (damaged folios, reconstructed fragments, OCR breakdowns, translator's notes, editor's notes). The chapter file is the spoken content — only include prose the hosts should discuss as substantive philosophy."`

**Verification:** Re-run Phase 0e for one chapter (preferably without piping back to NotebookLM — just verify the output prose) and confirm no manuscript-meta language.

---

### F4 — Phase 0d chapter design includes editorial-intro chapters

**Where:** `scripts/podcast/_authoring.py:author_phase_0d()` — the chapter-design step that maps source abwāb/fusūl to podcast episodes.

**What goes wrong:** For KaR, Phase 0d produced ch01a — "The Four Da'is and the Debate" — as one of 14 episodes. But ch01a's entire body is editor Aref Tamer's introduction to the book (biographies of the three preachers, chain of four debate-books, historical setup). None of it is al-Kirmani's own prose. It shipped as an episode contract anyway.

**Impact:** Asif had to manually drop ch01a from the series after observing the content. For a book with extensive editorial frontmatter (which most scholarly editions have), this happens by default.

**Proposed fix:** Phase 0d should distinguish "content chapters" (the author's own prose) from "editorial frontmatter" (editor's intro, translator's preface, manuscript history) and either (a) skip frontmatter entirely from the episode plan, or (b) emit it as `intro-context` non-episode metadata for the series plan to optionally use.

**Verification:** Run Phase 0d on a book with substantial editorial frontmatter (e.g., a future scholarly edition) and confirm the editor's intro doesn't show up as an episode contract.

---

### F5 — Phase 0e enrichment emits repeated honorific glyphs

**Where:** `scripts/podcast/_authoring.py:author_phase_0e()` — same prompt as F3.

**What goes wrong:** Phase 0e generates chapter prose that uses the honorific glyph ﷺ (sallallahu alayhi wa sallam) multiple times per chapter. For KaR: ch12 had 26 occurrences, ch14b had 11, ch08 and ch09 had 3 each. The R-HONORIFIC-ONCE rule then halts the episode at Phase 0g build step because NotebookLM vocalizes every glyph as the full phrase.

**Impact:** Four chapters required manual dedup. ([X6 fix](https://github.com/asifhussain60/Journal/commit/801d2fd) deduplicated KaR's chapter files but the underlying enrichment prompt still emits the repeats.)

**Proposed fix:** Add to the Phase 0e prompt: `"Honorific glyphs (ﷺ, peace be upon him, etc.) should appear AT MOST ONCE per figure per chapter — on first mention. Subsequent mentions use the contracted name only."`

**Verification:** Run Phase 0e on a chapter known to be prophet-dense (e.g., a future book's prophetic-cycle chapter) and confirm ≤1 occurrence of ﷺ per figure.

---

### F6 — Cost-ledger silently fails on Python 3.9

**Where:** `scripts/podcast/_authoring.py:_run_claude_p()` — the per-LLM-call cost-ledger append.

**What goes wrong:** Throws `AttributeError("module 'datetime' has no attribute 'UTC'")` on every Claude shell-out. `datetime.UTC` is Python 3.11+. Air runs Python 3.9 (per `infra/azure/store-keychain-keys.sh` and observed runtime). The cost-ledger silently fails to record spend; the orchestrator continues without halting.

**Impact:** Spend on Air-run books is not tracked. Need to reconstruct retroactively from wall-clock + per-episode rates. Studio (which probably runs 3.11+) is unaffected.

**Proposed fix:** Replace `datetime.UTC` with the compatibility-safe `datetime.timezone.utc`. Verify across all callsites.

**Verification:** Re-run any Phase that calls `_run_claude_p` on Python 3.9 and confirm `cost-ledger.jsonl` gets appended successfully.

---

### F7 — Orchestrator doesn't surface multi-task cost projection

**Where:** `scripts/podcast/orchestrate_book.py:_drive_authoring_through_0f()` and the per-chapter loop in `run_resume()`.

**What goes wrong:** When resuming after Phase 0f, the orchestrator launches into per-chapter authoring for all queued chapters without surfacing the projected total spend. For KaR, this means starting a run that will burn $14-42 across 14 episodes without an explicit "this exceeds the $20 multi-task cost ceiling" warning.

**Impact:** Asif has to mentally project the spend each time. The coord-protocol cost cap is advisory not enforced.

**Proposed fix:** At resume time, before entering the per-chapter loop, the orchestrator computes `remaining_episodes × estimated_per_episode_cost` and either prints a warning or requires `--accept-cost N` if over the cap.

**Verification:** Resume a book at the per-chapter phase and confirm the orchestrator surfaces the projection before starting.

---

### F8 — Stale `episode-drafts/EP*` directories accumulate

**Where:** `scripts/podcast/orchestrate_book.py:per_chapter_pass()` and `_authoring.py:author_framing()`.

**What goes wrong:** When an X-class bug causes the orchestrator to write a framing to the wrong directory (e.g., `EP14b/` instead of `EP14/`), the wrong directory persists across subsequent runs. Manual cleanup commits are required (KaR did this multiple times today).

**Impact:** Confusing filesystem state; risk that the validator picks the wrong directory.

**Proposed fix:** At per-chapter loop start, scan `_system/episode-drafts/` for any directory whose name doesn't match the expected `EP##-<slug>` for the chapters in `chapters/`. Either delete (aggressive) or warn (conservative).

**Verification:** Trigger an X-class bug scenario, then run resume; confirm stale directories are cleaned (or surfaced for cleanup).

---

### F9 — R-PHONETICS-OUT pattern set audit needed

**Where:** `scripts/podcast/build_episode_txt.py:168-179` — `INLINE_PHONETIC_PATTERNS`.

**What goes wrong:** Pattern #1 was over-broad — matched scholarly Arabic transliterations alongside true pronunciation guides. Fixed in [X5 commit c9424dd](https://github.com/asifhussain60/Journal/commit/c9424dd). But the other R-* rules in the validator may have similar intent-vs-implementation drift.

**Status:** Triaged — X5 fixed the immediate hit. Remaining work: audit each R-* rule's regex against its handbook-defined intent, looking for false-positive risk.

**Proposed fix:** Pair each rule's regex with a unit test exercising both "should match" and "should not match" cases. Today none of the validator rules have unit tests.

**Verification:** Run the audit; produce a rule-set health report.

---

### F10 — Word-band rules with "~" prose use exact thresholds in code

**Where:** `scripts/podcast/build_episode_txt.py` — `CHAPTER_WORD_MAX_HARD`, `FRAMING_WORD_MAX`, etc.

**What goes wrong:** The rule prose in `content/podcast/.skill/handbook/notebooklm-best-practices.md` says things like `"episodes over ~10,000 words risk..."`. The tilde is empirical-tolerance language. But the code enforced exact 10000. For KaR ch12 (10180) and ch14b (10112), the chapters were 1-2% over a round-number cap and got blocked.

**Status:** Triaged — [X6](https://github.com/asifhussain60/Journal/commit/801d2fd) bumped `CHAPTER_WORD_MAX_HARD` from 10000 → 10500 (5% tolerance, aligning code with prose). `FRAMING_WORD_MAX` (3500) is still exact.

**Proposed fix:** Apply the same alignment to `FRAMING_WORD_MAX` if its prose source carries similar "~" language. Or introduce a `TOLERANCE_PCT` constant that derives soft/hard bands from a single source-of-truth threshold.

**Verification:** Run a book whose framing lands at 3501 and confirm the validator's response is consistent with the prose's stated intent.

---

## Closed / shipped (historical)

For X-class fixes that have already shipped, see git log on `book/kitab-al-riyad`. As of 2026-05-21:

| ID | Title | Shipped commit |
|---|---|---|
| X1, X2 | Earlier Phase 0g blockers + state reset | [b8a2b82](https://github.com/asifhussain60/Journal/commit/b8a2b82) |
| X3 | Strip letter suffix from chapter filename when forming episode_id (orchestrate_book.py) | [562b7d5](https://github.com/asifhussain60/Journal/commit/562b7d5) |
| X4 | Don't renormalize chapter filename in extract_chapter (preserve letter suffix) | [ba52d21](https://github.com/asifhussain60/Journal/commit/ba52d21) |
| X5 | R-PHONETICS-OUT regex tightened (pattern #1 had false-positive on scholarly transliterations) | [c9424dd](https://github.com/asifhussain60/Journal/commit/c9424dd) |
| X6 | ﷺ honorific dedup across 4 chapters + chapter word-band 10000→10500 | [801d2fd](https://github.com/asifhussain60/Journal/commit/801d2fd) |
| X7 | Mirror X3 fix in _authoring.author_framing() (second code path) | [95c4569](https://github.com/asifhussain60/Journal/commit/95c4569) |

## How to use this file

When a new framework gap surfaces:
1. Add a row to the "Active framework debt" table at the top
2. Add the detail block to "Item details"
3. If it's a code patch that ships in the same session (like the X-class fixes), close it: move the row out of the active table, add to "Closed / shipped"
4. Commit on the active book branch; merge to develop with the next book ship

When triaging:
- **Severity High** — actively blocks a book in flight or wastes substantial operator time per episode
- **Severity Medium** — wastes operator time per book; would be felt on next book
- **Severity Low** — observed but mitigated; nice to fix when there's slack
