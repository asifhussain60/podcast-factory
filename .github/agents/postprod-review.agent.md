---
name: postprod-review
description: "Post-production audit for NotebookLM-generated audio episodes. Consumes Turboscribe-produced transcripts of the downloaded m4a files and scores each against (a) the book's genre archetype and (b) the Dos/Don'ts protocol. Identifies drift the source-side `podcast-challenger` cannot catch because it only sees the *upload bundle* — postprod-review sees what NotebookLM *actually produced*. Identify-only in v1.0 (no mutations). Delegates filename normalization to the `vacuum` agent. Writes per-chapter and per-book reports under `audits/`, appends to `_learning/findings.jsonl` with prefix `PR`, and stamps `postprod_version` into every report. Book-agnostic: caller supplies `<book-slug>`. Invoke for: 'postprod <book-slug>', 'review the audio', 'audit the m4a output', '/postprod-review', 'check what NotebookLM produced', 'transcribe-and-review <book-slug>'."
---

This file is a discovery stub. Full specification at [infra/claude-agents/postprod-review.md](../../infra/claude-agents/postprod-review.md).
