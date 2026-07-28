# Automated QA session deleted two Companion notes from a live book

### Date

2026-07-28

### Authors

Claude (session driver), with Asif as reviewer

### Status

Resolved — data restored (one verbatim, one regenerated), delete path now
confirmation-guarded, agent spec hardened.

### Summary

During an automated verification round for Scholar-panel UI changes, two of the
three Companion notes for *The Master and the Disciple* chapter 3 disappeared
from `_system/companion-notes/3-the-boy-at-the-door-limits-and-conditions.json`:
`4d9bc9db` ("But my mercy toward you…", committed) and `fa504bc8` ("It is
neither identical…", Asif's uncommitted note from earlier the same day). The
Composer's card delete was a single un-confirmed click at the time, hover-revealed
in the card corner, and both a human and any automated browser session could fire
it silently.

### Impact

- One committed note lost from the working tree (recoverable, and recovered,
  from git HEAD).
- One uncommitted, paid-generation note lost with no on-disk backup. ~90% of its
  body was recovered verbatim from QA screenshots the killed agent left behind
  (preserved in `assets/2026-07-28-companion-note-loss/`); the note was
  regenerated through the same grounded route against the same passage (new id
  `5de6a25d`). Wording differs from the original; the three etymology terms
  (حقيقة, ظاهر, باطن) were regenerated as four entries.
- No other chapter or book was touched (verified via `git diff` over
  `content/`).

### Root Causes

1. **A destructive control with no confirmation.** `.xpl-del` deleted a note on
   a single click, immediately and silently. Any stray click — human slip or
   automated pointer — was an irreversible data loss. (5 Whys bottom: the card
   component shipped its delete in the same pattern as its other buttons, and no
   gate distinguishes "control that navigates" from "control that destroys".)
2. **QA automation exercised real content.** The runtime-QA agent's contract
   said "never edits `content/`" — written as a *file-edit* rule. Its browser
   clicks mutate the same files through the running app's API, and that pathway
   was not covered by the rule.
3. **The note worth the most was the one never committed.** The working tree
   carried an hour-old human-initiated note with no durable copy anywhere.

### Trigger

Automated card-exercising (expand/collapse sweeps at two viewports, hover
states) over live cards whose corner carries the hover-revealed delete. No
explicit delete call appears in any transcript or generated script, so the
precise firing click was not conclusively identified; the killed agent's own
last observation ("only one of the two notes matched this run") shows it saw the
aftermath, not the act. `4d9bc9db` may alternatively have been deleted by a
human slip during the pre-session Studio session — same unguarded control,
same root cause either way.

### Resolution

- `4d9bc9db` restored verbatim from `git show HEAD:…`.
- `fa504bc8` regenerated as `5de6a25d` by driving the new selection→Explain flow
  over the identical passage (grounded, morphology-attached). Original body
  transcription and screenshots preserved beside this RCA.
- Both delete buttons (card and etymology entry) now route through
  `confirmDialog` — danger-styled, focus defaults to Cancel.
- `site-health-sentinel` spec extended: interaction-level prohibition on
  operating destructive or state-writing controls against real content.

### Detection

Human-adjacent: the driver noticed a verification script failing to find the
second card, then diffed the notes file against expectations. Nothing in the
pipeline or gates flagged the loss — the file is auto-generated-adjacent state
that no gate checksums.

## Action Items

| # | Action | Type | Status |
|---|---|---|---|
| 1 | Confirmation dialog on both Companion delete paths | prevent | DONE (this session) |
| 2 | Sentinel spec: never operate destructive/state-writing controls on real content; stop at confirmation dialogs and Cancel | prevent | DONE (this session, spec + regenerated wrappers) |
| 3 | Caller discipline: QA prompts that say "exercise the cards" must name the safe interactions (expand/collapse/hover) and forbid the rest | prevent | DONE (recorded here; applies to future agent prompts) |
| 4 | Commit companion-notes as part of session-end hygiene so human notes are never solely in the working tree | mitigate | APPROVED by Asif 2026-07-28 — standing rule (memory: companion-notes-commit-hygiene) |

## Lessons Learned

### What went well

The killed agent's un-cleaned screenshots turned out to be the only surviving
copy of the lost note's content — enough to recover ~90% verbatim and validate
the regeneration. Damage stayed confined to one file, verified by git.

### What went wrong

A destructive one-click control sat unguarded in a surface that both humans and
automation sweep. The file-edit framing of the content-safety rule missed the
API pathway entirely.

### Where we got lucky

The regeneration route (same passage, same grounding) exists and is cheap; the
committed note was one `git show` away; the QA agent was killed *before* its
cleanup step would have deleted the screenshots holding the only copy.

## Timeline (EST, 2026-07-28)

- ~12:00 PM — Asif generates the "It is neither identical…" note in his own
  Studio session (visible in his message's screenshot; file uncommitted).
- ~2:20 PM — Single-Explain-button change verified; a test note created and
  cleanly deleted by the driver; both real notes confirmed present after.
- ~3:21 PM — Deterministic gates green; round-2 QA agents launched.
- 3:39 PM — Killed agent's own probe logs both notes present on disk.
- ~3:41–3:48 PM — Agent's interactive probing window; note(s) lost in this
  span; agent notices "only one of the two notes matched".
- ~3:50 PM — Driver's verification script can't find the second card; file
  diff reveals the loss; agent stopped immediately.
- ~4:10 PM — Both notes restored (git + regeneration); confirm dialogs shipped;
  spec hardened; this RCA filed.

## Supporting information

- Evidence screenshots: `assets/2026-07-28-companion-note-loss/`
- Store code (synchronous single-process read-modify-write — server-side race
  ruled out): `plan-dashboard/src/lib/reader/companion/store.server.ts`
- Confirm dialog: `plan-dashboard/src/scripts/confirm-dialog.ts`, wired in
  `plan-dashboard/src/lib/reader/companion/explanation-card.ts`
