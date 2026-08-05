/**
 * attach.ts — bind the package to an Editor the HOST already owns.
 *
 * This is the primary entry point, and the asymmetry is deliberate. A host with
 * an existing editor keeps ownership of its schema, its editor props and its
 * extension list; the package contributes UI and reads state. That means a
 * package release can never widen the host's schema, never replace a drop or
 * paste handler the host installed for its own reasons, and never change what
 * the host's serializer is asked to write.
 *
 * `mount()` is the greenfield convenience: it builds an Editor, then calls this.
 */
import type { Editor } from "@tiptap/core";
import { DOMSerializer } from "@tiptap/pm/model";
import type { Mapping } from "@tiptap/pm/transform";
import { assertSerializerTotal } from "./serialize/coverage.ts";
import { createMarkdownSerializer } from "./serialize/markdown.ts";
import type { Serializer, SerializerSpec } from "./serialize/types.ts";
import type {
  EditorApi,
  ProseEditor,
  SelectionAnchor,
  SelectionState,
  UiHost,
} from "./types.ts";
import { createFallbackUiHost } from "./ui/fallback-ui-host.ts";
import { createToolbar } from "./toolbar/toolbar.ts";
import type { Toolbar, ToolbarOptions } from "./toolbar/toolbar.ts";
import { createBubble } from "./toolbar/bubble.ts";
import type { Bubble, BubbleOptions } from "./toolbar/bubble.ts";
import { builtinButtons } from "./toolbar/builtins.ts";
import { createPasteSanitizer, pasteSanitizerKey } from "./input/paste.ts";
import type { PasteOptions } from "./input/paste.ts";
import {
  bindingsFromButtons,
  createShortcutRegistry,
} from "./input/shortcuts.ts";
import type { ShortcutBinding } from "./input/shortcuts.ts";
import type { RegisteredExtension } from "./extend/define.ts";

export interface AttachOptions {
  /**
   * REQUIRED. There is deliberately no default: a default serializer is the
   * same silent-loss trap this package exists to close, moved up to the API.
   */
  serializer: SerializerSpec;
  /** Custom nodes and marks already present in the editor's schema. Listed here
   *  so their serializer rules and paste allowances are registered. */
  extensions?: readonly RegisteredExtension[];
  ui?: UiHost;
  /** Element CustomEvents are fired on. Defaults to the editor's own DOM. */
  eventTarget?: HTMLElement;
  /** Build a toolbar. `false` (the default) builds none — a host may want only
   *  the serializer guarantee and its own chrome. */
  toolbar?: ToolbarOptions | false;
  /** Build a selection bubble. `false` (the default) builds none. The host
   *  places `bubbleEl` itself. */
  bubble?: BubbleOptions | false;
  /** Install the paste sanitizer. `false` disables it. Default: on, in
   *  "schema" mode. */
  paste?: PasteOptions | false;
  /**
   * Keyboard shortcuts. `true` (the default) binds the ones declared on the
   * built-in buttons; a list adds host bindings on top. `false` binds none.
   *
   * A duplicate combination THROWS rather than last-wins — silent last-wins is
   * how a shortcut ends up doing something other than its tooltip says.
   */
  shortcuts?: boolean | readonly ShortcutBinding[];
}

const WORD_RE = /\S+/g;

