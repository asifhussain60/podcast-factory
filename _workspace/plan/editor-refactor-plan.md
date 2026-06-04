# Editor refactor plan — studio-poc batch

Status: INVESTIGATION PHASE — do not implement until Asif signs off.
Target: implement in a single batch after holistic review.
Landing zone: studio-poc → promote to /studio after approval.

---

## F1 — Strip pipeline-metadata artifact paragraphs from stage files

**Request:** The italic provenance paragraph in the narrator stage header should be removed.
It appears in the rendered editor and is not content.

**Investigation findings:**
- Pattern Type B (italic provenance para) appears in 4 of 6 stage types × all 5 chapters:
  - source/core: `_Extracted span: lines XXXX–XXXX of the OCR'd English edition..._`
  - augmented: `_Re-voiced from the Denoised stage into the global house style..._`
  - narrator: `_Cleaned from lecture transcript(s): lec01-..., ... This is the explainer's commentary..._`
- H1 heading lines (`# Normalized — ch01-...`) are NOT artifacts — they are stage labels and stay.
- Denoise does NOT cover narrator (runs core→denoised only). This is a generation problem,
  not a denoise failure.

**Pipeline homes (two, both required):**

  A. ROOT FIX — narrator_additions.py: do not write the italic metadata paragraph into the
     content file. Extract it to a sidecar `_system/narrator-meta.json`
     `{chapter, lectures_used, note}`. Same pattern for source.md, core.md, augmented.md —
     their italic provenance lines should move to `_system/stage-meta.json`.
     This prevents regeneration on the next run.

  B. UI — on stage load in StudioPoc.tsx: scan the first 3 paragraphs of every stage for the
     artifact regex patterns below. Auto-apply the 🗑️ "delete" tag to any match so they show
     highlighted in the editor. The user can confirm or untag. Patterns:
       - /^_Cleaned from lecture transcript\(s\):/i  (narrator)
       - /^_Extracted span: lines \d+/i              (source, core)
       - /^_Re-voiced from the/i                     (augmented)

**Implementation scope:**
  - scripts/podcast/narrator_additions.py: strip provenance comment from output, write sidecar
  - scripts/podcast/intake_stage.py: same pattern for source/core provenance lines
  - plan-dashboard/src/components/reader/poc/StudioPoc.tsx: ARTIFACT_PATTERNS array → scan
    first 3 paragraphs on stage load → pre-apply delete tag

**Confidence:** HIGH. Root cause clear. Regex patterns are deterministic. No ambiguity.


---

## F2 — H1 stage headings: suppress in editor, don't delete from files

**Request:** Are H1 stage headings needed by the pipeline? What's the impact of removing them?

**Investigation findings:**
- gemini_refine.py reads full stage file (incl. H1) → sends to Gemini → Gemini strips it as
  apparatus → script writes a FRESH generated H1 to the output. No script parses the H1 text.
- assemble_bundle.py + challenger read from `chapters/` not `_stages/`. The H1 never reaches
  the podcast output.
- Only consumers: Studio editor, stage_runner.py (existence check only), _stage_gate.py
  (existence check only).

**Pipeline impact of removing H1:** ZERO. No script breaks.

**Recommendation (two-part, kept separate):**

  A. EDITOR (this batch): suppress the first H1 in TipTap content area via CSS
     `.studio-poc__editor .ProseMirror > h1:first-child { display: none; }`
     Zero-risk, instantly reversible. Stage tabs already provide the context.

  B. PIPELINE (future quiet cleanup): stop writing the H1 title line into stage output files
     in gemini_refine.py, narrator_additions.py, and intake_stage.py. Move stage label to
     a `_system/stage-labels.json` sidecar if human orientation is still wanted.
     This batch does NOT include B — it's a follow-on.

**Confidence:** HIGH. Traced every reader. No ambiguity.


---

## F3 — Biographical padding in ch01 narrator additions: condense to single paragraph

**Request:** Too much historical Ghazali biography in ch01 narrator layer. Reduce to a
single paragraph with a few sentences. Suppress in editor or delete from chapter?

