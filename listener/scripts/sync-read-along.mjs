// Which paragraph is being spoken is ONE rule, and this copies it.
//
// Source of truth: plan-dashboard/src/lib/reader/read-along.ts. Two surfaces ask
// the question — the Podcast Factory Library, where a reader follows a recording
// through a published chapter, and the Book Composer, where Asif follows it
// through the chapter he is editing. Two implementations would be free to
// disagree about the same second of the same audio, and the disagreement shows
// as the wrong sentence lit up in one of them: the precise failure the timing
// gate exists to prevent.
//
// Copied at author time rather than imported at build or run time, exactly like
// sync-quote-inks.mjs and sync-fonts.mjs and for the same reason: this app has no
// coupling to the admin site, and a module reaching across the repo boundary
// would be the first. The generated file is committed; test/read-along.test.ts
// runs this in --check mode, and the repo's pre-commit hook runs that test, so a
// rule changed on one side and not the other cannot be committed.
//
//   node scripts/sync-read-along.mjs [--check]
//
// --check writes nothing and exits non-zero when the copy is out of date.
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const SOURCE = resolve(
  HERE,
  "../../plan-dashboard/src/lib/reader/read-along.ts",
);
const TARGET = join(HERE, "../app/lib/read-along.ts");

const BANNER = `// GENERATED — do not edit.
//
// Copied from plan-dashboard/src/lib/reader/read-along.ts by
// listener/scripts/sync-read-along.mjs. Change the rule THERE, then run
// \`npm run read-along\`. test/read-along.test.ts fails when this drifts.
`;

/** @param {string} source */
function generate(source) {
  return BANNER + "\n" + source.trimStart();
}

const check = process.argv.includes("--check");

if (!existsSync(SOURCE)) {
  // The admin site is a sibling checkout, not a dependency: a repo without it is
  // not a drift, and failing here would make this app unbuildable on its own.
  console.log(
    "sync-read-along: no admin site alongside this one — nothing to check",
  );
  process.exit(0);
}

const wanted = generate(readFileSync(SOURCE, "utf8"));
const current = existsSync(TARGET) ? readFileSync(TARGET, "utf8") : "";

if (check) {
  if (current !== wanted) {
    console.error(
      "sync-read-along: app/lib/read-along.ts is out of date with " +
        "plan-dashboard/src/lib/reader/read-along.ts — run `npm run read-along`",
    );
    process.exit(1);
  }
  console.log("sync-read-along: up to date");
  process.exit(0);
}

writeFileSync(TARGET, wanted);
console.log(`sync-read-along: wrote ${TARGET.replace(/.*\/listener\//, "")}`);
