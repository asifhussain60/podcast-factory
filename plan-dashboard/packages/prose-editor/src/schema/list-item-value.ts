/**
 * list-item-value.ts — carry an ordered item's STATED ordinal through the schema.
 *
 * StarterKit's listItem has no `value` attribute, so `<li value="3">` parses to
 * an item that knows only its position. Every serializer downstream then has no
 * choice but to renumber from 1 — which silently rewrites two things that are
 * content, not accidents:
 *
 *   - a list that legitimately begins at 3 (continuing an earlier one)
 *   - an author style that repeats "1." for every item
 *
 * Renumbering those invents numbering the source never claimed. The markdown
 * serializer's orderedList rule reads this attribute; without the attribute the
 * rule has nothing to read, so the two ship together.
 */
import { Extension } from "@tiptap/core";

export const ListItemValue = Extension.create({
  name: "listItemValue",
  addGlobalAttributes() {
    return [
      {
        types: ["listItem"],
        attributes: {
          value: {
            default: null,
            parseHTML: (element: HTMLElement) => {
              const raw = element.getAttribute("value");
              if (raw === null) return null;
              const n = Number(raw);
              return Number.isInteger(n) ? n : null;
            },
            renderHTML: (attrs: Record<string, unknown>) =>
              typeof attrs.value === "number"
                ? { value: String(attrs.value) }
                : {},
          },
        },
      },
    ];
  },
});
