/**
 * builtins.ts — the shipped button set.
 *
 * Every one of these acts on a StarterKit type the markdown serializer can
 * write. There is no button here for a capability the package cannot save.
 *
 * Note what is NOT here and why, because the omissions are the design:
 *   - no image / video / file button — placing media is a host concern, and a
 *     host that models figures OUTSIDE the document (so they cannot be
 *     serialized into prose) must not have that undone by a generic insert;
 *   - no colour, highlight, font or size — none has a markdown spelling;
 *   - no table — the serializer has no rule for one, so the coverage assertion
 *     would refuse the schema that admitted it.
 */
import { defineButton, defineDropdown } from "../extend/define.ts";
import type { RegisteredButton, RegisteredDropdown } from "../extend/define.ts";
import { ICONS } from "./icons.ts";

export interface BuiltinOptions {
  /**
   * Heading levels the paragraph-format control offers, and their labels.
   *
   * Configurable rather than fixed because which levels are AUTHORABLE inside a
   * body of text is a host's structural decision, not a universal one — a host
   * whose file format treats some level as a document boundary must be able to
   * withhold it, and the package has no way to know which.
   */
  headingLevels?: readonly { level: number; id: string; label: string }[];
  /** Label for "no heading". */
  bodyLabel?: string;
}

const DEFAULT_HEADING_LEVELS = [
  { level: 2, id: "h2", label: "Heading 2" },
  { level: 3, id: "h3", label: "Heading 3" },
  { level: 4, id: "h4", label: "Heading 4" },
] as const;

