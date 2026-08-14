/**
 * markdown.ts — the built-in markdown rule set.
 *
 * Covers exactly the StarterKit types this package's base schema admits. It is
 * deliberately NOT a CommonMark writer: the formats it can write are the formats
 * it has been shown to round-trip, and every one it cannot write is absent from
 * the schema rather than approximated.
 */
import type { Node as PMNode } from "@tiptap/pm/model";
import { createSerializer } from "./serializer.ts";
import type {
  MarkdownOptions,
  MarkSerializerRule,
  NodeSerializerRule,
  Serializer,
  SerializerRules,
} from "./types.ts";

/** Innermost first. Declared, not inferred: `bold`+`italic` must compose to
 *  `***text***`, which only happens if italic wraps before bold. */
export const MARKDOWN_MARK_ORDER = [
  "code",
  "strike",
  "italic",
  "bold",
  "link",
] as const;

export function createMarkdownRules(
  options: MarkdownOptions = {},
): SerializerRules {
  const bullet = options.bullet ?? "-";
  const emphasis = options.emphasis ?? "*";
  const strong = options.strong ?? "**";
  const fence = options.codeFence ?? "```";
  const fenceLanguage = options.fenceLanguage ?? true;
  const hardBreak = options.hardBreak ?? "error";

  const nodes: Record<string, NodeSerializerRule> = {
    paragraph: (ctx) => ctx.inline(),

    heading: (ctx) =>
      `${"#".repeat(Number(ctx.attrs.level) || 2)} ${ctx.inline()}`,

    blockquote: (ctx) => {
      // A blank `>` between paragraphs is load-bearing, not cosmetic: without
      // it a reader re-parsing this merges the paragraphs into one run, which
      // is how an Arabic line and its translation become a single line.
      const lines: string[] = [];
      ctx.childBlocks().forEach((block, i) => {
        if (i > 0) lines.push("");
        const trimmed = block.trimEnd();
        if (trimmed) lines.push(...trimmed.split("\n"));
      });
      if (lines.length === 0) return ">";
      return lines.map((l) => (l === "" ? ">" : `> ${l}`)).join("\n");
    },

    bulletList: (ctx) =>
      ctx
        .childBlocks()
        .map((item) => `${bullet} ${item}`)
        .join("\n"),

    orderedList: (ctx) => {
      // An item's STATED ordinal wins over its position. A list legitimately
      // starting at 3, or an author style repeating "1." per item, is content —
      // renumbering it invents numbering the source never claimed.
      let counter = Number(ctx.attrs.start) || 1;
      return ctx
        .childBlocks()
        .map((item, i) => {
          const child = ctx.node.child(i);
          const stated = child.attrs?.value;
          const n = typeof stated === "number" ? stated : counter;
          counter = n + 1;
          return `${n}. ${item}`;
        })
        .join("\n");
    },

    listItem: (ctx) => ctx.inline().trim(),

    codeBlock: (ctx) => {
      const lang = fenceLanguage ? String(ctx.attrs.language ?? "") : "";
      return `${fence}${lang}\n${ctx.text()}\n${fence}`;
    },

    horizontalRule: () => "---",

    // A node type defined by a consuming application's own editor schema,
    // covered here so that application's coverage assertion stays meaningful
    // rather than permanently failing the moment its schema grows a node this
    // package's base schema doesn't define. Mirrors that application's own
    // serialization rule exactly: alt text is emitted only when non-empty.
    chapterImage: (ctx) => {
      const alt = String(ctx.attrs.alt ?? "").trim();
      return `![${alt}](${String(ctx.attrs.src ?? "")})`;
    },
  };

  // `error` (the default) registers NO rule, so a schema carrying hardBreak
  // fails the coverage assertion at attach rather than at save. Inventing a
  // spelling the host's reader cannot parse back does not save the break — it
  // moves the loss to the next read, where it is harder to attribute.
  if (hardBreak !== "error") {
    nodes.hardBreak = () =>
      hardBreak === "backslash"
        ? "\\\n"
        : hardBreak === "twoSpaces"
          ? "  \n"
          : "\n";
  }

  const marks: Record<string, MarkSerializerRule> = {
    code: ({ inner }) => `\`${inner}\``,
    strike: ({ inner }) => `~~${inner}~~`,
    italic: ({ inner }) => `${emphasis}${inner}${emphasis}`,
    bold: ({ inner }) => `${strong}${inner}${strong}`,
    link: ({ inner, attrs }) =>
      typeof attrs.href === "string" && attrs.href
        ? `[${inner}](${attrs.href})`
        : inner,
  };

  return {
    nodes,
    marks,
    markOrder: MARKDOWN_MARK_ORDER,
    blockSeparator: "\n\n",
  };
}

export function createMarkdownSerializer(
  options: MarkdownOptions & { rules?: Partial<SerializerRules> } = {},
): Serializer {
  const base = createMarkdownRules(options);
  const merged: SerializerRules = {
    nodes: { ...base.nodes, ...(options.rules?.nodes ?? {}) },
    marks: { ...base.marks, ...(options.rules?.marks ?? {}) },
    markOrder: options.rules?.markOrder ?? base.markOrder,
    blockSeparator: options.rules?.blockSeparator ?? base.blockSeparator,
  };
  const inner = createSerializer(merged);
  return {
    covers: inner.covers,
    // A single trailing newline, always: a file that sometimes ends with one
    // and sometimes does not produces a one-byte diff on every other save.
    serialize: (doc: PMNode) => `${inner.serialize(doc).trimEnd()}\n`,
  };
}
