# Podcast intelligence enhancements — tracking plan

**Authored:** 2026-05-22 (Air machine, interactive planning sessions with Asif)
**Status:** 🟡 READY TO EXECUTE — spec locked across two interactive sessions; awaiting your green light to start Phase 1. KaR's currently-in-flight per-chapter work (EP04+ authoring) gets folded INTO this plan rather than running separately.

This doc records the decisions made during 2026-05-22 planning sessions
on six podcast-pipeline enhancements + book-intake automation. When
implementation starts, treat this as the authoritative spec — items
already locked shouldn't be re-debated, only refined. Section
"§9 Final sequencing (LOCKED)" at the bottom is the day-by-day work plan.

---

## Scope

| # | Idea | Status | Effort estimate |
|---|---|---|---|
| 1 | Summary-episode generation | spec locked | 2-3 days |
| 2 | Etymology | TBD — track for later | — |
| 3 | Host-role gender + position lock | spec locked | 1 day |
| 4 | Essential Teachings closing | spec locked | 0.5 day |
| 5 | Imam doctrine substitution rule | spec locked | 0.5 day + sweep |
| 6 | Reflective-reverent emotion register | spec locked | 0.5-1 day |
| 7 | Challenger enhancements (rollup of 1-6) | derived | interleaved |
| 7.5 | Book-intake automation (`intake_book.py`) | spec locked | 0.5 day |
| 7.6 | Series-plan automation | deferred — re-evaluate after first new-book run | — |

Total estimated focused work: **5.5-8 days** through plan completion + first new-book run.

---

## 1. Summary-episode generation

**Decision** (2026-05-22, structural trigger chosen over density-detection after pushback):

- **Per-chapter-group**: when one source chapter splits into multiple EPs (e.g., KaR ch01 → EP03/04/05), emit a chapter-group summary EP after that group.
- **Per-book**: every book gets one summary EP at the series end.
- **Skipped**: density-based per-chapter triggers. Rejected because (a) operational complexity of detecting "philosophical-dense" requires an LLM pre-classification phase, (b) single-EP dense chapters are better served by improving the single EP than by self-recapping, (c) structural triggers already catch the highest-value cases.

**KaR concrete impact**: 2 extra episodes total — EP05.5 (recap of EP03/04/05 "Perfection of the Soul" arc) + EP15.5 (book-end summary of all 13 EPs).

### Format

- Each summary EP is a NEW podcast: NEW source file (recap chapter) + NEW customize prompt (recap framing).
- Numbering convention: `.5` suffix after the last EP of the group, OR after the last EP of the book.
- Length: target 15-25 min (shorter than the 30-45 min per-chapter episodes); summary-chapter source ~2500-4000 words.

### Implementation surfaces

- New orchestrator phase between `trainer` and `merge` (or as a sub-step within `merge`): `13.5-summary` or similar.
- New script `scripts/podcast/author_summary_chapter.py` — LLM-assisted summary authoring; takes the chapter-group's existing EP framings + source chapters as input, emits the summary chapter + framing.
- Series-plan author (`scripts/podcast/series_plan.py` or wherever) computes the summary-EP set up-front from the chapter→EP mapping.
- New file locations: `library/books/<slug>/podcasts/series-NN/EP##.5-summary/{source.txt, framing.md, ...}`.
- `ship_to_library.py` extended to handle the `.5-summary` EP variants.

### Open questions

- Exact length target (15 min? 25 min?) — calibrate against listener attention after KaR ships.
- Whether the book-end summary should include EP10 + EP14 (already-shipped under the old archetype) or only forward-authored episodes. Probably include all; the recap doesn't re-author, just synthesizes.

---

## 2. Etymology

**Decision** (2026-05-22): TBD. No further spec required at this time.

Tracked here so the next planning session knows to define it.

---

## 3. Host-role gender + position lock

**Decision** (2026-05-22, simplified from 3-host to 2-host after pushback):

- Standardize on **2 hosts** across both formats. The original "debate" format's 3rd "Arbiter" role is retired — NotebookLM's Audio Overview is a 2-voice conversation, so 3-host declarations get collapsed by the platform anyway.
- Each host's role is **locked at episode start** — no swap mid-episode.
- Gender is **locked per format** — and consistent across the BOOK (same role → same gender across all episodes of a series).

### Format mappings

