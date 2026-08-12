# Kashkole Wisdom corpus — English rendering: where it stands

**Last updated:** 2026-08-12, after the first full run stopped roughly halfway.
**Pending item:** `kashkole-urdu-to-english` in `_workspace/plan/pending-work.yaml` —
still OPEN, deliberately. Half a corpus is not a completed item.

---

## Where it stands

**47.7% done by work; 5.6% by topic count.** Both are true and the gap is the
whole story: the run takes the largest topics first, so the expensive material
is finished and what remains is a long tail of short topics.

| Measure | Done | Remaining |
|---|---|---|
| Source characters | **4,330,116 of 9,086,511 (47.7%)** | 4,756,395 |
| Topics | 76 of 1,347 | 1,271 |
| Topics with a substantial body (>200 chars) | 76 of 1,055 | 979 |
| English written | 4,345,900 characters | — |

Of the 76 rendered: **70 clean**, **6 flagged `review`** (topic ids 5702, 5708,
5715, 5726, 5740, 5766), each for exactly one Qur'anic verse that was rendered
into English instead of being carried through as Arabic script. Every giant is
finished, including the 312,374-character topic. The 76 done average ~57,000
characters each; the 1,271 remaining average ~3,700.

## How to pick it up

```
python3 scripts/podcast/intelligence/translate_kashkole.py --status
python3 scripts/podcast/intelligence/translate_kashkole.py --workers 5
```

The pass is **idempotent on `source_sha`**, so a re-run skips the 76 already
done and picks up exactly the 1,271 outstanding. A failed topic writes no row,
which is why `remaining` is honest after a crash. `--rescore` re-runs the
quality gates over stored renderings without translating anything — use it when
a gate is corrected, never re-translate to fix a verdict.

At the rate the first run held (~1.65M source characters/hour, 5 workers), the
remainder is roughly **2.5–3 hours** of wall clock.

## Why the first run stopped, and the three faults to fix first

The run rendered 76 topics over about three hours, then **every one of the
remaining 1,271 failed within minutes**: 1,233 reporting `claude -p rc=1` with
empty stderr, 37 naming a GitKraken `SessionEnd` hook. Sudden, uniform and
instant — consistent with the subscription's usage allowance being reached
rather than any fault in the corpus or the prompts. The CLI answered a probe
again shortly afterwards.

Nothing durable was lost. But the way it ended exposed three real defects in
`translate_kashkole.py`, and they should be fixed BEFORE the next run:

1. **No circuit breaker.** When calls began failing systematically the pass
   chewed through all 1,271 remaining topics in minutes, marking each failed,
   instead of halting after a handful of consecutive failures. A pause became a
   full-queue churn and a log that says nothing useful. *Fix: halt the pool
   after N consecutive failures and report how far it got.*
2. **No retry.** It calls `_run_claude_p` rather than
   `_run_claude_p_with_retry`, so a single slow window kills a topic with no
   second attempt. *Fix: use the retrying runner.*
3. **Storage is per-topic, not per-window.** A failure part-way through a long
   body discards every window already rendered — which is what cost topic 5786
   (243,806 characters) about twenty minutes of work. *Fix: persist windows as
   they complete so a resume restarts mid-topic.*

Topic 5786 is the one timeout failure and is still outstanding; it will be
retried automatically by any re-run.

## What the pass is, for whoever picks this up cold

- **Engine is `claude -p` on the flat-rate subscription.** The existing
  `tools/content_translator` is Azure Translator — literal, per-character, about
  **$91** for this corpus, and it produces the machine gloss that D8 exists to
  keep out of the atom store. This pass targets the reading editions' own
  articulation standard (`docs/standards/book-articulation.md`, REQ-BA-*), which
  is a judgement no phrase-level engine can make.
- **Output goes to `topic_translation`**, an ordinary table beside the FTS index
  rather than inside it. `fts_topics` is a virtual table whose columns are an
  index, not a record; English written there would be unversioned and destroyed
  by the next re-import.
- **Every row carries its own provenance** — source SHA, character counts,
  window count, model, prompt version, a hash of the standard it was written
  against, run id and timestamp — so a rendering can be traced to the exact Urdu
  it came from and revised when either end changes.
- **Long bodies are windowed** at 3,500 characters, split on paragraph then
  sentence boundaries, never mid-clause. Below 5,000 characters a body goes in
  one piece.
- **Two quality gates.** Output under 60% of source length is `short` (REQ-BA-100
  says a rendering is never shorter). A Qur'anic run in the source that is not
  present in the output is `review` — compared on the consonantal skeleton via
  `arabic_span_is_grounded`, because a raw substring test reported verses missing
  that were plainly there.
- **D8 is updated** in `intelligence/ingest_kashkole.py`, both in the module
  docstring and at the deferral site. The importer still mints no atoms from
  topics — that is a separate, unchanged decision about the atom store — but the
  reason is no longer "there is no usable English".

## Open questions for Asif

1. **`mirror.db` is a 33 MB tracked binary and this pass grows it.** Each commit
   stores a full new blob, so committing it after every translation run would add
   tens of megabytes per run to the repository. Committed once here because
   4.3M characters of rendered English must not live only on one disk. A durable
   answer is needed before the remaining 1,271 topics land.
2. **The six `review` topics need a decision**: repair the single missing verse
   in each surgically (the gate records exactly which verse in which topic), or
   re-render those topics with the verse quoted back in the prompt.
3. **The renderings are inert until something reads them.** Nothing queries
   `topic_translation` yet — wiring it into the corpus index and the Companion
   lane is separate, smaller work.
