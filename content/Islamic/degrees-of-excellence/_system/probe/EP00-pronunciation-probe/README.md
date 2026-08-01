# Pronunciation probe — degrees-of-excellence

A one-time pronunciation check covering the 39 highest-risk Arabic terms in
this book, BEFORE any episode is generated. Catch and fix mispronunciations
here, and every chapter (and future book, via the shared library) inherits the
corrections.

## Generate this in NotebookLM

Click the Chapters cell to open the SOURCE to upload; the Episodes cell to
open the FRAMING to paste into Customize.

| Chapters | Episodes | Deep dive or debate | Length |
|---|---|---|---|
| [(pronunciation probe)](pronunciation-probe.md) | [EP00 — Pronunciation probe](00-framing.md) | Deep Dive | Default |

(Length is a real variable here, not a formality. Run 1 on 2026-08-01 used
**Shorter** for 39 terms — five minutes, seven seconds a term — and the model
spent its budget on theme instead, naming 9. Use **Default**, or probe fewer
terms: `run_pronunciation_probe.py <slug> --top-n 15 --rebuild`. Settled terms
drop out of the next run, so a short list is a batch, not a compromise.)

1. New notebook -> upload `pronunciation-probe.md` as the source.
2. Customize -> paste `00-framing.md` into the prompt box.
3. Generate the Audio Overview (**Default** length; see the note above).
4. Listen once with `listen-checklist.md` open; mark OK? / Fix per term.
5. Save the filled checklist; resume the orchestrator to apply corrections.

Note: NotebookLM is non-deterministic. The probe shifts the odds toward
correct pronunciation and surfaces terms it can NEVER say (mark those
`GLOSS:`) — it is not a guarantee of a perfect final render.
