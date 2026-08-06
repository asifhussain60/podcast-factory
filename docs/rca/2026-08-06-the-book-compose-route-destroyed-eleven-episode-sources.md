> Template from: Betsy Beyer, Chris Jones, Jennifer Petoff, and Niall Richard Murphy. [“Site Reliability Engineering.”](https://landing.google.com/sre/book/chapters/postmortem.html).

# The book compose route destroyed eleven episode sources, and the fix left them destroyed (RCA-010)

### Date

2026-08-06

### Authors

Claude (session: full repo audit), reported by `repo-surgeon`

### Status

Resolved. All eleven files restored; the eight files that replaced them removed; twelve red tests green.

### Summary

On 2026-07-16 the book-compose route wrote its per-chapter prose into
`content/Islamic/the-master-and-the-disciple/chapters/` — the **podcast** lane's
directory — and in doing so deleted eleven of that lane's twenty episode source
files. The collision mechanism was found and fixed three days later, on
2026-07-19. **The data was never restored.** The eleven files stayed deleted for
twenty-one days, during which twelve tests failed continuously on `develop` and
the failure was read as a known-red baseline rather than as missing content.

### Impact

Eleven episode source files — roughly 166 KB of authored, model-generated
narration framing, each the upload source for one NotebookLM episode — were
absent from the working tree for 21 days. Every byte was recoverable from git for
the whole period, so nothing was permanently lost and no shipped artifact
regressed: the twenty episodes had already been recorded and are live on the
Listener.

The real cost was the gate. Twelve tests were red on `develop` for three weeks —
eleven per-chapter regression baselines and one lane-separation test — which
means every other change landed during that window against a suite that was
already failing. A red suite that is expected to be red stops being a signal.

### Root Causes

Three, compounding:

1. **Two lanes shared one directory name with no ownership rule.** The podcast
   lane's episode sources and the book lane's chapter prose both wanted
   `chapters/`. Nothing declared which owned it, so a compose route could write
   there without doing anything it understood to be wrong.
2. **The two lanes' files are distinguishable only by a naming convention that
   nothing enforced.** Episode sources are `ch<NN><letter>-<title>.txt`; book
   prose is `ch<NN>-<title>.txt`. A writer that emitted the bare form landed
   *beside* the suffixed form rather than being rejected by it.
3. **The fix addressed the mechanism and not the damage.** Commit `79b20ad`
   stopped the collision. Stopping a process that deletes files does not undelete
   them, and nothing in the fix looked at what had already been lost.

### Trigger

Commit `69811c1` (2026-07-16 9:16 AM EST), `0book-compose — unified path (v2)`,
introduced the unified compose path that wrote into `chapters/`. Commit `1b59e09`
(2026-07-16 2:58 PM EST) is the commit in which the eleven deletions actually
appear.

### Resolution

All eleven files restored from `1b59e09^` — verified absent beforehand so the
restore could not overwrite newer work, and byte-identical to their last good
state.

The eight bare-numbered files that had been written into `chapters/` were then
examined rather than assumed to be debris. They were found to be **stale
duplicates**: `book/_chapters/` holds the same eight chapter titles at a *later*
compose stage (every one differs, and the book-lane copy is the further-processed
one). The podcast lane was independently confirmed complete without them — twenty
episode sources against twenty episodes. They were removed.

### Detection

Not detected by any gate. Found on 2026-08-06 by a `repo-surgeon` sweep run as
part of a general repo audit, twenty-one days after the deletion.

The twelve failing tests were, in fact, the detection — they fired immediately and
never stopped. They named the exact missing paths in their assertion messages. But
because they were failing continuously they had become the background state of the
suite rather than an alarm.

## Action Items

| Action | Type | Owner | Status |
|---|---|---|---|
| Restore the eleven deleted episode sources | mitigate | this session | done |
| Remove the eight stale book-prose duplicates from the podcast lane | mitigate | this session | done |
| `test_compose_lanes_distinct` already asserts every `chapters/` file carries narration framing — it is the correct guard and it worked | prevent | — | already in place |
| Decide a policy for a persistently-red suite on `develop`: a failure older than N days should escalate rather than normalize | prevent | Asif | open |
| Consider making the lane boundary structural rather than conventional — a book-lane write into `chapters/` should be impossible, not merely linted | prevent | Asif | open |

## Lessons Learned

### What went well

- Everything was in git. The blast radius of a content deletion in this repo is
  bounded by whether it was committed, and it was.
- `test_compose_lanes_distinct` is a genuinely good test: it detected the damage
  the moment it happened and described it accurately in plain language ("book
  prose copied over them?"). It did its job for three weeks.
- The eight replacement files were investigated before being deleted. They looked
  like obvious debris and were — but the check that proved it (comparing against
  `book/_chapters/` and confirming the podcast lane's own completeness) is what
  made deletion safe rather than lucky.

### What went wrong

- A fix was declared complete when the mechanism was fixed. The question "what did
  this already break?" was never asked.
- Twelve continuously-failing tests were treated as the status quo. The
  information needed to find this was on screen every time anyone ran the suite.

### Where we got lucky

- The eleven episodes had already been recorded before their sources were deleted.
  Had the deletion happened a week earlier, the recordings would not exist and the
  sources would have had to be re-authored at real model cost.
- The collision wrote *beside* the episode sources rather than *over* them for the
  nine that survived. A different naming overlap would have overwritten all twenty
  with book prose, and the restore would then have been a merge rather than a copy.

## Timeline

All times EST.

- **2026-07-16 9:16 AM** — `69811c1` introduces the unified book-compose path that
  writes into the podcast lane's `chapters/`.
- **2026-07-16 2:58 PM** — `1b59e09` lands; eleven episode sources are deleted and
  eight book-prose files appear in their place. Twelve tests go red.
- **2026-07-19 12:44 PM** — `79b20ad` stops the collision mechanism. The eleven
  files remain deleted; the twelve tests remain red.
- **2026-07-19 → 2026-08-06** — twenty-one days. The suite fails continuously.
- **2026-08-06** — `repo-surgeon` sweep identifies the deletion as the single root
  cause of all twelve failures and confirms every file recoverable from
  `1b59e09^`.
- **2026-08-06** — restored, duplicates removed, suite green.

## Supporting information

The eleven restored files:
`ch04a`, `ch08a`, `ch09b`, `ch10c`, `ch11d`, `ch14c`, `ch15d`, `ch16e`, `ch18b`,
`ch19c`, `ch20d`.

The eight removed duplicates: `ch01`–`ch08` (bare-numbered), superseded by
`content/Islamic/the-master-and-the-disciple/book/_chapters/` and recoverable from
git history.
