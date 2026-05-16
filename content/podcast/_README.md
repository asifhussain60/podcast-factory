# Podcast Workspace — README

This is the working directory for podcast episode bundles. Each bundle is a coordinated set of markdown files designed to be uploaded to **NotebookLM** so its Audio Overview feature produces a strong two-host conversation.

## What this folder is and isn't

**This folder IS**:
  - The source-of-truth for episode bundles
  - A registry of episodes (`_registry.md`)
  - The hand-off point between Claude (which builds the bundle) and NotebookLM (which generates the audio)

**This folder IS NOT**:
  - The audio output location (download MP3s to `_archive/audio/` if you want them stored)
  - A staging area for in-progress episodes (use `_workspace/EP##-[slug]/` for scratch)

## Folder layout

```
/PROJECTS/journal/content/podcast/
├── _README.md              this file
├── _registry.md            episode index (number, title, slug, status, NotebookLM URL, date)
├── _archive/               retired or superseded episodes
├── _workspace/             scratch distillation per episode (cleaned up after Phase 4)
└── episodes/
    └── EP##-[slug]/
        ├── 00-framing.md          uploaded as source + pasted into NotebookLM Customize
        ├── 01-source-primary.md   distilled main source
        ├── 02-key-passages.md     verbatim quotes
        ├── 03-context-pack.md     author, tradition, historical moment
        ├── 04-discussion-spine.md 6–12 thematic beats
        └── 99-show-notes.md       (optional) episode title, blurb, references
```

The skill definition itself lives at `/PROJECTS/journal/skills-staging/podcast/` (canonical, version-controlled). This folder is the content workspace only.

## NotebookLM upload workflow

For each episode bundle:

1. Open https://notebooklm.google.com → **New notebook**
2. Name it `EP##: [Episode Title]`
3. **Add sources** → upload these files in order:
   - `00-framing.md`
   - `01-source-primary.md`
   - `02-key-passages.md`
   - `03-context-pack.md`
   - `04-discussion-spine.md`
4. Click **Audio Overview** → **Customize**
5. Paste the contents of `00-framing.md` into the Customize prompt box
6. Click **Generate**
7. Wait ~3–5 minutes
8. Listen. If the result is strong: download the MP3 from the player menu, paste the NotebookLM notebook URL into `_registry.md`.
9. If the result is weak: re-read `04-discussion-spine.md` and `00-framing.md` — the bundle was the bottleneck, not NotebookLM.

## Episode lifecycle

  - **draft** — bundle being built
  - **ready** — bundle complete, awaiting NotebookLM upload
  - **generated** — Audio Overview generated, URL captured
  - **published** — MP3 downloaded and stored (if applicable)
  - **archived** — superseded or retired

Status is tracked in `_registry.md`.

## Working with Claude

Triggers for the `/podcast` skill:
  - "Build a podcast episode from [source]"
  - "New episode on [topic]"
  - "Refine the bundle for EP##"
  - Drop a PDF and say "make this a podcast"

Claude will:
  1. Ask intake questions (audience, angle, length, host dynamic)
  2. Distill the source(s) into scratch
  3. Build the 5-to-6-file bundle in the episode folder
  4. Update the registry
  5. Hand back an upload checklist

Claude does NOT:
  - Generate audio (NotebookLM does this)
  - Write a script (NotebookLM does this)
  - Upload to NotebookLM (manual)

## Installing the /podcast skill

The canonical skill source lives at `/PROJECTS/journal/skills-staging/podcast/`. To activate it in this Claude environment:

```bash
# macOS plugin skills directory (replace with actual plugin path on your system)
cp -R /Users/asifhussain/PROJECTS/journal/skills-staging/podcast \
      ~/Library/Application\ Support/Claude/<plugin-skills-path>/
```

Once installed, restart the Claude session. The skill will trigger on `/podcast`, `@podcast`, "new episode", "turn this into a podcast", etc.

## Workspace hygiene

  - All scratch files live under `_workspace/EP##-[slug]/` — never in the episode folder
  - Cleaned up after Phase 4 of the workflow
  - Per the user's workspace scratchpad rule: nothing in `/PROJECTS/journal/` root that isn't a deliverable
