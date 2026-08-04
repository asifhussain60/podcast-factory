import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

/**
 * The stylesheet and the markup agree about what exists.
 *
 * Two failures this catches, both of which have actually happened here:
 *
 *   1. A class used in a component with no rule anywhere — the element renders
 *      unstyled, which on a card or a panel looks like a layout bug rather than
 *      like a missing rule, so it gets debugged in the wrong file.
 *
 *   2. A rule nobody uses. The 2026-08-03 audit found eight, one of them a
 *      `.pf-table` that had never been used by anything. Dead rules are not
 *      harmless: the next person to need a table finds one, adopts it, and
 *      inherits whatever it drifted into while nothing was rendering it.
 *
 * It does NOT catch the collision that motivated it — a component class named
 * `.pf-note` over a text utility already called `.pf-note`, which put a border
 * around every muted paragraph on the admin screens. Both were used and both had
 * rules. That one is only findable by looking, which is what `npm run shots` is
 * for; this test is the cheap half.
 */

const CSS = readFileSync(new URL("../app/styles/podcast-factory.css", import.meta.url), "utf8");

/** Every `.pf-*` / `.reader*` class the stylesheet declares a rule for. */
function declared(css: string): Set<string> {
  return new Set([...css.matchAll(/\.(pf-[a-z0-9_-]+)/g)].map((m) => m[1]));
}

/** Every class named in a `className` anywhere in the app. */
async function used(): Promise<Set<string>> {
  const { glob } = await import("node:fs/promises");
  const out = new Set<string>();

  for await (const entry of glob("app/**/*.{ts,tsx}")) {
    const text = readFileSync(entry, "utf8");
    // Both `className="a b"` and the template-literal form the reader uses for
    // its colour modifiers, which is where a whole family would otherwise look
    // unused: `pf-mark--${annotation.colour}`.
    // BOTH capture groups. Reading only the first meant every template-literal
    // className was silently skipped, and the whole `pf-gate` family was
    // reported as dead CSS while it was rendering on two live pages.
    // A third form, added when the selection bar started choosing between two
    // literals — `className={noting ? "pf-selbar pf-selbar--paper" : "pf-selbar"}`
    // — and BOTH classes were reported as dead CSS while the composer was
    // rendering them. Any braced expression carrying no backtick and no nested
    // brace, split like the others; the template branch is tried first so a
    // `${…}` inside a template literal still matches there.
    for (const [, quoted, templated, braced] of text.matchAll(
      /className=(?:"([^"]*)"|\{`([^`]*)`\}|\{([^`{}]*)\})/g,
    )) {
      const value = quoted ?? templated ?? braced;
      // Split on anything a class name cannot contain, so the quotes and
      // ternary punctuation inside a template literal do not glue themselves to
      // the name — `" pf-header--bare"` was reported as unused for exactly that.
      for (const cls of (value ?? "").split(/[^A-Za-z0-9_-]+/)) {
        if (cls.startsWith("pf-")) out.add(cls);
      }
    }
    // Selectors the components QUERY FOR rather than render. The leading dot is
    // required: without it every `localStorage` key in the app (`pf-theme`,
    // `pf-reading`, `pf-marks`, `pf-positions`) and every element id read as a
    // class that had no rule.
    for (const [, cls] of text.matchAll(/["'`]\.(pf-[a-z0-9_-]+)/g)) out.add(cls);
  }

  return out;
}

/**
 * Families whose members are composed at run time from a value.
 *
 * `pf-hl--gold` is written as `pf-hl--${colour}`, so the four concrete names
 * never appear in source. Listing the PREFIX rather than the four names means
 * adding a fifth colour needs no edit here — and the palette test already fails
 * if a colour is declared in one theme and not another.
 */
const COMPOSED_PREFIXES = [
  "pf-hl",
  "pf-mark--",
  "pf-selbar__colour--",
  "pf-swatch",
  // The two side panels are one component rendered twice, so the edge each one
  // is pinned to arrives as `--${side}` rather than as a literal.
  "pf-drawer--",
  "pf-edge-tab--",
  // Which of the two hosts is speaking arrives as an integer from the
  // transcription service, so `pf-cue--speaker-2` is composed rather than
  // written. Listing the prefix means a three-voice recording needs no edit here.
  "pf-cue--speaker-",
];


/** Rules that exist for a reason other than being rendered by this app. */
const DELIBERATE = new Set([
  // Rendered by the Icon component, which builds its class list rather than
  // writing a literal `className`.
  "pf-icon",
  // The Companion tint. Painted into the chapter by Highlights.tsx, which sets
  // `className` on an element it created rather than writing one in JSX — the
  // same reason `pf-hl` is listed as a composed prefix above.
  "pf-cp",
  // A BEM block whose block-level rule is genuinely empty: `.pf-section__title`,
  // `__head`, `__count` and `__intro` all carry rules, and the wrapper needs
  // none. Naming the block anyway is what makes the element names legible.
  "pf-section",
]);

describe("the stylesheet and the markup", () => {
  it("has a rule for every class the app renders", async () => {
    const rules = declared(CSS);
    const missing = [...(await used())]
      .filter((c) => !rules.has(c))
      .filter((c) => !DELIBERATE.has(c))
      // The bare stem of a composed family — `pf-mark--` out of
      // `pf-mark--${colour}` — is not a class anyone renders.
      .filter((c) => !COMPOSED_PREFIXES.includes(c))
      .sort();

    expect(
      missing,
      `these classes are used in app/ and styled nowhere:\n  ${missing.join("\n  ")}`,
    ).toEqual([]);
  });

  it("has no rule the app never renders", async () => {
    const rendered = await used();
    const dead = [...declared(CSS)]
      .filter((c) => !rendered.has(c))
      .filter((c) => !COMPOSED_PREFIXES.some((p) => c.startsWith(p)))
      .filter((c) => !DELIBERATE.has(c))
      .sort();

    expect(
      dead,
      `these rules are declared and never used. Delete them, or render them:\n  ${dead.join("\n  ")}`,
    ).toEqual([]);
  });
});
