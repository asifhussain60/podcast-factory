---
name: podcast-challenger
description: "Semantic-quality challenger for podcasted-book chapters (uploaded to NotebookLM as the SOURCE) and framings/episode-txts (pasted into the NotebookLM Customize prompt box). Validates everything `build_episode_txt.py` cannot statically catch: citation authenticity, phonetic coverage, enrichment depth, framing integrity, NotebookLM literalness, welcome openings, anti-repetition, no-irrelevant-background, name aliasing, interruption avoidance. Runs in a convergence loop (up to 5 iterations), auto-fixes deterministic issues, surfaces semantic findings for human resolution, emits findings to the `_learning/findings.jsonl` ledger, writes per-book health score, and stamps `CHALLENGER_VERSION` from `_rules.py` into every report. Book-agnostic: caller supplies `<book-slug>`. Invoke for: 'challenge <book-slug>', 'review podcast', 'audit chapters', '/podcast-challenger', 'converge before publish', 'check book before upload'."
---

This file is a discovery stub. Full specification at [infra/claude-agents/podcast-challenger.md](../../infra/claude-agents/podcast-challenger.md).
