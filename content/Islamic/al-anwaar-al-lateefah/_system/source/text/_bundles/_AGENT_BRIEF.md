# Holistic-editor section brief — al-Anwaar al-Lateefah (enhanced reading edition)

You are producing ONE section of an Ismaili scholarly reading edition built from oral lecture
transcripts. You will be told which bundle file to read and which output file to write.

## Inputs
- `_bundles/sec-NN.md` contains, for your lecture range:
  1. A checklist of **LEDGER SPINE TEACHINGS** (each with an id like `S014`) — the fidelity
     contract. Every one MUST survive in your output at FULL DEPTH.
  2. The **RAW SPINE TRANSCRIPT** for those lectures — your raw material to enhance.

## What the raw transcript looks like (and what to strip)
The source is a live oral lecture, transcribed. It is full of:
- Socratic call-and-response drilling ("How many gates? Five. How many? Five.") — KEEP the
  teaching once, in declarative prose; DROP the repeated drill.
- False starts and self-corrections ("...so two of them... were for the Qa'im...") — repair into
  one clean sentence.
- Ellipsis fragments, "Understood?", "Yes.", filler, audio crosstalk, restarts — DROP.
- The teacher re-reading the same Arabic line two or three times — keep it ONCE.

## Your job (in priority order)
1. **Preserve every ledger teaching at FULL DEPTH** — full exposition, reasoning, examples,
   scriptural support. NOT a one-line mention. The ledger ids are your coverage checklist; every
   id in the bundle must be fully present in your prose. Do NOT summarize.
2. **Keep all Arabic/Quran quotations VERBATIM.** Where the transcript gives an Arabic line in
   backticks followed by a parenthetical English gloss, reproduce the Arabic exactly (in
   backticks) and keep a clean English translation. Do NOT alter Arabic script/transliteration in
   quotations — it is canonically restored by a later step. In ordinary PROSE use plain ASCII
   transliteration (e.g. tawhid, hudud, aql al-awwal, Qa'im).
3. **Denoise** per the list above — remove oral redundancy, drilling, false starts, crosstalk,
   off-topic asides, filler. Genuine teaching analogies (the TV-receiver image, the body's 360
   parts, etc.) are CONTENT — keep them; they are not noise.
4. **Reorganize into a logical reading flow** under the section's H2 title (given to you) with
   `###` H3 sub-theme headings where the material naturally turns. Smooth the order so a reader
   can follow it; you may move a teaching to sit with its kin.
5. **Enrich the author's OWN language** — turn telegraphic fragments into full, dignified
   scholarly sentences; add connective tissue and transitions. But invent NO new doctrine, no
   new claims, no outside material. Every idea must trace to the transcript or the ledger.

## Hard rules
- DO NOT introduce any teaching the spine does not raise. No augmentation here.
- DO NOT summarize or compress teachings to hit a word target. **Fidelity beats brevity** — if
  full preservation would exceed the target, exceed it.
- Output is reading PROSE (paragraphs), not bullet lists or a study guide. Reverent, lucid,
  scholarly register suited to an Ismaili haqa'iq text.

## Output
- Write to the given output file with the Write tool.
- Begin the file with the H2 line: `## <section title given to you>`
- Use `###` for sub-themes. Flowing paragraphs throughout.
- Hit roughly the target word count you are given; never fall below the stated floor (a floor
  breach means you summarized — go back and restore depth).

## Final message back to caller (SHORT — do NOT paste the prose)
Return only:
- `section: NN`
- `words: <actual word count of the file you wrote>`
- `h3_headings: [...]`  (the sub-theme titles you used)
- `ledger_ids_covered: <count> / <total in bundle>` — confirm all covered; name any you could
  not place.
- `denoise_removed:` 3–6 one-line bullets naming what you stripped (for the curation log), e.g.
  "Socratic gate-counting drill in L4 (repetition)", "false-start fragments throughout".
