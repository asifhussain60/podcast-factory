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
import { openDepthPicker, openTagPicker } from "../editor/studio-editor-pickers";
import { useAnnotations } from "../editor/useAnnotations";
import { useSectionDepth } from "../editor/useSectionDepth";
import type { ComposeEditorBridge } from "../../../scripts/compose-editor-bridge";

// Deferred (CLI-drain) marks only — the immediate/AI actions (Arabic,
// English, Explain) live in ComposeAiTools instead, right next to the AI tools.
const DEFERRED_ACTIONS = ACTION_REGISTRY.filter(
  (a) => (a.applyMode ?? "deferred") === "deferred",
);

interface Props {
  slug: string;
  chapter: string;
  editor: Editor;
  bridge: ComposeEditorBridge;
}

export default function ComposeDetailsTab({
  slug,
  chapter,
  editor,
  bridge,
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
    activeParaIdx !== null ? (commentsRef.current.get(activeParaIdx) ?? "") : "";

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
        <h3>Mark for follow-up</h3>
        <div className="cx-details-mark-row">
          {DEFERRED_ACTIONS.map((def) => (
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
          ))}
        </div>
        {markedCount > 0 && (
          <ul className="cx-details-queue">
            {chapterActions.map((item) => (
              <li key={item.id}>
                <span>
                  {item.action_kind}
                  {item.term_text ? ` · "${item.term_text}"` : ""}
                </span>
                <button
                  type="button"
                  onClick={() => removeActionFnRef.current(item.id)}
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
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
