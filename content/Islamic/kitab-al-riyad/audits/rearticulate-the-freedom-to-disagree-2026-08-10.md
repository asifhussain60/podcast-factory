# Rearticulation audit — "The Freedom to Disagree" (chapter key: `the freedom to disagree`)

Date: 2026-08-10
Book: kitab-al-riyad

## Verdict: REVERTED

The engine's own quality gates rejected the rewrite and restored the pre-run
chapter untouched. `book/book.md` carries the same base-translation text it
had before this run; no hand-patching was applied.

## Baseline (pre-run, matches post-run since the chapter was reverted)

- Word count: 1,632 (base_words, per sidecar and `book-fluency-report.json`)
- Arabic-script runs: 39 (regex count of contiguous Arabic-character
  sequences in the chapter body, including the four standalone
  transliteration/name blockquotes)
- Speech tags: none — this chapter is expository historical narration
  (no quoted dialogue between named speakers), so REQ-BA-040/100 do not
  bear on it directly
- Enumeration: none (no numbered/lettered lists in this chapter)
- Signature images/metaphors present in the source that any rewrite must
  preserve: the book titles read as their literal meanings — *al-Mahsul*
  ("The Harvest"), *al-Islah* ("The Correction"), *al-Nusra* ("The
  Defense"), *al-Riyad* ("The Gardens" / "a judgment between the two
  reformers"); "a garden opened not to be planted anew, but to be judged"
  (introduction, carries into the chapter's frame); "spilled beyond the
  oral discussions... into long treatises."

## Known pre-existing defect (out of scope for this pass)

`book-duplication-check.json` already flags this chapter: paragraphs 13–23
and 25–61 of the current `book.md` are near-duplicates of each other (a
~1,000-word block restating the same historical narrative twice, min_ratio
0.559). This looks like a base-compose seam artifact, not something a
rearticulation pass is meant to fix — but it explains why a faithful,
non-abridging rewrite of this chapter's *unique* content would legitimately
come out much shorter than 1,632 words, while the engine's length gate
cannot distinguish "collapsed duplication" from "lost content." Flagging
this for compose/challenger territory rather than trying to work around it
here, per the hard limit against fixing content-shape defects from this
agent.

## Gate findings (second attempt, this run)

- `rearticulate-02: abridged re-voice (856<979 words)` — output came in
  under the chapter's minimum floor.
- `rearticulate-02: P1 large length drop: 1632->856 words (52% of source —
  possible content loss)` — same signature as the first, reverted attempt
  (852/1623, 52%), reproduced almost exactly (856/1632, 52%).
- `rearticulate-02: Arabic runs dropped (31<39)` — new finding this attempt
  did not surface before: 8 Arabic-script runs (roughly a fifth of the
  chapter's Arabic) went missing from the rewrite. This is a direct
  REQ-BA-070/Arabic-retention concern and on its own would have been
  disqualifying even had the length gate passed.

## Judgment

The rewrite the model produced this round again cut the chapter to roughly
half its source length AND additionally lost eight Arabic-script runs —
a second, independent signal (beyond length) that the model is compressing
by dropping content rather than by tightening prose. Given that the source
already contains a genuine, flagged duplication artifact that makes some
length reduction legitimate, disentangling "the model correctly declined to
retranslate the duplicated block twice" from "the model dropped teaching
content and Arabic citations" is exactly the kind of judgment call the gate
is designed to force a human/agent review of rather than silently accept.
Re-running a third time without changing the underlying constraint (the
model's tendency to compress this specific chapter) would only spend more
without new information, so per the max-3-iteration/no-unbounded-looping
rule this is reported now rather than retried blind.

## Recommendation (not executed — compose/challenger territory)

Before a third rearticulation attempt is worth trying, the duplication
defect in `book-duplication-check.json` should be resolved by the compose
pipeline (collapsing the repeated ~1,000-word block into one telling). That
would both shrink the legitimate source word count the length gate compares
against and remove the ambiguity that likely drives the model toward
aggressive compression on this chapter specifically.

## Sidecar record

`_system/rearticulate-status.json`, `saved_at`/`finished_at`:
2026-08-10T14:52:46.202763+00:00 — `state: "done"`, `record.status:
"reverted"`, `record.base_words: 1632`, `record.output_words: 1632`
(unchanged, confirming no text was applied to `book.md`).
