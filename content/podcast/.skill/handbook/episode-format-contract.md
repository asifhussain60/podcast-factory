---
schema_version: 1
name: episode-format-contract
authored: 2026-05-20
authored_by: claude-opus-4.7 (draft for operator review — P23 W2)
status: DRAFT
applies_to: |
  All podcast episodes authored by the podcast skill / orchestrator when the
  per-series setting `audience_profile` is declared in `series-config.yaml`.
  Series WITHOUT `audience_profile` set retain pre-2026-05-20 behavior
  (full backward compatibility).
consumes:
  - content/_shared/traditions/<tradition-slug>.md   # OPTIONAL per-tradition supplement (schema in §3)
consumed_by:
  - scripts/podcast/_authoring.py                    # phases 0b, 0e, 11 prompts read this contract
  - infra/claude-agents/podcast-challenger/_rules.py # Challenger Category Q enforces this contract
  - content/podcast/.skill/handbook/two-host-framing.md  # cross-reference (voice / mode)
  - content/podcast/.skill/handbook/episode-architecture.md  # cross-reference (Pattern 5 recap)
related_protocols:
  - R-NOMODERNIZE          # anachronism-labeling discipline (P4.4) — re-asserted, not overridden
  - R-RESET                # episode-architecture.md reset-between-beats discipline
  - R-HONORIFIC-ONCE       # honorifics economy — generalized by §5 of this contract
  - Pattern 5              # recursive-scaffold opening-recap — extended by §3 of this contract
design_invariants:
  - tradition-agnostic     # the contract itself contains no tradition-specific content
  - audience-profile-gated # absent profile → contract inactive → zero regression
  - schema-validated       # frontmatter + per-tradition supplements are JSON-schema-checkable
  - additive-only          # no existing rule is removed or weakened; this is a layer above
---

# Episode Format Contract

A **tradition-agnostic, audience-aware** specification for podcast-episode
structure, citation form, reverence/honorifics, source-language preservation,
analogical framing, vagueness handling, modern-language refinement, and
closing discipline. This file is the **single source of truth** for episode
format; concrete particulars (revered figures, canonical-text citation
surface forms, source-language preservation hotspots) live in
**per-tradition supplement files** declared via `series-config.yaml`.

> **Backward compatibility (load-bearing).** Series whose `series-config.yaml`
> does NOT declare `audience_profile` retain pre-2026-05-20 behavior. Nothing
> in this contract activates without explicit per-series opt-in.
> Zero-regression is a hard invariant.

---

## 1. Conceptual model

```
                  ┌──────────────────────────────┐
                  │   series-config.yaml         │ ← per-series operator opt-in
                  │   - audience_profile         │
                  │   - source_tradition         │
                  │   - <optional overrides>     │
                  └────────────┬─────────────────┘
                               │ consumed by
                               ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │   episode-format-contract.md  (THIS FILE — generic schema)      │
   │   - 4 audience profiles                                          │
   │   - 8 generic rules (A–H)                                        │
   │   - per-tradition supplement schema (§3)                         │
   │   - Category Q challenger hooks                                  │
   └────────┬───────────────────────────────────┬────────────────────┘
            │ references                        │ enforced by
            ▼                                   ▼
   ┌──────────────────────────────┐  ┌──────────────────────────────┐
   │ content/_shared/traditions/  │  │ infra/claude-agents/         │
   │ <tradition-slug>.md          │  │ podcast-challenger/_rules.py │
   │ (concrete tradition data)    │  │ (Category Q sub-checks)      │
   └──────────────────────────────┘  └──────────────────────────────┘
```

The contract is layered:
- **Schema layer** (this file) — what every series must declare and how rules behave.
- **Tradition layer** (per-tradition supplement files) — concrete revered figures, citation forms, source-language hotspots for a specific source tradition.
- **Enforcement layer** (challenger Category Q + phase-prompt addenda) — runtime checking and authoring.

---

## 2. Audience profiles (the master switch)

Every series declares ONE profile in `series-config.yaml`:

```yaml
audience_profile: <profile-slug>   # one of: traditional | modern-secular | clinical-wellness | academic
```

