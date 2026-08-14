/**
 * quote-groups.mjs — which blocks merge into ONE quote card, and which don't.
 *
 * Sibling to quote-kind.mjs, not an extension of it. `quote-kind.json`'s keys
 * are only ever a quotation's own first line — a gloss paragraph has never
 * been representable there, and bolting a `group` field onto that map would
 * force every reader of `readQuoteKind` to newly tolerate entries that carry
 * no valid kind. A separate file keeps that file, and its carefully argued
 * tests, completely untouched: an empty `quote-groups.json` (the state of
 * every book today) changes nothing about how a book renders.
 *
 * TWO KINDS OF MEMBER, in one flat declaration space per chapter, BOTH keyed
 * the SAME way as quote-kind.json: the block's own first line, verbatim, not
 * a hash. `type: "quote"` is a blockquote fragment (identical to
 * `quoteKindKey`); `type: "gloss"` is a prose paragraph that is the TIGHT
 * translation of one specific quote fragment (never the author's own
 * commentary), keyed by ITS first line the same way.
 *
 * An earlier draft of this file keyed a gloss by `paraFingerprint` (a sha256
 * slice) instead — reused from para-blocks.mjs on the theory that it was
 * already the Arabic-reveal feature's identity for "which paragraph is
 * this." It was wrong for a reason quote-kind.mjs's own header already
 * warns about: `markdown.ts` is bundled into the BROWSER and cannot import
 * `node:crypto`, so the renderer that decides a gloss's card membership at
 * READ time would have needed its own hash implementation kept byte-for-byte
 * identical to Node's forever — "a fingerprint computed in three languages,
 * which becomes a fold table that has to be kept in step forever with a
 * silent misclassification as the failure mode," the exact sentence that
 * file's docstring uses to explain why quote identity is a first line and
 * not a hash. A gloss is short by construction (one tight sentence), so its
 * first line already IS effectively its whole text almost always, and where
 * it is not, the same "an edited key falls back to the default, never a
 * crash" conservatism applies as everywhere else in this store.
 *
 * ORDER IS NEVER DECLARED. A group is whatever contiguous run of same-group
 * blocks the renderer finds in document order — see mergeDeclaredGroups in
 * book-html.mjs / markdown.ts. That one rule removes a whole class of bug
 * (declared order silently disagreeing with book.md) and means writing a
 * declaration is always just "tag this block with this group id," never
 * "and also record where it goes."
 *
 * NOTHING IS EVER INFERRED. Group membership is a human declaration, exactly
 * like kind — no proximity heuristic, no "this paragraph looks like a
 * translation" guess. See quote-kind.mjs's header for why: an inferred
 * attribution on a religious text is a claim nobody made.
 */
import { existsSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import path from "node:path";

const SCHEMA = "book.quote-groups/v1";

/**
 * `_system/quote-groups.json` → { chapterKey: { key: {group, type} } }.
 * Malformed/missing/unreadable → {}, exactly like readQuoteKind — an edition
 * renders every quotation independently rather than failing to render.
 */
export function readQuoteGroups(bookDir) {
  const p = path.join(bookDir, "_system", "quote-groups.json");
  if (!existsSync(p)) return {};
  try {
    const raw = JSON.parse(readFileSync(p, "utf-8"));
    const out = {};
    for (const [chapter, blocks] of Object.entries(raw?.chapters ?? {})) {
      if (!blocks || typeof blocks !== "object") continue;
      const kept = {};
      for (const [key, declared] of Object.entries(blocks)) {
        const group = String(declared?.group ?? "").trim();
        const type = declared?.type === "gloss" ? "gloss" : "quote";
        if (!group) continue;
        kept[String(key).trim()] = { group, type };
      }
      if (Object.keys(kept).length) out[chapter] = kept;
    }
    return out;
  } catch {
    return {};
  }
}

/** The key for one block: its first non-empty line, trimmed. Literally
 *  `quoteKindKey` under a local name — kept as its own export rather than a
 *  re-export so a reader of this file never has to open quote-kind.mjs to
 *  see that a quote and a gloss are keyed identically. */
export function groupKey(lines) {
  for (const p of lines ?? []) {
    const line = String(p ?? "").trim();
    if (line) return line;
  }
  return "";
}

/** Flattened per-chapter maps, keyed the way the renderer looks them up: one
 *  map for quote-fragment keys, one for gloss keys — kept separate so the two
 *  key spaces can never collide even in theory, unlike flattenQuoteKind's
 *  single map (safe there because every key in that file is the same kind of
 *  thing: a quotation's text). Both key spaces are first-line strings. */
export function flattenQuoteGroups(byChapter) {
  const quote = {};
  const gloss = {};
  for (const blocks of Object.values(byChapter ?? {})) {
    for (const [key, decl] of Object.entries(blocks)) {
      (decl.type === "gloss" ? gloss : quote)[key] = decl.group;
    }
  }
  return { quote, gloss };
}

/**
 * Write (or clear) one member's group tag. Read-modify-write, mirroring
 * writeQuoteKind — the Composer's grouping control calls this once per block
 * it tags and awaits the response before the next call fires.
 *
 * `group: ""` deletes the entry (falls the block out of any group, same
 * "malformed/absent is the conservative default" posture as writeQuoteKind).
 */
export function writeQuoteGroup(bookDir, chapterKey, key, group, type) {
  const chapter = String(chapterKey ?? "").trim();
  const memberKey = String(key ?? "").trim();
  if (!chapter || !memberKey)
    throw new Error("chapterKey and key are required");
  const dir = path.join(bookDir, "_system");
  const p = path.join(dir, "quote-groups.json");
  const store = { schema: SCHEMA, chapters: readQuoteGroups(bookDir) };
  const g = String(group ?? "").trim();
  if (g) {
    const memberType = type === "gloss" ? "gloss" : "quote";
    store.chapters[chapter] = {
      ...(store.chapters[chapter] ?? {}),
      [memberKey]: { group: g, type: memberType },
    };
  } else if (store.chapters[chapter]) {
    delete store.chapters[chapter][memberKey];
    if (!Object.keys(store.chapters[chapter]).length)
      delete store.chapters[chapter];
  }
  mkdirSync(dir, { recursive: true });
  writeFileSync(p, JSON.stringify(store, null, 2) + "\n", "utf-8");
  return store;
}

/**
 * Collect a linear list of rendered-block markers into merged runs.
 *
 * `blocks` is an ordered array of `{ groupId: string|null, kind?: string }` —
 * one entry per already-decided block (quote fragment or gloss paragraph) in
 * document order, `groupId: null` for anything undeclared. Returns the SAME
 * length array of run indices: `runOf[i] === runOf[j]` means blocks i and j
 * merge into one card. A block with `groupId: null` always gets its own
 * singleton run (never merges). A run of DECLARED same-group blocks is only
 * collapsed into one merged run when (a) it has at least 2 members and
 * (b) every `type: "quote"` member in it shares the same effective kind —
 * otherwise every member of that would-be run reverts to its own singleton
 * run, i.e. renders exactly as if ungrouped. This is the ONE function shared
 * (copy-mirrored, not imported — markdown.ts is client-bundled and cannot
 * import this .mjs) between book-html.mjs and markdown.ts, and the one
 * `quote-groups.fixtures.json` pins.
 */
export function collectGroupRuns(blocks) {
  const runOf = new Array(blocks.length).fill(-1);
  let nextRun = 0;
  let i = 0;
  while (i < blocks.length) {
    const gid = blocks[i].groupId;
    if (!gid) {
      runOf[i] = nextRun++;
      i++;
      continue;
    }
    let j = i;
    while (j < blocks.length && blocks[j].groupId === gid) j++;
    const run = blocks.slice(i, j);
    const kinds = new Set(
      run.filter((b) => b.type !== "gloss" && b.kind).map((b) => b.kind),
    );
    const mergeable = run.length >= 2 && kinds.size <= 1;
    if (mergeable) {
      const id = nextRun++;
      for (let k = i; k < j; k++) runOf[k] = id;
    } else {
      for (let k = i; k < j; k++) runOf[k] = nextRun++;
    }
    i = j;
  }
  return runOf;
}
