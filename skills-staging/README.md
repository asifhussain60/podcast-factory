# Skills Registry

Central index of all skills in the journal ecosystem. The `journal-orchestrator` agent uses this to route intent.

## Execution Tiers

| Tier | Runner | Budget | Latency |
|---|---|---|---|
| T0 | Deterministic code | Free | <10ms |
| T1 | Haiku | ~$0.001/call | <2s |
| T2 | Sonnet | ~$0.01/call | <10s |
| T3 | Cowork (Claude Code) | ~$0.10-1.00/session | 30s-5min |

## Skill Index

### Cowork-Only Skills (Tier 3)

| Skill | Purpose | Owns | Does NOT Own | Triggers |
|---|---|---|---|---|
| [`trip-planner`](trip-planner/skill.md) | Build interactive trip itineraries | `trips/{slug}/itinerary.*`, `trip.yaml`, `budget.md` | Daily entries, memoir, queue drains | "plan a trip", "itinerary", "travel plan" |
| [`catch-up`](catch-up/skill.md) | End-of-day synthesis | Preview output only (Phase 7) | Canonical writes (Phase 8 drain) | "catch up", "daily recap", "end of day" |
| [`voice-to-prose`](voice-to-prose/skill.md) | Voice → memoir prose | Preview prose candidates | Canonical memoir writes | "voice to prose", "refine voice notes" |
| [`memory-promotion`](memory-promotion/skill.md) | Route memoryWorthy items | Routing plan (preview) | Actual memoir writes | "promote memories", "memoir backlog" |
| [`queue-triage`](queue-triage/skill.md) | Classify + order queue items | Processing plan | Queue mutations | "triage queues", "what's in my queue" |
| [`queue-health`](queue-health/skill.md) | Monitor queue health | Health report (JSON + text) | Queue mutations | "queue stats", "stuck items" |
| [`daily-drain`](daily-drain/skill.md) | Orchestrate full drain pipeline | Drain execution + drain-log | Individual transforms (delegates) | "drain queues", "morning drain" |
| [`food-photo`](food-photo/skill.md) | Pair receipts with memoir | Cross-link suggestions | Memoir edits | "pair food photos", "food receipts" |
| [`usage-auditor`](usage-auditor/skill.md) | Audit spend + forecast | Spend report | Budget enforcement (middleware does that) | "audit usage", "spend report" |
| [`ui-modernizer`](ui-modernizer/skill.md) | Execute UI modernization phases | CSS + component changes | Theme definitions (css-theme-sync) | "modernize ui", "run ui phases" |

### Hybrid Skills

| Skill | Purpose | App Role | Cowork Role | Triggers |
|---|---|---|---|---|
| [`css-theme-sync`](css-theme-sync/skill.md) | Theme parity validation + auto-fix | `npm run validate-themes` | Auto-fix violations | "validate themes", "theme parity" |

### App-Triggered Skills (Tier 1-2, server-executed)

| Skill | Purpose | Tier | Server Endpoints | Triggers |
|---|---|---|---|---|
| [`trip-edit`](trip-edit/skill.md) | Natural-language trip editing | T2 (Sonnet) | `/api/trip-edit`, `/api/find-alternatives`, `/api/insert-event`, etc. | User chat in FloatingChat |
| [`receipt-capture`](receipt-capture/skill.md) | Photo/receipt capture + classify | T1-T2 | `/api/log/capture`, `/api/extract-receipt`, `/api/upload` | Camera button, photo upload |
| [`dayone-publish`](dayone-publish/skill.md) | Compose + publish to DayOne | T2 (Sonnet) | `/api/publish-sessions/*`, `/api/dayone/*` | "Publish to DayOne" button |

### Framework-Defined Skills (Cowork Tier 3, defined in framework.md)

| Skill | Purpose | Owns |
|---|---|---|
| `journal` | Memoir chapter writing + refinement | `chapters/`, `chapters/snapshots/` |
| `trip-log` | Daily event recording in voice | `trips/{slug}/journal/` |

---

## Drain Pipeline

```
queue-health → queue-triage → daily-drain
                                    ↓
              voice-to-prose / memory-promotion / food-photo
                                    ↓
                                catch-up → canonical writes
```

## Named Prompt ↔ Skill Map

Server prompts (`server/src/prompts/`) are the AI instructions used by App-tier skills:

| Prompt | Used By Skill | Tier |
|---|---|---|
| `refine-general` | General voice refinement | T2 |
| `refine-note` | `receipt-capture` (note refinement) | T1 |
| `refine-voice-transcript` | `receipt-capture` (voice refinement) | T1 |
| `refine-receipt` | `receipt-capture` (receipt extraction) | T2 |
| `refine-reflection` | `dayone-publish` (trip reflection) | T2 |
| `trip-edit` | `trip-edit` | T2 |
| `find-alternatives` | `trip-edit` | T2 |
| `suggest-insert-event` | `trip-edit` | T2 |
| `trip-qa` | `trip-edit` (Q&A fallback) | T2 |
| `trip-assistant` | `trip-edit` (assistant mode) | T2 |
| `extract-receipt` | `receipt-capture` | T1 |
| `classify-image-kind` | `receipt-capture` | T1 |
| `classify-holiday-txns` | `usage-auditor` (YNAB) | T1 |
| `ingest-itinerary` | `trip-edit` (itinerary import) | T2 |
| `suggest-tags` | `dayone-publish` (Refine All) | T1 |
| `synthesize-trip-narrative` | `dayone-publish` (Refine All) | T2 |
| `theme-swatches` | `css-theme-sync` (tweaker) | T2 |
| `theme-review` | `css-theme-sync` (tweaker) | T2 |
