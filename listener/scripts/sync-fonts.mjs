// Copies the Listener's self-hosted faces into public/fonts/.
//
// Two sources, both one-time copies rather than runtime dependencies:
//   - node_modules/@fontsource-variable/*  (Literata, Fraunces, Inter)
//   - ../plan-dashboard/public/fonts/      (Cinzel, Scheherazade New,
//     OpenDyslexic — already licensed and subset in this repo; copied, never
//     imported, so the Listener has no runtime coupling to the admin site)
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
  // Book titles on the library card, and nowhere else. Asif asked for Roboto
  // Condensed there specifically: the grid sets a title at two lines in a narrow
  // column, and a condensed face fits a long one without shrinking it.
  //
  // COPIED like every other face rather than linked from fonts.googleapis.com.
  // A Google Fonts <link> is a third-party request on every page load of a
  // private library — it tells another origin who is reading and when — and it
  // is one more thing between a reader and the page rendering.
  {
    from: "node_modules/@fontsource-variable/roboto-condensed/files/roboto-condensed-latin-wght-normal.woff2",
    to: "roboto-condensed-latin-wght-normal.woff2",
    note: "Roboto Condensed Variable (library card titles)",
  },
  {
    from: "node_modules/@fontsource-variable/roboto-condensed/LICENSE",
    to: "roboto-condensed-LICENSE.txt",
    note: "Apache 2.0",
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
  // Chapter headings authored in the Book Composer. The admin site maps the
  // chapter-local Heading 1/2 controls to markdown h3/h4, and sets both in
  // Cinzel; publishing should preserve that hierarchy rather than translating
  // it into the Library's page-title face.
  {
    from: "../plan-dashboard/public/fonts/cinzel/cinzel-latin-600-normal.woff2",
    to: "cinzel-latin-600-normal.woff2",
    note: "Cinzel 600 (chapter headings)",
  },
  {
    from: "../plan-dashboard/public/fonts/cinzel/cinzel-latin-700-normal.woff2",
    to: "cinzel-latin-700-normal.woff2",
    note: "Cinzel 700 (chapter headings)",
  },
  {
    from: "../plan-dashboard/public/fonts/cinzel/LICENSE",
    to: "cinzel-LICENSE.txt",
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
  {
    from: "../plan-dashboard/public/fonts/traditional-arabic/TraditionalArabic-Regular.ttf",
    to: "TraditionalArabic-Regular.ttf",
    note: "Traditional Arabic Regular",
  },
  {
    from: "../plan-dashboard/public/fonts/traditional-arabic/SOURCE.txt",
    to: "TraditionalArabic-SOURCE.txt",
    note: "Traditional Arabic source note",
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
  // Urdu DISPLAY — Arabic and Urdu share codepoints, so the published language
  // tag, rather than glyph fallback, must select the Nastaliq face.
  {
    from: "../plan-dashboard/public/fonts/noto-nastaliq-urdu/NotoNastaliqUrdu-Regular.woff2",
    to: "noto-nastaliq-urdu-400-normal.woff2",
    note: "Noto Nastaliq Urdu 400 (Urdu titles)",
  },
  {
    from: "../plan-dashboard/public/fonts/noto-nastaliq-urdu/OFL.txt",
    to: "noto-nastaliq-urdu-LICENSE.txt",
    note: "SIL OFL 1.1",
  },
  // Arabic SCRIPTURE — Amiri Quran, and it is a different file from Amiri above,
  // not a weight of it. It draws U+06DF, the mark saying a letter is written but
  // not pronounced, as a mark: the Qur'anic face this corpus used until
  // 2026-08-09 declares that character a BASE glyph, so it printed as a full-size
  // circle that tore the word open, 175 times across the seven books. That font
  // may not be edited — its licence forbids it in so many words — and the one
  // character cannot be redirected in CSS, because a browser falls back per
  // cluster and keeps a combining mark in the font of the letter it sits on.
  //
  // Copied from the admin site rather than a package, which is where it is
  // vendored, and as TTF because that is the form it ships in there. Only
  // scripture uses it; every other Arabic run stays on Scheherazade.
  {
    from: "../plan-dashboard/public/fonts/amiri/AmiriQuran.ttf",
    to: "AmiriQuran.ttf",
    note: "Amiri Quran (scripture only)",
  },
  // ---- The reader's font picker ------------------------------------------
  //
  // Three faces beyond Literata and Inter, chosen because each is drawn for
  // reading rather than for looking different. They ship here rather than being
  // named as system fonts so that the same six choices exist on every device —
  // a picker whose options depend on the machine offers a setting that does
  // nothing on half of them.
  //
  // Merriweather — the second serif, and the one to reach for when Literata's
  // narrow forms are hard going. Drawn for screens: a large x-height, short
  // descenders and open apertures. The `opsz` cut for the same reason as
  // Literata's, since this is the size the reader changes most.
  {
    from: "node_modules/@fontsource-variable/merriweather/files/merriweather-latin-opsz-normal.woff2",
    to: "merriweather-latin-opsz-normal.woff2",
    note: "Merriweather Variable (roman)",
  },
  {
    from: "node_modules/@fontsource-variable/merriweather/files/merriweather-latin-opsz-italic.woff2",
    to: "merriweather-latin-opsz-italic.woff2",
    note: "Merriweather Variable (italic)",
  },
  {
    from: "node_modules/@fontsource-variable/merriweather/LICENSE",
    to: "merriweather-LICENSE.txt",
    note: "SIL OFL 1.1",
  },
  // Atkinson Hyperlegible — drawn by the Braille Institute for low vision. Its
  // whole design is telling confusable characters apart: I l 1, O 0, b d p q.
  // Not variable; 400 and its italic are what running prose needs.
  {
    from: "node_modules/@fontsource/atkinson-hyperlegible/files/atkinson-hyperlegible-latin-400-normal.woff2",
    to: "atkinson-hyperlegible-latin-400-normal.woff2",
    note: "Atkinson Hyperlegible 400",
  },
  {
    from: "node_modules/@fontsource/atkinson-hyperlegible/files/atkinson-hyperlegible-latin-400-italic.woff2",
    to: "atkinson-hyperlegible-latin-400-italic.woff2",
    note: "Atkinson Hyperlegible 400 italic",
  },
  {
    from: "node_modules/@fontsource/atkinson-hyperlegible/LICENSE",
    to: "atkinson-hyperlegible-LICENSE.txt",
    note: "SIL OFL 1.1",
  },
  // Lexend — drawn around reading proficiency rather than around a style: wide
  // spacing and simplified forms, and the face most often suggested beside
  // OpenDyslexic for readers who find dense text hard to hold. No italic in the
  // family, which is why the reading column falls back for `<em>`.
  {
    from: "node_modules/@fontsource-variable/lexend/files/lexend-latin-wght-normal.woff2",
    to: "lexend-latin-wght-normal.woff2",
    note: "Lexend Variable",
  },
  {
    from: "node_modules/@fontsource-variable/lexend/LICENSE",
    to: "lexend-LICENSE.txt",
    note: "SIL OFL 1.1",
  },
  // Shantell Sans — the two descriptions on the welcome chooser's tiles, and
  // nowhere else. Asif picked it from five handwriting faces set in the real
  // tile (2026-08-29), and it is the one of them drawn with the proportions of
  // a text face rather than of a signature — which is what lets a whole
  // paragraph of handwriting stay readable at body size.
  //
  // The `wght` cut, not `full`. The family carries three more axes — bounce,
  // informality and spacing — and shipping them costs bytes for axes nothing
  // varies. Swap the file the day a rule asks for one.
  {
    from: "node_modules/@fontsource-variable/shantell-sans/files/shantell-sans-latin-wght-normal.woff2",
    to: "shantell-sans-latin-wght-normal.woff2",
    note: "Shantell Sans Variable (welcome tile descriptions)",
  },
  {
    from: "node_modules/@fontsource-variable/shantell-sans/LICENSE",
    to: "shantell-sans-LICENSE.txt",
    note: "SIL OFL 1.1",
  },
  // Sora — the welcome chooser's tiles, and nowhere else. A geometric sans with
  // an open aperture and a tall x-height, chosen because the two tiles are the
  // one screen that is neither prose nor chrome: Literata reads as a page and
  // Inter reads as the interface, and the choice between the two collections is
  // meant to feel like neither. COPIED like every other face — a Google Fonts
  // <link> on a private library tells another origin who is reading and when.
  {
    from: "node_modules/@fontsource-variable/sora/files/sora-latin-wght-normal.woff2",
    to: "sora-latin-wght-normal.woff2",
    note: "Sora Variable (welcome tiles)",
  },
  {
    from: "node_modules/@fontsource-variable/sora/LICENSE",
    to: "sora-LICENSE.txt",
    note: "SIL OFL 1.1",
  },
  // OpenDyslexic — weighted bottoms, so letters are harder to rotate or flip.

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
      problems.push(
        `${entry.to} differs from its source — re-run \`npm run fonts\``,
      );
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

console.log(
  check
    ? "sync-fonts: all faces present and current"
    : `sync-fonts: ${copied} file(s) written to public/fonts/`,
);
