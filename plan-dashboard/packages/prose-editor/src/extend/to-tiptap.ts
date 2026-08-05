/**
 * to-tiptap.ts — turn a CustomNodeDef / CustomMarkDef into a TipTap extension.
 *
 * One direction only. The host describes its type once, in one object, and this
 * derives the schema contribution from it — so the parse rule, the render and
 * the serializer rule cannot end up describing three different things.
 */
import { Mark, Node } from "@tiptap/core";
import type { AnyExtension } from "@tiptap/core";
import type { AttrMap } from "../types.ts";
import type { AttrDef, CustomMarkDef, CustomNodeDef } from "./define.ts";

function mapAttrs(attrs: Record<string, AttrDef> | undefined): AttrMap {
  if (!attrs) return {};
  const out: AttrMap = {};
  for (const [key, def] of Object.entries(attrs)) {
    out[key] = {
      default: def.default,
      keepOnSplit: def.keepOnSplit ?? false,
      ...(def.parseHTML ? { parseHTML: def.parseHTML } : {}),
      ...(def.renderHTML ? { renderHTML: def.renderHTML } : {}),
    };
  }
  return out;
}

export function toTiptapNode(def: CustomNodeDef): AnyExtension {
  return Node.create({
    name: def.name,
    group: def.group ?? "block",
    ...(def.content !== undefined ? { content: def.content } : {}),
    ...(def.inline !== undefined ? { inline: def.inline } : {}),
    ...(def.atom !== undefined ? { atom: def.atom } : {}),
    ...(def.draggable !== undefined ? { draggable: def.draggable } : {}),
    ...(def.selectable !== undefined ? { selectable: def.selectable } : {}),
    ...(def.defining !== undefined ? { defining: def.defining } : {}),
    addAttributes: () => mapAttrs(def.attrs),
    parseHTML: () => [...def.parseHTML],
    renderHTML: ({ node }) => def.renderHTML({ attrs: node.attrs ?? {} }),
  }) as AnyExtension;
}

export function toTiptapMark(def: CustomMarkDef): AnyExtension {
  return Mark.create({
    name: def.name,
    ...(def.inclusive !== undefined ? { inclusive: def.inclusive } : {}),
    ...(def.excludes !== undefined ? { excludes: def.excludes } : {}),
    ...(def.spanning !== undefined ? { spanning: def.spanning } : {}),
    addAttributes: () => mapAttrs(def.attrs),
    parseHTML: () => [...def.parseHTML],
    renderHTML: ({ mark }) => def.renderHTML({ attrs: mark.attrs ?? {} }),
  }) as AnyExtension;
}
