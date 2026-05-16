# Podcast Scratchpad Markers (`@@`) — Podcast Skill Reference

**Authoritative spec for the `@@` marker vocabulary within the podcast skill.** Podcast owns this copy. The journal skill maintains a parallel copy at `content/babu-memoir/_system/scratchpad-markers.md` for memoir chapters. The two copies are independent; changes to one do not require changes to the other.

---

## The mental model

A **canonical file** is the finished artifact — a refined podcast episode at `content/podcast/<book>/_system/episode-drafts/EP##-<slug>/01-source-primary.md`. The canonical file is what NotebookLM ingests.

A **scratchpad file** mirrors the canonical file and carries `@@` markers. The user writes markers in the scratchpad; the skill scans, processes, and strips them; then it rewrites the canonical file. The scratchpad and canonical stay in sync but serve different purposes: the canonical for delivery, the scratchpad for direction-from-the-user.

Markers never appear in canonical files. They are stripped on every refinement pass.

## The 11-verb vocabulary

| Token | Purpose | Argument form | Example |
|---|---|---|---|
| `@@refine` | Sharpen this sentence or paragraph | none | `@@refine` |
| `@@replace` | Find a stronger word | optional hint | `@@replace`, `@@replace(stronger than "great")` |
| `@@expand` | Flesh out, add detail, slow down | optional hint | `@@expand`, `@@expand(more on Ghazali's tone)` |
| `@@cut` | Remove — does not earn its place | none | `@@cut` |
| `@@move` | Relocate the marked content | destination | `@@move(to Movement 5)`, `@@move(to next episode)` |
| `@@note` | Message to the skill — not content | freeform | `@@note(check verse number against Quran 18:110)` |
| `@@merge` | Combine paragraphs or sections | optional direction | `@@merge`, `@@merge(with next)`, `@@merge(with section above)` |
| `@@rephrase` | Propose 2–3 alternate phrasings | optional hint | `@@rephrase`, `@@rephrase(more conversational)` |
| `@@split` | Break this paragraph or section apart | optional hint | `@@split`, `@@split(after "lion")` |
| `@@pronounce` | Override phonetic for an Arabic or foreign term | `term: phonetic` | `@@pronounce(Tasawwuf: Ta-saw-woof)` |
| `@@policy` | Series-wide directive — applied to every future episode in this series | freeform directive | `@@policy(reduce formality across all episodes — more conversational, fewer ceremonial connectors)` |

## Three tiers of scope

Markers fall into three tiers based on how they propagate. The classification is fixed by verb, not by user choice — every marker has exactly one tier.

### Tier 1 — Local (9 verbs)

`@@refine`, `@@replace`, `@@expand`, `@@cut`, `@@move`, `@@note`, `@@merge`, `@@rephrase`, `@@split`.

Apply only to where the marker is placed. Cannot propagate because they reference specific content whose words differ in every episode. `@@cut` a paragraph in EP01; that does not cut anything in EP02.

`@@note` is also local — it's a message about specific content at that location.

### Tier 2 — Mechanical propagation (1 verb)

`@@pronounce(term: phonetic)`.

Auto-propagates. Once the user decides that *Sunnah* should be spoken *Soon-nah*, that fact is true everywhere in the series. On processing, the skill detects every `@@pronounce` marker, asks for one-line confirmation, then applies the override to every other episode in the project. The series-wide pronunciation guide is NOT modified; `@@pronounce` is a per-run override.

### Tier 3 — Policy (1 verb)

`@@policy(directive)`.

Lifted into `content/podcast/<book>/_system/scratchpad/series-policies.md` and applied as augmentation to every future refinement pass. Each entry has provenance (which scratchpad, which date), the directive, and an active/inactive flag.

Policies are typed by what they affect:

| Policy type | Example |
|---|---|
| Voice / tone | `@@policy(reduce formality across all episodes — more conversational, fewer ceremonial connectors)` |
| Structural | `@@policy(every Quranic transliteration's English meaning lands on its own line)` |
| Lexical | `@@policy(replace "Allah Ta'ala" with "Allah" except in opening salutations)` |
| Pacing | `@@policy(closings land harder — short final sentence, no trailing meta-commentary)` |
| Gloss handling | `@@policy(Sufi technical terms get their English gloss only on first appearance per episode, never thereafter)` |

A `@@policy` marker is processed once: it gets recorded in `series-policies.md`. The directive then augments every future refinement until the user deactivates it. Re-marking a policy that's already active is a no-op.

## Propagation workflow

When the user invokes refinement on an episode whose scratchpad contains `@@pronounce` or `@@policy` markers:

1. **Scan** the scratchpad. Classify every marker by tier.
2. **Apply local (Tier 1) markers** to this episode's canonical file. Strip them.
3. **Lift Tier 2 + Tier 3 markers** into proposed entries. Show the user:
   ```
   Detected propagation candidates:
   • 2 pronunciation overrides — auto-propagate to remaining N episodes?
   • 3 series policies — record in series-policies.md and apply to remaining N episodes?
   ```
