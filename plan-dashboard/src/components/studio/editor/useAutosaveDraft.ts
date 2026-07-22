/**
 * useAutosaveDraft — debounced per-stage draft persistence so in-progress
 * edits survive a refresh until the chapter is approved. Extracted verbatim
 * from StudioEditor.tsx (R2 pass 2 — one hook per commit).
 *
 * Contract notes (load-bearing, preserved exactly):
 *  - onUpdate reaches the scheduler through scheduleAutosaveRef (the editor is
 *    created before the scheduler exists — same indirection as before).
 *  - autosaveTimer + suppressFlushRef are returned so saveAndApprove can
 *    cancel a pending autosave before approval promotes-and-deletes the draft,
 *    and discard can suppress the beforeunload flush across its reload.
 *  - The draft indicator resets on chapter/stage/lineage switch.
 */
import { useCallback, useEffect, useRef, useState } from "react";

import { apiFetch } from "../../../lib/api-fetch";

interface AutosaveArgs {
  slug: string;
  chapter: string;
  stageId: string | undefined;
  isReadOnlyStage: boolean;
  editorReady: boolean;
  serializeToMarkdown: () => string;
  hasDraftForStage: boolean;
  chapIdx: number;
  activeLineageId: string;
  stageKey: string;
}

export function useAutosaveDraft({
  slug,
  chapter,
  stageId,
  isReadOnlyStage,
  editorReady,
  serializeToMarkdown,
  hasDraftForStage,
  chapIdx,
  activeLineageId,
  stageKey,
}: AutosaveArgs) {
  // Draft autosave state: 'saved' = a draft is on disk (seeded true when the
  // loaded content already came from a draft).
  const [draftState, setDraftState] = useState<
    "idle" | "saving" | "saved" | "error"
  >(hasDraftForStage ? "saved" : "idle");
  // Debounce timer + indirection ref for the autosave scheduler.
  const autosaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const scheduleAutosaveRef = useRef<() => void>(() => {});
  // Set true right before an intentional reload (discard) so the beforeunload
  // flush can't recreate the draft we just deleted.
  const suppressFlushRef = useRef(false);

  const autosaveDraft = useCallback(async () => {
    if (!stageId || isReadOnlyStage || !editorReady) return;
    const content = serializeToMarkdown();
    if (!content.trim()) return;
    setDraftState("saving");
    try {
      await apiFetch("/api/studio/draft", {
        method: "POST",
        body: { slug, chapter, stage: stageId, content },
      });
      setDraftState("saved");
    } catch {
      setDraftState("error");
    }
  }, [
    slug,
    chapter,
    stageId,
    isReadOnlyStage,
    editorReady,
    serializeToMarkdown,
  ]);

  // Debounced scheduler — onUpdate reaches this through scheduleAutosaveRef.
  const scheduleAutosave = useCallback(() => {
    if (isReadOnlyStage) return;
    if (autosaveTimer.current) clearTimeout(autosaveTimer.current);
    autosaveTimer.current = setTimeout(() => {
      void autosaveDraft();
    }, 1200);
  }, [autosaveDraft, isReadOnlyStage]);
  useEffect(() => {
    scheduleAutosaveRef.current = scheduleAutosave;
  }, [scheduleAutosave]);

  // Flush any pending draft when leaving the page/tab so nothing in the
  // debounce window is lost, and reset the indicator on chapter/stage switch.
  useEffect(() => {
    const flush = () => {
      if (suppressFlushRef.current) return;
      if (autosaveTimer.current) {
        clearTimeout(autosaveTimer.current);
        void autosaveDraft();
      }
    };
    const onVisibility = () => {
      if (document.visibilityState === "hidden") flush();
    };
    window.addEventListener("beforeunload", flush);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      window.removeEventListener("beforeunload", flush);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [autosaveDraft]);
  useEffect(() => {
    setDraftState(hasDraftForStage ? "saved" : "idle");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chapIdx, stageKey, activeLineageId]);

  return {
    draftState,
    setDraftState,
    autosaveTimer,
    scheduleAutosaveRef,
    suppressFlushRef,
  };
}