| Format | Male voice | Female voice |
|---|---|---|
| deep_dive | **Mentor** — the experienced teacher; carries the chapter's argument; explains terminology + cites passages | **Scholar Companion** — the curious learner; asks probing questions; delivers the literal challenger-friction pushbacks |
| debate | **Advocate B** — the challenger; questions the chapter's settled doctrine; surfaces counter-readings | **Advocate A** — the protagonist; defends the chapter's settled doctrine; closes with the verdict (folds in the retired Arbiter's synthesizing role) |

Rationale for the debate mapping: female voice gets the protagonist position so it's not always male=authority across formats. Across the two formats, both genders play "carrier of the argument" depending on chapter — varied without rotating roles within an episode.

### Implementation surfaces

- Archetype §4.2: rewrite R-STABLE-ROLE-LABELS to include gender-locking.
- New archetype rule R-HOST-GENDER-LOCK.
- Customize prompt must explicitly name "the male host is...", "the female host is..." to give NotebookLM the strongest possible voice-assignment hint.
- Challenger check: framing's `## Stable role-labels` section declares exactly 2 hosts + gender mapping per format.
- `build_episode_txt.py` validator: assert host count = 2 + gender hints present.

### Open questions

- **Risk**: gender hints in the customize prompt may not deterministically control NotebookLM's voice assignment. Validate empirically against EP03 (already authored) before committing to enforcement. If NotebookLM ignores the hints, the lock is aspirational and the challenger check should warn but not block.

---

## 4. Essential Teachings closing

**Decision** (2026-05-22, additive rather than replacement):

- **Two-beat close**: First beat preserves the current pattern (close on unresolved tension + question). Second beat is "Essential Teachings" — 3-5 takeaway sentences summarizing what the **chapter** (the author) teaches, NOT what the conversation covered.

### Rules

- `## Landing` section gains two named sub-beats: `### Unresolved tension` (current) + `### Essential Teachings` (new).
- Essential Teachings: 3-5 takeaway sentences, each one a doctrinal essential extracted from the chapter.
- Tone: declarative, distilled, pedagogical. NOT exclamatory.
- Forbidden phrases (carry forward from existing): "so today we covered", "we discussed", "in summary", "to recap", "we looked at", "join us next time".

### Implementation surfaces

- Archetype §4.1: rewrite Landing section to specify the two-beat structure.
- New archetype rule R-ESSENTIAL-TEACHINGS-PRESENT.
- Challenger check: Landing section contains a heading or marker for "Essential Teachings" + ≥3 declarative takeaway sentences.

---

## 5. Imam doctrine substitution rule

**Decision** (2026-05-22, retroactive + forward):

- Forbidden: "Imam Ali" (Ali is **not** referred to as "Imam Ali" in this tradition's doctrine).
- Forbidden: "Ali = first Imam" or any phrasing positioning Ali as the first Imam.
- Required substitutions for Ali: **"the Father of Imams"** OR **"the Commander of the Faithful"** (already an established epithet, archetype §3.3-aligned).
- Imam numbering: **Imam Hasan = first Imam, Imam Hussain = second Imam** (and so on through the succession; the doctrine continues from there per the Ismaili tradition).
- Apply to: chapter prose (source) AND framings (customize prompt).
- Retroactive: sweep all existing chapters (13 in KaR) + existing framings (EP03/EP10/EP14) + future books.

### Implementation surfaces

- Archetype §3 — new rule R-IMAM-NUMBERING with explicit table.
- Challenger check R-IMAM-ALI-SUBSTITUTION: grep for forbidden phrases; flag any occurrence.
- One-time sweep script: `scripts/podcast/sweep_imam_doctrine.py` — scans all chapter sources + framings + applies safe substitutions where context is unambiguous; flags ambiguous cases for human review.

### Notes from the corpus check

- Most of EP14's "Imam Ali" references were already cleaned up during the 2026-05-22 EP14 P0 challenger auto-fixes (commit `46f7e58`). Ali is referred to as "the Commander of the Faithful" in most current passages.
- EP03 + EP10 + the 10 unauthored chapters need verification.

---

## 6. Reflective-reverent emotion register

**Decision** (2026-05-22, two rules added to archetype):

### R-REFLECTIVE-EMOTION

Every episode includes **≥2 beats** where a host names an emotional response — wonder, return-to-the-passage, recognition, being-moved — through a **complete sentence in measured cadence**.

Sample phrases (illustrative; not a closed list):
- "There's something patient about this argument that I want to sit with."
- "What strikes me here is the way the author refuses the easy resolution."
- "I find myself returning to this passage."
- "You can feel the author working under the weight of three centuries of debate."
- "The way these sub-chapters fold into one another — it's quietly beautiful."

### R-NO-DETACHED-ACADEMIC

Forbid pure third-person descriptive stretches ("the author argues X; then the author argues Y; the conclusion is Z"). Each beat must include first-person host engagement at least once — verbs of investment like "I find...", "what strikes me...", "there's something...", "I notice...".

### Why this register specifically

Islamic-scholastic content's natural emotional vocabulary is **reverence + recognition**, not excitement. The existing archetype §7.2 R-NOSURPRISE already forbids exclamatory interjections (wow, that's so interesting, no way). What this addition does is REQUIRE positive emotional engagement through full reflective sentences — preventing dry-academic reportage at the other extreme.

### Implementation surfaces

- New archetype section §4.7 or §4.8 (between current §4.6 R-RECURRING-THESIS and §4.1 framing-structure).
- Challenger checks:
  - R-REFLECTIVE-EMOTION: count first-person-engagement phrases per episode (target ≥6 across 30-45 min — at least 2 per third of the episode).
  - R-NO-DETACHED-ACADEMIC: flag stretches of >5 sentences pure third-person without first-person engagement.
- Phrase-list approach (curated) vs. semantic LLM check — start with phrase-list for speed; upgrade to semantic if the phrase-list calibration proves too rigid against EP10/EP14.

---

## 7. Challenger enhancements (rollup)

Each of items 1, 3, 4, 5, 6 adds checks to the podcast-challenger:

| Item | New check name(s) | Severity | Implementation file |
|---|---|---|---|
| 1 | R-SUMMARY-EP-PRESENT (when applicable) | P2 advisory | `_rules.py` + new loop |
| 3 | R-HOST-GENDER-LOCK + R-NO-ROLE-SWAP-IN-EP | P1 | `_rules.py` |
| 4 | R-ESSENTIAL-TEACHINGS-PRESENT | P1 | `_rules.py` |
| 5 | R-IMAM-NUMBERING + R-IMAM-ALI-SUBSTITUTION | P0 (doctrine) | `_rules.py` |
| 6 | R-REFLECTIVE-EMOTION + R-NO-DETACHED-ACADEMIC | P1 | `_rules.py` (deterministic) + LLM-pass (semantic) |

Implementation surfaces:
- `infra/claude-agents/podcast-challenger.md`: update `reads_normative` + describe the new checks in the body.
- `scripts/podcast/_rules.py`: implement the deterministic checks.
- Semantic checks (reflective-emotion, detached-academic) live in the challenger's LLM-pass narrative review, in addition to (or instead of) deterministic phrase-list matching.

---

## §9 Final sequencing (LOCKED — interleaved with ch01 validation gate)

Locked in second interactive session 2026-05-22. The earlier "lowest-blast-radius first, summary episodes last" linear plan was superseded by interleaved sequencing with a hard validation gate after KaR's ch01 group (EP03+EP04+EP05+EP05.5). Rationale: empirical validation of NotebookLM voice-engine behaviour (item 3) and end-to-end summary infrastructure (item 1) both need at least one full chapter-group to complete, and finding archetype bugs after 7-10 authored chapters is 4× more expensive than finding them after 3.

### Phase 1 — Small enhancements + challenger rollup (Days 1-3)

Implement items 4, 5, 6 + their challenger checks. Apply Imam-doctrine sweep retroactively across EP03/EP10/EP14 + the 10 unauthored chapter sources. Apply Essential Teachings retroactively to EP03/EP10/EP14 framings.

| Day | Work |
|---|---|
| Day 1 | Item 5 Imam doctrine: archetype §3 new rule, `sweep_imam_doctrine.py`, retroactive sweep across all 13 KaR chapters + 3 existing framings. Commit. |
| Day 2 | Item 4 Essential Teachings: archetype §4.1 Landing rewrite to two-beat. Retroactive update on EP03/EP10/EP14 framings. Build_episode_txt validator R-ESSENTIAL-TEACHINGS-PRESENT. Re-emit episode .txts. |
| Day 3 | Item 6 Reflective-reverent emotion: archetype §4 new section + curated phrase list. Item 7 first cut of challenger rollup (rules 4 + 5 + 6 implemented in `_rules.py`). Re-run challenger against EP03/EP10/EP14; expect SHIP-READY or close. |

### Phase 2 — Host gender lock + empirical NotebookLM validation (Day 4)

Item 3 archetype rewrite + challenger rule + validator. Upload EP03 to NotebookLM with explicit gender hints in the customize prompt; verify voice assignment is deterministic. If NotebookLM ignores the hints, downgrade R-HOST-GENDER-LOCK to advisory + log the constraint as a future-platform issue.

### Phase 3 — Complete ch01 group end-to-end (Days 5-7)

| Day | Work |
|---|---|
| Day 5 | Author EP04 (ch04b "Soul, Intellect, and the Power of Emanation") using full enhanced pipeline. `claude -p` skeleton + hand-edit, build_episode_txt verify, commit. |
| Day 6 | Author EP05 (ch05c "The Soul in Time and the Rejoinder to al-Nusra"). Same pattern. |
| Day 7 | Item 1 summary-episode infrastructure: new orchestrator phase `13.5-summary`, `author_summary_chapter.py`, file layout `library/books/<slug>/podcasts/series-NN/EP##.5-summary/`, `ship_to_library.py` integration. Generate EP05.5 chapter-group summary. |

### Phase 4 — VALIDATION GATE (Day 8)

- Full challenger pass on EP03/04/05/05.5 — must be SHIP-READY or SHIP-WITH-CAUTION with only acceptable P1/P2 advisories.
- Asif listen-test: upload one EP + the EP05.5 summary to NotebookLM, audit the conversation quality.
- Decision: scale to remaining chapters as-is, or fix archetype/challenger gaps first and re-run the relevant chapter(s).

### Phase 5 — Scale to ch02-ch13 (Days 9-12)

Batch-author the remaining 7 chapters in sequence (parallelization NOT used — LLM call is ~30-90s but human review dominates, so parallel savings are ~10% wall time, not worth the complexity):

| Day | Chapters |
|---|---|
| Day 9 | EP06 (ch06 "The Intellect as the First Creation") + EP07 (ch07 "Soul and Spirit — One Substance or Two?") |
| Day 10 | EP08 (ch08 "Souls — Parts of the First Truths, or Only Traces?") + EP09 (ch09 "The Human Being — Fruit of All the Worlds") |
| Day 11 | EP11 (ch11 "The Sections of the World") + EP12 (ch12 "Qada and Qadar — Fate and Destiny") |
| Day 12 | EP13 (ch13a "The Shariʿah of Adam and the First Speaker") + EP15 (ch15 "Tawhid and the Critique of al-Mahsul") |

### Phase 6 — Book completion + KaR ship (Day 13)

- Generate EP15.5 (book-end summary across all 15 EPs).
- Final challenger pass on all 17 deliverables (15 EPs + 2 summaries).
- Update orchestrator state.json: phase=done, completed_slugs filled.
- `ship_to_library.py --book kitab-al-riyad` promotes everything to `library/books/kitab-al-riyad/`.
- Update KaR catalog row; merge `book/kitab-al-riyad` → `develop`.

### Phase 7 — First new-book run (Day 14)

- Pick a book from `raw/`. Recommended: **Ayyuhal Walad** — smallest (146KB PDF), faster end-to-end loop for first scaling validation.
- Run enhanced orchestrator end-to-end through Phase 0a-0g + the new summary-episode phase.
- Measure: per-chapter hand-edit minutes vs KaR baseline; identify any friction that didn't show up in KaR's KaR-specific tuning.

### Phase 7.5 — Book-intake automation (Day 14, parallel with first new-book setup)

`scripts/podcast/intake_book.py <pdf-path> <book-slug>`:
- Copies PDF from `raw/<book>.pdf` → `_workspace/books/<slug>/_source/<book>.pdf`
- Creates workspace skeleton (`_system/`, `chapters/`, `episodes/`, `episode-drafts/`)
- Initializes `_system/orchestrator-state.json` with phase=preflight
- Creates the `book/<slug>` git branch
- Prints next-action (operator runs `orchestrate_book.py --start <pdf-path> --slug <slug>`)

This script runs once per new book + saves ~30 min of manual setup. Built during Phase 7's setup so it's exercised on the first new-book run.

### Phase 7.6 — Series-plan automation (deferred)

Re-evaluate after Phase 7 completes. If Ayyuhal Walad needed substantial manual series-plan authoring, design the LLM-assisted generator next. If the structural pattern (single-chapter book) made it trivial, defer further.

---

## Roll-out (item-by-item against KaR's chapters)

| Phase | KaR target | Items rolled out |
|---|---|---|
| 1 Day 1-3 | EP03/EP10/EP14 retroactive | 4 + 5 + 6 + 7 (rollup so far) |
| 2 Day 4 | EP03 NotebookLM voice empirical test | 3 |
| 3 Day 5-7 | EP04 + EP05 authoring, EP05.5 generation | 3 + 6 (live) + 1 (chapter-group summary infra) |
| 4 Day 8 | ch01 group validation gate | 7 (full rollup verification) |
| 5 Day 9-12 | EP06-EP09, EP11-EP13, EP15 batch | all items live |
| 6 Day 13 | EP15.5 book-end summary + ship | 1 (book-end summary) |
| 7 Day 14 | First new-book run (Ayyuhal Walad) | 7.5 (intake automation) |

---

## Dependencies + risks

- **NotebookLM voice-engine constraint** (item 3): gender hints may not deterministically control voice assignment. Empirical validation needed before enforcement.
- **Summary-episode generation cost** (item 1): ~$0.10-0.30 per summary EP via Sonnet. KaR adds 2 summary EPs = ~$0.50 marginal cost. Acceptable.
- **Reflective-emotion phrase list** (item 6): curated list might be too rigid; semantic LLM check might be too loose. Need calibration against EP10/EP14/EP03 (the 3 existing episodes) to find the right threshold.
- **Retroactive sweep for Imam doctrine** (item 5): risk of mis-applying substitutions where "Imam Ali" is contextually correct (e.g., in a direct historical quote that NAMES the doctrinal error being corrected). The sweep script should flag ambiguous cases for human review rather than auto-substitute.

---

## How this plan was finalized

**Two interactive planning sessions with Asif on 2026-05-22.** Five Claude pushbacks during the sessions, all accepted by Asif:

1. **Q1 (summary trigger)**: Asif's initial choice was per-chapter threshold (word count + density). Claude pushed back — semantic density detection requires LLM call + dynamic episode numbering = high complexity for low marginal value. Asif accepted the structural-trigger alternative (chapter-group + book-end).
2. **Q2 (host shape)**: Asif's spec implied 2-host (his "A is the scholar, B (female) is the curious student" example). The existing "debate" format declared 3 hosts. Claude pushed back — NotebookLM is 2-voice; 3-host declarations get collapsed. Asif accepted the 2-host simplification + retire the Arbiter role.
3. **Q5 (emotion flavor)**: Asif's spec was qualitative ("balance of emotion and intelligence"). Claude offered 3 flavors (reflective-reverent / personal-stakes / hospitality). Asif accepted reflective-reverent as the best match for Islamic-scholastic content.
4. **Q6 (sequencing)**: Plan-doc's strictly linear "all enhancements → all chapters → ship" had a late-discovery risk (any archetype calibration error after 7+ chapters costs 4× to fix). Claude pushed back with an interleaved sequence + hard validation gate after the ch01 group (EP03+EP04+EP05+EP05.5). Asif accepted.
5. **Q7 (scaling automation)**: Plan-doc's 6 enhancements solve quality but not velocity; book-onboarding friction (manual PDF copy, workspace scaffolding, series-plan authoring) is the actual bottleneck for processing more books. Claude pushed back with Phase 7.5 book-intake automation. Asif accepted (and deferred series-plan automation pending first new-book run signal).

**Effective optimization function**: from "ship KaR fast" → "validate the enhanced pipeline thoroughly enough that the next book runs with minimal hand-holding." The validation gate + the empirical NotebookLM voice test + the book-intake script all serve this scaling intent.

Items not in scope of this plan:
- Memoir / journal repo work (different repo).
- General orchestrator infrastructure work (existing tasks in `podcast-plan.yaml`).
- Pipeline parallelization within Phase 5 (rejected — ~10% wall-time savings not worth the concurrent-commit complexity once human-review is the bottleneck).
- Multi-format archetype library for non-Islamic content (deferred — all current `raw/` books are Islamic-scholastic; revisit when a different-genre book lands).
- Cross-book challenger learning (challenger learns from book N's failure patterns to improve book N+1) — interesting future direction; not in scope.
