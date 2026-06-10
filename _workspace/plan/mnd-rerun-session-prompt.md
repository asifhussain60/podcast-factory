# New-session prompt — master-and-disciple density re-run (paste everything below the line)

---

We are testing the new chapter-density pipeline end-to-end on **the-master-and-the-disciple**. All build work is done and pushed on branch `Islamic/the-master-and-the-disciple` (6 commits). Your job this session is to DRIVE THE RE-RUN, not to build anything new.

Orient first (read-only, in this order):
1. `git checkout Islamic/the-master-and-the-disciple` and read the newest entry ("2026-06-10 (evening)") in `_workspace/plan/copilot-handoff.md` — it is the authoritative summary of what landed and what is next.
2. The full approved plan is at `~/.claude/plans/review-the-changes-made-synthetic-swan.md`; the standard is `docs/standards/chapter-density.md`.
3. Check the slide-intelligence smoke result on the OLD deck: `content/Islamic/the-master-and-the-disciple/slide-decks/_analysis/book-analysis.json` (per-page `svg_verified` flags) and `slide-decks/_svg/book/`. Report how many of the 13 high-value pages produced verified SVGs. If the run never finished, you may re-run it: `python3 scripts/podcast/_slide_replicate.py content/Islamic/the-master-and-the-disciple book` (vision analysis is sig-cached; only SVG authoring re-fires).

Then execute:
4. Archive the OLD deck's artifacts (they belong to the superseded 5-episode edition): move `slide-decks/book-deck.pdf`, `book-deck.pptx`, `_manifests/book-manifest.json`, and the smoke-test outputs `_analysis/`, `_svg/`, `_pages/book/` into `slide-decks/_archive/`. Commit.
5. **LAUNCH THE RE-RUN (I authorize this Tier-2 spend now):**
   `python3 scripts/podcast/orchestrate_book.py --resume the-master-and-the-disciple --retry-phase 0d`
   Run it in the background. Immediately arm the mandatory 270-second heartbeat (ScheduleWakeup) with the standard heartbeat card (book title, metrics table, orchestrator + watchdog PIDs, chapter list with status icons, EST timestamps). Active liveness: verify PIDs alive and outputs growing each tick; kill and surface on hang.
6. Phase 0d redesigns 5 source chapters into ~20 episodes under the new rules (max 3 concepts per episode, `(chapter N, verse M)` Quran references, no transliteration formula pairs, sermons rendered whole with `sermon:` contract blocks). The post-write concept gate and the post-0d chapter-set integrity gate (coverage / overlap / duplication / sermon checks) HALT on violations — this book runs `density_standard: 2`. If a systemic P0 pattern repeats across source chapters, halt and fix at the root before letting the loop burn spend.
7. At the series-confirmation halt: present the new episode design (titles, concept counts from `python3 scripts/podcast/chapter_density_audit.py --slug the-master-and-the-disciple`, sermon flags) for my review. Wait for my approval before resuming.
8. After my approval, resume through 0e + the per-chapter loop (framing + challenger convergence, ~20 episodes) to the **finalize halt**, which must print the locked 4-column NotebookLM upload table (Chapters | Episodes | Deep dive or debate | Length, all linked, Length=Long) PLUS the book-level slide card (paste `slide-decks/book-framing.md`, drop the exported deck at `slide-decks/book-deck.pdf`). That is my cue to generate ~20 audio episodes and ONE slide deck in NotebookLM.
9. When I later drop `book-deck.pdf` and resume, the book phases run: compose → illustrate → slide-import (vision analysis → high-value slides replicated as verified SVG, rest as raster) → render to the reading-edition PDF. Publish stays a separate explicit gate — never auto-publish, never merge to develop before publish completes, and run the post-merge repo-surgeon sweep once at end of chain.

Standing rules that apply: no pull requests (commit/push to the book branch directly); $50 per-book cost cap; status emojis in heartbeat cards; respond in the locked response format.
