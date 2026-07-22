/**
 * ComposeDetailsTab.tsx — per-paragraph comments (useAnnotations), deferred
 * action-item marks (useAnnotations), and section depth/tag summary
 * (useSectionDepth), reusing the SAME hooks StudioEditor.tsx uses, fed the
 * Book Composer's own vanilla TipTap editor via the compose-editor-bridge.
 * This is Compose's new 5th (last) inspector tab.
 *
 * Mounted imperatively (React 19 createRoot) by book-composer.ts alongside
 * ComposeAiTools — see that file's header comment for why (editor/chapter
 * props change on every chapter switch, which a client:only island can't
 * receive after mount).
 */
import { useCallback, useEffect, useLayoutEffect, useState } from "react";
import type { Editor } from "@tiptap/core";

import { ACTION_REGISTRY } from "../editor/studio-editor-constants";
import {
  openDepthPicker,
  openTagPicker,
} from "../editor/studio-editor-pickers";
import { useAnnotations } from "../editor/useAnnotations";
import { useSectionDepth } from "../editor/useSectionDepth";
import type { ComposeEditorBridge } from "../../../scripts/compose-editor-bridge";

// Deferred (queued) marks only — the immediate/AI actions (Arabic, English,
// Explain) live in ComposeAiTools instead, right next to the AI tools.
const DEFERRED_ACTIONS = ACTION_REGISTRY.filter(
  (a) => (a.applyMode ?? "deferred") === "deferred",
);
const DEFERRED_BY_KIND = Object.fromEntries(
  DEFERRED_ACTIONS.map((a) => [a.kind, a]),
);

// Outcome grouping for the mark buttons (2026-07-22, Asif-approved reorg): a
// wall of nine equal buttons told the reader nothing about what each family
// is FOR. Text marks are runnable from the queue today (through the
// Composer's own immediate-AI machinery); the knowledge/visual marks wait for
// a pipeline drain pass that does not exist yet — and the UI says so plainly
// instead of overpromising.
const MARK_GROUPS: { name: string; kinds: string[] }[] = [
  { name: "Text", kinds: ["rewrite", "expand", "condense", "simplify"] },
  { name: "Knowledge", kinds: ["etymology", "define", "xref", "addcorpus"] },
  { name: "Visual", kinds: ["visualize"] },
];

/** Compose-side operations the queue calls back into (book-composer.ts). */
export interface ComposeQueueOps {
  /** Scroll to and select the mark's anchored text in the editor. */
  jumpTo: (anchor: string) => void;
  /** Run the matching immediate AI action on the anchored text; `onApplied`
   *  fires when the human ACCEPTS a result (the mark then clears itself). */
  runNow: (kind: string, anchor: string, onApplied: () => void) => void;
  /** Mark kinds runNow can serve (the text transforms). */
  runnableKinds: readonly string[];
}

interface Props {
  slug: string;
  chapter: string;
  editor: Editor;
  bridge: ComposeEditorBridge;
  queueOps?: ComposeQueueOps;
}

