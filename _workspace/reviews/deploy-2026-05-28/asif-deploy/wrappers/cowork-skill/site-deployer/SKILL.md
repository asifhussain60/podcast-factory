---
name: site-deployer
description: Publish HTML pages, static sites, and rich SPAs to asif-studio on Cloudflare Pages and return a shareable URL. ALWAYS invoke when the user says 'deploy', 'publish', 'ship this', 'put this online', 'share this page', 'give me a link', 'host this', or asks to turn a generated HTML artifact into a viewable URL. Defaults to public; switches to SSO-gated when the user says 'private', 'auth', 'SSO', 'only for me', 'just for a few people', or shares anything that looks confidential (proposals, drafts, client work). Works from any folder. Wraps the global `asif-deploy` CLI installed at ~/.local/bin/asif-deploy.
---

# site-deployer — Cowork skill

You publish folders of web assets to `asif-studio` on Cloudflare Pages by calling the `asif-deploy` CLI. You return a shareable URL.

## Preflight

Before deploying, verify the CLI is installed:

```bash
command -v asif-deploy || echo "NOT_INSTALLED"
```

If not installed, tell the user:

> The `asif-deploy` CLI isn't on this machine yet. Run the one-time installer from the asif-deploy repo: `./install.sh`. After that you can deploy from anywhere.

Don't try to install it yourself — Asif keeps install discipline in his shell rc.

## Decide source directory

1. If the user pointed at a path, use it.
2. Otherwise look in cwd for, in order: `dist/`, `build/`, `out/`, `public/`, `site/`, then the cwd itself if it has `index.html`.
3. If no candidate, ask once: "Which folder should I deploy? (e.g., `./dist`)".

## Decide public vs private

Default = **public**. Switch to **private** (SSO-gated via Cloudflare Access) when:

- User says: private, auth, SSO, only for me, internal, gated, team only, share with a few people
- Content is clearly confidential: client proposals with pricing, pre-publish drafts, personal/memoir content, anything explicitly marked draft

When unsure, ask via AskUserQuestion (if available) with public as the recommended default.

## Decide slug

Default = basename of source dir. Override if basename is generic (`dist`, `build`, `out`, `public`, `site`, `tmp`). Then derive from:

1. The HTML `<title>` of `index.html` (kebab-cased), or
2. The parent repo/folder name.

The CLI normalizes the slug to `[a-z0-9-]{1,28}` automatically — don't preprocess.

## Dry-run when uncertain

For first deploys in a session, run:

```bash
asif-deploy <dir> --slug <slug> --dry-run --json
```

Parse the JSON, show the user the planned URL, then proceed. For repeat deploys of the same slug, skip the dry-run.

## Deploy

```bash
asif-deploy <dir> --slug <slug> [--private] --json -m "<one-line context>"
```

The `--json` output looks like:

```json
{"ok": true, "url": "https://<slug>.asif-studio.pages.dev", "project": "asif-studio", "slug": "<slug>", "gated": false}
```

Parse `url`, surface it to the user on its own line so it's easy to copy.

## Output format

```
✓ Deployed: https://<slug>.asif-studio.pages.dev
  Slug: <slug>  •  Mode: public (or "SSO-gated — only allowlisted users")
  Re-deploy with: asif-deploy <dir> --slug <slug>
```

For private deploys, append:

```
  ! First-time viewer? Add their email to the asif-studio-private Cloudflare Access policy.
```

## You DO NOT

- Build the site (no `npm run build` etc.) unless the user asks for it.
- Call `wrangler` directly — always go through `asif-deploy`.
- Create Cloudflare Pages projects or modify Access policies — surface as recommendations.
- Deploy `node_modules/`, `.git/`, `venv/` (refuse if pointed at one).
