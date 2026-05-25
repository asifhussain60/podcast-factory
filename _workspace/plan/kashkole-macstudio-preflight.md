# KAHSKOLE MacStudio Pre-flight — Infrastructure Sync

**Paste below as the first message in a fresh Claude Code session on MacStudio.**
Working directory: `~/PROJECTS/podcast-factory`

================================================================================

You are starting a new session in the podcast-factory repo on MacStudio.

Before creating the Kashkole book branch, you must land 7 infrastructure
commits from the MacBook Air's in-flight book branch onto develop. (6 of the
original 13 are already present on develop — confirmed 2026-05-25.)

This ensures book/kashkole inherits the full watchdog + pipeline infrastructure
and that future merges to develop are conflict-free.

Working directory: `~/PROJECTS/podcast-factory`
Working branch: `develop`

---

## Step 1 — Fetch all remote branches

```bash
git fetch --all --prune
git checkout develop
git merge --ff-only origin/develop
```

Verify these 6 commits are already present (confirm before cherry-picking):

```bash
git log --oneline develop | grep -E "85c6668|4efeb42|7715181|ad21a22|4f8048f|6e296e9"
```

Expected: 6 lines. If fewer than 6, surface immediately — do not proceed.

---

## Step 2 — Cherry-pick the 7 missing infrastructure commits (oldest → newest)

Run one at a time. If any cherry-pick fails with a conflict, STOP and surface it.

```bash
git cherry-pick bd98895   # feat: split publish — finalize (gates) + publish (file copy)
git cherry-pick f519dbd   # feat: slide decks required output, default=True
git cherry-pick 1beada5   # docs: podcast-auditor v1.1 + podcast-challenger v2.2
git cherry-pick 5ae5d07   # feat: self-healing watchdog for long-running orchestrator phases
git cherry-pick ce228a3   # fix: whitelist watchdog.json + _workspace/logs/ in pre-flight
git cherry-pick 2a2ddd2   # feat: auto-spawn watchdog on every --resume
git cherry-pick e99e90b   # fix: close 3 watchdog integration gaps (per-chapter-slides, 0f gate, docs)
```

---

## Step 3 — Run regression tests

```bash
/usr/bin/python3 -m unittest discover -s tests/regression -p "test_*.py" -v
```

All tests must pass. If any fail, fix before pushing.

---

## Step 4 — Push updated develop

```bash
git push origin develop
```

---

## Step 5 — Confirm and report

```bash
git log --oneline -10
```

Report: "develop updated with 7 infrastructure commits. Ready to create book/kashkole."

**Do NOT create book/kashkole yet.** Wait for Asif to confirm develop looks good.

---

## Context: what these commits add

| Commit | What it adds |
|---|---|
| bd98895 | Publish split into finalize (gate checks) + publish (file copy) |
| f519dbd | Slide decks as required output in pipeline |
| 1beada5 | Podcast-auditor v1.1 + podcast-challenger v2.2 agent specs |
| 5ae5d07 | Self-healing watchdog — restarts stalled orchestrator phases |
| ce228a3 | Pre-flight whitelist includes watchdog.json + _workspace/logs/ |
| 2a2ddd2 | Watchdog auto-spawns on every --resume (no manual intervention) |
| e99e90b | Watchdog integration gaps closed (per-chapter-slides, 0f gate) |
