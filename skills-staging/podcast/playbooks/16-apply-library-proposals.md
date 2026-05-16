# Stage 16 — Apply Library Proposals

**Purpose:** The explicit, user-initiated merge of staging proposals into live journal libraries. Invoked via `/podcast apply <source-slug>`. This is the only stage that writes to live library files.

## Trigger

User runs `/podcast apply <source-slug>` from Cowork. The skill loads `JOURNAL_DIR/_workspace/podcast/<source-slug>/06-library-proposals.md`.

## Pre-flight checks (all must pass)

### Check 1: Proposals file exists

Verify `WORK_DIR/06-library-proposals.md` exists. If not, report:
```
No proposals file found at [WORK_DIR]/06-library-proposals.md.
This source-slug has no library proposals to apply.
```

### Check 2: Proposals file has not been corrupted

Verify the file still parses per the canonical format (Sections A, B, C with the expected entry structure). If parsing fails:
```
Cannot parse proposals file. Last successful parse was [date]. 
Manual edits may have broken the structure. To proceed:
  – Revert manual edits, OR
  – Re-run `/podcast <slug>` to regenerate the proposals file.
```

### Check 3: Quality gates passed

Verify `WORK_DIR/_quality-gates-report.md` exists and reports `Overall: PASS`. If gates didn't pass:
```
Quality gates did not pass for this podcast run. Apply is blocked.
See [WORK_DIR]/_quality-gates-report.md for details.
Re-run the pipeline after fixing the gate failures.
```

### Check 4: Regression guard — no uncommitted changes in target libraries

For each Tier 1 file (`quotes-library.txt`, `clinic-library.txt`, `translations-glossary.md`):

Run `git status --porcelain` against the file. If uncommitted changes exist:
```
[file] has uncommitted changes. Apply is blocked.
Commit or stash your changes first:
  cd [JOURNAL_DIR]
  git add reference/[file]
  git commit -m "wip: your description"
Then re-run /podcast apply [source-slug].
```

This prevents the apply step from clobbering hand-edits in flight.

### Check 5: Target libraries exist

Verify each target library file is readable. If not, halt and report.

## Diff generation

For each proposal section (A: quotes, B: clinic, C: glossary):

### Step 1: Build proposed file content

For each proposal in the section:
- Generate the entry as it will appear in the target library (per the library's existing format).
- Determine insertion location (under correct theme/category heading, alphabetical sort if applicable).
- Append the provenance footer.

Compose the would-be new content of the library file.

### Step 2: Compute unified diff

```
git diff --no-index [current target library] [proposed target library]
```

Or equivalent in-memory diff if files are loaded.

### Step 3: Present to user

Write to a temporary review file: `WORK_DIR/_apply-review.md`:

```markdown
# Apply Review — [source-slug]

## quotes-library.txt — [N] proposals

Per-proposal diffs:

### Q-001
[Per-proposal diff showing exactly what would be added]
Decision: [ACCEPT | REJECT]  ← user edits this

### Q-002
[diff]
Decision: [ACCEPT | REJECT]

...

## clinic-library.txt — [N] proposals

### C-001
[diff]
Decision: [ACCEPT | REJECT]

...

## translations-glossary.md — [N] proposals

### G-001
[diff]
Decision: [ACCEPT | REJECT]

...

---

## Bulk decision shortcuts

To accept all: set `BULK_DECISION: accept_all` at the top of this file.
To reject all: set `BULK_DECISION: reject_all`.
To accept all of one type: set `BULK_DECISION: accept_quotes_only` (or `_clinic_only`, `_glossary_only`).
To make per-proposal decisions: edit each `Decision:` line above.

When ready, save this file and run:
    /podcast apply [source-slug] continue

The skill will read your decisions and proceed.
```

Pause and wait for user.

## Resume after user decision

User runs `/podcast apply [source-slug] continue`. Skill reads `_apply-review.md`:

### Step 4: Parse decisions

Read every `Decision:` line and any `BULK_DECISION:` line. Bulk decisions override per-proposal decisions for the matching type.

### Step 5: Apply accepted proposals

For each accepted proposal:
- Open the target library file.
- Insert the entry at the determined location with the provenance footer.
- Re-validate the file format (still parses correctly, no broken markdown tables, etc.).

If any target file becomes invalid after applying its proposals, revert that file to its pre-apply state and report which proposal caused the failure.

### Step 6: Run journal-side quality gates

After all applies complete, run the journal repo's own quality gates (the `validate-workflow-state.mjs` runtime validator if active; otherwise spot checks):
- Translations glossary still parses.
- Quotes library still parses.
- Clinic library still parses.
- No duplicate phonetic spellings in master lexicon.
- All provenance footers present.

If any check fails, revert the just-applied changes and report.

### Step 7: Commit

If all checks pass:

```bash
cd [JOURNAL_DIR]
git add reference/quotes-library.txt    # if changed
git add reference/clinic-library.txt    # if changed
git add reference/translations-glossary.md  # if changed
git commit -m "podcast: apply [N] proposals from [source-slug]

[breakdown by file with counts]
[brief description]"
```

The commit message includes:
- The source-slug.
- The number of proposals applied per file.
- A reference back to the WORK_DIR for full traceability.

Example commit message (placeholders bracketed):

```
podcast: apply [N] proposals from [source-slug]

Files changed:
  reference/quotes-library.txt: +[N] entries (themes: [list])
  reference/clinic-library.txt: +[N] entries
  reference/translations-glossary.md: +[N] phonetic terms

Source: [Detected Title] by [Detected Author]
        (trans. [Translator] if applicable)
Detected tradition: [tradition name or "none"]
Podcast run: [YYYY-MM-DD]
Full work dir: _workspace/podcast/[source-slug]/

Proposals not applied (kept as borderline or rejected):
  [list of proposal IDs]
```

### Step 8: Console summary

```
================================================
/podcast apply complete — [source-slug]
================================================

Decisions:
  Accepted: [N] / [Total]
  Rejected: [N]
  
Applied to libraries:
  quotes-library.txt:        +[N] entries
  clinic-library.txt:        +[N] entries
  translations-glossary.md:  +[N] terms

Journal quality gates: PASS
Committed as: [commit SHA]

Rejected proposals remain in [WORK_DIR]/06-library-proposals.md
(marked Decision: REJECT). You can edit and re-apply later.

================================================
```

## Failure modes and recovery

| Failure | Recovery |
|---|---|
| Pre-flight check fails | Report, halt, no changes made |
| User edits break review file | Report parse error, ask user to fix |
| Apply makes a library file invalid | Revert that file, report which proposal broke it |
| Journal quality gates fail | Revert all applied changes, report |
| Git commit fails (e.g., hooks reject) | Files remain modified but uncommitted; report hook output |

In every failure case, the libraries are left either in their pre-apply state (no partial changes) or in a state where the user can complete the work manually (with clear breadcrumbs).

## Multi-source apply

If the user wants to apply proposals from multiple source-slugs at once:
- Run `/podcast apply <slug-1>` first, complete it.
- Then `/podcast apply <slug-2>`, complete it.
- Each apply is its own commit. Atomic per source.

This deliberately prevents bulk applies — every commit traces to one source.

## What this stage does NOT do

- Does not modify the podcast outputs (`01-refined/`, `02-instructions/`, etc.).
- Does not delete `06-library-proposals.md` after apply — rejected proposals stay there for future review.
- Does not auto-discover proposals across all WORK_DIRs — user must specify which source-slug.
