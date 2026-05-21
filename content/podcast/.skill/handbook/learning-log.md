# Cross-book learning log

**Framework-level lessons captured from per-book audit cycles.** When a
pattern shows up across 2+ books, OR when a single book's iteration cap is
hit on the same issue 3 times, the learning lands here. Future books'
Phase 0g + per-chapter loop read this file at start; lessons auto-propagate.

For per-book learnings (lessons that only apply to one book's quirks), see
each book's `_system/podcast-quality-log.md`.

---

## How lessons get added here

Trigger conditions (any one):

1. **Same issue observed in 2+ books** — e.g., "every Arabic book mispronounces names ending in -ī" → fix once in the shared Arabic manifest + log here
2. **Single book hits the 3-iteration cap on the same dimension** — escalated by the per-book quality log
3. **Framework prompt edit triggered by a quality finding** — record the prompt edit + the originating finding here

Format per entry:

```
### YYYY-MM-DD — <short title>

**Trigger:** <book(s), episode(s), iteration(s) where this surfaced>
**Pattern observed:** <one paragraph; what was happening across cases>
**Fix landed at:** <file path(s) — Phase 0d prompt, Phase 0g prompt, SKILL.md, etc.>
**How future books pick it up:** <e.g., "next Phase 0d run reads new prompt automatically" or "operator must re-read SKILL.md §X">
**Validation:** <how we confirm the fix worked on the next book>
```

---

## Entries (newest first)

(Empty — populated as cross-book patterns emerge from the iteration loop.
First entries expected after Kitab al-Riyad's first 2-3 episodes are audited,
where book-specific vs framework-level patterns become distinguishable.)

---

## Where to read this from

| Reader | When | What it does |
|---|---|---|
| Phase 0d prompt | When scaffolding chapter contracts for a new book | Should inherit any prompt-level lessons logged here |
| Phase 0g prompt | When authoring per-episode customize prompts | Should inherit any framing lessons logged here |
| Challenger | When reviewing episode scripts | Should flag patterns already known to fail |
| Human reviewer (Asif) | Before launching a new book | Skim once; know what's been learned |

A future framework upgrade may make this an auto-included file in those
prompts; for now, manually reference in prompt edits.
