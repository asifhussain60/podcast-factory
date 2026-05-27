---
name: podcast-publisher
description: "Move shipped content from content/drafts/<slug>/ to content/published/books/<slug>/ after the convergence loop completes. Thin wrapper around scripts/podcast/publish_to_library.py. ALWAYS invoke when the user says \"publish <slug>\", \"ship to library\", \"promote to published\", \"/publish\", or after the orchestrator's per-chapter convergence reports SHIP-READY / SHIP-WITH-CAUTION on every chapter of a book. Runs gates G1 (structure) → G2 (chapter/episode pairs) → G3 (sequential numbering) → G4 (build-clean P0=0) → G5 (state.json shippable) → G6 (target wipe-safe) → G7 (challenger convergence verdict). Refuses to publish books whose pipeline_mode=non_orchestrated_mode_2 or whose verdict is not in {SHIP-READY, SHIP-WITH-CAUTION} unless --allow-mode-2 is passed. Distinct from the deprecated ship_to_library.py (removed 2026-05-24). Canonical tracked location."
---

This file is a discovery stub. Full specification at [infra/claude-agents/podcast-publisher.md](../../infra/claude-agents/podcast-publisher.md).
