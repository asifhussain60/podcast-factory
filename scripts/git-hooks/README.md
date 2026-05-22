# Git hooks

Repo-managed git hook source files. They live here so they're version-controlled
and travel with the repo; they get copied into `.git/hooks/` by the installer.

## Install

```bash
./scripts/install-git-hooks.sh
```

Run once after `git clone` on a new machine, or whenever hook sources change.
Idempotent — safe to re-run.

## Hooks

*No hooks currently installed.* The previous `pre-commit` theme-parity hook
was retired 2026-05-22 along with the rest of the journal-site stack (the
`server/` directory and the `skills-staging/css-theme-sync/` skill it
depended on were moved out during the repo split). Add new hooks here as
needed; the installer auto-discovers anything in this directory.
