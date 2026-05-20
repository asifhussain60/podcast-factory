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

## 7. Large-book chunking — root cause and the flat-layout decision

Folded in from `_workspace/podcast-orchestrator-large-books.md` (deleted after fold-in).
**Status:** implemented · branch `book/kitab-al-riyad` · orchestrator v1.2.

### What was broken

Phase 0b on `kitab-al-riyad` (88k-word raw extract) ran 22:51 → 23:20 and died at the 30-min `claude -p` timeout. Root cause: **one monolithic LLM call** for the entire book. The 30-min ceiling is a property of the headless CLI, not the input. So any book with more than ~30k words of OCR'd raw text would block here regardless of how chapters are later carved.

Two orthogonal problems surfaced together:

1. **Phase 0b/0c monolithic shellout** — pipeline-breaking. Bug.
2. **Per-chapter granularity for very long source chapters** — UX limitation, not a blocker.

The chunking fix (1) unblocks large books. The section-mode fix (2) is scoped narrowly so it does not cascade through downstream code.

### Why a nested-folder layout was rejected

A nested layout (chapters→sections→episodes) would have rippled through every downstream tool. The invariant that keeps the pipeline tractable is:

> One episode = one chapter file = one contract = one NotebookLM upload.

Every downstream tool (`extract_chapter.py`, `build_episode_txt.py`, `podcast-challenger`, `podcast-trainer`) assumes that invariant. Sections are just named episodes with a suffix (`ch03a-foo.txt`, `ch03b-bar.txt`) and a back-reference (`source_chapter_ref: ch03`, `section_index: 1`) inside their contract. The series-plan surfaces a source→episode map for human review. Nothing downstream needs to know whether `ch03a-` came from a whole source chapter or half of one.

### Fix 1 — Chunked Phase 0b/0c (`scripts/podcast/_chunking.py`)

- Paragraph-aligned windows of ~3000 words (0b) / ~8000 words (0c), with a 120-word context-overlap block prepended to every continuation.
- Per-window `claude -p` calls (10-min timeout each, well under the 30-min ceiling).
- **Checkpointed:** every window writes `_chunks/0b/win-NNN.in.md` (input provenance) and the model writes `win-NNN.out.md` (its output). On `--resume`, windows whose `out.md` already exists and is non-empty are skipped. Crash-safe.
- Stitching strips common LLM preambles ("Here is the refined text:") and stray markdown fences before assembling the final `refined-english.md` / `_phonetics.md`.
- `_phonetics.md` merge dedupes by first column (term, case-folded), preserving first-occurrence order across windows.

Validated on the real `kitab-al-riyad/raw-extract.md`: 32 windows, mean 2873 words, with `<!-- context-overlap from prior window -->` blocks on windows 2–32. Total throughput ~92k words.

### Fix 2 — Phase 0d `unit_mode` (`chapter | section | auto`)

- New state config `state.config.unit_mode`, written at initial-run time from `--unit-mode` (default `auto`).
- The Phase 0d prompt branches:
  - `chapter` — one episode per source chapter, never split. Small books / short chapters.
  - `section` — split every source chapter into sections sized to the tier band.
  - `auto` — per-chapter decision; split only when source word count exceeds 1.5× the tier upper bound. Recommended default.
- Section episodes named `ch03a-`, `ch03b-`, `ch03c-`. Each contract gets `source_chapter_ref` + `section_index`.
- When `unit_mode != chapter`, Phase 0d also writes `_system/source/text/source-chapter-map.md` (pipe table of source-chapter → episodes), embedded into the 0f series-plan for human review.

### Operator ergonomics — `--retry-phase`

Resetting a failed phase used to require hand-editing `orchestrator-state.json`. New flag:

```bash
python3 scripts/podcast/orchestrate_book.py --resume <slug> --retry-phase 0b
```

Sets the named phase to `pending`, clears any downstream `completed` markers in the authoring band (0b → 0e), and resumes. The chunking checkpoint means a retried 0b/0c reuses any already-completed windows.

### Driving `kitab-al-riyad` from the current state (0a complete, 0b pending)

```bash
git checkout book/kitab-al-riyad
python3 scripts/podcast/orchestrate_book.py --resume kitab-al-riyad
```

Window-processes 0b (~32 windows, ~5 min each on a stable connection) into `refined-english.md`, then chunks 0c into `_phonetics.md`, then 0d (with `unit_mode=auto`) into the contracts + chapter txts, then 0e, then halts at 0f for series-plan review.

**Note:** the P0 fix (`--permission-mode acceptEdits` + hardened artifact check) MUST be applied before this resume — see `podcast-plan.yaml` P0.1/P0.2.

### Files touched in this fix

- NEW: `scripts/podcast/_chunking.py`
- CHANGED: `scripts/podcast/_authoring.py` (phases 0b, 0c, 0d rewritten)
- CHANGED: `scripts/podcast/orchestrate_book.py` (CLI flags, state config, series-plan template, `--retry-phase`)
- CHANGED: `scripts/podcast/_progress.py` (version bump to 1.2)

## 8. System check snapshot — 2026-05-19

Verified by the repo-surgeon evidence sweep. Refresh before each batch.

| Domain | Status | Detail |
|---|---|---|
| Azure CLI | ✅ logged in | `Journal AI — primary` (subscription `3440564d-c056-4173-bec6-7af92dbece77`) |
| Azure Doc Intelligence | ✅ provisioned | `journal-docintel` (FormRecognizer, eastus, rg-journal-ai) |
| Azure Translator | ✅ provisioned | `journal-translator` (TextTranslation, eastus, rg-journal-ai) |
| Azure Speech | ✅ provisioned | `journal-speech` (SpeechServices, eastus, rg-journal-ai) |
| Claude CLI | ✅ 2.1.144 | `/Users/ahmac/.nvm/versions/node/v24.15.0/bin/claude` |
| Python | ✅ 3.14.4 | system python |
| Node | ✅ v24.15.0 | nvm |
| gh CLI | ⚠️ unauthenticated | non-blocking for plan work; needed for PR ops |
| Git | ✅ clean | branch `develop`, fast-forwarded to `origin/develop` |
| Orchestrator runs | ✅ none active | `pgrep -fl 'orchestrate_book|claude -p'` empty |
| `kitab-al-riyad` state | ✅ resumable | phase `0a` complete; `0b` pending; no orphan chunks |
| Podcast→journal feeds | ✅ none | boundary holds in current code; CI lock-down in P0a |
| Duplicate agents | ⚠️ migration needed | `podcast-challenger`/`podcast-extract`/`ui-reviewer` missing from `.github/agents/` |
| E2E tests | ❌ absent | only unit + integration tests exist; P0b creates the harness |
