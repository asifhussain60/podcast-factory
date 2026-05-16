# Stage 11 — Add Modern Analogies

**Purpose:** Add modern analogies where they illuminate the source's meaning for a 2026 listener. Use the active tradition's `modern_analogy_register` to choose appropriate domains.

## Input

- `WORK_DIR/_enriched/section-NN-<slug>-enriched.md` (each enriched section)
- `traditions/<detected-tradition>.yml`

## Output

- `WORK_DIR/_analogized/section-NN-<slug>-analogized.md` — enriched section with analogies woven in.
- Updates to `_editorial-notes-draft.md` recording every analogy added.

## Hard rules

1. **Analogies are windows, not rooms.** An analogy clarifies the source's idea, then the prose returns to the source.
2. **No bracketed labels.** Never write `[Modern Example]`, `[Analogy]`, or similar.
3. **Period-appropriate.** Use the active tradition's `modern_analogy_register.preferred_domains`. Avoid `avoid_domains`.
4. **Audience-appropriate.** Adjust the register for the audience parameter (general, spiritual-studies, academic, youth, technical).
5. **Sparingly.** Not every passage needs an analogy. Add one only when the source's idea would be hard to grasp without it.

## When to add an analogy

Add an analogy when:

- The source presents an abstract concept that has a modern parallel (the three-levels-of-knowledge / interface-code-architecture example from your spec).
- The source describes a relationship or dynamic that maps cleanly to a modern equivalent (oath / professional licensing).
- The source warns against a behavior whose modern form is recognizable (blind imitation / algorithmic echo chambers).
- The source describes a process whose modern equivalent listeners encounter daily (spiritual discipline / apprenticeship).

## When NOT to add an analogy

- The source is already clear without one.
- The proposed analogy comes from `avoid_domains` of the active tradition.
- The analogy would dominate the surrounding prose.
- The analogy would impose a contemporary framing that the source did not invite (e.g., political party parallels for religious figures).
- You cannot find an analogy that genuinely clarifies — better silence than a stretched analogy.

## How to weave analogies

A modern analogy is typically 2–4 sentences woven into the surrounding prose. The pattern:

1. **The source's idea** (as the source states it).
2. **A modern analogy that maps to it** (concrete and recognizable).
3. **Return to the source's idea** (carrying the analogy's clarity forward).

Example (illustrative):

**Source:**
> "Now I understand that there are three levels of knowledge. There is its outer aspect, its inner aspect, and the innermost dimension of that inner aspect."

**With analogy woven in:**
> "The young man said, 'Now I understand that knowledge has three levels. First, there is the outward form. Then there is the inner meaning. And beyond that, there is the innermost meaning within the inner meaning.'
>
> A modern example would be a software application. The visible screen is the outward form — the buttons, menus, colors, and layout. The source code is the inner level. But beneath both is the architecture: the permissions, database, logic, and design principles that explain why the system exists and how all its parts are connected.
>
> The same three levels exist in revealed knowledge. The outward practice, the inner meaning of that practice, and the architecture that gives the meaning its coherence."

The analogy clarifies the abstract concept. The next sentence returns to the source's argument. Total: 4 added sentences. Not labeled.

## Density limits

- No more than 1 analogy per ~300 words of source content.
- No more than 4 analogies per section.
- Two analogies should not appear in adjacent paragraphs (they need breathing room).

If a section needs many analogies, consider whether you are over-explaining.

## Audience tuning

Adjust analogy register based on `audience` parameter:

| Audience | Register |
|---|---|
| general | Everyday domains: cooking, driving, friendship, work |
| spiritual-studies | Mentorship, vocation, formation, monastic disciplines |
| academic | Scholarly disciplines, peer review, methodology |
| youth | Gaming, social media (use sparingly — dates fast), school, sports |
| technical | Software, engineering, design, systems |

The tradition file's `preferred_domains` interacts with audience. The Ismaili tradition's preferred software-architecture analogies work well for technical audiences and acceptably for general audiences. They do not work for youth audiences without translation.

## Avoid these analogies (universal)

Regardless of tradition or audience, never use:

- **Pop-culture references** that will date within a year (specific TV shows, current memes).
- **Political party parallels** for religious or philosophical figures.
- **Brand analogies** (no "Faith is like Netflix").
- **Stock-market metaphors** for spiritual concepts.
- **Marketing-funnel parallels** for any covenantal or sacred relationship.
- **War metaphors** for inner spiritual work (war language reduces nuance).

## Updating editorial notes

For every analogy added, append to `_editorial-notes-draft.md`:

```markdown
## Analogy — Section [N], approximate line [N]

Domain: [Software architecture | Mentorship | Engineering | ...]
Active tradition: [Ismaili | none | ...]
Domain status: [preferred | acceptable]
Analogy text: "[the new prose added]"
Original concept being clarified: [one-line summary of source idea]
Length added: [N] words
```

## Failure modes

- All candidate analogies come from `avoid_domains` → omit the analogy. Flag in editorial notes.
- Analogy attempts repeatedly read as forced or strained → omit. Better no analogy than a weak one.

## What this stage does NOT do

- Does not generate per-section instructions (Stage 13).
- Does not refine prose for audio readability (Stage 12).
- Does not modify the underlying source meaning — analogies clarify, they do not replace.
