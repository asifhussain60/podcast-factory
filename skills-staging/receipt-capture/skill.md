---
name: receipt-capture
description: "App-triggered capture skill for photos, notes, voice transcripts, and receipts. Handles image upload, OCR (macOS Vision first, Haiku fallback), image classification (photo vs receipt), voice refinement, note refinement, and queue writes to pending.json. Server-executed at Tier 1-2. Triggered by the Log view's capture buttons (camera, note, voice)."
---

# receipt-capture — Capture & Classify

App-tier skill that handles the full capture pipeline: upload → classify → extract → queue.

## Execution

- **Tier:** 1 (Haiku for classification) → 2 (Sonnet for receipt extraction with vision)
- **Surface:** App-triggered, server-executed
- **Latency budget:** <5s for classify, <10s for receipt extraction

## Owns

- Image upload + storage to `trips/{slug}/photos/`
- Image classification (photo / receipt / unsorted-image)
- Receipt field extraction (amount, merchant, currency, date, line items, YNAB category)
- Note text refinement in Asif's voice
- Voice transcript cleanup
- Queue row creation in `pending.json`
- In-process classify queue for async image classification

## Does NOT Own

- Memoir promotion (that's `memory-promotion`)
- DayOne publishing (that's `dayone-publish`)
- YNAB sync (that's Cowork via drain)
- Queue draining (that's `daily-drain`)

## Server Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/log/capture` | Main capture endpoint (photo + note + voice) |
| POST | `/api/upload` | Raw file upload |
| POST | `/api/extract-receipt` | Receipt field extraction |
| PATCH | `/api/log/:id` | Update notes / reviewStatus / draft |
| POST | `/api/log/:id/refine` | AI-refine a single entry |
| DELETE | `/api/log/:id` | Drop a row from queues |

## Named Prompts

- `classify-image-kind` — Haiku: is this a photo or receipt?
- `extract-receipt` — receipt field extraction
- `refine-note` — Haiku: polish a note in voice
- `refine-voice-transcript` — Haiku: clean voice transcript
- `refine-receipt` — Sonnet: extract structured fields + voice description

## Pipeline

```
User captures photo/note/voice
       ↓
POST /api/log/capture
       ↓
Image? → store to photos/ → enqueue classify job
       ↓
classify-image-kind (Haiku) → update kind: photo | receipt
       ↓
If receipt → refine-receipt (Sonnet) on user request
       ↓
Row in pending.json (status: pending, reviewStatus: unreviewed)
```

## Canonical Write Permissions

- MAY write: `trips/{slug}/pending.json`, `trips/{slug}/photos/*`, `trips/{slug}/receipts/*`
- MAY NEVER write: `chapters/`, `reference/`, `trips/{slug}/journal/`

## Adapters

- `fromPending.js` — normalizes pending.json rows to LogEntry schema
- `fromVoiceInbox.js` — normalizes voice-inbox.json rows to LogEntry schema

## Guardrails

- Image size cap: 4MB for vision calls
- Text size cap: 20,000 chars for refinement
- Rate limit: 20 req/min per endpoint
- Budget throttle: soft at 75%, hard at 90% of monthly cap
