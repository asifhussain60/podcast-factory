// astro-config-fs-deny.test.mjs — the dev server may not serve secrets files.
//
// `server.fs.allow` opens the whole repo (and its parent) to Vite's `/@fs/`
// handler so content/ and the workspace packages resolve. Vite's default deny
// list covers .env and .env.* but not Wrangler's `.dev.vars`, so on 2026-09-03
// `GET /@fs/<repo>/listener/.dev.vars` answered 200 with the Podcast Factory
// Library's local secrets. Same-origin only, but a secret served by a dev server
// is still a secret served. The deny list below is the fix; this test keeps it.

import { test } from "node:test";
import assert from "node:assert/strict";

const { default: config } = await import("../astro.config.mjs");

const REQUIRED_DENY = ["**/.dev.vars", "**/.dev.vars.*", "**/.wrangler/**"];

test("server.fs.deny names Wrangler's secrets file and state directory", () => {
  const deny = config.vite?.server?.fs?.deny ?? [];
  for (const glob of REQUIRED_DENY) {
    assert.ok(
      deny.includes(glob),
      `astro.config.mjs vite.server.fs.deny is missing ${glob} (have: ${JSON.stringify(deny)})`,
    );
  }
});

test("the repo-wide allow that made this necessary is still declared", () => {
  // If allow shrinks to the site dir this test can go; until then, deny must
  // sit beside it.
  const allow = config.vite?.server?.fs?.allow ?? [];
  assert.ok(allow.includes(".."), JSON.stringify(allow));
});
