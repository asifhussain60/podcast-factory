/**
 * base-extensions.ts — the schema `mount()` builds for a greenfield host.
 *
 * Opinionated, and the opinions are all the same opinion: a type is in the
 * schema only if the serializer can write it. StarterKit's defaults do not meet
 * that bar, so they are narrowed here rather than left for each host to discover
 * the hard way.
 *
 * A host that already owns its editor uses `attach()` and none of this applies —
 * its schema is its own business, and the coverage assertion is what holds it
 * honest.
 */
import StarterKit from "@tiptap/starter-kit";
import type { Extensions } from "@tiptap/core";
import { toTiptapMark, toTiptapNode } from "../extend/to-tiptap.ts";
import { ListItemValue } from "./list-item-value.ts";
import type { RegisteredExtension } from "../extend/define.ts";

export interface BaseExtensionOptions {
  /**
   * Allow a hard break. Default false: the markdown serializer's default
   * `hardBreak: "error"` has no spelling for one, so admitting the node without
   * also choosing a spelling means Shift+Enter produces something the save
   * cannot write. Enable both together or neither.
   */
  hardBreak?: boolean;
  /** Allow underline. Default false — markdown has no underline syntax, so the
   *  mark would be dropped on save while Mod-U kept cheerfully applying it. */
  underline?: boolean;
  /** Allow code blocks. Default true. */
  codeBlock?: boolean;
  /** Allow strikethrough. Default true. */
  strike?: boolean;
}

export function baseExtensions(
  options: BaseExtensionOptions = {},
  registered: readonly RegisteredExtension[] = [],
  extra: Extensions = [],
): Extensions {
  return [
    StarterKit.configure({
      ...(options.hardBreak === true ? {} : { hardBreak: false }),
      ...(options.underline === true ? {} : { underline: false }),
      ...(options.codeBlock === false ? { codeBlock: false } : {}),
      ...(options.strike === false ? { strike: false } : {}),
      // Links are DELIBERATE. autolink turns a typed domain into a link nobody
      // authored; openOnClick navigates away from an editor mid-edit, taking
      // whatever the host's autosave had not yet flushed with it.
      link: { autolink: false, linkOnPaste: false, openOnClick: false },
    }),
    // Ships WITH the orderedList serializer rule that reads it — the rule has
    // nothing to honour without the attribute, and the attribute is pointless
    // without the rule.
    ListItemValue,
    ...registered.map((ext) =>
      ext.kind === "node" ? toTiptapNode(ext.def) : toTiptapMark(ext.def),
    ),
    ...extra,
  ];
}
