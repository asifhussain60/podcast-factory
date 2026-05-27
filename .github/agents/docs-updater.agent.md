---
name: docs-updater
description: "Regenerate the single architecture view at docs/architecture/index.html from CURRENT repo truth. ALWAYS invoke this agent when the user says \"update the docs\", \"/update-docs\", \"refresh the architecture page\", \"regenerate the architecture view\", or any variant pointing at docs/. Reads CLAUDE.md, framework.md, scripts/podcast/_branching.py, infra/claude-agents/*.md, scripts/podcast/_rules.py, scripts/podcast/_doctrinal.py, scripts/podcast/_convergence.py, scripts/podcast/publish_to_library.py, scripts/podcast/orchestrate_book.py, and the last 30 commits on develop — then regenerates the single long-scrolling HTML page with D3.js diagrams. Idempotent: running twice on the same repo state produces the same file. Deletes obsolete architecture HTMLs that are NOT the canonical index.html. Never stamps a stale page with a new date."
---

This file is a discovery stub. Full specification at [infra/claude-agents/docs-updater.md](../../infra/claude-agents/docs-updater.md).
