# Runbook — Journal repo split into `podcast-factory` + `journal`

**Status:** DRAFTED 2026-05-22 — execution pending Asif's authorization AND Air's `book/kitab-al-riyad` Phase 10 merge to develop. Do not execute any step in this file until both gates clear.

**Authored on:** `book/asaas-al-taveel` (Studio Mac). Move to `develop` (commit + push) once Asif approves the runbook.

---

## 1. Goal

Split this single repo into two single-purpose repos:

| Repo | Source | Contents | GitHub URL |
|---|---|---|---|
| `podcast-factory` | Current `Journal` repo, renamed | All podcast pipeline content + infra + branches + worktrees | `github.com/asifhussain60/podcast-factory` (after rename) |
| `journal` | New empty repo, populated via `git filter-repo` | Memoir + site + server + journal skills + shared Arabic refs | `github.com/asifhussain60/journal` |

History is preserved on both sides — `git filter-repo` rewrites a clone to contain only journal-side commits, which become the new `journal` repo's history. The current repo loses nothing (just gets the journal files deleted in a single cleanup commit), so all podcast history is intact.

---

## 2. Decisions baked in

1. **Podcast repo name:** `podcast-factory` (per Asif 2026-05-22)
2. **Journal repo name:** `journal`
3. **Azure resources stay `journal-*` named** — cosmetic only, no rename. **`APP_NAME` edit in [azure-config.env](../../infra/azure/azure-config.env) is a code/config LABEL change only** — it does NOT trigger any Azure-side rename. The deployed resource group `rg-journal-ai`, all `journal-*` cognitive services, the storage account, and Key Vault all keep their existing names indefinitely. Post-split documentation (CLAUDE.md in podcast-factory + a note in [primary-mac-activation.md](primary-mac-activation.md) if it lives there) must clarify this cosmetic-only stance for future operators who'd otherwise be confused by `Journal`-prefixed Azure resources serving `podcast-factory` workloads.
4. **Cloudflare deploy + Anthropic API proxy RETIRED entirely** (per Asif 2026-05-22): the journal app no longer needs the Anthropic API, so the `journal` / `journal-dev` Cloudflare Workers, `wrangler.toml`, `site-worker.js`, `infra/cloudflare/`, `docs/cloudflare/`, AND the `server/` proxy are deleted from the runbook entirely. They are removed from podcast-factory in Phase 5 cleanup and NOT migrated to the new `journal` repo. The journal repo retains `site/` (static memoir display) but has no deploy target attached — operators may serve it locally via `npx serve site` or wire it to a different deploy mechanism in a future runbook. The original Phase 6 (Cloudflare re-pointing) has been deleted from this runbook.
5. **Both repos are completely separate and disconnected** (per Asif 2026-05-22 directive). Once split:
   - **No shared paths, no submodules, no symlinks, no canonical-vs-duplicate distinction.** Every file lives in exactly one repo OR in two repos as INDEPENDENT COPIES that evolve separately.
   - **General-utility skills, agents, Claude Code config, Cowork tooling, and reference materials are DUPLICATED into both repos** — see §17 inventory for the explicit "DUPLICATED to both" list.
   - **`content/_shared/arabic/` is duplicated as two independent copies** — neither is canonical; each repo evolves its own Arabic reference set going forward. (The directory name keeps `_shared/` for path stability with existing references, but the "shared" framing is historical only — there is no live sharing between the repos.)
   - **Trade-off Asif accepted**: skills/agents/refs duplicated this way will drift over time if changes aren't manually synced. This is the deliberately chosen trade-off; the repos prioritize disconnection over evolution-parity.
