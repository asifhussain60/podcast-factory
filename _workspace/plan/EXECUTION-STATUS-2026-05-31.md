# 13-Step Plan Execution — Handoff State (2026-05-31)

Branch: `develop` (pushed)
Last commit: `279a21e`

## Completed this session

| # | Commit | Description |
|---|---|---|
| Policy | `f6394f8` | Retired two-agent directory lane lock + plan-first execution gate. Repo is now LLM-framework-agnostic. |
| Step 1 | `16c220a` | **WC1 fix**: atoms.tradition column-shift bug. Root cause = migration 021 `INSERT OR IGNORE INTO atoms_v21 SELECT * FROM atoms` (positional, no column list) after migration 020 ALTER ADD COLUMN appended `tradition` last. Patched migration 021 with explicit column list; new migration 022 repairs live DB by rebuilding tradition from body JSON. 628 doctrine atoms now correctly tagged `fatimid-ismaili` (was timestamp strings). Augmenter doctrine-injection query: 0 → 628 atoms. |
| Step 2 | `279a21e` | Marked Waves A, B, G as `completed_2026_05_31` in `_workspace/plan/refactor/plan.yaml`. Regenerated dashboard snapshots. |

All 70 unit tests green. Lint baseline 0 errors / 52 warnings.

## Pending steps (resume here)

In execution order:

1. **Step 4 — J0 MCP source-library server** (≈400L FastAPI + stdio dual-interface at `scripts/mcp/source_library_server.py`, port 4390). Reads from `content/knowledge-base/knowledge.db` + `CONTENT/_shared/source-library/mirror.db`. **Blocks** steps J2/J3/J4/J5.
2. **Step 6 — J2 popover rewire**: `plan-dashboard/src/components/.../QuranPopover.tsx` + `TermPopover.tsx` → local MCP endpoint (drop external API dependency).
3. **Step 7 — K6 Interest axis + voice exemplar fix**: `_voice_score()` in `scripts/podcast/_quality.py` currently returns `0.0` unconditionally (no KSessions exemplar vectors). Build the exemplar set + wire scoring.
4. **Step 8 — WC2 → WC3 → WC4** annotation/knowledge/curation chain.
5. **Step 9 — Ayyuhal Walad G2 gate**: 3 orphan episodes (WC8 holistic 3-episode structure vs legacy 5-chapter). `validate_ship_ready.py books/ayyuhal-walad` shows episodes without chapters = `frame-and-the-problem-of-knowledge`, `the-disciplines-of-the-path`, `the-guiding-shaykh-and-final-counsels`. Need to reconcile `chapters/` dirs with `episode-chapter-map.json`.
6. **Step 10 — H2 file splits** (DR-005, 600L cap). Eight violators in `scripts/podcast/`:
   - `build_episode_txt.py`
   - `extract_chapter.py`
   - `tighten_source.py`
   - `run_wave.py`
   - `_slide_convergence.py`
   - `source_library_mirror.py`
   - `_slide_authoring.py`
   - `publish_to_library.py`
7. **Step 11 — H3 wave chain driver** completion.
8. **Step 12 — WC8-5c host roles guardrail** (pipeline + UI).
9. **Step 13 — WC8-7b video layer** — **Tier-2, needs authorization**.

## User's standing direction

Asif previously approved option A (autonomous execution of remaining steps with red-green test cycle between each, halting only for genuine Tier-2 actions). The pause was for the machine handoff, NOT a withdrawal of that authorization. On resume: proceed with Step 4 (J0 MCP server) unless Asif redirects.

## Key references

- Plan: `_workspace/plan/refactor/plan.yaml` + `.md`
- Architecture: `_workspace/plan/architecture.md`
- Live DB: `content/knowledge-base/knowledge.db` (tracked in git, now repaired)
- Mirror DB: `CONTENT/_shared/source-library/mirror.db` (gitignored)
- Session log to append to: `_workspace/plan/copilot-handoff.md`
