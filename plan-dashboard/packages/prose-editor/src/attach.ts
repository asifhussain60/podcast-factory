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
}

const WORD_RE = /\S+/g;

export function attach(editor: Editor, options: AttachOptions): ProseEditor {
  const serializer = resolveSerializer(options);

  // The gate. Runs against the FINAL schema — not the declared extension list —
  // so an extension the host added by any route is still covered by it.
  assertSerializerTotal(editor.schema, serializer.covers);

  const ui = options.ui ?? createFallbackUiHost();
  const eventTarget = options.eventTarget ?? (editor.view.dom as HTMLElement);

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

  let destroyed = false;

  return {
    editor,
    api,
    toolbarEl: null,
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
      // The editor may already be gone; its own teardown removes listeners.
      try {
        editor.off("transaction", onTransaction as never);
      } catch {
        /* already torn down */
      }
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
