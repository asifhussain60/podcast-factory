# Podcast intelligence enhancements — tracking plan

**Authored:** 2026-05-22 (Air machine, interactive planning session with Asif)
**Status:** 🟡 PLANNED — **not yet implemented**. Captured for after KaR archetype-driven manual finish completes.

This doc records the decisions made during a 2026-05-22 planning session
on six podcast-pipeline enhancements (plus one TBD). When implementation
starts, treat this as the authoritative spec — items already locked
shouldn't be re-debated, only refined.

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

Total estimated focused work: **5-7 days**.

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

## Sequencing

Recommended implementation order (lowest blast radius → highest scaffolding work):

1. **Item 5 (Imam doctrine sweep)** — quick + retroactive impact; doctrinal hygiene. **Day 1.**
2. **Item 4 (Essential Teachings)** — small archetype rewrite; touches Landing only. **Day 1-2.**
3. **Item 3 (Host gender lock)** — modest archetype rewrite + challenger rule + validator. Validate empirically against NotebookLM voice assignment. **Day 2-3.**
4. **Item 6 (Emotion register)** — archetype rules + curated phrase-list for validation. **Day 3-4.**
5. **Item 1 (Summary episodes)** — biggest scaffolding work; new orchestrator phase + new file types + ship integration. **Day 5-7.**
6. **Item 7 (Challenger rollup)** — implementation interleaved with each item above; final consolidation pass on day 7.

---

## Roll-out (against KaR's remaining chapters)

| Phase | KaR target | Items rolled out |
|---|---|---|
| 1 | Verify on EP03 (already authored) | 4 + 5 |
| 2 | Apply to EP04 (next chapter) | 3 |
| 3 | Apply to EP05 | 6 |
| 4 | After ch01 group (EP03/04/05) completes — generate EP05.5 summary | 1 (chapter-group summary) |
| 5 | After EP15 (book complete) — generate EP15.5 book summary | 1 (book-end summary) |
| 6 | Re-run challenger on EP03/EP10/EP14 with all new rules | 7 (rollup verification) |

---

## Dependencies + risks

- **NotebookLM voice-engine constraint** (item 3): gender hints may not deterministically control voice assignment. Empirical validation needed before enforcement.
- **Summary-episode generation cost** (item 1): ~$0.10-0.30 per summary EP via Sonnet. KaR adds 2 summary EPs = ~$0.50 marginal cost. Acceptable.
- **Reflective-emotion phrase list** (item 6): curated list might be too rigid; semantic LLM check might be too loose. Need calibration against EP10/EP14/EP03 (the 3 existing episodes) to find the right threshold.
- **Retroactive sweep for Imam doctrine** (item 5): risk of mis-applying substitutions where "Imam Ali" is contextually correct (e.g., in a direct historical quote that NAMES the doctrinal error being corrected). The sweep script should flag ambiguous cases for human review rather than auto-substitute.

---

## How this plan was finalized

Interactive planning session with Asif on 2026-05-22. Three pushbacks from Claude during the session, each accepted by Asif:

1. **Q1 trigger**: Asif's initial choice was per-chapter threshold (word count + density). Claude pushed back — semantic density detection requires LLM call + dynamic episode numbering = high complexity for low marginal value. Asif accepted the structural-trigger alternative.
2. **Q2 host shape**: Asif's spec implied 2-host (his "A is the scholar, B (female) is the curious student" example). The existing "debate" format declared 3 hosts. Claude pushed back — NotebookLM is 2-voice; 3-host declarations get collapsed. Asif accepted the 2-host simplification + retire the Arbiter role.
3. **Q5 emotion flavor**: Asif's spec was qualitative ("balance of emotion and intelligence"). Claude offered 3 flavors (reflective-reverent / personal-stakes / hospitality). Asif accepted reflective-reverent as the best match for Islamic-scholastic content.

Items not in scope of this plan:
- KaR's remaining EP04-EP15 authoring (operationally in flight; archetype-driven manual finish).
- Memoir / journal repo work (different repo).
- General orchestrator infrastructure work (existing tasks in `podcast-plan.yaml`).
