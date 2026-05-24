# Folder Structure Rules

Known folder layouts for Asif's projects. When auditing a folder, match it against these rules to determine what's in place and what's sprawl.

---

## Journal Repo ("What I Wish Babu Taught Me")

Canonical structure (v3.5+, post-podcast-restructure):

```
journal/
.git/
.gitignore
 framework.md # Cross-skill governance contract
 content/
 _shared/arabic/ # Cross-skill Arabic phonetic reference (only sanctioned cross-skill data)
 babu-memoir/ # The memoir
 chapters/ # ch00-intro.txt, ch01-man.txt, etc.
 _system/ # Voice fingerprint, master context, quotes library,
 # clinic library, scratchpad, snapshots, workflow,
 # scratchpad-markers, etc.
 podcast/ # Podcast workspace
 _README.md
 library/ # Source materials by category
 books/<book-slug>/ # Multi-chapter long-form works
 _system/ # Source PDF, episode-drafts, scratchpad,
 # pronunciation, editorial-notes, enrichment-log,
 # challenger-report
 chapters/ # chNN-<slug>.txt (NotebookLM SOURCE files)
 episodes/ # EP##-<slug>.txt (Customize prompt files)
 transcripts/ # Transcripts after audio renders
 chapter-contracts/ # Per-chapter Extract Mode contracts
 articles/ # Single essays / journal pieces
 documents/ # Reports, white papers
 lectures/ # Recorded talks, sermons
 interviews/ # Q&A transcripts
 letters/ # Epistolary works
.skill/ # Podcast-skill internals (hidden by leading dot)
 registry.md # Cross-book episode index
 handbook/ # Book-agnostic refs + templates
 archive/ # Superseded book snapshots
 scripts/
 memoir/ # auto_delta, save_snapshot, refresh_all_snapshots, etc.
 podcast/ # build_episode_txt, extract_chapter, audit_transcript
 site/ # sync_chapters
 skills-staging/ # Skill source-of-truth (canonical SKILL.md files)
 reference/ # Skill-registry, challenger framework, bootstrap, overlays
.github/agents/ # Agent definitions
 site/ # Babu App static site
 docs/ # Architecture HTMLs
```

### What belongs where

| File type | Belongs in | Notes |
|---|---|---|
| Memoir chapter files (.txt) | `content/babu-memoir/chapters/` | Named ch{NN}-{slug}.txt |
| Memoir workflow + reference | `content/babu-memoir/_system/` | journal-workflow-v2.md, voice-fingerprint.md, quotes-library.txt, etc. |
| Podcast book chapters (in flight) | `content/drafts/<slug>/chapters/` | Named ch{NN}-{slug}.txt; uploaded to NotebookLM as SOURCE |
| Podcast book chapters (shipped) | `content/published/books/<slug>/chapters/` | Hoisted from `_workspace/` on ship (Phase 9.5) |
| Podcast episode prompts | `content/drafts/<slug>/episodes/` or `content/published/books/<slug>/episodes/` | Built from 00-framing.md by build_episode_txt.py |
| Slide-deck deliverables | `content/drafts/<slug>/slide-decks/` | chNN-deck-<slug>.txt + chNN-framing-<slug>.md pairs (slide-deck enhancement 2026-05-23) |
| Per-chapter Extract contracts | `content/drafts/<slug>/chapter-contracts/` | YAML schema in `content/podcast/.skill/handbook/chapter-contract.template.yml` |
| Skill handbook refs (podcast) | `content/podcast/.skill/handbook/` | Book-agnostic; book-bound = `content/drafts/<slug>/_system/` |
| Per-book registry | `content/drafts/<slug>/_system/registry.md` | Validated by `scripts/podcast/validate_registry.py` |
| Top-level book index | `content/podcast/.skill/books.md` | One row per book pointing at its per-book registry (no cross-book monotonic index per the 2026-05-17 workspace restructure) |
| Skill source-of-truth | `skills-staging/<skill>/SKILL.md` | Tracked in git; install copies go to Claude Code per-machine |
| Agent definitions | `.github/agents/<name>.agent.md` | Plus a thin wrapper at `.claude/agents/<name>.md` for per-machine load |
| Cross-skill governance | `framework.md`, `reference/skill-registry.md` | Authoritative; every cross-skill operation reads these |

### What does NOT belong

| Pattern | Why it's sprawl |
|---|---|
| `.skill` files in root | Packaging artifacts — install to Claude Code, don't leave in repo |
| Loose `.md` / `.txt` in root | Everything has a home folder; root carries only CHANGELOG.md, README.md (if any), framework.md, package.json, wrangler.toml |
| `chapters/`, `reference/`, `scratchpad/`, `trips/` at root | All relocated under `content/` (memoir) or removed (trips) in v3.0–v3.2 |
| Files under `content/podcast/<book>/` (no `library/<category>/` prefix) | Legacy podcast layout — current canonical is `library/<category>/<book>/` |
| `_handbook/` anywhere | Renamed to `.skill/handbook/` in v3.5 |
| `from-memoir/` under podcast | Severed in v3.5 — memoir is not a podcast source |
| `*.lock` in `.git/` | Stale lock files from crashed git processes |
| `.DS_Store` anywhere | macOS metadata — should be gitignored |

###.gitignore should contain

```
.DS_Store
Thumbs.db
*.swp
*.swo
*~
*.skill
```

---

## Generic Code Repo

For repos without documented structure, apply these conventions:

```
repo/
 src/ # Source code
 tests/ # Test files
 docs/ # Documentation
 scripts/ # Build/deploy/utility scripts
.github/ # CI/CD workflows
.gitignore
 README.md
 package.json / requirements.txt / Cargo.toml # Dependency manifest
```

### Common sprawl in code repos

| Pattern | Action |
|---|---|
| `node_modules/` committed | Remove, add to.gitignore |
| `dist/`, `build/`, `out/` committed | Remove, add to.gitignore |
| `.env`, `.env.local` committed | Remove, add to.gitignore, WARN about secrets |
| `*.log` files | Remove, add to.gitignore |
| IDE folders (`.idea/`, `.vscode/settings.json`) | Confirm with user — some teams track these |
