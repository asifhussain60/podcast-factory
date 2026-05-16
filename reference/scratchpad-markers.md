# Scratchpad Markers (`@@`) — Canonical Reference

**Authoritative spec for the `@@` marker vocabulary.** Used by both the `journal` skill (memoir chapters) and the `podcast` skill (refined episodes). Any future skill that takes a canonical text file and lets the user mark up a parallel scratchpad for refinement should cite this file as the source of truth.

**Supersedes:** the marker section in `reference/memoir-rules-supplement.txt` Section E. That older document remains accurate for the 9 verbs it covers; this document is the consolidated, current spec including the podcast-specific `@@pronounce` addition.

---

## The mental model

A **canonical file** is the finished artifact — a memoir chapter in `chapters/`, a refined podcast episode in `_workspace/podcast/<slug>/01-refined/`. The canonical file is what gets shipped: NotebookLM ingests it; the memoir publishes it.

A **scratchpad file** mirrors the canonical file and carries `@@` markers. The user writes markers in the scratchpad; I scan, process, and strip them; then I rewrite the canonical file. The scratchpad and canonical stay in sync but exist for different purposes — the canonical for delivery, the scratchpad for direction-from-the-user.

Markers never appear in canonical files. They are stripped on every refinement pass.

## The 11-verb vocabulary

| Token | Purpose | Argument form | Example |
|---|---|---|---|
| `@@refine` | Sharpen this sentence or paragraph | none | `@@refine` |
| `@@replace` | Find a stronger word | optional hint | `@@replace`, `@@replace(stronger than "great")` |
| `@@expand` | Flesh out, add detail, slow down | optional hint | `@@expand`, `@@expand(more on Ghazali's tone)` |
| `@@cut` | Remove — does not earn its place | none | `@@cut` |
| `@@move` | Relocate the marked content | destination | `@@move(to section 3)`, `@@move(to next episode)` |
| `@@note` | Message to me — not content | freeform | `@@note(check this verse number against Quran 18:110)` |
| `@@merge` | Combine paragraphs or sections | optional direction | `@@merge`, `@@merge(with next)`, `@@merge(with section above)` |
| `@@rephrase` | Propose 2-3 alternate phrasings | optional hint | `@@rephrase`, `@@rephrase(more conversational)` |
| `@@split` | Break this paragraph or section apart | optional hint | `@@split`, `@@split(after "lion")` |
| `@@pronounce` | Override phonetic for a term (podcast only) | `term: phonetic` | `@@pronounce(Tasawwuf: Ta-saw-woof)` |
| `@@policy` | Series-wide directive — applies to every refinement pass on every chapter or episode | freeform directive | `@@policy(reduce formality across all episodes — more conversational, fewer ceremonial connectors)` |

## Three tiers of scope

Markers fall into three tiers based on how they propagate. The classification is fixed by verb, not by user choice — every marker has exactly one tier.

### Tier 1 — Local (8 verbs)

`@@refine`, `@@replace`, `@@expand`, `@@cut`, `@@move`, `@@merge`, `@@rephrase`, `@@split`.

Apply only to where the marker is placed. Cannot propagate because they reference specific content whose words differ in every chapter or episode. `@@cut` a paragraph in Episode 1; that does not cut anything in Episode 2.

`@@note` is also local — it's a message about specific content at that location.

### Tier 2 — Mechanical (1 verb)

`@@pronounce(term: phonetic)`.

Auto-propagates. The term and phonetic are unambiguous; once the user has decided that *Sunnah* should be spoken *Soon-nah*, that fact is true everywhere in the series. On processing, the skill detects every `@@pronounce` marker, asks for one-line confirmation, then propagates the override to every other chapter or episode in the project. The series-wide pronunciation guide (`03-pronunciation.md`) is NOT modified by this — `@@pronounce` is an *override*, scoped to this run.

### Tier 3 — Policy (1 verb)

`@@policy(directive)`.

Lifted into `scratchpad/series-policies.md` and applied as augmentation to Stage 12 Hard Rules on every refinement pass — for the marked chapter and for every other chapter or episode the skill subsequently refines.

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

When the user invokes refinement on a chapter or episode whose scratchpad contains `@@pronounce` or `@@policy` markers:

1. **Scan** the scratchpad. Classify every marker by tier.
2. **Apply local (Tier 1) markers** to this chapter's canonical file. Strip them.
3. **Lift Tier 2 + Tier 3 markers** into proposed entries. Show the user:
   ```
   Detected propagation candidates:
   • 2 pronunciation overrides — auto-propagate to remaining N chapters?
   • 3 series policies — record in series-policies.md and apply to remaining N chapters?
   ```
4. **User confirms or declines.** Declined entries are dropped; accepted entries are recorded.
5. **Run Stage 12 refinement** on every other chapter/episode in the project with the policies augmenting Hard Rules. Each chapter is refined once under the new policies; no per-chapter markers needed.
6. **Strip the Tier 2 + Tier 3 markers** from the original scratchpad (they have been recorded in their persistent locations).
7. **Write the marker manifest** documenting what propagated and what stayed local.

If the user wants to mark up one chapter and have the rest of the series inherit those changes, the workflow above is the path. Local markers handle "fix this specific spot"; policies handle "everywhere in the series, do this differently."

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

### Per-canonical-file scratchpad pattern

| Skill | Canonical | Scratchpad |
|---|---|---|
| journal | `chapters/ch03-marriage.txt` | `scratchpad/scratch-marriage.txt` |
| podcast | `_workspace/podcast/<slug>/01-refined/episode-NN-<slug>.md` | `_workspace/podcast/<slug>/scratchpad/episode-NN-<slug>.scratch.md` |

Same pattern, same lifecycle, same vocabulary. Skill differs only in where it scans.

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

Markers are for **changes the user wants me to make to the canonical text**. They are not for:

- **Per-episode metadata** (NotebookLM format, length setting, source-chapter mapping) → edit `_meta/_segments/segments.yml` directly.
- **Segmentation boundaries** (where one episode ends and the next begins) → edit `segments.yml`; the skill re-segments on next run.
- **Pronunciation guide entries that apply to the whole series** → edit `03-pronunciation.md` directly. Use `@@pronounce` only when overriding the canonical phonetic for a single episode.
- **Editorial provenance** (why a passage was added or removed) → editorial-notes.md, not a marker.

If the answer is "edit a configuration file," that's not a marker.

## Validation

`server/scripts/validate-markers.mjs` enforces:
- Every `@@` marker uses one of the 10 known verbs.
- Marker format is parseable (verb + optional parenthesized argument).
- Canonical files contain zero markers.
- The validator scans `chapters/`, `chapters/scratchpads/`, and `_workspace/podcast/*/scratchpad/`.

A failed validation halts the build/commit until the markers are cleaned up.
