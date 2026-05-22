# Mac Studio prompt: merge `book/asaas-al-taveel` into `develop`

**Run it on the Mac Studio while on the `book/asaas-al-taveel` branch.**

Before pasting, run this one line in the Studio terminal to confirm:

```bash
cd /Users/ahmac/Code/podcast-factory/book-asaas && git checkout book/asaas-al-taveel && git status
```

(Adjust path if Studio's worktree is elsewhere. The branch must be `book/asaas-al-taveel` and the working tree clean.)

Then paste this entire block into the Studio's Claude Code session:

---

```
You are running on the Mac Studio (primary machine, machine_id `mac-studio-primary`). Your job is to safely merge the `book/asaas-al-taveel` branch into `develop`. The Mac Air (secondary) just merged `book/kitab-al-riyad` into `develop` (commit e122fa0 on origin/develop) and pushed it. Your merge is the symmetric operation for your branch.

BEFORE YOU DO ANYTHING ELSE, READ THESE TWO FILES:

1. `_workspace/plan/response-conventions.md` — the cross-machine response-format conventions. Every response you give Asif from this session must follow the BLUF format (TL;DR, Status emoji, structured body, Your next step) defined there. The conventions also cover AskUserQuestion ordering (recommended first), the halt-and-surface pattern, file/commit linking, and cross-machine awareness. THESE CONVENTIONS ARE NON-NEGOTIABLE. The Air session uses them; you use them; we stay in sync.

2. `_workspace/plan/operators/mac-studio-primary.md` — your operator file. The Air updated it on 2026-05-21 with a one-time write exception (explicitly authorized by Asif). The frontmatter describes your current state, your next action, and the broader cross-machine context. Use it as your starting situational awareness.

CONTEXT YOU MUST KNOW BEFORE TOUCHING ANY GIT STATE:

1. `develop` is now AHEAD of where you last saw it. It contains all 36 commits from book/kitab-al-riyad including framework upgrades to scripts/podcast/_authoring.py (Phase 0d prompt now classifies episode_format + essential), scripts/podcast/orchestrate_book.py (Phase 0f template surfaces those fields), skills-staging/podcast/SKILL.md (schema docs), a new helper at scripts/podcast/normalize_double_parens.py, and this very prompt + the response-conventions file.

2. Three commits on your book/asaas-al-taveel branch have already landed on develop via cherry-picks the Air made on day 1. These three:
     - 5201b54  podcast(P22.markers): fix Phase 0b page-marker stripping defect
     - 0844e1e  coord(macbook-air-secondary): unblock Air for KaR Phase 0e + P22.markers prereq
     - 5dae77c  coord(macbook-air-secondary): amend §4.2 — also cherry-pick this coord commit
   When you merge book/asaas-al-taveel into develop, git's patch identity should dedup these — they'll appear in the merge commit's history but contribute no diff. Do NOT try to rebase them away or revert them; the merge handles it.

3. There WILL be a conflict on `_workspace/plan/operators/macbook-air-secondary.md`. The Air's session has the canonical view of its own operator file now on develop (status_tag: HALTED-AT-0F-AWAITING-0G-GO, current_phase: 0f). Your branch likely has older state on that file. RESOLUTION: take develop's version of that file (the Air-side fields). The Air owns its own operator-doc updates per coordination-protocol.md §1.

4. There MAY also be a conflict on `_workspace/plan/operators/mac-studio-primary.md`. The Air wrote your file on 2026-05-21 (one-time exception). If you have local edits on your branch that conflict, RESOLUTION: take YOUR branch's version (your own self-report wins on any field describing your machine's state). Then re-apply the cross-machine sync notes from the Air's 2026-05-21 version manually.

EXECUTE THESE GATES IN ORDER. Halt and surface to Asif at any RED gate.

──────────────────────────────────────────────────────────────────────
GATE 0 — Read conventions + operator file (no writes)

  cat _workspace/plan/response-conventions.md       # absorb the BLUF format
  cat _workspace/plan/operators/mac-studio-primary.md  # absorb your own state

After this, every response you give Asif uses the BLUF format. No long paragraphs without the TL;DR / Status / Body / Your next step structure.

──────────────────────────────────────────────────────────────────────
GATE 1 — Survey + sync remote on ALL branches you'll touch (no writes that modify history)

  git fetch --all --prune
  git rev-parse --abbrev-ref HEAD                          # confirm: book/asaas-al-taveel
  git status --porcelain                                   # confirm: clean working tree
  ps aux | grep orchestrate_book | grep -v grep            # confirm: no orchestrator running

  # Sync your own book branch from remote (catch any push you forgot you did)
  git pull --ff-only origin book/asaas-al-taveel

  # Sync develop locally from remote (it just moved due to the Air's merge)
  git fetch origin develop:refs/remotes/origin/develop

  # Report counts
  git rev-list --count origin/develop..origin/book/asaas-al-taveel    # commits ahead
  git rev-list --count origin/book/asaas-al-taveel..origin/develop    # commits behind

If working tree is dirty OR orchestrator is running OR `git pull` is non-fast-forward (meaning your local has commits not on remote — surface them first), HALT and tell Asif. Do not proceed.

──────────────────────────────────────────────────────────────────────
GATE 2 — Dry-run merge for conflict surface (no writes that persist)

  git checkout develop
  git pull --ff-only origin develop
  git merge --no-commit --no-ff origin/book/asaas-al-taveel
  git status | head -30                                    # see conflict files
  git merge --abort
  git checkout book/asaas-al-taveel

Expected conflicts: `_workspace/plan/operators/macbook-air-secondary.md` (always)
and possibly `_workspace/plan/operators/mac-studio-primary.md`. Any conflict on
OTHER files (especially scripts/podcast/*, content/podcast/library/books/asaas-al-taveel/*,
or content/podcast/.skill/*) is unexpected — HALT and surface the full conflict
list. Do NOT proceed without Asif's decision on those.

──────────────────────────────────────────────────────────────────────
GATE 3 — Execute the merge

  git checkout develop
  git merge --no-ff origin/book/asaas-al-taveel -m "merge book/asaas-al-taveel into develop — Studio's Phase 0a-0b work + framework cherry-picks

Integrates the Studio session's completed work on asaas-al-taveel:

BOOK CONTENT (asaas):
- Phase 0a Azure ingest (with retry handling for transient Translator failures)
- Phase 0b English refinement (chunked) with operator transcript review
  cleared at the P22 gate

FRAMEWORK (already on develop via KaR cherry-picks, dedup expected):
- P22.markers fix (5201b54): Phase 0b page-marker preservation
- Two coord-doc commits for the Air's operator-file updates

COORD:
- mac-studio-primary.md — taking Studio's branch version on any field
  describing Studio's own state (Studio owns this file); cross-machine sync
  notes from develop manually re-applied

CONFLICT RESOLUTION:
- _workspace/plan/operators/macbook-air-secondary.md — taking develop's
  version. Air owns this file per coordination-protocol.md §1.
- _workspace/plan/operators/mac-studio-primary.md — taking ours (book/asaas-al-taveel)
  for Studio-state fields; re-applying the 2026-05-21 cross-machine sync notes
  written by the Air on develop."

  # When the merge stops at conflicts:
  git checkout --theirs _workspace/plan/operators/macbook-air-secondary.md
  git add _workspace/plan/operators/macbook-air-secondary.md

  # For the Studio's own file (only if it conflicts):
  git checkout --ours _workspace/plan/operators/mac-studio-primary.md
  # IMPORTANT: now manually re-apply the cross-machine sync notes the Air wrote.
  # Look at the develop version: git show origin/develop:_workspace/plan/operators/mac-studio-primary.md
  # Copy the WRITE EXCEPTION block + the response_conventions field + any
  # next_action updates that reference the merge prompt path.
  # Then: git add _workspace/plan/operators/mac-studio-primary.md

  git commit --no-edit

──────────────────────────────────────────────────────────────────────
GATE 4 — Verify (RED if anything fails)

  python3 -m unittest scripts.podcast.tests.test_phase_0b_preserves_page_markers scripts.podcast.tests.test_audit_page_markers 2>&1 | tail -3
  # Expect: Ran 30 tests, OK

  python3 -c "
  import sys; sys.path.insert(0, 'scripts/podcast')
  from orchestrate_book import phase_0f_write_series_plan
  print('  0f template imports cleanly')
  "
  # Expect: no traceback

If either fails, HALT. The merge has not been pushed yet — `git reset --hard origin/develop` will undo it cleanly. Surface failure details to Asif before retrying.

──────────────────────────────────────────────────────────────────────
GATE 5 — Push develop

  git push origin develop

If push is rejected (non-fast-forward), it means develop moved between your fetch and your push — the Air or someone else pushed in the meantime. HALT and surface. DO NOT force-push.

──────────────────────────────────────────────────────────────────────
GATE 6 — Return to your branch + update YOUR operator file

  git checkout book/asaas-al-taveel

  # Pull develop into your branch so book/asaas-al-taveel is fresh
  # (this brings the cross-machine sync notes + KaR's framework upgrades
  # onto your branch so future asaas work uses them):
  git merge --no-ff origin/develop -m "merge develop into book/asaas-al-taveel — pick up Air's framework upgrades + cross-machine sync"

  # Now update your operator file frontmatter to remove the WRITE EXCEPTION note
  # and write a fresh status entry from YOUR observed state.
  # Specifically update macbook frontmatter fields:
  #   status_tag: <your current state — e.g., RESUMING-PHASE-0C>
  #   current_phase: <your current phase>
  #   current_phase_status_summary: <2-3 sentences from YOUR view>
  #   next_action: <YOUR next action — likely Phase 0c on asaas>
  #   last_verified_at: <now UTC>
  #   last_updated: <today>
  # Remove the WRITE EXCEPTION block. Keep response_conventions field.

  git add _workspace/plan/operators/mac-studio-primary.md
  git commit -m "coord(mac-studio-primary): re-assert ownership after Air's 2026-05-21 write exception + record post-merge state"
  git push origin book/asaas-al-taveel

──────────────────────────────────────────────────────────────────────
HANDOFF

When done, report to Asif using the BLUF format from response-conventions.md:

  **TL;DR:** asaas-al-taveel merged into develop, cherry-pick dedups confirmed clean, tests pass, Studio's operator file re-asserted.
  **Status:** 🟢 ship-ready
  [optional Body if there are notable issues to surface]
  **Your next step:** resume Phase 0c on asaas-al-taveel — `python3 scripts/podcast/orchestrate_book.py --resume asaas-al-taveel`

If any gate halts, report:

  **TL;DR:** asaas merge halted at gate N.
  **Status:** 🟡 needs your decision
  **What happened:** <verbatim error or unexpected condition>
  **Proposed next step:** <what you'd do; ask for approval>
```

---

## Quick reference for Asif

- The prompt loads response-conventions + operator-file at GATE 0 so Studio's session immediately adopts the same BLUF format the Air uses.
- The prompt pulls from remote on BOTH the book branch and develop (Gate 1) so Studio doesn't merge stale state.
- GATE 6 explicitly walks Studio through re-asserting ownership of mac-studio-primary.md (the Air wrote it as a one-time exception).
- After Studio runs this and reports green, both books are integrated on `develop`, Studio's operator file is back under Studio's ownership, and Studio can continue Phase 0c on asaas.
- If Studio reports a halt at any gate, the BLUF format makes it easy to see what's needed and what to authorize.
