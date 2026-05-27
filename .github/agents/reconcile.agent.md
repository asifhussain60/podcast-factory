---
name: reconcile
description: "Reconciliation agent for architecture docs. Given (a) a file:// or https:// link to one of Asif's architecture HTML views and (b) a free-text change request, the agent first verifies whether the underlying skill/agent/script ALREADY implements the requested behaviour, fixes any gap in the code FIRST with zero regression, then updates the HTML view (and any sibling views) to reflect the new reality. Never updates docs ahead of code. Invoke for: 'fix this view', 'this should also support X', 'pipeline is wrong about Y', 'docs and code disagree', '/reconcile <link> <request>', or any time Asif pastes an architecture-docs URL + a sentence saying what is wrong or missing."
---

This file is a discovery stub. Full specification at [infra/claude-agents/reconcile.md](../../infra/claude-agents/reconcile.md).
