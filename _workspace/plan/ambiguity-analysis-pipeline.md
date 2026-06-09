# Ambiguity Analysis Pipeline — Phase 0e.5

**Status:** Approved (option B) — implement before Vol 2, manual pass for Vol 1  
**Approved:** 2026-06-09  
**Scope:** New pipeline step inserted between enrichment (phase 0e) and per-chapter framing authorship

---

## What this solves

The per-chapter framing authorship step currently authors host guidance cold — it has no structured view of gaps, tensions, or undefined references in the source chapter. This leads to:

- Pedagogical gaps that only surface in a post-hoc spot check (e.g. "Father of Imams" never mapped to Ali ibn Abi Talib)
- Doctrinal tensions that the framing doesn't steer hosts toward (e.g. Adam excluded from "foremost in resolve" yet treated as first Speaker-Prophet)
- Missing scaffolding for concepts introduced but not unpacked (e.g. Eve as the Silent One / Proof)
- Unexplained structural absences (e.g. Vol 1 has no chapter on the seventh Speaker-Prophet — not flagged for hosts)

**What this does NOT do:** autonomously fill chapter text with inferred doctrine. Chapters are source-faithful revoicings; the framing files are where host context belongs.

---

## Design boundary (critical)

| Action | Allowed | Reason |
|---|---|---|
| Flag gaps in chapters for framing context | ✅ | Framing is host guidance, not source transcription |
| Search within-corpus source material for answers | ✅ | Same author, same work — faithful citation |
| Add explanatory content to chapter .txt files | ❌ | Faithfulness violation — R-FAITHFULNESS rule |
| Pull from general Islamic scholarship databases | ❌ | Non-canonical sourcing risk for doctrinal text |
| Infer what the author "should have said" | ❌ | Doctrinal invention |

---

## Implementation steps

### 1. New script — `scripts/podcast/analyze_chapter_ambiguities.py`

Reads an enriched chapter file. Runs a structured LLM prompt identifying:

