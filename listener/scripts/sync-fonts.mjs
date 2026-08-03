// Copies the Listener's self-hosted faces into public/fonts/.
//
// Two sources, both one-time copies rather than runtime dependencies:
//   - node_modules/@fontsource-variable/*  (Literata, Fraunces, Inter)
//   - ../plan-dashboard/public/fonts/      (Scheherazade New, OpenDyslexic —
//     already licensed and subset in this repo; copied, never imported, so the
//     Listener has no runtime coupling to the admin site)
//
// The copied files are committed. Re-run only when adding or changing a face.
//
//   node scripts/sync-fonts.mjs [--check]
//
// --check verifies every target exists and is current without writing.

import { cpSync, existsSync, mkdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const LISTENER = resolve(HERE, "..");
const REPO = resolve(LISTENER, "..");
const OUT = join(LISTENER, "public", "fonts");

/** @type {{from: string, to: string, note: string}[]} */
const MANIFEST = [
  // Prose — Literata carries an optical-size axis, so raising the reader's
  // font size reproportions the letterforms instead of only scaling them.
  {
    from: "node_modules/@fontsource-variable/literata/files/literata-latin-opsz-normal.woff2",
    to: "literata-latin-opsz-normal.woff2",
    note: "Literata Variable (roman)",
  },
  {
    from: "node_modules/@fontsource-variable/literata/files/literata-latin-opsz-italic.woff2",
    to: "literata-latin-opsz-italic.woff2",
    note: "Literata Variable (italic)",
  },
  // Display — Fraunces, for headings only.
  //
  // The `opsz` cut rather than the plain weight one, and for the same reason
  // Literata carries it above: Fraunces' optical-size axis is dramatic, gaining
  // real stroke contrast as the size grows, which is exactly what makes it read
  // as a heading face rather than as body copy set large.
  {
    from: "node_modules/@fontsource-variable/fraunces/files/fraunces-latin-opsz-normal.woff2",
    to: "fraunces-latin-opsz-normal.woff2",
    note: "Fraunces Variable (display)",
  },
  {
    from: "node_modules/@fontsource-variable/fraunces/LICENSE",
    to: "fraunces-LICENSE.txt",
    note: "SIL OFL 1.1",
  },
  // UI — Inter, per Asif 2026-08-03.
  //
  // It replaces IBM Plex Sans as `--l-font-ui`, which is every label, pill,
  // button, count and list row on the site. Inter is drawn for exactly that: a
  // tall x-height and open apertures that hold up at the 11–13px the pills and
  // eyebrows are set at, where Plex's narrower forms were starting to close up.
  // The italic ships too — the reading column's `<em>` is Literata's, but a
  // `.pf-note` in the UI face has no italic of its own without it.
  {
    from: "node_modules/@fontsource-variable/inter/files/inter-latin-wght-normal.woff2",
    to: "inter-latin-wght-normal.woff2",
    note: "Inter Variable (roman)",
  },
  {
    from: "node_modules/@fontsource-variable/inter/files/inter-latin-wght-italic.woff2",
    to: "inter-latin-wght-italic.woff2",
    note: "Inter Variable (italic)",
  },
  {
    from: "node_modules/@fontsource-variable/inter/LICENSE",
    to: "inter-LICENSE.txt",
    note: "SIL OFL 1.1",
  },
  // Arabic — Scheherazade New is engineered for fully-vowelled text, which is
  // what this corpus carries.
  {
    from: "../plan-dashboard/public/fonts/scheherazade-new/scheherazade-new-arabic-400-normal.woff2",
    to: "scheherazade-new-arabic-400-normal.woff2",
    note: "Scheherazade New 400",
  },
  {
    from: "../plan-dashboard/public/fonts/scheherazade-new/scheherazade-new-arabic-600-normal.woff2",
    to: "scheherazade-new-arabic-600-normal.woff2",
    note: "Scheherazade New 600",
  },
  {
    from: "../plan-dashboard/public/fonts/scheherazade-new/LICENSE",
    to: "scheherazade-new-LICENSE.txt",
    note: "SIL OFL 1.1",
  },
  // Arabic DISPLAY — Amiri, and only ever for display.
  //
  // It is a revival of the Bulaq/Amiri naskh types: more stroke contrast and
  // far more presence than Scheherazade at the same size, which is what a book
  // title set at 2rem on a coloured band wants. It is NOT a replacement for
  // Scheherazade. The reading column carries fully-vowelled prose, Scheherazade
  // is engineered for exactly that, and swapping the running text for a face
  // with this much contrast is how vowel marks start colliding.
  //
  // 400 only. Nothing sets a bold Arabic title, and an unused face still
  // ships in the build — add the 700 here the day a rule asks for it.
  {
    from: "node_modules/@fontsource/amiri/files/amiri-arabic-400-normal.woff2",
    to: "amiri-arabic-400-normal.woff2",
    note: "Amiri 400 (display only)",
  },
  {
    from: "node_modules/@fontsource/amiri/LICENSE",
    to: "amiri-LICENSE.txt",
    note: "SIL OFL 1.1",
  },
  // Accessibility option in the reader's font picker.
  {
    from: "../plan-dashboard/public/fonts/opendyslexic/opendyslexic-latin-400-normal.woff2",
    to: "opendyslexic-latin-400-normal.woff2",
    note: "OpenDyslexic 400",
  },
  {
    from: "../plan-dashboard/public/fonts/opendyslexic/LICENSE",
    to: "opendyslexic-LICENSE.txt",
    note: "SIL OFL 1.1",
  },
];

const check = process.argv.includes("--check");
const problems = [];
let copied = 0;

mkdirSync(OUT, { recursive: true });

for (const entry of MANIFEST) {
  const src = entry.from.startsWith("..")
    ? resolve(REPO, entry.from.replace(/^\.\.\//, ""))
    : join(LISTENER, entry.from);
  const dest = join(OUT, entry.to);

  if (!existsSync(src)) {
    problems.push(
      `missing source for ${entry.note}\n    expected: ${src}\n    (run \`npm install\` first if this is a node_modules path)`,
    );
    continue;
  }

  if (check) {
    if (!existsSync(dest)) {
      problems.push(`${entry.to} has not been synced`);
    } else if (statSync(src).size !== statSync(dest).size) {
      problems.push(`${entry.to} differs from its source — re-run \`npm run fonts\``);
    }
    continue;
  }

  cpSync(src, dest);
  copied += 1;
  console.log(`  ${entry.to}  <-  ${entry.note}`);
}

if (problems.length > 0) {
  console.error(`\nsync-fonts: ${problems.length} problem(s)`);
  for (const p of problems) console.error(`  - ${p}`);
  process.exit(1);
}

console.log(check ? "sync-fonts: all faces present and current" : `sync-fonts: ${copied} file(s) written to public/fonts/`);
