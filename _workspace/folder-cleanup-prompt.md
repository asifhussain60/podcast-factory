# Repo Folder-Structure Cleanup — Claude Code Brief

## Context

Repo: `journal/` (you are running inside it via the VS Code Claude Code extension; use repo-relative paths). Branch is `develop`, currently ahead of `origin/develop` by ~8 commits. Recent work is structural — preserve all content, this is paths-only.

Operate under CORTEX governance. Use CORTEX intelligence augmented by your Claude Code AI capabilities. Executive summary at the end; no code-detail spam during execution.

The recommendations below come from a holistic folder-structure review. Each is independent and atomic. Execute steps 1-4 unconditionally; ask before step 5.

## Goal

1. Delete `_workspace/whisper-pivot/` (obsolete tombstone from a reverted experiment).
2. Rename `skills-staging/` → `skills/` (these skills are in active use; "staging" is misleading).
3. Rename `content/podcast/babu-memoir/` → `content/podcast/from-memoir/` (resolve name collision with the memoir authoring tree at `content/babu-memoir/`).
4. Fold `reference/` into `skills/` (its 7 files are all about skills; eliminates a top-level dir).
5. (Optional, confirm first) Flatten `.github/agents/_contracts/operating-contract.md` → `.github/agents/operating-contract.md` if no future contract files are anticipated.

## Non-goals (do NOT touch these)

- File contents beyond path-reference updates.
- Subgrouping `content/podcast/_handbook/`, `content/<series>/_system/`, or `docs/architecture/`. They are intentionally flat.
- `.github/agents/` location (locked by Claude convention).
- Root-level files (`framework.md`, `CHANGELOG.md`, `package.json`, `wrangler.toml`, `site-worker.js`).
- Anything under `content/babu-memoir/chapters/` — memoir voice-sensitive, no mechanical edits.
- Anything in `_workspace/` other than the `whisper-pivot/` deletion.

## Step-by-step protocol

### Step 0 — Pre-flight
- Confirm `git status` is clean. If dirty, halt and ask.
- Confirm branch is `develop`.
- Confirm `_workspace/whisper-pivot/` exists (sanity check on starting state).

### Step 1 — Delete `_workspace/whisper-pivot/`
- `rm -rf _workspace/whisper-pivot`
- No reference sweep needed.
- Commit immediately as a standalone tombstone removal.

### Step 2 — Rename `skills-staging/` → `skills/`
- `git mv skills-staging skills` (preserves history).
- Sweep references across:
  - All `.md` files (especially every `skills/*/SKILL.md`, every `.github/agents/*.agent.md`, `framework.md`)
  - All `.html` files under `docs/architecture/`
  - All `.py` files under `scripts/`
  - All `.js` files under `server/` and `shared/`
- Replace `skills-staging/` → `skills/` (literal substring).
- Verify: `git grep -n "skills-staging" -- ':!CHANGELOG.md'` returns nothing significant. CHANGELOG entries documenting prior history stay as-is.
- Commit as a refactor.

### Step 3 — Rename `content/podcast/babu-memoir/` → `content/podcast/from-memoir/`
- `git mv content/podcast/babu-memoir content/podcast/from-memoir`
- Sweep references in:
  - `skills/podcast/SKILL.md`
  - `.github/agents/podcast-extract.agent.md`
  - `.github/agents/podcast-challenger.agent.md`
  - `scripts/podcast/extract_chapter.py` (carefully — check PROHIBITED_PATH_PREFIXES and the sanctioned-crossing logic; the literal path strings need updating)
  - `scripts/podcast/build_episode_txt.py` (any path refs)
  - `content/podcast/_handbook/extract-capability.md`
  - `framework.md`
  - `docs/architecture/cross-skill-boundaries.html` and any other architecture HTML mentioning the extract bundle
- Verify: `git grep -n "podcast/babu-memoir" -- ':!CHANGELOG.md'` returns nothing.
- Commit as a refactor.

### Step 4 — Fold `reference/` into `skills/`
Move files (each via `git mv` to preserve history):
- `reference/skill-registry.md` → `skills/REGISTRY.md`
- `reference/skill-bootstrap.md` → `skills/_framework/bootstrap.md`
- `reference/cortex-challenger-framework.md` → `skills/_framework/cortex-challenger.md`
- `reference/skill-overlays/` → `skills/_overlays/`

Then sweep these reference patterns across all `.md`/`.html`/`.py`/`.js`:
- `reference/skill-registry.md` → `skills/REGISTRY.md`
- `reference/skill-bootstrap.md` → `skills/_framework/bootstrap.md`
- `reference/cortex-challenger-framework.md` → `skills/_framework/cortex-challenger.md`
- `reference/skill-overlays/` → `skills/_overlays/`
- Any standalone `reference/` directory references (verify these are correct before changing — the word "reference" is also used as English; only match path-shaped occurrences with a trailing `/` or filename)

Likely heavy-touch files:
- `.github/agents/CORTEX.agent.md`
- `.github/agents/_contracts/operating-contract.md`
- Every `skills/*/SKILL.md`
- `framework.md`

After sweep: `rmdir reference/` (must be empty).

Verify: `git grep -n "^reference/\|[^a-zA-Z]reference/" -- ':!CHANGELOG.md' ':!**/*.txt'` shows no stale path refs.

Commit as a refactor.

### Step 5 — (Optional, ask first) Flatten `_contracts/`
If Asif confirms:
- `git mv .github/agents/_contracts/operating-contract.md .github/agents/operating-contract.md`
- `rmdir .github/agents/_contracts`
- Sweep `.github/agents/_contracts/operating-contract.md` → `.github/agents/operating-contract.md`.
- Commit.

### Step 6 — Verification pass
- `git status` clean.
- `git log --oneline` shows the new commits in order.
- Python syntax: `python3 -c "import ast; ast.parse(open('scripts/podcast/extract_chapter.py').read())"`.
- Node syntax (if touched): `node --check server/src/index.js`.
- No stale paths: run the three `git grep` commands from steps 2-4.
- Confirm no chapter file under `content/babu-memoir/chapters/` was modified.

### Step 7 — Executive summary
Report back with:
- 4 (or 5) commit hashes + one-line subjects
- Files-changed count per commit
- Any references the sweep flagged as ambiguous (where you used judgment)
- Any stale references still in CHANGELOG.md (intentionally preserved as history)
- Confirmation that no chapter file was touched
- Anything that required halting/asking

Do NOT push. Asif will review and push.

## Commit message format (each commit)

```
<type>(<scope>): <one-line summary>

<body explaining why, 1-3 sentences>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

Use Conventional Commits prefixes:
- Step 1: `chore(repo)`
- Step 2: `refactor(skills)`
- Step 3: `refactor(podcast)`
- Step 4: `refactor(skills)` (folding reference/)
- Step 5: `chore(agents)`

## Halt-and-ask conditions

Stop and ask Asif if:
- `git status` is not clean at start.
- A reference sweep produces >100 file modifications in a single step (likely over-matching).
- A `git mv` fails.
- Any matched reference would touch a memoir chapter file under `content/babu-memoir/chapters/`.
- The word "reference" appears in a way that's ambiguous (English vs path) and you cannot disambiguate from context.

## Rules during execution

- File-first model: edit files; let `git diff` show the changes. Never dump file contents in chat.
- Inside code blocks (markdown) documenting historical state, leave the literal text alone.
- CHANGELOG.md historical entries stay verbatim — they document past state.
- When in doubt, ask before sweeping.
