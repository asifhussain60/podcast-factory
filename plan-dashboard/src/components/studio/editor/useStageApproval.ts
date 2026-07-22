/**
 * useStageApproval — the WC8 write-back approval cluster: per-stage approved
 * flags + approval tokens + accepted-approval keys (localStorage-backed), the
 * Save & Approve / Accept flows, chapter-level finalize (Publish), and the
 * approval toast. Extracted verbatim from StudioEditor.tsx (R2 pass 2 — one
 * hook per commit).
 *
 * Contract notes (load-bearing, preserved exactly):
 *  - saveAndApprove reconstructs the pre-apiFetch error strings byte-for-byte:
 *    an HTTP-level save failure shows the server's message (old !res.ok
 *    branch); transport failures rethrow the underlying cause so the outer
 *    catch renders the same "Network error: …" string; a non-2xx approve
 *    silently skips the success block (approveOk), as the old code did.
 *  - saveAndApprove cancels any pending autosave (autosaveTimer) FIRST so the
 *    debounce can't recreate the draft that approval promotes-and-deletes.
 *  - Acceptance is remembered per (slug, chapter, stage, token) under
 *    pf:approval-accepted:* — approve clears the key for the fresh token,
 *    accept sets it, and the chapter/lineage-switch effect re-seeds
 *    acceptedApprovalKeys from localStorage. That switch effect also reloads
 *    approvals + the finalize flag from the incoming chapter; the stage reset
 *    and the studio:chapter-change dispatch stay in StudioEditor.
 */
import { useCallback, useEffect, useState } from "react";
import type { useEditor } from "@tiptap/react";

import { ApiFetchError, apiFetch } from "../../../lib/api-fetch";
import type { Chapter, Stage } from "./studio-editor-types";

interface StageApprovalArgs {
  slug: string;
  chapter: string;
  chap: Chapter;
  stage: Stage | undefined;
  editor: ReturnType<typeof useEditor>;
  isArchivedView: boolean;
  chapIdx: number;
  activeLineageId: string;
  serializeToMarkdown: () => string;
  commentsRef: React.RefObject<Map<number, string>>;
  /** useAutosaveDraft's debounce timer — cancelled before approval. (Named
   *  *Ref so react-hooks/immutability allows the .current mutation.) */
  autosaveTimerRef: React.RefObject<ReturnType<typeof setTimeout> | null>;
  setDraftState: React.Dispatch<
    React.SetStateAction<"idle" | "saving" | "saved" | "error">
  >;
  /** Clears the locally-cached chap.drafted flag after approval promotes the
   *  draft — the mutation stays in StudioEditor (chap is a hook argument here,
   *  and react-hooks/immutability forbids mutating arguments). */
  clearDraftedFlag: (stageId: string) => void;
  normalizeCurrentEditorBaseline: () => void;
  refresh: () => void;
}

