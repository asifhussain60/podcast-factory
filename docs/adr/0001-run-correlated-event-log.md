# ADR 0001: Run-correlated structured event log for the podcast orchestrator

**Status:** Accepted with amendments — step 1 implemented 2026-07-31
**Date:** 2026-07-31
**Scope:** `scripts/podcast/orchestrate_book.py` and its phase / authoring modules
**Decision driver:** Make each autonomous book run produce one durable, machine-readable trail that a human — or Claude — can open after the fact to pinpoint *which step failed and why*, without re-running.

> **Amendment note.** The original proposal was reviewed against the code on 2026-07-31. Four of its claims were verified as written; five things changed. Each amendment is marked **[A1]**–**[A5]** at the point it applies, and the reasoning is collected in section 7.

---

## 1. Context

`orchestrate_book.py` is not a linear script. It is a resumable state-machine driver over a phase sequence (`pre-flight -> branch -> scaffold -> 0a...0e -> 0literary -> per-chapter -> publish -> merge`), where the LLM-authoring phases shell out to `claude -p` via `_authoring/_core.py`. Work is spread across ~250 scripts and a dozen extracted phase modules under `scripts/podcast/phases/` and `scripts/podcast/_authoring/`.

Observability already exists, but it is **fragmented and uncorrelated**:

| Artifact | What it captures | Gap |
|---|---|---|
| `_system/orchestrator-state.json` | Atomic, versioned per-phase status, `last_error`, cost, wall-clock | A *checkpoint*, not a timeline — no narrative of what happened *inside* a phase |
| `_learning/findings.jsonl` | Challenger findings | Convergence findings only; not phase/step events |
| `_system/cost-ledger.jsonl` | Per-`claude -p` tokens | Cost only; not tied to a run timeline. **Written on success only** |
| `_workspace/logs/orchestrator-<slug>.log` | Full stdout/stderr + watchdog events | **Only when launched through the watchdog** (`watch_orchestrator.sh` pipes through `tee`). Direct runs lose it. Unstructured; no phase/chapter keys |

So the problem is **not** "there is no logging." It is that (a) the signal is scattered across four artifacts, (b) nothing correlates them to a single run, and (c) the console narrative is ephemeral outside the watchdog.

### 1.1 The sharper problem: instrumentation is wired to the success branch **[A2]**

The original draft called seam 2 "the highest-value capture" on the grounds that a generic logger is blind inside LLM calls. The real reason is worse and more specific.

In `_authoring/_core._run_claude_p`, a **successful** call wrote two artifacts: a cost-ledger row and a model-provenance row. A **failed** call wrote nothing at all:

- non-zero return code: stdout and stderr were handed back to the caller and evaporated;
- `subprocess.TimeoutExpired`: raised as `AuthoringError("LLM call timed out after Ns")`, and the partial child output carried on the exception object was **discarded unread** — despite being, very often, the only evidence of *why* the call hung;
- binary missing: no record.

The longest-running, highest-cost, most failure-prone operation in a multi-hour autonomous run therefore kept evidence exactly when it was not needed and none when it was. That inversion — not the absence of a logging framework — is the defect this ADR closes.

### 1.2 Prior art in this repo: `run_telemetry`

`_db.py` already defines `run_telemetry_repository` (`start_run` / `complete_run` / `total_cost`, keyed by `run_id`). It has **zero production callers**. A run-correlation surface was built here once and never wired to anything that a human reads. That outcome shapes the rollout order in section 5: the piece with a human reader ships first.

### 1.3 Rejected approach: global file logger

A `logging.basicConfig(filename=...)` bolted across the phase modules produces one interleaved text file with no notion of which book / phase / chapter / convergence pass a line belongs to. That is close to useless for post-hoc debugging, and it re-implements what `state.json` and the watchdog tee-log already do. Rejected.

---

## 2. Decision

