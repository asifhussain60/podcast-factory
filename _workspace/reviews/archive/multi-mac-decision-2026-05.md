# Multi-Machine Execution Model — RESOLVED

## Decision

The podcast factory runs on a **primary-only** model.

All pipeline work — Claude API calls, Azure OCR, Azure speech, and local
orchestration — executes on the single primary machine. Secondary machines
may observe in-progress runs via **SSH-tunneled** port-forwarding to the
primary's local dashboard (`plan-dashboard` dev server on port 4321).

## Status: RESOLVED

This decision supersedes the earlier dual-machine coordination model
(operator files, machine-id detection, book-queue mutex) which was
retired on 2026-05-23.

## Rationale

- Pipeline cost is dominated by remote APIs (Anthropic + Azure), not
  local CPU/RAM. Running on one machine eliminates coordination overhead
  with no meaningful latency penalty.
- The SSH-tunneled observer pattern gives a second seat full read access
  to the live dashboard without any write exposure to pipeline state.
- A single `develop` branch and single `orchestrator-state.json` per book
  remove all race-condition risk that dual-machine coordination introduced.

## Access pattern for observers

```
# On observer machine — tunnel primary's dashboard to localhost:4322
ssh -N -L 4322:localhost:4321 <primary-host>

# Open in browser
open http://localhost:4322
```

The tunnel is read-only: the observer sees the live plan-dashboard but
cannot write to `content/drafts/` or trigger any pipeline phase.