export function attach(editor: Editor, options: AttachOptions): ProseEditor {
  const serializer = resolveSerializer(options);

  // The gate. Runs against the FINAL schema — not the declared extension list —
  // so an extension the host added by any route is still covered by it.
  assertSerializerTotal(editor.schema, serializer.covers);

  const ui = options.ui ?? createFallbackUiHost();
  const eventTarget = options.eventTarget ?? (editor.view.dom as HTMLElement);

  /** Every listener registered here, so tearing down and re-attaching (which a
   *  host does whenever it swaps the document being edited) cannot leave one
   *  firing against an editor that is already gone. */
  const cleanups: Array<() => void> = [];

  // Position mapping for anchors. Collected ONLY while an anchor is outstanding,
  // so a long editing session does not accumulate a mapping per keystroke.
  let anchorsOutstanding = 0;
  let mappings: Mapping[] = [];
  const onTransaction = ({
    transaction,
  }: {
    transaction: { docChanged: boolean; mapping: Mapping };
  }): void => {
    if (anchorsOutstanding > 0 && transaction.docChanged) {
      mappings.push(transaction.mapping);
    }
  };
  editor.on("transaction", onTransaction as never);
  cleanups.push(() => editor.off("transaction", onTransaction as never));

  const mapPos = (pos: number, since: number): number => {
    let p = pos;
    for (let i = since; i < mappings.length; i++) {
      const m = mappings[i];
      if (m) p = m.map(p);
    }
    return p;
  };

  const releaseAnchor = (): void => {
    anchorsOutstanding = Math.max(0, anchorsOutstanding - 1);
    if (anchorsOutstanding === 0) mappings = [];
  };

  function readState(): SelectionState {
    const { state } = editor;
    const { from, to, empty } = state.selection;
    const activeMarks = new Set<string>();
    for (const name of Object.keys(state.schema.marks)) {
      if (editor.isActive(name)) activeMarks.add(name);
    }
    const activeNodes = new Set<string>();
    for (const name of Object.keys(state.schema.nodes)) {
      if (editor.isActive(name)) activeNodes.add(name);
    }
    let headingLevel: number | null = null;
    for (let level = 1; level <= 6; level++) {
      if (editor.isActive("heading", { level })) {
        headingLevel = level;
        break;
      }
    }
    return {
      empty,
      text: state.doc.textBetween(from, to, " "),
      activeMarks,
      activeNodes,
      headingLevel,
      canUndo: editor.can().undo(),
      canRedo: editor.can().redo(),
      editable: editor.isEditable,
      isActive: (name, attrs) =>
        attrs ? editor.isActive(name, attrs) : editor.isActive(name),
    };
  }

  const api: EditorApi = {
    editor,
    get state() {
      return readState();
    },
    chain: () => editor.chain(),
    getSelectedText: () => {
      const { from, to } = editor.state.selection;
      return editor.state.doc.textBetween(from, to, " ");
    },
    getSelectedHTML: () => {
      const { from, to } = editor.state.selection;
      const slice = editor.state.doc.slice(from, to);
      const doc = eventTarget.ownerDocument;
      const div = doc.createElement("div");
      div.appendChild(
        DOMSerializer.fromSchema(editor.schema).serializeFragment(
          slice.content,
          { document: doc },
        ),
      );
      return div.innerHTML;
    },
    insertNode: (name, attrs, content) =>
      editor
        .chain()
        .insertContent({ type: name, attrs: attrs ?? {}, content })
        .run(),
    toggleMark: (name, attrs) => editor.chain().toggleMark(name, attrs).run(),
    unsetMark: (name) => editor.chain().unsetMark(name).run(),
    captureAnchor: () => {
      anchorsOutstanding += 1;
      const { from, to } = editor.state.selection;
      return { from, to, stepsAtCapture: mappings.length };
    },
    insertAtAnchor: (anchor, name, attrs, content) => {
      const from = mapPos(anchor.from, anchor.stepsAtCapture);
      const to = mapPos(anchor.to, anchor.stepsAtCapture);
      releaseAnchor();
      return editor
        .chain()
        .insertContentAt(
          { from, to },
          { type: name, attrs: attrs ?? {}, content },
        )
        .run();
    },
    restoreSelection: (anchor: SelectionAnchor) => {
      const from = mapPos(anchor.from, anchor.stepsAtCapture);
      const to = mapPos(anchor.to, anchor.stepsAtCapture);
      releaseAnchor();
      editor.chain().focus().setTextSelection({ from, to }).run();
    },
    ui,
    serialize: () => serializer.serialize(editor.state.doc),
    emit: (name, detail) => {
      eventTarget.dispatchEvent(
        new CustomEvent(name, { detail, bubbles: true }),
      );
    },
  };

  // Built AFTER `api`, because every control reads state through it.
  let toolbar: Toolbar | null = null;
  if (options.toolbar) {
    toolbar = createToolbar(api, {
      document: eventTarget.ownerDocument,
      ...options.toolbar,
    });
    // Repaint pressed/disabled state on anything that could change it. The
    // toolbar is a pure OBSERVER here: it never calls focus() in response, or
    // it would fire the very event it is reacting to.
    const repaint = () => toolbar?.refresh();
    editor.on("selectionUpdate", repaint);
    editor.on("transaction", repaint);
    editor.on("focus", repaint);
    editor.on("blur", repaint);
    cleanups.push(() => {
      editor.off("selectionUpdate", repaint);
      editor.off("transaction", repaint);
      editor.off("focus", repaint);
      editor.off("blur", repaint);
    });
  }

  // ── Selection bubble ───────────────────────────────────────────────────────
  let bubble: Bubble | null = null;
  if (options.bubble) {
    bubble = createBubble(api, {
      document: eventTarget.ownerDocument,
      ...options.bubble,
    });
    const onSelection = () => bubble?.update();
    editor.on("selectionUpdate", onSelection);
    editor.on("transaction", onSelection);
    editor.on("blur", onSelection);
    cleanups.push(() => {
      editor.off("selectionUpdate", onSelection);
      editor.off("transaction", onSelection);
      editor.off("blur", onSelection);
    });
    bubble.update();
  }

  // ── Paste sanitizer ────────────────────────────────────────────────────────
  // Registered as a ProseMirror plugin using `transformPastedHTML`, which is a
  // DIFFERENT hook from `handleDrop` — so a host's own drop handling (the kind
  // that stops a dragged payload being inserted as prose) cannot be clobbered
  // by installing this.
  if (options.paste !== false) {
    const allowances = (options.extensions ?? [])
      .map((e) => e.def.pasteAllow)
      .filter((a): a is NonNullable<typeof a> => Boolean(a));
    const plugin = createPasteSanitizer({
      ...(options.paste ?? {}),
      extensionAllowances: [
        ...allowances,
        ...((options.paste || {}).extensionAllowances ?? []),
      ],
    });
    editor.registerPlugin(plugin);
    cleanups.push(() => {
      try {
        editor.unregisterPlugin(pasteSanitizerKey);
      } catch {
        /* editor already torn down */
      }
    });
  }

  // ── Shortcuts ──────────────────────────────────────────────────────────────
  if (options.shortcuts !== false) {
    const registry = createShortcutRegistry();
    const builtins = builtinButtons((options.toolbar || {}).builtins ?? {});
    const buttonDefs = Object.values(builtins)
      .filter((c) => c.kind === "button")
      .map((c) => c.def);
    for (const binding of bindingsFromButtons(buttonDefs)) {
      registry.register(binding);
    }
    if (Array.isArray(options.shortcuts)) {
      for (const binding of options.shortcuts) registry.register(binding);
    }
    cleanups.push(registry.listen(eventTarget, api));
  }

  let destroyed = false;

  return {
    editor,
    api,
    toolbarEl: toolbar?.el ?? null,
    bubbleEl: bubble?.el ?? null,
    serialize: () => serializer.serialize(editor.state.doc),
    counts: () => {
      const text = editor.state.doc.textContent;
      return {
        words: (text.match(WORD_RE) ?? []).length,
        characters: text.length,
      };
    },
    destroy() {
      if (destroyed) return;
      destroyed = true;
      mappings = [];
      toolbar?.destroy();
      bubble?.destroy();
      // The editor may already be gone; its own teardown removes listeners, so
      // a second removal here can throw and must not.
      for (const fn of cleanups) {
        try {
          fn();
        } catch {
          /* already torn down */
        }
      }
      cleanups.length = 0;
    },
  };
}

