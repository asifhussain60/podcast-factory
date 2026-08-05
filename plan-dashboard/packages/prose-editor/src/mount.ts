/**
 * mount.ts — the greenfield entry point.
 *
 * Builds an Editor from the package's base schema plus whatever the host
 * registered, then hands it to `attach()`. Everything the guarantee depends on
 * lives in attach, so the two paths cannot diverge.
 */
import { Editor } from "@tiptap/core";
import type { Extensions } from "@tiptap/core";
import { attach } from "./attach.ts";
import type { AttachOptions } from "./attach.ts";
import { baseExtensions } from "./schema/base-extensions.ts";
import type { BaseExtensionOptions } from "./schema/base-extensions.ts";
import type { ProseEditor } from "./types.ts";

export interface MountOptions extends AttachOptions {
  /** Seed HTML. Parsed through the schema, so anything the schema cannot
   *  represent is dropped HERE, visibly, rather than silently at save. */
  content?: string;
  editable?: boolean;
  autofocus?: boolean | "start" | "end";
  schema?: BaseExtensionOptions;
  /**
   * Raw TipTap extensions. Named for what it is: anything here that widens the
   * schema is still subject to the coverage assertion in attach, so the escape
   * hatch cannot be used to smuggle in an unserializable type.
   */
  unsafeTiptapExtensions?: Extensions;
  /** Attributes on the contenteditable element. */
  editorAttributes?: Record<string, string>;
}

export function mount(
  element: HTMLElement,
  options: MountOptions,
): ProseEditor & { editor: Editor } {
  const editor = new Editor({
    element,
    extensions: baseExtensions(
      options.schema ?? {},
      options.extensions ?? [],
      options.unsafeTiptapExtensions ?? [],
    ),
    content: options.content ?? "",
    editable: options.editable ?? true,
    autofocus: options.autofocus ?? false,
    editorProps: {
      attributes: {
        class: "rte-prose",
        ...(options.editorAttributes ?? {}),
      },
    },
  });

  const attached = attach(editor, options);

  return {
    ...attached,
    editor,
    destroy() {
      attached.destroy();
      editor.destroy();
    },
  };
}