6. **Both repos retain their own history** via `git filter-repo`. The current `Journal` repo's full commit history stays as `podcast-factory`'s history; the new `journal` repo gets a filtered history containing only journal-side-touching commits. **The new `journal` repo receives only `develop` and `main` branches** — not the podcast/book branches (filter-repo's `--refs develop main` scopes the extraction to those refs only).
7. **Execution gates:** Air's KaR orchestrator Phase 10 merge to develop MUST complete before any step in this runbook runs.
8. **Studio-local directory layout: contained parent folder** (per Asif 2026-05-22). All Studio worktrees move under `~/Code/podcast-factory/` so the entire podcast-factory repo is one self-contained directory tree. See §2A below for the full folder structure of both repos and the worktree layout on disk.

---

## 2A. Folder structure after split — visual reference

This is what both repos look like on disk AFTER the split completes. The podcast-factory side shows the contained-parent worktree layout; the journal side is a single clone with no worktrees.

### 2A.1 podcast-factory — repo content tree

Single tree, replicated across each worktree directory. All 4 worktree dirs share one underlying `.git` database, so the file contents in any one worktree match the branch that worktree is checked out to.

```
podcast-factory/                       (root of the repo)
│
├── content/
│   ├── _shared/
│   │   └── arabic/                    (independent copy; journal has its own independent copy)
│   │       ├── 00-README.md
│   │       ├── 01-tts-pronunciation-key.md
│   │       ├── 02-quran-letter-phonetics.md
│   │       ├── 03-arabic-english-manifest.md
│   │       ├── 04-common-term-substitutions.md
│   │       ├── 05-name-alias-policy.md
│   │       └── 06-abjad-numerals.md
│   └── podcast/
│       ├── _README.md
│       ├── .skill/                    (handbook + _learning substrate)
│       │   ├── ROADMAP.md
│       │   ├── handbook/
│       │   └── _learning/
│       │       ├── archive/
│       │       ├── fixtures/
│       │       ├── health/
│       │       └── promoted/
│       └── library/
│           ├── articles/
│           ├── books/
│           │   ├── asaas-al-taveel/
│           │   ├── ayyuhal-walad/
│           │   ├── islr-mas-i/
│           │   ├── kitab-al-riyad/
│           │   └── the-master-and-the-disciple/
│           ├── documents/
│           ├── interviews/
│           ├── lectures/
│           │   └── kunooz-al-hikmah/
│           ├── letters/
│           └── _sandbox/
│
├── scripts/
│   ├── git-hooks/
│   ├── podcast/                       (orchestrate_book.py, _authoring.py, build_episode_txt.py, extract_chapter.py, …)
│   ├── install-claude-skills.sh
│   └── install-git-hooks.sh
│
├── skills-staging/
│   ├── clean-commit/
│   ├── cowork-brief/
│   ├── css-theme-sync/
│   ├── podcast/                       (SKILL.md + references)
│   ├── repo-surgeon/
│   ├── tell-me/
│   ├── ui-modernizer/
│   └── usage-auditor/
│
├── docs/
│   ├── architecture/                  (HTML pipeline diagrams)
│   ├── azure/
│   ├── multi-mac-runbook.md           (rewritten podcast-only)
│   ├── podcast/
│   └── voice-refine-test-samples.md
│
├── infra/
│   ├── azure/                         (azure-config.env, provision-azure.sh, store-keychain-keys.sh, …)
│   ├── claude-agents/
│   └── launchd/
│
├── _workspace/
│   ├── README.md
│   ├── _archive/
│   ├── audit/
│   ├── chats/
│   ├── orchestrator-logs/
│   ├── plan/
│   │   ├── book-queue.md
│   │   ├── operators/
│   │   ├── response-conventions.md
│   │   ├── response-template.md
│   │   └── …
│   └── runbooks/
│       ├── README.md
│       ├── primary-mac-activation.md
│       └── repo-split.md              ← this file (historical reference after execution)
│
├── .github/
│   ├── agents/                        (podcast-* + CORTEX + refine-prompt + reconcile + repo-surgeon + operating-contract)
│   ├── workflows/                     (release.yml, ci.yml, podcast-e2e.yml)
│   └── copilot-instructions.md
│
├── reference/
│   ├── cortex-challenger-framework.md
│   ├── skill-bootstrap.md
│   ├── skill-overlays/
│   └── skill-registry.md
│
├── shared/
│   └── tag-normalize.js
│
├── CLAUDE.md                          (podcast-only after Phase 5 rewrite)
├── framework.md                       (podcast-only after Phase 5 rewrite)
├── Makefile                           (podcast + Azure targets)
├── package.json                       (name: "podcast-factory")
├── .gitignore
└── README.md
```

### 2A.2 podcast-factory — worktree layout on disk (Studio)

Studio's `~/Code/` after Phase 7.4 reorganization:

```
~/Code/
│
├── podcast-factory/                   ← PARENT (contains everything for podcast work)
│   │
│   ├── main/                          ← main clone — owns the .git/ directory
│   │   │                                currently on branch: dump
│   │   ├── .git/                      ← the actual git database for the whole repo
│   │   │   └── worktrees/             ← admin records for each linked worktree
│   │   │       ├── book-asaas/
│   │   │       ├── book-islr/
│   │   │       └── feat-w1/
│   │   ├── content/  scripts/  skills-staging/  …  (full tree per §2A.1)
│   │   └── …
│   │
│   ├── book-asaas/                    ← linked worktree
│   │   │                                branch: book/asaas-al-taveel
│   │   ├── .git                       ← a FILE (not dir) → ../main/.git/worktrees/book-asaas
│   │   ├── content/  scripts/  …      (same tree, checked out to book/asaas-al-taveel)
│   │   └── …
│   │
│   ├── book-islr/                     ← linked worktree
│   │   │                                branch: book/islr-mas-i
│   │   ├── .git                       ← FILE → ../main/.git/worktrees/book-islr
│   │   └── …
│   │
│   └── feat-w1/                       ← linked worktree
│       │                                branch: feat/operator-review-studio
│       ├── .git                       ← FILE → ../main/.git/worktrees/feat-w1
│       └── …
│
└── journal/                           ← SEPARATE REPO (single clone, no worktrees)
    └── …                              (see §2A.3)
```

Key properties:
- Single `.git/` for the whole podcast-factory repo, owned by `main/`.
- Each linked worktree has a `.git` **file** (not directory) pointing back at `main/.git/worktrees/<name>/`.
- All worktrees share one branch namespace and ref database — switching branches in one worktree doesn't affect the others.
- The `journal` repo lives at `~/Code/journal/` as a sibling — completely independent git database.

Air's local layout mirrors this pattern with her own worktree set (typically `main/` + `book-kitab-al-riyad/` + whatever else she has). Phase 8.4 captures her exact pre-move manifest then mirrors the Studio reorganization.

### 2A.3 journal — repo content tree

The journal repo is **fully self-contained** post-split: it has its own copies of all general-utility skills, agents, reference materials, and Claude Code config — no shared paths with podcast-factory, no submodules, no symlinks.

```
journal/                                (root of the repo)
│
├── content/
│   ├── _shared/
│   │   └── arabic/                    (independent copy; podcast-factory has its own)
│   └── babu-memoir/
│       ├── _system/
│       │   ├── scratchpad/
│       │   ├── snapshots/
│       │   ├── scratchpad-markers.md
│       │   └── translations-glossary.md
│       └── chapters/                  (canonical memoir chapters .txt files)
│
├── site/                              (static memoir display; no deploy target — Cloudflare retired 2026-05-22)
│   ├── chapters/                      (mirrored from content/babu-memoir/chapters/ via scripts/site/sync_chapters.sh)
│   ├── css/
│   │   ├── base.css
│   │   ├── app.css
│   │   ├── themes/                    (runtime-swappable theme stylesheets)
│   │   └── …
│   ├── data/
│   ├── js/
│   ├── index.html                     (React SPA entry point — Anthropic API integration removed)
│   ├── package.json
│   └── web.config
│
├── scripts/
│   ├── install-claude-skills.sh       (DUPLICATED from podcast-factory; installs journal's skill set)
│   ├── memoir/                        (auto_delta.py, save_snapshot.py, detect_user_delta.py, refresh_all_snapshots.py)
│   └── site/
│       └── sync_chapters.sh           (mirrors content/babu-memoir/chapters/ → site/chapters/)
│
├── skills-staging/                    (journal-only + duplicated general-utility skills)
│   ├── clean-commit/                  (DUPLICATED)
│   ├── cowork-brief/                  (DUPLICATED)
│   ├── css-theme-sync/                (RECLASSIFIED — site theme work)
│   ├── journal/                       (journal-only)
│   │   └── SKILL.md
│   ├── repo-surgeon/                  (DUPLICATED)
│   ├── tell-me/                       (DUPLICATED)
│   ├── ui-modernizer/                 (RECLASSIFIED — site UI work)
│   └── usage-auditor/                 (DUPLICATED)
│
├── .github/
│   ├── agents/                        (journal-only + duplicated general-utility agents)
│   │   ├── CORTEX.agent.md            (DUPLICATED)
│   │   ├── journal-challenger.agent.md
│   │   ├── journal-orchestrator.agent.md
│   │   ├── operating-contract.md      (DUPLICATED)
│   │   ├── reconcile.agent.md         (DUPLICATED)
│   │   ├── refine-prompt.agent.md     (DUPLICATED)
│   │   └── repo-surgeon.agent.md      (DUPLICATED)
│   └── copilot-instructions.md        (DUPLICATED + tailored to journal)
│
├── infra/
│   └── claude-agents/                 (journal-only + duplicated)
│       ├── journal-challenger.md
│       └── refine-prompt.md           (DUPLICATED)
│
├── reference/                         (DUPLICATED — full subtree)
│   ├── cortex-challenger-framework.md
│   ├── skill-bootstrap.md
│   ├── skill-overlays/
│   └── skill-registry.md              (tailored: lists journal's skill set only)
│
├── CLAUDE.md                          (journal-only after Phase 4 rewrite)
├── framework.md                       (journal-only after Phase 4 rewrite)
├── Makefile                           (slimmed — site-dev, site-deploy, install-skills; no Azure or podcast targets)
├── package.json                       (name: "journal")
├── .gitignore                         (slimmed — no podcast/Azure entries)
└── README.md
```

**Annotation legend** (used in the tree above and in §17 inventory):
- `(DUPLICATED)` — file lives in BOTH repos as independent copies; future edits do NOT cross-propagate
- `(RECLASSIFIED)` — file was previously planned for podcast-factory but moves to journal per the 2026-05-22 refactor (site/UI-related). Cloudflare-related items WERE reclassified in an earlier draft of this runbook but are now RETIRED entirely (see §17.B-RETIRED).
- No annotation — journal-exclusive

The journal repo is the smaller side (~1.4 MB tracked content) but now includes ~5–7 duplicated skills, ~5 duplicated agents, the full `reference/` subtree, the skill installer, and tailored root config files (CLAUDE.md / Makefile / package.json / .gitignore / README.md — each rewritten for journal independently of podcast-factory's versions). Full self-containment with no cross-repo dependencies.

### 2A.4 journal — on-disk layout (Studio)

```
~/Code/journal/                        ← single clone, no worktrees
└── (the tree shown in §2A.3)
```

Memoir is single-doc work — one canonical chapter set, one site that serves it. The repo lives independently as a sibling of `~/Code/podcast-factory/`; it has normal `develop`/`main` branches but **no book-branch or multi-worktree operating model** — no `book/*` or `feat/*` branches, no linked worktrees.

### 2A.5 Quick comparison

| Aspect | podcast-factory | journal |
|---|---|---|
| Root on disk | `~/Code/podcast-factory/` | `~/Code/journal/` |
| Worktrees | 4 (main + 3 linked) on Studio; ≥2 on Air | 1 (no worktrees) |
| Active branches | 6 (`develop`, `main`, 4 book/feat) | 2 (`develop`, `main`) |
| Repo size | ~18 MB tracked content + duplicated skills/agents/refs | ~1.4 MB content + duplicated skills/agents/refs |
| Deploys to | Nothing (pipeline outputs) | None (Cloudflare deploy retired 2026-05-22; `site/` is local-only static files, served via `npx serve site` if needed) |
| Azure dependency | Yes (Translator, Doc Intel, Speech) | None (Anthropic API proxy via `server/` retired 2026-05-22) |
| General-utility skills present | clean-commit, cowork-brief, repo-surgeon, tell-me, usage-auditor, podcast | clean-commit, cowork-brief, repo-surgeon, tell-me, usage-auditor, journal, css-theme-sync, ui-modernizer |
| General-utility agents present | CORTEX, refine-prompt, reconcile, repo-surgeon, operating-contract, podcast-* | CORTEX, refine-prompt, reconcile, repo-surgeon, operating-contract, journal-* |
| Cross-repo sharing | **NONE** — fully disconnected; duplicated items evolve independently | **NONE** — fully disconnected |

### 2A.6 podcast-factory — post-Phase-9.5 final layout (library hoist applied)

The trees in §2A.1–§2A.2 above show the **immediate post-split** state. **Phase 9.5 — Library structure consolidation** (see §12A) then hoists the library out of `content/podcast/` into a top-level `library/` folder containing ONLY shipped, prod-ready artifacts. The end state of the podcast-factory tree is:

```
podcast-factory/                       (root of the repo, post-Phase-9.5)
│
├── library/                           ← NEW top-level — SHIPPED catalog only (read-only by convention)
│   ├── _meta/
│   │   ├── catalog.md                 (auto-generated cross-book index — markdown table)
│   │   └── catalog.json               (optional — same data, machine-readable for site/site-tools)
│   ├── archetypes/                    (moved from content/podcast/library/archetypes/)
│   │   └── islamic-scholastic-text.md
│   ├── books/
│   │   └── <slug>/
│   │       ├── index.md               (book metadata: title en+ar, author, archetype, series list, ship date+verdict, episode count, cover ref)
│   │       ├── cover.{jpg,png}        (optional — book art, if curated)
│   │       ├── transcript/            (polished NotebookLM SOURCE — one file per chapter, clean prose)
│   │       │   ├── 01-<chapter-slug>.md
│   │       │   ├── 02-<chapter-slug>.md
│   │       │   └── …
│   │       └── podcasts/              (episode bundles organized by series; some books span multiple series)
│   │           ├── _series-index.md   (top-level series list for this book)
│   │           ├── series-01-<series-slug>/
│   │           │   ├── _series.md     (series description + episode ordering)
│   │           │   ├── EP01-<chapter-slug>/
│   │           │   │   ├── source.txt          (the NotebookLM SOURCE upload — TTS-safe)
│   │           │   │   ├── framing.md          (the NotebookLM CUSTOMIZE PROMPT)
│   │           │   │   ├── challenger-report.md
│   │           │   │   └── audio.mp3            (optional — NotebookLM-generated audio, when archived)
│   │           │   └── …
│   │           └── series-02-<series-slug>/
│   ├── articles/                      (shipped articles, same per-piece pattern)
│   ├── documents/
│   ├── interviews/
│   ├── lectures/
│   │   └── kunooz-al-hikmah/
│   └── letters/
│
├── content/
│   ├── _shared/
│   │   └── arabic/                    (unchanged — duplicated independent copy)
│   └── podcast/
│       ├── _README.md
│       └── .skill/                    (handbook + _learning substrate — unchanged)
│
├── _workspace/                        ← EXTENDED — single root-level workspace folder per Asif 2026-05-22 directive
│   │                                    (accessible from all worktrees/branches; structure is shared, contents are branch-specific)
│   ├── README.md                      (unchanged)
│   ├── _archive/                      (unchanged)
│   ├── audit/                         (unchanged)
│   ├── chats/                         (unchanged)
│   ├── orchestrator-logs/             (unchanged)
│   ├── plan/                          (unchanged — operator coord)
│   ├── runbooks/                      (unchanged — this runbook lives here)
│   ├── books/                         ← NEW — per-book in-progress state (moved from content/podcast/library/books/)
│   │   ├── asaas-al-taveel/           (active work — _system/, chapter-contracts/, chapters/, episodes/, episode-drafts/, transcripts/)
│   │   │   ├── _system/
│   │   │   │   ├── orchestrator-state.json
│   │   │   │   ├── challenger-report.md
│   │   │   │   ├── series-plan.md
│   │   │   │   └── …
│   │   │   ├── chapter-contracts/
│   │   │   ├── chapters/              (TTS-safe .txt source per chapter)
│   │   │   ├── episodes/
│   │   │   ├── episode-drafts/
│   │   │   ├── transcripts/
│   │   │   └── source/                (raw PDF intake — gitignored per .gitignore patterns added in Phase 9.5.3)
│   │   ├── ayyuhal-walad/
│   │   ├── islr-mas-i/
│   │   ├── kitab-al-riyad/
│   │   └── the-master-and-the-disciple/
│   ├── articles/                      (in-progress articles — moved from content/podcast/library/articles/)
│   ├── documents/
│   ├── interviews/
│   ├── lectures/
│   ├── letters/
│   ├── _sandbox/
│   └── Books/                         ← LEGACY case-folded alias of books/ on macOS APFS (PDF intake convention; gitignored content)
│
└── (everything else from §2A.1 unchanged: scripts/, skills-staging/, docs/, infra/, .github/, reference/, root config files)
```

Key invariants of the post-Phase-9.5 layout:

- **`library/` is invariantly "shipped only"** — every file inside has passed a challenger verdict (SHIP-READY or operator-approved SHIP-WITH-CAUTION) and is the canonical prod-grade output.
- **`_workspace/books/<slug>/` is invariantly "scratch"** — orchestrator state, intermediate transcripts, draft episodes, draft framings, in-progress challenger reports all live here. The pipeline writes here freely. Per Asif's 2026-05-22 directive, the workspace is a single root-level folder accessible from every worktree/branch (structure is shared; per-branch contents are naturally branch-specific via git).
- **Promotion is one-way and explicit** — `scripts/podcast/ship_to_library.py` (authored in Phase 9.5) is the only path from workspace → library. Manual edits to `library/` are discouraged and CI-checked.
- **Worktrees on book branches** (e.g., `book-asaas/`, `book-islr/`) carry their own checkout of `_workspace/books/<book>/` — that's where book-specific in-progress work happens. The top-level `library/` is only meaningfully populated on `develop` and `main`.
- **`content/podcast/library/` no longer exists** — its contents split between top-level `library/` (shipped), root `_workspace/books/` + `_workspace/<category>/` (in-progress), and `library/archetypes/` (cross-book reference). The remaining `content/podcast/` holds only `_README.md` and `.skill/` (handbook + learning substrate).

This end-state is the user-visible folder model for podcast-factory; the immediate post-split layout in §2A.1–§2A.2 is a transient intermediate stage between Phases 5 and 9.5.

---

## 3. Pre-flight checks

Before executing Phase 1:

- [ ] Air's [book/kitab-al-riyad](https://github.com/asifhussain60/Journal/tree/book/kitab-al-riyad) orchestrator Phase 10 merged to develop. Verify: `git fetch origin && git log origin/develop --oneline | head -5` should show the KaR merge commit.
- [ ] **All 4 worktrees clean** — `git status --short` returns EMPTY output in each of `~/Code/Journal`, `~/Code/Journal-book-asaas`, `~/Code/Journal-book-islr`, `~/Code/Journal-feat-w1`. Plain `git status` prints a "clean working tree" message even when clean; `--short` is the empty-on-clean form.
- [ ] **develop synced on Studio (main worktree ONLY)** — do NOT run `git pull` from book/feat worktrees; that would merge develop INTO the active book branch. Correct sequence:
  ```bash
  git -C ~/Code/Journal fetch origin --prune          # fetch refs only, no merge
  git -C ~/Code/Journal checkout develop              # main worktree's branch → develop
  git -C ~/Code/Journal pull --ff-only origin develop # fast-forward only, fails if diverged
  ```
  Other worktrees verify cleanliness independently (the `git status --short` check above) — they stay on their own branches.
- [ ] **No unpushed local commits on any branch** — Phase 1.1 tags `origin/<branch>` (the authoritative GitHub state), so any local-only commits not yet pushed wouldn't appear in Layer 1 safety tags. They WILL be captured by Layer 3 (tar) as defense-in-depth, but cleaner to push first. Check:
  ```bash
  for br in develop main book/asaas-al-taveel book/kitab-al-riyad book/islr-mas-i \
            book/master-disciple-notebooklm-scaffolding \
            feat/operator-review-studio feat/podcast-w1-foundation; do
    if git -C ~/Code/Journal rev-parse --verify "$br" >/dev/null 2>&1; then
      unpushed=$(git -C ~/Code/Journal rev-list --count "origin/$br..$br" 2>/dev/null)
      [[ "$unpushed" -gt 0 ]] && echo "WARN: $br has $unpushed unpushed local commit(s) — push before backup OR rely on Layer 3 tar"
    fi
  done
  ```
- [ ] **Backup disk space** — at least 2 GB free in `~/Backups/` (or wherever the backup target lives). Check: `df -h ~/Backups/ 2>/dev/null || df -h ~/`. Layers 2 + 3 together typically run ~500MB–1GB for this repo's size, but headroom matters if the run is repeated.
- [ ] `git-filter-repo` installed: `which git-filter-repo` resolves. Install if missing: `brew install git-filter-repo`.
- [ ] Air notified — she'll need `git remote set-url origin <new-url>` after Phase 7.
- [ ] GitHub admin access to `asifhussain60/Journal` confirmed.

---

## 4. Phase 1 — Comprehensive backup + GitHub prep

This phase establishes a **4-layer backup BEFORE any destructive operation**, then preps GitHub. Each backup layer is an independent restore path — any single one is sufficient to return to the current state; together they provide defense in depth against partial-failure scenarios.

Backup layers:
1. **Per-branch git tags pushed to origin** — survives any local-disk failure (GitHub holds them)
2. **Complete `--mirror` clone in `~/Backups/`** — captures all refs including branches, tags, remotes, notes, and `refs/stash` if present. **Does NOT capture reflogs** (`.git/logs/*`) — those are a per-clone artifact and are covered by Layer 3 (tar) instead.
3. **Filesystem `tar.gz` of all worktrees** — captures untracked files, IDE state, unstaged changes, AND reflogs (`.git/logs/*`). The filesystem-level snapshot complements Layer 2's ref-level snapshot.
4. **Optional secondary GitHub mirror repo** — full second copy on GitHub for paranoid redundancy

### 1.1. Backup layer 1 — Per-branch safety tags + tag-branch map

Tag the authoritative GitHub state of every active branch and push tags immediately so they exist on origin before any state change. **Tag `origin/<branch>` (not the local branch)** — this guarantees we capture the state visible to all machines, and catches branches that exist on origin but not in Studio's local refs.

Write an explicit tag-to-branch map alongside the tags so restore procedures can read it directly instead of reconstructing branch names from tag strings (brittle when branch naming conventions evolve).

```bash
DATE=$(date +%Y-%m-%d)
echo "Backup date: $DATE"   # remember this — it's the rollback anchor key

mkdir -p ~/Backups/repo-split-$DATE
MAP_FILE=~/Backups/repo-split-$DATE/tag-branch-map.txt
: > "$MAP_FILE"   # truncate any prior content

cd ~/Code/Journal
git fetch origin --prune

# Tag every branch we care about — sourced from origin/<branch>, not local
for br in develop main \
          book/asaas-al-taveel book/kitab-al-riyad book/islr-mas-i \
          book/master-disciple-notebooklm-scaffolding \
          feat/operator-review-studio feat/podcast-w1-foundation \
          dump plan/v2-execute-readiness plan/v2-gap-close; do
  if git rev-parse --verify "origin/$br" >/dev/null 2>&1; then
    tag_name="pre-split-$DATE/$(echo $br | tr '/' '-')"
    # ONLY append to map file when tag creation succeeds — never write a
    # misleading entry if the tag already exists or fails to create.
    if git tag "$tag_name" "origin/$br" 2>/dev/null; then
      echo "Tagged: $tag_name → origin/$br"
      echo "$br $tag_name $(git rev-parse origin/$br)" >> "$MAP_FILE"
    else
      echo "WARN: tag $tag_name already exists or failed to create; not added to map"
    fi
  else
    echo "SKIP: origin/$br does not exist on remote"
  fi
done

# Push all new tags to origin
git push origin --tags

# Verify tags are on origin
echo "Tags on origin: $(git ls-remote --tags origin | grep "pre-split-$DATE" | wc -l)"   # expect ≥9
echo "Map file entries: $(wc -l < $MAP_FILE)"

# Sanity check — map file content
cat "$MAP_FILE"
```

The map file format is `<branch> <tag-name> <commit-sha>` per line — three space-separated fields. Path A restore (§14.2) reads this directly to know which tag belongs to which branch.

To restore any branch manually: `git reset --hard pre-split-$DATE/<branch-with-dashes>` OR look up the tag in `tag-branch-map.txt`.

### 1.2. Backup layer 2 — Full mirror clone (local)

A `--mirror` clone captures ALL refs (branches, tags, remotes, notes) — unlike a regular clone which only captures the default branch. This is the canonical local restore point.

```bash
mkdir -p ~/Backups/repo-split-$DATE
cd ~/Backups/repo-split-$DATE

git clone --mirror /Users/ahmac/Code/Journal Journal-mirror.git

# Verify completeness
cd Journal-mirror.git
echo "Branches: $(git branch -a | wc -l)"
echo "Tags: $(git tag | wc -l)"
echo "All refs: $(git for-each-ref | wc -l)"
echo "Mirror size: $(du -sh . | cut -f1)"

# Store ref count snapshot for restore verification
git for-each-ref --format='%(refname) %(objectname)' > ~/Backups/repo-split-$DATE/refs-snapshot.txt
wc -l ~/Backups/repo-split-$DATE/refs-snapshot.txt
```

To restore from this mirror: `git clone --no-local ~/Backups/repo-split-$DATE/Journal-mirror.git <new-path>` recreates the working tree with full fidelity.

### 1.3. Backup layer 3 — Filesystem tar (untracked + worktree state)

The mirror captures git-tracked content. A tar additionally captures:
- Untracked-but-important files (drafts, scratchpad text, local `.env` files)
- The exact filesystem state of all 4 worktrees including any unstaged changes
- IDE workspace files, `.vscode/` per-worktree settings

```bash
cd ~/Code
tar -czf ~/Backups/repo-split-$DATE/worktrees-snapshot.tar.gz \
  Journal \
  Journal-book-asaas \
  Journal-book-islr \
  Journal-feat-w1 \
  --exclude='*/node_modules' \
  --exclude='*/.venv' \
  --exclude='*/_workspace/Books' \
  --exclude='**/.DS_Store'

du -sh ~/Backups/repo-split-$DATE/worktrees-snapshot.tar.gz
ls -la ~/Backups/repo-split-$DATE/
```

To restore: `cd ~/Code && tar -xzf ~/Backups/repo-split-$DATE/worktrees-snapshot.tar.gz` recreates all 4 worktree directories at their original paths.

### 1.4. Backup layer 4 — Optional secondary GitHub mirror

For paranoid redundancy, push the mirror to a separate private GitHub backup repo. Optional but cheap insurance — protects against an unlikely scenario where the live `asifhussain60/Journal` is unrecoverable.

```bash
# Create a private backup repo
gh repo create asifhussain60/journal-backup-pre-split-$DATE \
  --private \
  --description "Pre-split backup of Journal repo, $DATE. Delete after stable for 7 days."

# Push the mirror to it
cd ~/Backups/repo-split-$DATE/Journal-mirror.git
git push --mirror https://github.com/asifhussain60/journal-backup-pre-split-$DATE.git

# Verify
gh repo view asifhussain60/journal-backup-pre-split-$DATE --json defaultBranchRef
```

To restore from the GitHub backup: `git clone https://github.com/asifhussain60/journal-backup-pre-split-$DATE.git`.

### 1.5. Backup verification — HALT GATE

Before proceeding to Phase 2, run the verification script. If ANY layer is missing, HALT and investigate.

```bash
DATE=<the-date-set-in-1.1>
echo "=== Backup verification for repo-split-$DATE ==="

echo "Layer 1 — Local tags:"
git -C ~/Code/Journal tag | grep "pre-split-$DATE" | wc -l

echo "Layer 1b — Tags pushed to origin:"
git -C ~/Code/Journal ls-remote --tags origin | grep "pre-split-$DATE" | wc -l

echo "Layer 1c — Tag-branch map:"
if test -s ~/Backups/repo-split-$DATE/tag-branch-map.txt; then
  wc -l ~/Backups/repo-split-$DATE/tag-branch-map.txt
else
  echo "MISSING — Path A restore (§14.2) cannot run without this file"
fi

echo "Layer 2 — Mirror clone:"
test -d ~/Backups/repo-split-$DATE/Journal-mirror.git && \
  du -sh ~/Backups/repo-split-$DATE/Journal-mirror.git || echo "MISSING"

echo "Layer 3 — Tar snapshot:"
test -f ~/Backups/repo-split-$DATE/worktrees-snapshot.tar.gz && \
  du -sh ~/Backups/repo-split-$DATE/worktrees-snapshot.tar.gz || echo "MISSING"

echo "Layer 4 (optional) — GitHub mirror backup:"
gh repo view asifhussain60/journal-backup-pre-split-$DATE 2>/dev/null >/dev/null && \
  echo "OK" || echo "SKIPPED (optional)"
```

**STOP CONDITION**: if Layer 1, **Layer 1c (tag-branch map)**, Layer 2, or Layer 3 is missing, do NOT proceed to Phase 2. Layer 1c is critical because Path A restore (§14.2) reads it directly — without it, restore falls back to the more destructive NUCLEAR path. Layer 1b (tags pushed to origin) failing is recoverable by re-running the push; Layer 4 is optional.

### 1.6. GitHub prep — Create new `journal` repo

Once backups are verified intact:

```bash
gh repo create asifhussain60/journal \
  --private \
  --description "Asif's journal & memoir engine — split from podcast-factory $DATE"
```

Match the current `Journal` repo's privacy setting (the current Journal is PUBLIC per `gh repo view`; set `--public` instead of `--private` if Asif wants the journal repo public too). **Do NOT** initialize with README, .gitignore, or license — we're pushing filtered history into a clean target.

Verify:
```bash
gh repo view asifhussain60/journal --json url,visibility,defaultBranchRef
```

### 1.7. Deferred — DO NOT rename `Journal` → `podcast-factory` yet

The rename happens at Phase 7 (after the split is verified working). Keeping the original URL during surgery means the backup tags, the mirror remote, and Air's clone all continue to resolve normally throughout Phases 2–6.

---

## 5. Phase 2 — Extract journal-side history into a sibling clone

Work happens in a SEPARATE filter-repo workspace to keep all 4 live worktrees untouched.

2.1. Fresh clone to a sibling directory:

```bash
cd ~/Code
git clone --no-local /Users/ahmac/Code/Journal Journal-filter
cd Journal-filter
git checkout develop
```

The `--no-local` flag forces a real clone (not hardlink) so filter-repo can rewrite history safely.

2.2. Run filter-repo, keeping all paths that become part of journal repo's content (journal-only + duplicated general-utility items + reclassified site/Cloudflare items). Process develop + main only (book/feat branches have no journal-side history worth preserving):

```bash
git filter-repo \
  --refs develop main \
  \
  `# Journal-exclusive content & code` \
  --path content/babu-memoir \
  --path scripts/memoir \
  --path scripts/site \
  --path skills-staging/journal \
  --path site \
  --path .github/agents/journal-orchestrator.agent.md \
  --path .github/agents/journal-challenger.agent.md \
  --path infra/claude-agents/journal-challenger.md \
  \
  `# Reclassified to journal (site / UI-related)` \
  --path skills-staging/css-theme-sync \
  --path skills-staging/ui-modernizer \
  \
  `# NOTE: Cloudflare scaffold (wrangler.toml, site-worker.js, infra/cloudflare/, docs/cloudflare/)` \
  `# AND the Anthropic API proxy (server/) are RETIRED entirely 2026-05-22 — NOT migrated to journal.` \
  `# They are deleted from podcast-factory in Phase 5 cleanup, and never appear in the new journal repo.` \
  \
  `# DUPLICATED to both repos — kept here so journal has its own independent copies` \
  --path content/_shared/arabic \
  --path skills-staging/clean-commit \
  --path skills-staging/cowork-brief \
  --path skills-staging/repo-surgeon \
  --path skills-staging/tell-me \
  --path skills-staging/usage-auditor \
  --path .github/agents/CORTEX.agent.md \
  --path .github/agents/refine-prompt.agent.md \
  --path .github/agents/reconcile.agent.md \
  --path .github/agents/repo-surgeon.agent.md \
  --path .github/agents/operating-contract.md \
  --path .github/copilot-instructions.md \
  --path infra/claude-agents/refine-prompt.md \
  --path reference \
  --path scripts/install-claude-skills.sh \
  \
  `# Shared root files (kept because they have journal-touching history; rewritten per repo in Phase 4)` \
  --path CLAUDE.md \
  --path framework.md \
  --path Makefile \
  --path package.json \
  --path .gitignore \
  --path .vscode \
  --path README.md
```

Notes:
- All `(DUPLICATED)` paths are included here so journal gets its own historical copies; podcast-factory's copies stay in place (Phase 5 cleanup does NOT remove them).
- All `(RECLASSIFIED)` paths (`css-theme-sync`, `ui-modernizer`) move to journal entirely and are removed from podcast-factory in Phase 5.
- **RETIRED paths (NOT migrated to journal, deleted from podcast-factory in Phase 5)**: `server/`, `wrangler.toml`, `site-worker.js`, `infra/cloudflare/`, `docs/cloudflare/`, `docs/anthropic-api-setup.md`, `docs/proxy-setup.md`. The journal app no longer needs the Anthropic API, so the Cloudflare deploy scaffold and the API proxy are both retired as of 2026-05-22.
- Shared root files (`CLAUDE.md`, `framework.md`, `Makefile`, `package.json`, `.gitignore`, `README.md`) are kept because they have journal-touching history. Each will be REWRITTEN per repo in Phase 4 (journal) and Phase 5 (podcast-factory) — same filename, different content, no future cross-propagation.
- Excluded (stay only in podcast-factory): `content/podcast/`, `scripts/podcast/`, `scripts/git-hooks/`, `scripts/install-git-hooks.sh`, `skills-staging/podcast/`, `infra/azure/`, `infra/launchd/`, `_workspace/`, `.github/agents/podcast-*`, `.github/agents/CORTEX-archived/` (if any), `.github/workflows/`, `docs/podcast/`, `docs/architecture/`, `docs/azure/`, `docs/multi-mac-runbook.md`, `docs/voice-refine-test-samples.md`, `shared/`.
- `shared/tag-normalize.js` is excluded by default (assumed podcast-only); add `--path shared` to the filter-repo args ONLY if Asif confirms it's used by the static `site/` (server/ is retired 2026-05-22, so it's no longer a consumer).

2.3. Verify only journal-side files remain:

```bash
ls
git log --oneline | head -20
find . -type f -not -path './.git/*' | head -40
```

Expected after filter-repo:
- **Journal-exclusive**: `content/babu-memoir/`, `site/`, `scripts/memoir/`, `scripts/site/`, `skills-staging/journal/`, `.github/agents/journal-*.agent.md`, `infra/claude-agents/journal-challenger.md`
- **Reclassified**: `skills-staging/css-theme-sync/`, `skills-staging/ui-modernizer/`
- **Duplicated** (also stay in podcast-factory): `content/_shared/arabic/`, `skills-staging/{clean-commit,cowork-brief,repo-surgeon,tell-me,usage-auditor}/`, `.github/agents/{CORTEX,refine-prompt,reconcile,repo-surgeon,operating-contract}.agent.md`, `.github/copilot-instructions.md`, `infra/claude-agents/refine-prompt.md`, `reference/`, `scripts/install-claude-skills.sh`
- **Root config files** (rewritten per repo in Phase 4): `CLAUDE.md`, `framework.md`, `Makefile`, `package.json`, `.gitignore`, `README.md`

Absent (retired entirely OR podcast-only): `content/podcast/`, `scripts/podcast/`, `scripts/git-hooks/`, `scripts/install-git-hooks.sh`, `infra/azure/`, `infra/launchd/`, `infra/cloudflare/`, `_workspace/`, `.github/workflows/`, `.github/agents/podcast-*`, `docs/podcast/`, `docs/architecture/`, `docs/azure/`, `docs/cloudflare/`, `docs/multi-mac-runbook.md`, `docs/anthropic-api-setup.md`, `docs/proxy-setup.md`, `server/`, `wrangler.toml`, `site-worker.js`, `shared/`.

---

## 6. Phase 3 — Push to new `journal` repo

3.1. Add the new remote and push **branches only — NO `--tags`**. The pre-split safety tags from Phase 1.1 belong to the podcast-factory side; the journal repo starts with a clean tag namespace.

```bash
git remote remove origin
git remote add origin https://github.com/asifhussain60/journal.git

# Belt-and-suspenders: delete any surviving pre-split-* tags from the filter-repo
# clone before push, so even an accidental --tags push later wouldn't leak them.
# (Filter-repo drops tags pointing at non-surviving commits; only pre-split-*/develop
# and pre-split-*/main typically survive. Removing them keeps the journal repo clean.)
# NOTE: macOS BSD xargs does not accept -r; using `while read` for portability.
git tag --list "pre-split-*" | while IFS= read -r tag; do
  [[ -n "$tag" ]] && git tag -d "$tag"
done

# Push branches only
git push -u origin develop
git push origin main
```

3.2. Create a fresh `journal`-side anchor tag — a meaningful "this is where the journal repo started its independent life" reference:

```bash
git tag "journal-split-$DATE" develop
git push origin "journal-split-$DATE"
```

This tag is the journal repo's own restore anchor for its initial state — distinct from the pre-split tags, which live on the podcast-factory side and reference the parent-repo lineage.

3.3. Verify on GitHub: `github.com/asifhussain60/journal` has develop, main, the `journal-split-$DATE` tag, and the expected file tree. NO `pre-split-*` tags should be present.

```bash
gh repo view asifhussain60/journal --json defaultBranchRef
gh api repos/asifhussain60/journal/tags --jq '.[].name' | head -10
```

---

## 7. Phase 4 — Initialize journal repo's identity

Still in `~/Code/Journal-filter`. Make the files reflect single-purpose journal-only:

4.1. Edit [CLAUDE.md](../../CLAUDE.md):
- Remove "Podcast pipeline" section under "What this repo contains"
- Remove "Cross-machine coordination" section (memoir is single-machine)
- Remove "Run this on session start" section (`start-session.sh` doesn't exist in journal repo)
- Replace with a journal-focused brief

4.2. Edit `framework.md`:
- Remove all podcast pipeline sections
- Keep memoir authoring + site sections

4.3. Edit `Makefile`:
- Remove `podcast-ingest`, `podcast-transcribe`, `podcast-audit`, `podcast-post-publish` targets
- Remove `provision`, `store-keys`, `verify`, `azure-probe`, `migrate-to-keyvault` (Azure-specific, podcast-only)
- Keep `bootstrap`, `install-skills` (if relevant to journal)
- Add `site-dev`, `site-deploy` targets if missing

4.4. Edit `package.json`:
- `"name": "journal"` (was `"babu-journal"`)
- `"description": "Babu memoir engine + journal site"` (drop "podcast source-bundle prep")
- `"keywords": ["journal", "memoir"]` (drop "podcast")

4.5. Edit `.gitignore`:
- Remove podcast-specific entries (`_workspace/Books/`, podcast chunks, orchestrator logs)
- Remove `server/node_modules` entry (server/ retired 2026-05-22; the entry is now an orphaned reference)
- Keep `.DS_Store`, `.env`, `site/node_modules` (if site/ has its own deps), etc.

4.6. Edit `README.md` (if exists) to be journal-only.

4.7. **Tailor duplicated config files for journal-only identity.** The duplicated items came over from podcast-factory verbatim; each needs editing so it reflects what's IN journal repo only:

- `.github/copilot-instructions.md`: rewrite to remove podcast references; describe journal's surface (memoir + site + server) and conventions
- `reference/skill-registry.md`: trim to list ONLY skills present in journal (clean-commit, cowork-brief, repo-surgeon, tell-me, usage-auditor, journal, css-theme-sync, ui-modernizer). Remove podcast entries.
- `reference/cortex-challenger-framework.md`: if it has podcast-specific examples, replace with journal examples (memoir challenger, site challenger). Otherwise leave as-is — it's a general framework.
- `reference/skill-bootstrap.md`: same — review for podcast specifics; rewrite as needed.
- `.github/agents/CORTEX.agent.md`, `refine-prompt.agent.md`, `reconcile.agent.md`, `repo-surgeon.agent.md`, `operating-contract.md`: general-utility agents; review each for podcast-specific examples or path references; edit to be repo-neutral or journal-specific as appropriate.

4.8. Commit:

```bash
git add -A
git commit -m "init: journal repo skeleton — single-purpose memoir + site

Extracted from asifhussain60/Journal via git-filter-repo.
History preserved for memoir + site files; podcast surface removed.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
git push
```

---

## 8. Phase 5 — Clean podcast surface from current repo

Switch back to the current repo (still named `Journal` on GitHub at this point).

5.1. From the main worktree:

```bash
cd /Users/ahmac/Code/Journal
git fetch origin --prune
git checkout develop
git pull --ff-only origin develop
git checkout -b chore/extract-journal-to-separate-repo
```

`--ff-only` enforces the no-accidental-merge discipline used throughout the runbook. If develop has diverged locally, the pull fails loudly and the operator investigates instead of silently creating a merge commit during surgery.

5.2. Remove journal-EXCLUSIVE files, reclassified-to-journal files (site/UI), AND retired-entirely files (Cloudflare scaffold + API proxy). **DO NOT remove any DUPLICATED items** — those stay in podcast-factory as the repo's own independent copies (see §17.A for the duplicated list).

```bash
# Journal-exclusive (only-in-journal post-split)
git rm -r content/babu-memoir
git rm -r scripts/memoir
git rm -r scripts/site
git rm -r skills-staging/journal
git rm -r site
git rm .github/agents/journal-orchestrator.agent.md
git rm .github/agents/journal-challenger.agent.md
git rm infra/claude-agents/journal-challenger.md

# Reclassified to journal (site/UI — no longer needed in podcast-factory)
git rm -r skills-staging/css-theme-sync
git rm -r skills-staging/ui-modernizer

# RETIRED entirely 2026-05-22 — NOT migrated to journal (orphaned references cleanup)
# Cloudflare deploy scaffold: deleted from podcast-factory AND excluded from Phase 2 filter-repo
git rm site-worker.js wrangler.toml
git rm -r docs/cloudflare
git rm -r infra/cloudflare
# Anthropic API proxy: journal app no longer needs the Anthropic API
git rm -r server
# API/proxy-related docs that only made sense in the retired-stack context
git rm docs/anthropic-api-setup.md 2>/dev/null || true
git rm docs/proxy-setup.md 2>/dev/null || true
```

**Explicitly KEEP** (stays in podcast-factory as its own independent copy — duplicated to journal in Phase 2):
- `content/_shared/arabic/`
- `skills-staging/clean-commit/`, `cowork-brief/`, `repo-surgeon/`, `tell-me/`, `usage-auditor/`
- `.github/agents/CORTEX.agent.md`, `refine-prompt.agent.md`, `reconcile.agent.md`, `repo-surgeon.agent.md`, `operating-contract.md`
- `.github/copilot-instructions.md` (tailored per-repo in 5.3)
- `infra/claude-agents/refine-prompt.md`
- `reference/` (full subtree — but 5.3 tailors `reference/skill-registry.md` to list only podcast-factory's skills)
- `scripts/install-claude-skills.sh`

5.3. Edit root files + tailor duplicated config for podcast-only identity:

- [CLAUDE.md](../../CLAUDE.md): remove memoir + site sections; tighten to podcast-only
- [framework.md](../../framework.md): remove memoir sections
- [Makefile](../../Makefile): remove any site/memoir targets (probably none — Makefile is already podcast-leaning)
- [package.json](../../package.json): `"name": "podcast-factory"`, drop memoir/journal keywords
- [infra/azure/azure-config.env](../../infra/azure/azure-config.env): change `APP_NAME="journal"` → `APP_NAME="podcast-factory"` (cosmetic only; resources stay named `journal-*`)
- [README.md](../../README.md): rewrite to podcast-only
- [.github/copilot-instructions.md](../../.github/copilot-instructions.md): tailor to podcast-only (remove any memoir/site references); the journal repo gets its own tailored version in Phase 4
- [reference/skill-registry.md](../../reference/skill-registry.md): trim to list ONLY skills present in podcast-factory (clean-commit, cowork-brief, repo-surgeon, tell-me, usage-auditor, podcast). Remove journal, css-theme-sync, ui-modernizer entries.

5.4. Search for any remaining "memoir" / "babu" / "journal site" references and clean:

```bash
grep -rn "memoir\|babu" --include="*.md" --include="*.py" --include="*.sh" --include="*.yml" 2>/dev/null
```

Update or remove as appropriate. Some references are historical commit messages — leave those.

5.5. Commit and push:

```bash
git add -A
git commit -m "chore: extract journal/memoir/site into separate repo

Journal repo now lives at github.com/asifhussain60/journal.
This repo (Journal, to be renamed podcast-factory) is now podcast-only.

Both repos are completely separate and disconnected per the 2026-05-22 refactor:
- General-utility skills, agents, reference materials, content/_shared/arabic/,
  and Claude Code config are duplicated as independent copies in each repo.
- Site/UI-related items (css-theme-sync, ui-modernizer) reclassified to journal.
- Cloudflare deploy scaffold (wrangler.toml, site-worker.js, infra/cloudflare/,
  docs/cloudflare/) AND the Anthropic API proxy (server/) are RETIRED entirely
  per Asif 2026-05-22 — the journal app no longer needs the Anthropic API.
  These are deleted from podcast-factory and never appear in the journal repo.
- No shared paths, no submodules, no symlinks between the two repos.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
git push -u origin chore/extract-journal-to-separate-repo
```

5.6. Open PR `chore/extract-journal-to-separate-repo → develop`, merge after review.

---

## 9. Phase 6 — DELETED (was: Re-point Cloudflare deploy to new `journal` repo)

> **RETIRED 2026-05-22**: per Asif's directive, the journal app no longer uses the Anthropic API, so the Cloudflare deploy scaffold AND the API proxy are deleted from the runbook entirely. No re-pointing is needed because there is no Cloudflare Workers project remaining for `journal` after Phase 5 cleanup deletes the scaffold (`wrangler.toml`, `site-worker.js`, `infra/cloudflare/`, `docs/cloudflare/`) and the API proxy (`server/`). The `journal` Worker on Cloudflare itself remains an orphaned external resource — Asif may delete it manually in the Cloudflare dashboard when convenient; no runbook step is needed for that. Phase numbering is preserved: subsequent phases remain Phase 7, Phase 8, etc., for backward compatibility with any prior cross-machine references.

---

## 10. Phase 7 — Rename GitHub repo: `Journal` → `podcast-factory`

> ⚠️ **`gh repo rename` is a §19.4 destructive operation. Phase 7 green-light authorizes the phase as a whole, but Step 7.1 specifically requires a FRESH explicit confirmation from Asif immediately before the rename runs.** The rename produces durable external state visible to all collaborators (Air, anyone with bookmarks to `github.com/asifhussain60/Journal/*`, GitHub Apps installations). Halt and surface before running 7.1 even after Phase 7 is green-lit. Document the approval inline in the chat or operator file before executing.

7.1. **After fresh Asif confirmation** (per the warning above), execute the rename:

```bash
# ASIF-APPROVE-REQUIRED — confirm immediately before running:
gh repo rename --repo asifhussain60/Journal podcast-factory
```

Alternative (manual, equivalent): GitHub UI → `asifhussain60/Journal` → Settings → "Repository name" → enter `podcast-factory` → Rename repository.

7.2. GitHub auto-creates a permanent redirect from `github.com/asifhussain60/Journal/*` to `github.com/asifhussain60/podcast-factory/*`. Old clones continue working transparently.

7.3. Update Studio's main-worktree remote (clean URL):

```bash
cd /Users/ahmac/Code/Journal
git remote set-url origin https://github.com/asifhussain60/podcast-factory.git
git remote -v   # verify
```

Worktrees (`Journal-book-asaas`, `Journal-book-islr`, `Journal-feat-w1`) inherit the parent's remote — no per-worktree update needed.

7.4. **Worktree directory reorganization — MANDATORY** (Studio-local). Consolidate all 4 worktrees under a single parent folder `~/Code/podcast-factory/` so the entire podcast-factory repo is one contained tree.

Target layout after reorganization:

```
~/Code/podcast-factory/         ← parent
├── main/                       ← main clone (.git lives here, branch: dump)
├── book-asaas/                 ← linked worktree, branch book/asaas-al-taveel
├── book-islr/                  ← linked worktree, branch book/islr-mas-i
└── feat-w1/                    ← linked worktree, branch feat/operator-review-studio
```

**Pre-check:** before moving anything, confirm all worktrees are clean (`git status --short` returns empty in each). Stash or commit any in-flight work first.

7.4a. **Close VS Code windows** pointing at any `~/Code/Journal*` path before moving. macOS Finder windows too. File handles on the old paths can interfere with the move.

7.4b. **Capture the current worktree manifest BEFORE moving** — preserves the source-of-truth for the explicit-path repair in 7.4e, and serves as rollback reference if a partial-move failure happens:

```bash
cd ~/Code/Journal
git worktree list --porcelain > ~/Backups/repo-split-$DATE/worktree-manifest-pre-move.txt
cat ~/Backups/repo-split-$DATE/worktree-manifest-pre-move.txt
```

Expected output: 4 worktree blocks, one for `~/Code/Journal` (main) and one for each linked worktree.

7.4c. **Pre-check that the target parent does NOT already exist** — a pre-existing `~/Code/podcast-factory` is a red flag (partial previous attempt, unrelated clone, OS-side leftover). Do NOT use `mkdir -p` here; fail loudly instead.

```bash
test ! -e ~/Code/podcast-factory || {
  echo "ERROR: ~/Code/podcast-factory already exists. Inspect before continuing."
  echo "  If partial previous attempt: review with 'ls -la ~/Code/podcast-factory/' and decide whether to remove it."
  echo "  If unrelated content: choose a different parent path and update the runbook."
  exit 1
}
mkdir ~/Code/podcast-factory
```

7.4d. Move all 4 directories using plain `mv` (worktree pointers temporarily break — repaired in 7.4e). Persist successful moves to `~/Backups/repo-split-$DATE/studio-moved-worktrees.txt` so partial-failure rollback has a durable manifest and subsequent steps don't depend on a transient bash array.

```bash
cd ~/Code

MOVED_FILE=~/Backups/repo-split-$DATE/studio-moved-worktrees.txt
: > "$MOVED_FILE"

# Move main clone first (the one with .git/ directory inside)
mv Journal podcast-factory/main || {
  echo "ERROR: failed to move Journal → podcast-factory/main"
  echo "  Rollback: rmdir ~/Code/podcast-factory (only if empty); investigate; retry."
  exit 1
}

# Move each linked worktree — record each successful move to the manifest file
for pair in "Journal-book-asaas:book-asaas" "Journal-book-islr:book-islr" "Journal-feat-w1:feat-w1"; do
  src="${pair%%:*}"
  dst="${pair##*:}"
  if mv "$src" "podcast-factory/$dst"; then
    echo "$dst" >> "$MOVED_FILE"
    echo "Moved: $src → podcast-factory/$dst"
  else
    moved_count=$(wc -l < "$MOVED_FILE")
    echo "ERROR: failed to move $src → podcast-factory/$dst"
    echo "  Partial state: main already moved; $moved_count linked worktree(s) moved successfully (see $MOVED_FILE)."
    echo "  Rollback: see §14 Path F (filesystem tar restore) — DO NOT proceed with 'git worktree repair' in this state."
    exit 1
  fi
done

echo "Studio moved-worktrees manifest:"
cat "$MOVED_FILE"
```

If any `mv` fails mid-sequence, the script halts with explicit instructions to use Path F (tar restore from `~/Backups/repo-split-$DATE/worktrees-snapshot.tar.gz`) rather than attempt partial repair. The `studio-moved-worktrees.txt` file makes the partial state machine-readable for any recovery scripts.

7.4e. Repair worktree linkage from the new main clone location. `git worktree repair` is bidirectional — it fixes both the main clone's `.git/worktrees/<name>/gitdir` pointers AND each worktree's `.git` file:

```bash
cd ~/Code/podcast-factory/main
git worktree repair \
  ~/Code/podcast-factory/book-asaas \
  ~/Code/podcast-factory/book-islr  \
  ~/Code/podcast-factory/feat-w1

git worktree list
```

Expected output (4 entries, all under `~/Code/podcast-factory/`):

```
/Users/ahmac/Code/podcast-factory/main         <sha> [dump]
/Users/ahmac/Code/podcast-factory/book-asaas   <sha> [book/asaas-al-taveel]
/Users/ahmac/Code/podcast-factory/book-islr    <sha> [book/islr-mas-i]
/Users/ahmac/Code/podcast-factory/feat-w1      <sha> [feat/operator-review-studio]
```

7.4f. **Verify git operations work** in each worktree (sanity check post-move):

```bash
for d in main book-asaas book-islr feat-w1; do
  echo "--- $d ---"
  (cd ~/Code/podcast-factory/$d && git status --short && git log -1 --oneline)
done
```

Each should show clean status and a recognizable commit. If any worktree errors with "fatal: not a git repository" or "gitdir invalid," re-run `git worktree repair` on that path.

7.4g. Update VS Code workspace bookmarks (manual, IDE-side):
- Reopen each worktree at the new path (`File → Open Folder → ~/Code/podcast-factory/<name>`)
- If any `.code-workspace` files exist, edit their `path` fields from `~/Code/Journal*` to `~/Code/podcast-factory/<name>`

7.4h. Search for hardcoded old paths in tracked files (cleaned up in Phase 9):

```bash
cd ~/Code/podcast-factory/main
grep -rn "/Code/Journal" --include="*.md" --include="*.sh" --include="*.py" 2>/dev/null | grep -v "^\\.git/"
```

Capture the list; the actual edits happen in Phase 9.

---

## 11. Phase 8 — Air machine sync

On Air (in a session NOT running the KaR orchestrator — that one should be complete by now).

**Critical first step — set `$DATE` to match Studio's Phase 1.1 execution date.** Air did NOT run Phase 1 (that was Studio-side), so `$DATE` is not defined in Air's shell. Without setting it explicitly, all `~/Backups/repo-split-$DATE/...` paths in this phase expand to `~/Backups/repo-split-/...` and silently misbehave.

```bash
# Set DATE to the same execution date Studio used in Phase 1.1 (Asif passes this in).
# Format: YYYY-MM-DD. Example below; replace with the actual Studio date.
DATE="2026-05-XX"   # ← replace XX with the actual day Studio ran Phase 1
echo "Air using DATE: $DATE"

# Sanity check the value looks right
[[ "$DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || { echo "ERROR: DATE format invalid; expected YYYY-MM-DD"; exit 1; }
```

Air's backup paths point at her OWN `~/Backups/repo-split-$DATE/` directory (separate from Studio's backups, since Studio and Air have independent filesystems). Using Studio's date is a naming-convention choice for cross-machine parity, not a shared-state link.

8.1. From Air's main worktree, update the remote URL and pull:

```bash
cd ~/Code/Journal   # or wherever Air's main clone currently lives
git fetch origin    # redirect handles old URL
git remote set-url origin https://github.com/asifhussain60/podcast-factory.git
git fetch origin
# Switch to develop first so the ff-only pull lands on the right branch
git checkout develop
git pull --ff-only origin develop
```

`--ff-only` matches the discipline used in Phase 3 / Phase 5.1 — Air should not accidentally create a merge commit during sync. If develop has diverged locally on Air (unlikely, but possible if she has work-in-progress on develop), the pull fails loudly and Asif investigates.

8.2. Verify journal-side files are gone:

```bash
ls content/    # should NOT show babu-memoir
ls scripts/    # should NOT show memoir or site
test -d site && echo "ERROR: site still present" || echo "OK: site removed"
```

8.3. Verify book branches still resolve:

```bash
git branch -a | grep book/
git log --oneline origin/develop | head -10
```

8.4. **Apply the contained-parent directory layout** (Air mirrors Studio's Phase 7.4 pattern, using explicit new paths — NOT relying on stale `git worktree list` output after the move).

Pre-check: all of Air's worktrees clean (`git status --short` returns empty in each); close any VS Code windows on the old paths.

**Step 1 — Capture Air's exact worktree inventory BEFORE moving** (this is the source of truth for the repair-paths list; without this, `git worktree list` after `mv` returns stale paths):

```bash
cd ~/Code/Journal   # Air's main clone path
mkdir -p ~/Backups/repo-split-$DATE
git worktree list --porcelain > ~/Backups/repo-split-$DATE/air-worktree-manifest-pre-move.txt
cat ~/Backups/repo-split-$DATE/air-worktree-manifest-pre-move.txt

# Derive the linked-worktree directory names Air needs to move
# (excludes the main worktree, which is at ~/Code/Journal itself)
LINKED_WORKTREES=$(grep "^worktree " ~/Backups/repo-split-$DATE/air-worktree-manifest-pre-move.txt | \
  awk '{print $2}' | grep -v "/Journal$" | xargs -n1 basename)
echo "Linked worktrees to move:"; echo "$LINKED_WORKTREES"
```

**Step 2 — Pre-check parent does not exist, then move** (mirrors Studio Phase 7.4c–7.4d, including partial-move rollback).

Persist the successfully-moved-set to a file at `~/Backups/repo-split-$DATE/air-moved-worktrees.txt`. This makes Steps 3 and 4 resilient to copy/paste execution: if the operator runs each Step in a fresh shell, the file is the durable source of truth — no reliance on a transient bash array.

```bash
cd ~/Code

MOVED_FILE=~/Backups/repo-split-$DATE/air-moved-worktrees.txt
: > "$MOVED_FILE"   # truncate any prior content from a re-run

test ! -e ~/Code/podcast-factory || {
  echo "ERROR: ~/Code/podcast-factory already exists. Inspect before continuing."
  exit 1
}
mkdir ~/Code/podcast-factory

# Move main clone
mv Journal podcast-factory/main || {
  echo "ERROR: failed to move Journal → podcast-factory/main"
  rmdir ~/Code/podcast-factory 2>/dev/null
  exit 1
}

# Move each linked worktree (Air-specific list from Step 1)
for src_basename in $LINKED_WORKTREES; do
  # Map old → new path. Pattern: Journal-<branch-name-with-dashes> → <branch-name-with-dashes>
  dst="${src_basename#Journal-}"
  if mv "$src_basename" "podcast-factory/$dst"; then
    echo "$dst" >> "$MOVED_FILE"
    echo "Moved: $src_basename → podcast-factory/$dst"
  else
    moved_count=$(wc -l < "$MOVED_FILE")
    echo "ERROR: failed to move $src_basename → podcast-factory/$dst"
    echo "  Partial state: main + $moved_count linked worktrees moved (see $MOVED_FILE for the list)."
    echo "  See §14 Path F for restore via filesystem tar."
    exit 1
  fi
done

echo "Air moved-worktrees list:"
cat "$MOVED_FILE"
```

**Step 3 — Repair worktree linkage with EXPLICIT new paths**, reading the moved-set from the file written in Step 2 (Air mirrors Studio Phase 7.4e — does NOT pipe `git worktree list` after the move, which returns stale paths):

```bash
cd ~/Code/podcast-factory/main

MOVED_FILE=~/Backups/repo-split-$DATE/air-moved-worktrees.txt
test -s "$MOVED_FILE" || { echo "ERROR: $MOVED_FILE missing or empty — rerun Step 2"; exit 1; }

# Build the explicit new-path list from the persisted moved-set
REPAIR_PATHS=()
while IFS= read -r dst; do
  REPAIR_PATHS+=("$HOME/Code/podcast-factory/$dst")
done < "$MOVED_FILE"

git worktree repair "${REPAIR_PATHS[@]}"
git worktree list   # verify all paths point at ~/Code/podcast-factory/*
```

**Step 4 — Sanity check each moved worktree** (also reads the file, no bash-array dependency):

```bash
MOVED_FILE=~/Backups/repo-split-$DATE/air-moved-worktrees.txt

# main first, then each moved worktree
for d in main $(cat "$MOVED_FILE"); do
  echo "--- $d ---"
  (cd ~/Code/podcast-factory/"$d" && git status --short && git log -1 --oneline)
done
```

If anything errors, halt and use §14 Path F (filesystem tar restore) — DO NOT attempt manual `.git` file edits.

8.5. (Optional) Clone the new `journal` repo if Asif wants memoir work on Air:

```bash
cd ~/Code
git clone https://github.com/asifhussain60/journal.git
```

Note: `journal` clones outside the `podcast-factory/` parent — it's a separate repo with its own root.

---

## 12. Phase 9 — Update operator infrastructure on `podcast-factory`

9.1. Update repo-name references in tracked docs:

```bash
grep -rl "github.com/asifhussain60/Journal" --include="*.md" 2>/dev/null
# For each file, replace Journal → podcast-factory in URLs (NOT in historical commit messages or content discussing the rename itself)
```

9.2. Update hardcoded local-path references (from Phase 7.4h grep output):

```bash
grep -rl "/Code/Journal" --include="*.md" --include="*.sh" --include="*.py" 2>/dev/null | grep -v "^\\.git/"
# For each file, replace:
#   /Code/Journal-book-asaas    → /Code/podcast-factory/book-asaas
#   /Code/Journal-book-islr     → /Code/podcast-factory/book-islr
#   /Code/Journal-feat-w1       → /Code/podcast-factory/feat-w1
#   /Code/Journal/              → /Code/podcast-factory/main/
#   /Code/Journal:              → /Code/podcast-factory/main:    (rare — usually in shell-prompt examples)
```

Be careful not to replace inside historical commit messages or release-notes content that intentionally references the old path (the operator audit doc at [_workspace/audit/operator-audit-2026-05-21.md](../audit/operator-audit-2026-05-21.md) may have legitimate historical refs).

9.3. Files most likely to need updates:
- [_workspace/plan/operators/coordination-protocol.md](../plan/operators/coordination-protocol.md)
- [_workspace/plan/operators/index.md](../plan/operators/index.md)
- [_workspace/plan/book-queue.md](../plan/book-queue.md)
- [_workspace/plan/operators/setup/recreate-from-scratch.md](../plan/operators/setup/recreate-from-scratch.md)
- [_workspace/plan/operators/setup/machines.md](../plan/operators/setup/machines.md) — likely hardcodes path conventions
- [_workspace/plan/operators/start-session.sh](../plan/operators/start-session.sh) — may resolve worktree paths
- [CLAUDE.md](../../CLAUDE.md)
- `docs/multi-mac-runbook.md` (note: this moves to journal repo; podcast-factory needs a separate podcast-only multi-mac runbook authored here)

9.4. Commit:

```bash
git checkout develop
git checkout -b chore/operator-files-post-split
# ... edits ...
git add -A
git commit -m "chore: post-split operator-file URL updates (Journal → podcast-factory)"
git push
```

---

## 12A. Phase 9.5 — Library structure consolidation

**Goal**: Hoist `content/podcast/library/` to a top-level `library/` folder that contains ONLY shipped, prod-ready artifacts. The per-book in-progress workspace moves from `content/podcast/library/books/<slug>/` to the root-level `_workspace/books/<slug>/` so workspace lives in a single root folder accessible from every worktree/branch (per Asif 2026-05-22 directive). Books are processed in worktrees on book branches against `_workspace/books/<slug>/`; when a book reaches a ship verdict, its polished outputs are promoted into `library/books/<slug>/` via a one-way script. See §2A.6 for the visual reference.

This phase runs **after** Phase 9 (operator-file URL/path updates) because Phase 9 only repairs `/Code/Journal` → `/Code/podcast-factory/` paths; Phase 9.5's path rewrites are a separate, content-side move (`content/podcast/library/books/` → `_workspace/books/`) that touches different files (mostly `scripts/podcast/`, `skills-staging/podcast/`, `.github/agents/podcast-*.agent.md`, and orchestrator state files inside `_workspace/books/<book>/_system/`).

**Note on macOS case-folding** (APFS default): the existing `_workspace/Books/` PDF intake folder (capital B, gitignored) and the new `_workspace/books/` orchestrator workspace (lowercase b, tracked) resolve to the SAME folder on case-insensitive filesystems. That's intentional — the merged folder holds both raw PDF source (gitignored via `_workspace/books/*/source*` and `_workspace/books/*.pdf`) AND the orchestrator state (tracked). Operators on case-sensitive Linux filesystems can opt to treat them as separate; the runbook canonicalizes on lowercase `_workspace/books/` for paths in tracked content.

### 12A.1 Pre-flight for Phase 9.5

- [ ] Phases 1 through 9 complete on `develop`.
- [ ] No active orchestrator run on any book — all `orchestrator-state.json` files show `phase_status` of `halted-*`, `shipped`, or `idle`. (Active runs would race with the workspace move.)
- [ ] All 4 worktrees clean (`git status --short` empty in each).
- [ ] Workspace location DECIDED 2026-05-22: per Asif's directive, the per-book workspace moves to root-level `_workspace/books/<slug>/` (single root folder, accessible from all worktrees/branches). The existing `_workspace/Books/` PDF intake convention merges in on case-insensitive macOS filesystems.

### 12A.2 Target structure

Top-level `library/` after Phase 9.5 is complete (see §2A.6 for the full tree). The four invariants:

| Path | Role | Mutability |
|---|---|---|
| `library/books/<slug>/index.md` | Book metadata (title, author, archetype, series list, ship verdict, dates, episode count, cover ref) | Auto-generated by promotion script; manual edits discouraged |
| `library/books/<slug>/transcript/` | Polished NotebookLM SOURCE — one clean prose file per chapter | Auto-promoted; never edited in place |
| `library/books/<slug>/podcasts/` | Episode bundles organized by series; `_series-index.md` + `series-NN-<slug>/EP<NN>-<chapter>/{source.txt, framing.md, challenger-report.md, audio.mp3?}` | Auto-promoted; never edited in place |
| `library/_meta/catalog.md` | Cross-book index (markdown table) | Auto-generated; manual edits discouraged |

Optional additions per book:
- `library/books/<slug>/cover.{jpg,png}` — book art if curated (manual asset, not pipeline-generated)
- `library/books/<slug>/podcasts/series-NN-<slug>/EP<NN>-<chapter>/audio.mp3` — NotebookLM-generated audio, populated only when audio-archive integration lands (see §12A.7 open decision 2)

`library/archetypes/` (currently at `content/podcast/library/archetypes/`) moves to top-level `library/archetypes/` — already a cross-book reference, doesn't belong inside the workspace.

Non-book categories (`articles/`, `documents/`, `interviews/`, `lectures/`, `letters/`) follow the same hoist-to-top pattern: shipped items land in `library/<category>/<slug>/`; in-progress drafts move to `_workspace/<category>/`.

### 12A.3 Move per-book workspace to root and create top-level library

```bash
cd ~/Code/podcast-factory/main
git checkout develop
git pull --ff-only origin develop
git checkout -b chore/library-hoist

# Move per-book in-progress state to root-level _workspace/books/
# (On case-insensitive macOS APFS, this merges with the existing _workspace/Books/ PDF intake folder — intentional)
git mv content/podcast/library/books _workspace/books

# Move category sub-workspaces (in-progress drafts for non-book content)
for cat in articles documents interviews lectures letters _sandbox; do
  if [[ -d "content/podcast/library/$cat" ]]; then
    git mv "content/podcast/library/$cat" "_workspace/$cat"
  fi
done

# Create the empty shipped-catalog skeleton at top level
mkdir -p library/{_meta,archetypes,books,articles,documents,interviews,lectures,letters}
touch library/_meta/.gitkeep library/archetypes/.gitkeep \
      library/books/.gitkeep library/articles/.gitkeep \
      library/documents/.gitkeep library/interviews/.gitkeep \
      library/lectures/.gitkeep library/letters/.gitkeep

# Move the cross-book archetypes (finished reference material, not in-progress)
git mv content/podcast/library/archetypes/* library/archetypes/ 2>/dev/null || true
git rm -rf content/podcast/library/archetypes 2>/dev/null || true

# Remove the now-empty content/podcast/library/ scaffold
git rm -rf content/podcast/library 2>/dev/null || true

# Update .gitignore to selectively ignore raw PDF intake inside _workspace/books/
# (keeps orchestrator state tracked, ignores source PDFs and bulky intermediate audio)
cat >> .gitignore <<'EOF'

# Phase 9.5 — per-book workspace at _workspace/books/<slug>/
# Track orchestrator state + chapters + episode drafts; ignore raw source intake.
_workspace/books/*/source*
_workspace/books/*/*.pdf
_workspace/books/*/raw/
_workspace/Books/*/source*
_workspace/Books/*/*.pdf
_workspace/Books/*/raw/
EOF

git status --short
```

### 12A.4 Update pipeline scripts to point at the new workspace location

The path move breaks every hardcoded `content/podcast/library/books/` reference. Rewrite in two passes (workspace path + new shipped-library path):

```bash
# Pass 1 — per-book workspace path rewrite (mechanical)
grep -rl "content/podcast/library/books/" \
  scripts/podcast/ skills-staging/podcast/ \
  _workspace/plan/operators/ .github/agents/ docs/podcast/ \
  --include="*.py" --include="*.md" --include="*.sh" --include="*.yml" 2>/dev/null \
  | xargs sed -i '' 's|content/podcast/library/books/|_workspace/books/|g'

# Pass 2 — bare content/podcast/library/ references (archetypes, category folders)
grep -rl "content/podcast/library/" \
  scripts/podcast/ skills-staging/podcast/ \
  _workspace/plan/operators/ .github/agents/ docs/podcast/ \
  --include="*.py" --include="*.md" --include="*.sh" --include="*.yml" 2>/dev/null \
  | xargs sed -i '' 's|content/podcast/library/archetypes/|library/archetypes/|g; s|content/podcast/library/|_workspace/|g'

# Verify nothing broke obviously
python3 -c "import ast; ast.parse(open('scripts/podcast/orchestrate_book.py').read())"
python3 -c "import ast; ast.parse(open('scripts/podcast/_authoring.py').read())"
python3 -c "import ast; ast.parse(open('scripts/podcast/build_episode_txt.py').read())"
python3 -c "import ast; ast.parse(open('scripts/podcast/extract_chapter.py').read())"

# Pass 3 — add the shipped-library reference to scripts that need it
# (Only ship_to_library.py and the catalog generator; orchestrator stays workspace-only.)
```

Files most likely affected (verify with the grep above):
- `scripts/podcast/orchestrate_book.py` — workspace path → `_workspace/books/<slug>/`
- `scripts/podcast/_authoring.py` — workspace path
- `scripts/podcast/build_episode_txt.py` — workspace path
- `scripts/podcast/extract_chapter.py` — workspace path
- `skills-staging/podcast/SKILL.md` — workspace path + new ship-to-library mention
- `.github/agents/podcast-orchestrator.agent.md` — workspace path
- `.github/agents/podcast-operator.agent.md` — workspace path + new ship-to-library mention
- `_workspace/plan/operators/start-session.sh` — workspace path (resolves orchestrator-state.json at the new location)
- `_workspace/plan/operators/coordination-protocol.md` — workspace path
- `_workspace/plan/operators/index.md` — workspace path

### 12A.5 Author the promotion script

`scripts/podcast/ship_to_library.py` — the ONLY supported path from workspace → library. Behavior:

```
ship_to_library.py --book <slug> [--episode <EP-id>] [--dry-run]
```

The script:
1. Reads `_workspace/books/<slug>/_system/orchestrator-state.json` to confirm shippable state. Halts if `phase_status` is not `shipped`, `ship-ready`, or `ship-with-caution-approved`.
2. Reads `_workspace/books/<slug>/_system/challenger-report.md` to record the verdict.
3. For each shipped episode:
   - Copies `_workspace/books/<slug>/chapters/<chapter>.txt` (the TTS-safe polished SOURCE) → `library/books/<slug>/transcript/<NN>-<chapter-slug>.md` with a minimal YAML front-matter block (title, chapter-id, source-path-in-workspace, ship-date).
   - Copies `_workspace/books/<slug>/episode-drafts/<chapter>/source.txt`, `framing.md`, `challenger-report.md` → `library/books/<slug>/podcasts/series-<NN>-<series-slug>/EP<NN>-<chapter-slug>/`.
   - If `_workspace/books/<slug>/episode-drafts/<chapter>/audio.mp3` exists (post audio-archive integration), copies that too.
4. Generates `library/books/<slug>/podcasts/_series-index.md` from `_workspace/books/<slug>/_system/series-plan.md`.
5. Generates `library/books/<slug>/podcasts/series-<NN>-<series-slug>/_series.md` from `_system/series-plan.md` (per-series block).
6. Generates `library/books/<slug>/index.md` from series-plan + challenger-report + orchestrator-state.
7. Regenerates `library/_meta/catalog.md` (markdown table of all books with archetype, ship date, episode count, link).
8. Optional: emits `library/_meta/catalog.json` for downstream site-tools.

Idempotency: re-running the script after additional episodes ship should add/update only the new episodes; never delete from `library/`.

### 12A.6 Migration of existing books

Each book gets an explicit promotion decision based on current state:

| Book | Current phase / verdict | Phase 9.5 action |
|---|---|---|
| `kitab-al-riyad` | HALTED-BY-OPERATOR; EP10 SHIP-WITH-CAUTION; EP14 partial; EP01–09 + EP11–13 TTS-safe .txt only | Promote ONLY EP10 (`--episode EP10`); leave the rest in workspace. Studio's manual archetype-driven finish promotes each chapter as it lands. |
| `asaas-al-taveel` | Phase 0b / halted-for-transcript-review | NO promotion — not yet shipped. Stays in workspace. |
| `islr-mas-i` | (verify with state.json) | Promote only if shipped; otherwise stays in workspace. |
| `ayyuhal-walad` | (verify with state.json) | Promote only if shipped; otherwise stays in workspace. |
| `the-master-and-the-disciple` | (verify with state.json) | Promote only if shipped; otherwise stays in workspace. |

Verify each book's actual state before deciding:
```bash
for b in asaas-al-taveel ayyuhal-walad islr-mas-i kitab-al-riyad the-master-and-the-disciple; do
  echo "=== $b ==="
  jq '{phase, phase_status, last_completed_phase}' \
    _workspace/books/$b/_system/orchestrator-state.json 2>/dev/null \
    || echo "(no state.json)"
done
```

### 12A.7 Phase 9.5 design picks (all resolved 2026-05-22)

All five decisions are baked in below; the runbook now executes Phase 9.5 deterministically.

1. ~~**Workspace location**~~ — **Resolved 2026-05-22**: per-book workspace moves to root-level `_workspace/books/<slug>/` (single root folder, accessible from all worktrees/branches per Asif's directive). The existing `_workspace/Books/` PDF intake folder merges in on case-insensitive macOS APFS.
2. ~~**Audio archival in `library/books/<slug>/podcasts/.../audio.mp3`**~~ — **Resolved 2026-05-22: DEFER**. NotebookLM-audio download isn't yet automated; including it in Phase 9.5 expands scope unnecessarily. `ship_to_library.py` will copy `audio.mp3` opportunistically if the file exists in `_workspace/books/<slug>/episode-drafts/<chapter>/`, but the script does NOT block on its absence. A separate future runbook ("audio-archive integration") will add the download step.
3. ~~**Catalog format**~~ — **Resolved 2026-05-22: markdown only initially**. `library/_meta/catalog.md` is the only auto-generated catalog file in Phase 9.5. A `library/_meta/catalog.json` companion gets added later when site-tools or downstream consumers actually need it — adding it speculatively now would create a maintenance burden with no consumer.
4. ~~**Cover art ingestion**~~ — **Resolved 2026-05-22: manually-curated**. `library/books/<slug>/cover.{jpg,png}` is treated as a manual asset that operators drop in post-ship. `ship_to_library.py` does NOT create or fetch covers. A short `library/README.md` (also created in Phase 9.5) documents this convention so operators on other machines know where covers go.
5. ~~**CI guard against manual `library/` edits**~~ — **Resolved 2026-05-22: ADD IT**. Phase 9.5 includes authoring `.github/workflows/library-readonly.yml` — fails any PR that touches `library/` without either (a) a commit message starting with `ship: ` (the convention used by `ship_to_library.py`), or (b) an explicit `[library-manual-edit]` marker in the commit body for one-off manual overrides (e.g., dropping cover art). The workflow runs on `pull_request` and posts an inline check failure if violated.

### 12A.8 Commit + push

```bash
cd ~/Code/podcast-factory/main
git add -A
git commit -m "chore: library hoist — shipped catalog at library/, workspace at _workspace/books/

Top-level library/ now holds only shipped, prod-ready artifacts:
- library/books/<slug>/{index.md, transcript/, podcasts/, cover.*}
- library/archetypes/ (moved from content/podcast/library/archetypes/)
- library/_meta/catalog.md (auto-generated cross-book index)

Per-book in-progress workspace moved from content/podcast/library/books/
to root-level _workspace/books/<slug>/ per Asif's directive: single
root-level workspace folder accessible from all worktrees/branches.
On case-insensitive macOS APFS, the existing _workspace/Books/ PDF intake
folder merges with this new path.

Promotion is one-way and explicit via scripts/podcast/ship_to_library.py;
manual edits to library/ are discouraged and CI-checked.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"

git push -u origin chore/library-hoist
```

Open PR `chore/library-hoist → develop`, merge after review. Runbook then advances to Phase 10 (post-split verification), with the added verification step: `library/_meta/catalog.md` lists every shipped book; `_workspace/books/` is the only path the orchestrator reads/writes for per-book state.

### 12A.9 Post-Phase-9.5 invariants to enforce

- Pipeline writes per-book state ONLY to `_workspace/books/<slug>/`.
- `ship_to_library.py` is the ONLY writer of `library/`.
- `library/` paths appear in commit messages as `ship: <book> <episode>` (convention used by the CI guard above).
- `start-session.sh` checks `library/_meta/catalog.md` for shipped state in addition to `_workspace/books/<slug>/_system/orchestrator-state.json`.

---

## 13. Phase 10 — Post-split verification

**On podcast-factory:**

- [ ] All 6 active branches still resolve: `git branch -a | grep -E "book/|feat/"`
- [ ] All 4 worktrees still functional: `git worktree list`
- [ ] `make verify` passes (Azure stack OK — should be untouched)
- [ ] Active orchestrator can be resumed: try `python3 scripts/podcast/orchestrate_book.py --resume <a-book>` on a benign phase
- [ ] CI workflows pass on the next push
- [ ] `github.com/asifhussain60/podcast-factory/issues` opens correctly; old `Journal` issue links redirect

**On journal:**

- [ ] `git clone https://github.com/asifhussain60/journal.git` works
- [ ] `cd journal && site/index.html` exists; `npx serve site` shows the page locally (no deploy target; local-only)
- [ ] No leftover podcast references in [CLAUDE.md](../../CLAUDE.md), [framework.md](../../framework.md), or [package.json](../../package.json)
- [ ] No `infra/azure/` directory present
- [ ] No `scripts/podcast/` directory present
- [ ] **Cloudflare/API-proxy retirement verified**: no `server/`, `wrangler.toml`, `site-worker.js`, `infra/cloudflare/`, `docs/cloudflare/`, `docs/anthropic-api-setup.md`, or `docs/proxy-setup.md` present anywhere in the repo. Run: `git ls-files | grep -E '^(server/|wrangler\.toml$|site-worker\.js$|infra/cloudflare/|docs/cloudflare/|docs/anthropic-api-setup\.md$|docs/proxy-setup\.md$)'` should return EMPTY.

**Library hoist (Phase 9.5) invariants on podcast-factory:**

- [ ] `library/` exists at the repo root and contains only shipped artifacts
- [ ] `_workspace/books/` exists (moved from `content/podcast/library/books/`) and contains the in-progress per-book state; orchestrator-state.json files resolve at the new location
- [ ] No pipeline script writes outside `_workspace/` — verify: `grep -rn "content/podcast/library/" scripts/ skills-staging/podcast/ .github/agents/podcast-*.agent.md 2>/dev/null | wc -l` returns 0
- [ ] `content/podcast/library/` directory no longer exists — verify: `test ! -d content/podcast/library && echo OK || echo "STILL PRESENT — Phase 9.5 cleanup incomplete"`
- [ ] `library/_meta/catalog.md` exists and lists at least the books promoted in Phase 9.5.6 (e.g., kitab-al-riyad EP10)
- [ ] `library/archetypes/islamic-scholastic-text.md` exists (moved from prior location)
- [ ] For each promoted book: `library/books/<slug>/{index.md, transcript/, podcasts/}` all populated

---

## 14. Rollback / restore procedure

This section defines restore paths for every failure point in the runbook. The right path depends on how far execution progressed before the failure. **All restore paths assume Phase 1's backups completed successfully** — if any backup layer was skipped or corrupt, halt and contact Asif before attempting recovery.

### 14.1 Restore decision tree

| Failed during | Path | What it does | Affected machines |
|---|---|---|---|
| Phase 1.1–1.5 (backup setup) | A | Local reset, no GitHub state changed | Studio only |
| Phase 1.6 (journal repo created) | B | Delete journal repo, retry | Studio + GitHub |
| Phase 2 (filter-repo) | A | Discard sibling clone | Studio only |
| Phase 3 (push to journal) | B | Delete journal repo + retry | Studio + GitHub |
| Phase 4 (journal repo identity edits) | B | Delete journal repo OR keep and re-edit | Studio + GitHub |
| Phase 5 (cleanup commit on podcast-factory) | C | Revert merge OR reset develop | Studio + GitHub |
| Phase 6 — DELETED | — | n/a (Cloudflare retired 2026-05-22) | n/a |
| Phase 7 (GitHub rename) | E | Rename back via `gh repo rename` | Studio + GitHub |
| Phase 7.4 (worktree reorganization) | F | Restore from tar snapshot | Studio only |
| Phase 8 (Air sync) | G | Air resets remote + repulls (Air-local) | Air only |
| Phase 9 (operator-file URL/path updates) | H | Revert the operator-update commit | Studio + GitHub |
| Phase 10 reveals corruption / unknown state | NUCLEAR | Mirror restore + GitHub-side rewind | Both machines |

### 14.2 Path A — Local-only reset (no GitHub state changed)

Use when: failed before any GitHub-side state change (Phases 1.1–1.5, Phase 2).

Reads the tag-branch map written in Phase 1.1 — **does NOT reconstruct branch names from tag strings** (that approach is brittle when branch naming evolves).

```bash
# 1. Discard any in-progress filter-repo clone
rm -rf ~/Code/Journal-filter

# 2. Reset every Studio branch using the explicit map file
MAP_FILE=~/Backups/repo-split-$DATE/tag-branch-map.txt
test -f "$MAP_FILE" || { echo "ERROR: map file missing — use Path NUCLEAR instead"; exit 1; }

cd ~/Code/Journal
while IFS=' ' read -r branch tag_name commit_sha; do
  if git rev-parse --verify "$branch" >/dev/null 2>&1; then
    git checkout "$branch" && git reset --hard "$tag_name"
    echo "Restored: $branch → $tag_name ($commit_sha)"
  else
    echo "SKIP: local branch $branch does not exist (origin-only; re-create via 'git checkout -b $branch origin/$branch' if needed)"
  fi
done < "$MAP_FILE"
git checkout develop

# 3. Verify clean state
git status --short && git log --oneline -5
```

No GitHub cleanup needed. Resume by re-attempting Phase 1.

### 14.3 Path B — Delete new journal repo + reset

Use when: failed at Phase 1.6 / 2 / 3 / 4 (new repo exists, may have content).

```bash
# Delete the new journal repo on GitHub
gh repo delete asifhussain60/journal --yes

# Discard local filter-repo clone
rm -rf ~/Code/Journal-filter

# Reset local state per Path A if needed
```

Resume from Phase 2 after fixing the underlying cause.

### 14.4 Path C — Revert podcast-factory cleanup commit

Use when: failed at Phase 5 (journal files removed, podcast-factory cleanup commit merged to develop).

**Preferred (non-destructive): `git revert`.**

```bash
cd ~/Code/Journal   # or new path if Phase 7.4 already ran
git checkout develop

CLEANUP_SHA=$(git log --oneline | grep "chore: extract journal" | head -1 | awk '{print $1}')
git revert "$CLEANUP_SHA"
git push origin develop
```

> ⚠️ **DESTRUCTIVE ALTERNATIVE — REQUIRES EXPLICIT ASIF APPROVAL — DO NOT RUN WITHOUT GREEN-LIGHT** ⚠️
>
> Only use this if `git revert` cannot resolve cleanly (extreme conflict scenario). Force-push to develop rewrites shared history and impacts Air's clone.
>
> ```bash
> # ASIF-APPROVE-REQUIRED:
> # git reset --hard pre-split-$DATE/develop
> # git push --force-with-lease origin develop
> ```
>
> Halt and surface to Asif before running. Document the approval inline in the chat / operator file before executing.

### 14.5 Path D — DELETED (was: Re-point Cloudflare back)

> **RETIRED 2026-05-22**: Phase 6 no longer exists, so Path D no longer applies. If for some reason Cloudflare re-pointing becomes necessary again, restore the original Path D from git history before the 2026-05-22 Cloudflare-retirement edit.

### 14.6 Path E — GitHub repo rename back

Use when: failed at Phase 7 (Journal already renamed to podcast-factory).

```bash
# Rename back (GitHub creates an inverse redirect)
gh repo rename --repo asifhussain60/podcast-factory Journal

# Restore Studio's remote URL
cd ~/Code/podcast-factory/main   # or whatever path is current
git remote set-url origin https://github.com/asifhussain60/Journal.git
git remote -v   # verify

# Notify Air to do the same
```

### 14.7 Path F — Filesystem tar restore (worktree reorg failed)

Use when: Phase 7.4 worktree reorg got into a broken state — worktree pointers won't repair via `git worktree repair`.

```bash
# 1. Quarantine the broken state
mv ~/Code/podcast-factory ~/Code/podcast-factory.BROKEN.$(date +%s)

# 2. Extract the tar snapshot to original paths
cd ~/Code
tar -xzf ~/Backups/repo-split-$DATE/worktrees-snapshot.tar.gz

# 3. Verify worktrees are functional
cd Journal
git worktree list
git status

# 4. Test each worktree
for d in ../Journal-book-asaas ../Journal-book-islr ../Journal-feat-w1; do
  (cd "$d" && git status --short && git log -1 --oneline)
done
```

After confirming the tar restore is clean, the BROKEN directory can be deleted. Resume from Phase 7.4 (worktree reorg) with the lesson learned.

### 14.8 Path G — Air-side recovery

Use when: Air's machine got into a confused state during Phase 8.

```bash
# On Air, from the main clone
cd ~/Code/Journal   # or wherever Air's clone is
git remote set-url origin https://github.com/asifhussain60/podcast-factory.git
git fetch origin

# Reset Air's branch to its tracked origin counterpart
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
git reset --hard "origin/$CURRENT_BRANCH"

# If Air's worktrees are corrupted, repair from a fresh clone:
# (Air's local-machine equivalent of NUCLEAR — see 14.10)
```

If Air ran her own Phase 1 backup, she can restore from her local mirror/tar. Otherwise she clones fresh from origin.

### 14.9 Path H — Revert operator-file updates

Use when: failed at Phase 9 (operator-file path/URL rewrites introduced errors).

```bash
cd ~/Code/podcast-factory/main
git checkout develop
OPERATOR_SHA=$(git log --oneline | grep "chore: post-split operator-file" | head -1 | awk '{print $1}')
git revert "$OPERATOR_SHA"
git push origin develop
```

### 14.10 NUCLEAR — Mirror restore + GitHub-side rewind

Use when: catastrophic — can't determine intermediate state, local clone corrupted, or restore paths A–H fail to produce a clean state.

**Step 1 — Local restore from mirror:**

```bash
# Quarantine all broken local state
mv ~/Code/podcast-factory ~/Code/podcast-factory.BROKEN.$(date +%s) 2>/dev/null
mv ~/Code/Journal ~/Code/Journal.BROKEN.$(date +%s) 2>/dev/null
mv ~/Code/Journal-book-asaas ~/Code/Journal-book-asaas.BROKEN.$(date +%s) 2>/dev/null
mv ~/Code/Journal-book-islr ~/Code/Journal-book-islr.BROKEN.$(date +%s) 2>/dev/null
mv ~/Code/Journal-feat-w1 ~/Code/Journal-feat-w1.BROKEN.$(date +%s) 2>/dev/null

# Restore from mirror
cd ~/Code
git clone --no-local ~/Backups/repo-split-$DATE/Journal-mirror.git Journal
cd Journal
git remote set-url origin https://github.com/asifhussain60/Journal.git

# Recreate worktrees
git worktree add ../Journal-book-asaas book/asaas-al-taveel
git worktree add ../Journal-book-islr book/islr-mas-i
git worktree add ../Journal-feat-w1 feat/operator-review-studio
```

**Step 2 — GitHub-side rewind (destructive; each command requires EXPLICIT Asif approval before running):**

> ⚠️ **EVERY COMMAND IN STEP 2 REWRITES SHARED STATE ON GITHUB. DO NOT RUN UNATTENDED.** ⚠️
>
> Each `gh repo delete`, `gh repo rename`, and especially `git push --mirror` (or `--force-with-lease` of refs/heads/*) is a separately authorized operation. Halt and surface to Asif for explicit go-ahead on each one. Document the approval inline before executing.

```bash
# ASIF-APPROVE-REQUIRED: Delete the new journal repo if created
# gh repo delete asifhussain60/journal --yes 2>/dev/null

# ASIF-APPROVE-REQUIRED: Rename podcast-factory back to Journal if renamed
# gh repo rename --repo asifhussain60/podcast-factory Journal 2>/dev/null

# ASIF-APPROVE-REQUIRED (HIGHEST BLAST RADIUS): Force-restore origin from mirror
# This rewrites every ref on origin to the pre-split state. Air will need to
# `git fetch + reset --hard` her local clone afterwards.
# cd ~/Backups/repo-split-$DATE/Journal-mirror.git
# git push --mirror https://github.com/asifhussain60/Journal.git
```

The `git push --mirror` command pushes every local ref to origin and DELETES any origin refs that don't exist locally. It is the most destructive single command in the runbook. Treat it as a separately-approved nuclear option, never the default first move.

Less-destructive alternative when only develop/main need rewinding (still requires approval):

```bash
# ASIF-APPROVE-REQUIRED: Surgically rewind develop + main only
# cd ~/Backups/repo-split-$DATE/Journal-mirror.git
# git push --force-with-lease https://github.com/asifhussain60/Journal.git \
#   refs/heads/develop:refs/heads/develop \
#   refs/heads/main:refs/heads/main
# (No --tags; tag pollution is reversed separately if needed)
```

**Step 3 — Cloudflare:** N/A — Cloudflare deploy was retired 2026-05-22. If the runbook's Cloudflare-retirement edit (Phase 5 cleanup deleting `wrangler.toml`, `site-worker.js`, `infra/cloudflare/`, `docs/cloudflare/`, `server/`) is being rolled back as part of the nuclear restore, the mirror clone in Layer 2 already contains the pre-retirement state — `git push --mirror` (Step 2 above) restores those files automatically.

**Step 4 — Air re-clones:**
Air discards her local clone and re-clones from origin: `cd ~/Code && rm -rf Journal* && git clone https://github.com/asifhussain60/Journal.git`. Air's worktrees recreate as needed.

### 14.11 Verification of restore

After ANY restore path, run this verification:

```bash
echo "=== Local state ==="
cd ~/Code/Journal   # or main clone after restore
git status
git branch -a | wc -l
git log --oneline -5
git worktree list
git remote -v

echo "=== Backup-tag parity (should match pre-execution counts) ==="
git tag | grep "pre-split-$DATE" | wc -l
diff <(git for-each-ref --format='%(refname) %(objectname)' | sort) \
     <(sort ~/Backups/repo-split-$DATE/refs-snapshot.txt) | head -20

echo "=== GitHub-side ==="
gh repo view asifhussain60/Journal --json url,visibility 2>&1 | head -3
gh repo view asifhussain60/journal 2>&1 | grep -q "Could not resolve" && echo "OK: journal repo does NOT exist (deleted)" || echo "WARN: journal repo still exists"
gh repo view asifhussain60/podcast-factory 2>&1 | grep -q "Could not resolve" && echo "OK: podcast-factory does NOT exist (renamed back)" || echo "WARN: podcast-factory still exists"
```

If `refs-snapshot.txt` diff shows zero lines, the restore matches the pre-execution state exactly.

### 14.12 Backup retention policy

Do NOT delete any backup layer until at least **7 days of stable operation** on both new repos. After that:

```bash
# Move backup to long-term archive
mv ~/Backups/repo-split-$DATE ~/Backups/_archive/

# Optionally delete the secondary GitHub backup repo
gh repo delete asifhussain60/journal-backup-pre-split-$DATE --yes
```

Recommended: keep at least Layer 2 (mirror clone) indefinitely in `~/Backups/_archive/`. It's compressed, small, and immutable — cheap insurance against late-discovered issues.

---

## 15. Estimated time

| Phase | Time | Notes |
|---|---|---|
| 1 — 4-layer backup + GitHub journal repo create | 25 min | Tags + mirror clone + tar + optional Layer 4 + journal repo creation |
| 2 — filter-repo extract | 15 min | Fresh sibling clone + filter-repo run |
| 3 — Push to journal repo + anchor tag | 10 min | branches only (no --tags); `journal-split-$DATE` tag |
| 4 — Journal repo identity + tailor duplicated configs | 45 min | CLAUDE/Makefile/package.json edits + skill-registry tailoring + copilot-instructions tailoring + agent reviews |
| 5 — Podcast-factory cleanup commit + tailored configs | 35 min | git rm (journal-exclusive + reclassified + retired Cloudflare/server) + edit shared root files + tailor skill-registry/copilot-instructions for podcast-factory + PR + merge |
| ~~6 — Cloudflare re-point~~ | — | **DELETED 2026-05-22** (Cloudflare deploy retired) |
| 7 — GitHub rename + Studio remote update | 5 min | `gh repo rename` + one `git remote set-url` |
| 7.4 — Studio worktree reorganization (contained-parent layout) | 20 min | pre-checks + mv + `git worktree repair` + verify each |
| 8 — Air sync + Air-side worktree reorg | 20 min | Air mirrors Studio's 7.4 pattern with her own worktree set |
| 9 — Operator-file URL + path updates | 25 min | URL rewrites + `/Code/Journal` → `/Code/podcast-factory/` path rewrites |
| 9.5 — Library structure consolidation (hoist library/ to top level + workspace rename) | 60 min | Path rename (mechanical sed) + author `ship_to_library.py` + first promotion (KaR EP10) + catalog generation + commit + PR + merge |
| 10 — Verification | 20 min | Checklist walk-through (now includes library hoist invariants) |
| **TOTAL** | **~4 hours 45 min** | Focused work; can be split across sessions. Phase 6 deletion (-15 min) net-against Phase 9.5 addition (+60 min) = +45 min vs prior estimate. |

Plus 2–4 hour wait for Air's KaR Phase 10 merge before Phase 1 begins.

---

## 16. Open questions for Asif before execution

1. ~~**Worktree directory rename** (Phase 7.4): leave as-is or rename?~~ **Resolved 2026-05-22**: contained-parent layout is mandatory. All Studio worktrees move under `~/Code/podcast-factory/` (main + book-asaas + book-islr + feat-w1). Air applies the same pattern locally in Phase 8.4.
2. ~~**Azure `APP_NAME` field** (Phase 5.3): edit from `"journal"` to `"podcast-factory"` for label consistency, or leave as-is for zero churn?~~ **Resolved 2026-05-22**: edit to `"podcast-factory"` as a cosmetic config-label change only; Azure resources themselves remain `journal-*` named (no Azure-side rename). Decision codified in §2 decision 3 + executed in Phase 5.3.
3. **Air's journal-repo clone** (Phase 8.5): does Asif do memoir work on Air? If yes, clone the new journal repo there too. If no, skip — Studio remains the only memoir-capable machine.
4. **Safety tag date** (Phase 1.1): use `pre-split-2026-05-XX` with the actual execution date. Replace XX before running.
5. **GitHub repo creation + rename** (Phase 1.2 + Phase 7.1): can Claude do these via `gh` CLI (if authenticated locally with `repo` + `delete_repo` scopes), or does Asif do them manually in GitHub UI? See §19 for the answer based on local environment check.

---

## 17. Appendix — File-by-file inventory

Three categories: **DUPLICATED to both**, **journal-only**, **podcast-factory-only**. After the split, the two repos are fully disconnected — duplicated items become two independent copies that evolve separately.

### 17.A DUPLICATED to BOTH repos (independent copies after split)

These items are general-utility — Asif uses them across both projects. Each repo gets its own copy; future edits do NOT cross-propagate.

**General-utility skills** (each becomes 2 independent copies):
- `skills-staging/clean-commit/`
- `skills-staging/cowork-brief/`
- `skills-staging/repo-surgeon/`
- `skills-staging/tell-me/`
- `skills-staging/usage-auditor/`

**General-utility Claude Code agents** (each becomes 2 independent copies):
- `.github/agents/CORTEX.agent.md`
- `.github/agents/refine-prompt.agent.md`
- `.github/agents/reconcile.agent.md`
- `.github/agents/repo-surgeon.agent.md`
- `.github/agents/operating-contract.md`

**General-utility Claude Code agent installers** (each becomes 2 independent copies):
- `infra/claude-agents/refine-prompt.md`

**Reference materials**:
- `reference/cortex-challenger-framework.md`
- `reference/skill-bootstrap.md`
- `reference/skill-overlays/` (full subtree)
- `reference/skill-registry.md` — each copy edited per Phase 4 / Phase 5 to list only the skills present in that repo

**Skill installer**:
- `scripts/install-claude-skills.sh` — both repos need it to install their respective skill sets

**Arabic reference set** (two independent copies, neither canonical):
- `content/_shared/arabic/` (full subtree) — directory name preserves `_shared/` for path stability; the "shared" framing is historical only

**GitHub-level metadata** (each repo gets its own tailored version):
- `.github/copilot-instructions.md` — tailored per repo (Phase 4 / Phase 5 Asif-edits)
- `CLAUDE.md` — rewritten per repo to reflect single-purpose
- `framework.md` — rewritten per repo
- `README.md` — rewritten per repo

### 17.B Journal-only (exclusive to the new `journal` repo)

**Content**:
- `content/babu-memoir/` (full subtree)

**Scripts**:
- `scripts/memoir/` (auto_delta, snapshot, etc.)
- `scripts/site/sync_chapters.sh`

**Skills + agents (journal-specific)**:
- `skills-staging/journal/`
- `.github/agents/journal-orchestrator.agent.md`
- `.github/agents/journal-challenger.agent.md`
- `infra/claude-agents/journal-challenger.md`

**Site (static memoir display; no deploy)**:
- `site/` (full subtree — local-only after Cloudflare deploy retirement; serve via `npx serve site`)

**Site/UI-related general skills (RECLASSIFIED to journal per refactor)**:
- `skills-staging/css-theme-sync/` — theme work targets site CSS → journal
- `skills-staging/ui-modernizer/` — UI work targets site → journal

**Slimmed root files** (rewritten/tailored):
- `Makefile` — slimmed: site-dev, site-deploy, no Azure or podcast targets
- `package.json` — `"name": "journal"`
- `.gitignore` — slimmed: no podcast/Azure entries

### 17.B-RETIRED Retired entirely on 2026-05-22 — present in NEITHER repo post-split

These items existed in the pre-split `Journal` repo but are deleted entirely by Phase 5 cleanup and NOT migrated to the new `journal` repo. Reason (per Asif 2026-05-22): the journal app no longer needs the Anthropic API, so the Cloudflare deploy scaffold and the API proxy together become orphaned references.

**Cloudflare deploy scaffold**:
- `wrangler.toml` (Cloudflare Workers config)
- `site-worker.js` (Worker entry — assets-only static deploy)
- `infra/cloudflare/` (Cloudflare setup scripts/config)
- `docs/cloudflare/` (Cloudflare deployment docs)

**Anthropic API proxy**:
- `server/` (Node/Express proxy that bound to 127.0.0.1:3001 and forwarded browser requests to Anthropic)

**API/proxy-specific docs that no longer apply**:
- `docs/anthropic-api-setup.md`
- `docs/proxy-setup.md`

**External resource** (not in repo; Asif's manual cleanup):
- The `journal` and `journal-dev` Cloudflare Workers on Cloudflare itself — orphaned external state. Asif may delete via the Cloudflare dashboard when convenient; no runbook step is required.

### 17.C Podcast-factory-only (stays in current repo, renamed)

**Content** (post-Phase-9.5 layout — see §2A.6):
- `library/` (TOP-LEVEL — shipped catalog only, populated by `ship_to_library.py`)
  - `library/_meta/catalog.md` (auto-generated)
  - `library/archetypes/` (moved from `content/podcast/library/archetypes/`)
  - `library/books/<slug>/{index.md, cover.*, transcript/, podcasts/}`
  - `library/{articles,documents,interviews,lectures,letters}/`
- `_workspace/books/<slug>/` (root-level per-book workspace — orchestrator state, drafts, intermediate transcripts, raw PDF intake)
- `_workspace/{articles,documents,interviews,lectures,letters,_sandbox}/` (root-level category sub-workspaces for non-book in-progress content)
- `content/podcast/.skill/` (handbook + _learning substrate — unchanged)
- `content/podcast/_README.md` (unchanged)
- Pre-Phase-9.5 transient layout: `content/podcast/library/` (full subtree, ~18MB) — gets split across `library/` (shipped) and `_workspace/` (in-progress) in Phase 9.5

**Scripts**:
- `scripts/podcast/` (orchestrate_book, _authoring, build_episode_txt, extract_chapter, **ship_to_library** [authored in Phase 9.5 — promotes workspace → library], …)
- `scripts/git-hooks/`
- `scripts/install-git-hooks.sh`

**Skills + agents (podcast-specific)**:
- `skills-staging/podcast/`
- `.github/agents/podcast-operator.agent.md`
- `.github/agents/podcast-orchestrator.agent.md`
- `.github/agents/podcast-challenger.agent.md`
- `.github/agents/podcast-trainer.agent.md`
- `.github/agents/podcast-extract.agent.md`
- `infra/claude-agents/podcast-extract.md`
- `infra/claude-agents/podcast-challenger.md`

**Infrastructure (podcast-specific)**:
- `infra/azure/` (full subtree — Translator, Doc Intel, Speech, Key Vault provisioning)
- `infra/launchd/` (scheduled tasks for the orchestrator)

**Operator + planning infrastructure (cross-machine podcast coordination + per-book workspace post-Phase-9.5)**:
- `_workspace/` (full subtree — README, _archive, audit, chats, orchestrator-logs, plan, runbooks; **post-Phase-9.5 also contains `books/<slug>/` per-book workspace and `articles/`, `documents/`, `interviews/`, `lectures/`, `letters/`, `_sandbox/` category sub-workspaces**)
  - Note: this current runbook lives in `_workspace/runbooks/repo-split.md` and STAYS in podcast-factory after the split as historical reference
- `_workspace/chats/cowork-master-disciple-instructions.md` — book-specific Cowork prompt, stays podcast-only (the cowork-brief SKILL duplicates; book-specific prompts do not)

**Docs (podcast-specific)**:
- `docs/podcast/`, `docs/architecture/` (podcast pipeline diagrams), `docs/azure/`, `docs/multi-mac-runbook.md`, `docs/voice-refine-test-samples.md`
- (`docs/anthropic-api-setup.md` + `docs/proxy-setup.md` — RETIRED 2026-05-22 with the Cloudflare/server retirement, see §17.B-RETIRED)

**CI/CD**:
- `.github/workflows/` (release.yml, ci.yml, podcast-e2e.yml)

**Other**:
- `shared/tag-normalize.js` — purpose unclear; **DEFAULT to podcast-only unless Asif specifies otherwise**. If used by site code in `journal` too, duplicate during Phase 4.
- `Makefile` (post-cleanup) — podcast + Azure targets
- `package.json` — `"name": "podcast-factory"`
- `.gitignore` — keeps podcast-specific entries

**Branches (all stay in podcast-factory; no journal-side branches except develop/main extracted via filter-repo)**:
- `book/asaas-al-taveel`, `book/kitab-al-riyad`, `book/islr-mas-i`, `book/master-disciple-notebooklm-scaffolding`
- `feat/operator-review-studio`, `feat/podcast-w1-foundation`
- `dump`, `plan/v2-execute-readiness`, `plan/v2-gap-close`

**Worktrees (all 4 stay in podcast-factory)**.

---

## 18. Sign-off

This runbook does NOT execute. Asif reviews and authorizes phase-by-phase, or as a single "execute Phase 1 through 10" green-light. Execution gates: Air's Phase 10 merge complete AND Asif's explicit approval of this runbook.

Operator on execute: Studio Mac (this machine). Air's role is passive — she clones / re-syncs after the rename in Phase 8.

---

## 19. Tooling, automation, and who-does-what

### 19.1 Tooling status (verified on Studio 2026-05-22)

| Tool | Status | Version | Notes |
|---|---|---|---|
| `gh` (GitHub CLI) | ✅ Installed + authenticated | 2.92.0 | Logged in as `asifhussain60`; ADMIN on `Journal` repo; scopes: `gist`, `read:org`, `repo`, `workflow`. **`repo` scope is sufficient for `gh repo create` and `gh repo rename`.** Missing `delete_repo` scope — `gh repo delete` may prompt for re-auth. |
| `git-filter-repo` | ✅ Installed 2026-05-22 | 2.47.0 | Required for Phase 2. Path: `/Users/ahmac/homebrew/bin/git-filter-repo`. |
| `git` | ✅ Installed | system | Worktree commands all available. |
| `brew` | ✅ Installed | 5.1.12 | For installing `git-filter-repo`. |
| `az` (Azure CLI) | ✅ Installed | 2.86.0 | Not needed for the split — Azure resources untouched. |
| ~~`wrangler` (Cloudflare CLI)~~ | n/a | — | **Cloudflare retired 2026-05-22** — wrangler not needed. |
| `gh repo view` permission check | ✅ ADMIN on `asifhussain60/Journal` | — | Confirms Asif can rename, set visibility, create new repos under his namespace. |

### 19.2 Automation matrix — Claude (this session) vs Asif (manual)

| Phase | Step | Who | Method |
|---|---|---|---|
| 1.1 | Tag branches + push | Claude | Bash via this session |
| 1.2 | Mirror clone to `~/Backups/` | Claude | Bash |
| 1.3 | Tar snapshot | Claude | Bash |
| 1.4 | Secondary GitHub backup repo | Claude | `gh repo create` + `git push --mirror` |
| 1.5 | Backup verification | Claude | Bash |
| 1.6 | Create new `journal` repo | Claude | `gh repo create asifhussain60/journal` |
| 1.7 | (Deferred — no action) | — | — |
| 2 | `git filter-repo` extraction | Claude | Bash (after `git-filter-repo` installed) |
| 3 | Push to journal repo | Claude | Bash |
| 4 | Journal repo identity edits | Claude | Edit tool (CLAUDE.md, Makefile, package.json, etc.) |
| 5 | Podcast-factory cleanup commit | Claude | Bash + Edit tool |
| ~~6~~ | **DELETED 2026-05-22** (was: Cloudflare re-point) | — | — |
| 7.1 | `gh repo rename Journal → podcast-factory` | Claude (executes) + Asif (FRESH confirmation immediately before) | `gh repo rename`. Phase 7 green-light authorizes the phase; Step 7.1 specifically requires a separate "go" before the rename actually runs (see §10 warning + §19.4). |
| 7.2 | Redirect auto-creates (no action) | GitHub | Automatic |
| 7.3 | Studio remote URL update | Claude | Bash |
| 7.4 | Worktree directory reorganization | Claude | Bash (mv + `git worktree repair`) |
| 7.4g | VS Code window reopen | **Asif** | IDE-side |
| 8.1–8.5 | Air-side sync + worktree reorg | **Asif** (or Air's Claude session) | Bash on Air |
| 9 | Operator-file URL/path updates | Claude | Edit tool |
| 9.5.1–9.5.4 | Library hoist: workspace rename + top-level library scaffold + script-path sed | Claude | Bash + Edit tool |
| 9.5.5 | Author `scripts/podcast/ship_to_library.py` | Claude | Write tool |
| 9.5.6 | First promotion runs (per-book ship-verdict decisions) | Claude (executes) + Asif (per-book SHIP/NOT-SHIP go-ahead for each book ≥ SHIP-WITH-CAUTION) | `python3 scripts/podcast/ship_to_library.py --book <slug>` |
| 9.5.8 | Library-hoist commit + PR + merge | Claude | Bash |
| 10 | Verification | Claude (mostly) + Asif (visual checks) | Mixed |

**Bottom line**: Claude (this Studio session) can execute approximately **90% of the runbook automatically** given Asif's go-ahead at each phase boundary. The non-Claude steps are: VS Code window reopening (Phase 7.4g), Air-side commands (Phase 8 — driven by Air's own Claude session or Asif running them manually on Air), and per-book SHIP/NOT-SHIP go-aheads in Phase 9.5.6 (Asif's editorial decision for any book above SHIP-WITH-CAUTION threshold). Phase 6 (the prior Cloudflare manual step) is deleted entirely as of 2026-05-22.

### 19.3 Preparation tasks (before any execution)

These are NOT runbook execution — they're prerequisites that should be done before Phase 1.

- [ ] **Install `git-filter-repo`**: `brew install git-filter-repo` (~30 sec, one-time)
- [ ] **Confirm `gh` auth is still valid**: `gh auth status` returns logged-in
- [ ] **Confirm disk space for backups**: at least 2 GB free in `~/Backups/`
- [ ] **Wait for Air's KaR Phase 10 merge**: see Phase 0 pre-flight in §3
- [ ] **Commit + push this runbook to develop** so Air can read it before her Phase 8

### 19.4 Authorization model

Each phase boundary is an authorization checkpoint. Asif says "go Phase N" → Claude executes Phase N's steps in order, reports verification output, and waits. Within a phase, Claude does not pause unless a destructive operation needs explicit re-confirmation (force-push, delete operation, anything destructive on shared origin).

**Destructive operations that always require explicit re-approval mid-phase**:
- `git push --force` / `git push --force-with-lease` to develop or main
- `git push --mirror` to any remote (highest blast radius — rewrites all refs and deletes origin-only refs)
- `gh repo delete <anything>`
- `gh repo rename` (renames a repository — durable external state change visible to all collaborators)
- `git reset --hard` on a branch that has been pushed
- `rm -rf` of any directory under `~/Code/` (other than the quarantined `.BROKEN.<timestamp>` paths)
- Any command that deletes or overwrites a backup directory under `~/Backups/`

**Allowed within a phase after the phase's green-light** (no per-operation re-approval):
- Creating new git branches off develop / main
- Committing on feature branches
- Creating new GitHub repos via `gh repo create` (non-destructive — purely additive; creates new namespace state, no overwrite risk)
- Pushing the safety mirror to the optional secondary backup repo (Layer 4)
- Creating new annotated tags
- Mirror-cloning the local repo to `~/Backups/` (Layer 2)
- Filesystem `tar` snapshots into `~/Backups/` (Layer 3)
- Standard `git push` to non-protected branches
