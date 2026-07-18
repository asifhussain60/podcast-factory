/**
 * useAnnotations — the per-paragraph annotation cluster: paragraph comments
 * (ref-mirrored for the PM plugin, persisted via the annotations API) and
 * deferred AI action-item marks (per-chapter load, optimistic stamp/remove
 * with server reconciliation, plus the render-derived queue list). Extracted
 * verbatim from StudioEditor.tsx (R2 pass 2 — one hook per commit).
 *
 * Contract notes (load-bearing, preserved exactly):
 *  - commentsRef/actionsRef are refs so PM widgets built outside React always
 *    see the latest values, mirrored to state (setCommentsKey/setActionsKey)
 *    purely so the inspector panel re-renders.
 *  - removeActionFnRef is assigned during render (not in an effect), exactly
 *    as the component assigned it before extraction, so the inline
 *    per-paragraph badge's mousedown never sees a stale closure between
 *    render and effect flush. (react-hooks/refs is warn-level for this
 *    deliberate pattern — same as useSectionDepth's mirror refs.)
 *  - The action-items loader clears actionsRef synchronously before fetching
 *    so the previous chapter's marks never flash on the new chapter; both
 *    loaders and every writer (PATCH/POST/DELETE) are fire-and-forget,
 *    offline-friendly.
 *  - stampAction toggles: an identical existing mark is removed instead. A
 *    negative temp id marks optimistic-only items (removeAction never DELETEs
 *    them server-side) until the POST response reconciles the real id.
 *  - useStageApproval consumes commentsRef (approval saves the comments) —
 *    the component calls this hook FIRST and passes the returned ref through;
 *    hooks compose at the component level.
 *  - CALL ORDER IS LOAD-BEARING: this hook must run BEFORE useEditor. TipTap
 *    creates the editor view synchronously inside useEditor(), and the
 *    StudioDecos decorations body reads actionsRef.current on that first
 *    pass — a post-useEditor call site throws "Cannot access 'actionsRef'
 *    before initialization" (caught by npm run smoke). That is why `editor`
 *    arrives as editorRef.current, not the useEditor return (which doesn't
 *    exist yet at this call site) — see the arg doc below.
 *  - Dependency arrays are verbatim from the component (exhaustive-deps is
 *    advisory; identities of the passed-in helpers are unchanged).
 */
import { useCallback, useEffect, useRef, useState } from "react";
import type { useEditor } from "@tiptap/react";

import { apiFetch } from "../../../lib/api-fetch";
import type { ActionDef, ClientActionItem } from "./studio-editor-constants";

interface AnnotationsArgs {
  slug: string;
  chapter: string;
  /** Passed as editorRef.current (this hook runs before useEditor — see the
   *  header note). Null only on the very first render, when stampAction — the
   *  sole consumer — is inert anyway (activeParaIdx is still null until an
   *  onSelectionUpdate re-render, by which point the ref carries the live
   *  editor instance). */
  editor: ReturnType<typeof useEditor> | null;
  editorRef: React.RefObject<ReturnType<typeof useEditor> | null>;
  activeParaIdx: number | null;
  isReadOnlyStage: boolean;
  selection: string;
  /** Component-level tick bump so the JSX re-reads editor state. */
  refresh: () => void;
}

