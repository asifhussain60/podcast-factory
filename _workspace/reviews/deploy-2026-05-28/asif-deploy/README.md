# asif-deploy

One command to publish any folder of HTML / JS / CSS to **asif-studio** on Cloudflare Pages — public or SSO-gated — callable from any repo, any terminal, and from Claude Code, Claude Cowork, or VS Code GitHub Copilot.

```
asif-deploy ./my-site                            # public  → https://my-site.asif-studio.pages.dev
asif-deploy ./client-doc --private               # gated   → https://client-doc.asif-studio-private.pages.dev
asif-deploy ./demo --slug q4-pitch --json -m v3  # explicit slug + JSON for AI
asif-deploy --doctor                             # verify install + auth
asif-deploy --list                               # recent deploys
```

## Install on a new machine

```bash
git clone <this-repo-url> ~/Code/asif-deploy
cd ~/Code/asif-deploy
./infra/setup.sh
```

That's the whole install. `infra/setup.sh` is the fire-and-forget installer — idempotent, ~5 minutes the first time, zero changes on re-runs. It handles wrangler install, Cloudflare login, API token, Pages project creation, Cloudflare Access SSO setup, smoke tests, and AI surface wrapper install.

For a full breakdown of what the script does (and manual fallbacks if any phase fails) see [infra/README.md](infra/README.md).

## Architecture — one brain, three faces

Each AI surface uses a different plugin format, so there's no single "global agent" that works in all of them. Instead, the deploy logic lives in **one CLI**, and each surface gets a thin wrapper (~30 lines) that tells its AI how to call the CLI.

```
              ┌────────────────────────────────────────────┐
              │   ~/.local/bin/asif-deploy  (the brain)    │
              │   • slug normalization                     │
              │   • wraps `wrangler pages deploy`          │
              │   • public / private project routing       │
              │   • JSON output for AI consumption         │
              └────────────────┬───────────────────────────┘
                               │ called via Bash by:
        ┌──────────────────────┼───────────────────────────┐
        │                      │                           │
┌───────▼─────────┐  ┌─────────▼──────────┐  ┌─────────────▼────────────┐
│ Claude Code     │  │ Claude Cowork      │  │ VS Code Copilot          │
│ ~/.claude/      │  │ Skills directory   │  │ ~/.../User/prompts/      │
│   agents/       │  │   site-deployer/   │  │   deploy-site.prompt.md  │
│   site-         │  │   SKILL.md         │  │                          │
│   deployer.md   │  │ (.skill bundle)    │  │                          │
└─────────────────┘  └────────────────────┘  └──────────────────────────┘
```

Why this beats "one global agent":

- One bug fix lands everywhere — no drift across three surface-specific copies.
- Also callable from terminal, shell scripts, CI, cron — not just AI surfaces.
- New AI surfaces in the future = write one more 30-line wrapper, no logic duplication.
- SSO config lives in one place (Cloudflare dashboard), not three.

## Hosting target — Cloudflare Pages

Free for our volume (500 deploys/month, unlimited bandwidth, 100 custom domains), branch-named preview URLs out of the box, Cloudflare Access for SSO (free for up to 50 users), global CDN. Two Pages projects:

| Project | URL pattern | Purpose |
|---|---|---|
| `asif-studio` | `https://<slug>.asif-studio.pages.dev` | Public deploys |
| `asif-studio-private` | `https://<slug>.asif-studio-private.pages.dev` | SSO-gated — gated by Cloudflare Access |

Custom domains (`studio.yourdomain.com`) are optional and free if your domain is on Cloudflare DNS. See [infra/README.md §Custom domain](infra/README.md) for setup.

## Repo layout

```
asif-deploy/
├── README.md                 you are here
├── bin/
│   └── asif-deploy           the CLI (Python, no deps beyond stdlib)
├── infra/
│   ├── README.md             comprehensive setup + manual fallback per phase
│   └── setup.sh              fire-and-forget installer (run this)
├── wrappers/
│   ├── claude-code/
│   │   └── site-deployer.md             Claude Code subagent
│   ├── cowork-skill/
│   │   ├── site-deployer/
│   │   │   └── SKILL.md                 Cowork skill source
│   │   └── site-deployer.skill          installable .skill bundle
│   └── copilot/
│       ├── deploy-site.prompt.md        VS Code Copilot prompt
│       └── copilot-instructions-snippet.md  optional global Copilot context
└── examples/
    └── asif-studio-landing/  landing page deployed to https://asif-studio.pages.dev
        └── index.html
```

## Cost

| | Free tier | Where you'd pay |
|---|---|---|
| Cloudflare Pages | 500 deploys/month, unlimited bandwidth, 100 custom domains | $20/mo above 500 deploys |
| Cloudflare Access | 50 users | $7/user/mo above 50 |
| DNS / SSL | unlimited | n/a |

**$0/month for normal use.**

## Updating

```bash
cd ~/Code/asif-deploy
git pull
./infra/setup.sh    # idempotent re-run picks up any new phases
```

## Uninstalling

```bash
rm ~/.local/bin/asif-deploy
rm ~/.claude/agents/site-deployer.md
rm "$HOME/Library/Application Support/Code/User/prompts/deploy-site.prompt.md"
# Cowork: uninstall the site-deployer skill from Cowork settings
# Keychain: security delete-generic-password -s cloudflare_asif_deploy_api_token -a "$USER"
```

Leaving the Cloudflare Pages projects in place keeps deployed sites alive even after uninstalling the CLI.

## Sibling repos

asif-deploy is independent of [podcast-factory](https://github.com/asifhussain60/podcast-factory) and [journal](https://github.com/asifhussain60/journal). It can be cloned and installed standalone on any machine.