export function useStageApproval({
  slug,
  chapter,
  chap,
  stage,
  editor,
  isArchivedView,
  chapIdx,
  activeLineageId,
  serializeToMarkdown,
  commentsRef,
  autosaveTimerRef,
  setDraftState,
  clearDraftedFlag,
  normalizeCurrentEditorBaseline,
  refresh,
}: StageApprovalArgs) {
  // WC8 write-back loop: which stages are approved (seeded from disk, updated on approve).
  const [approvedStages, setApprovedStages] = useState<Record<string, boolean>>(
    () =>
      Object.fromEntries(
        Object.entries(chap.reviewed).map(([k, v]) => [k, !!v?.approved]),
      ),
  );
  const [approvalTokens, setApprovalTokens] = useState<Record<string, string>>(
    () =>
      Object.fromEntries(
        Object.entries(chap.reviewed).map(([k, v]) => [
          k,
          v?.approved_at ?? "approved",
        ]),
      ),
  );
  const [acceptedApprovalKeys, setAcceptedApprovalKeys] = useState<
    Record<string, boolean>
  >({});
  // Chapter-level finalize flag (Publish button). Seeded from disk, updated on finalize.
  const [finalized, setFinalized] = useState<{ at: string } | null>(
    chap.finalized ?? null,
  );
  // On chapter/lineage switch: reload approvals + finalize flag from the
  // incoming chapter, and re-seed the accepted-approval keys from localStorage.
  useEffect(() => {
    const tokens = Object.fromEntries(
      Object.entries(chap.reviewed).map(([k, v]) => [
        k,
        v?.approved_at ?? "approved",
      ]),
    );
    setApprovedStages(
      Object.fromEntries(
        Object.entries(chap.reviewed).map(([k, v]) => [k, !!v?.approved]),
      ),
    );
    setApprovalTokens(tokens);
    const accepted: Record<string, boolean> = {};
    if (typeof window !== "undefined") {
      for (const [stageKey, token] of Object.entries(tokens)) {
        if (
          window.localStorage.getItem(
            `pf:approval-accepted:${slug}:${chap.slug}:${stageKey}:${token}`,
          ) === "1"
        ) {
          accepted[`${stageKey}:${token}`] = true;
        }
      }
    }
    setAcceptedApprovalKeys(accepted);
    setFinalized(chap.finalized ?? null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chapIdx, activeLineageId]);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [approvalToastOpen, setApprovalToastOpen] = useState(false);
  const [approvalToastText, setApprovalToastText] =
    useState("Augmented Approved");

  const saveAndApprove = useCallback(async () => {
    if (!stage || !editor) return;
    // Cancel any pending autosave so it can't recreate the draft after approval
    // promotes-and-deletes it on the server.
    if (autosaveTimerRef.current) {
      clearTimeout(autosaveTimerRef.current);
      autosaveTimerRef.current = null;
    }
    setSaving(true);
    setSaveError("");
    try {
      const content = serializeToMarkdown();
      const comments = Object.fromEntries(
        [...commentsRef.current.entries()]
          .filter(([, v]) => v.trim())
          .map(([k, v]) => [String(k), v.trim()]),
      );
      try {
        await apiFetch("/api/studio/save-stage", {
          method: "POST",
          body: { slug, chapter, stage: stage.id, content, comments },
        });
      } catch (e) {
        if (e instanceof ApiFetchError && e.status > 0) {
          // HTTP-level failure: show the server's message (old !res.ok branch).
          setSaveError(e.message || `Save failed (${e.status})`);
          return;
        }
        // Transport failure: rethrow the underlying error so the outer catch
        // renders the same "Network error: …" string as before.
        throw e instanceof ApiFetchError ? (e.cause ?? e) : e;
      }
      let approvedPayload: {
        stages?: Record<string, { approved_at?: string }>;
      } | null = null;
      let approveOk = true;
      try {
        approvedPayload = await apiFetch<{
          stages?: Record<string, { approved_at?: string }>;
        }>("/api/studio/review", {
          method: "POST",
          body: { slug, chapter, stage: stage.id, approved: true },
        });
      } catch (e) {
        // The old code silently skipped the success block on a non-2xx approve;
        // transport failures still surface via the outer catch, as before.
        approveOk = false;
        if (!(e instanceof ApiFetchError) || e.status === 0) {
          throw e instanceof ApiFetchError ? (e.cause ?? e) : e;
        }
      }
      if (approveOk) {
        const approvedAt =
          approvedPayload?.stages?.[stage.id]?.approved_at ??
          new Date().toISOString().replace(/\.\d+Z$/, "Z");
        try {
          window.localStorage.removeItem(
            `pf:approval-accepted:${slug}:${chapter}:${stage.id}:${approvedAt}`,
          );
        } catch {
          // localStorage is best-effort; the fresh in-memory token still shows the confirmation.
        }
        setApprovedStages((m) => ({ ...m, [stage.id]: true }));
        setApprovalTokens((m) => ({ ...m, [stage.id]: approvedAt }));
        setAcceptedApprovalKeys((m) => {
          const next = { ...m };
          delete next[`${stage.id}:${approvedAt}`];
          return next;
        });
        // Draft was promoted to the chapter + deleted server-side; clear the
        // indicator and the locally-cached draft flag for this stage.
        setDraftState("idle");
        clearDraftedFlag(stage.id);
        normalizeCurrentEditorBaseline();
        setApprovalToastText(`${stage.label} Approved`);
        setApprovalToastOpen(false);
        window.setTimeout(() => setApprovalToastOpen(true), 0);
        refresh();
      }
    } catch (e) {
      setSaveError(`Network error: ${String(e)}`);
    } finally {
      setSaving(false);
    }
  }, [
    slug,
    chapter,
    stage,
    editor,
    serializeToMarkdown,
    normalizeCurrentEditorBaseline,
  ]);

  const acceptApprovedStage = useCallback(() => {
    if (!stage || !editor) return;
    normalizeCurrentEditorBaseline();
    const token = approvalTokens[stage.id] ?? "approved";
    const acceptedKey = `${stage.id}:${token}`;
    try {
      window.localStorage.setItem(
        `pf:approval-accepted:${slug}:${chapter}:${stage.id}:${token}`,
        "1",
      );
    } catch {
      // localStorage is best-effort; the in-memory state still updates the UI.
    }
    setAcceptedApprovalKeys((m) => ({ ...m, [acceptedKey]: true }));
    setSaveError("");
  }, [
    stage,
    editor,
    normalizeCurrentEditorBaseline,
    approvalTokens,
    slug,
    chapter,
  ]);

  // Publish = mark THIS chapter finalized (reuses the per-chapter review JSON via
  // POST /api/studio/review {finalize}). Reversible. Disabled in archived view.
  const [publishing, setPublishing] = useState(false);
  const toggleFinalized = useCallback(async () => {
    if (isArchivedView) return;
    const next = finalized ? false : true;
    setPublishing(true);
    try {
      const payload = await apiFetch<{ finalized?: { at: string } | null }>(
        "/api/studio/review",
        { method: "POST", body: { slug, chapter, finalize: next } },
      );
      setFinalized(
        next ? (payload?.finalized ?? { at: new Date().toISOString() }) : null,
      );
    } catch {
      /* non-blocking */
    } finally {
      setPublishing(false);
    }
  }, [slug, chapter, finalized, isArchivedView]);

  return {
    approvedStages,
    approvalTokens,
    acceptedApprovalKeys,
    finalized,
    saving,
    saveError,
    approvalToastOpen,
    setApprovalToastOpen,
    approvalToastText,
    publishing,
    saveAndApprove,
    acceptApprovedStage,
    toggleFinalized,
  };
}