4. **User confirms or declines.** Declined entries are dropped; accepted entries are recorded.
5. **Run refinement** on every other episode in the project with the policies augmenting the quality rules. Each episode is refined once under the new policies.
6. **Strip the Tier 2 + Tier 3 markers** from the original scratchpad (they have been recorded in their persistent locations).
7. **Write the marker manifest** documenting what propagated and what stayed local.

### Argument syntax

- Parentheses are optional when no argument is needed: `@@refine` and `@@refine()` are equivalent.
- Inside parentheses, the first colon separates key from value for `@@pronounce`: `@@pronounce(Tasawwuf: Ta-saw-woof)`.
- For hint verbs, the entire parenthetical is the hint.
- Marker placement: at the **start of a line** when it applies to that line; on its own line above a paragraph when it applies to the paragraph; on a section header when it applies to the whole section.

## Lifecycle

1. **User edits the scratchpad.** Drops markers wherever they want changes. Saves.
2. **User invokes the podcast skill.** "Refine EP01" or "rebuild EP02 source."
3. **Skill scans the scratchpad** for `@@` markers. Builds a marker manifest with file, line, verb, args.
4. **Skill processes each marker.**
   - For content-mutating markers (refine, replace, expand, cut, merge, rephrase, split): apply the change.
   - For meta markers (note, move): record the directive, apply to both scratchpad and canonical as appropriate.
   - For pronounce: surface for one-line confirmation, then propagate on accept.
5. **Skill rewrites the canonical file** with the changes applied. Markers do not appear in the canonical.
6. **Skill strips processed markers from the scratchpad.** The legend block persists; only the user-added markers are removed.
7. **Skill validates** that every remaining marker uses a known verb and the canonical file has zero markers.

The scratchpad never becomes a long-lived artifact carrying stale markers. Every pass cleans itself.

## File layout

### Per-episode scratchpad pattern

| Skill | Canonical | Scratchpad |
|---|---|---|
| podcast | `content/podcast/ayyuhal-walad/_system/episode-drafts/EP01-ayyuhal-walad-ch1/01-source-primary.md` | `content/podcast/ayyuhal-walad/_system/episode-drafts/EP01-ayyuhal-walad-ch1/01-source-primary.scratch.md` |

### Scratchpad file structure

```
=== @@ QUICK MARKERS, drop at start of any line ===
@@refine     sharpen this sentence or paragraph
@@replace    find a stronger word, @@replace(stronger than "great") optional hint
@@expand     flesh out, add detail, slow down, @@expand(more on the angel) optional hint
@@cut        remove this, it does not earn its place
@@move       relocate, @@move(to Movement 5) destination required
@@note       message to me, not content, @@note(check verse number against Quran 18:110)
@@merge      combine paragraphs or sections, @@merge(with next) optional direction
@@rephrase   propose 2-3 alternate phrasings, @@rephrase(more conversational) optional hint
@@split      break this apart, @@split(after "lion") optional hint
@@pronounce  override phonetic, @@pronounce(Tasawwuf: Ta-saw-woof), auto-propagates across episodes
@@policy     series-wide directive, @@policy(reduce formality across all episodes), propagates
=== END MARKERS ===

# Scratchpad, EP##, 01-source-primary.md
# Mirror of: content/podcast/<book>/_system/episode-drafts/EP##-<slug>/01-source-primary.md
# Purpose: refinement + enrichment surface. Drop @@ markers wherever you want changes.
# Markers are stripped from the canonical on every refinement pass. The legend above persists.
# Re-invoke the podcast skill (e.g. "refine EP01") to apply your markup.

[canonical content here]
```

The marker legend at the top is reference for the user — they don't have to memorize the verbs. It is stripped at finalization (when the episode ships) but persists through every refinement pass.

## What NOT to use markers for

- **Pronunciation entries that apply to the whole series permanently** — edit `content/podcast/<book>/_system/pronunciation.md` directly. Use `@@pronounce` only for a per-run override.
- **Episode metadata** — edit the registry directly.
- **Content outside podcast episodic files** — this vocabulary does not apply to journal memoir chapters.

## Permitted library feed (the only journal connection)

After processing an episode, the podcast skill MAY propose additions to the journal's shared libraries:

- `content/babu-memoir/_system/quotes-library.txt` — propose a quote entry if the episode surfaces a passage likely to inform memoir work.
- `content/babu-memoir/_system/clinic-library.txt` — propose a craft observation if the episode's source material contains a technique relevant to memoir craft.

**How to propose:** Write the proposed entry to `content/podcast/<book>/_system/episode-drafts/EP##-<slug>/proposed-library-entries.md`. Do NOT write directly to `content/babu-memoir/_system/quotes-library.txt` or `content/babu-memoir/_system/clinic-library.txt`. The journal skill owns those files; Asif routes the proposal himself.

The podcast skill reads nothing from `content/babu-memoir/`. Proposals flow outward only.