export function builtinButtons(
  options: BuiltinOptions = {},
): Record<string, RegisteredButton | RegisteredDropdown> {
  const levels = options.headingLevels ?? DEFAULT_HEADING_LEVELS;
  const bodyLabel = options.bodyLabel ?? "Body text";

  return {
    undo: defineButton({
      id: "undo",
      label: "Undo",
      icon: { svg: ICONS.undo ?? "" },
      shortcut: "Mod-z",
      priority: 20,
      isEnabled: (s) => s.canUndo,
      run: (api) => void api.chain().focus().undo().run(),
    }),

    redo: defineButton({
      id: "redo",
      label: "Redo",
      icon: { svg: ICONS.redo ?? "" },
      shortcut: "Mod-Shift-z",
      priority: 21,
      isEnabled: (s) => s.canRedo,
      run: (api) => void api.chain().focus().redo().run(),
    }),

    paragraphFormat: defineDropdown({
      id: "paragraphFormat",
      label: "Paragraph format",
      priority: 10,
      options: [
        { id: "body", label: bodyLabel },
        ...levels.map((l) => ({ id: l.id, label: l.label })),
      ],
      current: (s) => {
        const match = levels.find((l) => l.level === s.headingLevel);
        return match ? match.id : "body";
      },
      run: (api, optionId) => {
        if (optionId === "body") {
          void api.chain().focus().setNode("paragraph").run();
          return;
        }
        const chosen = levels.find((l) => l.id === optionId);
        // An option id that is not in the configured set is not a level to
        // guess at — a host withholds a level for a reason.
        if (!chosen) return;
        void api
          .chain()
          .focus()
          .toggleHeading({ level: chosen.level as 1 | 2 | 3 | 4 | 5 | 6 })
          .run();
      },
    }),

    bold: defineButton({
      id: "bold",
      label: "Bold",
      icon: { svg: ICONS.bold ?? "" },
      shortcut: "Mod-b",
      priority: 30,
      isActive: (s) => s.isActive("bold"),
      run: (api) => void api.chain().focus().toggleBold().run(),
    }),

    italic: defineButton({
      id: "italic",
      label: "Italic",
      icon: { svg: ICONS.italic ?? "" },
      shortcut: "Mod-i",
      priority: 31,
      isActive: (s) => s.isActive("italic"),
      run: (api) => void api.chain().focus().toggleItalic().run(),
    }),

    strike: defineButton({
      id: "strike",
      label: "Strikethrough",
      icon: { svg: ICONS.strike ?? "" },
      priority: 60,
      isActive: (s) => s.isActive("strike"),
      run: (api) => void api.chain().focus().toggleStrike().run(),
    }),

    code: defineButton({
      id: "code",
      label: "Inline code",
      icon: { svg: ICONS.code ?? "" },
      shortcut: "Mod-e",
      priority: 55,
      isActive: (s) => s.isActive("code"),
      run: (api) => void api.chain().focus().toggleCode().run(),
    }),

    link: defineButton({
      id: "link",
      label: "Link",
      icon: { svg: ICONS.link ?? "" },
      shortcut: "Mod-k",
      priority: 40,
      ariaHasPopup: "dialog",
      isActive: (s) => s.isActive("link"),
      run: async (api) => {
        // Capture BEFORE the dialog: the host's UI may be async, and the
        // selection is gone the moment focus leaves the editor.
        const anchor = api.captureAnchor();
        const existing = api.editor.getAttributes("link").href;
        const answer = await api.ui.openDialog<{ href?: string }>({
          kind: "link",
          title: "Link",
          fields: [
            {
              name: "href",
              type: "url",
              label: "Address",
              placeholder: "https://",
            },
          ],
          initial: typeof existing === "string" ? { href: existing } : {},
          context: {
            selectedText: api.getSelectedText(),
            selectedHTML: api.getSelectedHTML(),
          },
        });
        api.restoreSelection(anchor);
        if (!answer) return; // cancelled — leave the document alone
        const href = (answer.href ?? "").trim();
        if (!href) {
          void api.chain().focus().unsetMark("link").run();
          return;
        }
        void api.chain().focus().setMark("link", { href }).run();
      },
    }),

    bulletList: defineButton({
      id: "bulletList",
      label: "Bulleted list",
      icon: { svg: ICONS.bulletList ?? "" },
      priority: 45,
      isActive: (s) => s.isActive("bulletList"),
      run: (api) => void api.chain().focus().toggleBulletList().run(),
    }),

    orderedList: defineButton({
      id: "orderedList",
      label: "Numbered list",
      icon: { svg: ICONS.orderedList ?? "" },
      priority: 46,
      isActive: (s) => s.isActive("orderedList"),
      run: (api) => void api.chain().focus().toggleOrderedList().run(),
    }),

    blockquote: defineButton({
      id: "blockquote",
      label: "Quote",
      icon: { svg: ICONS.blockquote ?? "" },
      priority: 50,
      isActive: (s) => s.isActive("blockquote"),
      run: (api) => void api.chain().focus().toggleBlockquote().run(),
    }),

    codeBlock: defineButton({
      id: "codeBlock",
      label: "Code block",
      icon: { svg: ICONS.codeBlock ?? "" },
      priority: 70,
      isActive: (s) => s.isActive("codeBlock"),
      run: (api) => void api.chain().focus().toggleCodeBlock().run(),
    }),

    horizontalRule: defineButton({
      id: "horizontalRule",
      label: "Divider",
      icon: { svg: ICONS.horizontalRule ?? "" },
      priority: 65,
      run: (api) => void api.chain().focus().setHorizontalRule().run(),
    }),

    clearFormatting: defineButton({
      id: "clearFormatting",
      label: "Clear formatting",
      icon: { svg: ICONS.clearFormatting ?? "" },
      priority: 80,
      run: (api) => void api.chain().focus().unsetAllMarks().clearNodes().run(),
    }),
  };
}

/** A sensible full bar. `|` is a separator. */
export const TOOLBAR_FULL = [
  "undo",
  "redo",
  "|",
  "paragraphFormat",
  "|",
  "bold",
  "italic",
  "code",
  "link",
  "|",
  "bulletList",
  "orderedList",
  "blockquote",
  "|",
  "horizontalRule",
  "clearFormatting",
] as const;

/** Marks only — the default set for a selection bubble. */
export const TOOLBAR_INLINE = ["bold", "italic", "code", "link"] as const;
