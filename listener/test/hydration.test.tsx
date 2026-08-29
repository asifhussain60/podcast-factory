import { describe, expect, it, vi } from "vitest";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { renderToStaticMarkup } from "react-dom/server";

import { WorkCard } from "../app/components/WorkCard";
import type { WorkVolume } from "../app/components/WorkCard";

/**
 * No stored preference may be read while the first render is still running.
 *
 * The failure this exists to catch is not a wrong pixel, and that is why it went
 * unnoticed for so long. A stored value read during render — the classic
 * `useState(() => localStorage.getItem(...))` — is correct on every reload where
 * the reader happens to be on the default, and only wrong for a reader who
 * changed the setting. For that reader the client's first tree cannot match the
 * server's HTML, React throws the server's DOM away and rebuilds it, and
 * `data-theme` goes with it: THEME_INIT_SCRIPT stamps that attribute on `<html>`
 * before first paint, so no React tree owns it and nothing puts it back.
 *
 * The visible consequence is one step removed from the cause, which is what made
 * it hard to see. EVERY `[data-theme]`-scoped rule stops applying — the reader's
 * Dark or Sepia palette silently reverts to the base one, and session cards drop
 * out of violet into the books' navy. The shelf's view-mode toggle and a
 * multi-volume work's remembered volume were both doing this on `/library`, the
 * second on the DEFAULT view.
 *
 * So the assertion is structural rather than a list of keys: nowhere in the app
 * may a `useState`/`useReducer` initial value reach `localStorage`, directly or
 * through a helper. The correct shape is the one `hydrateTheme`, `hydrateReading`
 * and the player's `rate` already use — default first, storage in an effect.
 */

const APP = fileURLToPath(new URL("../app", import.meta.url));

function sourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((entry) => {
    const path = join(dir, entry);
    if (statSync(path).isDirectory()) return sourceFiles(path);
    return /\.tsx?$/.test(entry) ? [path] : [];
  });
}

/**
 * The top-level declarations in a file, as name -> body. Column-0 only, which is
 * every helper of this kind in this app: these loaders are module-level
 * functions by construction, since a lazy initializer has to be one.
 */
function topLevelBlocks(source: string): Map<string, string> {
  const blocks = new Map<string, string>();
  const start = /^(?:export\s+)?(?:async\s+)?(?:function|const|let)\s+(\w+)/;
  const lines = source.split("\n");
  let name: string | null = null;
  let body: string[] = [];
  const flush = () => {
    if (name !== null) blocks.set(name, body.join("\n"));
  };
  for (const line of lines) {
    const match = start.exec(line);
    if (match !== null) {
      flush();
      name = match[1];
      body = [line];
    } else if (name !== null) {
      body.push(line);
    }
  }
  flush();
  return blocks;
}

/**
 * Comments and string literals blanked out, so scanning finds only real code.
 *
 * Not optional: `Player.tsx` explains in prose that it does NOT seed state with
 * `useState(loadRate())`, and a scanner that reads its own documentation as
 * evidence would fail the one file that already gets this right.
 */
function code(source: string): string {
  let out = "";
  let i = 0;
  while (i < source.length) {
    const two = source.slice(i, i + 2);
    if (two === "//") {
      while (i < source.length && source[i] !== "\n") i += 1;
      continue;
    }
    if (two === "/*") {
      const end = source.indexOf("*/", i + 2);
      i = end === -1 ? source.length : end + 2;
      continue;
    }
    const quote = source[i];
    if (quote === '"' || quote === "'" || quote === "`") {
      i += 1;
      while (i < source.length && source[i] !== quote) {
        i += source[i] === "\\" ? 2 : 1;
      }
      i += 1;
      continue;
    }
    out += source[i];
    i += 1;
  }
  return out;
}

/** The argument list of each call to `name`, parens balanced. */
function callArguments(input: string, name: string): string[] {
  const source = code(input);
  const args: string[] = [];
  const call = new RegExp(`\\b${name}\\s*(?:<[\\s\\S]*?>)?\\s*\\(`, "g");
  let match: RegExpExecArray | null;
  while ((match = call.exec(source)) !== null) {
    let depth = 1;
    let i = match.index + match[0].length;
    const from = i;
    while (i < source.length && depth > 0) {
      if (source[i] === "(") depth += 1;
      else if (source[i] === ")") depth -= 1;
      i += 1;
    }
    args.push(source.slice(from, i - 1));
  }
  return args;
}

