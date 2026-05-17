# Episode Architecture — Beats, Hook, Landing

The discussion spine (`04-discussion-spine.md`) is the hidden steering layer. NotebookLM hosts will follow the spine when it's well-built. This document codifies how a good spine is shaped.

## Beat count

  - **Tight episode (~8 min)**: 5–6 beats
  - **Standard episode (~12–15 min)**: 7–10 beats
  - **Long-form (~25 min+)**: 10–14 beats

Below 5 beats: hosts ramble. Above 14: hosts compress past anything meaningful.

## Beat shape

Every beat in the spine has the same structure:

```markdown
### Beat N: [Beat title]
- **Key question:** What's the question this beat is asking?
- **Tension:** What's the friction in this beat?
- **Anchor passage:** Reference (or short quote from) the passage from `02-key-passages.md`
- **Landing:** What state does this beat leave the listener in?
```

The "Key question" is the host instinct. The "Tension" is what makes the beat alive. The "Anchor passage" is what NotebookLM retrieves when discussing the beat. The "Landing" is the emotional/intellectual residue.

## The arc across beats

A good spine has SHAPE. Beats should not be parallel or interchangeable. Common patterns:

### Pattern 1 — Pressure Build
Beats build escalating pressure. Each beat raises the stakes. Final beat lands at maximum pressure, then resolves or leaves open.

  - Beat 1: opening hook (low pressure, high curiosity)
  - Beats 2–N-2: build tension progressively
  - Beat N-1: peak pressure
  - Beat N: resolution OR open question

### Pattern 2 — Lens Rotation
Each beat looks at the same core question from a different angle. Useful for philosophical/spiritual sources.

  - Beat 1: state the question
  - Beats 2–N-1: rotate through angles (historical, personal, traditional, critical, lived)
  - Beat N: synthesis or unresolved residue

### Pattern 3 — Counterpoint
Two positions in conversation, alternating beat by beat.

  - Beat 1: Position A
  - Beat 2: Position B
  - Beat 3: Position A again, but deeper
  - Beat 4: Position B again, with the counter
  - ...
  - Final beat: where the listener now stands

### Pattern 4 — Narrative Walk-Through
Used when the source IS a narrative (chapter, memoir, story). Beats follow the source's own arc.

  - Beat 1: opening scene
  - Beats 2–N-1: key moments in order
  - Beat N: the residue the narrative leaves

## Opening hook (Beat 1)

NEVER let Beat 1 be "today we'll be discussing [source]." The framing instruction "Don't open with 'today we'll discuss...' — start in the middle of the question" handles this, but the spine has to support it.

**Strong Beat 1 patterns**:
  - Start with a single passage. "Listen to how [author] opens this..."
  - Start with a question the source forces. "Is [X] really [Y]? [Author] doesn't think so."
  - Start with a misunderstanding. "Most readers think this is about X. It isn't."
  - Start with a tension the listener walks in with. "We tend to assume Y. [Author] is going to argue the opposite."

The opening should make the listener lean in, not nod along.

## Closing beat (Beat N)

The closing beat decides what the listener carries out of the episode. Strong closings:

  - **Open question**: leave the listener with a question they didn't have before
  - **Anchor quote**: end with a passage from the source, read in full, no host commentary
  - **Listener invitation**: turn the episode toward the listener's own life (works especially for memoir / spiritual sources)
  - **Tension preserved**: explicitly refuse to resolve the central tension

Avoid:
  - Summary of what we covered (filler)
  - "So in conclusion..." (lecture energy)
  - Cheerful sign-off (false closure)
  - Teaser for a future episode (we don't run a series — each episode is standalone)

## Beat anchors — make the spine usable

For each beat, link to an actual passage in `02-key-passages.md`. The anchor passage is what NotebookLM retrieves when the spine directs hosts to that beat. Without anchors, the spine is decorative.

If a beat has no anchor passage available, either:
  - Add the passage to `02-key-passages.md`
  - Remove the beat
  - Mark the beat `[NO ANCHOR — RELIES ON CONTEXT PACK]` and link to a `03-context-pack.md` section

## Tension density

Every beat should have at least one named tension. Beats without tension feel flat to the hosts; they paraphrase rather than discuss.

Tensions can be:
  - **Internal** — the author argues with themselves
  - **Against tradition** — the author breaks with their tradition
  - **Against modernity** — the source pushes back against contemporary assumptions
  - **Against the reader** — the source asks something hard of the listener
  - **Across sources** (multi-source) — two sources in conflict

Avoid tensions that are stock/generic ("faith vs. reason"). Name the SPECIFIC tension in THIS source.

## Pacing within the spine

Not every beat is equal weight. In the spine, mark heavy beats with a longer Landing description, light beats with a shorter one. NotebookLM retrieves the Landing text and uses it as a signal for how much airtime to give a beat.

  - Heavy beat → 2–3 sentence Landing
  - Light beat → 1 sentence Landing

This is how we modulate pacing without word-count instructions (which NotebookLM ignores).

## What a finished spine looks like

A spine that passes the quality gate has:
  - 6–12 beats with consistent structure
  - Clear opening hook (Beat 1 is not generic)
  - Each beat has Key question + Tension + Anchor + Landing
  - The arc fits one of the four patterns above (or a deliberate variant)
  - Closing beat lands the episode without summarizing it
  - At least one beat has explicit "Quote in full" instruction in the Anchor