**Investigation findings:**
- ch01 narrator has 7 consecutive biographical paragraphs (P2–P8, ~540 words): birth name
  and kunya etymology, birth year, descent, study under al-Juwayni, Baghdad appointment,
  spiritual crisis, five-year journey, the Ihya, retirement, death.
- P1 (blessing of teaching this text) + P9–P12 (tarbiya insight, modern relevance, Dhahabi
  quote, letter opening) are substantive Shaykh commentary — KEEP ALL.
- ch02–ch05: no biographical padding. Open directly into text commentary. No action needed.
- The biographical content originates in Lecture 1 (live audience introduction). Structurally
  appropriate for a live lecture; not appropriate as a narrator additions layer for the podcast.

**Decision: DELETE (condense in file) — not suppress.**
- Narrator additions will eventually assemble into episode text. Suppressing creates debt
  that has to be caught again at bundle time.
- The Shaykh's words are preserved in spirit via the condensed paragraph.
- If a "book introduction" segment is ever built, the raw lecture content is always
  recoverable from `_system/source/lectures/lec01-introduction.txt`.

**Condensed replacement paragraph (plan spec):**
  "Imam al-Ghazali — Hujjat al-Islam, born in Tus in 450 AH — spent forty years mastering
   the religious sciences before a profound spiritual crisis led him to resign from the
   prestigious Nizamiya Madrasa in Baghdad, travel for five years, and produce the Ihya
   Ulum al-Din. Ayyuhal Walad is a later distillation of that work, written in response
   to a student's request for concise, actionable guidance."

**Implementation scope:**
  A. content/drafts/books/ayyuhal-walad/_stages/ch01-frame-and-first-counsel/additions-narrator.md:
     Replace P2–P8 with the condensed paragraph above. Keep P1, P9–P12 verbatim.
  B. scripts/podcast/narrator_additions.py: Add guardrail to Gemini prompt —
     "If the lecture opens with biographical background about the author (birth, education,
     career, death), condense it to a single paragraph of no more than 3 sentences before
     the substantive commentary begins. Do not omit it entirely — a brief contextual
     anchor is useful. But 7 paragraphs of biography is not commentary."

**Confidence:** HIGH. Scope clear. ch01-only. Other chapters unaffected.


---

## CATEGORY DEFINITIONS (locked)

Two and only two editorial actions exist in this plan:

**SUPPRESS** — the paragraph IS required in the source file (pipeline needs it, or it's
attributed source material that must be preserved) but should NOT be rendered in the editor
as readable prose. In the editor: collapsed to a single-line icon marker (e.g. ⊘ or ◎).
Hovering reveals the hidden paragraph in a well-formatted pop-up. The file on disk is unchanged.
Examples: pipeline metadata paragraphs (F1), H1 stage headings (F2).

**CONSOLIDATE** — the paragraph exists in the source but adds no value to the podcast
generation pipeline. Background info, biography, encyclopedic context that is not the
teaching. Action: replace N paragraphs with 1 condensed paragraph in the source file
(the file changes). The condensed version preserves the essential context in 2–3 sentences.
Examples: biographical intro padding (F3).

F1 and F2 are reclassified: both are SUPPRESS (not delete — the metadata lines serve
pipeline traceability; the H1 serves file orientation when opened in a text editor).


---

## AGENT DESIGN — editorial-auditor (skeleton, locked decisions)

**Name:** `editorial-auditor` (script: `scripts/podcast/editorial_auditor.py`,
slash command: `/editorial-audit <slug>`)

**Output:** `content/drafts/books/<slug>/_system/editorial-audit/<chapter>.json`
per chapter. Shape (provisional):
  {
    "slug": "ayyuhal-walad",
    "chapter": "ch01-...",
    "stage": "narrator",        // which stage file was audited
    "audited_at": "2026-...",
    "findings": [
      {
        "id": "EA-001",
        "paragraph_index": 1,   // 0-based, matches TipTap paragraph order
        "action": "suppress",   // "suppress" | "consolidate"
        "confidence": "high",   // "high" (deterministic) | "medium" (LLM)
        "reason": "Pipeline metadata artifact — lec transcript provenance",
        "pattern": "METADATA_ITALIC",   // named pattern that fired
        "condensed_replacement": null   // only for consolidate findings
      }
    ]
  }

