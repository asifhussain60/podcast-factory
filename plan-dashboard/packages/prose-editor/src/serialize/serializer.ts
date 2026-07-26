/**
 * serializer.ts — the visitor engine.
 *
 * Format-agnostic: it walks the document and dispatches to rules. Markdown is
 * one rule set (markdown.ts); a host could supply another for a different
 * output format without touching this file.
 *
 * The engine THROWS on an unknown type rather than skipping it. That is the
 * whole point. `assertSerializerTotal` catches the same problem earlier and with
 * a better message, but a serializer built standalone still cannot silently drop
 * a node — silence is what turns an editing bug into a corrupted file nobody
 * notices until the text is already gone.
 */
import type { Mark as PMMark, Node as PMNode } from "@tiptap/pm/model";
import { SerializerCoverageError } from "../errors.ts";
import type {
  NodeSerializeContext,
  Serializer,
  SerializerRules,
} from "./types.ts";

/** Types that are structural, never written: the document wrapper and raw text
 *  (whose content the engine emits directly). */
const IMPLICITLY_COVERED = new Set(["doc", "text"]);

export function createSerializer(rules: SerializerRules): Serializer {
  const blockSeparator = rules.blockSeparator ?? "\n\n";
  const markOrder = rules.markOrder ?? [];

  const markRank = (name: string): number => {
    const i = markOrder.indexOf(name);
    return i === -1 ? Number.MAX_SAFE_INTEGER : i;
  };

  function applyMarks(text: string, marks: readonly PMMark[]): string {
    if (marks.length === 0) return text;
    // Innermost first. Left unsorted, the output would depend on the order
    // ProseMirror happens to store marks in — stable in practice, unspecified
    // in principle, and an unstable serializer makes every save a diff.
    const ordered = [...marks].sort(
      (a, b) => markRank(a.type.name) - markRank(b.type.name),
    );
    let out = text;
    for (const mark of ordered) {
      const rule = rules.marks[mark.type.name];
      if (!rule) throw new SerializerCoverageError([], [mark.type.name]);
      out = rule({ mark, attrs: mark.attrs ?? {}, inner: out });
    }
    return out;
  }

  function serializeInlineContent(node: PMNode): string {
    let out = "";
    node.forEach((child, _offset, index) => {
      if (child.isText && typeof child.text === "string") {
        out += applyMarks(child.text, child.marks);
        return;
      }
      // An inline leaf (a hard break, an inline atom) still needs its own rule.
      if (child.isLeaf) {
        out += applyMarks(runNode(child, node, index), child.marks);
        return;
      }
      out += serializeInlineContent(child);
    });
    return out;
  }

  function runNode(node: PMNode, parent: PMNode | null, index: number): string {
    const name = node.type.name;
    const rule = rules.nodes[name];
    if (!rule) throw new SerializerCoverageError([name], []);
    return rule(makeContext(node, parent, index));
  }

  function makeContext(
    node: PMNode,
    parent: PMNode | null,
    index: number,
  ): NodeSerializeContext {
    const childBlocks = (): string[] => {
      const out: string[] = [];
      node.forEach((child, _offset, i) => out.push(runNode(child, node, i)));
      return out;
    };
    return {
      node,
      attrs: node.attrs ?? {},
      parent,
      index,
      isFirstChild: index === 0,
      isLastChild: parent ? index === parent.childCount - 1 : true,
      childBlocks,
      children: () => childBlocks().join(blockSeparator),
      inline: () => serializeInlineContent(node),
      text: () => node.textContent,
      prefixLines: (value, first, rest = first) =>
        value
          .split("\n")
          .map((line, i) => (i === 0 ? first : rest) + line)
          .join("\n"),
    };
  }

  return {
    covers: [
      ...IMPLICITLY_COVERED,
      ...Object.keys(rules.nodes),
      ...Object.keys(rules.marks),
    ],
    serialize(doc: PMNode): string {
      const blocks: string[] = [];
      doc.forEach((node, _offset, index) =>
        blocks.push(runNode(node, doc, index)),
      );
      return blocks.join(blockSeparator);
    },
  };
}
