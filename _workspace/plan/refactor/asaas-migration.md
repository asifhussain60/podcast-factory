# Phase 5 (DEFERRED) — asaas migration + `content/` → `library/` rename

**Status:** NOT STARTED — deferred by design. Tracked as `plan.yaml` step **WM5**.

**Why bundled + deferred:** both are a top-level move/rename on `develop`. A rename
of the content root collides with the active `Islamic/asaas-al-taveel` branch at
merge time, so BOTH land together, ONCE, at asaas's **next clean boundary** (the
current volume reaches publish / before the next volume starts) — never mid-flight.
This caps the migration debt before it compounds across all 6 volumes.

**Trigger:** Asif says go, when asaas is at a phase boundary with a committed tree.

**Foundation already built migration-aware:** the resolver (`_paths.py` +
`_work_manifest.py`, Wave M1) recognises the nested `work.yml` layout, so the
conversion is a scripted one-time step, not a cliff.

---

## Part A — folder rename `content/` → `library/` (Q11)

1. Change the single root constant `_paths.py` `CONTENT_ROOT` (`REPO_ROOT / "content"`
   → `"library"`) and the 4 `content-paths.ts` `join(…, 'content', …)` sites.
   Keep a legacy fallback so a path under the old `content/` root still resolves
   during transition. NOTE: `intake_staging.staging_root()` + `intake_launch` already
   resolve through `_paths.SYSTEM_ROOT`, so they follow the rename with ZERO edits —
   verify, don't re-point.
2. `git mv content library` (one move; preserves history).
3. Sweep the ~393 prose references (`docs/`, agent specs, skills, `CLAUDE.md`,
   `framework.md`, plan files) `content/` → `library/`; regenerate dashboard snapshots.
4. Full `pytest scripts/podcast/tests/` + `npm run lint:views` + `repo-surgeon --scope podcast` green.

## Part B — asaas → one-PDF-per-volume manifest model

5. Bring `Islamic/asaas-al-taveel` to a clean stopping point (current volume at a
   phase boundary, working tree committed); rebase onto the renamed `develop`.
6. Provision one PDF per volume into `library/Islamic/asaas/vol-NN/_source/`
   (keep the master Arabic PDF as archival original — it is the split source, not a
   runtime input).
7. Generate `work.yml` for asaas (title, `islamic_scholarly`, ordered volumes + role-
   tagged `sources:`) via `_work_manifest.write_manifest`.
8. Run the one-time layout conversion (nested page-sliced → manifest model): stamp each
   volume's `work_slug`/`branch`, ensure volume dirs are `vol-NN`, move the staged
   wisdom corpus + 40 pronunciation terms into the work shared library.
9. Re-point the branch to `Islamic/asaas`; verify each volume's
   `orchestrator-state.json` resolves through `find_content` (composite slug) +
   `_work_manifest`; run the Wave-M regression suite (`test_work_manifest.py`) against asaas.
10. Merge to `develop` via the standard per-volume publish/merge flow.

## Acceptance

- `git status --porcelain content/` (pre-rename) / `library/` (post) shows no change
  to the existing FLAT books (M&D, ayyuhal-walad, journey-to-the-west-vol-1) — the
  must-not-regress pin.
- `find_content("asaas")` → work rollup; `find_content("asaas-vol-NN")` → volume dir.
- Full suite + `lint:views` + post-merge `repo-surgeon --scope podcast` green.