| Profile | Best for | Honorifics density | Source-language preserved | Analogical framing | Voice register |
|---|---|---|---|---|---|
| `traditional` | Listeners anchored in the source tradition | First mention each episode | High (terms kept; target-language gloss in parens) | OFF (no modernizing analogies) | Reverent, classical |
| `modern-secular` | General curious lay audience; podcast-default | First mention first episode of series only | Low (target-language first; source-language only where indispensable) | OPTIONAL (light, always labeled) | Conversational |
| `clinical-wellness` | Self-development / wellness listeners; the contract's **primary innovation** | First mention of series only | Low | **ON** (medical / clinical / physiological / psychological — always labeled as analogy) | Accessible, contemporary |
| `academic` | Scholarly / academic-podcast audiences | None (names only) | High (source-language with target-language gloss) | Source-author analogies only (no modern reductions) | Formal, technical |

**Single profile per series.** Audience profile is series-wide, not episode-wide.

> **P24 ↔ P23 synergy.** `audience_profile` and `source_tradition` can be hand-declared by the operator before any content is read, OR proposed by the `podcast-blueprint` agent at slot `05.5-blueprint` (the new content-aware classifier that runs between the P22 transcript-review resume and `06-phonetics`). Blueprint's Layer 1 emits a `classification.json` with `recommended_audience_profile` and `recommended_source_tradition` derived from the refined English transcript; the operator confirms via `--approve-blueprint`, and the orchestrator merges the values into `series-config.yaml` — activating this contract for downstream phases. See [blueprint-protocol.md](./blueprint-protocol.md).

---

## 3. Source tradition + supplement-file schema

### 3.1 Declaration

```yaml
# series-config.yaml
source_tradition: <tradition-slug>   # references content/_shared/traditions/<tradition-slug>.md
```

