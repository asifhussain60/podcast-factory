---
mode: agent
description: Append a session-log entry to _workspace/plan/copilot-handoff.md before ending a Copilot session. Copilot's only form of cross-session memory.
---

End the current Copilot session by leaving a clear note for the next one (whether that's another Copilot session or Asif coming back on Claude with tokens).

## Steps

1. Read `#file:../../_workspace/plan/copilot-handoff.md` end-to-end so you know where the existing `## Session log` section is.

2. Identify:
   - Today's date in `YYYY-MM-DD HH:MM` (EST)
   - Every commit you authored or co-authored this session (`git log --author=Copilot --oneline` — fall back to `git log --since='today' --author='<email>' --oneline` if that's empty)
   - What roadmap step was advanced (statement, not step ID, in the visible log)
   - What's queued next
   - Any unresolved blocker, halt, or question for Asif

3. Append a new entry to the **bottom** of the `## Session log` section using this exact shape:

   ```
   ### YYYY-MM-DD HH:MM EST — Copilot session

   **Closed:** {plain-English statement of what shipped}
   **Commits:** {short-sha — one line each}
   **Next:** {single sentence — what should happen next session}
   **Blocked / open:** {one line per item, or "none"}
   ```

4. Commit ONLY the handoff doc:

   ```
   git add _workspace/plan/copilot-handoff.md
   git commit -m "chore(handoff): session log entry — <one-line summary>"
   ```

   No `Co-Authored-By` trailer on this commit; it's a meta record.

5. Report back to Asif in his response format:

   ```
   ## Session wrapped

   > **{What shipped + what's next, one sentence each.}**

   ### Commits this session

   {Bullet list — short SHA + plain-English title.}

   ### What's queued

   {The "Next" line from the handoff entry, in plain English.}

   ---

   ### Next: 👤 Asif

   A. **(Recommended)** {logical next action when you return — e.g. 'review the handoff entry and tell Copilot to proceed' or 'pause and verify in the dashboard'}.

   B. {alternative}.
   ```

## Hard rules

- Never overwrite the existing session log — append only.
- Never skip this step before ending a session. The handoff doc is Copilot's only memory.
- If you have NOTHING to log (read-only session, no commits, no decisions), still append an entry with `Closed: read-only orientation, no edits` so the gap is explicit.