- **(a) Conceptual tensions** — claims in the chapter that contradict or sit in tension with other claims in the same chapter or other chapters in the volume
- **(b) Undefined references** — figures, texts, or concepts named without a gloss (e.g. "the Father of Imams," "the sixth Imam," "the Peak of Eloquence")
- **(c) Scaffolding gaps** — doctrines introduced but not explained for a listener without prior background
- **(d) Structural absences** — content the chapter implies but deliberately omits (e.g. the Qa'im chapter)

Output: structured `ambiguity-report.md` written to `_system/episode-drafts/EP##-<slug>/` alongside the framing file.

Schema (per ambiguity item):
```
type: tension | undefined_reference | scaffolding_gap | structural_absence
location: line or section reference in chapter
description: plain English statement of the gap
resolution_found: null | "<citation from source material>"
resolution_source: null | "<file path or chapter reference>"
surfaced_to_framing: true | false
```

### 2. Within-corpus cross-reference search

For each flagged item, the script searches:

- Other chapter files in the same volume (`chapters/ch0N-*.txt`)
- Other volume directories in the work container (`../vol-02/chapters/`, etc. — if present)
- Texts cited by name in the chapter (e.g. "The Peak of Eloquence," "The Pillars of Islam") — searched against `content/_shared/source-library/` if available

If a resolution is found, it is attached as a citation. If not, the item is marked `resolution_found: null` and goes into the Asif-review section.

### 3. Framing authorship integration

Update the per-chapter framing authorship prompt (in `_authoring.py` or the chapter driver) to receive the ambiguity report as an additional input section labeled `## Host Context Notes`.

The authorship LLM is instructed to:
- Use undefined-reference resolutions to write "name discipline" entries (e.g. "the Father of Imams → Ali ibn Abi Talib — say 'Ali' once at first mention")
- Use scaffolding gaps to write friction beats (Host B's challenge questions)
- Use structural absences to write closing orientation lines ("this volume deliberately omits the seventh cycle — that is the subject of Vol 6")

### 4. Unresolvable gap surface — `ambiguity-report.md` review section

The bottom section of each episode's `ambiguity-report.md` lists items with no resolution found:

```
## For your review

### [tension] Adam excluded from "foremost in resolve" but treated as first Speaker-Prophet
Location: ch02 paragraph 3, ch03 paragraph 1
Gap: The Quran verse (20:115) excludes Adam from firm determination, yet he initiates 
     the speaker-prophet cycle. The text does not reconcile this in one place.
Action options:
  A. Add a one-sentence framing note: "Adam is the initiating Speaker but his 
     specific failing distinguishes him from the five who bore their tests fully."
  B. Flag as an intentional open question for the hosts to raise.
  C. Leave — the tension is theologically productive and does not confuse the hosts.
```

Asif reviews these before NotebookLM upload and annotates with A/B/C. Pipeline reads the annotation on the next run.

---

## Orchestrator wiring

Insert as phase `0e.5` between `0e` (enrichment) and the per-chapter loop:

```
phases: 0a → 0b → 0c → 0d → 0e → 0e.5 (ambiguity analysis) → 0f → per-chapter
```

Phase 0e.5 runs once per chapter (same as enrichment) and writes its report before the chapter driver starts authoring the framing.

---

## Vol 1 manual pass (before NotebookLM upload)

The spot check on 2026-06-09 surfaced 7 ambiguities. These need to be woven into each episode's framing before upload:

| Priority | Item | Target framing |
|---|---|---|
| 🔴 High | Father of Imams / sixth Imam — never mapped to personal names | All 5 episodes — name discipline section |
| 🔴 High | Qa'im chapter deliberately absent — not explained to listeners | EP01 (intro chapter) — closing orientation |
| 🟡 Medium | Adam excluded from "foremost in resolve" tension | EP04 (Adam chapter) — friction beat |
| 🟡 Medium | Eve as Silent One / Proof — needs one more unpacking pass | EP04 — host context note |
| 🟡 Medium | Ten-limit cosmology appears only at Ch05 end — no buildup | EP05 — host context note |
| 🟢 Low | Alexandrian-to-Ismaili genealogy — not revisited after Ch01 | EP01 — closing note |
| 🟢 Low | Enoch's 365-year lifespan — inner-meaning opportunity unexplored | EP05 — optional friction beat |

---

## Files to create / modify

| File | Action |
|---|---|
| `scripts/podcast/analyze_chapter_ambiguities.py` | Create — new analysis script |
| `scripts/podcast/orchestrate_book.py` | Modify — add phase 0e.5 to phase sequence |
| `scripts/podcast/_authoring.py` | Modify — framing authorship prompt consumes ambiguity report |
| `skills-staging/podcast/SKILL.md` | Modify — document new phase |
| `framework.md` | Modify — add phase 0e.5 to pipeline diagram |

---

## Success criteria

- Each chapter's framing file contains a `## Host Context Notes` section populated from the ambiguity report before per-chapter convergence runs
- Unresolvable gaps generate a reviewable `ambiguity-report.md` section that Asif can annotate
- No chapter text is altered by this step
- Challenger P1 count on "undefined reference" and "name discipline" findings drops measurably on Vol 2 vs Vol 1

---

## Astro Site addition — "Additional Context" on Framing Fixes cards

**Status:** Planned (not yet implemented). Start next session.

### What it does

Each ambiguity card on the `/pre-upload/[slug]` Framing Fixes tab gains an
**Additional Context** textarea beneath the existing "Text to insert into
framing" area. Asif types his own clarification about the ambiguity — domain
knowledge, interpretation, or doctrinal correction not derivable from the source
alone.

That context has two downstream effects:

1. **Framing fix** — the additional context is appended to the framing note
   that gets applied to the episode's `00-framing.md` (via the existing
   `apply-fix` API action, extended to include the context paragraph under a
   `### Host context (from review)` subsection).

2. **Source fix** — when context resolves something that is also wrong or
   incomplete in the chapter source file, Asif can tick a checkbox
   "Also apply to chapter source" and provide a corrected sentence or
   replacement. The API runs that correction through the same
   `apply-deletions-to-source` / `apply-source-replacements` logic.

### Data model change

`ambiguity-items.json` gains two new optional fields per item:

```json
{
  "id": "enoch-365-years",
  ...
  "asif_context": "",
  "source_fix": ""
}
```

The UI saves these on every Apply click via the existing
`mark-fix-status` action (extended to also persist `asif_context` +
`source_fix`).

### UI changes (plan-dashboard/)

| Component | Change |
|---|---|
| `AmbiguityCard` in `PreUploadTabs.tsx` | Add `asifContext` + `sourceFix` state; render two new textareas with their own labels beneath the existing fix textarea; add "Also apply to source" checkbox |
| `pre-upload.css` | Add `.pu-amb-context-wrap` and `.pu-amb-source-fix-wrap` sections (same card-body pattern, no inline styles) |
| `/api/pre-upload.ts` — `apply-fix` | Pass `asif_context` through to the framing write; append as `### Host context (from review)` block |
| `/api/pre-upload.ts` — `mark-fix-status` | Also persist `asif_context` + `source_fix` into `ambiguity-items.json` |
| `/api/pre-upload.ts` — new `apply-context-to-source` | If `source_fix` non-empty, run the sentence-level replacement; same logic as `apply-deletions-to-source` |

### Gate

Gate through `html-view-challenger` before marking complete, same as all
pre-upload UI work. Zero inline styles; all tokens from `--c-*` palette.

---

## Next session — resume here first

**Session start task: COMPLETE (2026-06-09)**

Asif provided the Ismaili cosmological context for Enoch/Idris and the 365-year lifespan:
- 365 = the 365 degrees of the solar cycle (shams); each year of earthly life mirrors one day in the Sun's celestial revolution.
- Macrocosm/microcosm (alam / insan) correspondence — physical numbers are outer forms of inner spiritual completeness.
- Saturn sphere / 30-year detail confirmed as legitimate broader Islamic cosmological tradition (NOT al-Nu'man); introduced with that attribution guard.
- Allah elevates prophets on the basis of cosmic and spiritual purity.

Host context block written to EP05 framing file at:
`content/Islamic/asaas-al-taveel/vol-01/_system/episode-drafts/EP05-two-parties-and-the-line-to-noah/00-framing.md`

No source fix needed — the chapter source text does not need generalizing; the detail belongs in the framing only.
