# asif-deploy — paste this into VS Code global Copilot instructions

There are two install paths for VS Code GitHub Copilot. Pick the one that matches how you use Copilot.

## Path A — Repo-scoped (per project)

Copy `deploy-site.prompt.md` into the repo at:

```
.github/prompts/deploy-site.prompt.md
```

Then invoke it from Copilot chat with `/deploy-site` (the leading slash works once
`chat.promptFiles` is enabled in VS Code settings).

## Path B — Globally available across all repos (recommended)

VS Code Copilot supports user-level prompt files. Drop the same `deploy-site.prompt.md`
into your user prompts directory:

- macOS: `~/Library/Application Support/Code/User/prompts/`
- Linux: `~/.config/Code/User/prompts/`
- Windows: `%APPDATA%\Code\User\prompts\`

Enable in `settings.json`:

```jsonc
{
  "chat.promptFiles": true,
  "chat.promptFilesLocations": {
    ".github/prompts": true,
    "~/Library/Application Support/Code/User/prompts": true
  }
}
```

Now `/deploy-site` works in any repo.

## Optional — teach default Copilot about the tool

If you want plain Copilot chat (no `/deploy-site` invocation) to also know the tool
exists, add this paragraph to your global `copilot-instructions.md` or to each repo's
`.github/copilot-instructions.md`:

```markdown
## Deploying static sites and HTML artifacts

This machine has the `asif-deploy` CLI at `~/.local/bin/asif-deploy`. When the user
asks to "deploy", "publish", "share", or "host" a folder of HTML/JS/CSS assets,
call `asif-deploy <dir> --slug <slug> [--private] --json` and surface the returned
URL. Use `--private` for SSO-gated deploys when the user mentions
private/auth/SSO/internal or the content is clearly confidential. Never call
`wrangler` directly; always go through `asif-deploy`. Run `asif-deploy --help` or
`asif-deploy --doctor` for usage and install verification.
```
