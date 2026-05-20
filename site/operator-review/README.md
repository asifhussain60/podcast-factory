# Operator Review Studio

Browser SPA for the P22 transcript-review gate. Pairs with `scripts/podcast/review_server.py` FastAPI backend at `localhost:8766`.

**Branch:** `feat/operator-review-studio` (forked off `feat/podcast-w1-foundation` post-P24).

## Quick start

```bash
# 1. Install backend deps (one-time, on your Mac)
pip install fastapi uvicorn pyyaml

# 2. Start the backend (in repo root)
python3 scripts/podcast/review_server.py --repo-root .

# 3. In a second terminal: install frontend + launch dev server
cd site/operator-review
npm install
npm run dev

# 4. Open http://localhost:5173
```

The Vite dev server proxies `/api/*` → `http://localhost:8766` so the browser stays same-origin. Production builds (`npm run build`) emit static assets to `dist/`.

## Multi-worktree mode

Single-worktree (default): `--repo-root <path>` or runs from current dir.

Multi-worktree: create `~/.journal-worktrees.yaml`:

```yaml
worktrees:
  - ~/Code/Journal
  - ~/Code/Journal-book-asaas
  - ~/Code/Journal-feat-w1
```

Then: `python3 scripts/podcast/review_server.py --config ~/.journal-worktrees.yaml`. Books from all paths appear in one list.

## Architecture

```
Browser SPA (Vite/React/TS)         FastAPI backend (Python)
  src/main.tsx                        scripts/podcast/review_server.py
       │                                  │
       │ fetch /api/* ─────────────────▶ │ ROUTES
       │                                  │   • list books
       │                                  │   • get/put operator-review.md
       │                                  │   • approve + fire resume (subprocess)
       │                                  │   • SSE resume log
       │                                  │   • 10 AI features → claude -p subprocess
       │                                  │
       │                                  ▼
       │                              scripts/podcast/
       │                                _review_serializer.py   (md ↔ struct)
       │                                _review_ai.py           (claude -p wrappers)
       │                                _cost_ledger.py         (existing)
       │
       └─ writes/reads ──────────────▶ content/podcast/library/books/<slug>/
                                          operator-review.md   ← THE SOURCE OF TRUTH
                                          _system/source/text/refined-english.md
                                          state.json
                                          _system/ai-cache/    (per-source-signature)
                                          _system/cost-ledger.jsonl
```

**Persistence model:** `operator-review.md` stays the single source of truth that the pipeline reads on `--approve-transcript` resume. The studio writes atomically (tmp + fsync + rename). Crash-safe drafts live in `localStorage` (key `review-draft:<slug>`). External-edit detection via mtime polling every 5 sec.

## AI features (P25.7)

Ten helper features wired through `claude -p` subprocess — **no new API keys**. Operator's existing Claude CLI auth is reused:

| Feature | Model | Cost / book | Trigger |
|---|---|---|---|
| Per-page summaries | Haiku | ~$0.05 | AI bar "Per-page summaries" |
| Diff-with-raw explainer | Sonnet | ~$0.20 | Hover any `.diff-changed` span |
| Arabic-term highlighting | Sonnet | ~$0.15 | AI bar "Highlight Arabic" |
| Pre-flight scan | Sonnet | ~$0.30 | Cmd-K |
| Voice-shift detection | Sonnet | ~$0.18 | AI bar |
| Episode plan (Opus) | Opus | ~$0.50 | AI bar |
| Suggested flags | Sonnet | ~$0.20 | AI bar "Suggest flags" |
| Smart note autocomplete | Haiku | ~$0.02 | While typing in any textarea |
| Auto-categorize notes | Haiku | ~$0.01 | After saving a note |
| Content-range recommender | Haiku | ~$0.01 | Auto on §7 focus |

Per-book budget: **~$1.62 total**, enforced at $2.00 hard cap by `scripts/podcast/_review_ai.py`. Cost-ledger captures every call (`agent_id=podcast-review-studio`).

Whole-book features are **cached per source-signature** (sha256 of `refined-english.md`). Re-runs are free until the source changes.

## Plan tracking

This work lives in plan phase **P25** — see [`_workspace/plan/podcast-plan.yaml`](../../_workspace/plan/podcast-plan.yaml) `phases[id: P25]`. Six core tasks (P25.1-P25.6) + AI layer (P25.7). Halt-with-DoR runner at [`scripts/podcast/phases/p25_1.py`](../../scripts/podcast/phases/p25_1.py).

## Keyboard shortcuts

| Cmd-F | Search transcript |
| Cmd-P | Jump to page |
| Cmd-D | Toggle diff-with-raw |
| Cmd-L | Flag selected text |
| Cmd-K | AI pre-flight scan |
| Cmd-+ / Cmd-- | Font size up/down |
| Cmd-↩ | Approve & Resume |
| ? | Help overlay |
| ESC | Close overlays |

## Visual style

CORTEX-aligned dark canvas + glassmorphism + Plus Jakarta Sans + Space Grotesk + Lato for reading. Three reader themes (Dark / Sepia / Light). Four reading fonts (Lato / Cormorant / Lora / OpenDyslexic). Three content widths and line-spacings. All controls remember their last value across sessions via localStorage.

Built by [CORTEX](https://asifhussain60.github.io/CORTEX/) — the framework that powers this studio.
