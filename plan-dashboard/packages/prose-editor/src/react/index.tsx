/**
 * react/index.tsx — the React wrapper.
 *
 * Thin on purpose: it owns lifecycle and nothing else. Every guarantee lives in
 * `attach`, so the React path and the vanilla path cannot diverge — a bug fixed
 * in one is fixed in both because there is only one of it.
 *
 * React is an OPTIONAL peer dependency. A vanilla consumer importing the package
 * root never reaches this file and never acquires a React requirement.
 */
import { useEffect, useImperativeHandle, useRef, useState } from "react";
import type { Ref } from "react";
import { mount } from "../mount.ts";
import type { MountOptions } from "../mount.ts";
import type { ProseEditor } from "../types.ts";

export interface ProseEditorHandle {
  serialize(): string;
  focus(): void;
  readonly editor: ProseEditor["editor"] | null;
}

export interface ProseEditorProps extends Omit<MountOptions, "content"> {
  /** Seed HTML. Used ONCE, on mount: this is an uncontrolled editor, because a
   *  controlled one would re-seed on every keystroke and fight the user. */
  initialContent?: string;
  onChange?: (serialized: string) => void;
  className?: string;
  /** Where the toolbar goes. Omit and it is placed above the editor. */
  toolbarRef?: Ref<HTMLDivElement>;
  ref?: Ref<ProseEditorHandle>;
}

export function ProseEditor({
  initialContent = "",
  onChange,
  className,
  ref,
  ...options
}: ProseEditorProps) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const toolbarSlotRef = useRef<HTMLDivElement | null>(null);
  const editorRef = useRef<ProseEditor | null>(null);
  const [error, setError] = useState<Error | null>(null);

  // The options object is recreated on every render by any caller using object
  // literals, so it must NOT be an effect dependency — it would tear down and
  // rebuild the editor on each render, losing the caret and the undo history.
  const optionsRef = useRef(options);
  optionsRef.current = options;
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    let instance: ProseEditor | null = null;
    try {
      instance = mount(host, {
        ...optionsRef.current,
        content: initialContent,
      });
    } catch (err) {
      // A coverage failure is a programming error the developer must see, not
      // something to swallow — surface it instead of rendering a dead box.
      setError(err as Error);
      return;
    }
    editorRef.current = instance;

    if (instance.toolbarEl && toolbarSlotRef.current) {
      toolbarSlotRef.current.append(instance.toolbarEl);
    }
    if (instance.bubbleEl) host.append(instance.bubbleEl);

    const off = instance.editor.on("update", () =>
      onChangeRef.current?.(instance!.serialize()),
    );
    void off;

    return () => {
      instance?.destroy();
      editorRef.current = null;
    };
    // Mount once. StrictMode's double-invoke is handled by the cleanup above
    // tearing the first instance down before the second is built.
  }, [initialContent]);

  useImperativeHandle(
    ref,
    () => ({
      serialize: () => editorRef.current?.serialize() ?? "",
      focus: () => editorRef.current?.editor.commands.focus(),
      get editor() {
        return editorRef.current?.editor ?? null;
      },
    }),
    [],
  );

  if (error) throw error;

  return (
    <div className={className}>
      <div ref={toolbarSlotRef} />
      <div ref={hostRef} />
    </div>
  );
}