Add a **run-correlated structured event log**: a `run_id` stamped into `state.json` at run start, and one JSONL event appended per meaningful step. Route the existing print/transition/LLM chokepoints through a single `log_event()` helper that **keeps printing to console** and **also** appends the structured record. Keep `state.json` as the source-of-truth *checkpoint* and the JSONL as the *narrative timeline* — complementary, not competing.

### 2.1 Event schema (one JSON object per line)

```json
{
  "ts": "2026-07-31T14:02:11.442Z",
  "run_id": "20260731T140158Z-a1b2c3",
  "book_slug": "the-forty-hadith",
  "phase": "0d",
  "chapter": "EP03-patience",
  "event": "claude_p.call",
  "level": "info",
  "step": "ch03-design",
  "model": "claude-opus-4-7",
  "rc": 0,
  "duration_ms": 48210,
  "tokens_in": 91204,
  "tokens_out": 8140,
  "msg": "",
  "prompt_sha256": "9f2c...",
  "stdout_tail": "...last 800 chars...",
  "stderr_tail": "",
  "prompt_dump": null
}
```

Rules: `chapter` is `null` outside the per-chapter loop. `level` is one of `debug|info|warn|error`. JSONL (not a JSON array) so it is append-only, crash-safe, and streamable. Greppable with `jq 'select(.level=="error")'` — which is the whole point.

**[A2]** `cost_delta_usd` is dropped in favour of `tokens_in` / `tokens_out`. On the flat-rate Max subscription the marginal dollar cost of a `claude -p` call is always `0.0`, so the field carried no signal; token counts do (a truncated or abridged response shows up as an anomalous `tokens_out` before it shows up in the prose).

### 2.2 Location **[A1]**

`_workspace/runs/<slug>/<run_id>.jsonl` — **not** `content/<Bucket>/<slug>/_system/`.

The original leaned toward `_system/` "so a book's trail moves with its branch", describing it parenthetically as git-ignored. It would not have been: `_system/` is not broadly ignored, and sibling files there (`cost-ledger.jsonl` among them) are tracked and committed. Per-run JSONL carrying stdout excerpts would have been committed on every book branch and merged into `develop` — merge noise, repo bloat, and prompt content in permanent history. `_workspace/runs/` was already reserved and git-ignored for exactly this class of artifact. Trail-travels-with-the-branch also turns out to be an anti-feature: run logs inherited through a merge are somebody else's debugging noise.

The one human-facing artifact, `_system/last-failure.md`, does live with the book (that is where a person looks, next to the state file) and is git-ignored alongside `_system/watchdog.json`, which is the same class of thing.

### 2.3 The three seams

1. **`_progress.update_phase(book_dir, *, phase, status, error, extras)`** — every phase transition already funnels through this one function (**verified: 135 call sites across 8 production modules**). Emits `phase.<status>` alongside the existing `write_state`, and stamps `run_id` into the state dict so checkpoint and timeline share a key.

2. **`_authoring/_core._run_claude_p(...)`** — the single LLM shellout (**verified: 41 call sites across 19 production modules**); already receives `book_dir/phase/step/model` and already appends to the cost ledger, so the event slots in beside an existing hook. Emits `claude_p.call` (success and non-zero rc), `claude_p.timeout`, `claude_p.missing_binary`. **This is the highest-value capture**, for the reason in section 1.1.

3. **`_subprocess.info` / `_subprocess.err`** **[A3]** — *not* `orchestrate_book._info` / `_err` as originally proposed. Those two are local duplicates (`orchestrate_book.py:202-207`) with 5 and 13 call sites between them. The real chokepoint is `_subprocess.py:28,33`: thirteen modules import it, and the phase drivers thread it downward as the `log=` callable into every authoring phase (`author_phase_0b(bd, log=_info)` and siblings), giving roughly 265 narration sites. Same one-function edit, about fifteen times the coverage. The orchestrator's duplicate pair should be deleted in favour of importing the shared one.

### 2.4 Prompt bodies: hash by default, full body on failure **[A4]**

