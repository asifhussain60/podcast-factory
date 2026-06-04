# KASHKOLE Pipeline — Efficiency Improvements for Future Books
*Standalone brief for Claude Sonnet. Self-contained — no prior context needed.*

---

## Background: What Was Built and What It Cost

The KASHKOLE corpus (122-chapter Urdu scholarly compendium) was processed through a
3-phase pipeline before podcast intake:

| Phase | Tool | Service | Actual Cost |
|---|---|---|---|
| Phase 1 — Translate | `tools/content_translator/stages/translate.py` | Azure Translator v3 | **$38.37** |
| Phase 2 — Adapt | `tools/content_translator/stages/adapt_auto.py` | `claude -p` (Max plan) | **$0 billed / ~$17.40 tracked** |
| Phase 3 — Challenge | `tools/content_challenger/wisdom/challenge_auto.py` | `claude -p` (Max plan) | **~$0.43** |

**The problem discovered:** Phase 2 used `claude -p` (subprocess calls to the Claude CLI),
which draws from the Max plan's weekly token limit. Running 215 sequential calls overnight
on 122 chapters exhausted the weekly "All models" limit (100% used), then continued billing
**$466.27 in usage credits** because Auto-reload was enabled. The Max plan is designed for
interactive use; batch pipeline processing should never share that pool.

---

## The Architectural Fix

**Decouple all batch pipeline processing from the Max plan.**

All `claude -p` subprocess calls in the pipeline should be replaced with direct Anthropic
API calls using a **separate API key** with its own monthly spend cap set at
`console.anthropic.com`. The Max plan remains clean for interactive Claude Code sessions.

### Current pattern (adapt_auto.py, line 94):
```python
def _call_claude_p(user_content: str, timeout: int = 1800) -> tuple[str, int, int]:
    """Shell out to `claude -p` (Max subscription — no API key, no quota)."""
    full_prompt = SYSTEM_PROMPT + "\n\n---\n\n" + user_content
    result = subprocess.run(
        ["claude", "-p", full_prompt, "--tools", "", "--no-session-persistence"],
        capture_output=True, text=True, timeout=timeout, check=False,
    )
    return result.stdout.strip(), 0, 0   # ← token counts unavailable, burns Max plan
```

### Target pattern (direct API, returns real token counts):
```python
import anthropic

def _call_api(user_content: str) -> tuple[str, int, int]:
    """Direct Anthropic API call — separate key, metered, capped."""
    client = anthropic.Anthropic(api_key=_get_api_key())   # from keychain
    message = client.messages.create(
        model=MODEL,
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )
    in_tok = message.usage.input_tokens
    out_tok = message.usage.output_tokens
    return message.content[0].text, in_tok, out_tok
```

The `anthropic` package is already installed in the wisdom venv (`anthropic>=0.104`).
The API key should be stored in macOS keychain as `anthropic-pipeline-key` (separate from
any key used by Claude Code itself) and retrieved with:
```python
import subprocess
def _get_api_key() -> str:
    result = subprocess.run(
        ["security", "find-generic-password", "-s", "anthropic-pipeline-key", "-w"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError("anthropic-pipeline-key not found in keychain. Run: "
                           "security add-generic-password -s anthropic-pipeline-key -a pipeline -w <key>")
    return result.stdout.strip()
```

---

## Three Compounding Optimizations (stack in this order)

### Optimization 1 — Prompt Caching (implement first, easiest)

The `SYSTEM_PROMPT` in `adapt_auto.py` is identical across every chapter call. With
Anthropic prompt caching, the repeated system prompt prefix is billed at 10% of normal
input cost after the first call per session.

```python
message = client.messages.create(
    model=MODEL,
    max_tokens=8192,
    system=[
        {
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},  # ← cache this prefix
        }
    ],
    messages=[{"role": "user", "content": user_content}],
)
```

**Estimated saving:** 30–40% on input token costs across a full corpus run. The system
prompt is ~1,500–2,000 tokens; across 215 calls that's ~400K tokens billed at full rate
today, vs ~40K with caching.

### Optimization 2 — Message Batches API (implement second, for non-real-time phases)

Phases 2 and 3 are not real-time. You don't need results while the job runs — you check
back the next day. The Anthropic Batches API is **50% cheaper** than synchronous calls
and designed exactly for this.

