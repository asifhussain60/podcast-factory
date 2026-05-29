---
name: html-view-challenger
description: "Conformance challenger for HTML views, Astro pages, components, and diagrams on the Podcast Factory Astro Site (directory plan-dashboard/). Validates a built view against the Cortex HTML View Quality Standard (74 REQ-NNN rules) plus this repo's styling DoD (ZERO inline styling, external CSS/JS only, colour theme unchanged, vertical/uncapped/varied diagrams). Runs the §10 checklist + §11 automated greps, emits REQ-NNN-cited findings at MUST (blocking) / SHOULD (warn) severity, converges fix->re-audit (up to 5 iterations), and stamps a verdict + conformance level (L1 Conformant / L2 Recommended / L3 Exemplary). Pairs with the html-view-quality skill (the author-side contract). Invoke for: 'challenge view <name>', 'audit the site', 'check this page against Cortex', '/html-view-challenger', 'converge view before ship'."
tools: Read, Edit, Glob, Grep, Bash
---

This file is a discovery stub. Full specification at [infra/claude-agents/html-view-challenger.md](../../infra/claude-agents/html-view-challenger.md).
