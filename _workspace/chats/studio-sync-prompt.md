# Mac Studio sync prompt — v3 (2026-05-21)

Paste the block below into the Mac Studio's **Claude Code session in VSCode**.
The session figures out paths, syncs from remote with hang detection, reads
new coord docs, and reports back in BLUF format. No terminal commands
needed up front.

---

```
You are the Mac Studio Claude Code session (machine_id: mac-studio-primary). The Air session shipped coordination updates to develop on 2026-05-21. develop HEAD as of this prompt: 774b002. Your job: sync up, read the new conventions, refresh your operator file + dashboard column, and report back. Do NOT start any LLM-spending work on asaas until Asif explicitly authorizes — Air is also paused.

EXECUTE THESE GATES IN ORDER. Halt and surface at any RED gate using BLUF format (TL;DR / Status / Body blocks or table / Your next step — NO custom section labels).

──────────────────────────────────────────────────────────────────────
GATE 1 — Find the Studio's journal repo

Asif's prior terminal attempt hung; we don't know the exact path. Run:

  echo "▸ search 1: ~/Code/"
  ls ~/Code/ 2>&1 | grep -iE "journal|Journal" || echo "  (none)"
  echo ""
  echo "▸ search 2: ~/PROJECTS/"
  ls ~/PROJECTS/ 2>&1 | grep -iE "journal|Journal" || echo "  (none)"
  echo ""
  echo "▸ search 3: any journal git repo under ~"
  for d in $(find ~ -maxdepth 5 -name ".git" 2>/dev/null | head -20 | xargs -I {} dirname {} 2>/dev/null); do
    if echo "$d" | grep -iqE "journal|Journal"; then
      cd "$d" 2>/dev/null && echo "  $d  →  branch $(git rev-parse --abbrev-ref HEAD 2>/dev/null)"
      cd ~
    fi
  done

If multiple journal-* folders show up, they're git worktrees of the SAME repo (one .git database, multiple working dirs). Pick the one whose current branch is `book/asaas-al-taveel`. Set REPO=<that path>.

If you find a journal-feat (or similar) worktree on a dormant branch (0 commits ahead of develop), DO NOT use it — and at the end of this prompt, prune it per GATE 9 below.

If no journal repo resolves, HALT and ask Asif for the path.

──────────────────────────────────────────────────────────────────────
GATE 2 — Pre-flight

  cd "$REPO"
  pwd
  git rev-parse --abbrev-ref HEAD    # expected: book/asaas-al-taveel
  git status --porcelain             # expected: empty (clean tree)
  ps aux | grep orchestrate_book | grep -v grep || echo "  no orchestrator running ✓"
  cat ~/.machine-id 2>/dev/null || { echo "▸ creating ~/.machine-id"; echo mac-studio-primary > ~/.machine-id; cat ~/.machine-id; }

If the working tree is dirty: HALT and surface the dirty files. Asif decides whether to commit or stash.
If you're on a wrong branch: HALT.

──────────────────────────────────────────────────────────────────────
GATE 2.5 — Auth check (only if a git fetch hangs in the next gate)

If a fetch hangs longer than 30 seconds in GATE 3:

  ssh -T git@github.com 2>&1 | head -3
  # Expect: "Hi <user>! You've successfully authenticated"
  # If "Permission denied" or hangs: HALT. The SSH key isn't unlocked.
  #   Asif fixes via:  ssh-add ~/.ssh/id_rsa     (or the relevant key)
  #   Then re-run from GATE 3.

──────────────────────────────────────────────────────────────────────
GATE 3 — Sync develop (and your branch) from remote, with timeouts

  cd "$REPO"
  timeout 60 git fetch --all --prune

  # Pull develop's updates into local
  git checkout develop
  timeout 30 git pull --ff-only origin develop
  echo "▸ develop @ $(git rev-parse --short HEAD) — $(git log -1 --format=%s | head -c 80)"

  # Pull develop into your book branch so you have the latest framework + coord docs
  git checkout book/asaas-al-taveel
  timeout 30 git pull --ff-only origin book/asaas-al-taveel
  git merge --no-ff origin/develop -m "merge develop → book/asaas-al-taveel — pick up coord-doc cleanup + worktree clarification (2026-05-21)"

If merge succeeds clean: proceed to GATE 4.

If conflicts surface:
  - Expected conflict: _workspace/plan/operators/mac-studio-primary.md
    Resolution: take YOUR branch's view on Studio-state frontmatter fields (status_tag, current_phase, current_phase_status_summary, next_action). Re-apply ONLY the `response_conventions:` reference and any cross-machine sync notes from develop's body that aren't about Studio's state.
  - Any OTHER conflict: HALT and surface the full list. Do NOT auto-resolve.

  git add <resolved files>
  git commit --no-edit

Then push:

  timeout 30 git push origin book/asaas-al-taveel

──────────────────────────────────────────────────────────────────────
GATE 4 — Run the session-starter (single command that does it all)

  bash _workspace/plan/operators/start-session.sh

Expected output (verbatim shape):
  ▸ machine: mac-studio-primary
  ▸ starting branch: book/asaas-al-taveel
  ▸ syncing develop from remote...
    develop @ 774b002
  ▸ assignment from _workspace/plan/operators/mac-studio-primary.md:
      branch:     book/asaas-al-taveel
      book:       asaas-al-taveel
      status_tag: <whatever the file says>
      phase:      <whatever the file says>
  ▸ switching to book/asaas-al-taveel...
    now on: book/asaas-al-taveel @ <hash>
  ▸ orchestrator state: phase: 0c / <status>, last_completed: 0b, last_error: null
  ▸ next_action: ...
  ▸ ready.

If exit 1 (pre-flight failed): debug the cause shown.
If exit 2 (IDLE): unexpected — should be in-flight on asaas. HALT.

──────────────────────────────────────────────────────────────────────
GATE 5 — Absorb the new coordination docs (read all, no edits yet)

  cat _workspace/README.md
  cat _workspace/plan/operators/README.md
  cat _workspace/plan/operators/index.md
  cat _workspace/plan/book-queue.md
  cat _workspace/plan/response-conventions.md
  cat _workspace/plan/operators/coordination-protocol.md
  cat _workspace/plan/operators/mac-studio-primary.md

Critical takeaways:
- ONE git repo per machine, ONE working directory per machine. Books are processed on branches (book/<slug>), not in separate folders. Avoid git worktrees unless you have a clear reason — they create visual sprawl.
- Pull-on-demand work queue at _workspace/plan/book-queue.md. Mutex via git push-rejection.
- BLUF response format: TL;DR / Status emoji / Body with per-issue blocks (### N. <name> + Plain English / Impact / Fix / Where) OR tables / Your next step. NO custom section labels like "Deviation from plan", "Verification", "Coord doc", "Next per machine roadmap".
- Coordination protocol v2: §14 concurrency models, §15 WRITE EXCEPTION protocol.

──────────────────────────────────────────────────────────────────────
GATE 6 — Re-assert ownership of mac-studio-primary.md (if WRITE EXCEPTION still applies)

Open _workspace/plan/operators/mac-studio-primary.md. If the frontmatter still has a `written_by: macbook-air-secondary (one-time exception...)` field OR the body still has a `> ⚠️ **WRITE EXCEPTION — 2026-05-21 (Air-authored)**` blockquote, do the following:

1. Refresh frontmatter from YOUR observed reality:
   - last_verified_at: now (ISO 8601 UTC)
   - last_updated: 2026-05-21
   - status_tag, current_phase, current_phase_status_summary, next_action: from your asaas state.json + your understanding of next step
   - Remove the `written_by:` field
   - Keep `response_conventions:` field
2. Remove the WRITE EXCEPTION blockquote from the body
3. Commit + push:
   git add _workspace/plan/operators/mac-studio-primary.md
   git commit -m "coord(mac-studio-primary): re-assert ownership after 2026-05-21 Air write exception + sync with operators v2"
   git push origin book/asaas-al-taveel

If the WRITE EXCEPTION is already gone (you re-asserted earlier): skip this gate.

──────────────────────────────────────────────────────────────────────
GATE 7 — Refresh your Mac Studio column in the index dashboard

Open _workspace/plan/operators/index.md. In the "Machine Status" table, your column should reflect:
  - Current phase: from asaas state.json
  - Pages, Episodes (est), ETA, Spend so far: your observed reality
  - Last verified: now, UTC

  git add _workspace/plan/operators/index.md
  git commit -m "coord(mac-studio-primary): refresh index.md Mac Studio dashboard column"
  git push origin book/asaas-al-taveel

──────────────────────────────────────────────────────────────────────
GATE 8 — Known bugs (heads-up only — Air owns the fix; you do NOT touch framework code)

Two pre-existing bugs block Phase 0g and will hit asaas when it reaches per-chapter:

- Bug X1: scripts/podcast/orchestrate_book.py line 669 builds chapter ref as "<book>:<slug>" but extract_chapter.py expects "<book>/<full-filename-with-ch##-prefix>". Per-chapter loop fails on first chapter.
- Bug X2: contracts with episode_format: debate require a populated debate: block (proposition/host_a/host_b/resolution per debate-framing.md). Null debate block rejects.

Air will fix these. When fixes land on develop, you'll pull develop into your branch (same pattern as GATE 3) and get them.

──────────────────────────────────────────────────────────────────────
GATE 9 — (Optional) Prune any dormant worktrees on this machine

If GATE 1 found a second journal-* worktree on a dormant branch (0 commits ahead of develop), prune it:

  cd "$REPO"
  git worktree list                              # see all worktrees
  git worktree remove <dormant worktree path>    # branch survives; only the working dir is removed

If there's only one worktree on this machine, skip this gate.

──────────────────────────────────────────────────────────────────────
HANDOFF — report to Asif in BLUF format

Reply EXACTLY in this shape (no custom section labels):

  **TL;DR:** Studio synced with develop @ <hash>; operator file re-asserted; dashboard refreshed; bugs X1/X2 acknowledged; awaiting authorization to continue asaas Phase <X>.
  **Status:** 🟢 ready

  ### 1. Sync result 🟢
  - *Plain English:* one sentence on what merged + any conflicts you resolved
  - *Impact:* Studio now reads the same coord docs as Air
  - *Where:* [merge commit](https://github.com/asifhussain60/podcast-factory/commit/<sha>)

  ### 2. Operator file 🟢
  - *Plain English:* one sentence on ownership re-assertion (if it applied) or "already clean"
  - *Impact:* single-owner model restored
  - *Where:* [mac-studio-primary.md](_workspace/plan/operators/mac-studio-primary.md)

  ### 3. Dashboard refreshed 🟢
  - *Plain English:* Studio column in index.md now shows current phase + ETA + spend
  - *Impact:* Asif can read cross-machine state at a glance
  - *Where:* [index.md](_workspace/plan/operators/index.md)

  ### 4. Worktree state 🟢 (or 🟡 if you pruned one, mention it)
  - *Plain English:* "single worktree at <path>" OR "pruned dormant <path>"
  - *Impact:* no visual sprawl

  **Your next step:** authorize Studio to continue asaas Phase <X>, OR ask Studio to wait while Air fixes X1+X2.

If anything halts at a gate, report:

  **TL;DR:** Sync halted at GATE <N>.
  **Status:** 🟡 needs your decision
  ### What happened
  - *Plain English:* one sentence
  - *Verbatim error:* <copy the actual error>
  **Your next step:** one explicit thing for Asif to decide.

DO NOT START asaas LLM work until Asif explicitly authorizes.
```
