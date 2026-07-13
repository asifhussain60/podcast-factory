# Book Pipeline v2 — cutover checklist (HELD, pending fixture validation)

Phases 0–6 landed the full v2 machinery behind `book_pipeline_v2` (default **OFF**).
Phase 7's acceptance matrix is green. The remaining cutover — flip the default ON,
delete the legacy paths — is deliberately **held** here rather than executed
autonomously, because it depends on a validation gate that needs authorized LLM
spend and because deleting the legacy fallback is a Tier-2 destructive step.

## Why held

The plan's own verification gate is a flag-ON end-to-end run across the knob matrix
`{none|source_only} x {faithful|author_companion}` on BOTH fixture books
(`the-master-and-the-disciple`, `mukhtasar-ul-asar-2`), green on `book-challenger`
BK-P4 (faithfulness) AND `book-render-challenger` (print). That run is multi-hour
LLM generation (Tier-2 spend) and has not been executed. Flipping the default ON
before it passes would make an unvalidated, accuracy-critical path the default for
every book — a direct conflict with "accuracy is paramount, no change may alter a
teaching." Deleting `generate_translation_edition.py` + the legacy inject paths
removes the OFF-path safety net before v2 is proven.

**Current state is safe:** with the flag OFF (default), the pipeline reproduces
today's output byte-for-byte (proven by the acceptance suite + per-phase tests).
Landing this on `develop` changes nothing until someone opts a book in.

## Validation progress (2026-07-13)

**Fluency de-calque — VALIDATED on real content.** The highest-risk new behavior
(the fluency de-calque pass + its faithfulness gates, `_book_voice.apply_fluency_adapt`
/ `revoice_gates`) was exercised directly on two real chapters of
`mukhtasar-ul-asar-2` (Binding Words 1060w; What We Wear 3012w / 59 Arabic runs):

- Both **KEPT** (de-calqued, passed every gate); **0 reverted-on-drift**.
- Genuine prose de-calque (e.g. "went out one cold day wearing a fur cloak" ->
  "once went out on a cold day in a fur") with the teaching, the quoted hadith, and
  the `(ع)` honorific preserved verbatim.
- **All 59 Arabic-script runs preserved** (Arabic-preservation gate held); word
  counts held/rose (anti-abridge gate held); no new doctrinal P0.

The author-companion re-voice pass shares the same `revoice_gates` machinery, so this
also validates that path's safety. **Conclusion:** the accuracy question at the heart
of the cutover is answered — the new pass improves readability without altering
meaning. Still outstanding for a FULL cutover gate: the whole knob matrix run
end-to-end on both fixture books + the Astro Composer -> Generate PDF ->
book-render-challenger loop (needs a stable session for the long compose; the
environment killed the multi-hour base recompose twice on 2026-07-13).

## Validation gate (run first, when spend is authorized)

On a fixture book, set `book_pipeline_v2: true` in its `series-config.yaml` (or
export `BOOK_PIPELINE_V2=1`) and, for each knob cell:

1. Run the book branch (design -> compose(v2) -> illustrate -> slide-import ->
   awaiting-layout halt). Confirm `book.md` has zero `<figure>` and
   `book/visuals/index.json` lists every candidate.
2. `none` adds no un-sourced content (BK-P4); `source_only` blocks are labeled +
   traceable and pass `_doctrinal` T1–T5.
3. Drive the Astro Book Composer: place visuals (each align + flow, resize,
   drag-move), Save -> `book/visual-layout.json`, Generate PDF.
4. Confirm the PDF: no figure spanning a page break, no `NotebookLM` watermark, no
   duplicated caption, correct float(wrap)/centered(standalone) placement, no
   blank/half-empty interior pages. `book-render-challenger` RENDER-CLEAN.
5. Green `book-challenger` (BK-P4) on the whole book.

## Cutover steps (execute ONLY after the gate passes + explicit approval)

1. Flip the default: `_pipeline_flags.book_pipeline_v2_enabled` returns True when
   unset (or set the config default). Update the tests that assert default-OFF.
2. Delete the now-dead legacy paths: `generate_translation_edition.py`, the
   `_inject_figures` path in `_book_illustrate.py`, the `inject_slides` write in
   `_slide_import.py`, and the legacy compose branch in `book_driver.py`.
3. Remove the flag scaffolding once nothing reads it.
4. Regenerate dashboard snapshots; keep TS<->Python mirrors in sync; update
   `plan.yaml`/`plan.md`.
5. Run `repo-surgeon --scope podcast`; fix findings.

Until then: `book_pipeline_v2` stays OFF on `develop`, fully tested, ready to
validate.