The original asked hash-only vs. full-behind-a-flag. Neither: hash-only is right for the success path and useless for the failure path, because you cannot diff a prompt you no longer have — and a `--verbose-log` flag has to be set *before* the failure you did not predict.

So: `prompt_sha256` on every event, and on a **failed** call only, the complete prompt plus both full streams are written to a sidecar at `_workspace/runs/<slug>/<run_id>.<step>-<hhmmss>.failure.txt`, with the event carrying its path in `prompt_dump`. Bounded excerpts (800 chars) in the timeline; complete evidence exactly where it is needed, and nowhere else.

### 2.5 Rich failure dump

On any phase `failed`/`halted`, `update_phase` writes `_system/last-failure.md`: the failing phase and its `last_error`, the last `claude_p.*` event with rc / duration / tokens / stream excerpts / sidecar path, the tail of the run timeline, and the exact `--resume ... --retry-phase ...` command to continue. One file to read instead of four to cross-reference.

### 2.6 Configuration and safety

`log_event()` lives in **`scripts/podcast/_runlog.py`** **[A5]**, re-exported from `_progress.py` so every name stays importable there. The original placed it *in* `_progress.py` as "already the state/observability module" — which pushed that file to 642 lines and tripped the repo's own DR-005 pre-commit gate (600-line module limit). The gate was right: state-machine writing and run narration are separate concerns that happened to share a neighbourhood. The split follows the established DR-005 pattern in this repo (extract verbatim, re-export one line per name), and a test pins both modules under the limit so the split cannot silently undo itself.

It is module-level context, not `basicConfig` sprinkled per module, and it **initialises lazily**: any call carrying a `book_dir` mints the `run_id` if nothing has yet, which removes an entire class of "forgot to initialise" bugs and means `main()` needs no edit for the log to work. An explicit `init_run_log()` remains exported for a true run-start stamp.

Before init, and whenever the book is unknown, `log_event` is a silent no-op, so importing phase modules in isolation never crashes.

**Enablement guard.** The log engages only for a book under the repo's content root, unless `PODCAST_RUN_LOG=1|0` forces it. Without this, the ~170 existing unit tests that drive `update_phase` against temp directories write junk into the developer's real `_workspace/runs/` — which they did, once, before the guard was added.

**Every** logging call is individually wrapped: an I/O error degrades to a console warning and never propagates. A broken log must not turn a working phase into a failed one.

### 2.7 Retention **[A4]**

`_workspace/runs/<slug>/` keeps the last 10 runs, **plus the newest run containing an error**, which is never pruned. Recency alone is the wrong eviction key: one failed run's log is worth more than nine clean ones. Failure sidecars are pruned with their parent run.

---

## 3. Consequences

**Positive.** One correlated timeline per run. LLM failures — including timeouts — now persist evidence where previously they persisted none. A single failure artifact for triage. Works whether launched directly or via the watchdog. Builds on existing seams. `state.json` semantics are unchanged apart from an additive `run_id` key, so `--resume` and `--status` are unaffected.

**Costs / risks.** A new artifact family to maintain and document. Stream excerpts are size-bounded to avoid bloating logs with full transcripts. The failure sidecar contains full prompt bodies — acceptable because it is git-ignored, local, pruned, and written only on failure.

**Honest limitation.** This is pure observability with zero behaviour change. It makes *debugging* deterministic; it does not make the *pipeline* more robust, and should not be described as if it does. Its regression surface is correspondingly near-nil: the only genuinely new failure mode is the logging path itself, which is why every call is wrapped and the guarantee is regression-tested.

**Known gap.** `fill_glossary_arabic.py` declares its own `CLAUDE_CMD` and shells out independently of `_run_claude_p`, so seam 2 does not observe it. Either route it through `_run_claude_p` or accept the blind spot deliberately.

**Explicitly out of scope.** No dashboard/UI. No cross-run analytics. No external tracing backend.

---

## 4. Alternatives considered

