# Source Distillation Patterns — by source type

Distillation is Phase 2 work that produces signal from the raw source. Under the strict 1:1 chapter ↔ episode mapping (`skills-staging/podcast/SKILL.md` §0), distillation extracts what the chapter is saying so the episode's `00-framing.md` and authoring scaffolds (`02-key-passages`, `03-context-pack`, `04-discussion-spine`, `99-show-notes`) can shape the listener's experience.

**The chapter itself is authored in Phase 0d (design) + Phase 0e (enrichment) of the any-format long-source ingestion protocol** — not in Phase 2. Phase 0a normalizes the source (PDF, audio, Word, PPT, etc.) to text; Phase 2 reads the already-enriched chapter and extracts the spine from it.

All patterns produce the same six outputs (core thesis, arc, key passages, tensions, context, application angle) but the EXTRACTION method differs by source type.

## Enriched book chapter (the default — produced by Phase 0)

**Method**: read the enriched chapter `BOOK_DIR/chapters/chNN-<slug>.txt` twice.
  - First pass: take no notes. Just absorb the argument.
  - Second pass: capture the spine.

**Capture**:
  - **Core thesis** — the one sentence the chapter would write if forced to summarize itself.
  - **Arc** — beat-by-beat: opening claim → support → counter-position → resolution. Enriched chapters often have 4–8 movements.
  - **Key passages** — 8–15. Bias toward passages that:
    - State a position clearly
    - Surprise (the chapter goes somewhere unexpected)
    - Contradict another part of the chapter or another tradition
    - Anchor a tradition or terminology (the Phase 0e enrichment quotes are gold here — they're already attributed)
    - Land emotionally
  - **Tensions** — both internal (within the chapter) and external (e.g., between the source author and an enrichment source the chapter quotes).
  - **Context** — when the original source was written, who the author was responding to, what tradition (the chapter's enrichment paragraph carries this; the distillation extracts and tightens it).
  - **Application angle** — how does this land for the named audience.

**Trap to avoid**: distilling away the enrichments. The Quranic verses, hadith, sayings of Imam Ali (AS), and Ismaili sources Phase 0e wove into the chapter ARE part of the spine and belong in `02-key-passages.md` with their attributions intact.

## Article / essay (single chapter only — no Phase 0 multi-chapter design)

**Method**: single pass, then beat-mapping.
  - Articles already have a thesis upfront — find it in the first 1–2 paragraphs.
  - Identify the move structure: claim → evidence → objection → response → conclusion.
  - Often 1–3 key passages is plenty.
  - For a stand-alone article, the chapter file `BOOK_DIR/chapters/ch01-<slug>.txt` can be near-complete: refine the article's English (Phase 0b), apply phonetic transcription if it contains Arabic (Phase 0c), and enrich modestly per the whitelist in `enrichment-sources.md` (Phase 0e). The article's own structure IS the chapter.

**Trap to avoid**: over-distilling. If the essay is already tight, your distillation is mostly direct quotation with light framing.

## Memoir chapter (from `content/babu-memoir/chapters/`)

Memoir chapters reach this skill via the one sanctioned crossing declared in SKILL.md §9: `content/babu-memoir/chapters/*.txt` is read-only input to the `extract` capability (`scripts/podcast/extract_chapter.py`). Everything else under `content/babu-memoir/` — `reference/`, `_system/`, `scratchpad/`, any `voice-fingerprint*` or `master-context*` file — remains journal-skill territory and is blocked at the adapter layer (`PROHIBITED_PATH_PREFIXES`, `PROHIBITED_NAME_PATTERNS`).

When a memoir chapter is podcasted, treat it as authored prose under Extract Mode (`content/podcast/_handbook/extract-capability.md`). The chapter file IS the SOURCE upload; the per-chapter contract at `content/podcast/from-memoir/chapter-contracts/<slug>.yml` carries audience, angle, tensions, anchor passages, and phonetic overrides. No enrichment from the whitelist (Phase 0e) is applied to memoir material — memoir is first-person voice and stays unembellished. The `derived_from:` field in each contract tracks lineage when a single memoir chapter has been split into two derivatives (e.g., `ch01-man.txt` → `inheritance` + `becoming`).

**Trap to avoid**: pulling memoir reference files (voice-fingerprint, master-context, scratchpad notes) into a podcast bundle. Those are journal-skill territory and the adapter refuses to read them.

## Transcript / lecture

**Method**: structure-finding through the spoken meander.
  - First pass: read the full transcript. Note where the speaker reaches their actual point.
  - Speakers often spend 2–3 minutes circling before landing the argument. Discard the circling when authoring the chapter in Phase 0d.
  - Preserve speaker's verbatim quotes in `02-key-passages.md` — including hesitations if they're meaningful.

**Capture**:
  - **Core thesis** — the argument once stripped of verbal filler.
  - **Arc** — often the speaker's actual argument is non-linear; reorder for clarity in the chapter (Phase 0d) but note in `chapters-rationale.md` that you reordered.
  - **Key passages** — the moments where the speaker lands the punch.
  - **Tensions** — the speaker may have argued with themselves; capture the contradiction.
  - **Context** — venue, occasion, audience, year.
  - **Application angle** — adjusted for written/listening audience.

**Trap to avoid**: cleaning up the speaker so much that they sound like a different person. Preserve the voice while removing the filler.

## Audio recording (transcribed in Phase 0a)

**Method**: same as Transcript/lecture above, but with two added concerns introduced by automatic transcription.
  - **Transcription confidence**: Phase 0a's transcriber is not perfect. Names, technical terms, and rapid speech are common mis-transcriptions. Spot-check anything that lands in `02-key-passages.md` against the original audio (Phase 0a leaves the original at `BOOK_DIR/_system/source/<title>.mp3`).
  - **Speaker diarization**: if more than one voice was on the recording, Phase 0a's diarizer labels speakers as `Speaker A` / `Speaker B` etc. Replace with real names in Phase 0b where confidence is high; flag the rest in `_extraction-notes.md`.
  - **Timestamps**: Phase 0a inserts `<!-- mm:ss -->` markers every ~60s. Keep them through Phase 0d so Phase 2 distillation can cite back to specific moments in `02-key-passages.md` (format: `(audio 14:23)` instead of `(page 14)`).

**Trap to avoid**: trusting the transcript verbatim for quoted material. Any quote you plan to include MUST be verified against the audio, because a 95%-accurate transcriber still mis-hears one word in twenty.

## Word document (.docx) / structured prose

**Method**: identical to "Enriched book chapter" above once Phase 0a has normalized the document. Two notes:
  - Heading hierarchy in the source is a *hint* for Phase 0d chapter design but is not binding. A Word document with five H1 sections may still resegment into 3, 7, or 10 chapters based on thematic weight.
  - Tables in the source survive Phase 0a as markdown tables; they may or may not be load-bearing for the argument — distillation decides whether each table is a key passage or context.

## PowerPoint deck (.pptx)

**Method**: slide-first reading, then thematic re-segmentation.
  - Phase 0a extracted both slide text AND speaker notes. Speaker notes typically carry the argument; slide text typically carries the headlines.
  - First pass: read all speaker notes in order. They give you the spoken argument the deck would have carried.
  - Second pass: read slide text. Identify which slides are setup, which carry punch, which are placeholders.
  - Phase 0d should group slides into 4–10 chapters based on argument arcs, never one chapter per slide.

**Capture**:
  - **Core thesis** — usually emerges from the first 3–5 slides' speaker notes.
  - **Arc** — slide order is your starting point but you may reorder if the deck was poorly structured.
  - **Key passages** — quote either the slide headline OR the speaker note, whichever carries the punch; never both unless they say different things.

**Trap to avoid**: treating the deck as if each slide were a chapter. Decks are dense headline-and-illustration formats; a 40-slide deck is rarely more than a 10,000-word essay's worth of content.

## Excel / spreadsheet (.xlsx)

**Method**: only used when the spreadsheet IS the source (a table of aphorisms, a structured journal of one-line teachings, a register of incidents). For data spreadsheets where the analysis is the point, the spreadsheet is supporting evidence, not the source — author the analysis separately and treat the spreadsheet as an enrichment reference.
  - Phase 0a flattens each sheet to a markdown table. Read each table end-to-end.
  - Decide whether each row is its own micro-chapter (rare) or whether thematic groupings yield 5–10 chapters.

**Trap to avoid**: turning a spreadsheet podcast into row-by-row recitation. Find the patterns across rows.

## Asif's notes

**Method**: expansion with marking.
  - Notes are usually outline form.
  - Expand each bullet into a paragraph or short section in the chapter file.
  - Anywhere you expand beyond what the note says, mark `[expanded from note]`.
  - Anywhere you add an inference, mark `[claude inference]`.

**Always ask Asif**:
  - What did you mean by [ambiguous bullet]?
  - Was [X] meant as a tension or as your settled position?
  - Who is this for?

**Trap to avoid**: producing fluent prose that sounds like Asif but contains positions he didn't state. Use the marks. Better honest than smooth.

## Multi-source synthesis (2–4 sources in one chapter)

**Method**: distill each source independently, then synthesize into ONE chapter.
  - Run the appropriate single-source method per source.
  - Author a single chapter that puts the sources in conversation; the chapter is still one NotebookLM source per the 1:1 mapping.
  - The synthesis lens lives in the chapter's opening contextual frame and in `04-discussion-spine.md`.
  - The framing file (`00-framing.md`) declares the lens to NotebookLM.

**Capture additionally**:
  - **Agreements** — where do the sources overlap?
  - **Tensions** — where do they disagree?
  - **Synthesis lens** — what is the EPISODE arguing by putting these in conversation?

**Trap to avoid**: false equivalence. If one source is much stronger than the other, say so in the framing — don't pretend balance.

---

## How distillation connects to chapter design (Phase 0d) and enrichment (Phase 0e)

The order matters:

1. **Phase 0a/0b/0c** produce a single refined English source file with full Arabic phonetic coverage. This is `normalized.md`.
2. **Phase 0d** is chapter design — split `normalized.md` into balanced thematic chapters in `BOOK_DIR/chapters/`. Distillation (this file) is NOT yet running.
3. **Phase 0e** enriches each chapter from the whitelist in `enrichment-sources.md`. Outside material ≤ 60%. The chapter is now substantively complete.
4. **Phase 1–3** then run per episode: intake → distill the enriched chapter (this file's methods) → author the episode-draft scaffolds (`00-framing.md` etc.).
5. **Phase 4** builds the episode txt from `00-framing.md` + the matched chapter.

Distillation is downstream of authoring. The chapter file is the source of truth; this file's methods extract from it, they do not produce it.
