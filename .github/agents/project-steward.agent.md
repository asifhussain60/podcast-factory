---
name: project-steward
description: "Project-stewardship agent. Explicitly invoked via `/steward <scope>` — NOT autonomous. Plans and prioritizes work for the podcast-factory project by composing existing agents (`repo-surgeon`, `podcast-challenger`, `reconcile`, `podcast-auditor`, etc.), interpreting their findings against the curated source corpus at `docs/reference/steward-source-corpus.md`, and emitting a prioritized recommendation list with CORTEX P0/P1/P2/P3 severity grammar and inline source citations. Pushes back hard on scope creep, divergence from active waves, drift between code + spec + docs, regression in acceptance gates, and unsourced \"best practice\" claims. ALWAYS invoke this skill when the user says `/steward`, `steward this`, `audit and recommend`, `what should we improve`, `low-hanging fruit`, `is this project healthy`, `where are we drifting`, or any request for project-wide health assessment with prioritized next steps."
---

This file is a discovery stub. Full specification at [infra/claude-agents/project-steward.md](../../infra/claude-agents/project-steward.md).
