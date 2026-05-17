# Scratchpad Markers (`@@`) — Journal Skill Reference

**Authoritative spec for the `@@` marker vocabulary within the journal skill.** Used for memoir chapter refinement via memoir chapter scratchpads in `content/babu-memoir/_system/scratchpad/`. The podcast skill maintains a parallel, independent copy at `content/podcast/.skill/handbook/scratchpad-markers.md`. The two copies are independent; changes to one do not require changes to the other.

---

## The mental model

A **canonical file** is the finished artifact — a memoir chapter in `content/babu-memoir/chapters/`. The canonical file is what gets shipped and published.

A **scratchpad file** mirrors the canonical file and carries `@@` markers. The user writes markers in the scratchpad; the skill scans, processes, and strips them; then it rewrites the canonical file. The scratchpad and canonical stay in sync but serve different purposes: the canonical for delivery, the scratchpad for direction-from-the-user.

Markers never appear in canonical files. They are stripped on every refinement pass.

## The 10-verb vocabulary

| Token | Purpose | Argument form | Example |
|---|---|---|---|
| `@@refine` | Sharpen this sentence or paragraph | none | `@@refine` |
| `@@replace` | Find a stronger word | optional hint | `@@replace`, `@@replace(stronger than "great")` |
| `@@expand` | Flesh out, add detail, slow down | optional hint | `@@expand`, `@@expand(more on Ghazali's tone)` |
| `@@cut` | Remove — does not earn its place | none | `@@cut` |
| `@@move` | Relocate the marked content | destination | `@@move(to section 3)`, `@@move(to next episode)` |
| `@@note` | Message to me — not content | freeform | `@@note(check this verse number against Quran 18:110)` |
| `@@merge` | Combine paragraphs or sections | optional direction | `@@merge`, `@@merge(with next)`, `@@merge(with section above)` |
| `@@rephrase` | Propose 2–3 alternate phrasings | optional hint | `@@rephrase`, `@@rephrase(more conversational)` |
| `@@split` | Break this paragraph or section apart | optional hint | `@@split`, `@@split(after "lion")` |
| `@@policy` | Series-wide directive — applies to every refinement pass on every chapter | freeform directive | `@@policy(reduce formality across all chapters — more conversational, fewer ceremonial connectors)` |

## Two tiers of scope

Markers fall into two tiers based on how they propagate.

### Tier 1 — Local (9 verbs)

`@@refine`, `@@replace`, `@@expand`, `@@cut`, `@@move`, `@@merge`, `@@rephrase`, `@@split`.

Apply only to where the marker is placed. Cannot propagate because they reference specific content whose words differ in every chapter. `@@cut` a paragraph in ch01; that does not cut anything in ch02.

`@@note` is also local — it's a message about specific content at that location.

### Tier 2 — Policy (1 verb)

`@@policy(directive)`.

Lifted into `content/babu-memoir/_system/scratchpad/series-policies.md` and applied as augmentation to every refinement pass — for the marked chapter and for every other chapter the skill subsequently refines.

The policy file is a persistent style guide for the project. Each entry has provenance (which scratchpad it came from, when), the directive itself, and an active/inactive flag. The user can edit the file directly to adjust, deactivate, or remove policies.

Policies are typed by what they affect:

| Policy type | Example |
|---|---|
| Voice / tone | `@@policy(reduce formality across all episodes — more conversational, fewer ceremonial connectors)` |
| Structural | `@@policy(every Quranic transliteration's English meaning lands on its own line)` |
| Lexical | `@@policy(replace "Allah Ta'ala" with "Allah" except in opening salutations)` |
| Pacing | `@@policy(closings land harder — short final sentence, no trailing meta-commentary)` |
| Gloss handling | `@@policy(Sufi technical terms get their English gloss only on first appearance per episode, never thereafter)` |

A `@@policy` marker is processed once: it gets recorded in `series-policies.md`. The directive then augments Stage 12 for every future refinement until the user deactivates it. Re-marking a policy that's already active is a no-op.

## Propagation workflow

When the user invokes refinement on a chapter whose scratchpad contains `@@policy` markers:

1. **Scan** the scratchpad. Classify every marker by tier.
2. **Apply local (Tier 1) markers** to this chapter's canonical file. Strip them.
3. **Lift Tier 2 markers** into proposed entries. Show the user:
   ```
   Detected propagation candidates:
   • 3 series policies — record in series-policies.md and apply to remaining N chapters?
   ```
