---
mode: agent
description: Publish a static site, HTML page, or SPA to asif-studio on Cloudflare Pages and return a shareable URL. Use when the user says deploy / publish / ship / share this page / host this / give me a link.
tools: ['runCommands', 'codebase']
---

# Deploy site to asif-studio

You publish a folder of HTML/JS/CSS assets to Cloudflare Pages via the `asif-deploy` CLI. You return a shareable URL.

## Inputs to determine

1. **Source directory** — explicit from user, or first match in cwd of: `dist/`, `build/`, `out/`, `public/`, `site/`, else cwd if it has `index.html`. Ask if none found.
2. **Mode** — `--public` (default, anyone with URL) or `--private` (SSO-gated via Cloudflare Access). Use `--private` when the user says private/auth/SSO/internal/team-only/only-for-me or when the content is clearly confidential (proposals with pricing, drafts, client work pre-approval).
3. **Slug** — default = basename of source. Override if basename is generic (`dist`, `build`, `out`, `public`, `site`). Derive from `<title>` of index.html or repo name. CLI normalizes to `[a-z0-9-]{1,28}`.

## Preflight

```bash
command -v asif-deploy || echo "Install asif-deploy first: see https://github.com/asifhussain60/asif-deploy"
```

## Run

```bash
asif-deploy <dir> --slug <slug> [--private] --json -m "<one-line context>"
```

Parse the JSON `url` field and surface on its own line:

```
✓ Deployed: https://<slug>.asif-studio.pages.dev
  Slug: <slug>  •  Mode: public | SSO-gated
  Re-deploy: asif-deploy <dir> --slug <slug>
```

For `--private`, add: `! First-time viewer? Add their email to the asif-studio-private Cloudflare Access policy.`

## Do NOT

- Build the site (no `npm run build` etc.) unless asked.
- Call `wrangler` directly. Always go through `asif-deploy`.
- Create Cloudflare projects or modify Access — surface as a recommendation.
- Deploy `node_modules/`, `.git/`, `venv/`.

#fetch https://github.com/asifhussain60/asif-deploy/blob/main/README.md