```python
import anthropic

client = anthropic.Anthropic(api_key=_get_api_key())

# Build one batch request per chapter
requests = []
for binder_id, chapter_id in pending_chapters:
    requests.append({
        "custom_id": f"b{binder_id}-c{chapter_id}",
        "params": {
            "model": MODEL,
            "max_tokens": 8192,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": _build_user_msg(binder_id, chapter_id)}],
        }
    })

# Submit entire corpus in one call
batch = client.messages.batches.create(requests=requests)
print(f"Batch submitted: {batch.id}. Poll tomorrow.")

# Next day — poll and process
batch = client.messages.batches.retrieve(batch.id)
if batch.processing_status == "ended":
    for result in client.messages.batches.results(batch.id):
        _write_adapted_output(result.custom_id, result.result.message.content[0].text)
```

The batch driver already exists at `_workspace/plan/_drivers/wisdom_adapt_all.py` —
it just needs to submit to the Batches API instead of running 215 sequential subprocesses.

**Estimated saving:** 50% off all Phase 2 + Phase 3 costs.

### Optimization 3 — Chapter Count Cap per Session (safety net)

Add `--max-chapters N` to all batch drivers so a runaway overnight job cannot exceed
a set number of chapters before stopping and requiring a manual restart. The current
`SESSION_COST_CAP = $30.00` check doesn't work with Max plan calls (cost shows $0.00).

```python
# In wisdom_adapt_all.py main():
ap.add_argument("--max-chapters", type=int, default=50,
                help="Stop after N chapters to limit per-session token spend")

# In the chapter loop:
if chapters_done >= args.max_chapters:
    print(f"Chapter cap {args.max_chapters} reached. Re-run to continue (idempotent).")
    sys.exit(0)
```

---

## Cost Comparison: Current vs Improved

For a 122-chapter corpus similar to KASHKOLE:

| Approach | Phase 2 (Adapt) | Phase 3 (Challenge) | Total pipeline |
|---|---|---|---|
| Current (`claude -p` Max plan) | $0 billed + $466 overflow | ~$0.43 | **$466+** |
| Direct API, no optimizations | ~$140 | ~$7 | **~$147** |
| Direct API + prompt caching | ~$85 | ~$4 | **~$89** |
| Direct API + caching + batches | ~$42 | ~$2 | **~$44** |

For comparison: Phase 1 (Azure Translate) stays at ~$38 regardless. Total end-to-end
cost per 122-chapter book with all optimizations: ~**$80–85**.

---

## Files to Change

| File | Change needed |
|---|---|
| `tools/content_translator/stages/adapt_auto.py` | Replace `_call_claude_p()` with `_call_api()` using direct client + cache_control on system prompt |
| `tools/content_challenger/wisdom/challenge_auto.py` | Same — replace `claude -p` subprocess with direct API call |
| `_workspace/plan/_drivers/wisdom_adapt_all.py` | Add `--max-chapters` cap; optionally refactor to submit Batches API |
| `_workspace/plan/_drivers/wisdom_challenge_all.py` | Same cap + optional batch submission |

No changes needed to: Phase 1 translate (Azure, already direct API), source extractor
(local DB query, no LLM), bundle.yml schema, or the downstream podcast pipeline.

---

## For Future Books Beyond KASHKOLE

The same pattern applies to every book that goes through a translate → adapt → challenge
preprocessing step before podcast intake:

1. Phase 1 (Azure Translate): keep as-is, already direct API, $10/M chars is good value
2. Phase 2 (adapt): direct Anthropic API + prompt cache + batch submission
3. Phase 3 (challenge): direct Anthropic API + batch submission
4. Podcast pipeline phases 0a–0f: these already use the orchestrator's own model calls;
   apply the same direct-API + cache pattern to `scripts/podcast/orchestrate_book.py`
   if those phases are also currently using `claude -p` internally

**Rule of thumb for future planning:** Any pipeline stage that fires more than 10 LLM
calls unattended should use the direct API with a spend cap, never `claude -p`. The Max
plan is for the human operator — conversations, reviews, one-off tasks. The pipeline is
infrastructure and should be budgeted separately.

---

## Keychain Setup (one-time, run once before first direct-API book)

```bash
# Add a dedicated pipeline API key (get from console.anthropic.com → API Keys)
security add-generic-password -s anthropic-pipeline-key -a pipeline -w sk-ant-...

# Verify
security find-generic-password -s anthropic-pipeline-key -a pipeline -w
```

Set a monthly spend cap on this key at `console.anthropic.com/settings/limits`.
Recommended starting cap: **$50/month** — covers ~1,200 chapters of adapt + challenge
with all optimizations, well above any realistic monthly throughput.