4. **User confirms or declines.** Declined entries are dropped; accepted entries are recorded.
5. **Run Stage 12 refinement** on every other chapter in the project with the policies augmenting Hard Rules. Each chapter is refined once under the new policies.
6. **Strip the Tier 2 markers** from the original scratchpad (they have been recorded in their persistent location).
7. **Write the marker manifest** documenting what propagated and what stayed local.

### Argument syntax

- Parentheses are optional when no argument is needed: `@@refine` and `@@refine()` are equivalent.
- Inside parentheses, the first colon separates a key from a value when the verb expects a key (e.g., `@@pronounce(Tasawwuf: Ta-saw-woof)`).
- For verbs that take freeform hints, the entire parenthetical is the hint.
- Marker placement: at the **start of a line** when it applies to that line's content; on its own line above a paragraph when it applies to the paragraph; on the section header line when it applies to the whole section.

## Lifecycle

1. **User edits the scratchpad.** Drops markers wherever they want changes. Saves.
2. **User invokes the relevant skill.** "Refine episode 1" or "rebuild chapter 3."
3. **Skill scans the scratchpad** for `@@` markers. Builds a marker manifest with file, line, verb, args.
4. **Skill processes each marker.**
   - For content-mutating markers (refine, replace, expand, cut, merge, rephrase, split): apply the change.
   - For meta markers (note, move, pronounce): record the directive, apply across both scratchpad and canonical as appropriate.
5. **Skill rewrites the canonical file** with the changes applied. Markers do not appear in the canonical.
6. **Skill strips processed markers from the scratchpad.** The legend block and per-section one-liners stay; only the user-added markers are removed.
7. **Skill validates** via `validate-markers.mjs` (or its successor): every remaining marker uses a known verb; the canonical file has zero markers.

The scratchpad never becomes a long-lived artifact carrying stale markers. Every pass cleans itself.

## File layout

### Per-chapter scratchpad pattern

| Skill | Canonical | Scratchpad |
|---|---|---|
| journal | `content/babu-memoir/chapters/ch03-marriage.txt` | `content/babu-memoir/_system/scratchpad/scratch-marriage.txt` |

### Scratchpad file structure

```
=== @@ QUICK MARKERS, drop at start of any line ===
@@refine     sharpen this sentence or paragraph
@@replace    find a stronger word
@@expand     flesh out, add detail, slow down
@@cut        remove this, it does not earn its place
@@move       relocate — @@move(to section 3)
@@note       message to Claude, not content
@@merge      combine paragraphs or sections
@@rephrase   propose 2-3 alternate phrasings
@@split      break this apart
@@pronounce  override phonetic — @@pronounce(Tasawwuf: Ta-saw-woof) — auto-propagates
@@policy     series-wide directive — @@policy(reduce formality across episodes) — propagates
=== END MARKERS ===

# Scratchpad: Episode 1 — The Frame and the First Counsel
# Mirror of 01-refined/episode-01-frame-and-first-counsel.md
# Markers stripped on every refinement pass.

[the canonical content, paragraph by paragraph, with @@ markers
sprinkled at the lines or paragraphs the user wants changed]
```

The marker legend at the top is reference for the user — they don't have to memorize the verbs. It is stripped at finalization (when the project ships) but persists through every refinement pass so the user always has the legend at hand.

## When *not* to use a marker

Markers are for **changes the user wants the journal skill to make to memoir chapter text**. They are not for:

- **Per-chapter metadata** — edit the chapter status file directly.
- **Pronunciation overrides on podcast episodes** — use the podcast skill's `@@pronounce` verb (in `skills-staging/podcast/references/scratchpad-markers.md`; the journal skill does not implement `@@pronounce`).
- **Editorial provenance** (why a passage was added or removed) — editorial-notes.md, not a marker.

If the answer is "edit a configuration file," that's not a marker.

## Validation

`server/scripts/validate-markers.mjs` enforces:
- Every `@@` marker in memoir files uses one of the 10 known journal verbs.
- Marker format is parseable (`@@verb` with optional parenthesized argument).
- Canonical chapter files contain zero markers.
- The validator scans `content/babu-memoir/chapters/` and `content/babu-memoir/_system/scratchpad/` only.

Podcast scratchpad validation is the podcast skill's own responsibility and is not part of this validator.

A failed validation halts the build/commit until the markers are cleaned up.
