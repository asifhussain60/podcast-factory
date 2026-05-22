# Studio alignment brief — 2026-05-22

**Purpose**: orient the Mac Studio's Claude session to the substantial doctrinal + framework changes the Mac Air made on `book/kitab-al-riyad` (this branch). Read this once. Then act per the "Studio next-actions" section at the bottom.

**Status**: Air's orchestrator is currently re-emitting all 13 KaR chapters under v4-revised doctrine (Phase 6 of a 10-phase plan). ETA 2-4 hours from launch. Studio MUST NOT touch this branch or any KaR artifacts until Phase 10 merge to `develop` completes.

---

## What changed in this session (10-phase plan)

| Phase | What | Commit |
|---|---|---|
| 1 | Working-tree state commit (post-orchestrator) | [3f0e380](https://github.com/asifhussain60/Journal/commit/3f0e380) |
| 2 | Pipeline-debt holistic refactor + validator coverage matrix | [c3d3f29](https://github.com/asifhussain60/Journal/commit/c3d3f29) |
| 3 | F27 Tier 2.5 validators in `build_episode_txt.py` (7 new asserts) | [3631bc0](https://github.com/asifhussain60/Journal/commit/3631bc0) |
| 4 | v4-revised doctrine propagation to `_authoring.py` Phase 0e + 0g prompts | [23009eb](https://github.com/asifhussain60/Journal/commit/23009eb) |
| 5 | All 13 KaR chapter sources rewritten (2,634 substitutions) | [f54c657](https://github.com/asifhussain60/Journal/commit/f54c657) |
| 6 prep | Clear KaR artifacts + state reset for re-emit | [9ac6fab](https://github.com/asifhussain60/Journal/commit/9ac6fab) |
| 6 run | Orchestrator running (PID 31322 on Air) | in flight |
| 7 | Re-emit episode bundles (validators run automatically) | pending |
| 8 | Manual eval each chapter + framing + bundle | pending |
| 9 | Final cleanup + commit residual fixes | pending |
| 10 | Merge `book/kitab-al-riyad` → `develop`; push to remote | pending |

---

## The v4-revised doctrine — empirically locked

After 3 audio audits (v3, v4, v4-revised of KaR Ch07) the following doctrines are LOCKED:

1. **F20 — zero Arabic person/book/concept names in spoken audio.** No "al-Kirmani," "al-Sijistani," "al-Islah," etc. TTS mangles every Arabic transliteration unreliably (e.g., "al-Kirmani" → 12 variants in 42 min in v1 audio; "Qaf" → "cough" in v4 audio).
2. **F21 — book-wrap convention.** Every book reference: "the book *The Correction*" (al-Islah), "the book *The Defense*" (al-Nusra), "the book *The Harvest*" (al-Mahsul), etc.
3. **F16 — episode-number announcement.** Open with "This is Episode N of our walkthrough of this book, covering the book's Chapter M."
4. **Stable role-labels** (replaces rotation). One label per figure, used every time. Pattern:
   - Established English title → use it ("the Commander of the Faithful," "the Prophet," "the fourth Imam," "the Fatimid caliph").
   - Functional role-title → use it ("the author," "the compiler," "a companion of the Prophet").
   - No established form + phonetic-collision risk → proper English name with one-shot role-epithet at first mention ("Jonathan, the earlier scholar who wrote the book *The Correction*" → thereafter "Jonathan").
5. **R-RECURRING-THESIS** — central thesis verbatim 3× (open, pivot, close).
6. **R-DRAMATIC-ARC** — 6-beat structure (crisis → failed answer A → failed answer B → pivot → non-bodily correction → stakes+question).
7. **R-CHALLENGER-FRICTION** — 4 literal pushback patterns; Color host pushes back, doesn't chorus.
8. **R-ANALOGY-CAP-STRICT** — 3 governing analogies + source-image carve-out (chapter-prose images permitted in passing).
9. **R-HONORIFIC-ONCE bounded both sides** — exactly once each, MANDATORY at first mention.
10. **F29 — R-SURAH-ENGLISH-ONLY** — surah names by English meaning ("the chapter on the sun" not "al-Shams"; "the chapter on the night journey" not "al-Isra"). Discovered when "Qaf" pronounced "cough" in v4-revised audio.
11. **F24 — R-ALQAAB-FUNCTIONAL-PARAPHRASE** — only established English alqaab (Commander of the Faithful, Lion of God) spoken. Novel alqaab → functional paraphrase ("one of his martial honorifics"). NEVER literal translation ("the Striker" anti-pattern).

---

## Where the doctrine lives in code

| Layer | File | What |
|---|---|---|
| Prompts | `scripts/podcast/_authoring.py` — `author_phase_0e()` lines ~1055-1099 | Chapter authoring rules (F20, F29, F24, R-NO-MANUSCRIPT-META, R-PHONETICS-OUT, R-HONORIFIC-ONCE) |
| Prompts | `scripts/podcast/_authoring.py` — `author_framing()` lines ~1227-1320 | Phase 0g framing-gen rules (R-STABLE-ROLE-LABELS, R-DRAMATIC-ARC, R-CHALLENGER-FRICTION-LITERAL, R-ANALOGY-CAP-STRICT, R-RECURRING-THESIS, R-HONORIFIC-ONCE-BOTH-BOUNDS, R-SURAH-ENGLISH-ONLY, R-ALQAAB-FUNCTIONAL-PARAPHRASE, length target) |
| Validators | `scripts/podcast/build_episode_txt.py` — lines ~570-820 | 7 F27 assert_* validators (all P1 flags — warn don't hard-fail) |
| Per-book | `_system/name-aliases.yml` | KaR mapping; future: F26 schema v2 |
| Handbook | `content/podcast/.skill/handbook/notebooklm-customize-prompt-rules.md` | Canonical R-rule reference (P1 deferred update — see pipeline-debt) |

---

## Pipeline-debt — F1-F29 status (refactored 2026-05-22)

See `_workspace/plan/pipeline-debt.md` top section ("Refactored synthesis view") for the canonical view. Key matrix:

- **Doctrine LOCKED (🟢)**: F20, F21, F16, R-RECURRING-THESIS, R-DRAMATIC-ARC, R-CHALLENGER-FRICTION, stable role-labels, mirror-as-source-aligned.
- **Doctrine pending validation (🟡)**: F24 (alqaab — KaR Ch07 has no novel alqaab to test); F22 length target (structural NotebookLM ~40-45 min ceiling).
- **Open framework work**: F23 (book-coherence check Phase 0d.5), F25 (apparatus-table schema), F26 (name-aliases v2 schema + Phase 0d auto-emit), F11 (iter-1-ship vs iter-2-timeout), F12 (episode-id from contract.episode_number), F13 (Phase 0e inline-phonetics leaks).
- **Decided**: F28 (Asif: re-emit KaR under v4-revised doctrine — in flight).

**Validator coverage matrix**: 7 of 14 R-rules have validator-side enforcement after Phase 3 (F27). 7 are still prompt-only (= M1 risk surface). F27 closes 6 of those 7. Remaining: R-PHONETICS-OUT (F9 audit pending).

---

## Critical: what Studio should NOT do

While Air's orchestrator is running on `book/kitab-al-riyad`:

1. **Do NOT** run any orchestrator command against KaR.
2. **Do NOT** touch any file under `content/podcast/library/books/kitab-al-riyad/`.
3. **Do NOT** push to `book/kitab-al-riyad` from Studio.
4. **Do NOT** merge anything to `develop` while KaR re-emit is in flight (will conflict with Phase 10).
5. **Do NOT** force-push to any branch.

You can:
- Read this repo for orientation (read-only).
- Continue work on a DIFFERENT book if Studio is currently assigned one (check `_workspace/plan/operators/mac-studio-primary.md`).
- Prepare to pull `develop` after Phase 10 completes (Air will surface when ready).

---

## What Studio should DO after Phase 10 completes (Air will notify)

1. `git pull origin develop` to inherit the v4-revised framework.
2. Read `_workspace/plan/pipeline-debt.md` top section to understand the new R-rules + validator matrix.
3. For any new book Studio processes: the new doctrine applies automatically (Phase 0g framing-gen uses the updated `_authoring.py`; build_episode_txt.py runs F27 validators).
4. For each new book, expect to:
   - Build a `_system/name-aliases.yml` (v2 schema once F26 lands; until then use the KaR-style schema as a template).
   - Verify the first chapter's framing manually against `R-STABLE-ROLE-LABELS` discipline (pick proper names where established titles don't exist).
   - Audit the first chapter's audio (1-round, not 4) — the doctrine is now framework-default; if it produces clean output, propagate.

---

## Recovery + revert paths

If the v4-revised doctrine breaks anything unexpectedly on Studio's next book:

- Pre-v4-revised state: `git log --oneline | grep -B2 "Phase 3"` finds [3631bc0] — that's the boundary.
- Revert `_authoring.py` to v3-doctrine: `git checkout 02c714b -- scripts/podcast/_authoring.py` (last v3 state before Phase 4).
- Revert validators: `git checkout 3631bc0~1 -- scripts/podcast/build_episode_txt.py` (state before F27).

But: don't revert without surfacing. The doctrine is empirically validated; failure is more likely book-specific (e.g., alqaab missing from KaR but present in a Hadith-commentary book → F24 hasn't been empirically tested).

---

## Files to read for full context

When you have time (in priority order):

1. `_workspace/plan/pipeline-debt.md` — top section "Refactored synthesis view" (the doctrine + validator + open-debt matrix).
2. `_workspace/plan/v4-doctrine-propagation.md` — the 6 _authoring.py prompt updates + handbook updates planned.
3. `_workspace/plan/f27-validator-drafts.md` — the 8 validator drafts (Phase 3 landed 7 of 8; #8 apparatus-table deferred).
4. `content/podcast/library/books/kitab-al-riyad/_system/ch07-lab/v4-revised/` — the canonical doctrine reference (chapter.txt, framing.md, audit-checklist.md).
5. `scripts/podcast/build_episode_txt.py` lines ~570-820 — the F27 validator implementations.
6. `scripts/podcast/_authoring.py` `author_phase_0e()` + `author_framing()` — the prompt-side enforcement.

---

## Standing instruction

This brief is a snapshot of doctrine + framework + in-flight state as of 2026-05-22. If Studio sees content/code that contradicts this brief, the in-repo files win (they're updated by Air). Resync via `claude --agent operator-sync` if drift is suspected.
