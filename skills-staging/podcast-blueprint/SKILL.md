---
name: podcast-blueprint
description: "Content-aware episode-structure planner for the /podcast pipeline. ALWAYS invoke when user says 'blueprint <book-slug>', '/podcast-blueprint', '@podcast-blueprint', 'classify book', 'plan episodes for <slug>', 'arc this book'. Runs in slot 05.5-blueprint between the P22 transcript-review resume and the existing 06-phonetics stage. Three layers — Layer 1 (Haiku-default scan/classify → classification.json), Layer 2 (episode-plan.md, model per Layer 1 recommendation), Layer 3 (DRAFT arc-conventions.md, first-run only, NEVER overwrites). Tradition-agnostic; seeds P23's series-config.yaml audience_profile + source_tradition via proposed-config.yaml. Anti-requirement: NO global episode template — every book is classified, every planning mode is genre-appropriate (tribunal_arc / chronological / problem_solution / vignette_grid / dialectical_pairs). Does NOT replace 06-phonetics, 07-chapter-design, or 11-per-chapter framing; it INFORMS them. BOUNDARY: this skill reads nothing from /journal memoir content (content/babu-memoir/). Reads only from <book>/_system/source/text/refined-english.md, <book>/operator-review.md, <book>/arc-conventions.md."
locked_decisions:
  - "name = podcast-blueprint (NOT podcast-arc)"
  - "slot = phase 0b.5 (orchestrator slug 05.5-blueprint)"
  - "Layer 1 auto-upgrades the model for Layers 2-3; --force-model overrides"
  - "arc-conventions.md is OPTIONAL input, agent-seeded DRAFT on first run, operator-editable thereafter; Layer 3 NEVER overwrites"
---

# podcast-blueprint — Skill Overview

This skill is the **planner**, not the framer. It reads a post-P22 refined English transcript and emits the artifacts that downstream phases (06-phonetics, 07-chapter-design, 08-enrichment, 11-per-chapter framing) consume to make genre-appropriate episodes.

## What this skill DOES

1. **Classifies** the source (Layer 1) — genre, density, narrative mode, structural units, cross-reference load, vocabulary contestedness.
2. **Recommends** a model for Layers 2–3 based on its own classification (Haiku / Sonnet / Opus). Operator overrides via `--force-model`.
3. **Recommends** P23 `audience_profile` + `source_tradition`. Operator confirms via `--approve-blueprint`.
4. **Plans episodes** (Layer 2) — count, breakdown, recap/preview discipline, structural-unit mapping.
5. **Seeds DRAFT arc-conventions.md** (Layer 3, first run only). Operator-editable; Layer 3 never overwrites.

## What this skill does NOT do

- Does NOT replace the existing 06-phonetics, 07-chapter-design, or 11-per-chapter framing phases. It feeds them.
- Does NOT decide audience_profile or source_tradition — recommends; operator confirms.
- Does NOT call Azure (only `claude -p`).
- Does NOT touch any artifact outside `content/podcast/`, `scripts/podcast/`, `_workspace/plan/`, and `<book>/_system/blueprint/`.
- Does NOT classify books past slot 05.5 (asaas-al-taveel mid-0b, kitab-al-riyad at 0d→0e are NOT replanned).
- Does NOT overwrite operator-edited `arc-conventions.md`.

## Phase order in the pipeline

```
01-preflight → 04-ocr-translate → 05-refine-english →
  [P22 halt + operator transcript review] →
  [--approve-transcript resume] →
05.5-blueprint (THIS SKILL):
    Layer 1 (Haiku) → classification.json + proposed-config.yaml
    [halt rc=3 unless --auto-approve-blueprint]
    [--approve-blueprint resume]
    Layer 2 (per Layer 1) → episode-plan.md
    Layer 3 (first run only) → arc-conventions.md DRAFT
    Orchestrator: merge proposed-config.yaml → series-config.yaml
      → P23 audience_profile activates downstream
→ 06-phonetics → 07-chapter-design → 08-enrichment → 11-per-chapter → ...
```

## Authoritative files

| Role | Path |
|---|---|
| Operator handbook | [content/podcast/.skill/handbook/blueprint-protocol.md](../../content/podcast/.skill/handbook/blueprint-protocol.md) |
| Agent spec (canonical) | [infra/claude-agents/podcast-blueprint.md](../../infra/claude-agents/podcast-blueprint.md) |
| Agent spec (mirror) | [.github/agents/podcast-blueprint.agent.md](../../.github/agents/podcast-blueprint.agent.md) |
| JSON-Schema for Layer 1 | [content/podcast/.skill/handbook/_schemas/classification.schema.json](../../content/podcast/.skill/handbook/_schemas/classification.schema.json) |
| arc-conventions.md template | [content/podcast/.skill/handbook/_templates/arc-conventions.template.md](../../content/podcast/.skill/handbook/_templates/arc-conventions.template.md) |
| CLI | [scripts/podcast/blueprint_book.py](../../scripts/podcast/blueprint_book.py) |
| Library | [scripts/podcast/_blueprint.py](../../scripts/podcast/_blueprint.py) |
| Pydantic models | [scripts/podcast/_blueprint_schema.py](../../scripts/podcast/_blueprint_schema.py) |
| Plan source | [\_workspace/plan/podcast-plan.yaml § P24](../../_workspace/plan/podcast-plan.yaml) |

## Status (2026-05-20)

| Component | Status |
|---|---|
| Plan (P24 + W2 wiring) | ✅ landed |
| Agent spec | ✅ landed |
| JSON-Schema for `classification.json` | ✅ landed |
| `arc-conventions.md` template | ✅ landed |
| Operator handbook | ✅ landed |
| Pydantic models + schema tests | 🚧 in flight (P24.1) |
| `_blueprint.py` shell + orchestrator slot | 🚧 in flight (P24.1 + P24.4 shell) |
| Layer 1 / Layer 2 / Layer 3 prompts | 🟠 BLOCKED on Air handoff (P24.2 + P24.3) |
| E2E test | 🟠 BLOCKED on P24.2 + P24.3 |

When Air's truncated three-layer architecture body arrives, P24.2 + P24.3 unblock. Until then, the SHELL is everything operators need to review the contract and the orchestrator wiring.
