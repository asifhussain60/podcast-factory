---
name: trip-edit
description: "App-triggered trip editing skill. Handles natural-language trip editing via FloatingChat. Classifies intent, researches venues via web_search, emits bounded JSON Patches, and applies them after semantic validation. Triggered by user messages in the Trip Overview FloatingChat that express edit intent (add/move/change/delete events, swap venues, adjust times). Server-executed at Tier 2 (Sonnet)."
---

# trip-edit — Natural-Language Trip Editing

App-tier skill that handles real-time conversational trip editing. User speaks intent in FloatingChat; the server classifies, researches, and applies bounded edits.

## Execution

- **Tier:** 2 (Sonnet + web_search)
- **Surface:** App-triggered, server-executed
- **Latency budget:** <15s per edit (including web_search)
- **Token budget:** ~2K input + ~1K output per call

## Owns

- Intent classification (edit / qa / needs_info / unknown)
- Venue research via web_search
- JSON Patch generation (RFC 6902)
- Semantic validation (dates monotonic, no flight overlap, events have required fields)
- Edit provenance logging to `edit-log.json`
- Snapshot creation before destructive edits

## Does NOT Own

- Trip creation (that's `trip-planner`)
- Daily trip recording (that's `trip-log`)
- Itinerary HTML rendering (that's client-side)
- Queue mutations
- Memoir content

## Server Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/trip-edit` | Main edit handler (classify + patch) |
| POST | `/api/trip-edit/revert` | Revert to snapshot |
| GET | `/api/edit-log` | Read edit history |
| POST | `/api/find-alternatives` | Suggest alternative venues |
| POST | `/api/verify-venue` | Verify venue exists |
| POST | `/api/swap-event` | Swap event with alternative |
| POST | `/api/insert-event` | Insert new event |
| POST | `/api/suggest-insert` | AI-suggest where to insert |
| POST | `/api/delete-event` | Remove an event |

## Named Prompts

- `trip-edit` — main intent classifier + patch generator
- `find-alternatives` — venue alternative research
- `suggest-insert-event` — smart insertion point suggestion
- `trip-qa` — Q&A fallback when intent is not an edit
- `trip-assistant` — assistant mode for complex requests

## Validation Rules

- Every destination event MUST have `venue`, `phone`, `rating`
- Destination tags: DINING, CAFE, NATURE, SHOPPING, SPA, ENTERTAINMENT, REST, ENGAGEMENT_HIGHLIGHT, EVENT, CELEBRATION
- Optional but recommended: `category`, `duration_min`, `alt_venue`
- Dates must be monotonic within a day
- No flight time overlap
- Event start < end

## Canonical Write Permissions

- MAY write: `trips/{slug}/trip.yaml` (bounded edits), `trips/{slug}/edit-log.json`, `trips/{slug}/snapshots/`
- MAY NEVER write: `chapters/`, `reference/`, git metadata

## Escalation

- If web_search fails 3 times → return `needs_info` and ask user
- If patch validation fails → return error with specific reason, do not apply
- If edit would delete >3 events → require explicit user confirmation
