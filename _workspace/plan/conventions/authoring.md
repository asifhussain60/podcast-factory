# Authoring Conventions — Standing Rules

Locked authoring rules that govern every podcast episode the pipeline produces. Extracted from `podcast-intelligence-enhancements.md` (now archived). Apply to every archetype unless explicitly overridden in the archetype's `spec.yml`.

These rules are enforced by `podcast-challenger` checks and (where deterministic) by `scripts/podcast/_rules.py` R-* constants.

---

## 1. Host-Role Gender + Position Lock (R-HOST-GENDER-LOCK · R-NO-ROLE-SWAP-IN-EP)

Two hosts per episode across both formats. Each host's role is locked at episode start — no swap mid-episode. Gender is locked per format AND consistent across the entire book (same role → same gender across all episodes).

**Format mappings (canonical):**

| Format | Male voice | Female voice |
|---|---|---|
| deep_dive | **Mentor** — experienced teacher; carries the chapter's argument; explains terminology + cites passages | **Scholar Companion** — curious learner; asks probing questions; delivers literal challenger-friction pushbacks |
| debate | **Advocate B** — challenger; questions the chapter's settled doctrine; surfaces counter-readings | **Advocate A** — protagonist; defends the chapter's settled doctrine; closes with the verdict (subsumes the retired Arbiter's synthesizing role) |

**Rationale.** Female voice gets the protagonist position in `debate` so authority isn't always male=expert across formats. Across both formats, both genders carry the argument depending on chapter — varied without rotating roles within an episode. The original 3-host `debate` format's Arbiter is retired; NotebookLM is a 2-voice conversation, so 3-host declarations get collapsed by the platform anyway.

**Enforcement.**
- Archetype §4.2 R-STABLE-ROLE-LABELS rewritten to include gender-locking.
- New archetype rule R-HOST-GENDER-LOCK.
- Customize prompt must explicitly name "the male host is...", "the female host is..." to give NotebookLM the strongest possible voice-assignment hint.
- Challenger check: framing's `## Stable role-labels` section declares exactly 2 hosts + gender mapping per format.
- `build_episode_txt.py` validator: assert host count = 2 + gender hints present.

**Known risk.** Gender hints in the customize prompt may not deterministically control NotebookLM's voice assignment. Empirically validate before treating as hard enforcement. If NotebookLM ignores hints, the lock is aspirational and the challenger check warns but does not block.

---

## 2. Essential Teachings Closing (R-ESSENTIAL-TEACHINGS-PRESENT)

Every episode's `## Landing` section uses a two-beat close:

1. **`### Unresolved tension`** (existing) — close on the unresolved tension + question.
2. **`### Essential Teachings`** (new) — 3-5 takeaway sentences summarizing what the **chapter** (the author) teaches, NOT what the conversation covered.

**Rules.**
- Each Essential Teaching is one declarative sentence — distilled, pedagogical. NOT exclamatory.
- Carry forward existing banned phrases: "so today we covered", "we discussed", "in summary", "to recap", "we looked at", "join us next time".
- Anti-cliché list also applies (see `scripts/podcast/intelligence/_anti_cliche.CAPSTONE_DENY`).

**Enforcement.**
- Archetype §4.1 Landing section specifies the two-beat structure.
- New archetype rule R-ESSENTIAL-TEACHINGS-PRESENT.
- Challenger check: Landing section contains a heading or marker for "Essential Teachings" + ≥ 3 declarative takeaway sentences.

---

## 3. Imam Doctrine Substitution (R-IMAM-NUMBERING · R-IMAM-ALI-SUBSTITUTION)

**Forbidden phrasings.** "Imam Ali" — Ali is **not** referred to as "Imam Ali" in this tradition's doctrine. "Ali = first Imam" or any phrasing positioning Ali as the first Imam.

**Required substitutions for Ali.** "the Father of Imams" OR "the Commander of the Faithful" (the latter is an established epithet, archetype §3.3-aligned).

**Imam numbering.** Imam Hasan = first Imam. Imam Hussain = second Imam. Succession continues from there per the Ismaili tradition.

**Scope.** Applies to chapter prose (source) AND framings (customize prompt). Retroactive for all existing books (see [refactor/plan.md](../refactor/plan.md) step E2 KaR + E3 M&D).

**Enforcement.**
- Archetype §3 — rule R-IMAM-NUMBERING with explicit table.
- Challenger check R-IMAM-ALI-SUBSTITUTION: grep for forbidden phrases; flag any occurrence as P0 (doctrine).
- One-time sweep script: `scripts/podcast/sweep_imam_doctrine.py` — auto-substitute where context is unambiguous, flag ambiguous cases for human review.

**Edge case.** Direct historical quotes that NAME the doctrinal error being corrected may legitimately use "Imam Ali" in their citation context. The sweep script flags rather than auto-substitutes these.

---

## 4. Reflective-Reverent Emotion Register (R-REFLECTIVE-EMOTION · R-NO-DETACHED-ACADEMIC)

Islamic-scholastic content's natural emotional vocabulary is **reverence + recognition**, not excitement. The existing archetype R-NOSURPRISE already forbids exclamatory interjections (wow, that's so interesting, no way). These two rules REQUIRE positive emotional engagement through full reflective sentences — preventing dry-academic reportage at the other extreme.