function resolveSerializer(options: AttachOptions): Serializer {
  const spec = options.serializer;
  if (spec.kind === "custom") {
    return { serialize: spec.serialize, covers: spec.covers };
  }
  const custom = collectCustomRules(options.extensions ?? []);
  return createMarkdownSerializer({
    ...(spec.options ?? {}),
    rules: {
      nodes: { ...custom.nodes, ...(spec.rules?.nodes ?? {}) },
      marks: { ...custom.marks, ...(spec.rules?.marks ?? {}) },
      ...(spec.rules?.markOrder ? { markOrder: spec.rules.markOrder } : {}),
      ...(spec.rules?.blockSeparator
        ? { blockSeparator: spec.rules.blockSeparator }
        : {}),
    },
  });
}

/** Every registered node and mark contributes its `toOutput` — which is why a
 *  registered type can never be uncovered. */
function collectCustomRules(extensions: readonly RegisteredExtension[]) {
  const nodes: Record<string, never> = {} as never;
  const marks: Record<string, never> = {} as never;
  for (const ext of extensions) {
    if (ext.kind === "node") {
      (nodes as Record<string, unknown>)[ext.name] = ext.def.toOutput;
    } else {
      (marks as Record<string, unknown>)[ext.name] = ext.def.toOutput;
    }
  }
  return { nodes, marks };
}