const hookArguments = (source: string): string[] => [
  ...callArguments(source, "useState"),
  ...callArguments(source, "useReducer"),
];

/** Top-level commas only — a type argument or a nested call carries its own. */
function splitArguments(list: string): string[] {
  const parts: string[] = [];
  let depth = 0;
  let start = 0;
  for (let i = 0; i < list.length; i += 1) {
    const c = list[i];
    if (c === "(" || c === "[" || c === "{") depth += 1;
    else if (c === ")" || c === "]" || c === "}") depth -= 1;
    else if (c === "," && depth === 0) {
      parts.push(list.slice(start, i));
      start = i + 1;
    }
  }
  parts.push(list.slice(start));
  return parts.map((part) => part.trim()).filter((part) => part !== "");
}

describe("no stored preference is read during the first render", () => {
  const files = sourceFiles(APP);

  it("finds the app's source to scan", () => {
    // A walk that silently returns nothing would pass every assertion below.
    expect(files.length).toBeGreaterThan(40);
  });

  for (const path of files) {
    const source = readFileSync(path, "utf8");
    if (!source.includes("localStorage")) continue;
    const relative = path.slice(APP.length + 1);

    it(`${relative} seeds no state from storage`, () => {
      const readers = [...topLevelBlocks(code(source))]
        .filter(([, body]) => body.includes("localStorage.getItem"))
        .map(([name]) => name);

      for (const argument of hookArguments(source)) {
        expect(
          argument.includes("localStorage"),
          `${relative} reads localStorage in a useState/useReducer initial value`,
        ).toBe(false);

        for (const reader of readers) {
          expect(
            new RegExp(`\\b${reader}\\b`).test(argument),
            `${relative} seeds state with ${reader}(), which reads localStorage. ` +
              `Start at the default and call it from an effect instead.`,
          ).toBe(false);
        }
      }
    });
  }
});

describe("every external store renders the same thing on both sides", () => {
  // `useSyncExternalStore` is the correct way to read a client-only value, and
  // it is only correct WITH its third argument: without `getServerSnapshot` the
  // server render throws, and a third argument that returned the stored value
  // would reintroduce the very mismatch the hook is here to avoid. It must be a
  // default, which is why the ones in `~/lib/shelf` are named `defaultX`.
  const calls = sourceFiles(APP).map((path) => ({
    relative: path.slice(APP.length + 1),
    // Real calls, not the prose about them: `code()` has already blanked the
    // comments, and several modules explain this hook without calling it.
    calls: callArguments(readFileSync(path, "utf8"), "useSyncExternalStore"),
  }));

  it("finds the stores to check", () => {
    expect(calls.flatMap((file) => file.calls).length).toBeGreaterThan(0);
  });

  for (const { relative, calls: found } of calls) {
    if (found.length === 0) continue;

    it(`${relative} passes a server snapshot`, () => {
      for (const call of found) {
        expect(
          splitArguments(call).length,
          `${relative} calls useSyncExternalStore without a getServerSnapshot`,
        ).toBe(3);
      }
    });
  }
});

describe("a multi-volume work on the shelf", () => {
  const volumes: WorkVolume[] = [
    { slug: "vol-1", title: "Volume One", bucket: "Islamic", card: null },
    { slug: "vol-2", title: "Volume Two", bucket: "Islamic", card: null },
  ];

  it("renders the same picker whether or not a volume was remembered", () => {
    // The behavioural half of the rule above, on the component that was doing
    // this in the shelf's DEFAULT view. Both renders are the SERVER's render;
    // the second one simply has a storage to reach for. If it reaches, the two
    // strings differ — which is exactly the mismatch a browser would report.
    const plain = renderToStaticMarkup(
      <WorkCard workSlug="a-work" title="A Work" volumes={volumes} />,
    );

    vi.stubGlobal("localStorage", {
      getItem: () => "vol-2",
      setItem: () => {},
    });
    try {
      const remembered = renderToStaticMarkup(
        <WorkCard workSlug="a-work" title="A Work" volumes={volumes} />,
      );
      expect(remembered).toBe(plain);
    } finally {
      vi.unstubAllGlobals();
    }
  });
});
