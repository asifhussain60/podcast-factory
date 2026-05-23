# Backfill Mode — Retroactive Bundle Augmentation

When an enhancement (slide decks, future additions) is introduced after episodes already exist, Backfill Mode batch-augments those episodes without disrupting forward production.

KaR is the inaugural backfill target. Backfill Mode is general: future enhancements use the same workflow without per-enhancement custom scripts.

---

## When to Use

Backfill Mode runs when:

- A new enhancement adds a required artifact (folder, file, registry column) to the bundle.
- Existing episodes predate the enhancement and therefore lack the artifact.
- The enhancement's value depends on coverage across the back catalog, not just forward production.

Backfill Mode does NOT run when:

- An enhancement is purely forward-looking (e.g., a new audio steering pattern that's irrelevant to already-uploaded episodes).
- The enhancement is experimental and may be reverted.
- The episodes in scope are flagged for archival.

---

## Trigger

```
/podcast backfill [scope]
```

Where `[scope]` is one of:
- A book slug (e.g., `KaR`) — backfills all episodes under that book
- A series identifier — backfills all episodes in a named series
- `all` — backfills every episode in the workspace
- A range (e.g., `EP01..EP05`) — backfills a specific episode range

---

## Workflow

### Phase B1 — Inventory

1. Enumerate every episode folder in scope.
2. For each, check what artifacts the enhancement requires (e.g., `slide-decks/EP##-[slug]/` for the slide-deck enhancement).
3. Tag each episode as one of:
   - `MISSING` — artifact is absent, needs backfill
   - `PRESENT` — artifact already exists (skip)
   - `PARTIAL` — artifact exists but incomplete (treat as MISSING)
4. Output an inventory table:

```
EP01-[slug]: MISSING — needs slide-deck folder
EP02-[slug]: MISSING — needs slide-deck folder
EP03-[slug]: PRESENT — skip
...
```

### Phase B2 — Reuse Audit

For each episode marked MISSING:

1. Verify the audio bundle is intact and complete (5 mandatory files present).
2. Verify `04-discussion-spine.md` is structured and parseable.
3. Confirm `02-key-passages.md` and `03-context-pack.md` are usable as inputs.

If any episode's audio bundle is itself incomplete, Backfill Mode FLAGS that episode as a separate audio-bundle defect — backfill does not proceed for that episode until the audio bundle is healed.

Backfill Mode never silently produces a slide deck on top of a broken audio bundle.

### Phase B3 — Density Gauge

For each healthy episode, measure visual moment density before building:

```
density = count of [VISUAL CANDIDATE] beats / total beats in discussion spine
```

If beats are not yet tagged (pre-enhancement audio bundle), Backfill Mode tags them now as part of the workflow.

**Thresholds**:
- `density ≥ 0.5` — slide deck is strongly warranted. Build standard.
- `0.25 ≤ density < 0.5` — slide deck is warranted. Build, but anticipate fewer slides.
- `density < 0.25` — slide deck is questionable. Trigger justified-skip flow: produce a justification entry naming the source's lack of structural content. Challenger reviews the justification (Probe 7) before the skip is accepted.

The density gauge is also the foundation of forward-mode opt-outs. The same threshold applies to new episodes.

### Phase B4 — Beat ID Assignment

For backfilled episodes, the discussion-spine beats receive monotonic IDs (`B01`, `B02`, …) in order of appearance. This is a non-destructive edit to `04-discussion-spine.md` — IDs are added to existing beat headings without altering content.

The Slide Deck `Anchor:` field requires these IDs. Backfilled episodes whose audio bundle predates the beat-ID convention have IDs added here.

### Phase B5 — Distill Diff

Lightweight Phase 2 pass per episode. Inputs are the existing audio bundle artifacts; no new source distillation needed.

Process:
1. Re-read `04-discussion-spine.md`.
2. Tag each beat as `[VISUAL CANDIDATE]` or `[AUDIO-ONLY]` (or carry forward existing tags).
3. Identify the likely diagram type for each `[VISUAL CANDIDATE]` beat, drawing on `slide-deck-patterns.md` and the source-type affinity matrix.
4. Note any beats that would benefit from cross-episode visual consistency (see Per-Book Visual Registry below).

Output a distill-diff document in `_workspace/EP##-[slug]/distill-diff.md` — NOT in the episode folder.

### Phase B6 — Build

Run Phase 3 of the standard skill workflow in **slide-deck-only mode**:

1. Create `slide-decks/EP##-[slug]/`.
2. Build `00-slide-framing.md` per spec.
3. Build `01-slide-spine.md` per spec, anchoring slides to beat IDs.
4. Optionally build `02-visual-glossary.md` if cross-episode consistency requires it.

The audio bundle is UNTOUCHED. Backfill Mode does not modify audio bundle files except for the beat-ID assignment in Phase B4 (which is metadata, not content).

### Phase B7 — Challenger

Run the Slide Deck Challenger per `slide-deck-challenger.md`. Same probes, same pass/fail authority, same iteration protocol.

A backfilled deck has no special pass criteria. It either passes or it iterates.

### Phase B8 — Register

Update `_registry.md`:

- `slide-deck-status` → `ready` (or `not-needed` with justification)
- `challenger-status` → `pass`
- `backfill-batch` → batch identifier (e.g., `KaR-backfill-2026-05`)

### Phase B9 — Batch Close

After all episodes in scope have either passed or are flagged as needing manual intervention, Backfill Mode emits a batch summary report to `_workspace/_batches/[batch-id].md`:

- Episodes processed
- Episodes passed
- Episodes flagged (audio bundle defects, persistent Challenger failures, justified skips)
- Time elapsed
- Steering phrases / patterns that emerged for promotion to permanent reference files

---

## Per-Book Visual Registry

Multi-episode series (KaR, future books) maintain a per-book visual registry at:

```
slide-decks/_visual-registry.md
```

Or, if episodes are organized per-book:

```
books/[book-slug]/slide-decks/_visual-registry.md
```

The registry tracks entities, themes, and motifs that recur across episodes and need consistent visual treatment.

### Registry Schema

```markdown
# Visual Registry — [book-slug]

## Entity: [name]
- **Visual convention**: [color, position, shape, treatment]
- **First defined in**: EP##
- **Reason**: [why this convention]
- **Episodes referencing**: EP##, EP##, ...

## Theme: [name]
- **Visual convention**: [recurring diagram type, framing approach]
- **First defined in**: EP##
- **Episodes referencing**: EP##, EP##, ...
```

### When the Registry Updates

- A new entity earns an entry when it appears in 2+ episodes.
- An entity's convention CAN change between episodes if there's a documented reason — the registry entry then notes the transition.
- The Challenger's Cross-Episode Consistency check (Architectural Pass 4) reads the registry.

### Backfill Registry Strategy

For KaR (and any backfill target):

1. During Phase B5 (distill diff), tag recurring entities across episodes.
2. After all backfill episodes complete Phase B6, generate a draft registry.
3. The draft registry is reviewed and finalized.
4. The finalized registry is referenced by all backfilled `00-slide-framing.md` files retroactively (Steering Phrases section, Category 6).

If conventions emerge that conflict across early episodes (e.g., EP01 puts Ghazali left, EP03 puts him right), Backfill Mode flags the conflict and asks Asif to pick the convention. The "losing" episode's slide deck is re-iterated with the chosen convention.

---

## KaR-Specific Instructions

**Scope**: all existing KaR episodes in the podcast workspace.

**Order**: **oldest first**. The earliest KaR episodes establish the visual language. Backfilling oldest-first means the per-book visual registry grows naturally and later episodes inherit conventions rather than colliding with them.

**Gating**: each KaR episode's slide-deck folder must pass the Challenger before the next KaR episode's backfill begins. No parallel backfills within KaR.

**First three episodes — learning phase**: the first three KaR backfills are treated as a learning phase. Their Challenger reports inform refinement of `slide-deck-steering.md` and `slide-deck-patterns.md` BEFORE backfill 4 begins.

After backfill 3:
- Promote any candidate steering phrases that demonstrably helped.
- Promote any candidate diagram patterns that emerged.
- Add any new probes (rare; only if a failure mode appeared that the existing probes missed).

Then continue with the rest of the KaR backfill at standard pace.

**Batch identifier**: `KaR-backfill-[YYYY-MM]` based on the month the batch begins.

**Forward production**: no new (non-KaR) episodes are produced until the KaR backfill completes. This is a hard sequencing rule — slide-deck patterns mature on KaR before being applied to new books.

---

## Failure Modes and Handling

### Persistent Challenger Failure

If an episode fails the Challenger 3 times in a row during backfill:

1. Stop iterating on that episode.
2. Flag it in `_workspace/_batches/[batch-id].md` as `STUCK`.
3. Continue with the next episode in scope.
4. Asif reviews stuck episodes manually after the batch.

### Audio Bundle Defect

If the audio bundle for a backfill target is itself broken:

1. Skip the slide-deck backfill for that episode.
2. Flag the episode as `AUDIO-DEFECT`.
3. Audio bundle repair is out of Backfill Mode's scope — it's a separate workflow.

### Density Below Threshold

If `density < 0.25` and the justified-skip flow produces a Challenger-passable justification:

1. Mark `slide-deck-status = not-needed` with justification reference.
2. The episode is considered backfilled (correctly skipped).
3. The justification is itself logged so future patterns can be detected (e.g., if 30% of an entire book's episodes are below threshold, the slide-deck enhancement may not be a good fit for that book at all).

---

## Future Backfill Triggers (Not Yet Active)

This section is a stub for future enhancements that will use Backfill Mode. Each will document its own Phase B5 (distill diff) logic and Phase B6 (build) logic when introduced. Backfill Mode's other phases (inventory, density gauge, beat IDs, challenger, register, batch close) are reusable.
