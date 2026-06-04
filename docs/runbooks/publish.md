# Publish runbook (G1–G7 gates)

`publish_to_library.py` is the Tier 2 gate that moves a book from `content/drafts/<slug>/` to `content/published/books/<slug>/`. ALWAYS requires Asif's explicit authorization per CLAUDE.md authorization tiers — never auto-triggered.

## Pre-flight gates

```bash
# Dry-run the gates without writing anything:
python3 scripts/podcast/validate_ship_ready.py my-book-slug
```

Returns `SHIP-READY` if all 7 pass, lists failures otherwise.

| Gate | Check | Failure means |
|---|---|---|
| **G1** | Chapter count == episode count (`chapters/ch*-*.txt` matches `episodes/EP*-*.txt`) | Per-chapter loop hasn't completed or chapters were added/removed since |
| **G2** | Every chapter slug has a paired episode (no orphan chapters, no episodes without chapters) | F8 sweep should have caught this; manual triage needed |
| **G3** | Episode numbering is sequential 1..N (no gaps, no duplicates) | F12 (`_resolve_episode_id` reading contract.episode_number) should ensure this; check contracts |
| **G4** | `build_episode_txt.py` clean on every episode (P0=0 across all Tier 2.5 validators) | Re-run build per episode; fix flagged violations |
| **G5** | `phases.publish` is shippable (`phase ∈ {finalize, publish, done}` AND `phase_status ∈ {halted, completed}`) | Book isn't past finalize-halt yet |
| **G6** | Target `content/published/books/<slug>/` doesn't exist OR is safely wipe-able (no uncommitted changes inside) | Existing published version — confirm overwrite intent |
| **G7** | Challenger verdict on every chapter ∈ {SHIP-READY, SHIP-WITH-CAUTION} (orchestrated mode) | Some chapters FAILED or COST-CAPPED per F33-second / F35-second; triage failed_slugs in state |

## Execute publish (Tier 2 — REQUIRES Asif authorization)

```bash
python3 scripts/podcast/publish_to_library.py my-book-slug
```

Refuses to publish books whose `pipeline_mode=non_orchestrated_mode_2` OR whose verdict is not in {SHIP-READY, SHIP-WITH-CAUTION} unless `--allow-mode-2` is passed. On success: copies drafts → published, updates state to `phase=publish, phase_status=completed`, then the orchestrator's `merge` phase merges `book/<slug>` → `develop` with --no-ff and pushes.

## Known issues

- **Publish dry-run mutates source files (`project_publish_dry_run_bug`).** `--dry-run` claims "no files written" but mutates `content/drafts/<slug>/episodes/*.txt`. Workaround: `git checkout HEAD -- content/drafts/<slug>/episodes/` after each dry-run. Fix not yet implemented.
- **Backward-compat decision (F28, 2026-05-25): GRANDFATHER pre-doctrine books.** kitab-al-riyad shipped May 2026 pre-v4 doctrine; episodes at `content/published/books/kitab-al-riyad/` are v1-quality reference. Books from the-master-and-the-disciple onward ship at the full v4 + v2.2 + F30 + scaffold-retirement bar. Re-emission of KaR is opt-in per chapter at operator discretion; no scheduled backfill.

## Post-publish

The orchestrator's merge phase fires automatically after publish succeeds. The book branch is now safe to delete per the "ONE branch per active book" rule (preserve as `archive/<slug>-shipped-<date>` tag first; tags push to origin as durable backup).

```bash
# Verify orgin has the archive tag before deleting the branch:
git tag -a archive/my-book-slug-shipped-$(date -u +%Y-%m-%d) <branch-tip-sha> \
    -m "Archive: book/my-book-slug at ship"
git push origin archive/my-book-slug-shipped-$(date -u +%Y-%m-%d)
# Then the branch is deletable:
git branch -D book/my-book-slug
git push origin --delete book/my-book-slug
```

Run `python3 scripts/podcast/cross_book_dashboard.py` to confirm the book moves from `in-flight` to `shipped` in the fleet table.
