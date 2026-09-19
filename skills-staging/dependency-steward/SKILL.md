---
name: dependency-steward
description: "Monthly, local, deliberate dependency upkeep for podcast-factory's three package sets (the Python pipeline, the Podcast Factory Astro Site in plan-dashboard/, and the Podcast Factory Library in listener/). Produces ONE grouped upgrade branch per ecosystem, gated by the real build/lint/test suites, with this repo's known lockfile and CI-minute traps written in. Use when the user says 'update dependencies', 'what is outdated', 'dependency audit', 'security audit', 'bump packages', '/dependency-steward', or when a security advisory names a package here. Chosen over Dependabot on purpose: every Dependabot PR starts a metered CI run on a private repo whose allowance already ran dry once (2026-08-13, four days of refused jobs). Never runs `npm audit fix --force`, never upgrades across a major version without saying so, never touches a live book's branch."
---

# dependency-steward

Dependency upkeep is boring until it isn't: an unpinned bump breaks a live run, a lockfile regenerated on a Mac breaks Linux CI, a "fix" installs a new major. This skill makes the boring job safe, on a schedule Asif controls, and costs **zero CI minutes until a branch is ready**.

## Ground rules

- **One ecosystem per branch, one group of related packages per commit.** `chore/deps-python-YYYY-MM`, `chore/deps-site-YYYY-MM`, `chore/deps-listener-YYYY-MM`. Never all three in one branch — a red gate must point at one thing.
- **Work in a worktree**, never in the primary checkout while a book run is live (`pgrep -fl orchestrate_book`).
- **Majors are proposals, not upgrades.** List them with the changelog link and stop; only minors and patches go in the branch unless Asif says otherwise.
- **Push once per ecosystem, when its gates are green** (private repo, metered minutes — see the batch-pushes rule in CLAUDE.md).
- **Nothing deploys.** The Library reaches production only after Asif's local sign-off.

## Step 1 — see what is behind (read-only, free)

```bash
.venv/bin/pip list --outdated                       # Python (requirements.txt is fully pinned)
cd plan-dashboard && npm outdated                   # Astro Site
cd listener && npm outdated                         # Library
cd plan-dashboard && npm audit --omit=dev; cd ../listener && npm audit --omit=dev   # advisories
```

Report a short table: package, current → wanted, is it a major, is it in `dependencies` or dev-only, and whether an advisory names it. **Advisories on production dependencies jump the queue.**

## Step 2 — upgrade one group

- **Python:** edit the pin in `requirements.txt` (every line is pinned on purpose), `pip install -r requirements.txt`, then the full suite. Watch the ones with real blast radius: `anthropic`, `google-genai` (model calls and cost accounting), `pydantic`.
- **Site / Library:** `npm install --no-audit --no-fund <pkg>@<version>` — **never `npm ci` and never a bare `npm install` on the whole tree without reading the lockfile diff.**

### The lockfile traps (both are documented in `.github/workflows/lint.yml`, and both have bitten)

1. **`npm ci` fails on this repo's lockfiles** (npm 11 on Node 24 reports `@emnapi/*` missing) — CI deliberately uses `npm install`. Do the same locally.
2. **A lockfile written on macOS structurally PRUNES the Linux-only optional packages** (rollup/esbuild/lightningcss platform binaries); an ubuntu runner then resolves fresh and the lock drifts. Do not commit a wholesale lockfile regeneration; commit the smallest diff that changes only the packages you meant to.
3. **`kysely` is required by better-auth and looks unused** — and `isbot` is redundant but harmless. An "unused dependency" tool will tell you to remove them; do not, without reading the importers of the packages that depend on them.

## Step 3 — the gates (all must pass, with output pasted, before pushing)

| Ecosystem | Run |
|---|---|
| Python | `make lint` · `.venv/bin/python -m pytest -q -p no:cacheprovider` · `python3 scripts/repo_surgeon_probe.py` |
| Astro Site | `cd plan-dashboard && npm run check && npm test && npm run lint:views && npm run ratchets && npm run smoke` |
| Library | `cd listener && npm run cf-typegen && npm run typecheck && npm run lint && npm test` (write the CI placeholder `.dev.vars` first — see `lint.yml`) |

A major bump of Astro, React Router, Vite, Playwright or `@react-router/dev` additionally needs a manual look at the rendered site (`site-health-sentinel`) — the test suites do not see layout.

**Playwright is special:** its browser build must match its version (`chromium-<build>`). After bumping it, run `npx playwright install chromium` in `plan-dashboard/`; a mismatch is diagnosed by `scripts/podcast/_playwright_diag.py` and must never be "fixed" with a symlink.

## Step 4 — hand back

Report: what moved (count and the notable ones), what was skipped and why (majors with links), what advisories remain, gate output, and the exact branch to review. Do not merge.

## What this skill does not do

Deploy anything, rotate a credential, change `requirements.txt` pins without running the suite, or touch `content/`.
