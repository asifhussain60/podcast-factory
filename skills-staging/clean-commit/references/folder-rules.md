# Folder Structure Rules

Known folder layouts for Asif's projects. When auditing a folder, match it against these rules to determine what's in place and what's sprawl.

---

## Journal Repo ("What I Wish Babu Taught Me")

Canonical structure:

```
journal/
  .git/
  .gitignore
  chapters/               # Memoir chapter files (ch00-intro.txt, ch01-man.txt, etc.)
    snapshots/            # Point-in-time chapter snapshots
  reference/              # Living reference docs (incident-bank.md, quotes-library.txt, etc.)
  scratchpad/             # Working drafts (scratchpad-*.txt, scratch-*.txt)
  trips/                  # Trip folders, each self-contained
    {year}-{month}-{slug}/
      trip.yaml
      voice-guide.md
      memoir-extracts.md
      journal/
        day-{NN}.md
      photos/
        day-{NN}/
      dayone/
        day-{NN}-dayone.md
    {year}-{month}-daily/  # Non-trip daily logs (monthly rolling)
      trip.yaml
      journal/
        {YYYY-MM-DD}.md
      dayone/
  gpt/                    # GPT prompt archives (read-only reference)
```

### What belongs where

| File type | Belongs in | Notes |
|---|---|---|
| Chapter files (.txt) | `chapters/` | Named ch{NN}-{slug}.txt |
| Incident bank, quotes, voice analysis | `reference/` | Living docs, updated regularly |
| Working drafts | `scratchpad/` | Prefixed with scratch- or scratchpad- |
| Trip entries | `trips/{slug}/journal/` | Never in root or chapters |
| DayOne exports | `trips/{slug}/dayone/` | Never loose in trips/ |
| Trip metadata | `trips/{slug}/trip.yaml` | One per trip folder |
| Photos | `trips/{slug}/photos/` | Organized by day |
| GPT prompts | `gpt/` | Archive, rarely changed |

### What does NOT belong

| Pattern | Why it's sprawl |
|---|---|
| `.skill` files in root | Packaging artifacts — install to Cowork, don't leave in repo |
| `.html` files in `trips/` root | Dashboard or tool artifacts — either move inside a trip or delete |
| `_skill-install/`, `_dashboard*` | Tool scaffolding — one-time-use, should be removed after install |
| Loose `.md` or `.txt` in root | Everything has a home folder — nothing lives in the repo root except .gitignore |
| `*.lock` in `.git/` | Stale lock files from crashed git processes |
| `.DS_Store` anywhere | macOS metadata — should be gitignored |

### .gitignore should contain

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
  src/          # Source code
  tests/        # Test files
  docs/         # Documentation
  scripts/      # Build/deploy/utility scripts
  .github/      # CI/CD workflows
  .gitignore
  README.md
  package.json / requirements.txt / Cargo.toml  # Dependency manifest
```

### Common sprawl in code repos

| Pattern | Action |
|---|---|
| `node_modules/` committed | Remove, add to .gitignore |
| `dist/`, `build/`, `out/` committed | Remove, add to .gitignore |
| `.env`, `.env.local` committed | Remove, add to .gitignore, WARN about secrets |
| `*.log` files | Remove, add to .gitignore |
| IDE folders (`.idea/`, `.vscode/settings.json`) | Confirm with user — some teams track these |