export default function ComposeDetailsTab({
  slug,
  chapter,
  editor,
  bridge,
  queueOps,
}: Props) {
  const [, setTick] = useState(0);
  const refresh = useCallback(() => setTick((t) => t + 1), []);
  const [activeParaIdx, setActiveParaIdx] = useState<number | null>(null);
  const [selection, setSelection] = useState("");

  // Track the caret's paragraph (comments/marks) and selected text (term marks).
  useEffect(() => {
    const onSelUpdate = () => {
      const { from, to } = editor.state.selection;
      setSelection(editor.state.doc.textBetween(from, to, " ").trim());
      const $head = editor.state.selection.$head;
      let paraIdx = -1;
      let i = 0;
      editor.state.doc.forEach((_node, offset) => {
        const size = editor.state.doc.child(i)?.nodeSize ?? 0;
        if ($head.pos >= offset && $head.pos < offset + size) paraIdx = i;
        i++;
      });
      setActiveParaIdx(paraIdx >= 0 ? paraIdx : null);
    };
    editor.on("selectionUpdate", onSelUpdate);
    onSelUpdate();
    return () => {
      editor.off("selectionUpdate", onSelUpdate);
    };
  }, [editor]);

  // The bridge's fields are plain mutable ref boxes shared with the vanilla
  // decoration plugin. Naming them as locals here makes that ownership explicit
  // to reader and lint alike, and keeps the writes below off the prop object.
  const {
    editorRef,
    actionsRef: bridgeActionsRef,
    removeActionFnRef: bridgeRemoveActionFnRef,
    sectionDepthsRef: bridgeSectionDepthsRef,
    sectionTagsRef: bridgeSectionTagsRef,
    saveSectionDepthRef: bridgeSaveSectionDepthRef,
  } = bridge;

  const {
    commentsRef,
    refreshComments,
    persistComment,
    actionsRef,
    removeActionFnRef,
    markedCount,
    chapterActions,
    stampAction,
  } = useAnnotations({
    slug,
    chapter,
    editor,
    editorRef,
    activeParaIdx,
    isReadOnlyStage: false,
    selection,
    refresh,
  });

  const { sectionDepths, sectionTagsMap, saveSectionDepthRef } =
    useSectionDepth(slug, chapter, editorRef);

  // Publish this tab's live state into the shared bridge so the vanilla
  // decoration plugin (which reads these boxes from a PM widget mousedown)
  // never sees a stale value.
  //
  // These were render-phase assignments. Mutating a caller-owned object during
  // render is unsafe under concurrent rendering — React may render without
  // committing, leaving the bridge pointing at state from a discarded pass —
  // and the compiler lint rejects it. A layout effect keeps the observable
  // timing: the only reader is a widget mousedown, which cannot fire before
  // commit, and layout effects run before paint.
  useLayoutEffect(() => {
    editorRef.current = editor;
    bridgeActionsRef.current = actionsRef.current;
    bridgeRemoveActionFnRef.current = removeActionFnRef.current;
    bridgeSectionDepthsRef.current = sectionDepths;
    bridgeSectionTagsRef.current = sectionTagsMap;
    bridgeSaveSectionDepthRef.current = saveSectionDepthRef.current;
  });

  const activeComment =
    activeParaIdx !== null
      ? (commentsRef.current.get(activeParaIdx) ?? "")
      : "";

  const sectionTitles = useCallback((): string[] => {
    const titles: string[] = [];
    editor.state.doc.forEach((node) => {
      if (node.type.name === "heading" && node.attrs.level === 2)
        titles.push(node.textContent);
    });
    return titles;
  }, [editor]);

  const sections = sectionTitles();

  return (
    <div className="cx-details-tab">
      <section className="cx-details-block">
        <h3>
          Mark for follow-up
          {markedCount > 0 && (
            <span className="cx-count-badge">{markedCount}</span>
          )}
        </h3>
        {activeParaIdx === null && (
          <p className="cx-details-hint">
            Click into a paragraph (or select a phrase) to mark it.
          </p>
        )}
        {MARK_GROUPS.map((group) => (
          <div className="cx-mark-group" key={group.name}>
            <span className="cx-mark-group-name">{group.name}</span>
            <div className="cx-details-mark-row">
              {group.kinds.map((kind) => {
                const def = DEFERRED_BY_KIND[kind];
                if (!def) return null;
                return (
                  <button
                    key={def.kind}
                    type="button"
                    className="cx-btn-mark"
                    title={def.hint}
                    disabled={activeParaIdx === null}
                    onClick={() =>
                      stampAction(def, def.scope === "term" && !!selection)
                    }
                  >
                    <i className={`fa-solid ${def.icon}`} aria-hidden="true" />{" "}
                    {def.label}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
        <p className="cx-details-hint">
          Text marks can be run from the queue below. Knowledge and Visual
          marks are stored for a future pipeline pass — they wait until that
          pass exists.
        </p>
        {markedCount > 0 && (
          <ul className="cx-details-queue">
            {chapterActions.map((item) => {
              const def = DEFERRED_BY_KIND[item.action_kind];
              const snippet = item.term_text || item.anchor_text;
              const runnable = queueOps?.runnableKinds.includes(
                item.action_kind,
              );
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    className="cx-queue-jump"
                    title="Jump to the marked text"
                    onClick={() => queueOps?.jumpTo(item.anchor_text)}
                  >
                    <strong>{def?.label ?? item.action_kind}</strong>
                    {snippet ? ` · ${snippet.slice(0, 60)}` : ""}
                  </button>
                  {runnable && queueOps && (
                    <button
                      type="button"
                      className="cx-queue-run"
                      title="Run this mark now with AI; accepting the result clears it"
                      onClick={() =>
                        queueOps.runNow(item.action_kind, item.anchor_text, () =>
                          removeActionFnRef.current(item.id),
                        )
                      }
                    >
                      Run now
                    </button>
                  )}
                  <button
                    type="button"
                    className="cx-queue-remove"
                    onClick={() => removeActionFnRef.current(item.id)}
                  >
                    Remove
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <section className="cx-details-block">
        <h3>Comment</h3>
        {activeParaIdx === null ? (
          <p className="cx-details-hint">
            Click into a paragraph to leave a comment.
          </p>
        ) : (
          <textarea
            className="cx-details-comment"
            placeholder="Comment on this paragraph…"
            value={activeComment}
            onChange={(e) => {
              commentsRef.current.set(activeParaIdx, e.target.value);
              refreshComments();
            }}
            onBlur={(e) => persistComment(activeParaIdx, e.target.value)}
          />
        )}
      </section>

      <section className="cx-details-block">
        <h3>Section depth &amp; tags</h3>
        {sections.length === 0 ? (
          <p className="cx-details-hint">
            This chapter has no subsection headings to tag.
          </p>
        ) : (
          <ul className="cx-details-sections">
            {sections.map((title, ord) => {
              const depth = sectionDepths[ord];
              const tags = sectionTagsMap[ord] ?? [];
              return (
                <li key={ord}>
                  <span className="cx-details-section-title">{title}</span>
                  <button
                    type="button"
                    className="cx-btn-depth"
                    onClick={(e) =>
                      openDepthPicker(
                        e.currentTarget,
                        saveSectionDepthRef.current,
                        ord,
                        title,
                        depth,
                        bridge.depthLevels,
                        tags,
                      )
                    }
                  >
                    {depth ?? "∅ depth"}
                  </button>
                  <button
                    type="button"
                    className="cx-btn-tags"
                    onClick={(e) =>
                      openTagPicker(
                        e.currentTarget,
                        saveSectionDepthRef.current,
                        ord,
                        title,
                        tags,
                        depth ?? "",
                      )
                    }
                  >
                    {tags.length ? tags.join(", ") : "+ tags"}
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}