`source_tradition` is OPTIONAL. When unset, the contract operates on the GENERIC defaults defined in this file (no tradition-specific honorifics, generic canonical-text citation as `<source>:<locator>`, no source-language preservation beyond the operator's per-book glossary).

### 3.2 Per-tradition supplement file schema

Each supplement file under `content/_shared/traditions/<tradition-slug>.md` MUST conform to the following schema:

```yaml
---
schema_version: 1
name: <tradition-slug>                    # matches filename
tradition_family: <family-slug>           # e.g., abrahamic | dharmic | east-asian | indigenous | secular
target_languages: [<lang-code>, ...]      # languages this tradition has historically used as source
honorifics_matrix:
  # Each entry: figure_slug → honorific surface form per audience_profile.
  # SCOPE: PERSONAL revered figures (founders, messengers, sages, teachers, saints).
  <figure-slug>:
    canonical_name: <how to refer to the figure>
    traditional: <full honorific form, e.g. "[Name] ([honorific phrase])">
    modern_secular: <name only or short form>
    clinical_wellness: <name only or short form>
    academic: <scholarly form>
    first_mention_scope: episode | series | book   # how often to use the FULL form
reverent_entities:
  # Each entry: entity_slug → reverent surface form per audience_profile.
  # SCOPE: NON-personal entities that the tradition treats with reverence —
  # canonical texts referenced by name, sacred objects, sacred places, sacred concepts.
  # Resolves handbook Q-CFG-7; mirrors honorifics_matrix structure for parity.
  <entity-slug>:
    canonical_name: <how to refer in target-language>
    entity_type: text | place | object | concept | event   # broad category for reporting
    traditional: <reverent form, e.g. "the Holy [X]" / "the Blessed [Y]">
    modern_secular: <plain form>
    clinical_wellness: <plain form>
    academic: <scholarly form>
    first_mention_scope: episode | series | book   # how often to use the FULL reverent form
canonical_text_citations:
  - text_slug: <slug>                     # e.g., "primary-scripture", "secondary-canon"
    formats:
      chapter-verse: <template>           # e.g., "in [Section X], [unit Y]"
      numeric: <template>                 # e.g., "[Slug] X:Y"
      named-section: <template>           # e.g., "in [Named Section], verse Y"
    default_format: <one of the keys above>
source_language_preservation_hotspots:
  - <reason-slug>                         # e.g., "esoteric-interpretation", "numerology", "liturgical-formulae"
    description: <when source-language must NOT be translated>
period_glossary_anchors: []               # optional: terms whose 13th-c. (or analogous) referent needs modern bridging
---

# <tradition-slug> — supplement notes

<free-form prose: editorial notes, anti-patterns, footguns for hosts/operators>
```

### 3.3 Supplement-file invariants

- **Tradition-agnostic contract — tradition-specific data.** This contract file references the supplement BY SLUG only; it never embeds tradition-specific terms.
- **Operator-authored.** Supplement files are HUMAN-AUTHORED. Trainer never adds or modifies them (same anti-overfit rule as challenger fixtures).
- **Versioned.** Schema bumps update `schema_version`; the contract supports the active schema and one previous version.
- **Discoverable.** A registry file at `content/_shared/traditions/_registry.md` lists known traditions and their status (DRAFT / SHIPPED / DEPRECATED).

---

## 4. Rule A — Chapter intro economy (cross-episode anti-repetition)

**Replaces**: nothing (extends Pattern 5 / Recursive Scaffold).

### 4.1 First episode of a chapter (or series)

A first episode does the full primer in Beat 1:

1. **Source context** — 1-2 sentences: author, period, what the source is.
2. **Chapter context** — 1-2 sentences: where this chapter sits in the source's arc; what the chapter is doing.
3. **Episode focus** — 1-2 sentences: which slice of the chapter THIS episode covers.

**Total budget: 30-60 seconds of audio (~120-200 words).**

### 4.2 Subsequent episodes (same source or chapter)

≤10 seconds reference, NEVER a full re-introduction. Use a stem like:

> *"Continuing from where we left off in [chapter X / last episode], today we turn to [Y]."*

**Forbidden in episodes 2+**:
- Re-stating the source's author, period, or thesis at length
- Re-explaining the chapter's place in the source
- Re-defining glossary terms covered in earlier episodes (rely on `concept-glossary.md` + the listener's accumulated context)

### 4.3 Edge cases

| Case | Treatment |
|---|---|
| First episode of a NEW chapter (mid-series) | Chapter primer ONLY (source primer was done in Ep1) — ~15-30 seconds |
| Listener may have skipped earlier episodes | Acceptable: a 5-second pointer (*"If you're joining mid-series, episode 1 sets the larger frame."*) — once per chapter, not per episode |
| Series uses Pattern 5 (Recursive Scaffold) | Pattern 5's mandatory 30-sec recap (per `episode-architecture.md`) STILL APPLIES and is in ADDITION to (not instead of) §4.2 above |

### 4.4 Enforcement

| Sub-check | Severity | Trigger |
|---|---|---|
| `Q-INTRO-ECONOMY` | P2 | Episode index > 1 AND Beat 1 word-count > 250 |
| `Q-NO-REINTRO` | P2 | Episode index > 1 AND Beat 1 contains source-thesis re-statement (text lifted from concept-glossary or earlier framing) |

---

## 5. Rule B — Canonical-text citation format

**Replaces**: nothing (new convention).

### 5.1 Per-series setting

```yaml
citation_format: chapter-verse   # one of: chapter-verse | numeric | named-section
```

The concrete surface form is supplied by the **per-tradition supplement file** (§3.2 `canonical_text_citations`). The contract enforces format CONSISTENCY; the supplement supplies the template.

| Setting | Schema-level description | Tradition supplies |
|---|---|---|
| `chapter-verse` | Verbal form using ordinal section + unit (reads cleanly aloud) | Template, e.g. *"in [Section X], [unit Y]"* |
| `numeric` | Compact numeric form for academic / aside use | Template, e.g. *"[Slug] X:Y"* |
| `named-section` | Section name + unit; assumes listener knows section names | Template, e.g. *"in [Named Section], [unit Y]"* |

### 5.2 Discipline

- **One format per series** — never mix within a series.
- **First mention each episode** — say the full form. **Subsequent mentions same episode** — short form is acceptable per supplement.
- **Pronunciation** — handled by `pronunciation.md` (per-book); this contract does not duplicate.

### 5.3 Absence semantics

If no `source_tradition` is declared, `citation_format` is treated as informational only — the framing author uses a sensible default for the source's apparent tradition with no Q-enforcement.

### 5.4 Enforcement

| Sub-check | Severity | Trigger |
|---|---|---|
| `Q-CITE-FORMAT` | P1 | A canonical-text citation in framing does NOT match the declared series format AS INSTANTIATED by the per-tradition supplement template |

Pre-existing `R-CITATION-AUTHENTICITY` (challenger) is unchanged; this rule adds **format** enforcement on top of authenticity.

---

## 6. Rule C — Reverence policy (figures + non-personal entities)

**Replaces**: informal "respect the source's tradition" guidance in `two-host-framing.md` — does NOT contradict, only specifies.

### 6.1 Generic policy

The contract knows TWO abstract reverence concepts:

1. **Revered figures** — personal figures the tradition treats with honor (founders, messengers, sages, teachers, saints). Supplied by the supplement's `honorifics_matrix` field.
2. **Reverent entities** — non-personal entities the tradition treats with reverence (canonical texts referenced by name, sacred objects, sacred places, sacred concepts, sacred events). Supplied by the supplement's `reverent_entities` field.

Each entry in EITHER field declares:
- `canonical_name` — the bare name used in target-language prose
- `traditional` / `modern_secular` / `clinical_wellness` / `academic` — the reverent surface form under that profile
- `first_mention_scope` — `episode`, `series`, or `book`: how often the FULL form should be used
- For entities only: `entity_type` — `text | place | object | concept | event` (for reporting and to disambiguate near-collisions)

### 6.2 Anti-repetition discipline (the "once" rule, generalized)

Reverence markers carry warmth on first hearing; they become noise on the fifth. The supplement's matrices (`honorifics_matrix` for figures, `reverent_entities` for non-personal entities) and their `first_mention_scope` fields are engineered so the listener hears the full reverent form **as often as the source's tradition calls for, and no more**.

This generalizes the existing `R-HONORIFIC-ONCE` rule: that rule's previous narrow meaning ("once per episode") becomes the `modern-secular` / `clinical-wellness` default; the new matrices replace the binary with a per-profile cap derived from the supplement, and extend the discipline to non-personal entities.

### 6.3 Voice mode interaction

If `series-config.voice_mode = curated_anthology` (per `two-host-framing.md`), honorifics default to `modern-secular` density unless `audience_profile` overrides.

### 6.4 Absence semantics

If no `source_tradition` is declared, the contract emits NO Category Q reverence findings. The framing author uses target-language names only (the `academic` setting's behavior). If the supplement declares ONLY `honorifics_matrix` and not `reverent_entities` (or vice-versa), only the declared half is enforced.

### 6.5 Enforcement

| Sub-check | Severity | Trigger |
|---|---|---|
| `Q-HONORIFIC-DENSITY` | P1 | Honorific count for a figure exceeds 1 occurrence per its `first_mention_scope` window (over-use) |
| `Q-HONORIFIC-MISSING` | P2 | `audience_profile: traditional` AND a known revered figure is referenced WITHOUT the full honorific form on first mention within the configured scope |
| `Q-ENTITY-DENSITY` | P1 | Reverent-entity surface form for an entity exceeds 1 occurrence per its `first_mention_scope` window (over-use) |
| `Q-ENTITY-MISSING` | P2 | `audience_profile: traditional` AND a known reverent entity is referenced by bare `canonical_name` WITHOUT the reverent form on first mention within the configured scope |

---

## 7. Rule D — Analogical framing for esoteric / period-distant concepts (CONDITIONAL — clinical-wellness only)

**Replaces**: nothing. **Activates ONLY under `audience_profile: clinical-wellness`.**

### 7.1 What this rule does

When the source describes an **esoteric or period-distant concept** (interpretive depth-meaning, archaic psychology, cosmological models, archetypal-figure typology, ritual theory, etc.), the framing offers a **labeled modern analogy** drawn from medical / clinical / physiological / psychological knowledge to help a contemporary listener get a foothold.

### 7.2 What this rule does NOT do

This rule does **NOT** reduce the source's claim to a modern science finding. It does **NOT** assert identity between the source's concept and the modern construct. It does **NOT** override `R-NOMODERNIZE` (P4.4) — it operates underneath it.

### 7.3 Required surface form (labeling discipline)

| Acceptable pattern | Forbidden pattern |
|---|---|
| "This **resembles** what modern psychology calls X" | "This **is** modern psychology's X" |
| "**A way to understand this through** contemporary medicine: X" | "X is what the source actually means" |
| "**An analogy that may help**: in clinical terms, X" | "The source is describing X" |
| "**Without collapsing** the source's claim into modern terms, **a foothold**: X" | (any unmodified equation of source ↔ modern construct) |

### 7.4 Source domains (analogical material)

- **Medical / clinical** — diagnostic frames; pathological vs healthy states
- **Physiological** — nervous-system, endocrine, circadian-rhythm, sensorimotor framings
- **Psychological** — attachment theory, dual-process cognition, internal-family-systems, polyvagal theory, acceptance-and-commitment-therapy, cognitive-behavioral-therapy framings
- **Cognitive science** — schema theory, embodied cognition, conceptual-metaphor theory

These are CATEGORIES, not a mandatory checklist. Per beat, at most one major analogy.

### 7.5 Constraints

- **At most one major analogy per beat.** Listeners drown in mixed metaphors.
- **Cite the modern construct by its accepted name** so the listener can search later — never *"some scientists say"*.
- **Avoid pop-psychology.** Use peer-reviewed constructs; flag if the construct is contested.
- **Never invent.** If no reasonable modern analogy exists for the concept, skip — say so explicitly: *"There isn't a clean modern analogy here — we'll have to sit with the source's own language."*

### 7.6 Enforcement

| Sub-check | Severity | Trigger |
|---|---|---|
| `Q-ANALOGY-LABELED` | P1 | An analogy lacking a labeling phrase from §7.3 acceptable patterns |
| `Q-NO-IDENTITY-CLAIM` | **P0** (blocks ship) | An analogy whose surface form asserts identity (regex against forbidden patterns) |

`R-NOMODERNIZE` ALSO fires on identity claims; the two are complementary.

---

## 8. Rule E — Source-language preservation policy

**Replaces**: nothing (formalizes informal practice).

### 8.1 Default behavior (all profiles)

Source-language terms appearing in the source text are **translated to the target language on first mention** within an episode:

> *"The [source-language] term `<term>` — [target-language gloss] — …"*

Subsequent mentions in the same episode use the **target language**, unless an exception (§8.2) applies.

### 8.2 Preserve source-language (mandatory) when

The per-tradition supplement file's `source_language_preservation_hotspots` field declares the abstract REASONS for which source-language preservation is required. The contract recognizes these generic reason-slugs:

| Reason slug | Generic description |
|---|---|
| `esoteric-interpretation` | The interpretive meaning depends on source-language letters, root, or sound |
| `numerology` | Numeric-symbolic claims depend on source-language letter values or counts |
| `liturgical-formulae` | The phrase is a direct quote of liturgical / scriptural text |
| `concept-glossary-anchor` | First mention of a glossary-anchored term (per the book's `concept-glossary.md`) |
| `untranslatable` | The term has no adequate target-language equivalent |

The supplement file SPECIFIES which of these reason-slugs apply to its tradition and provides example surface forms.

### 8.3 Audience-profile interaction

- `traditional` / `academic` — preserve source-language more liberally (additional hotspots permitted per supplement).
- `modern-secular` / `clinical-wellness` — strict §8.2 enforcement.

### 8.4 Absence semantics

If no `source_tradition` is declared, only `concept-glossary-anchor` enforcement applies (the per-book glossary is always available regardless of tradition).

### 8.5 Enforcement

| Sub-check | Severity | Trigger |
|---|---|---|
| `Q-SOURCELANG-PRESERVE` | P1 | A source-language term in framing that does NOT match a §8.2 reason and has no target-language gloss within 50 characters |

Pre-existing `R-PHONETICS-OUT` (assembly-time phonetic substitution) is unchanged — it operates on rendered output AFTER framing authoring.

---

## 9. Rule F — Vagueness flag + period-bridge enrichment (CONDITIONAL)

**Replaces**: nothing. **Activates under `audience_profile: clinical-wellness` or `modern-secular`.**

### 9.1 What this rule does

Phase 0e (enrichment) runs an additional pass: for each chapter, the prompt scans for **vague passages** — sentences whose period-of-origin context is opaque to a modern listener, or whose referent is so culturally distant that a modern reader cannot infer the author's intent.

For each vague passage, the enrichment writes a `vagueness-note` entry to `concept-glossary.md`:

```markdown
## Vagueness notes

### page-<N>-line-<M>
- **Source surface form**: "<the vague phrase, verbatim>"
- **Why vague to modern listener**: <one-line explanation of the period-bound referent>
- **Modern context (labeled)**: "<labeled analogy or contextual gloss>"
- **Decision**: include in framing IF this passage is invoked in any episode
```

### 9.2 What this rule does NOT do

This rule does **NOT** edit the source. It does **NOT** override the author's claim. It only **annotates** for the framing-authoring phase (11-per-chapter) to use.

### 9.3 Constraints

- **Conservative threshold.** Vagueness-notes are added only when ALL three conditions fire:
  1. The passage uses a culturally-specific referent absent from the concept-glossary.
  2. A modern listener cannot infer the referent from surrounding text.
  3. The framing in phase 11 is likely to invoke this passage.
- **Maximum cap** — 8 vagueness-notes per chapter to prevent over-annotation.
- **Operator override.** Operator can edit or delete any vagueness-note at the P22 review gate.

### 9.4 Period-bridge data source

The per-tradition supplement's `period_glossary_anchors` field MAY pre-seed common vagueness-triggers for that tradition (cosmology models, ritual practices, social institutions). When the supplement is absent, the LLM operates without seeding and the cap drops to 4 per chapter (more conservative).

### 9.5 Enforcement

| Sub-check | Severity | Trigger |
|---|---|---|
| `Q-VAGUENESS-LABEL` | P2 | A framing that uses modernizing language (regex: *"in modern terms"*, *"today we'd call this"*, etc.) on a passage that has NO vagueness-note in concept-glossary |

This is a yellow-flag check — encourages discipline, does not block ship.

---

## 10. Rule G — Modern (non-literal) target-language refinement

**Replaces**: nothing (formalizes Phase 0b's implicit behavior).

### 10.1 What Phase 0b does (made explicit)

Phase 0b's refinement prompt is augmented (via P19 phase-prompt addendum) with:

> **MODERN-TARGET-LANGUAGE DISCIPLINE.** Refine into **contemporary, fluent target-language prose**. The reader is a modern speaker, not a 19th-century scholar. Specifically:
>
> **Required**:
> - Contemporary syntax — short, clear sentences
> - Meaning preserved, idioms naturalized
> - Period-appropriate WHERE the source is period-bound (preserve historicity of voice without imitating archaic syntax)
>
> **Forbidden**:
> - Word-for-word literalism
> - Archaized target-language ("thou", "thee", "verily", "lo", or analogous in other target languages)
> - Archaic syntax ("It is upon the seeker that he should…")
> - Literal-translation tells ("the said house", "with respect to", "as for the matter of")
>
> If the source's literal surface form would be unclear in modern target-language, prefer **the source's intent in modern target-language**, not the surface.

### 10.2 Audience-profile interaction

| Profile | Register |
|---|---|
| `traditional` | Formal modern target-language (no contractions; full sentences) but still modern |
| `modern-secular` / `clinical-wellness` | Conversational modern target-language (contractions OK) |
| `academic` | Formal modern target-language with technical precision |

### 10.3 Enforcement

- Phase 0b regression fixtures (per P19.2) gain 3 new fixtures: `archaic-literal` (fails loud), `archaized-target-language` (fails loud), `modern-fluent-golden` (passes).
- Challenger does NOT enforce this at the framing layer — by the time framing runs, 0b has already produced refined-english.md (or its target-language analogue). Enforcement is at the **0b output** level.

---

## 11. Rule H — Three-part closing

**Replaces**: open-ended closing patterns in `episode-architecture.md` — **extends** them, does not contradict.

### 11.1 Required structure (final 60-120 seconds of every episode)

Every episode ends with **all three parts, in this order**:

#### Part 1 — Key learnings (20-40 seconds)

3 to 5 concise points the listener should walk away with. Extracted from the episode's beats, not editorialized. Spoken by the Driver host in a clean, listing voice.

> *"Three things to carry from this conversation: first, … Second, … Third, …"*

#### Part 2 — What's coming next (10-20 seconds)

1-2 sentences naming the next episode's focus. NOT a teaser cliffhanger; an informative pointer.

> *"In our next conversation, we turn to [chapter X / theme Y] — where the question becomes [Z]."*

If this is the FINAL episode of a series, replace with a closing arc statement:

> *"This brings our series to a close. What we've explored together: [one-sentence series arc]."*

#### Part 3 — Practical-life thought-provoking question (15-30 seconds)

A question the listener can take into their week. Anchored to **practical life** (relationships, work, daily practice, ethical choices), NOT to abstract metaphysics.

| Acceptable (practical-life) | Forbidden (abstract-metaphysical) |
|---|---|
| Anchored to a daily-life decision or habit | Anchored to abstract being / reality |
| Asks the listener about an action or noticing | Asks the listener about an ontological category |
| Specific enough to act on this week | So general the listener cannot act |

The forbidden patterns are detected by regex against phrases like *"the nature of"*, *"the essence of"*, *"reality itself"*, *"being itself"*, *"the All"*, *"the One"*. (Pattern list is operator-extensible.)

The question is **for the listener**, not for the hosts. It is not answered on air.

### 11.2 Audience-profile interaction

| Profile | Question style |
|---|---|
| `traditional` | Question rooted in faith-practice or scriptural reflection |
| `modern-secular` | Question rooted in lived experience / ethical practice |
| `clinical-wellness` | Question rooted in self-awareness / behavioral practice |
| `academic` | Question rooted in scholarly application / further inquiry |

### 11.3 Enforcement

| Sub-check | Severity | Trigger |
|---|---|---|
| `Q-CLOSING-3PART` | P1 | Closing beat missing any of {key-learnings, what's-next, practical-question} |
| `Q-PRACTICAL-QUESTION` | P2 | Closing question matches a forbidden abstract-metaphysical pattern |

---

## 12. Per-series configuration schema

```yaml
# content/podcast/library/books/<slug>/_system/series-config.yaml

# REQUIRED to activate the contract
audience_profile: clinical-wellness        # or: traditional | modern-secular | academic

# OPTIONAL — referenced from this contract's §3
source_tradition: <tradition-slug>         # references content/_shared/traditions/<tradition-slug>.md

# OPTIONAL per-series overrides
citation_format: chapter-verse             # or: numeric | named-section
honorifics_density: profile-default        # or: explicit override of §6 matrix
source_language_preservation: profile-default   # or: aggressive | minimal
analogical_framing:                        # only applies when audience_profile = clinical-wellness
  enabled: true
  domains: [medical, clinical, physiological, psychological, cognitive]
vagueness_enrichment:                      # only applies when audience_profile in [clinical-wellness, modern-secular]
  enabled: true
  max_notes_per_chapter: 8
closing_structure:
  enabled: true                            # set false ONLY to migrate an existing series with operator opt-out
  practical_question_required: true
```

### 12.1 Absence semantics

- **`audience_profile` missing** → contract INACTIVE for this series. Pre-2026-05-20 behavior holds. **No regression.**
- **`source_tradition` missing** → contract operates on generic defaults; Category Q sub-checks that depend on tradition data (Q-HONORIFIC-DENSITY, Q-HONORIFIC-MISSING, Q-CITE-FORMAT) become advisory (informational findings, not P1/P2).
- **Optional fields missing** → profile defaults apply per §2 matrix.

### 12.2 Validation

A new validator `scripts/podcast/_format_contract.py` parses `series-config.yaml`, validates against this contract's frontmatter schema, and is invoked at:
- Phase 0f operator gate (warns if a book has `audience_profile` declared but `source_tradition` references a non-existent supplement file).
- Per-episode build (`build_episode_txt.py`) — confirms profile is consistent across all episodes in the series.
- Challenger pre-flight — refuses to lint a framing whose series-config conflicts with the framing surface.

---

## 13. Challenger Category Q — enforcement summary

| Sub-check | Severity | What it catches | Activates under |
|---|---|---|---|
| `Q-INTRO-ECONOMY` | P2 | Beat 1 of episode > 1 over 250 words | any profile |
| `Q-NO-REINTRO` | P2 | Beat 1 of episode > 1 contains source-thesis re-statement | any profile |
| `Q-CITE-FORMAT` | P1 | Citation surface form mismatches series setting × supplement template | requires `source_tradition` |
| `Q-HONORIFIC-DENSITY` | P1 | Honorific count for a figure exceeds per-`first_mention_scope` cap | requires `source_tradition` + `honorifics_matrix` |
| `Q-HONORIFIC-MISSING` | P2 | `traditional` profile + revered figure mentioned without honorific | requires `source_tradition` + traditional profile |
| `Q-ENTITY-DENSITY` | P1 | Reverent-entity surface form for an entity exceeds per-`first_mention_scope` cap | requires `source_tradition` + `reverent_entities` |
| `Q-ENTITY-MISSING` | P2 | `traditional` profile + reverent entity referenced bare without reverent form on first mention | requires `source_tradition` + `reverent_entities` + traditional profile |
| `Q-ANALOGY-LABELED` | P1 | Analogy lacks labeling phrase | clinical-wellness only |
| `Q-NO-IDENTITY-CLAIM` | **P0** (blocks ship) | Analogy asserts source ↔ modern construct identity | clinical-wellness only |
| `Q-SOURCELANG-PRESERVE` | P1 | Source-language term with no target-language gloss within 50 chars | any profile |
| `Q-VAGUENESS-LABEL` | P2 | Framing uses modernizing language on un-flagged passage | clinical-wellness OR modern-secular |
| `Q-CLOSING-3PART` | P1 | Closing beat missing key-learnings, what's-next, or practical-question | any profile |
| `Q-PRACTICAL-QUESTION` | P2 | Closing question matches abstract-metaphysical pattern | any profile |

All Q sub-checks are **fixture-gated** per the existing challenger discipline (`infra/claude-agents/podcast-challenger/_rules.py`). Fixtures live under `_learning/fixtures/format_contract/<sub-check-slug>/`. Operator authors fixtures; trainer never adds or modifies fixtures (anti-Goodhart invariant).

---

## 14. Phase-prompt integration

Each affected phase reads the relevant slice of this contract via `_authoring.py`:

| Phase | Reads contract sections | Effect on prompt |
|---|---|---|
| 0b (refine-english) | §10 only | Modern-target-language discipline addendum appended to refinement prompt |
| 0e (enrichment) | §8, §9 | Source-language preservation cue + vagueness-flag scanner added to enrichment prompt |
| 11 (per-chapter framing) | §4, §5, §6, §7, §8, §11 | Full contract injected as `<format-contract>` XML block in framing prompt; per-tradition supplement injected as `<tradition-supplement>` XML block if declared |
| 12 (trainer) | §13 (Category Q) | Trainer reads Q-findings as learning signal but never modifies the contract or any supplement |

This follows the existing pattern from `numeric-symbolic-disambiguation.md` (P4) — handbook file is the source of truth; phase prompts cite it; challenger enforces it.

---

## 15. Migration notes (zero-regression discipline)

### 15.1 Existing series

- Any series whose `series-config.yaml` does NOT declare `audience_profile`: contract INACTIVE → behavior unchanged.
- Already-shipped series can opt in via a NEW pipeline run; the contract is per-run, not in-place.

### 15.2 New-series adoption path

1. Operator drafts `series-config.yaml` for a new series with `audience_profile` set.
2. Operator optionally declares `source_tradition` and ensures the supplement file exists at `content/_shared/traditions/<tradition-slug>.md`.
3. Run phases 0b / 0e / 11 with contract active.
4. Challenger Category Q runs; findings raised; operator reviews.
5. Ship.

### 15.3 Authoring a new per-tradition supplement file

1. Copy the schema in §3.2 into `content/_shared/traditions/<new-tradition-slug>.md`.
2. Populate honorifics matrix, citation templates, source-language preservation hotspots, and period-glossary anchors.
3. Register the file in `content/_shared/traditions/_registry.md` with status `DRAFT`.
4. Author ≥3 fixtures per Category Q sub-check that depends on `source_tradition`.
5. Run the contract validator (`scripts/podcast/_format_contract.py --tradition <slug>`).
6. Promote `_registry.md` status to `SHIPPED` after validator + fixtures pass.

---

## 16. Open questions (to resolve before P23 promotes from DRAFT → SHIPPED)

| ID | Question | Default if unresolved |
|---|---|---|
| Q-CFG-1 | Should `audience_profile` be settable per-EPISODE for hybrid series? | NO — per-series only; hybrid series should be split |
| Q-CFG-2 | Should `clinical-wellness` analogies be sourceable from a curated handbook file (e.g., `content/_shared/wellness/analogies.md`)? | YES, in a follow-up patch — initial P23 uses the LLM's general knowledge with `R-NOMODERNIZE` discipline as the guard |
| Q-CFG-3 | Should Category Q findings be promotable to P0 over time (after fixtures harden)? | Yes for `Q-NO-IDENTITY-CLAIM` (already P0); others stay P1/P2 until corpus signal accumulates |
| Q-CFG-4 | Should the closing practical-question be authored by a separate LLM call (single-purpose) for higher quality? | NO initially — inline in 11-per-chapter; revisit if quality is poor |
| Q-CFG-5 | Should multiple `source_tradition` files be supported per series (multi-tradition source material)? | NO initially — single tradition per series; multi-tradition can be modeled as a new composite supplement file |
| Q-CFG-6 | Should target-language be configurable (currently implicitly English)? | DEFERRED — declare via `target_language` in series-config; default English; full enforcement requires localized fixtures (future P-slot) |
| ~~Q-CFG-7~~ | ~~Should reverent treatment extend to NON-figure entities?~~ | **RESOLVED 2026-05-20**: `reverent_entities` field added to supplement schema (§3.2); Rule C (§6) extended to cover both figures + entities; Category Q sub-checks `Q-ENTITY-DENSITY` (P1) and `Q-ENTITY-MISSING` (P2) added to §13. |

---

## 17. Cross-references

- `episode-architecture.md` — beat structure, Pattern 5 recap (§4 of THIS file extends Pattern 5)
- `two-host-framing.md` — voice modes, host roles, the "respect the tradition" line (§6 of THIS file specifies it)
- `numeric-symbolic-disambiguation.md` — P4 numeric/symbolic discipline; R-NOMODERNIZE
- `pronunciation.md` — pronunciation surface forms (per-book)
- `_workspace/plan/podcast-plan.yaml` P23 — the implementation task for this contract
- `infra/claude-agents/podcast-challenger/_rules.py` — Challenger Category Q implementation site
- `content/_shared/traditions/_registry.md` — known tradition supplements registry
- `scripts/podcast/_format_contract.py` — contract + supplement validator (NEW per P23)
