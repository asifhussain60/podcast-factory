# Stage 12b — Library Cross-Pollination Proposals

**Purpose:** During refinement (and informed by enrichment and the detected terms from earlier stages), identify candidate additions to the three Tier 1 journal libraries: `quotes-library.txt`, `clinic-library.txt`, and `translations-glossary.md`. Write them to the staging file `06-library-proposals.md`. Never touch live library files at this stage.

This stage runs concurrently with Stage 12 (audio refinement). Both consume the enriched + analogized sections; refinement writes to `01-refined/`, this stage writes to `06-library-proposals.md`.

## Input

- `WORK_DIR/_analogized/section-NN-<slug>-analogized.md`
- `WORK_DIR/_lexicon/detected-terms.yml` (new terms from Stage 06–07)
- `JOURNAL_DIR/reference/quotes-library.txt` (read-only)
- `JOURNAL_DIR/reference/clinic-library.txt` (read-only)
- `JOURNAL_DIR/reference/translations-glossary.md` (read-only — already known from Stage 08)
- `traditions/<tradition>.yml` for quote attribution requirements

## Output

- `WORK_DIR/06-library-proposals.md` per the canonical format in `templates/library-proposal-entry.md`
- `WORK_DIR/06b-borderline.md` for candidates that didn't pass the quality bar

## Three-tier policy reminder

| Tier | Files | This stage's action |
|---|---|---|
| Tier 1 | `quotes-library.txt`, `clinic-library.txt`, `translations-glossary.md` | Propose additions in staging file |
| Tier 2 | `incident-bank.md`, `biographical-context.md`, `voice-fingerprint.md`, `craft-techniques.md`, `thematic-arc.md`, `master-context.md` | Read for context; never propose |
| Tier 3 | `locked-paragraphs.md`, `temporal-guardrail.md`, `memoir-rules-supplement.txt`, `chapter-status.md`, `journal-workflow-v2.md`, `quotes-workflow.md` | Never touched |

## Quote proposals (Section A of staging file)

### Detection

Scan each section for candidate quotes. A candidate is:
- Direct speech (in quotation marks) attributed to a named figure, OR
- A teaching ascribed to a named figure within the section text.

### Quality filters

Each candidate must pass all of these to be proposed:

1. **Explicit named attribution.** The figure is named in the section.
2. **Recognized figure.** The figure is in the active tradition's `figures` list. If tradition is `none`, the figure must be a verifiable historical, philosophical, scientific, or literary figure named in the source.
3. **Under 50 words.** Longer quotes get truncated to a meaningful 50-word fragment, marked as such in editorial notes.
4. **Non-aphoristic.** The quote must illuminate a specific point in the source, not be a generic truism that could fit anywhere.
5. **Not already covered.** No existing entry in `quotes-library.txt` matches at ≥ 85% Levenshtein similarity OR ≥ 0.85 semantic similarity (Haiku call).
6. **Theme match.** The quote relates to one of the memoir chapter themes (Babu / Faith / Discipline / Love / Marriage / Money / Man / future themes). Skill maintains a list of active memoir themes; reads `thematic-arc.md` for the list.

Candidates passing 1–6 → propose.
Candidates passing some but not all → borderline file with reason.
Candidates failing 1 or 2 → discard silently (not borderline material).

### Tradition-specific attribution requirements

Apply the active tradition's `quote_attribution_requirements`. For Ismaili tradition, this includes:
- Direct attribution to a named figure in the figures list.
- Source citation (work + section).
- Translator name if translated.
- Confirmation the quote appears in an `allowed_enrichment_source`.
- Quotes attributed to Prophet Muhammad must come from Da'a'im al-Islam or another tradition-accepted source.

If any requirement fails → discard.

### Entry format

Per `templates/library-proposal-entry.md`, "Quote entry format" section.

## Clinic proposals (Section B of staging file)

### Detection

Scan each section for psychological/clinical content. A candidate is:
- A description of a cognitive pattern (how someone thinks), OR
- A description of an emotional dynamic (how an emotion functions), OR
- A description of a behavioral mechanism (how a behavior persists or shifts), OR
- A developmental insight (how a person changes over time), OR
- A relational dynamic (how relationships work).

### Quality filters

1. **Surfaces a pattern, not just an event.** Pure narrative description ("he was sad and then he was happy") doesn't qualify. Pattern descriptions ("he realized that his sadness was anchored in unmet expectations rather than in present circumstances") do.
2. **Applicable to a memoir theme.** The pattern must connect to a chapter theme in `thematic-arc.md`.
3. **Has a "why this is psychologically useful" tag.** The skill writes a one-sentence explanation of the pattern's diagnostic or therapeutic value.
4. **Not already in clinic-library.txt.** ≥ 85% Levenshtein OR ≥ 0.85 semantic similarity blocks the proposal.

Candidates passing 1–4 → propose.
Candidates with strong pattern but weak theme match → borderline.
Pure narrative without pattern → discard.

### Entry format

Per `templates/library-proposal-entry.md`, "Clinic entry format" section.

## Glossary proposals (Section C of staging file)

### Detection

Every term in `_lexicon/detected-terms.yml` with `lexicon_status: new` AND `proposed_phonetic` filled becomes a proposal.

### Quality filters

1. **Phonetic generated.** Stage 07 must have produced a phonetic; terms with `NEEDS_REVIEW` go to borderline.
2. **Meaning generated.** Same.
3. **Not in master lexicon.** Cross-check `translations-glossary.md` Podcast Pronunciation Lexicon section. If present, skip — already covered.

### Entry format

Per `templates/library-proposal-entry.md`, "Glossary entry format" section.

## File construction

`WORK_DIR/06-library-proposals.md` follows the canonical format. Sections A, B, C in order. Proposals numbered Q-001, Q-002, etc. for quotes; C-001 for clinic; G-001 for glossary.

`WORK_DIR/06b-borderline.md` collects candidates that failed quality filters but might be promoted by the user. Each entry includes the reason it was borderline.

## Dedup mechanics — detailed

### Levenshtein fuzzy match

For each candidate text (quote or clinic excerpt):

1. Normalize: lowercase, strip punctuation, collapse whitespace.
2. For each existing entry in the target library, compute Levenshtein distance.
3. Score = 1 - (distance / max(len(a), len(b))).
4. If score ≥ 0.85 → duplicate. Discard.

### Semantic similarity (Haiku call)

For texts that pass Levenshtein but might be paraphrases:

1. Generate an embedding for the candidate (Haiku-call).
2. Compare against embeddings of existing entries.
3. If cosine similarity ≥ 0.85 → semantic duplicate. Discard.

Cache embeddings of existing entries in `WORK_DIR/_dedup-cache.json` so repeated runs are fast.

## Provenance footer

Every proposal carries:

```
Source: [Work title], Section [N], podcast skill [YYYY-MM-DD]
```

This footer is added to the entry when applied (Stage 16 / apply step). The proposal staging file shows the footer as "to be appended" so the user sees what will land in the library.

## Counts in console summary

The Stage 15 console summary references the proposal counts. This stage outputs three counts:
- Quotes proposed
- Clinic entries proposed
- Glossary terms proposed

Plus borderline counts:
- Quote candidates → borderline
- Clinic candidates → borderline

These appear in the summary banner.

## What this stage does NOT do

- Does not modify live library files. Only writes to staging.
- Does not apply proposals. That's the apply step (Stage 16).
- Does not run quality gates on the proposals themselves — that's part of Stage 14's broader check.