The Studio editor reads this JSON on stage load and pre-applies:
  - suppress findings → collapsed icon marker, hover reveals pop-up
  - consolidate findings → paragraph highlighted + suggested replacement shown

**Trigger:** on-demand only. CLI: `python3 scripts/podcast/editorial_auditor.py
--slug <slug> [--chapter <chapter>] [--stage <stage>] [--all-stages]`
Slash command: `/editorial-audit <slug>` (invokes the agent spec).

**Detection stack (two layers):**
  Layer 1 — deterministic patterns (zero cost, runs always):
    Named pattern registry (extensible dict, not hardcoded):
      METADATA_ITALIC    → r'^_Cleaned from lecture\|^_Extracted span\|^_Re-voiced'
      H1_STAGE_LABEL     → first H1 matching the stage label template
      BIO_INTRO_BLOCK    → run of ≥3 consecutive paragraphs matching biographical signals
                           (birth year, AH/AD dates, "was born in", "passed away",
                           "studied under", "appointed to", "began his studies")

  Layer 2 — LLM judgment (Gemini, ~$0.001/chapter, runs only when Layer 1 is ambiguous):
    Called when a paragraph matches partial signals but confidence is below threshold.
    Prompt: "Is this paragraph background/biographical context about the author, or is it
    the Shaykh's substantive commentary on the text's teaching? Reply: background | teaching"

**Extensibility:** new patterns added to the registry dict, not to the core logic.
The agent itself never needs to change when new pattern types are discovered.


---

## AGENT DESIGN (continued) — stages in scope

