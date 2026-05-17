# Podcast Workspace — README

This folder holds source-book workspaces for podcast-bound material. Each `<book-slug>/` is one source book. The `/podcast` skill turns its chapters into NotebookLM-ready bundles whose Audio Overview produces a focused two-host conversation.

The skill definition itself lives at `/PROJECTS/journal/skills-staging/podcast/SKILL.md` (canonical, version-controlled). This folder is the content workspace.

## Folder layout

```
/PROJECTS/journal/content/podcast/
├── _README.md                  this file
├── _handbook/                  book-agnostic skill refs + templates + cross-book registry
│   ├── registry.md             episode index across all books
│   ├── enrichment-sources.md   Tier 1–7 whitelist
│   ├── notebooklm-best-practices.md
│   ├── notebooklm-source-format.md
│   ├── two-host-framing.md
│   ├── source-distillation.md
│   ├── episode-architecture.md
│   ├── scratchpad-markers.md
│   └── workspace-readme-template.md
└── <book-slug>/                one source book (e.g. ayyuhal-walad/)
    ├── _README.md              book-specific conventions + upload checklist
    ├── _system/                book-specific authoring state (source, episode-drafts, scratchpad, pronunciation, editorial-notes, enrichment-log, challenger-report)
    ├── chapters/               source-book chapters as plain txt — uploaded to NotebookLM as SOURCE files
    └── episodes/               EP##-<slug>.txt — customize-prompt-only, pasted into NotebookLM's *Customize* box
```

## The two-file deliverable model (v3.4)

Per episode, two files reach NotebookLM in distinct roles:

| File | Role | NotebookLM action |
|---|---|---|
| `<book>/chapters/chNN-<slug>.txt` | The enriched chapter — the **SOURCE** | Uploaded directly as the single source for the notebook |
| `<book>/episodes/EP##-<slug>.txt` | The customize prompt only — the **CUSTOMIZE PROMPT** | Pasted into the *Customize* prompt box |

Strict 1:1 chapter ↔ episode mapping. Slug after the prefix is identical on both sides. The chapter IS the source — no transformation. Episode txts are emitted from `<book>/_system/episode-drafts/EP##-<slug>/00-framing.md` by `scripts/podcast/build_episode_txt.py`.

## NotebookLM upload workflow

For each episode:

1. Open https://notebooklm.google.com → **New notebook**
2. Name it `EP##: [Episode Title]`
3. **Add sources** → upload `<book>/chapters/chNN-<slug>.txt`
4. Click **Audio Overview** → **Customize**
5. Paste the contents of `<book>/episodes/EP##-<slug>.txt` into the Customize box
6. Click **Generate**, wait ~3–5 minutes
7. Listen. If strong: capture the notebook URL into `_handbook/registry.md`. If weak: re-read `00-framing.md` and the chapter — the bundle was the bottleneck, not NotebookLM.

## Working with Claude

The `/podcast` skill triggers on: "podcast", "/podcast", "@podcast", "new episode", "next episode", "turn this into a podcast", "NotebookLM episode", "audio overview", or dropping a PDF/book with "make this a podcast".

Claude will:
1. Ask intake questions (book, audience, angle, host dynamic)
2. Phase 0: extract → English refinement → Arabic phonetic pass → chapter design → enrichment (Tier 1–7 whitelist from `_handbook/enrichment-sources.md`)
3. Phase 3: author per-episode framing + scaffolds under `<book>/_system/episode-drafts/EP##-<slug>/`
4. Phase 4: run `podcast-challenger` to convergence, then build the episode txt via `scripts/podcast/build_episode_txt.py`
5. Hand back an upload checklist

Claude does NOT generate audio, write scripts, or upload to NotebookLM — those steps are NotebookLM + manual.

## Episode lifecycle

- **draft** — chapter or framing being authored
- **challenger-pending** — awaiting `podcast-challenger` convergence
- **ready** — `SHIP-READY` verdict; episode txt built; ready to upload
- **generated** — Audio Overview generated, URL captured in `_handbook/registry.md`
- **archived** — superseded or retired

Status is tracked in `_handbook/registry.md`.

## Hygiene

- Scratchpads live under `<book>/_system/scratchpad/` and per-episode at `<book>/_system/episode-drafts/EP##-<slug>/chapter.scratch.md` — never at this folder's root.
- Chapter files (`<book>/chapters/*.txt`) are upload-ready by construction: no HTML comments, no meta-prose. The build script's META_PROSE_TELLS gate hard-refuses any chapter that violates this.
- Authoring metadata for chapters lives in the sidecar `<book>/_system/enrichment-log.md`, not inline.
