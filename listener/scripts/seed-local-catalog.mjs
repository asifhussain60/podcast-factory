/**
 * Replay every published book's SQL into the LOCAL database.
 *
 * `publish_to_listener.py` writes one `.publish/<slug>.sql` file per book every
 * time it runs, tracked in git since 2026-08-17 for exactly this reason: which
 * books a machine's local database knows about used to depend entirely on which
 * publishes happened to run ON THAT MACHINE, with no way for a fresh clone to
 * catch up short of re-running the whole pipeline per book. The files are the
 * portable record; this script is what replays them.
 *
 * Safe to run repeatedly and in any order — each file DELETEs its own slug's
 * rows before re-INSERTing them (see publish_to_listener.build_statements), so
 * replaying a file that is already loaded is a no-op, not a duplicate.
 *
 * LOCAL ONLY, same as seed-people.mjs: every `wrangler d1 execute` below passes
 * `--local` and there is no `--remote` mode. Going live is `deploy_listener.sh`,
 * not this.
 *
 * Usage:
 *   node scripts/seed-local-catalog.mjs
 */
import { execFileSync } from "node:child_process";
import { readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const unknown = process.argv.slice(2);
if (unknown.length > 0) {
  console.error(
    `unknown option: ${unknown.join(" ")} (this script takes no flags)`,
  );
  process.exit(2);
}

const here = path.dirname(fileURLToPath(import.meta.url));
const publishDir = path.join(here, "..", ".publish");

let files;
try {
  files = readdirSync(publishDir)
    .filter((name) => name.endsWith(".sql"))
    .sort();
} catch {
  console.log(
    `No ${path.relative(process.cwd(), publishDir)}/ — nothing to seed.`,
  );
  process.exit(0);
}

if (files.length === 0) {
  console.log("No published-book SQL files found — nothing to seed.");
  process.exit(0);
}

let loaded = 0;
let failed = 0;
for (const file of files) {
  const slug = file.replace(/\.sql$/, "");
  try {
    execFileSync(
      "npx",
      [
        "wrangler",
        "d1",
        "execute",
        "podcast-listener",
        "--local",
        "--file",
        path.join(publishDir, file),
      ],
      { stdio: ["pipe", "pipe", "inherit"], encoding: "utf8" },
    );
    console.log(`  loaded ${slug}`);
    loaded += 1;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error(`  ! failed ${slug}: ${message}`);
    failed += 1;
  }
}

console.log(
  `\n${loaded} of ${files.length} books loaded into the local database.`,
);
if (failed > 0) process.exit(1);