### R-REFLECTIVE-EMOTION

Every episode includes **≥ 2 beats** where a host names an emotional response — wonder, return-to-the-passage, recognition, being-moved — through a **complete sentence in measured cadence**.

**Sample phrases** (illustrative; not a closed list):
- "There's something patient about this argument that I want to sit with."
- "What strikes me here is the way the author refuses the easy resolution."
- "I find myself returning to this passage."
- "You can feel the author working under the weight of three centuries of debate."
- "The way these sub-chapters fold into one another — it's quietly beautiful."

### R-NO-DETACHED-ACADEMIC

Forbid pure third-person descriptive stretches ("the author argues X; then the author argues Y; the conclusion is Z"). Each beat must include first-person host engagement at least once — verbs of investment like "I find...", "what strikes me...", "there's something...", "I notice...".

**Enforcement.**
- Archetype §4.7 (between R-RECURRING-THESIS and §4.1 framing-structure).
- Challenger checks:
  - R-REFLECTIVE-EMOTION: count first-person-engagement phrases per episode (target ≥ 6 across 30-45 min — at least 2 per third).
  - R-NO-DETACHED-ACADEMIC: flag stretches of > 5 sentences pure third-person without first-person engagement.
- Phrase-list (curated) for speed; upgrade to semantic LLM check if the phrase-list calibration proves too rigid.

---

## Challenger Check Rollup

| Convention | New check(s) | Severity | Implementation |
|---|---|---|---|
| §1 host gender + position | R-HOST-GENDER-LOCK + R-NO-ROLE-SWAP-IN-EP | P1 | `_rules.py` deterministic |
| §2 Essential Teachings | R-ESSENTIAL-TEACHINGS-PRESENT | P1 | `_rules.py` deterministic |
| §3 Imam doctrine | R-IMAM-NUMBERING + R-IMAM-ALI-SUBSTITUTION | **P0** doctrine | `_rules.py` + sweep script |
| §4 reflective emotion | R-REFLECTIVE-EMOTION + R-NO-DETACHED-ACADEMIC | P1 | `_rules.py` deterministic + LLM-pass semantic |

---

## Relationship to other plan artifacts

- **Multi-tier capstone anti-cliché** (refactor plan step C2 + Decision Record DR-002) — uses the shared `scripts/podcast/intelligence/_anti_cliche.py` registry. Tier-2 distillation gets the strictest `TIER_2_DENY` list. These conventions reuse the same registry.
- **Archetype-specific overrides** — `play-novel` may extend Essential Teachings to character-voicing constraints; `aphorism-collection` skips Essential Teachings (each aphorism IS the teaching).
- **Provenance** — These four conventions were locked across two interactive planning sessions with Asif on 2026-05-22. Five Claude pushbacks accepted; see git log for the original `podcast-intelligence-enhancements.md` history.
