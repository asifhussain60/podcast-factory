---
name: dayone-publish
description: "App-triggered DayOne publish skill. Manages the review → compose → publish workflow for pushing approved journal entries to DayOne. Handles publish sessions (create/resume/abandon), trip reflection generation, tag suggestion, narrative synthesis, and final DayOne entry composition. Server-executed at Tier 2 (Sonnet for synthesis). Triggered by the Publish button in the Log view."
---

# dayone-publish — DayOne Publish Workflow

App-tier skill that manages the review-to-publish pipeline for DayOne journal entries.

## Execution

- **Tier:** 2 (Sonnet for reflection/narrative synthesis, Haiku for tags)
- **Surface:** App-triggered, server-executed
- **Latency budget:** <15s for reflection generation, <5s for tag suggestion

## Owns

- Publish session lifecycle (create → resume → complete → abandon)
- Trip reflection generation (from approved captions)
- Trip narrative synthesis (150-300 word memoir paragraph)
- Tag suggestion (5-12 normalized tags from corpus)
- DayOne entry composition (structured payload for DayOne CLI)
- Session state persistence in `ops.db`

## Does NOT Own

- Capture (that's `receipt-capture`)
- Review/approval of individual entries (that's the Log view UI)
- Memoir chapter writes (that's `journal` skill via Cowork)
- YNAB sync (that's Cowork drain)

## Server Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/publish-sessions` | List sessions |
| GET | `/api/publish-sessions/:id` | Get session detail |
| POST | `/api/publish-sessions` | Create new session |
| PATCH | `/api/publish-sessions/:id` | Update session (add entries, set reflection) |
| POST | `/api/publish-sessions/:id/abandon` | Abandon session |
| POST | `/api/dayone/*` | DayOne CLI integration endpoints |
| POST | `/api/trip-refine-all` | Refine All coordinator (batch synthesis) |
| POST | `/api/trip-refine-field` | Single-field re-synthesis |
| GET | `/api/tag-corpus/top` | Cross-trip tag typeahead |

## Named Prompts

- `refine-reflection` — Sonnet: generate/polish trip reflection
- `synthesize-trip-narrative` — Sonnet: 150-300 word memoir paragraph
- `suggest-tags` — Haiku: 5-12 normalized tags

## Workflow

```
User approves entries in Log view
       ↓
Create publish session → session ID
       ↓
Refine All: for each field, call appropriate prompt
  - Tags → suggest-tags (Haiku)
  - Narrative → synthesize-trip-narrative (Sonnet)  
  - Reflection → refine-reflection (Sonnet)
       ↓
User reviews + edits synthesized fields
       ↓
Compose DayOne entry → POST to DayOne CLI
       ↓
Mark session complete, update entry publishedAt timestamps
```

## Canonical Write Permissions

- MAY write: `ops.db` (publish_sessions table), entry status updates in `pending.json`
- MAY NEVER write: `chapters/`, `reference/`, `trips/{slug}/journal/`

## Tag Normalization

Uses `shared/tag-normalize.js` (dual-surface: server + client). All tags are lowercase hyphen-separated slugs matching `/^[a-z0-9-]+$/`.

## Guardrails

- Reflection: 2-5 sentences max
- Narrative: 150-300 words
- Tags: 5-12 per trip, prefer existing corpus
- Sonnet calls: budget-throttled
- Session timeout: abandoned after 24h of inactivity (not yet enforced)
