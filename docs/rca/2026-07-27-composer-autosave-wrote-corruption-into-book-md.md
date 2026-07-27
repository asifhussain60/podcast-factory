# Composer autosave wrote four corruptions into a publication-bound book.md (RCA-002)

### Date

2026-07-27 (incident window: 2026-07-26 3:16 PM EST → 2026-07-27 9:05 AM EST)

### Authors

Claude (investigation + forensics), reviewed by Asif

### Status

RESOLVED 2026-07-27 — both files restored to HEAD, all four corruptions
verified absent, working tree clean. Corrective actions AI-1 … AI-5 open.

### Template

Google SRE postmortem format (Beyer/Jones/Petoff/Murphy, *Site Reliability
Engineering*), via [dastergon/postmortem-templates](https://github.com/dastergon/postmortem-templates).
Analysis pattern: blameless postmortem + 5 Whys + contributing-cause categories.

### Summary

Two Book Composer autosaves on the evening of 2026-07-26 — made during a
session whose subject was CSS and companion cards, not book content — wrote
four distinct corruptions into `the-master-and-the-disciple`'s reading edition
and froze two of them as durable "human-authored" Composer edits. The damage
sat uncommitted in the working tree for roughly eighteen hours with a dev
server still running against it, and was found at the start of the next
session by reading the diff, not by any gate.

This is the second incident in the same class as RCA-001: a Composer save
persisting text nobody authored into a publication-bound file. RCA-001's fix
hardened what the *pipeline* does with a Composer edit; it did not change what
a Composer *save* is permitted to write.

### Impact

- Four corruptions in a publication-bound edition, two of them frozen into
  `_system/composer-edits.json` — which, per the locked Composer-authority
  rule, means the pipeline would have passed those chapters through untouched
  on every subsequent compose.
- One near-miss already in history: commit `bff3680`, whose subject is
  "centre the formatting row, give controls a brown outline", carries three
  `content/` files. That commit's own message asserts "content/ checked
  dirty-count 0 before and after the run."
- No paid model work was lost. No published artifact shipped the damage — the
  PDF was not re-rendered in the window.

The four corruptions:

| Where | Damage |
|---|---|
| Introduction | Entire edition introduction stacked **three times**; `edition-intro` fence count 1 → 3 in both `book.md` and the sidecar. Frozen intro body 4,417 → 8,597 bytes. |
| `book.md:37` | "The Master here **is is** a teacher figure" — stray duplicated word. |
| `book.md:109` | Clause transposition: "grown dear to **your fellowship and us** has become sweet to us", from "dear to **us** and **your fellowship** has become sweet to us". |
| `book.md:124` | Nested editorial-note blockquote collapsed 10 lines → 1, leaving the inner `>` marker to render as literal text mid-paragraph. |

Nothing in the eighteen-hour delta was authored content. Every added line was
a duplicate, a corruption, or a reflow.

### Root Causes

1. **Autosave persists the whole document on any editor event, with no
   comparison against what was seeded (design).** `book-composer.ts:1176`
   wires `editor.on("update") → markDirty()`, and the save body is
   `activeEditor.toMarkdown()` — the entire chapter, unconditionally. There is
   no diff against the seed and no no-op guard. A single stray keystroke or an
   accidental pointer-drag therefore rewrites the whole chapter, and any
   round-trip drift in the untouched 99% is written along with it.

2. **The seed/serialize round trip is known to be lossy, and autosave was
   built on top of it anyway (design).** The site-work status file already
   records that round-tripping every chapter of all four books is not
   byte-exact on real content — multi-line quotes get joined, ayah-separator
   spacing is lost. `book.md:124` is exactly that defect. A lossy serializer
   is survivable behind an explicit Save the human reviews; behind a
   1.2-second debounce it is a corruption pump.

3. **The `edition-intro` guard is documented as dormant on this book
   (change management).** The 2026-07-22 fix refuses to enumerate a chapter
   whose heading sits inside the fence span. This book's front matter is
   hand-split — the heading sits *above* the fence — so its introduction
   remains an editable chapter carrying machine fences that the edit seed
   deliberately preserves (`keepMachineFences`). The fix was landed knowing it
   would not cover this book, and nothing else was put in its place.

4. **No gate watches `content/` cleanliness at commit time (detection).**
   `book-challenger` reads composed state, `book-render-challenger` reads the
   PDF, `smoke` and `lint:views` read the site. None of them look at whether
   a site-work session has left the content tree dirty. That is how three
   content files rode into a CSS commit under a message asserting the
   opposite, and how the remaining two stayed dirty across five subsequent
   commits without comment.

5. **Nothing bounds an editor session's blast radius to the book being
   edited (process).** The dev server ran for hours during work whose subject
   was companion cards and toolbar CSS. A Composer route open in a background
   tab is indistinguishable, to the system, from deliberate authoring.

### Trigger

A Composer surface open against `the-master-and-the-disciple` during a CSS and
companion-card session. Two chapters received editor `update` events —
consistent with an accidental pointer-drag inside the prose (`book.md:109`'s
transposition) and a stray keystroke (`book.md:37`) — each of which armed the
debounce and persisted the full serialized chapter.

The tripling mechanism was not reproduced: the corrupt state was captured as
evidence and then reverted rather than re-run. AI-2 covers reproducing it.

### Resolution

Dev server stopped first so its autosave could not race the restore, then
`git restore` of both files to HEAD. Verified after: `edition-intro` fences
back to 1, zero hits for "is is a teacher" and the transposed clause, the
correct clause present once, six Composer edits with the introduction back at
4,417 bytes, working tree clean.

Forensic evidence (both diffs plus the corrupt sidecar) captured before the
revert and retained for AI-2.

The vowelling change in `bff3680` was checked and **kept** — it applies an
approved entry from `_system/vowelling-proposals.json` (non-Quranic line,
`status: applied`, 21 marks). Only the commit hygiene was wrong, not the
content.

### Detection

Found by reading `git diff` at session start, roughly eighteen hours after the
first corrupting save. Every automated gate in the repo was green or
inapplicable throughout. Detection latency was bounded only by when a human
next looked at the diff — had the next session begun with a commit rather than
a review, the damage would have entered history.

## Action Items

| ID | Action | Type | Owner | Status |
|---|---|---|---|---|
| AI-1 | Autosave must no-op when the serialized document is byte-identical to the seed, and must diff against the seed rather than persisting unconditionally. Closes the corruption pump at its source. | Fix | Claude | Open |
| AI-2 | Reproduce the `edition-intro` tripling from the retained evidence, then fix the surgical section replace so a fenced, hand-split introduction cannot be re-nested. | Fix | Claude | Open |
| AI-3 | Add a pre-commit gate that refuses a commit touching `plan-dashboard/` while `content/` is dirty, unless the content change is named in the commit message. Directly prevents the `bff3680` sweep. | Gate | Claude | Open |
| AI-4 | Make the known round-trip losses (multi-line quote joining, ayah-separator spacing) either fixed or blocking, rather than recorded in a status file. A documented lossy serializer behind an autosave is an accepted risk that this incident shows is not acceptable. | Fix | Claude | Open |
| AI-5 | Session hygiene: stop the dev server at end of any site-work session, or make the Composer route refuse to autosave a book that the session never opened deliberately. | Process | Asif + Claude | Open |

## Lessons Learned

### What went well

- The evidence survived. Capturing both diffs and the corrupt sidecar before
  reverting means AI-2 can reproduce the tripling without re-corrupting a book.
- The vowelling change was checked rather than assumed guilty. A blanket
  revert of everything touched that evening would have discarded an approved,
  correctly-applied review decision.
- The corruption was structurally obvious once read — a tripled section and a
  transposed clause are not subtle. The problem was that nothing read it.

### What went wrong

- RCA-001's corrective actions all pointed downstream, at what the pipeline
  does with a Composer edit. The Composer's own write path — the thing that
  produced the bad data in both incidents — was never constrained.
- A known-lossy round trip was left in production behind an autosave, recorded
  as a status-file observation rather than tracked as a defect.
- A guard was landed with a documented gap on the very book most actively
  being edited, and the gap was never closed or tracked.

### Where we got lucky

- The PDF was not re-rendered during the eighteen-hour window, so no published
  artifact carried the damage.
- The next session opened with a review rather than a commit. There is no
  mechanism that made this so — it is the only reason the corruption did not
  enter history.
- The transposition landed in an ordinary narrative clause. The same accident
  inside an Arabic quotation or a Quranic citation would have been far harder
  to spot and far more serious.

## Timeline

All times EST, reconstructed from git and `_system/` ledger timestamps.

| Time | Event |
|---|---|
| 2026-07-26 3:16:47 PM | Vowelling proposal for ch3 decided `accepted` |
| 2026-07-26 3:16:52 PM | Introduction vowelling proposal decided `accepted` (never applied) |
| 2026-07-26 3:16:56 PM | Ch1 vowelling proposal decided `applied`; Composer edit for "the persian who was dead and revived" saved |
| 2026-07-26 3:17:01 PM | Commit `bff3680` — CSS subject, sweeps `book.md`, `composer-edits.json`, `vowelling-proposals.json` |
| 2026-07-26 3:44:53 PM | Composer save on the introduction — body 4,417 → 8,597 bytes, fences 1 → 3 |
| 2026-07-26 3:57:43 PM | Composer save on "a stranger in the city" — transposition + blockquote collapse |
| 2026-07-26 evening | Five further commits (companion-card work); content files stay dirty, uncommented |
| 2026-07-27 9:05 AM | Corruption found by reading the diff at session start |
| 2026-07-27 9:14 AM | Evidence captured; dev server stopped; both files restored; clean tree verified |

## Supporting information

- Corrupting saves: `_system/composer-edits.json` entries timestamped
  `2026-07-26T19:44:53.158Z` and `2026-07-26T19:57:43.820Z`.
- Autosave wiring: `plan-dashboard/src/scripts/book-composer.ts:1126-1177`.
- Related: [RCA-001](2026-07-22-composer-snapshots-froze-unarticulated-prose.md)
  — same class, upstream of this one.
