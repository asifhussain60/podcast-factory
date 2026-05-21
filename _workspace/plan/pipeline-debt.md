# Pipeline debt — framework gaps observed in flight, queued for fix

Tracks framework-level gaps in the podcast pipeline that today's per-book operator runs have surfaced. Each entry is a fix that lives in the pipeline code/prompts/rules — NOT in any single book's content. When a fix lands, it benefits every future book the pipeline processes (Raahat al-Aqal, Kitab Maqbas, Rasail Ikhwan AsSafa, etc.) automatically.

Both Air and Studio sessions write to this file (multi-writer, per `operators/coordination-protocol.md §14`). Add new items at the bottom of the relevant section. Use F-prefix IDs (F1, F2, ...) for framework debt items so they don't collide with X-prefix runtime fixes that are already-shipped code patches.

---

## Lessons learned — meta-patterns across F1–F15

First-read map for new operators. The 15 individual debt items collapse into 7 recurring meta-patterns. Each pattern is what to WATCH FOR in the next book. When a defect surfaces, ask "which Mn does this look like?" — if it matches, the proposed fix shape is already in this file; if it doesn't, you've found M8.

### M1 — LLM ignores explicit caps without self-check OR downstream validator

**Items:** F1 (framing word caps), F2 (unused pronunciation entries), F5 (honorific dedup), F14 (Arabic name repetition), F15 (analogy proliferation + dramatic tension).

**The deeper truth:** The framing-gen / enrichment LLM reads rules but doesn't enforce them. Every cap needs prompt-self-check AND ideally a post-hoc validator gate. Today's X-fixes added self-checks (X10/X14/X15/X16); validator gates remain missing for most rules.

**Triage status:** All 5 items Triaged via prompt-self-check additions. Validator coverage gap is the next framework session priority.

**Watch for:** any new "the LLM produced X over the explicit cap" pattern. Default response: add prompt self-check AND a validator rule simultaneously.

### M2 — Phase 0e enrichment under-disciplined

**Items:** F3 (manuscript-meta), F5 (honorifics in source prose), F13 (inline phonetics in chapter txt), F14 (Arabic name repetition in chapter prose).

**The deeper truth:** Phase 0e emits the chapter source — the file NotebookLM uploads as SOURCE. Every R-rule violation here cascades directly to spoken audio. The Phase 0e prompt is the most leveraged enrichment guard in the entire pipeline.

