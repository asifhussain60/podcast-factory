# Chapter set report — islr-mas-i

**Status:** N/A — Mode-2 path. Phase 0d chapter segmentation was decided manually in [_system/integration-analysis.md](integration-analysis.md) §6 ("MAS-I scope") and chapter rationale at [_system/source/text/chapters-rationale.md](source/text/chapters-rationale.md), rather than via the orchestrator's `check_chapter_set.py` artifact.

**7-chapter / 7-episode plan (MAS-I scope):**

| EP | Slug | Source chapter | Notes |
| --- | --- | --- | --- |
| EP01 | introduction | Ch 1 (full) | Pre-shipped 2026-05-21 at 1e3b7aa |
| EP02 | statistical-learning | Ch 2 | Excludes §2.2.3 (The Classification Setting) |
| EP03 | linear-regression | Ch 3 | §3.1–§3.3 only, plus §3.6 labs on §3.1–§3.3 |
| EP04 | classification | Ch 4 | §4.1–§4.4, **excluding** LDA portion of §4.4 (skip 4.4.1, 4.4.2; keep QDA 4.4.3 + Naive Bayes 4.4.4) |
| EP05 | resampling | Ch 5 | Full |
| EP06 | model-selection | Ch 6 | Full |
| EP07 | nonlinear | Ch 7 | Full |

**See also:** [orchestrator-state.json](orchestrator-state.json) `phases.0d`.