export function useAnnotations({
  slug,
  chapter,
  editor,
  editorRef,
  activeParaIdx,
  isReadOnlyStage,
  selection,
  refresh,
}: AnnotationsArgs) {
  // Per-paragraph comments: index → text. Stored in a ref for the PM plugin,
  // mirrored in state so the inspector panel re-renders.
  const commentsRef = useRef<Map<number, string>>(new Map());
  const [, setCommentsKey] = useState(0);
  const refreshComments = () => setCommentsKey((k) => k + 1);

  // Deferred AI action-item marks for the active chapter (persisted in the
  // knowledge DB; the CLI drain pass reads them). Held in a ref so PM widgets
  // built outside React always see the latest, mirrored to state for re-render.
  const actionsRef = useRef<ClientActionItem[]>([]);
  const [, setActionsKey] = useState(0);
  const refreshActions = () => setActionsKey((k) => k + 1);

  // Load action-item marks when the chapter changes. Clear synchronously first so
  // the previous chapter's marks never flash on the new chapter.
  useEffect(() => {
    if (!slug || !chapter) return;
    let cancelled = false;
    actionsRef.current = [];
    refreshActions();
    apiFetch<{ ok?: boolean; items?: ClientActionItem[] }>(
      "/api/studio/action-items",
      { query: { book: slug, chapter } },
    )
      .then((json) => {
        if (cancelled || !json?.ok || !Array.isArray(json.items)) return;
        actionsRef.current = json.items as ClientActionItem[];
        refreshActions();
        editorRef.current?.view.dispatch(
          editorRef.current.state.tr.setMeta("refreshTags", true),
        );
      })
      .catch(() => {
        /* offline-friendly */
      });
    return () => {
      cancelled = true;
    };
  }, [slug, chapter]);

  // Remove an action-item mark by id, called from the inline per-paragraph badge
  // toolbar (a PM widget built outside React). Held in a ref so the widget always
  // calls the latest closure.
  const removeActionFnRef = useRef<(id: number) => void>(() => {});

  // Persist a paragraph comment to SQLite (annotations API) on blur.
  const persistComment = useCallback(
    (idx: number, note: string) => {
      apiFetch("/api/annotations", {
        method: "PATCH",
        body: { book: slug, chapter, paraIdx: idx, note },
      }).catch(() => {
        /* non-blocking; comment is also saved with the stage */
      });
    },
    [slug, chapter],
  );

  // Pre-load saved paragraph comments from SQLite when the chapter changes.
  useEffect(() => {
    let cancelled = false;
    apiFetch<{ notes?: Record<string, unknown> }>("/api/annotations", {
      query: { book: slug, chapter },
    })
      .then((json) => {
        if (cancelled || !json) return;
        const notes = json.notes ?? {};
        for (const [idx, note] of Object.entries(notes)) {
          if (typeof note === "string" && note.trim()) {
            commentsRef.current.set(Number(idx), note);
          }
        }
        refreshComments();
      })
      .catch(() => {
        /* offline-friendly; stage-saved comments still load */
      });
    return () => {
      cancelled = true;
    };
  }, [slug, chapter]);

  const markedCount = actionsRef.current.length;
  // Chapter's marks, ordered for the queue list (by paragraph, then insertion).
  const chapterActions = [...actionsRef.current].sort(
    (a, b) => a.para_ordinal - b.para_ordinal || a.id - b.id,
  );

  // Remove one action-item mark (optimistic; DELETE only if it was persisted).
  const removeAction = useCallback(
    (id: number) => {
      actionsRef.current = actionsRef.current.filter((a) => a.id !== id);
      editorRef.current?.view.dispatch(
        editorRef.current.state.tr.setMeta("refreshTags", true),
      );
      refreshActions();
      refresh();
      if (id < 0) return; // optimistic-only, never hit the server
      apiFetch("/api/studio/action-items", {
        method: "DELETE",
        body: { book: slug, chapter, id },
      }).catch(() => {
        /* non-blocking */
      });
    },
    [slug, chapter],
  );

  // Stamp an action item on the active paragraph (or the selected term). Toggles:
  // an identical existing mark is removed. Anchor text is stored so the CLI never
  // depends on the paragraph ordinal staying stable.
  const stampAction = useCallback(
    (def: ActionDef, useSelection: boolean) => {
      if (!editor || activeParaIdx === null || isReadOnlyStage) return;
      const scope: "paragraph" | "term" = useSelection ? "term" : "paragraph";
      const termText = useSelection ? selection.trim() : "";
      if (scope === "term" && !termText) return;
      let paraText = "";
      let i = 0;
      editor.state.doc.forEach((n) => {
        if (i === activeParaIdx) paraText = n.textContent;
        i++;
      });
      const anchorText = scope === "term" ? termText : paraText;
      const existing = actionsRef.current.find(
        (a) =>
          a.para_ordinal === activeParaIdx &&
          a.action_kind === def.kind &&
          a.term_text === termText,
      );
      if (existing) {
        removeAction(existing.id);
        return;
      }
      const tempId = -Date.now();
      actionsRef.current = [
        ...actionsRef.current,
        {
          id: tempId,
          scope,
          para_ordinal: activeParaIdx,
          term_text: termText,
          anchor_text: anchorText,
          action_kind: def.kind,
          status: "pending",
        },
      ];
      editor.view.dispatch(editor.state.tr.setMeta("refreshTags", true));
      refreshActions();
      refresh();
      apiFetch<{ ok?: boolean; item?: ClientActionItem }>(
        "/api/studio/action-items",
        {
          method: "POST",
          body: {
            book: slug,
            chapter,
            scope,
            paraOrdinal: activeParaIdx,
            termText,
            anchorText,
            actionKind: def.kind,
          },
        },
      )
        .then((json) => {
          if (json?.ok && json.item) {
            actionsRef.current = actionsRef.current.map((a) =>
              a.id === tempId ? (json.item as ClientActionItem) : a,
            );
            refreshActions();
          }
        })
        .catch(() => {
          /* non-blocking; optimistic mark stays visible */
        });
    },
    [
      editor,
      activeParaIdx,
      isReadOnlyStage,
      selection,
      slug,
      chapter,
      removeAction,
    ],
  );

  removeActionFnRef.current = removeAction;

  return {
    commentsRef,
    refreshComments,
    persistComment,
    actionsRef,
    refreshActions,
    removeActionFnRef,
    markedCount,
    chapterActions,
    removeAction,
    stampAction,
  };
}