- **`structlog`** — reasonable if the hand-rolled shim outgrows itself; adds a dependency for what is currently a small module. Revisit if event volume or config grows.
- **OpenTelemetry** — the correct answer for *distributed* systems and when a tracing UI is wanted. The span model fits phases, but the operational weight (collector, exporters) is unjustified for a local single-user CLI.
- **Langfuse / LangSmith** — purpose-built LLM tracing, genuinely relevant given how LLM-heavy this pipeline is, and the closest match to seam 2's intent. Cloud-leaning and heavier than "debug my runs locally." A strong candidate later for prompt-level analytics across books.

Decision: start with the JSONL shim — owns the data locally, near-zero deps, directly readable by Claude. The `claude_p.*` event shape is deliberately Langfuse-shaped, so exporting later is a mapping, not a rewrite.

---

## 5. Rollout **[A2]** — re-ordered so the human-readable piece ships first

The original ordered this shim-first, seams next, `last-failure.md` fourth. That is the order that produced a dead `run_telemetry` table (section 1.2): three steps of plumbing before anything a person would open. Re-ordered so step 1 is independently valuable on its own and everything after it is optional polish.

1. **DONE (2026-07-31)** — `log_event()` + `run_id` minting + lazy init + no-op fallback + enablement guard in `_runlog.py`; seam 2 wired in `_run_claude_p` (success, non-zero rc, timeout with partial-output capture, missing binary); failure sidecars; `last-failure.md`; retention with failed-run preservation. Seam 1 is included because `last-failure.md` needs a trigger and a phase spine to be worth reading, and it is the same single function. Tests: `scripts/podcast/tests/test_run_log.py` (22 tests) — well-formed emission, `run_id` stamping, I/O errors not propagating, `update_phase` surviving a broken log, timeout partial-output capture, retention keeping the failed run, the enablement guard, and the module split staying under the line gate.
2. Seam 3 — route `_subprocess.info`/`err` through `log_event`; delete the orchestrator's duplicate pair.
3. `orchestrate_book.main()` mints the `run_id` explicitly at true run start (lazy init already covers correctness; this only tightens the start boundary).
4. `watch_orchestrator.sh` prints the `run_id` and JSONL path at launch so the tee-log and the structured log cross-reference.
5. Decide the `fill_glossary_arabic.py` blind spot.

Each step is independently shippable and reversible.

---

## 6. Verification status

| Original claim | Outcome |
|---|---|
| `update_phase` is the single phase funnel | Confirmed — `_progress.py:244`, 135 call sites, 8 modules |
| `_run_claude_p` is the single LLM funnel | Confirmed — `_core.py:245`, 41 call sites, 19 modules |
| Cost hook sits where the event belongs | Confirmed |
| Tee-log exists only under the watchdog | Confirmed — `watch_orchestrator.sh:217` |
| `orchestrate_book._info`/`_err` is the console chokepoint | **Wrong** — see [A3] |
| `_system/runs/` would be git-ignored | **Wrong** — see [A1] |
| `log_event()` can live in `_progress.py` | **Wrong** — breaches the 600-line module gate; see [A5] |

## 7. Amendments

- **[A1] Location.** `_workspace/runs/` (already reserved and git-ignored), not `_system/` (tracked, would be committed on every book branch).
- **[A2] Framing, schema, and order.** Lead with the success-only instrumentation defect; tokens instead of an always-zero cost delta; rollout re-ordered so the human-readable failure dump ships in step 1.
- **[A3] Seam 3 relocated.** `_subprocess.info`/`err` (~265 sites), not `orchestrate_book._info`/`_err` (18 sites, themselves duplicates).
- **[A4] Prompt bodies and retention.** Hash always plus full body on failure only, replacing the hash-vs-flag choice; retention preserves the newest failed run rather than pruning purely by recency.
- **[A5] Module.** `_runlog.py`, re-exported from `_progress.py`, because the original placement breached the repo's 600-line DR-005 gate. Discovered by the pre-commit hook, not by review — which is the gate doing its job.
