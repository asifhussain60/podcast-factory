# Wave 8 — §0 Senior-Architect Review

*Date: 2026-05-30. Reviewer: Claude Code (Sonnet 4.6) on behalf of the wave.*

**Canonical §0 audit:** [`_workspace/reviews/reports/2026-05-30-full-repo-audit.md`](../reviews/reports/2026-05-30-full-repo-audit.md)
(Four-stream architect + senior-engineer review; all findings below are cited from that document.)

---

## Six §0 Questions

**1. Up to par?**
Slices 0–4 and Normalize meet their stated goals at walking-skeleton quality. The Studio PoC
is explicitly throwaway (FC-1 through FC-5 issues documented; no inline styles violated after
WC7 enforcement). The five chapter pipeline (intake → denoise → normalize → augment → narrator)
produces readable artifacts on all five chapters of Ayyuhal Walad at ~$4.80. Three hardening
gaps exist before Wave 8 production-readiness can be claimed:

- **A3** — No Gemini retry on rate-limit (bare `urlopen`, no backoff). Mid-book failure forces
  manual `--retry-phase`.
- **F4** — `StudioPoc.tsx` has hardcoded `SLUG` and `CHAPTERS` array. Not a production blocker
  yet (throwaway PoC), but blocks Slice 6 productionization.
- **E1–E3** — Corpus population: only 1 of 3 sources wired; 92% of atoms have zero topic tags;
  no FTS5 on `knowledge.db`. Augmenter falls back to zero results on most queries.

**2. Regressions?**
No cross-slice regressions visible in the artifact trail. The chapter switcher works across all
five chapters; the six editor tabs render correctly. One latent regression risk: `extractor.py`
still calls `claude -p` (standing rule violation, §1) — the extractor is not yet wired into the
live pipeline (it runs offline), so no spend has leaked, but it MUST be fixed before Slice 4+
runs.

**3. Refactoring — consolidate?**
Five new stage scripts (`intake_stage.py`, `gemini_refine.py`, `transcribe_audio.py`,
`transcribe_all_lectures.py`, `narrator_additions.py`) run parallel to `orchestrate_book.py`.
They are NOT yet integrated into the orchestrator's `PHASE_ORDER`. The audit (§F6) flags this:
`build_episode_txt.py` (1,563 lines) and `extract_chapter.py` (1,301 lines) both exceed DR-005's
600-line cap. Consolidation into `_stages/` is the right seam and is the Slice 6 pipeline
decision (major-dent — bring to Asif). For Wave 8 content work this is not a blocker: the new
scripts can co-exist with `orchestrate_book` through Slice 7, then get folded in at Slice 6.

**4. Enhancements — highest-leverage?**
Two wins before Slice 7:

- **Slice 2-fix** (already in plan): add TERMINUS TECHNICUS guard to `gemini_refine.py` prompts
  so Arabic doctrinal terms (`tawil`, `wilaya`, `batin`) survive denoise/normalize. ~$0.07
  re-run cost. Must land before Slice 7.
- **E2 topic-tag fallback**: applying binder-level tags when `TypeID=0` lifts avg tags per atom
  from 0.076 to ~3–5 and makes the augmenter actually find results. Low effort, high leverage.

**5. Risks**

| Dimension | Risk | Severity |
|---|---|---|
| Scalability | `StudioPoc` loads all chapters server-side; inline reconcile will not scale to 30-chapter books; no FTS5 on `knowledge.db` limits augmenter to tag-only lookup | Medium |
| Extensibility | New source/stage/tradition is NOT yet one-file change — `_paths.py` has dual-tree fallback, three legacy books in wrong folder, `populate_corpus.py` has two commented-out ingest callables | Medium |
| Cost | Per-book cap ($10) does not cover Azure transcription at $4.31; Gemini has no retry/backoff so a single rate-limit doubles spend via manual re-run | Medium |
| Correctness/doctrine | Auto-applied normalize is interpretive; terminus technicus guard is missing (audit §2-fix); 20 Quran refs verified but hadith verification is corpus-lookup, not ground-truth | High — Slice 2-fix MUST land before Slice 7 |
| Security | A1: DB password in `tools/source_extractor/db.py` lines 10–11 is in git history; should move to keychain | High (but offline tool, not in-pipeline for Ayyuhal) |
| Cross-session memory | CLAUDE.md + memory files (`feedback_*.md`) cover all standing rules. One gap: the new stage scripts (intake_stage, narrator_additions, etc.) are not documented in CLAUDE.md or any runbook — a cold-start session would not know which scripts are "new Wave 8 producers" vs "legacy orchestrator phases" | Medium |

**6. Cross-session memory — sufficient for cold start?**
Mostly yes. CLAUDE.md, CONTINUATION-2026-05-30.md, `site-work-status.md`, and the
`orchestrator-state.json` together give a cold-start agent enough context to resume. The one gap
flagged above (new Wave 8 scripts not in CLAUDE.md) is acceptable for Wave 8 content work but
should be addressed before Slice 6 (productionization documentation pass).

---

## Severity-Ranked Findings

| # | Severity | Finding | Required Before |
|---|---|---|---|
| 1 | CRITICAL | `extractor.py` calls `claude -p` — standing rule violation | Slice 4+ |
| 2 | HIGH | Terminus technicus stripped during denoise/normalize | Slice 7 |
| 3 | HIGH | DB password plaintext in git (`tools/source_extractor/db.py:10`) | Next keychain pass |
| 4 | MEDIUM | 92% of corpus atoms have zero topic tags → augmenter returns nothing | Slice 4+ |
| 5 | MEDIUM | No Gemini API retry on rate-limit | Before multi-chapter runs |
| 6 | MEDIUM | `content/drafts/BOOKS/` legacy tree still has 3 books not migrated | Slice 6 restructure |
| 7 | LOW | New Wave 8 scripts not documented in CLAUDE.md | Before Slice 6 |

---

## Verdict

**GO** for autonomous Wave 8 content work, with two preconditions:

1. **Fix `extractor.py` `claude -p` → Gemini before Slice 4+ runs** (this is Blocker C in the
   current task — being resolved in this commit).
2. **Land Slice 2-fix (terminus technicus guard in `gemini_refine.py`)** before Slice 7 output
   runs. The plan already carries this as `K6-pre` (priority: `critical_before_slice_7`).

All other findings are tracked in the audit and can be addressed in their respective planned
phases without blocking Wave 8 content work.
