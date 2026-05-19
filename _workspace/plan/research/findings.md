# Research Findings — Podcast Pipeline

Source citations and key data informing the plan. **Podcast scope only.**

## 1. Sample book corpus (your iCloud `Books/` folder)

| Book | Pages | PDF size | Tier |
|---|---:|---:|---|
| MM - Anjum apa | 17 | — | tiny |
| Ahed Namah | 20 | 4.0 MB | tiny |
| Ayyuhal Walad | 30 | 143 KB | tiny |
| Masaail (searchable) | 81 | 3.2 MB | small |
| Majalis Moyyada | 139 | 11 MB | small |
| **Kitab al-Riyad** | **260** | **4.4 MB** | **medium** (already in pipeline) |
| Kitab Maqbas | 392 | 13 MB | large |
| Asaas Al-Taveel | 416 | 9.8 MB | large |
| Rasail Ikhwan AsSafa | 865 | 5.6 MB | xlarge |
| Raahat al-Aqal | 591 | 13 MB | xlarge |
| MM - Anjum apa (large copy) | — | 13 MB | — |

**Observation:** corpus spans 17 → 865 pages, max PDF 13 MB. Every single book fits comfortably inside Azure Document Intelligence Standard-tier limits (see §2). One outlier `.txt` file is 236 MB but is plain text, not a PDF, so it bypasses OCR entirely.

## 2. Azure Document Intelligence — Standard tier limits

Source: <https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/service-limits>

| Limit | Standard | Implication for us |
|---|---:|---|
| Max document size | **500 MB** | All sample books fit |
| Max pages (Analysis) | **2,000** | Largest book (865 p) is 43% of ceiling |
| Analyze POST | 15 TPS | Sequential calls are fine |
| Get-result GET | 50 TPS | Polling at 2 s is well under |
| Throttling backoff | exponential, 2-5-13-34 s pattern | Already implemented in current code |

**Conclusion:** PDF splitting is NOT required for any book in the current corpus. Deferred to P7 as speculative.

## 3. Anthropic SDK — streaming + error recovery

Source: <https://platform.claude.com/docs/en/build-with-claude/streaming>

### Two key patterns we will adopt in P3

**A. Streaming with final-message accumulation** — for "monolithic" calls (Phase 0d TOC, per-chapter framing, challenger). Removes HTTP-timeout risk and gives us live token-count telemetry without writing event handlers ourselves.

```python
with client.messages.stream(
    max_tokens=128000,
    messages=[{"role": "user", "content": prompt}],
    model="claude-opus-4-7",
) as stream:
    for text in stream.text_stream:
        heartbeat.tick(tokens=len(text))   # ~1 tick per delta
    message = stream.get_final_message()    # complete content, identical to .create()
final_text = message.content[0].text
```

**B. Error recovery (Claude 4.6+ pattern)** — for interrupted streams. We capture the partial response, then send a follow-up user message containing it + instruction to continue. Lets us survive transient network failures inside a long 0d/0e call without losing minutes of generation.

### Anti-pattern (current bug)

Running `claude -p` subprocess with default permission mode silently refuses file-write tools, returns `rc=0` with a refusal in stdout. Orchestrator's "did the file get written?" check then logs `NO ARTIFACT` and proceeds — losing windows silently. **Two fixes possible:**
1. Add `--permission-mode acceptEdits` (the patch in P0)
2. Migrate to native SDK so the orchestrator writes files itself (P3 — the real fix)

P0 is the band-aid; P3 is the cure.

## 4. FastAPI orchestration — what NOT to use

Source: <https://fastapi.tiangolo.com/tutorial/background-tasks/>

> If you need to perform heavy background computation … you might benefit from using other bigger tools like Celery. They tend to require more complex configurations, a message/job queue manager, like RabbitMQ or Redis, but they allow you to run background tasks in multiple processes…

**Decision:**
- ❌ `BackgroundTasks` — runs in the API worker process; hours-long jobs would block requests and die on restart.
- ❌ Celery/Redis — operational overhead far exceeds value at single-user scale.
- ✅ **Subprocess worker** — API server spawns `orchestrate_book.py` via `subprocess.Popen`, tracks PID + state file, polls heartbeat. Restart-safe (orchestrator already has `--resume`). Zero new infra.

## 5. Dos and Don'ts (curated)

### DO

- **Always pass `--permission-mode acceptEdits`** when shelling to `claude -p` with file-write tools (P0)
- **Verify artifact exists AND is non-empty** after every `claude -p` call, treat missing/empty as failure (P0)
- **Stream LLM responses** with `messages.stream() + get_final_message()` for any call with `max_tokens > 4096` (P3)
- **Write heartbeat every ≤30 s** from a daemon thread, atomic JSON, dedicated `heartbeat.json` (P1)
- **Spawn long jobs as subprocesses** of the API, never as in-process BackgroundTasks (P5)
- **Use exponential backoff** on Azure DI 429: 2-5-13-34 seconds (already done)
- **Keep state.json as authoritative**; SQLite is index/cache only (P5)
- **Append-only checkpoints** (`.done` markers, enrichment-log rows) — never overwrite (already done in 0d/0e)

### DON'T

- **Don't run `claude -p` without permission-mode flag** — silent failure mode
- **Don't trust subprocess `rc=0`** — always check artifacts independently
- **Don't run orchestrator in FastAPI BackgroundTasks** — kills resilience
- **Don't split PDFs** until Azure DI 500MB/2000-page limit is actually hit (none of the corpus needs it)
- **Don't conflate `_workspace/` with `content/`** — `_workspace/` = tooling/plans, `content/` = shipped artifacts
- **Don't mix journal and podcast** — separate skills, separate agents, separate state schemas, separate services
- **Don't add SQLite before P5** — JSON files are sufficient and human-debuggable for current scale
- **Don't rename phases mid-flight** — defer the `0a → 04-ocr-translate` rename until end-to-end is proven stable (P6)
- **Don't parallelize per-chapter LLM calls** until cost-tracking is in place (P7)

## 6. Decision: keep podcast and journal cleanly separated

| Concern | Podcast | Journal |
|---|---|---|
| Agent file(s) | `podcast-orchestrator.agent.md`, `podcast-trainer.agent.md` | `journal-orchestrator.agent.md`, `journal-challenger.agent.md` |
| Skill folder | `skills-staging/podcast/` | `skills-staging/journal/` |
| Code root | `scripts/podcast/` | `scripts/site/` (journal Markdown rendering) |
| Content root | `content/podcast/` | `content/babu-memoir/`, `content/_shared/` |
| Future API | `scripts/podcast/service/` (FastAPI, port 8765) | none planned |
| State store | per-book `_system/orchestrator-state.json` + optional `_workspace/podcast.db` | journal Git history is the state |
| Trainer | podcast-trainer agent + per-chapter convergence | journal has no trainer |

**Hard rule:** any file under `scripts/podcast/` or its FastAPI service may NOT import from `scripts/site/` or `scripts/memoir/`, and vice versa. Cross-cutting shared utilities (if any ever needed) go into a new `scripts/_shared/` package — currently empty by design.