**Triage status:** Triaged via X14 (R-NO-MANUSCRIPT-META, R-HONORIFIC-ONCE strengthened) + X15 (R-NAMEDISCIPLINE). Empirical verification awaits next book (KaR's chapters were authored before these patches landed).

**Watch for:** any chapter that ships with rule violations only Phase 0e could have introduced (e.g., manuscript-meta paragraphs, repeated honorifics in prose, Arabic-name density). Audit Phase 0e output of the FIRST chapter of the next book carefully.

### M3 — Phase 0d classification heuristics weak

**Items:** F4 (editorial-intro chapters scheduled as episodes), Ch07 host_dynamic mis-assignment (noted under F15's "Related root cause" section).

**The deeper truth:** Phase 0d picks `episode_format` and `host_dynamic` from chapter content without enough empirical structure. Adjudicative chapters get curious_mind+scholar_companion (supportive); editorial intros get full episode contracts. The heuristic needs sharper classification rules.

**Triage status:** Open (F4); Ch07 case documented under F15 but not separately patched.

**Watch for:** any chapter that ships with the WRONG host_dynamic for its rhetorical structure (debate-content with non-debate pairing) OR an editorial intro/foreword that wasn't manually dropped.

### M4 — Orchestrator state-machine has rough edges

**Items:** F8 (stale episode-draft directories), F11 (iter-1 ship + iter-2 timeout treated as chapter failure), F12 (episode IDs from filename digits vs `contract.episode_number`).

**The deeper truth:** Several spots where orchestrator semantics surprise the operator — "tree not clean" blocks after partial writes; "FAILED" verdicts when episodes actually shipped; episode IDs encoding non-listener-facing data. Each individually small; together a fluent-resume gap.

**Triage status:** F8 Triaged (X13 sweep in pre-flight + per-chapter entry). F11 + F12 still Open.

**Watch for:** any resume cycle that requires manual state patching. Each manual patch is a sign this meta-pattern needs another fix.

### M5 — Empirical thresholds vs handbook "~" prose use exact thresholds in code

**Items:** F10 (chapter word band + framing word band).

**The deeper truth:** Handbook says "episodes over ~10,000 words risk…"; code enforced exactly 10,000. Pattern recurs across all soft-with-tolerance limits. Single `TOLERANCE_PCT` constant would generalize the alignment.

**Triage status:** Triaged via X6 (chapter ceiling 10000→10500) + X13 (framing ceiling 3500→3700). Generalization to TOLERANCE_PCT not yet done.

**Watch for:** other "~X" in handbook prose that the code still enforces exactly. Audit on next framework-debt session.

### M6 — Cost tracking + visibility gaps

**Items:** F6 (datetime.UTC silent fail), F7 (no cost projection before multi-task runs).

**The deeper truth:** Operator runs blindly on spend. Cost-ledger was silently failing on Python 3.9 (F6); orchestrator never warned about projected total spend before starting (F7).

**Triage status:** F6 Triaged (X13 datetime.timezone.utc replacement). F7 Open.

**Watch for:** any multi-hour orchestrator run that completes without surfacing a spend tally. F7's fix is to compute `remaining_episodes × per-episode-cost` and surface at resume time.

### M7 — Rule-set drift between prose intent and regex implementation

**Items:** F9 (R-PHONETICS-OUT pattern audit), F13 (other R-rules not yet audited — partially under same heading).

**The deeper truth:** The R-rules are written in English prose (in handbook) AND in regex (in build_episode_txt.py). The two drift apart over time. R-PHONETICS-OUT pattern #1 was over-broad until X5; other patterns may have similar drift.

**Triage status:** F9 Triaged (X5 fixed pattern #1). Full audit of remaining R-rules + unit tests pending.

**Watch for:** any validator false-positive on legitimate content (a sign of over-broad regex) OR a known defect that the validator missed (a sign of under-broad regex).

### How to use this synthesis going forward

When you encounter a NEW defect in a future book, ask first: "which of M1–M7 does this look like?"

- If it matches one of M1–M7: the proposed fix SHAPE is already in this file. Apply the corresponding pattern's fix template; close the new F-item against the existing M.
- If it doesn't match: you've found M8 (or M9, etc.). Add it to this section. Document the meta-truth and the watch-for signal.

When you commit an X-class fix, update the corresponding Mn entry's triage status. When all items under an Mn are Triaged or Closed, mark the meta-pattern **Resolved** with a closing date.

When you author a new R-rule (handbook addition), CHECK whether it can be enforced both prompt-side AND validator-side. Single-enforcement-point rules are exactly the M1 root cause; double-enforcement closes the loop. The next framework session's first task is auditing existing R-rules for validator coverage gaps.

## Active framework debt

| ID | Title | Discovered | Severity | Status | Owner |
|---|---|---|---|---|---|
| F1 | Phase 0g framing-gen LLM ignores hard word-count caps | 2026-05-21 (KaR EP14) | High | Triaged ([X10](https://github.com/asifhussain60/Journal/commit/HEAD) added per-section caps + self-check in author_framing prompt) | — |
| F2 | Phase 0g framing-gen produces unused pronunciation entries | 2026-05-21 (KaR EP14) | Medium | Triaged ([X10](https://github.com/asifhussain60/Journal/commit/HEAD) prompt now requires grep chapter for terms before generating entries) | — |
| F3 | Phase 0e enrichment emits manuscript-history meta-commentary that NotebookLM hosts then vocalize | 2026-05-21 (KaR ch03a et al.) | High | Triaged (X14 added R-NO-MANUSCRIPT-META instruction to Phase 0e prompt with explicit forbidden patterns) | — |
| F4 | Phase 0d chapter design includes editorial-intro chapters that aren't substantive book content | 2026-05-21 (KaR ch01a) | Medium | Open | — |
| F5 | Phase 0e enrichment emits repeated honorifics (glyph + text forms) per chapter; R-HONORIFIC-ONCE flags downstream | 2026-05-21 (KaR ch08/ch09/ch12/ch14b + X8 text forms) | Medium | Triaged (X14 strengthened Phase 0e prompt: enumerates glyph + 5 text forms + requires self-count before return) | — |
| F6 | Cost-ledger silently fails on Python 3.9 due to `datetime.UTC` (3.11+ feature) | 2026-05-21 (KaR Phase 0g) | Medium | Triaged (X13 replaced `datetime.UTC` with `datetime.timezone.utc` in `_cost_ledger._now_iso`) | — |
| F7 | Orchestrator doesn't surface multi-task cost projection before starting long runs | 2026-05-21 (KaR Phase 0g) | Low | Open | — |
| F8 | Stale `episode-drafts/EP*` directories accumulate across X-class fix cycles; no auto-clean on resume | 2026-05-21 (KaR EP14b/EP12/EP04) | Low | Triaged (X13 added _sweep_orphan_episode_drafts() in preflight_resume + _drive_per_chapter_and_after; idempotent removal) | — |
| F9 | R-PHONETICS-OUT pattern #1 was over-broad; suggests rule-set audit for intent/implementation alignment | 2026-05-21 (KaR EP14 first attempt) | Low | Triaged ([X5](https://github.com/asifhussain60/Journal/commit/c9424dd) fixed pattern #1; audit remaining patterns) | — |
| F10 | Word-band rules with "~" prose use exact thresholds in code (no tolerance) | 2026-05-21 (KaR ch12/ch14b at 10180/10112) | Low | Triaged (X6 bumped chapter ceiling 10000→10500; X13 bumped framing ceiling 3500→3700) | — |
| F11 | Iter-1 SHIP verdict + iter-2 challenger timeout treated as chapter failure even though episode already shipped | 2026-05-21 (KaR EP04/EP07/EP08 — all shipped at iter 1, all marked FAILED on iter-2 timeout) | Medium | Open | — |
| F12 | Episode IDs derived from chapter filename digits, not from `contract.episode_number`; gaps in listener-facing numbering after chapter drops | 2026-05-21 (KaR EP04/EP07/EP10/EP12/EP14 with missing EP01-EP02 after ch01a/ch02b drops) | Medium | Open | — |
| F13 | Phase 0e enrichment leaks inline `(pho-net-ic — gloss)` parens into chapter txt despite R-PHONETICS-OUT; observed only in some chapters (ch15) while siblings are clean | 2026-05-21 (KaR ch15 — 18 inline phonetics on terms + 1 on people-name `Abu Hatim al-Razi`) | Medium | Open | — |
| F14 | Chapter prose + framing repeat Arabic names many times per episode; NotebookLM TTS mangles each occurrence into multiple inconsistent garbled forms (one chapter = 8+ variants of `al-Kirmani`); listeners hear pronunciation noise instead of substance | 2026-05-21 (KaR Ch07 audio transcript review) | **High** | Triaged (X15 added per-figure rotation-set discipline to Phase 0g framing-gen prompt + KaR name-aliases.yml; takes effect on next orchestrator launch for remaining 5 chapters) | — |
| F15 | Phase 0g framing-gen produces "two hosts unpacking" dynamic instead of "explainer vs genuine challenger"; over-explanation, premature resolution of central tension, analogy proliferation (14+ analogies in one Ch07 episode) | 2026-05-21 (independent GPT review of KaR Ch07 transcript) | **High** | Triaged (X16 added R-DRAMATIC-ARC + R-CHALLENGER-FRICTION + R-ANALOGY-CAP + R-RECURRING-THESIS to Phase 0g framing-gen prompt; takes effect on next orchestrator launch) | — |
| F16 | Framing's `## Opening directive` announces source-book chapter number ("Chapter Three") but not the podcast episode number ("Episode 7"); listener loses series-position context | 2026-05-21 (KaR Ch07 v2 audio review — listener heard "Chapter 3" and asked why episode 7 was labeled chapter 3) | Medium | Open | — |
| F17 | R-ANALOGY-CAP under-enforced — hosts respected the 3 governing analogies in `## Tone constraints` but ALSO introduced 5+ new analogies mid-episode (cosmic ruler, pitcher+silver cup, Venn diagram, signet ring, radio tower) despite explicit instruction | 2026-05-21 (KaR Ch07 v2 audio review) | Medium | Open | — |
| F18 | Single-Arabic-occurrence per chapter still results in TTS mangling — even one occurrence of `al-Kirmani` per chapter generates 8+ mangled variants in audio (Quraymani, Alcure Mane, al-Khir MNA, etc.). Reduction discipline (F14) is insufficient | 2026-05-21 (KaR Ch07 v2 audio review) | **High** | Open (superseded by F20 — total removal) | — |
| F19 | TTS-induced phonetic collisions create theological errors — "al-Qur'an Mayni" (al-Kirmani name colliding with the Quran), "Sahih al-Sajidiyya" (conflating Sahih al-Bukhari hadith collection with al-Sahifa al-Sajjadiyya supplication) | 2026-05-21 (KaR Ch07 v2 audio review) | **High** | Open (superseded by F20 — total removal eliminates this class) | — |
| F20 | Arabic names (person, book, author) in chapter prose AND framing leak into spoken audio; NotebookLM TTS cannot reliably pronounce them; editorial principle shift: knowledge is the key, not the references | 2026-05-21 (Asif's editorial doctrine after Ch07 v2 review) | **High** | Open | — |
| F21 | Book-title references in spoken audio need natural-language wrapping ("the book *The Harvest*") rather than bare English title ("The Harvest") to disambiguate from poems/metaphors/ideas | 2026-05-21 (Asif refinement to F20) | Medium | Open | — |
| F22 | Extended-tier length target needs to be 45-60 min (not 30-45) for dense scholarly content; bumped via X18 in Phase 0g framing-gen prompt; testing on Ch07 v3 upload | 2026-05-21 (Asif directive after Ch07 v2 audio review) | Medium | Triaged (X18 patch in `_authoring.py:author_framing()` Opening-directive line; Ch07 v3 lab carries the new directive as the empirical test) | — |

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

### F11 — Iter-1 SHIP verdict + iter-2 challenger timeout = chapter marked FAILED (even though episode shipped)

**Where:** `scripts/podcast/orchestrate_book.py:per_chapter_pass()` — the converge loop after `extract → frame → build`.

**What goes wrong:** When the build step succeeds, the episode `.txt` artifact is emitted to `episodes/EP##-<slug>.txt`. That artifact IS the ship — uploaded to NotebookLM, the chapter generates audio. The converge loop then runs the challenger to find P0/P1/P2 issues, runs the fixer to address them, and iterates. If any iteration's challenger pass times out, the orchestrator marks the entire chapter FAILED — overwriting the shipped status. KaR observed this on EP04 / EP07 / EP08: all three shipped via build step at iter 1, then iter-2's challenger timed out, all three were marked FAILED, requiring manual `state.completed_slugs` patches.

**Impact:** Every dense chapter follows this pattern, blocking auto-progress through the queue. The orchestrator restarts after each manual patch. ~3 minutes per chapter of operator work, recurring on every book.

**Proposed fix:** When any iteration achieves a SHIP-READY or SHIP-WITH-CAUTION verdict, set the chapter as shipped in `state.completed_slugs` immediately (without waiting for the converge loop to fully terminate). Subsequent iterations are best-effort polish — their timeouts should be logged but NOT roll back the ship verdict. Reformulate "FAILED" semantics: a chapter is FAILED only if BUILD fails (no episode artifact emitted). Converge timeouts/errors after a successful ship verdict are recorded as a warning, not a halt.

**Verification:** Run on a chapter known to produce SHIP-WITH-CAUTION at iter 1 (e.g., KaR ch08). Confirm chapter advances to next slug even if iter-2 challenger times out.

---

### F12 — Episode IDs derived from chapter filename digits, not from `contract.episode_number`

**Where:** `scripts/podcast/orchestrate_book.py:per_chapter_pass()` (around line 720) and `scripts/podcast/_authoring.py:author_framing()` (around line 1153) — both currently extract the digit prefix from the chapter filename (with X3 + X7 letter-strip logic) to form the episode_id.

**What goes wrong:** Listener-facing episode IDs derive from chapter filenames. Chapter files carry source-baab provenance (ch03a, ch04b, ch05c, ch13a, ch14b) and may include gaps after a chapter drop (ch01a, ch02b dropped → no EP01/EP02). The listener sees a non-sequential episode feed (KaR shipped EP04 / EP07 / EP10 / EP12 / EP14, queued EP03 / EP05 / EP06 / EP08 / EP09 / EP11 / EP13 / EP15 — visible gaps at EP01 / EP02 and the irregular spacing).

**Impact:** The chapter contracts already have an `episode_number:` field declaring the listener-facing sequence. The orchestrator ignores it and derives from filename digits instead. Renaming chapter files would lose source-baab provenance; the contract field is the right source of truth.

**Proposed fix:** Both `per_chapter_pass()` and `author_framing()` should read `contract.episode_number` and format it as `EP{episode_number:02d}-<slug>` instead of extracting digits from the chapter filename. Operator updates `episode_number` per contract to be sequential 1..N in series-plan order; orchestrator regenerates episode artifacts with the new IDs on next per-chapter pass. Chapter filenames remain unchanged (ch03a, ch04b, ch05c etc. preserve source-baab provenance for future books from the same author).

**Verification:** Set `episode_number: 1` on chapter contract `the-perfect-and-the-perfection-of-the-soul.yml` (currently ch03a). Run the per-chapter pass on it. Confirm episode artifact lands at `episodes/EP01-the-perfect-and-the-perfection-of-the-soul.txt`.

**Out-of-band KaR-specific rename:** see [series-plan.md](../../content/podcast/library/books/kitab-al-riyad/_system/series-plan.md) footer for the per-chapter rename checklist scoped to KaR. Execution waits for the orchestrator to quiesce on the current queue.

---

### F13 — Phase 0e enrichment leaks inline `(pho-net-ic — gloss)` parens despite R-PHONETICS-OUT

**Where:** `scripts/podcast/_authoring.py` Phase 0e enrichment prompt that produces `chapters/ch##*.txt`, AND the validator pass that's supposed to enforce R-PHONETICS-OUT (per [skills-staging/podcast/SKILL.md](../../skills-staging/podcast/SKILL.md) INVARIANT 5).

**What goes wrong:** R-PHONETICS-OUT (effective 2026-05-17) forbids inline `(pho-net-ic — gloss)` parens in chapter txt — phonetics belong only in the customize-prompt `## Pronunciation` block. Yet [ch15-tawhid-and-the-critique-of-al-mahsul.txt](../../content/podcast/library/books/kitab-al-riyad/chapters/ch15-tawhid-and-the-critique-of-al-mahsul.txt) shipped with 18 inline phonetics on terms (`tawhid (taw-heed — monotheism)`, `al-hayula (al-ha-yoo-laa — prime matter)`, etc.) plus 1 on a people-name (`Abu Hatim al-Razi (a-boo haa-tim ar-raa-zee)`). Sibling chapters (ch03a, ch04b, ch05c, ch06–ch09, ch10–ch14b) are all clean — only ch15 leaked. Manually stripped 2026-05-21 in the post-ship audit, but the underlying enrichment regression slipped past the validator.

**Impact:** Operator audit time to catch + manually strip per affected chapter (~10 min per chapter). At-scale across queued books, R-PHONETICS-OUT violations would drift into shipped episodes if not caught. Worse, the audit shows ch15 is INCONSISTENT with its 14 siblings — the regression is non-deterministic per chapter, suggesting either a prompt-sensitivity issue (some chapters' source text triggers more LLM inline-phonetic emission than others) or a validator gap (the rule fires on some patterns and not others).

**Proposed fix (two parts):**
1. **Detector:** Add a strict R-PHONETICS-OUT validator pass over every `chapters/ch##*.txt` after Phase 0e completes. Pattern: `\(([a-z']+(-[a-z']+){1,})(\s+—\s+[^)]+)?\)` — matches hyphenated-lowercase-syllable groups inside parens, optionally followed by ` — gloss`. Whitelist legitimate transliteration parens (no hyphens between Roman-letter syllables, e.g., `(al-aimma al-bararah)` passes; `(al-a-im-mah al-ba-ra-rah)` fails). Halt Phase 0e on detection; do not advance to framing.
2. **Auto-stripper:** When detector fires, run a deterministic strip that preserves glosses (`(taw-heed — monotheism)` → `(monotheism)`; `(al-mah-sool)` → drop parens entirely if no gloss) and emit a diff for operator review before re-running validator.

**Verification:** Re-run Phase 0e on a chapter whose source text is known to elicit inline phonetics from the current prompt (any chapter where the operator previously stripped phonetics manually — e.g., ch15 source). Confirm: (a) detector fires before framing; (b) auto-stripper output matches the manual strip diff; (c) re-validator passes.

**Related:** F9 (R-PHONETICS-OUT pattern #1 was over-broad — shipped as X5). F13 is the inverse problem: pattern coverage is now too narrow / not invoked at the right gate.

---

### F14 — Arabic names repeated dozens of times per episode; NotebookLM TTS mangles each occurrence inconsistently

**Where:** Two prompts contribute: (a) `_authoring.py:author_phase_0e()` — chapter-source generation; (b) `_authoring.py:author_framing()` — customize-prompt name-discipline section.

**What goes wrong:** Surfaced 2026-05-21 by listener feedback on the NotebookLM-generated audio for KaR Ch07 ("How the Soul Touches Prime Matter"). The transcript shows NotebookLM's text-to-speech mangling "al-Kirmani" into roughly eight different garbled forms in a single 30-minute episode: `al-Quraymani`, `alkyr M a knee`, `I'll carry many`, `Alcure MNE`, `al-kheir MNE`, `I'll care ma me`, `Alkur Emini`, `Alkyr a main knee`. Similar mangling on `al-Islah` (becomes `all is La H`), `al-Nusra` (`an NUS Ross` / `NUS Rob` / `an NUS raw`), `al-Hayuli` (`all how you law`, `al-hi you la`, `alayullah`), `ma'lul` (`ma. Lol`), `Ghurar al-Hikam` (`Garar al-hikm`). The listener hears pronunciation noise instead of substance.

**Impact:** Every chapter ships with this defect because the chapter prose + framing both repeat Arabic names dozens of times. Each occurrence is an independent TTS attempt — NotebookLM doesn't anchor to a prior pronunciation. The framing's `## Pronunciation` block tries to fix this with imperative pronounce-as-X-as-Y lines, but in practice the TTS still drifts. The listener's grasp of the philosophical content is undermined by constantly mangled name references.

**Proposed fix — three layers:**

1. **Phase 0e (chapter prose).** Add to the enrichment prompt: "Use each Arabic figure name ONCE on first mention with an English role-reference appositive (e.g., `Hamid al-Din Ahmad al-Kirmani, the author of Kitab al-Riyad`). Thereafter, refer to that figure using the English role-reference or a pronoun, NOT the Arabic name. The chapter prose should contain at most 1–2 occurrences of any Arabic figure name; everything else uses English aliases." Applies to authors, scholars, transmitters; technical Arabic vocabulary (tawhid, hudud, etc.) is unaffected — those are concept-words, not figure-names.

2. **Phase 0g (framing host-discipline).** Strengthen the existing "Name discipline" section in the framing template. Instead of just "use alias for subsequent mentions," enumerate a ROTATION SET of 3–4 English aliases per figure and instruct the hosts to rotate naturally among them (avoiding "the author" 20 times in a row). Example for al-Kirmani: rotation set = `{the author, the master, our author, he}`. For Imam Ali: rotation set = `{the Commander of the Faithful, the cousin of the Prophet, the gate of knowledge, the first Imam}`. The framing's `## Name discipline` section lists the rotation set for every figure that appears in the chapter.

3. **Per-figure rotation-set design (book-level decision).** For each figure that recurs across multiple chapters in a book, define a fixed rotation set at the book level (in `_system/series-plan.md` or a sibling file). The framing-gen step reads this and embeds the per-figure rotation set into every chapter's framing. Ensures consistency across episodes — listener hears the same English aliases for the same figure in every chapter, building familiarity.

**KaR-specific remediation (out-of-band):** the 7 already-shipped KaR episodes carry the defect in their generated audio. Options: (a) accept the cost; re-upload after a chapter-prose + framing edit pass; (b) accept what shipped and apply the framework fix to future books only. The 6 chapters still in the queue can benefit from a framing-level fix immediately — patch the framing-gen prompt with the rotation-set instructions before they run.

**Verification:** Re-author one chapter's framing with the strengthened name-discipline section; have NotebookLM regenerate the episode; transcript audit should show ≤2 Arabic-name occurrences per figure and natural rotation among English aliases.

---

### F15 — Framing produces "two hosts unpacking" dynamic instead of "explainer vs genuine challenger"

**Where:** `scripts/podcast/_authoring.py:author_framing()` — the framing-gen prompt; specifically the `## Host dynamic`, `## Central tensions`, and `## Three-part focus` instructions.

**What goes wrong:** Surfaced 2026-05-21 by an independent GPT review of the KaR Ch07 NotebookLM-generated audio transcript. Four structural defects:

1. **Second host too agreeable.** Transcript shows phrases like "That is a remarkably precise analogy", "That beautifully maps al-Kirmani's intent", "That is the perfect translation" — supportive-explainer dynamic instead of genuine-challenger dynamic. The episode reads like a polished lecture disguised as dialogue.
2. **Central tension introduced + resolved too quickly.** The crisis ("if higher and lower realities are categorically different, how do they connect at all?") is stated, then both reformers' positions, al-Kirmani's correction, and several analogies are explained before the listener has time to feel the problem.
3. **Analogy proliferation.** Ch07's 30-minute episode contains 14+ distinct analogies (footprint, political border, messenger, white-coat doctor, glass-and-stone, fulcrum, sphere, pie chart, cathedral, ladder/mountain/valley, seven seas, solar panels, wax-seal). Some are valuable; cumulative effect is fatigue.
4. **Thesis stated once, not repeated.** Al-Kirmani's central settled formula ("contact does not require resemblance — it requires rank, receptivity, and transmitted power") is stated once and never returned to. Listener loses the anchor.

**Impact:** Listener gets information but not suspense; the philosophical stakes (an-Nusra's universe-disconnection fear) are explained but don't land emotionally; the episode's intellectual richness is undermined by structural choices.

**Proposed fix (4 parts, all in Phase 0g framing-gen prompt):**

1. **Narrative-arc template for debate-format chapters.** Add a 6-beat structural arc to the framing's `## Three-part focus` template:
   - Beat 1: crisis statement (state the problem so the listener feels its stakes)
   - Beat 2: failed answer A (al-Islah's position; let it sound reasonable)
   - Beat 3: failed answer B (al-Nusra's position; same)
   - Beat 4: al-Kirmani's pivot (the move that escapes both)
   - Beat 5: non-bodily correction (why category mistakes were made)
   - Beat 6: human/political stakes (why this matters beyond metaphysics)
   - Beat 7 (closing): unresolved listener question
2. **Challenger-discipline section in host_dynamic.** Require the Color host (or scholar_companion) to genuinely push back. Examples of acceptable pushback openings: "I don't buy that yet…", "That sounds like wordplay…", "Isn't this just replacing X with Y…", "How is this different from hiding the problem under a different word…". Forbid agreeable affirmations as a host's FIRST sentence ("That's a remarkably precise…", "That beautifully maps…", "Perfect translation…"). The Color host's role is FRICTION, not chorus.
3. **Analogy budget — cap at 3–5 governing analogies.** The framing's `## Tone constraints` enumerates the chosen governing analogies UPFRONT (e.g., "for this chapter use these 3: footprint, messenger, light-through-glass-and-stone"). Hosts elaborate on the chosen ones, but cannot introduce new analogies mid-episode. Forbidden mid-episode invention.
4. **Recurring-thesis rule.** The chapter's central settled formula (from `contract.anchor_passages`) must be repeated 3 times across the episode: once at the open, once at the pivot, once at the close. Framing's `## Opening directive` + `## Three-part focus` + `## Landing` instructions explicitly reference the repetition rule.

**Push-back on GPT's recommendation:** GPT recommended capping analogies at 3. We recommend 3–5 — for dense philosophical chapters, 3 may be too few for the listener to find footholds across 30 minutes of audio. 5 governing analogies allows breadth without descending into the 14-analogy fatigue Ch07 produced.

**Related root cause (separate framework gap):** ch07's contract assigned `host_dynamic: curious_mind + scholar_companion`, which is supportive-by-design — the wrong host pairing for an adjudicative chapter that debates two reformers. Adjudicative chapters should default to `advocate_a + advocate_b + arbiter`. Phase 0d host-dynamic-selection heuristic needs review (queue as F16 if not already triaged by series-plan classification rules).

**KaR-specific remediation (out-of-band):** the 7 already-shipped KaR episodes carry this defect. The 6 remaining chapters can benefit from X16 (the Phase 0g prompt patch) on next orchestrator launch. Re-doing the 7 shipped is the same Middle Path vs Full Remediation decision as F14.

**Verification:** Re-author one debate-format chapter's framing with X16 in place; regenerate; transcript audit should show ≤5 distinct analogies, ≥3 challenger-pushback moments, central thesis repeated 3 times, and the 6-beat narrative arc visible in pacing.

---

### F16 — Framing announces source-book chapter number, not podcast episode number

**Where:** `_authoring.py:author_framing()` — the `## Opening directive` section of the framing template.

**What goes wrong:** The framing instructs hosts to open with "*Kitab al-Riyad*, Chapter Three" (the source-book's chapter number). The listener hears "Chapter 3" and gets confused when they're listening to "Episode 7" of the podcast. Empirical: KaR Ch07 v2 audio surfaced this — listener explicitly asked "why does the audio say chapter 3?"

**Impact:** Listener loses series-position context. For a 13-episode book, knowing whether you're at episode 4 of 13 or episode 11 of 13 matters for pacing your listen-through.

**Proposed fix:** Opening directive instructs hosts to announce BOTH — "Episode 7 of our walkthrough of *Kitab al-Riyad*, covering the book's Chapter Three." Order matters: episode-number first (listener's reference), source-chapter second (provenance reference). Phase 0g framing-gen prompt also gets a section reminder that `contract.episode_number` is the listener-facing reference; `contract.source_chapter_ref` is the source-tracing reference.

**Verification:** re-author one chapter's framing post-fix; transcript audit should show "Episode N" announced in the open before "Chapter M of the source."

---

### F17 — R-ANALOGY-CAP under-enforced; hosts introduce new analogies mid-episode despite explicit instruction

**Where:** `_authoring.py:author_framing()` R-ANALOGY-CAP rule (X16 addition); also the framing's `## Tone constraints` section.

**What goes wrong:** X16 added R-ANALOGY-CAP, instructing the framing to enumerate 3-5 governing analogies upfront and forbidding mid-episode introduction. KaR Ch07 v2 transcript audit shows the rule was PARTIALLY honored — hosts elaborated on the 3 governing analogies (footprint, messenger, light-on-glass-and-stone) AND introduced 5+ new ones (cosmic ruler, crystal pitcher + silver cup, Venn diagram of reality, signet ring + wax, radio tower / antenna).

**Impact:** v1 had 14+ analogies; v2 had 8 (3 governing + 5 invented). Improvement, but the cap discipline didn't fully take. NotebookLM apparently treats "forbidden mid-episode invention" as a soft suggestion rather than a hard rule.

**Proposed fix:** Strengthen the rule. Two options: (a) make the forbidden mid-episode invention an EXPLICIT instruction in the framing's `## Three-part focus` sections — "Beat 3 MAY ONLY use the governing analogies from Tone constraints; introducing new analogies here violates R-ANALOGY-CAP and the conversation should pause and return to a governing analogy"; or (b) extend the validator (Tier 2 additions) to count distinct analogies in the framing's prose and FAIL if any beat-section contains an analogy not declared upfront.

**Verification:** re-author one chapter's framing post-fix; transcript audit shows ≤5 distinct analogies and 0 mid-episode introductions.

---

### F18 — Single-Arabic-occurrence still mangled by TTS

**Where:** R-NAMEDISCIPLINE (X15 addition) — currently allows one Arabic-name occurrence on first mention with English appositive.

**What goes wrong:** Even with name-rotation discipline reducing the COUNT to ~1 per chapter, NotebookLM TTS mangles the single occurrence into multiple inconsistent garbled variants. The mangling propagates: when the host then says "the author" (the English alias), the listener has already heard 8+ garbled pronunciations and can't anchor.

**Impact:** F14's count-reduction discipline was a partial fix; F18 names the deeper truth that ANY Arabic occurrence in spoken content triggers TTS unpredictability.

**Status:** Open, superseded by F20 (total Arabic-name removal from spoken content) — F18 is preserved as the diagnostic step that motivated the larger F20 doctrine shift.

---

### F19 — TTS-induced phonetic collisions create theological errors

**Where:** NotebookLM TTS engine; not directly under operator control.

**What goes wrong:** Empirical Ch07 v2 audio observations:
- "al-Kirmani" → "al-Qur'an Mayni" (the author's name collides with the Quran itself in the listener's ear)
- "Sahih al-Sajidiyya" — the TTS conflates "Sahih al-Bukhari" (a hadith collection) with "al-Sahifa al-Sajjadiyya" (Imam Zayn's supplication). Two distinct works become one wrong work in the audio.

**Impact:** These aren't pronunciation imperfections — they're THEOLOGICAL ERRORS introduced by TTS. A listener hearing "al-Qur'an Mayni argued that the Second is born from the First" hears a claim that the Quran itself argues a metaphysical proposition. That's wrong content, not just wrong pronunciation.

**Status:** Open, superseded by F20 — total Arabic-name removal eliminates the collision-risk surface area entirely.

---

### F20 — Arabic names (person, book, author) leak into spoken audio; doctrine shift: remove entirely

**Where:** `_authoring.py:author_phase_0e()` (chapter-prose enrichment) + `_authoring.py:author_framing()` (host-instruction framing).

**What goes wrong:** F14 reduced the COUNT of Arabic names; F18 + F19 showed reduction is insufficient because EVEN ONE Arabic occurrence triggers TTS mangling AND phonetic collisions that create theological errors.

**Editorial doctrine (Asif 2026-05-21):** "I want all Arabic names (person, book and authors) removed from all chapters. Ignoring the reference weave the quote or statement directly in the dialog generalizing it to a scholar, a Daa-ee, messenger etc. This will resolve the issue. The knowledge is the key not the references."

**Proposed fix (three layers):**

1. **Phase 0e — chapter prose discipline.** New rule **R-NO-ARABIC-NAMES** instructing the LLM: NEVER write Arabic person-names, book-titles, or scholar references in the chapter prose. Replace ALL person-names with generic descriptors: "a scholar", "a preacher", "a Da'i" (acceptable loanword for a role-title), "the messenger", "a transmitter", "the early reformer". Quote attributions weave the statement directly into the conversation without naming the source ("It is said that…" / "A scholar of the school argued…" / "One early transmitter recorded…").

2. **Phase 0g — framing host-discipline.** The framing's `## Name discipline` section becomes `## No-name discipline` — explicitly instructs hosts to NEVER speak Arabic person-names or book-titles. The `## Pronunciation` section drops ALL figure-name entries. Concept-word loanwords that are necessary role-terms (Da'i, Imam) may stay with pronunciation guidance; figure-names cannot.

3. **Show notes / book entry preserves attribution.** The audio strips all Arabic; the written companion (book entry on the journal site + per-episode `99-show-notes.md`) preserves the full bibliography with Arabic names, transliterations, English glosses, and suggested-reading list. Listener who wants deeper study has full access; listener who only consumes audio gets clean prose.

**Push-back recorded:** Claude recommended specific English role-descriptors ("the Fatimid philosopher", "the chief preacher of the Persian school") instead of generic ("a scholar") to preserve figure-tracking across an episode. Asif chose generic per the simpler editorial doctrine. The trade-off accepted: listener cannot easily distinguish which-of-several-scholars-said-what; audio quality wins. Mitigation: when the same scholar is referenced multiple times in close sequence, use "the same scholar" or "the one who argued earlier" to preserve continuity within a beat.

**KaR-specific remediation:** the 8 already-shipped KaR episodes carry the defect. Per the established Middle Path scope for F14/F15: accept what's shipped; apply F20's framework patch for future books. KaR Ch07 v3 could be authored as a fresh lab iteration under the new doctrine if Asif wants to test.

**Verification:** apply F20 prompt patches; regenerate one chapter; transcript audit should show ZERO Arabic person-names spoken; ZERO Arabic book-titles spoken; ZERO TTS-mangle events of the F14/F18/F19 class. Show notes contain the full Arabic attribution.

---

### F21 — Book-title references in audio need natural-language wrapping ("the book *The Harvest*")

**Where:** Phase 0e + Phase 0g — wherever book titles appear in chapter prose or framing.

**What goes wrong:** F20 mandates English book titles instead of Arabic transliterations ("The Harvest" not "al-Mahsul"). But bare "The Harvest" in conversation can be heard as a poem, a metaphor, an idea, or a season — not clearly a book.

**Editorial refinement (Asif 2026-05-21):** "When referencing book, mention it is a book as in 'as stated in the book *The Harvest*…'". Wrap every book reference with the role-word "book" to disambiguate.

**Proposed fix:** Phase 0e + Phase 0g prompts require book references to use natural-language wrappings:
- First mention: "the book *The Harvest*" / "a book called *The Defense*" / "in the book *The Repose of the Intellect*"
- Subsequent in close sequence: "the book" / "that book" / "the earlier work" / "the same book"
- Scripture is the exception: "the Quran" is already unambiguous; doesn't need "the book the Quran". Hadith collections become "the canonical hadith collection" rather than "the book *Sahih al-Bukhari*".

**Verification:** apply prompt patch; transcript audit shows every English book-title is preceded or followed by the word "book" in conversation, OR uses an unambiguous descriptor ("the earlier work", "the corrective treatise").

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
