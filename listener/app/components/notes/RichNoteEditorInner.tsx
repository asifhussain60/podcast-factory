import { useState } from "react";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import {
  faBold,
  faItalic,
  faListOl,
  faListUl,
  type IconDefinition,
} from "@fortawesome/free-solid-svg-icons";

import { Icon } from "~/components/Icon";
import { sanitizeNote } from "~/lib/richNote";
import type { RichNoteEditorProps } from "./RichNoteEditor";

/**
 * The actual TipTap wiring. Never imported from anywhere except the single
 * `lazy(() => import(...))` in `RichNoteEditor.tsx` — see that file's
 * doc comment for why that matters.
 *
 * The toolbar is exactly four buttons, matching the four tokens
 * `~/lib/richNote` accepts (plus `p`/`br`, which every editor produces
 * without a button for them): bold, italic, bullet list, numbered list.
 * Everything else `StarterKit` offers — headings, blockquotes, code,
 * links, strikethrough, underline, horizontal rules — is turned off, so
 * the editor can never produce a token `sanitizeNote` would have to strip.
 */
export function RichNoteEditorInner({
  initialValue,
  onChange,
  placeholder,
  autoFocus,
  ariaLabel,
}: RichNoteEditorProps) {
  const [empty, setEmpty] = useState(initialValue.trim().length === 0);

  const editor = useEditor({
    // This app server-renders elsewhere in the same runtime, even though this
    // component itself only ever mounts client-side — set explicitly rather
    // than relying on Tiptap's own SSR detection.
    immediatelyRender: false,
    extensions: [
      StarterKit.configure({
        blockquote: false,
        code: false,
        codeBlock: false,
        heading: false,
        horizontalRule: false,
        link: false,
        strike: false,
        underline: false,
      }),
    ],
    content: initialValue,
    autofocus: autoFocus === true ? "end" : false,
    editorProps: {
      attributes: {
        role: "textbox",
        "aria-multiline": "true",
        "aria-label": ariaLabel,
        class: "pf-rte__editable",
      },
    },
    onUpdate: ({ editor: instance }) => {
      // An editor with nothing typed still serializes to `<p></p>` — real
      // markup, not an empty string. Collapsing that to "" here, at the one
      // place that knows what "nothing" looks like to ProseMirror, is what
      // lets every caller (and `marks.server.ts`'s own emptiness check,
      // which is a plain string comparison) keep treating "no note" as "".
      const isEmpty = instance.isEmpty;
      setEmpty(isEmpty);
      onChange(isEmpty ? "" : sanitizeNote(instance.getHTML()));
    },
  });

  return (
    <div className="pf-rte">
      <div role="toolbar" aria-label="Formatting" className="pf-rte__toolbar">
        <ToolbarButton
          label="Bold"
          icon={faBold}
          active={editor?.isActive("bold") === true}
          onClick={() => editor?.chain().focus().toggleBold().run()}
        />
        <ToolbarButton
          label="Italic"
          icon={faItalic}
          active={editor?.isActive("italic") === true}
          onClick={() => editor?.chain().focus().toggleItalic().run()}
        />
        <ToolbarButton
          label="Bullet list"
          icon={faListUl}
          active={editor?.isActive("bulletList") === true}
          onClick={() => editor?.chain().focus().toggleBulletList().run()}
        />
        <ToolbarButton
          label="Numbered list"
          icon={faListOl}
          active={editor?.isActive("orderedList") === true}
          onClick={() => editor?.chain().focus().toggleOrderedList().run()}
        />
      </div>

      <div className="pf-rte__content-wrap">
        <EditorContent editor={editor} className="pf-rte__content" />
        {empty && placeholder !== undefined ? (
          <span className="pf-rte__placeholder" aria-hidden="true">
            {placeholder}
          </span>
        ) : null}
      </div>
    </div>
  );
}

function ToolbarButton({
  label,
  icon,
  active,
  onClick,
}: {
  label: string;
  icon: IconDefinition;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      // Formatting must not steal focus from the text being edited — a mouse
      // click on a toolbar button blurs the editable region by default.
      onMouseDown={(e) => e.preventDefault()}
      onClick={onClick}
      aria-pressed={active}
      aria-label={label}
      title={label}
      // `.pf-tool` for the touch target and the existing on/off treatment
      // (`aria-pressed="true"` already tints it) — this toolbar shares the
      // vocabulary the reader toolbar and the drawer close buttons use rather
      // than inventing a second "small icon button" look.
      className="pf-tool pf-rte__toolbar-btn"
    >
      <Icon icon={icon} title={label} />
    </button>
  );
}
