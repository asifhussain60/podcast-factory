<!--
  SINGLE LIVING SOURCE for "where the work stands." The SessionStart hook
  (.claude/hooks/site-work-status.sh) injects this into every new conversation so
  the next session inherits context with zero re-reminding (WC7e). KEEP IT SHORT and
  CURRENT — update the fields at the end of any session. Stale status is worse than none.
-->
# Current work — status

**Last updated:** 2026-06-03 (session 5)

**BRANCH: `develop` — active. Wave M merged and pushed (c66c7e3).**

**Session work completed:**
- All stale branches deleted (local + remote): feature/wave-l-category-augmentation,
  book/ayyuhal-walad, ui/site-enhancements, refactor/wave-1, origin/refactor/wave-1,
  origin/site/claude-code, origin/site/healthequity, origin/book/ayyuhal-walad
- plan.yaml updated: waves G–M added with completed status; Wave CP status corrected
- Healthequity content cherry-picked from orphaned branch (transcripts, Azure runbook, TTS PoC)
- Wave M M-1: floating AI toolbar + inspector tabs (Details/Comment/AI/References) + scroll fix
- Wave M M-2: lib/db/knowledge.ts + /api/corpus/atoms GET + corpus.astro live DB (988 atoms)
- Wave M M-3: updateAtom/createAtom + /api/corpus/atom PATCH+POST + CorpusExplorer inline edit+create
- Post-merge P0 fixed: localAtoms useState hoisted above activeAtoms reference

**PIPELINE HEALTH:**
- 392 tests passing (1 skip)
- `astro check`: 0 errors
- `lint:views`: errors=0 warns=0

**OPEN DEBT:**
- P1 (low urgency): move MockAtom/AtomType/Tradition/CorpusId types from corpus-mock-sample into knowledge.ts — decouples live DB module from mock data file.

**NEXT WORK (Wave N — not yet designed):**
- Section-level depth markers (pipeline guesses, human corrects) — requires stable section IDs first
- Lookup_levels SQLite import + canonical term verification + full 6→7-rung ladder
- Wave CP formal implementation (content_profile field in series-config.yaml + pipeline gates)

**PARKED:**
- Ayyuhal Walad pipeline: 5 chapters fully staged; waiting on hadith DB from Asif
- Video visual layer (WC8.9, authorized, ~$2 cost)