Narrator stage only (Asif's decision). Other stages not audited in v1.

---

## F4 — ch02: Lecture-bridge framing wrapping real teaching content

**Chapter:** ch02-hatim-eight-benefits, P03
**Pattern:** RECAP — paragraph opens with lecture-bridge phrase before teaching content

**Full paragraph:**
  "The previous lesson concluded with Imam Al-Ghazali discussing Tahajjud, the night vigil
   prayer. He recounted the Prophet's words about Abdullah Ibn Omar, 'What an amazing man,
   if only he would stand up at night.' After hearing this, Abdullah Ibn Omar never missed
   Tahajjud. While this practice is easier for some than for others..."

**Analysis:** Two things fused. Lecture-bridge opening ("The previous lesson concluded with...")
is an artifact. The Tahajjud teaching and Abdullah Ibn Omar story are legitimate Shaykh
commentary relevant to ch02's theme (acting on knowledge). A podcast listener has no
"previous lesson" context.

**Action: CONSOLIDATE** — strip the lecture-bridge phrase, rewrite paragraph to open with
the teaching content. Proposed opening: "Among the most beloved acts of worship that Imam
al-Ghazali's counsel points toward is Tahajjud, the night vigil prayer..."

**Agent rule:** when RECAP pattern fires AND paragraph contains teaching content after the
bridge phrase → consolidate (not suppress). When RECAP fires AND paragraph contains ONLY
recap with no new teaching → suppress.

**All-chapters verdict:** ch01 clean, ch02 P03 hit, ch03 clean, ch04 clean, ch05 clean.

---

## F5 — ch05: Summary enumeration list at chapter close

**Chapter:** ch05-method-and-closing-prayer, P09
**Pattern:** SUMMARY_LIST — enumerated list of the letter's eight advices

**Full content:**
  "In summary, the eight advices from Imam al-Ghazali are: The four things to refrain from:
   1. Do not debate... 2. Do not be a preacher... 3. Do not mingle with rulers...
   4. Do not accept gifts from rulers..."

**Analysis:** NOT an artifact — the Shaykh deliberately summarised the letter. The list
maps directly to Ayyuhal Walad's architecture. Valuable for NotebookLM structure reference.

**Action: KEEP.** Do not tag for suppression or consolidation.

**Note for bundle assembly phase (not this plan):** if the episode goal is discovery-first,
this summary should move to the END of the assembled episode text rather than sitting
mid-narrator. Assembly-order concern, not editorial-quality concern.

**All-chapters verdict:** ch01–04 clean, ch05 P09 — KEEP.


---

## VISUAL DESIGN — three-state editorial annotation system (locked)

**SUPPRESS → collapsed pill, inline in document order**
- Paragraph replaced by a single-line pill at its exact position in the document.
- Shape: `⊘  <type label>  ·  <char count>                    ▾`
- Styling: subdued background (var(--c-bg-elev)), muted text (var(--c-ink-muted)),
  thin border (var(--c-rule)), border-radius: 999px, full-width or near-full-width.
- Hover: floating popover card shows full paragraph text + suppression reason + "Reveal" toggle.
- Click ▾: expand in-place to show full text (inline reveal, not popover).
- CSS class: `.para-suppressed-pill`
- Implementation: ProseMirror NodeDecoration replacing the paragraph node rendering.
- Position: stays in document order — pills are navigable, not hidden.

**CONSOLIDATE → amber left border + proposal slot**
- Original paragraphs stay fully readable (user must review before accepting).
- Left rule: 3px solid amber/warning color mapped to a new --c-warn token
  (approx. var(--c-amber, #d97706) or nearest existing token).
- Above the block: `▌ Condense  ·  N paragraphs → 1  ·  <pattern name>`
- Below the block: inset card with suggested replacement text + 3 actions:
  Accept (writes replacement to file), Edit (opens replacement in TipTap draft), Reject.
- CSS class: `.para-consolidate-block` on each paragraph in the group.
- Proposal card class: `.consolidate-proposal`

**KEEP → no visual treatment**
- Clean prose. Absence of any marker = audited and cleared.
- No gutter dot (Asif: "no marker = clean" is unambiguous enough).

**Decision: pills render in document order (inline), not pulled into inspector.**


---

## F6 — Chapter size disparity: denoise is correct, reconcile step is missing

**Request:** Why are ch01 and ch03 so much shorter? Is denoise over-stripping?

**Investigation findings:**

Word count matrix (words):
  ch01: source=6,435 → core=6,397 → denoised=505 → normalized=447 → final=3,067
  ch02: source=2,673 → core=2,655 → denoised=1,701 → normalized=1,387 → final=2,550
  ch03: source=505 → core=499 → denoised=214 → normalized=209 → final=3,061
  ch04: source=2,794 → core=2,782 → denoised=1,802 → normalized=1,554 → final=2,744
  ch05: source=1,808 → core=1,788 → denoised=874 → normalized=698 → final=2,677

ch01 source is 6,435w but 92% is translator's footnotes (Lane TON citations, Arabic
script explanations, academic apparatus). Gemini correctly stripped them. 505w is the
actual Ghazali prose in the English academic translation. Denoise behavior: CORRECT.

ch03 source is genuinely condensed in the English academic translation (sections XXI–XXII
= ~499w). Rich "path and stations" content is in the Arabic original. Denoise: CORRECT.

The v3.5 final chapters/ are balanced (all ~2,500–3,000w) because that pipeline used
a different source or reconstruction approach. WC8 _stages/ content is English-translation-
only without the reconcile step.

**Root cause: RECONCILE slice (Slice 3) was never productionized.**

Three source PDFs exist:
  Arabic original: 5,194w OCR — the spine (authoritative Ghazali text, no apparatus)
  English superior: 31,388w OCR — translation layer
  Scholarly edition: 33,475w OCR — commentary/additions layer

The reconcile step was designed to use the Arabic original as the spine, align the
English translation and scholarly commentary on top, and reconstruct chapter boundaries
based on content and flow. It was done ONCE inline for ch01 only (found 7 Quran citations).
It was never built as a script. No stage runner producer exists for it (returns no_script).

**Impact:** WC8 normalized content is NOT ready to replace the v3.5 chapters/ files.
The chapters/ files (used by assemble_bundle.py and NotebookLM) should remain as source
until the reconcile step is productionized.

**Action: NOT an editor display issue. Pipeline gap.**
  A. Productionize the reconcile step: build reconcile_stage.py that:
     - Reads Arabic OCR spine (_system/source/multi/ocr/arabic.md)
     - Reads per-chapter English denoised text (_stages/<ch>/denoised.md)
     - Aligns them (Gemini bulk for chapter segmentation, ~$0.02/book)
     - Writes _stages/<ch>/reconciled.md as a new stage
     - The reconciled stage becomes the input to normalize (replacing denoised)
  B. Until A is built: keep v3.5 chapters/ as the assembly source. Do not use
     _stages/normalized.md for podcast output.
  C. For the editorial auditor agent: flag when normalized word count < 400w as
     a PIPELINE_GAP warning, not an editorial finding.

**Confidence:** HIGH. Cause and consequence both clear.


---

## F7 — Full-book holistic segmentation: architectural requirement

**Context:** F6 identified that the reconcile step was never productionised. Asif confirmed
the correct architectural model: process the full book as a unified stream, THEN segment.

**Raw material inventory:**
  Arabic original:    5,194w  — spine (every word is Ghazali)
  English superior:  31,388w  — translation layer
  Scholarly edition: 33,475w  — commentary additions
  12 lectures:      136,258w  — narrator/explainer layer
  TOTAL:            206,315w  — full pool before distillation

**Current pipeline output (WC8 normalized, all 5 chapters):** 4,295w total (~859w avg)
**Target per episode (25–30 min NotebookLM):** 4,000–4,500w
**Required total for 5 episodes:** ~22,500w

**Architectural principle (locked by Asif):**
  Chapter boundaries are NOT inherited from source divisions. After the full book is
  translated, augmented, refined, and denoised as a SINGLE STREAM, the unified content
  is reviewed holistically and re-segmented into equally comparable episodes (~4,500w each).
  Thin sections are augmented from the wisdom corpus and online resources before segmentation.

**Required new pipeline stages (none of these exist as scripts):**
  1. full_book_ingest.py — OCR/transcribe all sources as single streams (no per-ch split)
  2. full_book_denoise.py — denoise each stream (Arabic → translate, then denoise)
  3. reconcile_book.py — align 4 streams against Arabic spine, inject corpus refs
  4. segment_book.py — holistic review + equal-length episode segmentation (~4,500w target)

**Decision: stop collecting editor findings. Execute the full-book processing pass.**
  Gate: reconcile_book.py must land before segment_book.py.
  The editorial auditor agent remains valid for the new chapter artifacts produced
  by segment_book.py — same patterns will apply to the new chapters.


---

## COST BREAKDOWN — full-book holistic processing pass

Already paid (not re-spent):
  OCR 3 PDFs (Azure):          $0.37
  12 lecture transcriptions:   $4.31
  Narrator additions + prior:  ~$0.22
  Total already paid:          ~$4.90

New work breakdown:
  Denoise Arabic (Gemini Flash):           $0.011
  Denoise English superior (Gemini Flash): $0.045
  Denoise Scholarly (Gemini Flash):        $0.048
  Reconcile 3→1 (Gemini Flash, 1M ctx):   $0.045
  Narrator layer inject (reuse, $0):       $0.000
  Holistic segmentation (Claude Sonnet):   $0.097  ← only Claude call
  Normalize 5 new chapters (Gemini):       $0.054
  Knowledge augment (corpus, $0):          $0.000
  TOTAL NEW:                              ~$0.30

Cumulative all-in:                        ~$5.20

Design principle:
  Gemini Flash for all mechanical bulk (68% of new cost).
  Claude Sonnet for exactly 1 judgment call: holistic segmentation.
  No re-running of prior correct work.

