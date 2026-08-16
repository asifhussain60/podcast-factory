/**
 * The one place that knows what a note is allowed to contain.
 *
 * A note (`annotation.note`, `episode_note.note`) is authored through a small
 * rich-text toolbar — bold, italic, bullet list, numbered list — nothing else.
 * That means exactly seven tokens are ever legitimate: `p strong em ul ol li`
 * and the void `br`. This module is a hand-rolled parser over exactly that
 * allow-list, with no attribute support at all (none of the seven tags is ever
 * allowed to carry one), and it is the ONLY parser: `sanitizeNote` (the
 * server-side write gate) and `renderNote` (what every surface displays) walk
 * the same tree, so "what can be stored" and "what can be rendered" can never
 * drift apart.
 *
 * Deliberately not a general HTML parser and not DOM-based: this module is
 * imported from both a `*.server.ts` file running on the Workers isolate
 * (no `document`, no `DOMParser`) and from React components running in the
 * browser, so it must not touch the DOM in either direction. Anything that
 * isn't exactly one of the seven allowed token shapes — `<script>`, an
 * `onerror=` attribute, a stray `<` a user typed, a mismatched close tag — is
 * never treated as structural. It degrades to visible, escaped text instead
 * of being dropped, so a rejected payload never produces a confusing empty
 * note and can never be interpreted as markup on the way back out.
 */

import { createElement, Fragment, type ReactNode } from "react";

const ALLOWED_WRAPPER = new Set([
  "p",
  "strong",
  "em",
  "ul",
  "ol",
  "li",
] as const);
type WrapperTag = "p" | "strong" | "em" | "ul" | "ol" | "li";

export type RichNode =
  | { type: "text"; text: string }
  | { type: "br" }
  | { type: WrapperTag; children: RichNode[] };

const OPEN_RE = /^<(p|strong|em|ul|ol|li)>/i;
const CLOSE_RE = /^<\/(p|strong|em|ul|ol|li)>/i;
const BR_RE = /^<br\s*\/?>/i;

const ENTITIES: Record<string, string> = {
  "&amp;": "&",
  "&lt;": "<",
  "&gt;": ">",
  "&quot;": '"',
  "&#39;": "'",
  "&apos;": "'",
};

function decodeEntities(text: string): string {
  return text.replace(
    /&(?:amp|lt|gt|quot|#39|apos);/g,
    (m) => ENTITIES[m] ?? m,
  );
}

function encodeEntities(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

interface Cursor {
  i: number;
}

/**
 * Recursive descent over the fixed token set. `stopTag` is the wrapper this
 * call is nested inside (or null at the top level); hitting that tag's close
 * ends this call and consumes it. Any other close tag encountered here is not
 * ours to consume — it is not a recognized token shape at all in that
 * position, so it falls through to the literal-text path below, exactly like
 * an unmatched or malformed tag does.
 */
function parseNodes(
  input: string,
  pos: Cursor,
  stopTag: WrapperTag | null,
): RichNode[] {
  const nodes: RichNode[] = [];
  let buf = "";

  const flush = () => {
    if (buf.length > 0) {
      nodes.push({ type: "text", text: decodeEntities(buf) });
      buf = "";
    }
  };

  while (pos.i < input.length) {
    const rest = input.slice(pos.i);

    if (input[pos.i] !== "<") {
      buf += input[pos.i];
      pos.i += 1;
      continue;
    }

    if (stopTag !== null) {
      const close = CLOSE_RE.exec(rest);
      if (close !== null && close[1].toLowerCase() === stopTag) {
        flush();
        pos.i += close[0].length;
        return nodes;
      }
    }

    const brMatch = BR_RE.exec(rest);
    if (brMatch !== null) {
      flush();
      nodes.push({ type: "br" });
      pos.i += brMatch[0].length;
      continue;
    }

    const openMatch = OPEN_RE.exec(rest);
    if (openMatch !== null) {
      flush();
      const tag = openMatch[1].toLowerCase() as WrapperTag;
      pos.i += openMatch[0].length;
      nodes.push({ type: tag, children: parseNodes(input, pos, tag) });
      continue;
    }

    // Not one of the recognized token shapes in this position (includes a
    // close tag for a wrapper we are not inside, any other tag, or a bare
    // '<'). Not structural — one literal character, and keep going.
    buf += "<";
    pos.i += 1;
  }

  flush();
  return nodes;
}

export function parseNote(raw: string): RichNode[] {
  if (raw.length === 0) return [];
  return parseNodes(raw, { i: 0 }, null);
}

function serializeNodes(nodes: RichNode[]): string {
  return nodes
    .map((node) => {
      if (node.type === "text") return encodeEntities(node.text);
      if (node.type === "br") return "<br>";
      return `<${node.type}>${serializeNodes(node.children)}</${node.type}>`;
    })
    .join("");
}

/**
 * The server-side write gate. Re-serializes the parsed tree back to a
 * canonical string containing only the seven allowed tokens, zero
 * attributes, all text HTML-escaped. Call this before anything reaches
 * `requireText`/storage — never store `raw` directly.
 */
export function sanitizeNote(raw: string): string {
  return serializeNodes(parseNote(raw));
}

function renderNodes(nodes: RichNode[], keyPrefix: string): ReactNode[] {
  return nodes.map((node, i) => {
    const key = `${keyPrefix}-${i}`;
    if (node.type === "text") return node.text.length > 0 ? node.text : null;
    if (node.type === "br") return createElement("br", { key });
    return createElement(
      node.type,
      { key },
      ...renderNodes(node.children, key),
    );
  });
}

/**
 * What every surface displays. Never uses `dangerouslySetInnerHTML` — walks
 * the same parse tree `sanitizeNote` produces and maps it straight to React
 * elements, so a rejected/neutralized payload is only ever plain text content
 * of a text node, never markup. A legacy note (plain text saved before this
 * feature existed, no recognized tags) parses to a single text node and
 * renders exactly as it always has.
 */
export function renderNote(raw: string | null | undefined): ReactNode {
  if (raw === null || raw === undefined || raw.length === 0) return null;
  return createElement(Fragment, null, ...renderNodes(parseNote(raw), "n"));
}

export { ALLOWED_WRAPPER };
