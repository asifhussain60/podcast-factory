# Stage 10 — Enrich With Relevant Context

**Purpose:** Add historical, intellectual, and tradition-specific context where the source's meaning would be opaque to a modern listener. Bounded strictly by the loaded tradition whitelist.

## Input

- `WORK_DIR/_segments/section-NN-<slug>.md` (each section file)
- `WORK_DIR/_metadata.yml`
- `traditions/<detected-tradition>.yml` (or none, if `source-tradition=none`)

## Output

- `WORK_DIR/_enriched/section-NN-<slug>-enriched.md` — each section with context bridges woven in.
- Updates to `WORK_DIR/_editorial-notes-draft.md` recording every enrichment with source attribution.

## Hard rules

1. **No invented citations.** Every quote, paraphrase, or factual claim attributed to an external source must be verifiable in `allowed_enrichment_sources` of the active tradition file. If you cannot verify, do not add the enrichment.
2. **No bracketed commentary.** Do not write `[Background]`, `[Historical Note]`, `[Context]`, `[Modern Example]`, `[Commentary]`, or similar. Enrichment must read as part of the section, not as study notes.
3. **No tradition violation.** If the active tradition file lists a source in `forbidden_enrichment_sources`, do not enrich from it even if you "know" the relevant material.
4. **Respect tone preferences.** Apply the `tone_preferences` from the tradition file to every enrichment.
5. **Sparingly.** Enrichment should be the minimum needed for the section to make sense to a modern listener. If the section is already clear, add nothing.

## When to enrich

Add a context bridge when:

- The section references a figure, place, event, or concept that a modern listener would not recognize.
- The section assumes background knowledge that was common to its original audience but is uncommon today.
- The section uses a technical term that is not defined in the section itself (the pronunciation guide gives meaning, but the listener needs intellectual context for the concept).
- The section's argument hinges on a premise that was self-evident to the original audience but needs articulation today.
- The section quotes scripture or a classic source without identifying it.

## When NOT to enrich

Do not add a bridge when:

- The source is already clear in context.
- The enrichment would only restate what the source says (no added value).
- The enrichment would impose a tradition or interpretation the source does not invite.
- The needed background is too long to integrate naturally — better to add a brief mention and let the editorial notes carry the detail.
- You cannot find a verifiable source for the enrichment in the active tradition's `allowed_enrichment_sources`.

## How to weave bridges

A context bridge is typically 1–3 sentences integrated into the surrounding prose. Examples (illustrative — generated bridges always come from the actual source, never from these examples):

**Before (source as-is):**
> "And as Imam Ja'far al-Sadiq taught, the Imamate is the heart of the religion."

**After (with bridge woven in):**
> "And as Imam Ja'far al-Sadiq taught — the sixth Imam in the line from Ali, and the figure from whom the Ithna'ashari and Ismaili lines later diverged — the Imamate is the heart of the religion."

The bridge identifies the figure for a listener who may not know who Imam Ja'far is, without breaking the surrounding rhythm.

## Bridge patterns

| Pattern | Example trigger | What the bridge does |
|---|---|---|
| Figure identification | A named figure unfamiliar to modern listeners | Adds a brief identifying phrase (era, role, lineage) |
| Place / event | A named place or event without context | One clause locating it in time and significance |
| Term definition | A technical term not defined in the section | Brief definition phrased as the source might phrase it |
| Premise articulation | An unstated assumption underlying an argument | One sentence making the premise visible |
| Scripture attribution | An unattributed quotation | The source of the quotation |

## Multiple-bridge sections

If a single section needs many bridges, consider whether you are over-enriching. Limit:
- No more than 1 bridge per ~200 words of source content.
- No more than 5 bridges per section.

If a section genuinely needs more, flag in editorial notes and let the user decide.

## Quote handling within enrichments

If a bridge includes a quote from a source in `allowed_enrichment_sources`:

- Quote is 1–2 sentences max.
- Use exact wording with attribution: "as Nasir-i Khusraw wrote, '[quote]'".
- If the quote is translated, note the translator in editorial notes.
- Translator should be a recognized translation (Daftary, Walker, Morris, etc. for Ismaili material; standard translations for other traditions).

## Updating editorial notes

For every enrichment added, append to `WORK_DIR/_editorial-notes-draft.md`:

```markdown
## Enrichment — Section [N], approximate line [N]

Type: [Figure identification | Place/event | Term definition | Premise articulation | Scripture attribution]
Source consulted: [Specific source from allowed_enrichment_sources]
Bridge text: "[the new prose added]"
Original source text around the bridge:
  Before: "[snippet]"
  After: "[snippet with bridge integrated]"
Verification: [Where this enrichment's claim was verified]
Translator: [If applicable]
```

These notes become part of `04-editorial-notes.md` at Stage 15.

## Failure modes

- Cannot find verifiable source for a needed enrichment → omit the enrichment. Flag in editorial notes as "Section [N] may benefit from background on [topic]; no verifiable source found in active tradition whitelist."
- All candidate enrichments would violate tradition `forbidden_enrichment_sources` → skip enrichment for that section entirely.

## What this stage does NOT do

- Does not add modern analogies (Stage 11).
- Does not refine the prose for audio (Stage 12).
- Does not generate the per-section instructions (Stage 13).
